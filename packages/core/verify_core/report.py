"""Scan report data structures."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    OK = "ok"
    INFO = "info"
    WARN = "warn"
    CRITICAL = "critical"


class Finding(BaseModel):
    """A single observation from a probe / auditor."""
    code: str
    severity: Severity
    title: str
    detail: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class AuthenticityResult(BaseModel):
    claimed_model: str
    confidence_is_claimed: float = Field(ge=0.0, le=1.0)
    likely_model: Optional[str] = None
    likely_model_confidence: float = 0.0
    model_probabilities: dict[str, float] = Field(default_factory=dict)
    evidence_count: int = 0
    findings: list[Finding] = Field(default_factory=list)


class BillingAuditResult(BaseModel):
    input_token_deviation_pct: float = 0.0
    output_token_deviation_pct: float = 0.0
    sample_count: int = 0
    systematic_inflation: bool = False
    findings: list[Finding] = Field(default_factory=list)


class CacheAuditResult(BaseModel):
    cache_supported: bool = False
    cache_claim_matches_reality: bool = True
    creation_discount_ok: Optional[bool] = None
    read_discount_ok: Optional[bool] = None
    ttl_behavior_ok: Optional[bool] = None
    estimated_overpay_pct: float = 0.0
    findings: list[Finding] = Field(default_factory=list)


class QoSResult(BaseModel):
    ttft_ms_p50: float = 0.0
    ttft_ms_p95: float = 0.0
    itl_ms_p50: float = 0.0
    error_rate: float = 0.0
    capability_score: Optional[float] = None
    quantization_suspected: bool = False
    findings: list[Finding] = Field(default_factory=list)


class PrivacyResult(BaseModel):
    canary_leaked: bool = False
    unexpected_hops: list[str] = Field(default_factory=list)
    tls_ok: bool = True
    findings: list[Finding] = Field(default_factory=list)


class ScanReport(BaseModel):
    scan_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    claimed_model: str
    base_url: str

    # NOTE: trust_score is a TECHNICAL INDICATOR, not a legal evaluation.
    # See docs/LEADERBOARD_POLICY.md for the interpretation guidance.
    trust_score: int = Field(0, ge=0, le=100)
    # verdict uses NEUTRAL, technical language only.
    # e.g. "consistent_with_claim", "deviates_from_claim", "insufficient_data"
    # NEVER: "fraud", "fake", "cheating"
    verdict: str = "unknown"

    authenticity: Optional[AuthenticityResult] = None
    billing_audit: Optional[BillingAuditResult] = None
    cache_audit: Optional[CacheAuditResult] = None
    qos: Optional[QoSResult] = None
    privacy: Optional[PrivacyResult] = None

    duration_s: float = 0.0
    probes_executed: int = 0
    tokens_consumed_estimate: int = 0

    # ── Leaderboard / audit trail ───────────────────────────────────
    methodology_version: str = "v1.0"
    published_to_leaderboard: bool = False
    disclaimer: str = Field(
        default=(
            "本报告反映特定时间点的技术指标观测，不构成对服务商的法律评价"
            "或商业决策建议。方法论见 docs/PROBE_DESIGN.md，"
            "榜单政策见 docs/LEADERBOARD_POLICY.md。"
        ),
        description="Legal-safe disclaimer embedded in every report",
    )

    # ── Branding / attribution (15code promo) ────────────────────────
    generated_by: str = "15code Verify"
    generator_url: str = "https://verify.15code.com"
    promo: dict[str, str] = Field(
        default_factory=lambda: {
            "message": "这个免费工具由 15code 出品 · 想用一个信得过的 LLM 服务？试试 15code。",
            "url": "https://15code.com",
        },
        description="Rotating promotional message + link to 15code",
    )

    def summary(self) -> str:
        lines = [
            f"Scan {self.scan_id}",
            f"  Target    : {self.base_url}",
            f"  Claimed   : {self.claimed_model}",
            f"  Trust     : {self.trust_score}/100  ({self.verdict})",
        ]
        if self.authenticity:
            ll = self.authenticity.likely_model or "?"
            lines.append(f"  Real Model: {ll} (p={self.authenticity.likely_model_confidence:.0%})")
        if self.billing_audit:
            lines.append(
                f"  Billing   : input {self.billing_audit.input_token_deviation_pct:+.1f}%  "
                f"output {self.billing_audit.output_token_deviation_pct:+.1f}%"
            )
        if self.cache_audit:
            lines.append(f"  Cache     : supported={self.cache_audit.cache_supported}")
        if self.qos:
            lines.append(f"  TTFT p50  : {self.qos.ttft_ms_p50:.0f}ms")
        return "\n".join(lines)
