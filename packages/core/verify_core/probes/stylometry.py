"""Stylometry probe — style fingerprinting at temperature=0.

Samples multiple deterministic generations and computes style features
(avg length, markdown rate, list-vs-prose preference). Compared against
Ground-Truth baselines harvested weekly from 15code's OWN API.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
from pathlib import Path

from verify_core.probes.base import Probe, ProbeResult, register_probe
from verify_core.providers.base import ChatProvider, ChatRequest

STYLOMETRY_PROMPTS = [
    "Briefly explain what a monad is to a programmer.",
    "Write a short haiku about distributed systems.",
    "List three tips for writing clean Python code.",
]


def _load_baselines() -> dict[str, dict[str, float]]:
    """Prefer dynamic Ground-Truth baselines; fall back to seed estimates."""
    env = os.getenv("GROUND_TRUTH_DIR")
    candidates = []
    if env:
        candidates.append(Path(env) / "baseline-latest.json")
    candidates.extend([
        Path("/opt/15code-verify/data/baselines/baseline-latest.json"),
        Path(__file__).resolve().parent.parent.parent.parent.parent /
            "data" / "baselines" / "baseline-latest.json",
    ])
    for c in candidates:
        if c and c.is_file():
            try:
                data = json.loads(c.read_text())
                return {k: v for k, v in data.get("baselines", {}).items() if "error" not in v}
            except Exception:
                continue
    # Seed fallback — covers 15code's 8 in-catalog models.
    return {
        "claude-opus-4-7":           {"avg_len": 420, "md_rate": 0.85, "list_rate": 0.60},
        "claude-opus-4-6":           {"avg_len": 415, "md_rate": 0.85, "list_rate": 0.60},
        "claude-sonnet-4-6":         {"avg_len": 380, "md_rate": 0.80, "list_rate": 0.55},
        "claude-haiku-4-5-20251001": {"avg_len": 220, "md_rate": 0.55, "list_rate": 0.50},
        "gpt-5.4":                   {"avg_len": 300, "md_rate": 0.65, "list_rate": 0.70},
        "gpt-5.3-codex":             {"avg_len": 260, "md_rate": 0.60, "list_rate": 0.65},
        "glm-5.1":                   {"avg_len": 340, "md_rate": 0.70, "list_rate": 0.60},
        "glm-5":                     {"avg_len": 280, "md_rate": 0.60, "list_rate": 0.55},
    }


REFERENCE_BASELINES = _load_baselines()


@register_probe
class StylometryProbe(Probe):
    probe_id = "stylometry_v1"
    category = "stylometry"
    weight = 1.2

    async def run(self, provider: ChatProvider, claimed_model: str) -> ProbeResult:
        t0 = time.perf_counter()
        reqs = [
            ChatRequest(
                model=claimed_model,
                messages=[{"role": "user", "content": p}],
                temperature=0.0,
                max_tokens=256,
            )
            for p in STYLOMETRY_PROMPTS
        ]
        resps = await asyncio.gather(
            *(provider.chat(r) for r in reqs), return_exceptions=True
        )
        texts = [
            r.text for r in resps
            if not isinstance(r, Exception) and r.status_code == 200 and r.text
        ]
        if not texts:
            return ProbeResult(
                probe_id=self.probe_id,
                passed=False,
                error="no successful responses",
                latency_ms=(time.perf_counter() - t0) * 1000.0,
            )

        features = self._extract_features(texts)
        scores = self._score_against_baselines(features)
        return ProbeResult(
            probe_id=self.probe_id,
            passed=True,
            model_log_scores=scores,
            evidence={"features": features, "samples": len(texts)},
            latency_ms=(time.perf_counter() - t0) * 1000.0,
        )

    def _extract_features(self, texts: list[str]) -> dict[str, float]:
        n = len(texts)
        avg_len = sum(len(t) for t in texts) / n
        md_rate = sum(1 for t in texts if re.search(r"[`*#_-]{1,}", t)) / n
        list_rate = sum(1 for t in texts if re.search(r"^\s*[-*\d]", t, re.MULTILINE)) / n
        return {"avg_len": avg_len, "md_rate": md_rate, "list_rate": list_rate}

    def _score_against_baselines(self, feats: dict[str, float]) -> dict[str, float]:
        scores: dict[str, float] = {}
        for model, baseline in REFERENCE_BASELINES.items():
            # Negative L1 distance (normalized) → higher = more similar
            d = 0.0
            d += abs(feats["avg_len"] - baseline["avg_len"]) / 500
            d += abs(feats["md_rate"] - baseline["md_rate"])
            d += abs(feats["list_rate"] - baseline["list_rate"])
            scores[model] = -d
        return scores
