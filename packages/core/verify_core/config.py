"""Scan configuration."""
from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, SecretStr, field_validator


class ScanDepth(str, Enum):
    QUICK = "quick"        # ~10 probes, ~30s
    STANDARD = "standard"  # ~50 probes, ~3min
    DEEP = "deep"          # ~200 probes, ~10min, with A/B compare


class ProviderProtocol(str, Enum):
    OPENAI_COMPATIBLE = "openai"    # /v1/chat/completions
    ANTHROPIC = "anthropic"         # /v1/messages
    GEMINI = "gemini"


class ScanConfig(BaseModel):
    # Target under test
    base_url: str = Field(..., description="Third-party API base URL")
    api_key: SecretStr = Field(..., description="Third-party API key")
    claimed_model: str = Field(..., description="Model name the provider claims to serve")
    protocol: ProviderProtocol = ProviderProtocol.OPENAI_COMPATIBLE

    # Scan parameters
    depth: ScanDepth = ScanDepth.STANDARD
    enable_authenticity: bool = True
    enable_billing_audit: bool = True
    enable_cache_audit: bool = True
    enable_qos: bool = True
    enable_privacy: bool = False   # off by default; requires canary infra

    # Execution
    concurrency: int = 4
    timeout_s: float = 60.0
    max_retries: int = 2

    # A/B comparison (deep mode)
    enable_ab_compare: bool = False
    reference_base_url: Optional[str] = None
    reference_api_key: Optional[SecretStr] = None

    # Tagging
    scan_id: Optional[str] = None
    user_label: Optional[str] = None

    # ── Leaderboard / legal ────────────────────────────────────────
    # Default-public product decision (v1.1):
    # scans contribute anonymous aggregates to the public leaderboard
    # unless explicitly set False by the caller. The web form does not
    # show a checkbox; the ToS discloses this behavior.
    publish_to_leaderboard: bool = True
    # Vendor display name (optional; host of base_url used if omitted)
    vendor_display_name: Optional[str] = None
    # User accepts the Terms of Service (docs/TERMS_OF_SERVICE.md)
    tos_accepted: bool = False
    # Methodology version applied to this scan (for audit trail)
    methodology_version: str = "v1.0"

    @field_validator("claimed_model")
    @classmethod
    def _validate_claimed_model(cls, v: str) -> str:
        """Only models offered by 15code are accepted.

        This is a deliberate scope limitation:
        - We serve Ground-Truth baselines only for models 15code itself offers.
        - It keeps the identification accuracy defensible.
        - It aligns with '只检测15code提供服务的模型' product decision.
        """
        from verify_core.catalog import get_catalog
        cat = get_catalog()
        if not cat.has(v):
            supported = ", ".join(cat.all_ids())
            raise ValueError(
                f"Model '{v}' is not in the 15code supported-models catalog. "
                f"Supported models: [{supported}]. "
                f"To request adding a new model, see: "
                f"https://verify.15code.com/docs/add-model"
            )
        return v

    @property
    def probe_budget(self) -> int:
        return {ScanDepth.QUICK: 10, ScanDepth.STANDARD: 50, ScanDepth.DEEP: 200}[self.depth]
