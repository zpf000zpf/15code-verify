"""Latency fingerprint probe — infer model size/quantization from TTFT/throughput.

Larger models (Opus/GPT-5.4) have meaningfully higher TTFT than mini/haiku.
Quantized variants often have *lower* ITL (faster per-token) but also
subtly different output patterns — this probe only measures timing.
"""
from __future__ import annotations

import asyncio
import time

from verify_core.probes.base import Probe, ProbeResult, register_probe
from verify_core.providers.base import ChatProvider, ChatRequest


@register_probe
class LatencyFingerprintProbe(Probe):
    probe_id = "latency_fingerprint_v1"
    category = "capability"
    weight = 0.7

    async def run(self, provider: ChatProvider, claimed_model: str) -> ProbeResult:
        t0 = time.perf_counter()
        ttft_samples: list[float] = []
        throughput_samples: list[float] = []

        for _ in range(3):
            t_start = time.perf_counter()
            req = ChatRequest(
                model=claimed_model,
                messages=[{"role": "user",
                           "content": "Write exactly 50 words about the Pacific Ocean."}],
                temperature=0.0,
                max_tokens=100,
                stream=True,
            )
            ttft = None
            n_chunks = 0
            try:
                async for chunk in provider.chat_stream(req):
                    now = time.perf_counter()
                    if ttft is None:
                        ttft = (now - t_start) * 1000
                    n_chunks += 1
                total = (time.perf_counter() - t_start)
                if ttft is not None and total > 0 and n_chunks > 10:
                    ttft_samples.append(ttft)
                    throughput_samples.append(n_chunks / total)
            except Exception:
                continue

        if not ttft_samples:
            return ProbeResult(probe_id=self.probe_id, passed=False,
                               error="no successful streaming responses",
                               latency_ms=(time.perf_counter()-t0)*1000)

        ttft_med = sorted(ttft_samples)[len(ttft_samples)//2]
        tput_med = sorted(throughput_samples)[len(throughput_samples)//2]

        # Heuristic tiers (illustrative — real tiers sourced from ground truth)
        scores: dict[str, float] = {}
        if ttft_med < 500:
            # very fast first byte → flash/mini/haiku tier
            scores = {"claude-haiku-4-5-20251001": 0.3,
                      "gpt-5.3-codex": 0.1,
                      "glm-5": 0.2,
                      "claude-opus-4-7": -0.3}
        elif ttft_med < 1500:
            scores = {"claude-sonnet-4-6": 0.2,
                      "gpt-5.3-codex": 0.2,
                      "gpt-5.4": 0.1,
                      "glm-5.1": 0.1}
        else:
            scores = {"claude-opus-4-7": 0.3,
                      "claude-opus-4-6": 0.2,
                      "gpt-5.4": 0.2,
                      "claude-haiku-4-5-20251001": -0.3}

        return ProbeResult(
            probe_id=self.probe_id,
            passed=True,
            model_log_scores=scores,
            evidence={"ttft_ms_median": round(ttft_med, 0),
                      "throughput_chunks_per_s": round(tput_med, 1)},
            latency_ms=(time.perf_counter()-t0)*1000,
        )
