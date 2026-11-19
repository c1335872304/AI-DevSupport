"""Run actual AgentRuntime episodes on synthetic SQLite; no real provider calls."""

import argparse
import asyncio
import importlib.util
import json
import os
import sys
import time
import uuid
import zipfile
from collections import Counter
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OBS = {
    "AUTH_MISSING": (401, {"authPresent": False}),
    "AUTH_FORMAT": (401, {"authPresent": True, "authSchemeValid": False}),
    "KEY_INVALID": (401, {"authPresent": True, "authSchemeValid": True, "keyStateAtCall": "REVOKED"}),
    "KEY_EXPIRED": (401, {"authPresent": True, "authSchemeValid": True, "keyStateAtCall": "EXPIRED"}),
    "APP_MISMATCH": (
        401,
        {
            "authPresent": True,
            "authSchemeValid": True,
            "keyStateAtCall": "ACTIVE",
            "keyAppIdAtCall": "app_other",
        },
    ),
    "RATE_LIMIT": (429, {"limiterKind": "RATE", "rateObserved": 12, "rateLimit": 10}),
    "CONCURRENCY_LIMIT": (
        429,
        {"limiterKind": "CONCURRENCY", "concurrencyObserved": 7, "concurrencyLimit": 5},
    ),
    "QUOTA_LIMIT": (429, {"limiterKind": "QUOTA", "quotaRemaining": 0}),
}


