"""Collect style / tokenizer / capability baselines against official-style APIs.

Designed to run periodically (weekly) on the 15code server with:
    GROUND_TRUTH_BASE_URL = "https://claude.15code.com/v1"  (or direct Anthropic)
    GROUND_TRUTH_API_KEY  = 15code-owned key
Outputs:
    data/baselines/baseline-YYYYMMDD.json
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import statistics
from datetime import datetime
from pathlib import Path
from typing import Optional

from verify_core.catalog import get_catalog
from verify_core.providers import build_provider
from verify_core.providers.base import ChatRequest


STYLOMETRY_PROMPTS = [
    "Briefly explain what a monad is to a programmer.",
    "Write a short haiku about distributed systems.",
    "List three tips for writing clean Python code.",
    "Explain REST vs GraphQL in one paragraph.",
    "Name three classic data-structure interview questions.",
]


class GroundTruthCollector:
    """Runs a fixed battery of prompts against each model in the 15code catalog
    and aggregates the statistical signatures used by stylometry probes."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ):
        self.base_url = base_url or os.getenv("GROUND_TRUTH_BASE_URL", "https://claude.15code.com/v1")
        self.api_key = api_key or os.getenv("GROUND_TRUTH_API_KEY", "")
        self.output_dir = Path(output_dir or os.getenv("GROUND_TRUTH_DIR", "data/baselines"))

    async def collect_all(self) -> Path:
        if not self.api_key:
            raise RuntimeError("GROUND_TRUTH_API_KEY not set — refusing to run")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        catalog = get_catalog()
        baselines: dict[str, dict] = {}

        for m in catalog.all():
            try:
                feats = await self._collect_one(m.id, m.protocol)
                baselines[m.id] = feats
                print(f"✓ {m.id:30s}  avg_len={feats['avg_len']:.0f}  md={feats['md_rate']:.2f}")
            except Exception as e:
                print(f"✗ {m.id:30s}  failed: {e}")
                baselines[m.id] = {"error": str(e)[:200]}

        out = {
            "schema_version": 1,
            "collected_at": datetime.utcnow().isoformat() + "Z",
            "methodology_version": "v1.0",
            "base_url": self.base_url,
            "baselines": baselines,
        }
        fname = self.output_dir / f"baseline-{datetime.utcnow().strftime('%Y%m%d')}.json"
        fname.write_text(json.dumps(out, indent=2, ensure_ascii=False))
        # also update the "latest" symlink
        latest = self.output_dir / "baseline-latest.json"
        if latest.exists() or latest.is_symlink():
            latest.unlink()
        try:
            latest.symlink_to(fname.name)
        except OSError:
            # fallback for systems without symlink support
            latest.write_text(json.dumps(out, indent=2, ensure_ascii=False))
        return fname

    async def _collect_one(self, model: str, protocol: str) -> dict:
        provider = build_provider(protocol, self.base_url, self.api_key, timeout_s=60)
        tasks = [
            provider.chat(ChatRequest(
                model=model,
                messages=[{"role": "user", "content": p}],
                temperature=0.0,
                max_tokens=256,
            ))
            for p in STYLOMETRY_PROMPTS
        ]
        resps = await asyncio.gather(*tasks, return_exceptions=True)
        texts = [r.text for r in resps if hasattr(r, "text") and r.status_code == 200 and r.text]
        if not texts:
            raise RuntimeError("no successful responses")

        lengths = [len(t) for t in texts]
        md_rate = sum(1 for t in texts if re.search(r"[`*#_]{1,}", t)) / len(texts)
        list_rate = sum(1 for t in texts if re.search(r"^\s*[-*\d]", t, re.MULTILINE)) / len(texts)
        avg_tokens_per_response = statistics.mean(
            [r.usage.output_tokens for r in resps if hasattr(r, "usage") and r.usage.output_tokens > 0]
            or [0]
        )

        return {
            "samples": len(texts),
            "avg_len": round(statistics.mean(lengths), 1),
            "std_len": round(statistics.stdev(lengths) if len(lengths) > 1 else 0.0, 1),
            "md_rate": round(md_rate, 3),
            "list_rate": round(list_rate, 3),
            "avg_tokens_per_response": round(avg_tokens_per_response, 1),
        }


async def main():
    """CLI entry: `python -m verify_core.ground_truth.collector`"""
    collector = GroundTruthCollector()
    out = await collector.collect_all()
    print(f"\n✓ Baseline written: {out}")


if __name__ == "__main__":
    asyncio.run(main())
