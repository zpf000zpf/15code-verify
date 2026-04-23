"""OpenAI-compatible provider (/v1/chat/completions)."""
from __future__ import annotations

import time
from typing import AsyncIterator

import httpx
import orjson

from verify_core.providers.base import ChatProvider, ChatRequest, ChatResponse, Usage


class OpenAILikeProvider(ChatProvider):
    async def chat(self, req: ChatRequest) -> ChatResponse:
        payload = self._build_payload(req, stream=False)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/chat/completions"
        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            resp = await client.post(url, headers=headers, content=orjson.dumps(payload))
            total_ms = (time.perf_counter() - t0) * 1000.0
            data = resp.json() if resp.content else {}

        text = ""
        usage = Usage()
        if resp.status_code == 200:
            try:
                text = data["choices"][0]["message"]["content"] or ""
            except (KeyError, IndexError, TypeError):
                text = ""
            u = data.get("usage") or {}
            usage = Usage(
                input_tokens=int(u.get("prompt_tokens") or 0),
                output_tokens=int(u.get("completion_tokens") or 0),
                cache_creation_input_tokens=int(u.get("cache_creation_input_tokens") or 0),
                cache_read_input_tokens=int(
                    u.get("prompt_tokens_details", {}).get("cached_tokens")
                    or u.get("cache_read_input_tokens")
                    or 0
                ),
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
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        url = f"{self.base_url}/chat/completions"
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            async with client.stream("POST", url, headers=headers, content=orjson.dumps(payload)) as resp:
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = orjson.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {}).get("content") or ""
                        if delta:
                            yield delta
                    except Exception:
                        continue

    def _build_payload(self, req: ChatRequest, stream: bool) -> dict:
        messages = list(req.messages)
        if req.system:
            messages = [{"role": "system", "content": req.system}] + messages
        payload = {
            "model": req.model,
            "messages": messages,
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
            "stream": stream,
        }
        if req.tools:
            payload["tools"] = req.tools
        if req.extra:
            payload.update(req.extra)
        return payload
