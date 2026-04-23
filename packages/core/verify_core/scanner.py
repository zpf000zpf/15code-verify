"""Scanner — main orchestrator that runs probes, auditors, and scoring."""
from __future__ import annotations

import asyncio
import secrets
import time
from typing import Callable, Optional

from verify_core.branding import BRAND, get_promo_rotation
from verify_core.cache_audit import CacheAuditor
from verify_core.config import ScanConfig
from verify_core.probes.base import ProbeRegistry, ProbeResult
from verify_core.providers import build_provider
from verify_core.providers.base import ChatProvider, ChatRequest
from verify_core.report import (
    BillingAuditResult, Finding, QoSResult, ScanReport, Severity,
)
from verify_core.scoring import ScoringEngine
from verify_core.tokenizers import TokenOracle


ProgressCallback = Callable[[str, float], None]


class Scanner:
    """The public-facing scanner.

    Usage:
        scanner = Scanner(ScanConfig(...))
        report = await scanner.run_async()
        # or
        report = scanner.run()
    """

    def __init__(self, config: ScanConfig, on_progress: Optional[ProgressCallback] = None):
        self.config = config
        self.on_progress = on_progress or (lambda _m, _p: None)

    # ------------------------------------------------------------------
    # sync convenience wrapper
    def run(self) -> ScanReport:
        return asyncio.run(self.run_async())

    # ------------------------------------------------------------------
    async def run_async(self) -> ScanReport:
        t0 = time.perf_counter()
        cfg = self.config
        scan_id = cfg.scan_id or f"scan_{secrets.token_hex(6)}"

        provider = build_provider(
            protocol=cfg.protocol.value,
            base_url=cfg.base_url,
            api_key=cfg.api_key.get_secret_value(),
            timeout_s=cfg.timeout_s,
        )

        promo = get_promo_rotation("zh")
        report = ScanReport(
            scan_id=scan_id,
            claimed_model=cfg.claimed_model,
            base_url=cfg.base_url,
            methodology_version=cfg.methodology_version,
            published_to_leaderboard=cfg.publish_to_leaderboard,
            generated_by=BRAND["name"],
            generator_url=BRAND["verify_url"],
            promo={"message": promo["text"], "url": f"https://{promo['cta']}"},
        )

        # Phase 1: connectivity
        self._notify("connectivity_check", 0.02)
        ok = await self._connectivity_check(provider, cfg.claimed_model)
        if not ok:
            report.verdict = "unreachable"
            report.duration_s = time.perf_counter() - t0
            return report

        # Phase 2: authenticity probes
        if cfg.enable_authenticity:
            self._notify("running_authenticity_probes", 0.1)
            probe_results = await self._run_probes(provider, cfg)
            engine = ScoringEngine()
            report.authenticity = engine.fuse_authenticity(probe_results, cfg.claimed_model)
            report.probes_executed += len(probe_results)

        # Phase 3: billing audit
        if cfg.enable_billing_audit:
            self._notify("running_billing_audit", 0.55)
            report.billing_audit = await self._audit_billing(provider, cfg.claimed_model)

        # Phase 4: cache audit
        if cfg.enable_cache_audit:
            self._notify("running_cache_audit", 0.75)
            auditor = CacheAuditor()
            report.cache_audit = await auditor.run(provider, cfg.claimed_model)

        # Phase 5: QoS
        if cfg.enable_qos:
            self._notify("running_qos_profile", 0.85)
            report.qos = await self._profile_qos(provider, cfg.claimed_model)

        # Final scoring
        self._notify("finalizing", 0.95)
        engine = ScoringEngine()
        report.trust_score, report.verdict = engine.compute_trust_score(
            report.authenticity, report.billing_audit, report.cache_audit, report.qos,
        )
        report.duration_s = time.perf_counter() - t0
        self._notify("done", 1.0)
        return report

    # ------------------------------------------------------------------
    def _notify(self, stage: str, p: float) -> None:
        try:
            self.on_progress(stage, p)
        except Exception:
            pass

    async def _connectivity_check(self, provider: ChatProvider, model: str) -> bool:
        try:
            req = ChatRequest(
                model=model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=4,
            )
            resp = await provider.chat(req)
            return resp.status_code == 200
        except Exception:
            return False

    async def _run_probes(self, provider: ChatProvider, cfg: ScanConfig) -> list[ProbeResult]:
        probe_classes = ProbeRegistry.all()[: cfg.probe_budget]
        sem = asyncio.Semaphore(cfg.concurrency)

        async def _run_one(cls):
            async with sem:
                probe = cls()
                try:
                    return await probe.run(provider, cfg.claimed_model)
                except Exception as e:
                    return ProbeResult(
                        probe_id=cls.probe_id,
                        passed=False,
                        error=str(e)[:200],
                    )

        results = await asyncio.gather(*(_run_one(c) for c in probe_classes))
        return [r for r in results if r is not None]

    async def _audit_billing(self, provider: ChatProvider, model: str) -> BillingAuditResult:
        findings: list[Finding] = []
        oracle = TokenOracle(model)
        authoritative_any = False

        # 3 sample prompts of varying lengths
        samples = [
            "Explain quantum entanglement in one sentence.",
            ("Summarize the following passage in bullet points. " * 20),
            ("The quick brown fox jumps over the lazy dog. " * 200),
        ]

        in_devs: list[float] = []
        out_devs: list[float] = []
        total_samples = 0

        for text in samples:
            msgs = [{"role": "user", "content": text}]
            local_in, exact = await oracle.count_messages_authoritative(msgs)
            if exact:
                authoritative_any = True
            req = ChatRequest(
                model=model,
                messages=msgs,
                temperature=0.0,
                max_tokens=64,
            )
            resp = await provider.chat(req)
            if resp.status_code != 200:
                continue
            total_samples += 1
            reported_in = resp.usage.input_tokens
            if local_in > 0 and reported_in > 0:
                in_devs.append((reported_in - local_in) / local_in * 100.0)
            local_out = oracle.count(resp.text or "")
            reported_out = resp.usage.output_tokens
            if local_out > 0 and reported_out > 0:
                out_devs.append((reported_out - local_out) / local_out * 100.0)

        in_dev = sum(in_devs) / len(in_devs) if in_devs else 0.0
        out_dev = sum(out_devs) / len(out_devs) if out_devs else 0.0

        authoritative = oracle.is_authoritative or authoritative_any
        systematic = abs(in_dev) > 5.0 and authoritative
        if systematic:
            findings.append(Finding(
                code="BILLING_INPUT_DEVIATION",
                severity=Severity.WARN,
                title="Input token count deviates from authoritative count",
                detail=(
                    f"Reported input tokens differ from authoritative count by "
                    f"an average of {in_dev:+.1f}% across {len(in_devs)} samples."
                ),
            ))
        elif not authoritative:
            findings.append(Finding(
                code="BILLING_ESTIMATE_ONLY",
                severity=Severity.INFO,
                title="Token accounting is an estimate",
                detail=(
                    "No authoritative tokenizer available for this model family "
                    "(set ANTHROPIC_API_KEY on the scanner host for exact Claude counts). "
                    "Billing deviation is approximate."
                ),
            ))

        return BillingAuditResult(
            input_token_deviation_pct=round(in_dev, 2),
            output_token_deviation_pct=round(out_dev, 2),
            sample_count=total_samples,
            systematic_inflation=systematic,
            findings=findings,
        )

    async def _profile_qos(self, provider: ChatProvider, model: str) -> QoSResult:
        """Real streaming QoS profile — measures TTFT (first-token latency)
        and ITL (inter-token latency) directly from the SSE stream."""
        import time as _time
        ttft_list: list[float] = []
        itl_list: list[float] = []
        total_list: list[float] = []
        errors = 0
        N = 5
        for _ in range(N):
            req = ChatRequest(
                model=model,
                messages=[{"role": "user",
                          "content": "Count from 1 to 20 separated by single spaces. Output only the numbers."}],
                temperature=0.0,
                max_tokens=96,
                stream=True,
            )
            t0 = _time.perf_counter()
            ttft = None
            last_t = None
            iters = 0
            try:
                async for _chunk in provider.chat_stream(req):
                    now = _time.perf_counter()
                    if ttft is None:
                        ttft = (now - t0) * 1000.0
                    else:
                        if last_t is not None:
                            itl_list.append((now - last_t) * 1000.0)
                    last_t = now
                    iters += 1
                total = (_time.perf_counter() - t0) * 1000.0
                if ttft is not None and iters > 0:
                    ttft_list.append(ttft)
                    total_list.append(total)
                else:
                    errors += 1
            except Exception:
                errors += 1

        def pct(arr, p):
            if not arr:
                return 0.0
            a = sorted(arr)
            idx = min(len(a) - 1, int(len(a) * p))
            return a[idx]

        return QoSResult(
            ttft_ms_p50=round(pct(ttft_list, 0.5), 1),
            ttft_ms_p95=round(pct(ttft_list, 0.95), 1),
            itl_ms_p50=round(pct(itl_list, 0.5), 1),
            error_rate=round(errors / N, 2),
            capability_score=None,
            quantization_suspected=False,
            findings=[],
        )
