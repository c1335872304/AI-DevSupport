from __future__ import annotations

import re
from typing import Any

_REDACTED = "[REDACTED]"
_SENSITIVE_FIELD = re.compile(
    r"(?:password|passwd|secret|token|api[_ -]?key|authorization|bearer|credential|"
    r"private[_ -]?key|access[_ -]?token|refresh[_ -]?token)",
    re.IGNORECASE,
)
_ENV_EXPRESSION = (
    r"(?:os\.environ\[(?:\"[A-Z_][A-Z0-9_]*\"|'[A-Z_][A-Z0-9_]*')\]|"
    r"os\.getenv\((?:\"[A-Z_][A-Z0-9_]*\"|'[A-Z_][A-Z0-9_]*')\)|"
    r"process\.env\.[A-Z_][A-Z0-9_]*)"
)
_KEY_VALUE = re.compile(
    r"((?:api[_ -]?key|access[_ -]?token|refresh[_ -]?token|password|passwd|secret|"
    r"authorization|bearer)\s*[:=]\s*[\"']?)(" + _ENV_EXPRESSION + r"|[^\s,;\"']+)",
    re.IGNORECASE,
)
_BEARER = re.compile(r"(\bBearer\s+[\x22']?)[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
_OPENAI_STYLE_KEY = re.compile(r"\b(?:sk|ak|rk)-[A-Za-z0-9][A-Za-z0-9_-]{7,}\b", re.IGNORECASE)
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")


def _replace_value(match: re.Match[str]) -> str:
    if match.group(1).lstrip().lower().startswith("authorization") and match.group(2).lower() == "bearer":
        # The scheme is public syntax. The credential after it is masked separately.
        return match.group(0)
    # An environment lookup in a documentation example is code, not the value
    # of that variable. Never evaluate it; literal credentials still get masked.
    if not match.group(1).endswith(("'", '"')) and re.fullmatch(_ENV_EXPRESSION, match.group(2)):
        return match.group(0)
    return f"{match.group(1)}{_REDACTED}"


def redact_text(value: str | None) -> str:
    """Remove credentials from logs, websocket diagnostics and persisted traces."""
    text = str(value or "")
    text = _BEARER.sub(lambda match: f"{match.group(1)}{_REDACTED}", text)
    text = _KEY_VALUE.sub(_replace_value, text)
    text = _OPENAI_STYLE_KEY.sub(_REDACTED, text)
    return _JWT.sub(_REDACTED, text)


def is_sensitive_field(name: object) -> bool:
    normalized = str(name or "").strip().lower().replace("-", "_").replace(" ", "_")
    # Identifiers such as api_key_id and request_id are diagnostic metadata, not
    # credentials. They remain visible so an operator can investigate a request.
    if normalized.endswith("_id") or normalized in {"id", "key_id"}:
        return False
    return bool(_SENSITIVE_FIELD.search(normalized))


def redact_data(value: Any, field_name: object = None) -> Any:
    """Recursively redact credential-like mapping fields and string values."""
    if is_sensitive_field(field_name):
        return _REDACTED
    if isinstance(value, dict):
        return {str(key): redact_data(item, key) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_data(item) for item in value]
    if isinstance(value, tuple):
        return [redact_data(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value
