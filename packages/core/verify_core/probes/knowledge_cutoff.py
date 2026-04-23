"""Knowledge-cutoff probe — indirect detection via dated events.

Instead of asking "what's your cutoff" (easily spoofed), we ask about
*specific* events whose dates we know, and observe whether the model
shows awareness of them.
"""
from __future__ import annotations

import asyncio
import re
import time

from verify_core.probes.base import Probe, ProbeResult, register_probe
from verify_core.providers.base import ChatProvider, ChatRequest


# (question, key-phrase regex that indicates knowledge of event, era_bucket)
PROBES = [
    # These are illustrative — real bank uses private, rotating set
    ("In one sentence, state who won the 2024 US Presidential election.",
     r"trump|harris",
     "post-2024-11"),
    ("Briefly describe Anthropic's Claude 3.5 Sonnet release.",
     r"claude\s*3\.?5|sonnet|june\s*2024|anthropic",
     "post-2024-06"),
    ("In one sentence, what is Python 3.13's major new feature?",
     r"jit|free[\s-]?threaded|nogil|3\.13",
     "post-2024-10"),
]


@register_probe
class KnowledgeCutoffProbe(Probe):
    probe_id = "knowledge_cutoff_v1"
    category = "capability"
    weight = 0.9

    async def run(self, provider: ChatProvider, claimed_model: str) -> ProbeResult:
        t0 = time.perf_counter()
        evidence: dict[str, str] = {}
        awareness_score = 0  # count of events the model is aware of
        n = 0

        for i, (q, pat, era) in enumerate(PROBES):
            resp = await provider.chat(ChatRequest(
                model=claimed_model,
                messages=[{"role": "user", "content": q}],
                temperature=0.0,
                max_tokens=100,
            ))
            if resp.status_code != 200 or not resp.text:
                continue
            n += 1
            ans = resp.text
            evidence[f"q{i}_{era}"] = ans[:100]
            if re.search(pat, ans, re.IGNORECASE):
                awareness_score += 1

        awareness_pct = awareness_score / max(n, 1)
        scores: dict[str, float] = {}
        # Claude family has ~late-2024 cutoff; GPT-5 same; GLM-5 ~late-2024
        # A model claiming to be "Opus-class" but failing all date-aware questions → suspicious
        if awareness_pct < 0.2:
            # too ignorant → likely older / smaller model
            scores = {"claude-haiku-4-5-20251001": 0.1,
                      "gpt-5.3-codex": 0.1,
                      "claude-opus-4-7": -0.2,
                      "gpt-5.4": -0.1}
        else:
            scores = {"claude-opus-4-7": 0.2,
                      "gpt-5.4": 0.2,
                      "claude-sonnet-4-6": 0.1,
                      "glm-5.1": 0.1}

        return ProbeResult(
            probe_id=self.probe_id,
            passed=True,
            model_log_scores=scores,
            evidence={**evidence, "awareness_pct": round(awareness_pct, 2)},
            latency_ms=(time.perf_counter()-t0)*1000,
        )
