from __future__ import annotations

from contextlib import contextmanager

from app.core.config import get_settings

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
except ImportError:  # pragma: no cover
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"
    Counter = Histogram = None
    generate_latest = None

settings = get_settings()

if Counter is not None:
    HTTP_REQUESTS = Counter("paismart_http_requests_total", "HTTP requests", ["method", "path", "status"])
    HTTP_LATENCY = Histogram("paismart_http_request_duration_seconds", "HTTP latency", ["method", "path"])
    TOOL_CALLS = Counter("paismart_tool_calls_total", "Agent tool calls", ["tool", "status"])
    TOOL_LATENCY = Histogram("paismart_tool_duration_seconds", "Agent tool latency", ["tool"])
    GENERATIONS = Counter("paismart_generations_total", "Chat generations", ["status"])
    GENERATION_LATENCY = Histogram("paismart_generation_duration_seconds", "End-to-end chat generation latency", ["status"])
    GENERATION_FIRST_TOKEN = Histogram("paismart_generation_first_token_seconds", "Time to first streamed answer token")
    GENERATION_TOKENS = Histogram("paismart_generation_tokens", "LLM tokens charged per generation", ["mode"])
else:  # lightweight no-op fallback for minimal environments
    HTTP_REQUESTS = HTTP_LATENCY = TOOL_CALLS = TOOL_LATENCY = GENERATIONS = None
    GENERATION_LATENCY = GENERATION_FIRST_TOKEN = GENERATION_TOKENS = None


def prometheus_payload() -> tuple[bytes, str]:
    if generate_latest is None:
        return b"# prometheus-client not installed\n", CONTENT_TYPE_LATEST
    return generate_latest(), CONTENT_TYPE_LATEST


def observe_tool(name: str, status: str, duration_ms: int | None) -> None:
    if TOOL_CALLS is not None:
        TOOL_CALLS.labels(tool=name, status=status).inc()
    if TOOL_LATENCY is not None and duration_ms is not None:
        TOOL_LATENCY.labels(tool=name).observe(max(0, duration_ms) / 1000.0)


def observe_generation(
    status: str,
    *,
    duration_ms: int | float | None = None,
    first_token_ms: int | float | None = None,
    tokens: int | None = None,
    token_mode: str = "unknown",
) -> None:
    if GENERATIONS is not None:
        GENERATIONS.labels(status=status).inc()
    if GENERATION_LATENCY is not None and duration_ms is not None:
        GENERATION_LATENCY.labels(status=status).observe(max(0.0, float(duration_ms)) / 1000.0)
    if GENERATION_FIRST_TOKEN is not None and first_token_ms is not None:
        GENERATION_FIRST_TOKEN.observe(max(0.0, float(first_token_ms)) / 1000.0)
    if GENERATION_TOKENS is not None and tokens is not None:
        GENERATION_TOKENS.labels(mode=token_mode).observe(max(0, int(tokens)))


def setup_otel(app) -> None:
    if not settings.otel_enabled:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        return
    provider = TracerProvider(resource=Resource.create({"service.name": settings.otel_service_name}))
    if settings.otel_exporter_otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


@contextmanager
def trace_span(name: str, attributes: dict | None = None):
    try:
        from opentelemetry import trace
        tracer = trace.get_tracer(settings.otel_service_name)
    except Exception:
        yield None
        return
    with tracer.start_as_current_span(name, attributes=attributes or {}) as span:
        yield span
