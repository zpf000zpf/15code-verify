"""Probe base class + registry."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, ClassVar, Optional

from verify_core.providers.base import ChatProvider


@dataclass
class ProbeResult:
    probe_id: str
    passed: bool
    # log-likelihood scores for candidate models ({"claude-opus-4-7": -1.2, "gpt-5-codex": -0.3})
    model_log_scores: dict[str, float] = field(default_factory=dict)
    # evidence / detail fields
    evidence: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    error: Optional[str] = None


class Probe(ABC):
    """A probe is a callable that runs on a provider and scores candidate models."""

    probe_id: ClassVar[str] = "unknown"
    category: ClassVar[str] = "authenticity"   # authenticity | stylometry | capability
    weight: ClassVar[float] = 1.0

    @abstractmethod
    async def run(self, provider: ChatProvider, claimed_model: str) -> ProbeResult:
        ...


class ProbeRegistry:
    _probes: dict[str, type[Probe]] = {}

    @classmethod
    def register(cls, probe_cls: type[Probe]) -> type[Probe]:
        cls._probes[probe_cls.probe_id] = probe_cls
        return probe_cls

    @classmethod
    def all(cls) -> list[type[Probe]]:
        return list(cls._probes.values())

    @classmethod
    def by_category(cls, category: str) -> list[type[Probe]]:
        return [p for p in cls._probes.values() if p.category == category]

    @classmethod
    def get(cls, probe_id: str) -> Optional[type[Probe]]:
        return cls._probes.get(probe_id)


def register_probe(cls: type[Probe]) -> type[Probe]:
    """Decorator to self-register a probe class."""
    return ProbeRegistry.register(cls)
