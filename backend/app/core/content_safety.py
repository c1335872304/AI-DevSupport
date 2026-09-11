from __future__ import annotations

import re
from typing import Any


_INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("instruction_override", re.compile(r"(?:ignore|disregard|forget)\s+(?:all\s+)?(?:previous|prior|above)\s+instructions", re.IGNORECASE)),
    ("role_override", re.compile(r"(?:system|developer)\s+(?:message|prompt|instruction)|you\s+are\s+now\s+", re.IGNORECASE)),
    ("secret_exfiltration", re.compile(r"(?:reveal|print|show|泄露|输出|提供).{0,24}(?:system prompt|secret|password|api key|token|密钥|密码|令牌)", re.IGNORECASE)),
    ("tool_authority", re.compile(r"(?:call|execute|invoke)\s+(?:the\s+)?(?:tool|function)|(?:调用|执行).{0,12}(?:工具|函数)", re.IGNORECASE)),
    ("instruction_override_zh", re.compile(r"(?:忽略|无视|忘记).{0,12}(?:之前|上面|先前).{0,12}(?:指令|规则|提示)")),
)


def detect_prompt_injection(value: str | None) -> list[str]:
    text = str(value or "")
    return [name for name, pattern in _INJECTION_PATTERNS if pattern.search(text)]


def sanitize_untrusted_data(value: Any) -> tuple[Any, list[str]]:
    """Isolate suspicious instructions before tool output reaches the LLM."""
    warnings: list[str] = []

    def walk(item: Any) -> Any:
        if isinstance(item, str):
            matches = detect_prompt_injection(item)
            if matches:
                warnings.extend(matches)
                return "[内容已隔离：检测到疑似提示注入，原文不可作为指令执行]"
            return item
        if isinstance(item, dict):
            return {str(key): walk(child) for key, child in item.items()}
        if isinstance(item, list):
            return [walk(child) for child in item]
        if isinstance(item, tuple):
            return [walk(child) for child in item]
        return item

    return walk(value), sorted(set(warnings))

