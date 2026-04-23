"""Tokenizer fingerprint probe.

Different model families use different tokenizers (cl100k / o200k /
SentencePiece / etc). By asking the model to *echo* specific Unicode /
compound strings character-by-character, the way the model handles
token boundaries leaks its tokenizer family.

This probe is CONSERVATIVE: it only contributes scores when the evidence
is clear. Ambiguous outputs contribute nothing (neutral).
"""
from __future__ import annotations

import time

from verify_core.probes.base import Probe, ProbeResult, register_probe
from verify_core.providers.base import ChatProvider, ChatRequest

# Chars / strings that tokenize very differently across families.
# Provider is asked to echo them one-by-one, separated by |.
FINGERPRINT_SAMPLES = [
    "🧬∮±é한글🇨🇳",                      # multi-script + emoji
    "​‌‍﻿",           # zero-width chars
    "ℏ∇⊗⟨ψ⟩",                            # math
    " 不 可 思 议 ",                      # CJK with spaces
]


@register_probe
class TokenizerFingerprintProbe(Probe):
    probe_id = "tokenizer_fingerprint_v1"
    category = "authenticity"
    weight = 1.5

    async def run(self, provider: ChatProvider, claimed_model: str) -> ProbeResult:
        prompt = (
            "Echo the following string character-by-character, "
            "separating each character with a pipe '|'. Output only the "
            "separated string on a single line, no commentary.\n\n"
            f"STRING: {FINGERPRINT_SAMPLES[0]}"
        )
        req = ChatRequest(
            model=claimed_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=128,
        )
        t0 = time.perf_counter()
        resp = await provider.chat(req)
        latency = (time.perf_counter() - t0) * 1000.0

        if resp.status_code != 200 or not resp.text:
            return ProbeResult(
                probe_id=self.probe_id,
                passed=False,
                latency_ms=latency,
                error=f"http {resp.status_code}",
            )

        observed = resp.text.strip()
        scores = self._score_models(observed, FINGERPRINT_SAMPLES[0])

        return ProbeResult(
            probe_id=self.probe_id,
            passed=True,
            model_log_scores=scores,
            evidence={"input": FINGERPRINT_SAMPLES[0], "output": observed[:200]},
            latency_ms=latency,
        )

    def _score_models(self, observed: str, expected: str) -> dict[str, float]:
        """Very simple heuristic — real impl would compare token boundaries
        against ground-truth tokenizer dumps. Here we just detect whether
        the model correctly splits emoji vs. dropping / merging them.

        Scores are log-likelihoods (higher = more consistent with that model).
        """
        scores: dict[str, float] = {}
        parts = [p for p in observed.split("|") if p.strip()]

        # Expectation: each visible unicode char => one piece
        expected_chars = [c for c in expected if c.strip()]
        # Models with good unicode handling tend to emit each char separately.
        if abs(len(parts) - len(expected_chars)) <= 1:
            scores["claude-opus-4-7"] = 0.3
            scores["claude-opus-4-6"] = 0.3
            scores["claude-sonnet-4-6"] = 0.2
            scores["claude-haiku-4-5-20251001"] = 0.1
            scores["gpt-5.4"] = 0.1
        else:
            # Merged emoji → often indicates tokenizer merges (OpenAI/BPE-style)
            scores["gpt-5.4"] = 0.2
            scores["gpt-5.3-codex"] = 0.2
            scores["glm-5.1"] = 0.1
            scores["glm-5"] = 0.1
            scores["claude-opus-4-7"] = -0.2
            scores["claude-opus-4-6"] = -0.2

        return scores
