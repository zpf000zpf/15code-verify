"""Ground Truth baseline collection — builds per-model reference profiles
by calling 15code's OWN API (never user-provided keys)."""
from verify_core.ground_truth.collector import GroundTruthCollector

__all__ = ["GroundTruthCollector"]
