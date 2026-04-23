"""Token accounting oracle — verifies provider's usage.* numbers against
local ground-truth tokenization."""
from verify_core.tokenizers.oracle import TokenOracle, count_tokens_for_model

__all__ = ["TokenOracle", "count_tokens_for_model"]
