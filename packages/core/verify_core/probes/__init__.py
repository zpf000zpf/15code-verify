"""Probes — pluggable detectors for authenticity / stylometry / capability."""
from verify_core.probes.base import Probe, ProbeResult, ProbeRegistry, register_probe

# Import built-in probes so they self-register
from verify_core.probes import tokenizer_fingerprint  # noqa: F401
from verify_core.probes import self_identification    # noqa: F401
from verify_core.probes import stylometry             # noqa: F401
from verify_core.probes import capability_diff        # noqa: F401
from verify_core.probes import refusal_pattern        # noqa: F401
from verify_core.probes import knowledge_cutoff       # noqa: F401
from verify_core.probes import latency_fingerprint    # noqa: F401

__all__ = ["Probe", "ProbeResult", "ProbeRegistry", "register_probe"]
