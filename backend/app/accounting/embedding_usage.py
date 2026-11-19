from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass
class EmbeddingUsageMeter:
    total_tokens: int = 0
    has_usage: bool = False
    request_ids: list[str] = field(default_factory=list)

    def add(self, tokens: int) -> None:
        self.total_tokens += max(0, int(tokens or 0))


_current: ContextVar[EmbeddingUsageMeter | None] = ContextVar("paismart_embedding_usage", default=None)


@contextmanager
def capture_embedding_usage():
    parent = _current.get()
    meter = EmbeddingUsageMeter()
    token = _current.set(meter)
    try:
        yield meter
    finally:
        _current.reset(token)
        if parent is not None:
            # Per-document meters must also contribute to an enclosing build/run
            # budget report, rather than hiding all indexed-document usage.
            parent.add(meter.total_tokens)
            parent.has_usage = parent.has_usage or meter.has_usage
            parent.request_ids.extend(meter.request_ids)


def record_embedding_usage(usage: dict | None, request_id: str | None = None) -> None:
    from app.accounting.provider_ledger import observe_usage
    observe_usage(usage, kind="EMBEDDING", request_id=request_id)
    meter = _current.get()
    if meter is None or not isinstance(usage, dict):
        return
    meter.has_usage = True
    if request_id:
        meter.request_ids.append(str(request_id))
    total = usage.get("total_tokens", usage.get("prompt_tokens", usage.get("input_tokens", 0)))
    meter.add(int(total or 0))
