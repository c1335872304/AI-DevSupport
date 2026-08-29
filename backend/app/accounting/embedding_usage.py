from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass
class EmbeddingUsageMeter:
    total_tokens: int = 0

    def add(self, tokens: int) -> None:
        self.total_tokens += max(0, int(tokens or 0))


_current: ContextVar[EmbeddingUsageMeter | None] = ContextVar("paismart_embedding_usage", default=None)


@contextmanager
def capture_embedding_usage():
    meter = EmbeddingUsageMeter()
    token = _current.set(meter)
    try:
        yield meter
    finally:
        _current.reset(token)


def record_embedding_usage(usage: dict | None) -> None:
    meter = _current.get()
    if meter is None or not isinstance(usage, dict):
        return
    total = usage.get("total_tokens", usage.get("prompt_tokens", usage.get("input_tokens", 0)))
    meter.add(int(total or 0))
