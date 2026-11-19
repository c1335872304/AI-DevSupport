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
    "api_version",
    "product",
    "region",
)

_ENTITY_RE: dict[str, re.Pattern[str]] = {
    "request_id": re.compile(r"\b(?:req_[A-Za-z0-9][A-Za-z0-9_-]*|request[_ -]?id\s*[:=：]?\s*[A-Za-z0-9][A-Za-z0-9_-]*)\b", re.I),
    "error_code": re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b"),
    # Do not use ``\b`` here: in Python, Chinese characters are word
    # characters, so ``返回401`` would otherwise fail the boundary check.
    "http_status": re.compile(r"(?<![A-Za-z0-9_])[1-5]\d{2}(?![A-Za-z0-9_])"),
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


def topic_changed(question: str) -> bool:
    question = question or ""
    if re.search(r"换个|换一个|另一个问题|新问题|不说这个|先不查", question):
        return True
    unrelated = re.search(r"退款|发票|账单|订单|套餐|介绍.*政策", question)
    same_incident = re.search(r"刚才|这个|那个|401|429|限流|鉴权|调用|请求|故障", question)
    return bool(unrelated and not same_incident)


def history_entities(history: list[dict] | None) -> dict[str, str]:
    """Use only contiguous user topic; assistant text never establishes IDs."""
    found: dict[str, str] = {}
    for item in history or []:
        if item.get("role") != "user":
            continue
        text = str(item.get("content") or "")
        current = extract_entities(text)
        changed = any(current.get(k) and found.get(k) and current[k] != found[k]
                      for k in ("request_id", "app_id"))
        if topic_changed(text) or changed:
            found = {}
        found.update(current)
    return found


def looks_like_follow_up(question: str, history: list[dict] | None = None) -> bool:
    if not history or topic_changed(question):
        return False
    markers = ("这个", "那个", "它", "刚才", "上面", "前面", "为什么", "那", "所以", "继续", "呢", "怎么办", "还是", "已经", "已修改", "已修正", "已恢复", "重试")
    return any(marker in (question or "") for marker in markers)


def resolve_entities(
    question: str, history: list[dict] | None,
    model_entities: dict[str, Any] | None = None,
    remembered_entities: dict[str, Any] | None = None,
    follow_up: bool | None = None,
) -> tuple[dict[str, str], dict[str, str]]:
    """Explicit current IDs win over model extraction and scoped history."""
    current = {k: v for k, v in normalize_entities(model_entities).items() if v in (question or "")}
    current.update(extract_entities(question))
    previous = history_entities(history) if history else normalize_entities(remembered_entities)
    boundary = topic_changed(question) or any(
        current.get(k) and current[k] != previous.get(k) for k in ("request_id", "app_id")
    )
    inherit = not boundary and (looks_like_follow_up(question, history) if follow_up is None else bool(follow_up))
    resolved = dict(previous) if inherit else {}
    resolved.update(current)
    sources = {key: "current" for key in current}
    for key in resolved:
        sources.setdefault(key, "history")
    return resolved, sources


def merge_memory(existing: dict[str, Any] | None, new_entities: dict[str, Any] | None) -> dict[str, str]:
    result = normalize_entities(existing)
    result.update(normalize_entities(new_entities))
    return result
