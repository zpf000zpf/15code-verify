"""TokenOracle — local, authoritative token counter.

Uses:
- tiktoken for OpenAI models (cl100k_base / o200k_base)
- anthropic's count_tokens endpoint OR SentencePiece fallback for Claude
- naive len() fallback for unknown models (clearly marked)

Only the deviation of *provider-reported* vs *local-counted* is used for audit.
"""
from __future__ import annotations

from typing import Optional

try:
    import tiktoken
except ImportError:
    tiktoken = None  # type: ignore


# Model -> tokenizer mapping
_OPENAI_O200K = {"gpt-4o", "gpt-4o-mini", "gpt-5", "gpt-5-mini", "gpt-5-codex",
                 "o1", "o1-mini", "o3", "o3-mini", "o4", "o4-mini"}
_OPENAI_CL100K = {"gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "text-embedding-3-large",
                  "text-embedding-3-small"}


def _resolve_encoding_name(model: str) -> Optional[str]:
    m = model.lower()
    for n in _OPENAI_O200K:
        if m.startswith(n):
            return "o200k_base"
    for n in _OPENAI_CL100K:
        if m.startswith(n):
            return "cl100k_base"
    if m.startswith(("claude", "anthropic")):
        # Anthropic: use official counting endpoint when available;
        # here we approximate with cl100k as ballpark (flagged as estimate).
        return "cl100k_base"
    return None


class TokenOracle:
    """Counts tokens locally for common models."""

    def __init__(self, model: str) -> None:
        self.model = model
        self._enc_name = _resolve_encoding_name(model)
        self._enc = None
        if self._enc_name and tiktoken is not None:
            try:
                self._enc = tiktoken.get_encoding(self._enc_name)
            except Exception:
                self._enc = None

    @property
    def is_authoritative(self) -> bool:
        """True if local count is exact. False = estimate, audit margin wider."""
        m = self.model.lower()
        if not self._enc:
            return False
        if m.startswith(("gpt", "o1", "o3", "o4")):
            return True
        return False

    @property
    def has_remote_authority(self) -> bool:
        """True if we can use an authoritative remote counter (Anthropic)."""
        from verify_core.tokenizers.anthropic_counter import AnthropicOfficialCounter
        m = self.model.lower()
        if m.startswith(("claude", "anthropic")):
            return AnthropicOfficialCounter().available
        return False

    def count(self, text: str) -> int:
        if self._enc:
            try:
                return len(self._enc.encode(text))
            except Exception:
                pass
        return max(1, len(text) // 3)

    def count_messages(self, messages: list[dict], system: Optional[str] = None) -> int:
        total = 0
        if system:
            total += self.count(system) + 4
        for m in messages:
            content = m.get("content", "")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and "text" in part:
                        total += self.count(part["text"])
            elif isinstance(content, str):
                total += self.count(content)
            total += 4
        return total + 2

    async def count_messages_authoritative(
        self, messages: list[dict], system: Optional[str] = None,
    ) -> tuple[int, bool]:
        """Best-effort exact count. Returns (count, is_exact).

        - GPT family → uses tiktoken (exact)
        - Claude family → tries Anthropic count_tokens endpoint if key set
                          falls back to tiktoken approx if not available
        """
        if self.is_authoritative:
            return self.count_messages(messages, system), True

        m = self.model.lower()
        if m.startswith(("claude", "anthropic")):
            from verify_core.tokenizers.anthropic_counter import AnthropicOfficialCounter
            counter = AnthropicOfficialCounter()
            if counter.available:
                # Try with sanitized message list for Anthropic API format
                cleaned = [
                    {"role": msg.get("role", "user"), "content": msg.get("content", "")}
                    for msg in messages if msg.get("role") in ("user", "assistant")
                ]
                n = await counter.count(self.model, cleaned, system)
                if n is not None:
                    return n, True

        return self.count_messages(messages, system), False


def count_tokens_for_model(model: str, text: str) -> tuple[int, bool]:
    """Convenience function. Returns (count, is_authoritative)."""
    o = TokenOracle(model)
    return o.count(text), o.is_authoritative
