"""Anthropic-compatible provider (/v1/messages)."""
from __future__ import annotations

import time
from typing import AsyncIterator

import httpx
import orjson

from verify_core.providers.base import ChatProvider, ChatRequest, ChatResponse, Usage


class AnthropicLikeProvider(ChatProvider):
    async def chat(self, req: ChatRequest) -> ChatResponse:
        payload = self._build_payload(req, stream=False)
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        url = f"{self.base_url}/messages"
        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            resp = await client.post(url, headers=headers, content=orjson.dumps(payload))
            total_ms = (time.perf_counter() - t0) * 1000.0
            data = resp.json() if resp.content else {}

        text = ""
        usage = Usage()
        if resp.status_code == 200:
            # content: [{type:"text", text:"..."}, ...]
            parts = data.get("content") or []
            text = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
            u = data.get("usage") or {}
            usage = Usage(
                input_tokens=int(u.get("input_tokens") or 0),
                output_tokens=int(u.get("output_tokens") or 0),
                cache_creation_input_tokens=int(u.get("cache_creation_input_tokens") or 0),
                cache_read_input_tokens=int(u.get("cache_read_input_tokens") or 0),
            )
        return ChatResponse(
            text=text,
            usage=usage,
            total_ms=total_ms,
            raw=data,
            status_code=resp.status_code,
        )

    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[str]:
        payload = self._build_payload(req, stream=True)
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "accept": "text/event-stream",
        }
        url = f"{self.base_url}/messages"
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            async with client.stream("POST", url, headers=headers, content=orjson.dumps(payload)) as resp:
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    try:
                        chunk = orjson.loads(data_str)
                    except Exception:
                        continue
                    if chunk.get("type") == "content_block_delta":
                        delta = chunk.get("delta", {}).get("text") or ""
                        if delta:
                            yield delta
                    elif chunk.get("type") == "message_stop":
                        break

    def _build_payload(self, req: ChatRequest, stream: bool) -> dict:
        payload = {
            "model": req.model,
            "messages": req.messages,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "stream": stream,
        }
        if req.system:
            if req.cache_control_prefix:
                payload["system"] = [
                    {"type": "text", "text": req.system, "cache_control": {"type": "ephemeral"}}
                ]
            else:
                payload["system"] = req.system
        if req.tools:
            payload["tools"] = req.tools
        if req.extra:
            payload.update(req.extra)
        return payload