async def main(args):
    output = ROOT / "data/checkpoints/phase4"
    output.mkdir(parents=True, exist_ok=True)
    label = "live" if args.live else args.mode
    live_key = ""
    configured_model = ""
    if args.live:
        from dotenv import dotenv_values

        values = dotenv_values(ROOT / ".env")
        live_key = os.environ.get("LLM_API_KEY") or values.get("LLM_API_KEY") or ""
        configured_model = os.environ.get("LLM_MODEL") or values.get("LLM_MODEL") or "deepseek-chat"
        if not live_key or args.model != "deepseek-flash":
            raise RuntimeError(
                "Live acceptance requires configured key and explicit --model deepseek-flash; config is never rewritten"
            )
    os.environ["DATABASE_URL"] = (
        "sqlite+aiosqlite:///" + (output / f"episodes-{label}-{uuid.uuid4().hex[:8]}.sqlite").as_posix()
    )
    os.environ.update(
        LLM_API_KEY="",
        EMBEDDING_API_KEY="",
        REDIS_ENABLED="false",
        BILLING_MCP_ENABLED="false",
        SKILLS_SEMANTIC_ROUTING_ENABLED="false",
        AGENT_TRACE_PERSIST_ENABLED="false",
        RAG_QUERY_REWRITE_ENABLED="false",
        DIAGNOSIS_RECOVERY_ENABLED="false",
    )
    from sqlalchemy import select

    from app.accounting.llm_usage import capture_llm_usage
    from app.agent.llm import llm_service
    from app.agent.runtime import AgentRuntime
    from app.core.config import get_settings
    from app.core.time import utcnow
    from app.db.models import (
        Base,
        ConversationSession,
        SupportApiCallLog,
        SupportApiKey,
        SupportHandoff,
        SupportRequestObservation,
        User,
    )
    from app.db.session import SessionLocal, engine
    from app.diagnosis.service import read_detail
    from app.evaluation.trajectory import score_episode, summarize
    from app.tools.base import ToolResult
    from app.tools.local.api_support import (
        QueryApiKeyStatusTool,
        QueryCallLogTool,
        QueryErrorCodeTool,
        QueryRecentCallStatsTool,
        QueryRequestObservationTool,
    )
    from app.tools.local.support import CreateSupportHandoffTool
    from app.tools.registry import ToolRegistry

    if args.mode == "preopt":
        with zipfile.ZipFile(ROOT / "data/checkpoints/phase4-start/source.zip") as archive:
            source = archive.read("backend/app/agent/graph/workflow.py")
        frozen = output / "preopt_workflow.py"
        frozen.write_bytes(source)
        spec = importlib.util.spec_from_file_location("phase4_preopt_workflow", frozen)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        from app.agent.graph import workflow

        workflow.CustomerServiceWorkflow.target_specialist_dispatch = (
            module.CustomerServiceWorkflow.target_specialist_dispatch
        )
    # A no-proposal planner records invocation overhead. It is not a real model.
    # Keep the nonempty marker to disable the offline fallback planner explicitly.
    get_settings().llm_api_key = live_key if args.live else "offline-evaluation-marker"
    counters = Counter()

    async def planner(*_, **__):
        counters["planner"] += 1
        if False:
            yield {}

    async def answer(*_, **__):
        yield "当前资料不足，无法确认账户状态。"

    http_calls, submitted_bytes = [], 0
    if args.live:
        import httpx

        budget_path = output / "live-budget.json"
        if budget_path.exists():
            reserved = json.loads(budget_path.read_text(encoding="utf-8"))
        else:
            previous_path = output / "diagnosis-live.json"
            previous = json.loads(previous_path.read_text(encoding="utf-8")) if previous_path.exists() else {}
            reserved = {
                "requests": previous.get("providerCalls", 0),
                "submittedBytes": sum(r["submittedBytes"] for r in previous.get("requests", [])),
            }
        settings = get_settings()
        if settings.llm_base_url.rstrip("/") not in {
            "https://api.deepseek.com",
            "https://api.deepseek.com/v1",
        }:
            raise RuntimeError("Live acceptance is restricted to the configured official provider")
        settings.llm_model, settings.llm_max_tokens = args.model, 512
        settings.llm_max_retries, settings.llm_request_timeout_seconds = 0, 30
        original_send = httpx.AsyncClient.send

        async def bounded_send(client, request, **kwargs):
            nonlocal submitted_bytes
            if request.url.host != "api.deepseek.com" or request.method != "POST":
                raise RuntimeError("Unexpected live provider destination")
            body = json.loads(request.content)
            if (
                reserved["requests"] >= 6
                or reserved["submittedBytes"] + len(request.content) > 100000
                or body.get("max_tokens", 0) > 512
            ):
                raise RuntimeError("Live request/token/byte budget reached")
            reserved["requests"] += 1
            reserved["submittedBytes"] += len(request.content)
            budget_path.write_text(json.dumps(reserved, indent=2), encoding="utf-8")
            submitted_bytes += len(request.content)
            entry = {"model": body.get("model"), "submittedBytes": len(request.content)}
            http_calls.append(entry)
            result = await original_send(client, request, **kwargs)
            entry["status"] = result.status_code
            return result

        httpx.AsyncClient.send = bounded_send
    else:
        llm_service.stream_agent_turn, llm_service.stream_messages = planner, answer
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        user, other = (
            User(username="episode_owner", password="unused", role="USER"),
            User(username="other_owner", password="unused", role="USER"),
        )
        db.add_all([user, other])
        await db.commit()
    cases = [
        json.loads(line)
        for line in (ROOT / "eval/phase4/diagnosis.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    if args.live:
        cases = [
            case
            for case in cases
            if case["id"] in {"dev-key_expired", "holdout-missing-observation", "holdout-explicit-handoff"}
        ]
    rows, artifacts = [], []
    usage_totals = Counter()
    for index, case in enumerate(cases):
        tag, calls, events = f"eval{index}", [], []
        request = f"req_eval_{index}_old"
        status, obs = OBS[case["cause"]]

        class Registry(ToolRegistry):
            async def execute(self, name, arguments, context):
                anchor = (
                    arguments.get("request_id") in {request, f"req_eval_{index}_new"}
                    if name in {"query_call_log", "query_request_observation"}
                    else arguments.get("app_id") in {"app_main", "app_other"}
                    if name == "query_api_key_status"
                    else arguments.get("request_id") in {request, f"req_eval_{index}_new"}
                    if name == "query_recent_call_stats"
                    else True
                )
                calls.append({"tool": name, "arguments": arguments, "anchored": anchor})
                if (
                    case.get("timeout")
                    and name == "query_call_log"
                    and sum(c["tool"] == name for c in calls) == 1
                ):
                    return ToolResult("TIMEOUT", error="injected timeout")
                return await super().execute(name, arguments, context)

        registry = Registry(
            [
                QueryCallLogTool(),
                QueryRequestObservationTool(),
                QueryApiKeyStatusTool(),
                QueryRecentCallStatsTool(),
                QueryErrorCodeTool(),
                CreateSupportHandoffTool(),
            ]
        )
        async with SessionLocal() as db:
            db.add(ConversationSession(conversation_id=tag, user_id=str(user.id)))
            if index == 0:
                db.add(
                    SupportApiKey(
                        id="eval-key",
                        user_id=str(user.id),
                        app_id="app_main",
                        key_masked="demo-***",
                        status="ACTIVE",
                    )
                )
            if not case.get("missing"):
                owner = other if case.get("foreign") else user
                db.add(
                    SupportApiCallLog(
                        request_id=request,
                        user_id=str(owner.id),
                        app_id="app_main",
                        endpoint="/v1/chat",
                        http_status=status,
                        created_at=utcnow() - timedelta(minutes=10),
                    )
                )
                if case.get("observations", True):
                    db.add(
                        SupportRequestObservation(
                            request_id=request,
                            user_id=str(owner.id),
                            service_id="demo-api",
                            rule_version=case.get("version", "2026-10-v1"),
                            observations_json=json.dumps(case.get("override", obs)),
                        )
                    )
            await db.commit()

        async def send(event):
            events.append(event)

        async def chunk(_):
            pass

        runtime = AgentRuntime(registry)
        question = f"请求 {request} 返回{case.get('claimedStatus', status)}，请核查。" + (
            "请转人工客服" if case.get("handoff") else ""
        )
        before = counters["planner"]
        started = time.perf_counter()
        http_before = len(http_calls)
        with capture_llm_usage() as usage:
            text, _ = await runtime.run(
                user=user,
                question=question,
                history=[],
                conversation_id=tag,
                generation_id=tag + "g1",
                send_json=send,
                on_chunk=chunk,
            )
        usage_totals.update(prompt=usage.prompt_tokens, completion=usage.completion_tokens)
        first = next(e["diagnosis"] for e in reversed(events) if e.get("type") == "diagnosis_state")
        history = [{"role": "user", "content": question}]
        if case.get("followup"):
            new = f"req_eval_{index}_new"
            code, followobs = OBS.get(case["followup"], (200, {}))
            async with SessionLocal() as db:
                db.add(
                    SupportApiCallLog(
                        request_id=new,
                        user_id=str(user.id),
                        app_id=case.get("newApp", "app_main"),
                        endpoint=case.get("newEndpoint", "/v1/chat"),
                        http_status=code,
                        created_at=utcnow() - timedelta(minutes=20) if case.get("oldTime") else utcnow(),
                    )
                )
                db.add(
                    SupportRequestObservation(
                        request_id=new,
                        user_id=str(user.id),
                        service_id="demo-api",
                        rule_version="2026-10-v1",
                        observations_json=json.dumps(followobs),
                    )
                )
                await db.commit()
            followup = f"已调整，复查 {new}"
        else:
            followup = "已恢复，不用复查" if case.get("feedback") else "继续核查"
        if case.get("followup") or case.get("feedback") or case.get("repeat"):
            text, _ = await runtime.run(
                user=user,
                question=followup,
                history=history,
                conversation_id=tag,
                generation_id=tag + "g2",
                send_json=send,
                on_chunk=chunk,
            )
        detail = await read_detail(user, first["diagnosisId"])
        async with SessionLocal() as db:
            tickets = list(
                (
                    await db.scalars(
                        select(SupportHandoff.handoff_id).where(
                            SupportHandoff.diagnosis_id == first["diagnosisId"]
                        )
                    )
                ).all()
            )
        artifact = {
            "id": case["id"],
            "userId": str(user.id),
            "diagnosis": detail,
            "tickets": tickets,
            "calls": calls,
            "plannerCalls": counters["planner"] - before,
            "durationMs": (time.perf_counter() - started) * 1000,
            "answer": text,
            "optimizationEvents": [e for e in events if e.get("type") == "diagnosis_planning_skipped"],
        }
        artifact["providerRequests"] = len(http_calls) - http_before
        if args.live:
            artifact["plannerCalls"] = artifact["providerRequests"]
        artifacts.append(artifact)
        rows.append({**score_episode(case["expected"], artifact), "split": case["split"]})
        if args.live and (
            (len(http_calls) > http_before and not usage.total_tokens)
            or any(
                plan.get("error")
                for event in events
                if event.get("type") == "target_specialists_dispatched"
                for plan in event.get("agentPlans", [])
            )
        ):
            rows[-1]["passed"] = False
            rows[-1]["checks"]["providerAvailableAndMetered"] = False
            break  # Unknown usage or provider failure must stop paid evaluation.
    report = {
        "mode": label,
        "providerCalls": len(http_calls),
        "tokens": usage_totals["prompt"] + usage_totals["completion"],
        "usage": dict(usage_totals),
        "costCny": None if args.live else 0,
        "conservativeCostUpperCny": (usage_totals["prompt"] * 2 + usage_totals["completion"] * 8) / 1000000
        if args.live
        else 0,
        "requestBudget": {
            "maxRequests": 6,
            "maxSubmittedBytes": 100000,
            "maxOutputPerRequest": 512,
            "maxCny": 2,
        },
        "requests": http_calls,
        "configuredModel": configured_model,
        "acceptanceModel": args.model if args.live else None,
        "summary": summarize(rows),
        "bySplit": {
            split: summarize([r for r in rows if r["split"] == split]) for split in {r["split"] for r in rows}
        },
        "rows": rows,
        "artifacts": artifacts,
    }
    if args.live and len(rows) != 3:
        report["summary"]["pass"] = False
    (output / f"diagnosis-{label}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report["summary"]))
    await engine.dispose()
    if not report["summary"]["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["preopt", "final"], default="final")
    parser.add_argument(
        "--live", action="store_true", help="Explicit bounded paid acceptance; synthetic business data only"
    )
    parser.add_argument("--model", default=None, help="Explicit acceptance-only override, never edits .env")
    asyncio.run(main(parser.parse_args()))
