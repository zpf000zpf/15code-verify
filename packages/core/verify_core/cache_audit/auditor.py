"""Cache audit — protocol-aware verification of prompt-caching claims."""
from __future__ import annotations

import asyncio

from verify_core.providers.base import ChatProvider, ChatRequest
from verify_core.providers.anthropic_like import AnthropicLikeProvider
from verify_core.providers.openai_like import OpenAILikeProvider
from verify_core.report import CacheAuditResult, Finding, Severity


# Long, stable prefix. Large enough to exceed most providers' cache threshold
# (Anthropic: 1024 tokens min for Claude; OpenAI: automatic at 1024 tokens).
CACHE_SYSTEM_PROMPT = (
    "You are a highly structured technical assistant. "
    "When answering, always provide: (1) a direct answer, (2) a short "
    "justification, (3) one relevant caveat. Keep answers under 120 words. "
) * 40


class CacheAuditor:
    """Auditor that dispatches to the right strategy per protocol."""

    async def run(self, provider: ChatProvider, claimed_model: str) -> CacheAuditResult:
        if isinstance(provider, AnthropicLikeProvider):
            return await self._audit_anthropic(provider, claimed_model)
        if isinstance(provider, OpenAILikeProvider):
            return await self._audit_openai(provider, claimed_model)
        return CacheAuditResult(findings=[Finding(
            code="CACHE_PROTOCOL_UNSUPPORTED",
            severity=Severity.INFO,
            title="Cache audit not supported for this protocol",
            detail=f"Protocol {type(provider).__name__} has no cache audit implementation.",
        )])

    # ─── Anthropic: explicit cache_control + cache_creation/read metrics ────
    async def _audit_anthropic(self, provider: ChatProvider, model: str) -> CacheAuditResult:
        findings: list[Finding] = []
        result = CacheAuditResult()

        req = ChatRequest(
            model=model,
            system=CACHE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": "Say OK and nothing else."}],
            temperature=0.0,
            max_tokens=8,
            cache_control_prefix=True,
        )
        r1 = await provider.chat(req)
        if r1.status_code != 200:
            findings.append(Finding(
                code="CACHE_ERROR",
                severity=Severity.WARN,
                title="Cache probe failed",
                detail=f"First cache request returned HTTP {r1.status_code}",
            ))
            result.findings = findings
            return result

        creation = r1.usage.cache_creation_input_tokens
        result.cache_supported = creation > 0
        if not result.cache_supported:
            findings.append(Finding(
                code="CACHE_NOT_USED",
                severity=Severity.INFO,
                title="Cache creation not observed",
                detail=(
                    "Provider did not populate cache_creation_input_tokens. "
                    "Either caching is not supported, cache_control was not honored, "
                    "or the prompt was below the provider's cache threshold."
                ),
                evidence={"usage": r1.usage.__dict__},
            ))
            result.findings = findings
            return result

        await asyncio.sleep(2.0)

        r2 = await provider.chat(req)
        hit = r2.usage.cache_read_input_tokens
        result.cache_claim_matches_reality = hit > 0

        if hit == 0:
            findings.append(Finding(
                code="CACHE_NO_HIT",
                severity=Severity.WARN,
                title="Cache read not observed on identical prefix",
                detail=(
                    "Second request with identical cached prefix did not report "
                    "cache_read_input_tokens > 0. Discount may not be applied."
                ),
                evidence={"first": r1.usage.__dict__, "second": r2.usage.__dict__},
            ))
            result.estimated_overpay_pct = 90.0
        else:
            ratio = hit / max(creation, 1)
            if ratio < 0.8:
                findings.append(Finding(
                    code="CACHE_PARTIAL_HIT",
                    severity=Severity.INFO,
                    title="Cache hit is partial",
                    detail=f"cache_read/creation = {ratio:.2f}",
                ))
            result.read_discount_ok = True

        result.findings = findings
        return result

    # ─── OpenAI-compat: no explicit cache_control, detect via prefix repeat ─
    async def _audit_openai(self, provider: ChatProvider, model: str) -> CacheAuditResult:
        """OpenAI-compat: providers implement automatic caching when the
        prefix is ≥1024 tokens. Detection method: send the same long prefix
        twice with a tiny differing tail; second call should report
        `prompt_tokens_details.cached_tokens > 0` (or equivalent).
        """
        findings: list[Finding] = []
        result = CacheAuditResult()

        long_prefix = CACHE_SYSTEM_PROMPT
        req1 = ChatRequest(
            model=model,
            system=long_prefix,
            messages=[{"role": "user", "content": "Answer with the single word 'A'."}],
            temperature=0.0,
            max_tokens=4,
        )
        r1 = await provider.chat(req1)
        if r1.status_code != 200:
            findings.append(Finding(
                code="CACHE_ERROR",
                severity=Severity.WARN,
                title="Cache probe failed",
                detail=f"First cache request returned HTTP {r1.status_code}",
            ))
            result.findings = findings
            return result

        # On first hit there should be NO cached_tokens (or cached=0)
        await asyncio.sleep(2.0)

        # Same prefix, tiny tail change
        req2 = ChatRequest(
            model=model,
            system=long_prefix,
            messages=[{"role": "user", "content": "Answer with the single word 'B'."}],
            temperature=0.0,
            max_tokens=4,
        )
        r2 = await provider.chat(req2)
        if r2.status_code != 200:
            findings.append(Finding(
                code="CACHE_ERROR",
                severity=Severity.WARN,
                title="Cache probe failed on second call",
                detail=f"Second cache request returned HTTP {r2.status_code}",
            ))
            result.findings = findings
            return result

        cached = r2.usage.cache_read_input_tokens
        result.cache_supported = cached > 0
        result.cache_claim_matches_reality = cached > 0

        if cached == 0:
            findings.append(Finding(
                code="CACHE_NO_HIT_OAI",
                severity=Severity.INFO,
                title="No cached_tokens observed on repeated prefix",
                detail=(
                    "Second request with identical long prefix did not report "
                    "prompt_tokens_details.cached_tokens > 0. Either the provider "
                    "does not implement automatic caching, or the discount is not "
                    "being passed through."
                ),
                evidence={"first": r1.usage.__dict__, "second": r2.usage.__dict__},
            ))
            result.estimated_overpay_pct = 50.0  # OpenAI's discount is 0.5x, not 0.1x
        else:
            findings.append(Finding(
                code="CACHE_HIT_OAI",
                severity=Severity.OK,
                title="Automatic prompt cache observed",
                detail=(
                    f"cached_tokens={cached} on second request with identical prefix. "
                    f"Provider appears to honor OpenAI-style automatic caching."
                ),
            ))
            result.read_discount_ok = True

        result.findings = findings
        return result
