"""Read-only Provider usage observation for an isolated copy of the real ASGI app.

No request/answer rewriting, model overrides or production configuration changes.
Only usage/model/latency metadata is persisted; credentials and prompts are not.
"""

import json
import time
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import httpx

CASE = ContextVar("answer_eval_case", default="unattributed")


class ProviderObserver:
    def __init__(self, settings, path):
        self.path = Path(path)
        self.llm_host = urlsplit(settings.llm_base_url).hostname
        self.embedding_host = urlsplit(settings.embedding_base_url).hostname
        self.requests = 0
        self.reserved_cny = 0.0
        self.realized = {}
        frozen = self.path.parent / "frozen-inputs.json"
        budget = json.loads(frozen.read_text()) if frozen.exists() else {}
        self.max_requests = int(budget.get("maxProviderRequests", 144))
        self.max_cny = float(budget.get("maxReservedCny", 10))
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                prior = json.loads(line)
                if prior.get("event") == "request":
                    self.requests = max(self.requests, prior["request"])
                    self.reserved_cny += prior["reservedUpperCny"]

    def log(self, row):
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")

    async def send(self, original, client, request, **kwargs):
        kind = (
            "llm"
            if request.url.host == self.llm_host and request.method == "POST"
            else "embedding"
            if request.url.host == self.embedding_host and request.method == "POST"
            else None
        )
        if not kind:
            return await original(client, request, **kwargs)
        body = json.loads(request.content)
        bound = (
            (len(request.content) * 2 + int(body.get("max_tokens", 2000)) * 8) / 1_000_000
            if kind == "llm"
            else len(request.content) * 0.0005 / 1000
        )
        if (
            self.requests >= self.max_requests
            or self.reserved_cny + bound > self.max_cny
            or len(request.content) > 240000
        ):
            raise RuntimeError("Independent answer evaluation budget reached")
        self.requests += 1
        self.reserved_cny += bound
        row = {
            "request": self.requests,
            "caseId": CASE.get(),
            "kind": kind,
            "requestedModel": body.get("model"),
            "startedAt": datetime.now(UTC).isoformat(),
            "reservedUpperCny": bound,
        }
        started = time.perf_counter()
        self.log({**row, "event": "request"})
        try:
            response = await original(client, request, **kwargs)
        except Exception as exc:
            self.log({**row, "event": "transport_error", "errorType": type(exc).__name__})
            raise
        row["httpStatus"] = response.status_code

        def observe(payload):
            if not isinstance(payload, dict):
                return
            if payload.get("model"):
                row["responseModel"] = payload["model"]
            usage = payload.get("usage")
            if isinstance(usage, dict) and usage:
                self.realized[row["request"]] = usage
                self.log(
                    {
                        **row,
                        "event": "usage",
                        "usage": usage,
                        "elapsedMs": round((time.perf_counter() - started) * 1000, 2),
                    }
                )

        if response.is_stream_consumed:
            try:
                observe(response.json())
            except ValueError:
                pass
            if row["request"] not in self.realized:
                self.log({**row, "event": "usage_missing"})
        else:
            lines = response.aiter_lines

            async def observed_lines():
                try:
                    async for line in lines():
                        if line.startswith("data:"):
                            try:
                                observe(json.loads(line[5:].strip()))
                            except ValueError:
                                pass
                        yield line
                finally:
                    if row["request"] not in self.realized:
                        self.log({**row, "event": "usage_missing"})

            response.aiter_lines = observed_lines
        return response


class CaseMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        case = dict(scope.get("headers") or []).get(b"x-eval-case", b"unattributed").decode()[:80]
        token = CASE.set(case)
        try:
            await self.app(scope, receive, send)
        finally:
            CASE.reset(token)


if __name__ == "__main__":
    import uvicorn

    from app.core.config import get_settings

    observer = ProviderObserver(get_settings(), "/evaluation/provider-usage.jsonl")
    original = httpx.AsyncClient.send

    async def observed_send(client, request, **kwargs):
        return await observer.send(original, client, request, **kwargs)

    httpx.AsyncClient.send = observed_send
    from app.main import app

    app.add_middleware(CaseMiddleware)
    # The existing services already own startup/recovery/maintenance. Do not
    # run duplicate orphan recovery or maintenance against the shared Demo DB.
    uvicorn.run(app, host="0.0.0.0", port=8000, lifespan="off", access_log=False)
