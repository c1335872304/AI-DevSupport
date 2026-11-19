import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from pydantic import SecretStr

from app.core import langfuse_observability as telemetry
from app.core.config import get_settings


@pytest.fixture
def langfuse_receiver(monkeypatch):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            data = self.rfile.read(int(self.headers["Content-Length"]))
            requests.append((self.path, self.headers, data))
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    settings = get_settings()
    monkeypatch.setattr(settings, "langfuse_enabled", True)
    monkeypatch.setattr(settings, "langfuse_base_url", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setattr(settings, "langfuse_public_key", "pk-test")
    monkeypatch.setattr(settings, "langfuse_secret_key", SecretStr("sk-test"))
    monkeypatch.setattr(settings, "llm_api_key", "")
    telemetry._provider.cache_clear()
    def exported_spans(*excluded):
        assert telemetry.flush_langfuse()
        assert requests
        spans = []
        for path, headers, body in requests:
            assert path == "/api/public/otel/v1/traces"
            assert headers["Authorization"] == "Basic cGstdGVzdDpzay10ZXN0"
            assert headers["x-langfuse-ingestion-version"] == "4"
            assert all(value.encode() not in body for value in excluded)
            batch = ExportTraceServiceRequest.FromString(body)
            for resource in batch.resource_spans:
                assert [item.key for item in resource.resource.attributes] == ["service.name"]
                spans.extend(span for scope in resource.scope_spans for span in scope.spans)
        return spans

    try:
        yield exported_spans
    finally:
        provider = telemetry._provider()
        if provider is not None:
            provider.shutdown()
        telemetry._provider.cache_clear()
        server.shutdown()
        server.server_close()
        thread.join()
