from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass
class LLMUsageMeter:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reasons: list[dict[str, str]] = field(default_factory=list)
    provider_errors: list[str] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def add(self, prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
        self.prompt_tokens += max(0, int(prompt_tokens or 0))
        self.completion_tokens += max(0, int(completion_tokens or 0))


_current_meter: ContextVar[LLMUsageMeter | None] = ContextVar("paismart_llm_usage_meter", default=None)


@contextmanager
def capture_llm_usage():
    meter = LLMUsageMeter()
    token = _current_meter.set(meter)
    try:
        yield meter
    finally:
        _current_meter.reset(token)


def record_provider_usage(usage: dict | None) -> None:
    meter = _current_meter.get()
    if meter is None or not isinstance(usage, dict):
        return
    prompt = usage.get("prompt_tokens", usage.get("input_tokens", 0))
    completion = usage.get("completion_tokens", usage.get("output_tokens", 0))
    meter.add(int(prompt or 0), int(completion or 0))


def record_provider_finish(stage: str, reason: str) -> None:
    meter = _current_meter.get()
    if meter is not None and reason:
        meter.finish_reasons.append({"stage": stage, "reason": reason})


def record_provider_error(reason: str) -> None:
    meter = _current_meter.get()
    if meter is not None:
        meter.provider_errors.append(reason)
