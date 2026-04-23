"""Smoke tests — verify the package imports and basic flows work
without needing a real LLM API."""
from __future__ import annotations

import asyncio

from verify_core import ScanConfig, ScanDepth, Scanner
from verify_core.config import ProviderProtocol
from verify_core.probes.base import ProbeRegistry
from verify_core.report import ScanReport
from verify_core.scoring import ScoringEngine
from verify_core.tokenizers import TokenOracle


def test_imports():
    assert Scanner
    assert ScanReport
    assert ScanConfig


def test_probe_registry_has_builtins():
    probes = ProbeRegistry.all()
    probe_ids = {p.probe_id for p in probes}
    assert "tokenizer_fingerprint_v1" in probe_ids
    assert "self_identification_v1" in probe_ids
    assert "stylometry_v1" in probe_ids
    assert "capability_diff_v1" in probe_ids
    # P1 new probes
    assert "refusal_pattern_v1" in probe_ids
    assert "knowledge_cutoff_v1" in probe_ids
    assert "latency_fingerprint_v1" in probe_ids
    assert len(probe_ids) >= 7


def test_token_oracle_basic():
    oracle = TokenOracle("gpt-5")
    n = oracle.count("hello world")
    assert n > 0


def test_scoring_engine_handles_empty_probes():
    engine = ScoringEngine()
    result = engine.fuse_authenticity([], claimed_model="claude-opus-4-7")
    assert result.evidence_count == 0
    assert result.confidence_is_claimed == 0.0


def test_config_requires_tos_fields():
    # must use a supported 15code model
    cfg = ScanConfig(
        base_url="https://example.com/v1",
        api_key="sk-test",
        claimed_model="claude-opus-4-7",
    )
    # v1.1: public-by-default. tos still defaults False (explicit accept required).
    assert cfg.publish_to_leaderboard is True
    assert cfg.tos_accepted is False
    assert cfg.methodology_version == "v1.0"


def test_config_rejects_unsupported_model():
    import pytest
    with pytest.raises(Exception):
        ScanConfig(
            base_url="https://example.com/v1",
            api_key="sk-test",
            claimed_model="gemini-2.5-pro",   # not offered by 15code
        )


def test_catalog_has_8_models():
    from verify_core.catalog import get_catalog
    cat = get_catalog()
    assert len(cat.all()) == 8
    ids = cat.all_ids()
    assert "claude-opus-4-7" in ids
    assert "gpt-5.4" in ids
    assert "glm-5.1" in ids
    # these were removed per product decision
    assert "codex" not in ids
    assert "gpt-5.3-codex-spark" not in ids


def test_trust_score_bounds():
    engine = ScoringEngine()
    from verify_core.report import (
        AuthenticityResult, BillingAuditResult, CacheAuditResult, QoSResult,
    )
    a = AuthenticityResult(claimed_model="x", confidence_is_claimed=0.0)
    b = BillingAuditResult(input_token_deviation_pct=-500, output_token_deviation_pct=500)
    c = CacheAuditResult(cache_claim_matches_reality=False)
    q = QoSResult(error_rate=1.0, quantization_suspected=True)
    score, verdict = engine.compute_trust_score(a, b, c, q)
    assert 0 <= score <= 100
    assert verdict in {
        "consistent_with_claim",
        "partial_consistency",
        "notable_deviations_observed",
        "significant_deviations_observed",
    }
