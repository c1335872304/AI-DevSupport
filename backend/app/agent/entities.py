from __future__ import annotations

import re
from typing import Any


# These are deliberately small, high-precision patterns. The LLM can resolve
# references such as “上面那个请求”, while these patterns make sure IDs and
# error codes are not lost when the model omits them from its JSON response.
ENTITY_KEYS = (
    "request_id",
    "error_code",
    "http_status",
    "endpoint",
    "app_id",
    "api_key_id",
    "month",
    "webhook_event_id",
    "invoice_id",
    "ticket_id",
    "order_id",
    "transaction_id",
)

_ENTITY_RE: dict[str, re.Pattern[str]] = {
    "request_id": re.compile(r"\b(?:req_[A-Za-z0-9][A-Za-z0-9_-]*|request[_ -]?id\s*[:=：]?\s*[A-Za-z0-9][A-Za-z0-9_-]*)\b", re.I),
    "error_code": re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b"),
    # Do not use ``\b`` here: in Python, Chinese characters are word
    # characters, so ``返回401`` would otherwise fail the boundary check.
    "http_status": re.compile(r"(?<!\d)[1-5]\d{2}(?!\d)"),
    "endpoint": re.compile(r"/v\d+(?:/[A-Za-z0-9._~-]+)+"),
    "app_id": re.compile(r"\b(?:app_[A-Za-z0-9][A-Za-z0-9_-]*|app[_ -]?id\s*[:=：]?\s*[A-Za-z0-9][A-Za-z0-9_-]*)\b", re.I),
    "api_key_id": re.compile(r"\b(?:key_[A-Za-z0-9][A-Za-z0-9_-]*|api[_ -]?key[_ -]?id\s*[:=：]?\s*[A-Za-z0-9][A-Za-z0-9_-]*)\b", re.I),
    "month": re.compile(r"\b20\d{2}-(?:0[1-9]|1[0-2])\b"),
    "webhook_event_id": re.compile(r"\b(?:evt_[A-Za-z0-9][A-Za-z0-9_-]*|webhook[_ -]?event[_ -]?id\s*[:=：]?\s*[A-Za-z0-9][A-Za-z0-9_-]*)\b", re.I),
    "invoice_id": re.compile(r"\b(?:inv_[A-Za-z0-9][A-Za-z0-9_-]*|invoice[_ -]?id\s*[:=：]?\s*[A-Za-z0-9][A-Za-z0-9_-]*)\b", re.I),
    "ticket_id": re.compile(r"\b(?:ticket_[A-Za-z0-9][A-Za-z0-9_-]*|ticket[_ -]?id\s*[:=：]?\s*[A-Za-z0-9][A-Za-z0-9_-]*)\b", re.I),
    "order_id": re.compile(r"\b(?:order_[A-Za-z0-9][A-Za-z0-9_-]*|订单号\s*[:：]?\s*[A-Za-z0-9][A-Za-z0-9_-]*)\b", re.I),
    "transaction_id": re.compile(r"\b(?:txn_[A-Za-z0-9][A-Za-z0-9_-]*|transaction[_ -]?id\s*[:=：]?\s*[A-Za-z0-9][A-Za-z0-9_-]*)\b", re.I),
}


def _clean_value(key: str, value: Any) -> str:
    value = str(value or "").strip().strip("`'\"，。；;：:")
    if not value or len(value) > 255:
        return ""
    if key == "http_status":
        return value if re.fullmatch(r"[1-5]\d{2}", value) else ""
    if key == "month":
        return value if re.fullmatch(r"20\d{2}-(?:0[1-9]|1[0-2])", value) else ""
    return value


def normalize_entities(raw: dict[str, Any] | None) -> dict[str, str]:
    """Keep only known, compact entity fields returned by the router LLM."""
    if not isinstance(raw, dict):
        return {}
    result: dict[str, str] = {}
    for key in ENTITY_KEYS:
        value = _clean_value(key, raw.get(key))
        if value:
            result[key] = value
    return result


def extract_entities(text: str) -> dict[str, str]:
    """High-precision local fallback for entities with recognizable formats."""
    found: dict[str, str] = {}
    for key, pattern in _ENTITY_RE.items():
        match = pattern.search(text or "")
        if not match:
            continue
        value = match.group(0)
        # For labelled forms, keep the value after the label rather than the
        # whole phrase. req_demo_401/app_demo already have the desired form.
        if key in {"request_id", "app_id", "api_key_id", "webhook_event_id", "invoice_id", "ticket_id", "order_id", "transaction_id"}:
            value = re.split(r"[:=：\s]+", value, maxsplit=1)[-1]
        value = _clean_value(key, value)
        if value:
            found[key] = value
    return found


def history_entities(history: list[dict] | None) -> dict[str, str]:
    """Extract from user turns only, avoiding assistant-generated guesses."""
    found: dict[str, str] = {}
    for item in history or []:
        if item.get("role") == "user":
            found.update(extract_entities(str(item.get("content") or "")))
    return found


def looks_like_follow_up(question: str, history: list[dict] | None = None) -> bool:
    if not history:
        return False
    normalized = (question or "").strip()
    markers = ("这个", "那个", "它", "刚才", "上面", "前面", "为什么", "那", "所以", "继续", "呢", "怎么办")
    return len(normalized) <= 80 or any(marker in normalized for marker in markers)


def resolve_entities(
    question: str,
    history: list[dict] | None,
    model_entities: dict[str, Any] | None = None,
    remembered_entities: dict[str, Any] | None = None,
    follow_up: bool | None = None,
) -> tuple[dict[str, str], dict[str, str]]:
    """Merge current entities with the original version's historical memory.

    Current values always win. Historical values are used for a follow-up; the
    memory is still retained by the caller for a later follow-up after a topic
    switch. Sources are exposed for trace/debugging and never contain secrets.
    """
    current = extract_entities(question)
    current.update(normalize_entities(model_entities))
    follow_up = looks_like_follow_up(question, history) if follow_up is None else follow_up
    previous = normalize_entities(remembered_entities)
    previous.update(history_entities(history))
    resolved = dict(previous) if follow_up else {}
    resolved.update(current)
    sources = {key: "current" for key in current}
    if follow_up:
        for key in resolved:
            sources.setdefault(key, "history")
    return resolved, sources


def merge_memory(existing: dict[str, Any] | None, new_entities: dict[str, Any] | None) -> dict[str, str]:
    result = normalize_entities(existing)
    result.update(normalize_entities(new_entities))
    return result
