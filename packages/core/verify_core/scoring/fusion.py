"""Score fusion — combines probe log-scores into model probabilities and a
trust score. Deliberately conservative / neutral."""
from __future__ import annotations

import math
from typing import Iterable

from verify_core.probes.base import ProbeResult
from verify_core.report import (
    AuthenticityResult, BillingAuditResult, CacheAuditResult,
    Finding, QoSResult, Severity,
)


class ScoringEngine:
    """Fuses per-probe log scores into a softmax over candidate models,
    then derives an authenticity verdict and trust score."""

    def fuse_authenticity(
        self,
        probe_results: Iterable[ProbeResult],
        claimed_model: str,
    ) -> AuthenticityResult:
        # accumulate weighted log scores per model
        total: dict[str, float] = {}
        count = 0
        for pr in probe_results:
            if not pr.passed or not pr.model_log_scores:
                continue
            count += 1
            for m, s in pr.model_log_scores.items():
                total[m] = total.get(m, 0.0) + s

        if not total:
            return AuthenticityResult(
                claimed_model=claimed_model,
                confidence_is_claimed=0.0,
                evidence_count=count,
                findings=[Finding(
                    code="AUTH_NO_SIGNAL",
                    severity=Severity.INFO,
                    title="Insufficient authenticity signal",
                    detail="No probe produced usable scores (likely due to errors or timeouts).",
                )],
            )

        # softmax
        m = max(total.values())
        exps = {k: math.exp(v - m) for k, v in total.items()}
        z = sum(exps.values())
        probs = {k: v / z for k, v in exps.items()}

        # find top model
        likely = max(probs.items(), key=lambda kv: kv[1])
        p_claimed = probs.get(claimed_model, 0.0)

        findings: list[Finding] = []
        if likely[0] != claimed_model and likely[1] - p_claimed > 0.35:
            findings.append(Finding(
                code="AUTH_CLAIM_MISMATCH",
                severity=Severity.WARN,
                title="Response patterns deviate from claimed model",
                detail=(
                    f"Observed patterns are more consistent with '{likely[0]}' "
                    f"(p={likely[1]:.0%}) than the claimed '{claimed_model}' "
                    f"(p={p_claimed:.0%}). This is a statistical indicator, "
                    f"not a definitive identification."
                ),
                evidence={"probabilities": {k: round(v, 3) for k, v in probs.items()}},
            ))

        return AuthenticityResult(
            claimed_model=claimed_model,
            confidence_is_claimed=round(p_claimed, 3),
            likely_model=likely[0],
            likely_model_confidence=round(likely[1], 3),
            model_probabilities={k: round(v, 3) for k, v in probs.items()},
            evidence_count=count,
            findings=findings,
        )

    def compute_trust_score(
        self,
        authenticity: AuthenticityResult | None,
        billing: BillingAuditResult | None,
        cache: CacheAuditResult | None,
        qos: QoSResult | None,
    ) -> tuple[int, str]:
        """Returns (trust_score_0_100, verdict).

        Verdict uses NEUTRAL technical language (never 'fraud' / 'fake').
        """
        score = 100.0

        if authenticity:
            # Up to -40 for low authenticity confidence
            score -= (1.0 - authenticity.confidence_is_claimed) * 40
        else:
            score -= 10

        if billing:
            # Only penalize when billing.systematic_inflation is True
            # (i.e. the tokenizer was authoritative AND the deviation was real).
            # Estimate-only numbers are noisy and must not affect trust score.
            if billing.systematic_inflation:
                infl = abs(billing.input_token_deviation_pct) + abs(
                    billing.output_token_deviation_pct
                )
                score -= min(infl, 25.0)

        if cache and not cache.cache_claim_matches_reality:
            score -= 15

        if qos:
            if qos.quantization_suspected:
                score -= 10
            score -= min(qos.error_rate * 100, 10)

        score = max(0.0, min(100.0, score))

        if score >= 85:
            verdict = "consistent_with_claim"
        elif score >= 60:
            verdict = "partial_consistency"
        elif score >= 35:
            verdict = "notable_deviations_observed"
        else:
            verdict = "significant_deviations_observed"

        return int(round(score)), verdict
