"""Run the frozen Phase A cases through AgentRuntime with isolated tool fixtures."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
import uuid
from collections import Counter
from copy import deepcopy
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.accounting.llm_usage import capture_llm_usage
from app.agent.llm import llm_service
from app.agent.runtime import AgentRuntime
from app.agent.types import AgentToolCall
from app.core.config import get_settings
from app.db.models import User
from app.evaluation.answer import evaluate_answer
from app.evaluation.customer_service import evaluate_customer_service_case, validate_customer_service_case
from app.evaluation.customer_service_live import _fixture_for
from app.tools.base import ToolResult
from app.tools.registry import ToolRegistry, tool_registry


def load_cases():
    directory = BACKEND / "eval" / "customer_service"
    manifest = json.loads((directory / "phase_a_manifest.json").read_text(encoding="utf-8"))
    for split, spec in manifest["splits"].items():
        payload = (directory / spec["file"]).read_bytes()
        if hashlib.sha256(payload).hexdigest() != spec["sha256"]:
            raise ValueError(f"Frozen fixture fingerprint mismatch: {split}")
        cases = [json.loads(line) for line in payload.splitlines() if line.strip()]
        if len(cases) != spec["cases"]:
            raise ValueError(f"Frozen fixture count mismatch: {split}")
        for case in cases:
            validate_customer_service_case(case)
            yield split, case


async def run_case(split, case, usage):
    counts = Counter()
    pending = {}
    events = []
    chunks = []
    first_token_ms = 0.0
    started = time.monotonic()

    async def transport(tool, context, arguments):
        index = counts[tool.name]
        counts[tool.name] += 1
        fixture = _fixture_for(case, AgentToolCall("", tool.name, arguments), index)
        return ToolResult(
            status=fixture.get("status", "SUCCESS"),
            data=deepcopy(fixture.get("data")),
            error=fixture.get("error"),
            duration_ms=fixture.get("durationMs"),
        )

    async def send(event):
        events.append(event)
        if event["type"] == "tool_call":
            event_id = event["toolCallId"]
            if event["status"] == "executing":
                pending[event_id] = {
                    "id": event_id, "name": event["tool"], "arguments": event["arguments"],
                    "step": event["agentStep"],
                }
            else:
                pending[event_id].update(
                    status=event["resultStatus"], durationMs=event.get("durationMs"), error=event.get("error"),
                )

    async def chunk(text):
        nonlocal first_token_ms
        if not chunks:
            first_token_ms = (time.monotonic() - started) * 1000
        chunks.append(text)

    registry = ToolRegistry((tool_registry.get(name) for name in tool_registry.names()), transport=transport)
    runtime = AgentRuntime(registry)
    if runtime.settings.billing_mcp_enabled:
        raise RuntimeError("Set BILLING_MCP_ENABLED=false for the isolated local-tool fixture run")
    user = User(id="phase-a-fixture-user", role="USER")
    answer, references = await runtime.run(
        user=user, question=case["question"], history=deepcopy(case.get("history") or []),
        generation_id=uuid.uuid4().hex, send_json=send, on_chunk=chunk,
    )
    trace = next(event["trace"] for event in reversed(events) if event["type"] == "skill_trace")
    artifact = {
        "answer": answer,
        "references": references,
        "activeSkills": trace.get("activeSkills", []),
        "toolCalls": list(pending.values()),
        "timing": {"totalMs": (time.monotonic() - started) * 1000, "firstTokenMs": first_token_ms},
        "usage": {"promptTokens": usage.prompt_tokens, "completionTokens": usage.completion_tokens,
                  "totalTokens": usage.total_tokens},
        "publicChunks": chunks,
        "trace": trace,
        "events": events,
    }
    score = evaluate_customer_service_case(case, artifact)
    return {
        "caseId": case["id"], "split": split, "automatedPass": score.passed,
        "layers": {
            name: {"passed": layer.passed, "metrics": layer.metrics, "details": layer.details}
            for name, layer in score.layers.items()
        },
        "artifact": artifact,
    }


async def smoke():
    with capture_llm_usage() as usage:
        chunks = [chunk async for chunk in llm_service.stream_messages(
            [{"role": "user", "content": "请用简体中文回复一句问候。"}], force_no_tools=True,
        )]
        if not chunks or usage.provider_errors or not any(
            item == {"stage": "answer", "reason": "stop"} for item in usage.finish_reasons
        ):
            raise RuntimeError(f"Streaming smoke failed: {usage.provider_errors or usage.finish_reasons}")
        print(f"smoke_text passed=true chunks={len(chunks)} tokens={usage.total_tokens}")

    with capture_llm_usage() as usage:
        tools = [{"type": "function", "function": {
            "name": "query_test_status", "description": "Look up the status of a synthetic test case.",
            "parameters": {"type": "object", "properties": {"case_id": {"type": "string"}},
                           "required": ["case_id"], "additionalProperties": False},
        }}]
        events = [event async for event in llm_service.stream_agent_turn(
            [{"role": "user", "content": "请调用 query_test_status 查询合成测试编号 smoke-17，不要猜测。"}],
            tools,
        )]
        calls = [call for event in events if event["type"] == "tool_calls" for call in event["tool_calls"]]
        if usage.provider_errors or not any(
            call.name == "query_test_status" and call.arguments == {"case_id": "smoke-17"} for call in calls
        ):
            raise RuntimeError(f"Tool smoke failed: {usage.provider_errors or usage.finish_reasons}")
        print(f"smoke_tool passed=true calls={len(calls)} tokens={usage.total_tokens}")


async def main(output, concurrency, offline, smoke_first=False):
    settings = get_settings()
    if settings.redis_enabled or settings.billing_mcp_enabled:
        raise RuntimeError("Disable Redis and Billing MCP to keep this fixture run isolated")
    if offline and (settings.llm_api_key or settings.langfuse_enabled):
        raise RuntimeError("Clear LLM_API_KEY and disable Langfuse for offline runs")
    cases = list(load_cases())
    if smoke_first:
        if offline or not settings.llm_api_key:
            raise RuntimeError("Smoke requires a configured live model")
        await smoke()
    semaphore = asyncio.Semaphore(concurrency)

    async def attempt(split, case):
        async with semaphore:
            with capture_llm_usage() as meter:
                try:
                    async with asyncio.timeout(240):
                        row = await run_case(split, case, meter)
                except Exception as exc:
                    row = {"caseId": case["id"], "split": split, "error": type(exc).__name__}
            row["providerErrors"] = meter.provider_errors
            row["finishReasons"] = meter.finish_reasons
            row["truncated"] = any(item["reason"] == "length" for item in meter.finish_reasons)
            stream.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
            stream.flush()
            return row

    with output.open("x", encoding="utf-8") as stream:
        rows = await asyncio.gather(*(attempt(split, case) for split, case in cases))
    pairs = Counter(row["caseId"].rsplit("-", 1)[0] for row in rows if row.get("automatedPass"))
    errors = sum("error" in row for row in rows)
    usage = sum(bool(row.get("artifact", {}).get("usage", {}).get("totalTokens")) for row in rows)
    cases_by_id = {case["id"]: case for _, case in cases}
    citations = []
    for row in rows:
        details = row.get("layers", {}).get("answerQuality", {}).get("details")
        if details is None:
            details = evaluate_answer("", cases_by_id[row["caseId"]]).details
        citations.append(details["citations"])
    applicable = [item for item in citations if item.get("requiredFactCount")]
    print(f"claim_citations={sum(item['passedFactCount'] for item in applicable)}/"
          f"{sum(item['requiredFactCount'] for item in applicable)} "
          f"case_citations={sum(item['allRequiredFactsPassed'] for item in applicable)}/{len(applicable)}")
    print(f"offline={offline} cases={len(rows)} passed={sum(pairs.values())} pairs_passed={sum(n == 2 for n in pairs.values())} "
          f"errors={errors} cases_with_provider_usage={usage}")
    # Some graph paths resolve deterministically and do not need a model call.
    if errors or (not offline and not usage):
        raise SystemExit(2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--offline", action="store_true", help="Exercise the production graph with its no-provider fallback")
    parser.add_argument("--smoke-first", action="store_true", help="Require live text and tool smoke checks before the suite")
    args = parser.parse_args()
    if args.concurrency < 1:
        parser.error("--concurrency must be positive")
    asyncio.run(main(args.output, args.concurrency, args.offline, args.smoke_first))
