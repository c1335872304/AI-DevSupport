from __future__ import annotations

import base64
import json
import logging
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache
from urllib.parse import urlsplit

from app.core.config import get_settings
from app.core.trace_identity import generation_trace_id

logger = logging.getLogger(__name__)
_active: ContextVar[bool] = ContextVar("langfuse_active", default=False)
_root_trace_id: ContextVar[int | None] = ContextVar("langfuse_root_trace_id", default=None)


@lru_cache(maxsize=1)
def _provider():
    settings = get_settings()
    if not settings.langfuse_enabled:
        return None
    if not (settings.langfuse_base_url and settings.langfuse_public_key and settings.langfuse_secret_key):
        logger.warning("Langfuse export disabled: base URL and both project keys are required")
        return None

    url = urlsplit(settings.langfuse_base_url)
    if url.scheme not in {"http", "https"} or not url.hostname or url.username is not None or url.query or url.fragment:
        logger.warning("Langfuse export disabled: invalid instance base URL")
        return None

    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.trace.id_generator import RandomIdGenerator

    class GenerationIdGenerator(RandomIdGenerator):
        def generate_trace_id(self) -> int:
            return _root_trace_id.get() or super().generate_trace_id()

    credentials = f"{settings.langfuse_public_key}:{settings.langfuse_secret_key.get_secret_value()}"
    encoded = base64.b64encode(credentials.encode()).decode()
    exporter = OTLPSpanExporter(
        endpoint=f"{settings.langfuse_base_url.rstrip('/')}/api/public/otel/v1/traces",
        headers={"Authorization": f"Basic {encoded}", "x-langfuse-ingestion-version": "4"},
        timeout=3,
    )
    provider = TracerProvider(resource=Resource({"service.name": "paismart-backend"}),
                              id_generator=GenerationIdGenerator())
    provider.add_span_processor(BatchSpanProcessor(exporter))
    return provider


@contextmanager
def langfuse_span(name: str, *, root: bool = False, kind: str = "span", attributes: dict | None = None,
                  generation_id: str | None = None):
    if not root and not _active.get():
        yield None
        return
    try:
        provider = _provider()
    except (ImportError, ValueError):
        logger.warning("Langfuse exporter could not initialize")
        provider = None
    if provider is None:
        yield None
        return

    from opentelemetry.context import Context
    token = _active.set(True)
    try:
        trace_id = int(generation_trace_id(generation_id), 16) if root and generation_id else None
        trace_token = _root_trace_id.set(trace_id)
        try:
            span = provider.get_tracer("ai_devsupport.langfuse").start_span(
                name,
                context=Context() if root else None,
                attributes={"langfuse.observation.type": kind, **(attributes or {})},
            )
        finally:
            _root_trace_id.reset(trace_token)
        from opentelemetry.trace import use_span
        with use_span(span, end_on_exit=True, record_exception=False, set_status_on_exception=False):
            try:
                yield span
            except BaseException as exc:
                observation_failed(span, type(exc).__name__)
                raise
    finally:
        _active.reset(token)


def observation_output(span, value: dict) -> None:
    if span is not None:
        span.set_attribute("langfuse.observation.output", json.dumps(value, ensure_ascii=False))


def record_model_usage(usage: dict | None) -> None:
    if not _active.get() or not isinstance(usage, dict):
        return
    from opentelemetry.trace import get_current_span

    span = get_current_span()
    if not span.is_recording():
        return
    details = {
        key: value
        for key, value in (
            ("input", usage.get("prompt_tokens", usage.get("input_tokens"))),
            ("output", usage.get("completion_tokens", usage.get("output_tokens"))),
        )
        if type(value) is int and value >= 0
    }
    if details:
        span.set_attribute("langfuse.observation.usage_details", json.dumps(details))


def observation_failed(span, status: str) -> None:
    if span is not None:
        from opentelemetry.trace import Status, StatusCode

        span.set_attribute("langfuse.observation.status_message", status)
        span.set_status(Status(StatusCode.ERROR, status))


def flush_langfuse() -> bool:
    provider = _provider()
    return provider.force_flush(timeout_millis=5000) if provider is not None else True
