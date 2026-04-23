"""15code supported-model catalog.

Single source of truth for which models the verify tool can audit.
Loaded from data/15code_catalog/models.yaml at import time.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:  # graceful fallback
    yaml = None  # type: ignore


@dataclass
class ModelInfo:
    id: str
    display_name: str
    family: str                   # anthropic | openai | zhipu
    protocol: str                 # anthropic | openai
    tier: str                     # flagship | mid | fast
    input_price_per_mtok: float
    output_price_per_mtok: float
    cache_read_per_mtok: Optional[float] = None
    cache_creation_per_mtok: Optional[float] = None
    supports_cache: bool = False


# Hard-coded fallback — used when yaml is unavailable or file missing.
# Kept in sync with data/15code_catalog/models.yaml
_FALLBACK_MODELS = [
    ModelInfo("claude-haiku-4-5-20251001", "Claude Haiku 4.5",  "anthropic", "anthropic", "fast",     1.30,  6.50, 0.13, 1.625, True),
    ModelInfo("claude-opus-4-6",           "Claude Opus 4.6",   "anthropic", "anthropic", "flagship", 6.50, 32.50, 0.65, 8.125, True),
    ModelInfo("claude-opus-4-7",           "Claude Opus 4.7",   "anthropic", "anthropic", "flagship", 6.50, 32.50, 0.65, 8.125, True),
    ModelInfo("claude-sonnet-4-6",         "Claude Sonnet 4.6", "anthropic", "anthropic", "mid",      3.90, 19.50, 0.39, 4.875, True),
    ModelInfo("gpt-5.3-codex",             "GPT-5.3 Codex",     "openai",    "openai",    "mid",      1.75, 14.00, 0.175, None, False),
    ModelInfo("gpt-5.4",                   "GPT-5.4",           "openai",    "openai",    "flagship", 2.50, 15.00, 0.25,  None, False),
    ModelInfo("glm-5",                     "GLM-5",             "zhipu",     "openai",    "mid",      0.48,  1.50, 0.12,  None, True),
    ModelInfo("glm-5.1",                   "GLM-5.1",           "zhipu",     "openai",    "flagship", 0.80,  2.40, 0.36,  None, True),
]


def _default_yaml_path() -> Path:
    # Try a few locations: env var, repo root, installed package dir.
    env = os.getenv("VERIFY_CATALOG_PATH")
    if env and Path(env).is_file():
        return Path(env)
    here = Path(__file__).resolve()
    # repo-relative (dev mode):  …/packages/core/verify_core/catalog.py → repo root is 3 up
    candidates = [
        here.parent.parent.parent.parent / "data" / "15code_catalog" / "models.yaml",
        Path.cwd() / "data" / "15code_catalog" / "models.yaml",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return candidates[0]


class ModelCatalog:
    """Loads and validates the 15code supported-models list."""

    def __init__(self, models: list[ModelInfo]):
        self._models: dict[str, ModelInfo] = {m.id: m for m in models}

    @classmethod
    def load(cls) -> "ModelCatalog":
        path = _default_yaml_path()
        if yaml is not None and path.is_file():
            with path.open("r", encoding="utf-8") as f:
                doc = yaml.safe_load(f) or {}
            models = []
            for m in doc.get("models", []):
                models.append(ModelInfo(
                    id=m["id"],
                    display_name=m["display_name"],
                    family=m["family"],
                    protocol=m["protocol"],
                    tier=m.get("tier", "mid"),
                    input_price_per_mtok=float(m["input_price_per_mtok"]),
                    output_price_per_mtok=float(m["output_price_per_mtok"]),
                    cache_read_per_mtok=m.get("cache_read_per_mtok"),
                    cache_creation_per_mtok=m.get("cache_creation_per_mtok"),
                    supports_cache=bool(m.get("supports_cache", False)),
                ))
            return cls(models)
        return cls(list(_FALLBACK_MODELS))

    def get(self, model_id: str) -> Optional[ModelInfo]:
        return self._models.get(model_id)

    def has(self, model_id: str) -> bool:
        return model_id in self._models

    def all_ids(self) -> list[str]:
        return list(self._models.keys())

    def all(self) -> list[ModelInfo]:
        return list(self._models.values())

    def by_family(self, family: str) -> list[ModelInfo]:
        return [m for m in self._models.values() if m.family == family]


# singleton (lazy)
_catalog: Optional[ModelCatalog] = None


def get_catalog() -> ModelCatalog:
    global _catalog
    if _catalog is None:
        _catalog = ModelCatalog.load()
    return _catalog
