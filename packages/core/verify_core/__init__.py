"""15code Verify — core scanning engine.

Public API:
    Scanner         - main orchestrator
    ScanConfig      - scan configuration
    ScanReport      - scan result
    register_probe  - register custom probes
"""
from verify_core.config import ScanConfig, ScanDepth
from verify_core.scanner import Scanner
from verify_core.report import ScanReport
from verify_core.probes.base import Probe, ProbeResult, register_probe

__version__ = "0.1.0"

__all__ = [
    "Scanner",
    "ScanConfig",
    "ScanDepth",
    "ScanReport",
    "Probe",
    "ProbeResult",
    "register_probe",
]
