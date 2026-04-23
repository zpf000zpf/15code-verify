"""Security utilities — log redaction, key masking."""
from __future__ import annotations

import logging
import re

# Recognize typical LLM provider key patterns
KEY_PATTERNS = [
    re.compile(r"(sk-[A-Za-z0-9_\-]{10,})"),       # OpenAI / generic
    re.compile(r"(sk-ant-[A-Za-z0-9_\-]{10,})"),    # Anthropic
    re.compile(r"(ya29\.[A-Za-z0-9_\-]{20,})"),     # Google
    re.compile(r"(AIza[A-Za-z0-9_\-]{20,})"),       # Google API key
    re.compile(r"\"api_key\"\s*:\s*\"([^\"]+)\""),
    re.compile(r"Bearer\s+([A-Za-z0-9_\-\.]{20,})"),
]


def mask_secret(s: str) -> str:
    """Mask a single key-like token. sk-abcdefgh1234 → sk-abcd****1234"""
    if not s or len(s) < 10:
        return "***"
    # keep a reasonable prefix (family hint) + last 4
    head_len = 4
    prefix_m = re.match(r"^(sk-ant-|sk-|ya29\.|AIza)", s)
    if prefix_m:
        head_len = len(prefix_m.group(1)) + 4
    return s[:head_len] + "****" + s[-4:]


def redact(text: str) -> str:
    """Redact all known secret patterns in a free-text string."""
    if not text:
        return text
    for pat in KEY_PATTERNS:
        text = pat.sub(lambda m: mask_secret(m.group(1)), text)
    return text


class RedactingFilter(logging.Filter):
    """logging filter that redacts secrets from all log records."""
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = redact(record.msg)
            if record.args:
                record.args = tuple(
                    redact(a) if isinstance(a, str) else a for a in record.args
                )
        except Exception:
            pass
        return True


def install_log_redaction() -> None:
    """Attach redaction filter to the root logger and common noisy ones."""
    f = RedactingFilter()
    logging.getLogger().addFilter(f)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi", "httpx"):
        logging.getLogger(name).addFilter(f)
