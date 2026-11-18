"""Run the immutable candidate's acceptance entry points with provider metadata capture."""
from __future__ import annotations

import argparse
import asyncio
import atexit
import json
import os
import sys
import time
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx

sys.path[:0] = ["/harness", "/app", "/app/scripts"]
case_id = ContextVar("release_case", default="smoke")
generation = ContextVar("release_generation", default=None)


def install(report: Path, maximum: int) -> None:
    from app.agent.runtime import AgentRuntime

    sink = report.open("x", encoding="utf-8")
    atexit.register(sink.close)
    sends = 0
    submitted = 0
    send_original = httpx.AsyncClient.send
    close_original = httpx.Response.aclose
    run_original = AgentRuntime.run
    streamed = ContextVar("release_streamed_requests", default=None)

    def write(row):
        sink.write(json.dumps(row, ensure_ascii=False) + "\n")
        sink.flush()

    def extract(row, body):
        if not isinstance(body, dict):
            return
        if isinstance(body.get("usage"), dict):
            row["usage"] = {
                key: val for key, val in body["usage"].items()
                if key in {"prompt_tokens", "completion_tokens", "total_tokens",
                           "prompt_cache_hit_tokens", "prompt_cache_miss_tokens"} and isinstance(val, int)
            }
        if isinstance(body.get("model"), str):
            row["model"] = body["model"]
        if isinstance(body.get("id"), str):
            row["providerId"] = body["id"]
        for choice in body.get("choices") or []:
            if choice.get("finish_reason"):
                row["finishReason"] = choice["finish_reason"]

    async def run(self, *args, **kwargs):
        token = generation.set(kwargs.get("generation_id"))
        try:
            return await run_original(self, *args, **kwargs)
        finally:
            generation.reset(token)

    async def send(self, request, *args, **kwargs):
        nonlocal sends, submitted
        if request.method != "POST" or not request.url.path.endswith("/chat/completions"):
            return await send_original(self, request, *args, **kwargs)
        if request.url.scheme != "https" or request.url.host != "api.deepseek.com":
            raise RuntimeError("Release model requests are limited to the official DeepSeek HTTPS endpoint")
        request_bytes = len(request.content)
        if sends >= maximum or submitted + request_bytes > 24_000_000:
            raise RuntimeError("Release model request budget reached")
        sends += 1
        submitted += request_bytes
        row = {"requestId": uuid4().hex, "caseId": case_id.get(), "generationId": generation.get(),
               "utc": datetime.now(timezone.utc).isoformat(), "requestBytes": request_bytes}
        started = time.monotonic()
        write({**row, "event": "attempt"})
        try:
            response = await send_original(self, request, *args, **kwargs)
        except BaseException as error:
            write({**row, "event": "result", "error": type(error).__name__,
                   "elapsedMs": (time.monotonic() - started) * 1000})
            raise
        row["status"] = response.status_code
        if not kwargs.get("stream"):
            try:
                extract(row, response.json())
            except ValueError:
                pass
            write({**row, "event": "result", "elapsedMs": (time.monotonic() - started) * 1000})
            return response
        responses = streamed.get()
        if responses is None:
            responses = {}
            streamed.set(responses)
        responses[id(response)] = (row, started)
        lines = response.aiter_lines

        async def observed_lines():
            async for line in lines():
                if line == "data: [DONE]":
                    row["streamDone"] = True
                elif line.startswith("data: "):
                    try:
                        extract(row, json.loads(line[6:]))
                    except ValueError:
                        pass
                yield line

        response.aiter_lines = observed_lines
        return response

    async def close(self):
        try:
            await close_original(self)
        finally:
            saved = (streamed.get() or {}).pop(id(self), None)
            if saved:
                row, started = saved
                write({**row, "event": "result", "elapsedMs": (time.monotonic() - started) * 1000})

    AgentRuntime.run = run
    httpx.AsyncClient.send = send
    httpx.Response.aclose = close


