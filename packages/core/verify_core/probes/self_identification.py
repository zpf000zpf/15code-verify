"""Self-identification probe.

We never ask "Who are you?" directly (easily overridden by system prompt).
Instead we use side-channel questions where different model families have
*distinct, hard-to-override* default answers.
"""
from __future__ import annotations

import re
import time

from verify_core.probes.base import Probe, ProbeResult, register_probe
from verify_core.providers.base import ChatProvider, ChatRequest

# (question, keyword_patterns → model_family scores)
# Patterns are regex, matched case-insensitive.
QUESTIONS: list[tuple[str, list[tuple[str, dict[str, float]]]]] = [
    (
        "In exactly one sentence, what is your approximate training data cutoff date? "
        "Just state the month and year.",
        [
            (r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+202[5-9]",
             {"claude-opus-4-7": 0.3, "claude-opus-4-6": 0.2,
              "claude-sonnet-4-6": 0.2, "gpt-5.4": 0.2, "gpt-5.3-codex": 0.1}),
            (r"(october|oct)\s+2023", {"claude-haiku-4-5-20251001": 0.2}),
            (r"202[3-4]", {"glm-5": 0.15, "glm-5.1": 0.15}),
        ],
    ),
    (
        "Reply with a single word: what is the default temperature used by your API "
        "when not specified?",
        [
            (r"\b1\.0?\b|\bone\b", {"claude-opus-4-7": 0.2, "claude-opus-4-6": 0.2,
                                    "claude-sonnet-4-6": 0.2,
                                    "claude-haiku-4-5-20251001": 0.2}),
            (r"\b0?\.7\b|\bseven\b", {"gpt-5.4": 0.2, "gpt-5.3-codex": 0.2,
                                      "glm-5": 0.15, "glm-5.1": 0.15}),
        ],
    ),
]


@register_probe
class SelfIdentificationProbe(Probe):
    probe_id = "self_identification_v1"
    category = "authenticity"
    weight = 1.0

    async def run(self, provider: ChatProvider, claimed_model: str) -> ProbeResult:
        scores: dict[str, float] = {}
        evidence: dict[str, str] = {}
        t0 = time.perf_counter()

        for i, (question, patterns) in enumerate(QUESTIONS):
            req = ChatRequest(
                model=claimed_model,
                messages=[{"role": "user", "content": question}],
                temperature=0.0,
                max_tokens=64,
            )
            resp = await provider.chat(req)
            if resp.status_code != 200 or not resp.text:
                continue
            answer = resp.text.strip()
            evidence[f"q{i}"] = answer[:120]
            for pattern, model_scores in patterns:
                if re.search(pattern, answer, re.IGNORECASE):
                    for m, s in model_scores.items():
                        if m.startswith("__"):
                            continue
                        scores[m] = scores.get(m, 0.0) + s

        latency = (time.perf_counter() - t0) * 1000.0
        return ProbeResult(
            probe_id=self.probe_id,
            passed=True,
            model_log_scores=scores,
            evidence=evidence,
            latency_ms=latency,
        )
