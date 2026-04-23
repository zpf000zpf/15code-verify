"""Abstract provider interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclass
class ChatRequest:
    model: str
    messages: list[dict[str, Any]]
    system: Optional[str] = None
    temperature: float = 0.0
    max_tokens: int = 512
    tools: Optional[list[dict[str, Any]]] = None
    cache_control_prefix: bool = False      # insert cache_control on system/first user
    stream: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatResponse:
    text: str
    usage: Usage
    ttft_ms: Optional[float] = None
    total_ms: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)
    status_code: int = 200


class ChatProvider(ABC):
    """Unified provider interface. All probes code against this."""

    def __init__(self, base_url: str, api_key: str, timeout_s: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_s = timeout_s

    @abstractmethod
    async def chat(self, req: ChatRequest) -> ChatResponse:
        ...

    @abstractmethod
    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[str]:
        ...


class StreamMetrics:
    """Instrumentation for streaming responses."""
    __slots__ = ("ttft_ms", "total_ms", "token_count", "itl_samples")

    def __init__(self):
        self.ttft_ms: float | None = None
        self.total_ms: float = 0.0
        self.token_count: int = 0
        self.itl_samples: list[float] = []