async def frozen(output: Path, concurrency: int):
    import run_phase_a_graph as phase

    original = phase.run_case

    async def run(split, case, usage):
        token = case_id.set(case["id"])
        try:
            return await original(split, case, usage)
        finally:
            case_id.reset(token)

    phase.run_case = run
    await phase.main(output, concurrency, False, True)


def instrument_client(destination: Path):
    import websockets

    connect = websockets.connect
    send = httpx.AsyncClient.send
    pending = {}

    def save(row):
        with destination.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")

    class Socket:
        def __init__(self, socket):
            self.socket = socket
            self.turn = None

        async def send(self, message):
            if not message.startswith('{"type":'):
                self.turn = {"sent": time.monotonic(), "startedUtc": datetime.now(timezone.utc).isoformat(),
                             "tools": [], "clarifications": 0}
            await self.socket.send(message)

        async def recv(self):
            raw = await self.socket.recv()
            event = json.loads(raw)
            row = self.turn
            if row is not None:
                elapsed = (time.monotonic() - row["sent"]) * 1000
                kind = event.get("type")
                if kind == "start":
                    row["generationId"] = event.get("generationId")
                    row["startEventMs"] = elapsed
                    pending[row["generationId"]] = row
                elif kind == "chunk" and event.get("chunk") and "firstVisibleMs" not in row:
                    row["firstVisibleMs"] = elapsed
                elif kind == "clarification_requested":
                    row["clarifications"] += 1
                elif kind == "tool_call" and event.get("status") != "executing":
                    row["tools"].append({"name": event.get("tool"), "status": event.get("resultStatus"),
                                         "durationMs": event.get("durationMs")})
                elif kind == "completion":
                    row["completionEventMs"] = elapsed
            return raw

    @asynccontextmanager
    async def observed_connect(*args, **kwargs):
        async with connect(*args, **kwargs) as socket:
            yield Socket(socket)

    async def observed_send(self, request, *args, **kwargs):
        response = await send(self, request, *args, **kwargs)
        path = request.url.path
        if request.method == "GET" and "/chat/generation/" in path and response.is_success:
            gid = path.rsplit("/", 1)[-1]
            row = pending.get(gid)
            body = response.json().get("data") or {}
            if row and body.get("status") in {"COMPLETED", "CANCELLED", "FAILED", "INTERRUPTED"}:
                pending.pop(gid)
                saved = (time.monotonic() - row.pop("sent")) * 1000
                save({**row, "persistedMs": saved, "status": body["status"],
                      "conversationId": body.get("conversationId")})
        return response

    websockets.connect = observed_connect
    httpx.AsyncClient.send = observed_send


async def client(mode: str, output: Path):
    if mode == "smoke":
        from run_phase_a_docker_acceptance import run
        if not await run(output):
            raise SystemExit(2)
    elif mode == "windows":
        import probe_missing_request_id as probe
        await probe.probe.run(str(output))
    elif mode == "seed":
        from probe_missing_request_id import seed_windows
        await seed_windows()
    else:
        from run_phase_b_docker import run
        for name in ("handoff-before", "handoff"):
            await run(name, 1, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["frozen", "serve", "smoke-serve", "smoke", "windows", "seed", "faults"])
    parser.add_argument("--output", type=Path, default=Path("/evidence/frozen.jsonl"))
    parser.add_argument("--requests", type=Path)
    parser.add_argument("--maximum", type=int, default=300)
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()
    if args.mode in {"frozen", "serve", "smoke-serve"}:
        if not os.environ.get("LLM_API_KEY") or args.requests is None:
            parser.error("LLM_API_KEY and --requests are required for the live acceptance")
        install(args.requests, args.maximum)
    if args.mode == "frozen":
        asyncio.run(frozen(args.output, args.concurrency))
    elif args.mode == "serve":
        from run_phase_b_docker import serve
        serve()
    elif args.mode == "smoke-serve":
        from run_phase_a_docker_acceptance import serve
        serve()
    else:
        if args.mode != "seed" and args.requests:
            instrument_client(args.requests)
        asyncio.run(client(args.mode, args.output))
