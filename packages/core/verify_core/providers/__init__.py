"""Provider adapters — unified interface over OpenAI / Anthropic / Gemini protocols."""
from verify_core.providers.base import ChatProvider, ChatRequest, ChatResponse, Usage
from verify_core.providers.openai_like import OpenAILikeProvider
from verify_core.providers.anthropic_like import AnthropicLikeProvider

__all__ = [
    "ChatProvider",
    "ChatRequest",
    "ChatResponse",
    "Usage",
    "OpenAILikeProvider",
    "AnthropicLikeProvider",
    "build_provider",
]


def build_provider(protocol: str, base_url: str, api_key: str, timeout_s: float = 60.0) -> ChatProvider:
    if protocol == "openai":
        return OpenAILikeProvider(base_url=base_url, api_key=api_key, timeout_s=timeout_s)
    if protocol == "anthropic":
        return AnthropicLikeProvider(base_url=base_url, api_key=api_key, timeout_s=timeout_s)
    raise ValueError(f"Unsupported protocol: {protocol}")
