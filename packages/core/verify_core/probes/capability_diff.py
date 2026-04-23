"""Capability differential probe.

Poses questions where we know ground-truth correctness + difficulty
varies across model tiers. A claimed "Opus-class" model that fails
Opus-easy questions is suspicious.

IMPORTANT (LEGAL): Questions and grading logic here are *illustrative*.
Production probes must use a separate private bank (data/probe_bank/capability/)
with frequent rotation so resellers cannot route-around.
"""
from __future__ import annotations

import time

from verify_core.probes.base import Probe, ProbeResult, register_probe
from verify_core.providers.base import ChatProvider, ChatRequest


# (prompt, expected keyword, difficulty_tier)
# tier: "easy_all" / "hard_opus_only" / "gpt_specific" / etc.
QUESTIONS: list[tuple[str, str, str]] = [
    ("What is 17 * 23? Reply with just the number.", "391", "easy_all"),
    (
        "A train leaves A at 9:00 going 60km/h. Another leaves B at 10:30 going 80km/h "
        "toward A. A and B are 400km apart. At what time do they meet? Just give HH:MM.",
        "12:30",
        "hard_opus_only",
    ),
]


@register_probe
class CapabilityDiffProbe(Probe):
    probe_id = "capability_diff_v1"
    category = "capability"
    weight = 1.3

    async def run(self, provider: ChatProvider, claimed_model: str) -> ProbeResult:
        t0 = time.perf_counter()
        evidence: dict[str, str] = {}
        easy_correct = 0
        hard_correct = 0
        easy_total = 0
        hard_total = 0

        for i, (prompt, expected, tier) in enumerate(QUESTIONS):
            req = ChatRequest(
                model=claimed_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=64,
            )
            resp = await provider.chat(req)
            ans = (resp.text or "").strip()
            evidence[f"q{i}"] = ans[:80]
            correct = expected.lower() in ans.lower()
            if tier == "easy_all":
                easy_total += 1
                if correct:
                    easy_correct += 1
            elif tier == "hard_opus_only":
                hard_total += 1
                if correct:
                    hard_correct += 1

        # Scoring rule of thumb (illustrative):
        #  - fail easy → model is broken (all scores negative)
        #  - pass easy + pass hard → consistent with top-tier (Opus)
        #  - pass easy, fail hard → consistent with mini / mid-tier
        scores: dict[str, float] = {}
        if easy_total and easy_correct / easy_total < 0.5:
            # fails even easy → badly broken
            scores = {"claude-opus-4-7": -0.5, "claude-opus-4-6": -0.5,
                      "gpt-5.4": -0.3, "claude-sonnet-4-6": -0.2,
                      "claude-haiku-4-5-20251001": 0.1}  # small models plausibly fail
        else:
            if hard_total and hard_correct / hard_total >= 0.8:
                # passes hard → top-tier flagship
                scores = {"claude-opus-4-7": 0.4, "claude-opus-4-6": 0.4,
                          "gpt-5.4": 0.3, "glm-5.1": 0.2,
                          "claude-haiku-4-5-20251001": -0.2}
            else:
                # passes easy but not hard → mid/fast tier
                scores = {"claude-sonnet-4-6": 0.2, "gpt-5.3-codex": 0.2,
                          "glm-5": 0.2, "claude-haiku-4-5-20251001": 0.1,
                          "claude-opus-4-7": -0.2}

        return ProbeResult(
            probe_id=self.probe_id,
            passed=True,
            model_log_scores=scores,
            evidence={
                **evidence,
                "easy_pass_rate": easy_correct / max(easy_total, 1),
                "hard_pass_rate": hard_correct / max(hard_total, 1),
            },
            latency_ms=(time.perf_counter() - t0) * 1000.0,
        )
