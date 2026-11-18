"""Build a bounded, user-reported diagnostic window when request ID is unavailable."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re

from app.agent.entities import extract_entities, topic_changed


_NO_REQUEST_ID = re.compile(
    r"(?:请求(?:号|ID)|request[_ ]?id).{0,12}(?:找不到|拿不到|看不到|没有|不给|没找到|不知道|不清楚)"
    r"|(?:没有|没找到|找不到|拿不到|看不到|不知道|不清楚|没法提供).{0,12}(?:请求(?:号|ID)|request[_ ]?id)",
    re.IGNORECASE,
)
_DATE_TIME = re.compile(
    r"(?<!\d)(20\d{2})[-年](\d{1,2})[-月](\d{1,2})日?[ T]+(\d{1,2}):(\d{2})(?::(\d{2}))?"
)
_ZONE = re.compile(r"北京时间|中国标准时间|\b(?:UTC|GMT)\s*([+-]\d{1,2})(?::([0-5]\d))?|(?<=\d)(Z|[+-]\d{2}:\d{2})\b", re.IGNORECASE)
_CORRECTION = re.compile(r"(?:说错|更正|纠正|不是).{0,80}?[，,：:]\s*(?:而?是|改为|实际是)")
_ENDPOINT = re.compile(r"(?<![A-Za-z0-9._~:/-])(/(?:[A-Za-z0-9._~-]+/)*[A-Za-z0-9._~-]+/?)")
_HTTP_STATUS = re.compile(
    r"(?:HTTP(?:\s*状态码)?|状态码|错误(?:码|是)|返回)\s*[:：=]?\s*([1-5]\d{2})(?![\w-])",
    re.IGNORECASE | re.ASCII,
)
_RADIUS = timedelta(minutes=5)


@dataclass(frozen=True)
class DiagnosticWindow:
    endpoint: str = ""
    error: str = ""
    occurred: datetime | None = None
    zone: timezone | None = None

    def next_question(self, now: datetime) -> str:
        if not self.endpoint:
            return "可以按线索排查。请先告诉我失败的接口路径。"
        if self.occurred is None:
            return "请告诉我大概哪天、几点发生的，并注明时区。"
        if self.zone is None:
            return "你提供的发生时间是哪个时区？例如北京时间（UTC+8）。"
        if self.occurred.replace(tzinfo=self.zone) >= now:
            return "这个时间按所给时区换算后还未发生。请核对日期、时间或时区。"
        if not self.error:
            return "失败时返回的 HTTP 状态码或业务错误码是什么？"
        return ""

    def arguments(self, now: datetime) -> dict:
        instant = self.occurred.replace(tzinfo=self.zone).astimezone(timezone.utc)
        return {
            "endpoint": self.endpoint,
            "window": "explicit",
            "start_at": (instant - _RADIUS).isoformat(),
            "end_at": min(instant + _RADIUS, now).isoformat(),
        }


def _timezone(text):
    match = _ZONE.search(text)
    if match is None:
        return None
    hours, minutes, iso = match.groups()
    if iso and iso.upper() != "Z":
        hours, minutes = iso.split(":")
    if hours is None:
        return timezone.utc if iso else timezone(timedelta(hours=8))
    magnitude = abs(int(hours)) * 60 + int(minutes or 0)
    if magnitude > 14 * 60:
        return None
    return timezone(timedelta(minutes=magnitude * (-1 if hours.startswith("-") else 1)))


def _date_time(text):
    match = _DATE_TIME.search(text)
    if match is not None:
        try:
            return datetime(*(int(field or 0) for field in match.groups()))
        except ValueError:
            pass
    return None


def _reported_error(text, entities):
    if match := _HTTP_STATUS.search(text):
        return match[1]
    if match := re.fullmatch(r"\s*([1-5]\d{2})[。.!！\s]*", text):
        return match[1]
    return entities.get("error_code", "")


def diagnostic_window(question: str, history: list[dict], *, diagnostic: bool) -> DiagnosticWindow | None:
    """Use scoped user turns only. Neither model guesses nor assistant text supply lookup arguments."""
    if topic_changed(question):
        return None
    current = extract_entities(question)
    if current.get("request_id"):
        return None
    if not (diagnostic or _NO_REQUEST_ID.search(question) or _DATE_TIME.search(question) or _ENDPOINT.search(question) or
            _ZONE.search(question) or current.keys() & {"endpoint", "http_status", "error_code"}):
        return None

    available = False
    endpoint = error = ""
    occurred = zone = None
    for text in [*(str(item.get("content") or "") for item in history if item.get("role") == "user"), question]:
        if topic_changed(text):
            available = False
            endpoint = error = ""
            occurred = zone = None
        if match := _CORRECTION.search(text):
            text = text[match.end():]
        entities = extract_entities(text)
        if entities.get("request_id"):
            available = False
            endpoint = error = ""
            occurred = zone = None
            continue
        available = available or bool(_NO_REQUEST_ID.search(text))
        if path := _ENDPOINT.search(text):
            endpoint = path[1]
        error = _reported_error(text, entities) or error
        occurred = _date_time(text) or occurred
        zone = _timezone(text) or zone
    return DiagnosticWindow(endpoint, error, occurred, zone) if available else None


def render_window_result(data: dict, error: str) -> str:
    total = data.get("total", 0)
    scope = f"该接口在 {data['windowStart']} 至 {data['windowEnd']}（UTC）的日志"
    if not total:
        return f"{scope}未查到调用记录。这个窗口无法确认失败原因，请核对接口路径或把发生时间范围说得更具体。"
    statuses = data.get("byStatus") or {}
    matching = statuses.get(error, statuses.get(int(error), 0) if error.isdecimal() else 0)
    if not error.isdecimal():
        return f"{scope}有 {total} 条调用。窗口统计按 HTTP 状态分组，无法核对业务错误码或确认你那次请求的原因。"
    return (
        f"{scope}有 {total} 条调用，其中 HTTP {error} 有 {matching} 条。"
        "这是所给时间和接口的汇总，无法确认其中哪条是你那次请求，也无法仅凭状态码断定原因。"
    )
