"""Authoritative Claude token counter using Anthropic's count_tokens endpoint.

This avoids the cl100k approximation (±10% noise) used previously.
Requires either:
  - a direct Anthropic API key (best), OR
  - cached counts (we only need a ratio, not exact match)

Only 15code's OWN ground-truth key is used here — never the user-under-test key.
Env: ANTHROPIC_API_KEY (only set on the 15code server)
"""
from __future__ import annotations

import os
from typing import Optional

import httpx

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages/count_tokens"


class AnthropicOfficialCounter:
    """Authoritative counter for Claude models via the public count_tokens endpoint."""

    def __init__(self, api_key: Optional[str] = None, timeout_s: float = 10.0):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.timeout_s = timeout_s

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    async def count(self, model: str, messages: list[dict], system: Optional[str] = None) -> Optional[int]:
        if not self.available:
            return None
        payload: dict = {"model": model, "messages": messages}
        if system:
            payload["system"] = system
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(
                    ANTHROPIC_URL,
                    json=payload,
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                )
                if resp.status_code != 200:
                    return None
                data = resp.json()
                return int(data.get("input_tokens", 0)) or None
        except Exception:
            return None
