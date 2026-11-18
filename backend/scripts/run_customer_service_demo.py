"""Run the customer-service acceptance flows in an isolated container."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import httpx

import probe_missing_request_id as windows
import run_phase_b_docker as drill


@asynccontextmanager
async def server(output: Path):
    with (output / "server.log").open("ab") as log:
        process = subprocess.Popen(
            [sys.executable, "-X", "utf8", drill.__file__, "serve"], stdout=log, stderr=subprocess.STDOUT,
        )
        try:
            async with httpx.AsyncClient(trust_env=False, timeout=1) as client:
                async with asyncio.timeout(35):
                    while True:
                        if process.poll() is not None:
                            raise RuntimeError("The API exited during startup. See server.log.")
                        try:
                            response = await client.get(drill.BASE + "/health")
                            if response.is_success:
                                break
                        except httpx.RequestError:
                            pass
                        await asyncio.sleep(0.2)
            yield
        finally:
            process.terminate()
            try:
                await asyncio.to_thread(process.wait, 10)
            except subprocess.TimeoutExpired:
                process.kill()
                await asyncio.to_thread(process.wait)


def emit(file: Path, record: dict) -> None:
    with file.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")


async def diagnostic_demo(output: Path) -> None:
    clarification = {
        "matching_window": ("哪项操作", "接口路径", "时区"),
        "empty_window": ("时区", "状态码"),
        "corrected_window": ("时区", "时区", "哪个时区"),
    }
    expected_times = (
        datetime(2026, 11, 18, 9, 25, tzinfo=timezone.utc),
        datetime(2026, 11, 18, 9, 35, tzinfo=timezone.utc),
    )
    for (scenario, turns), account in zip(
        windows.probe.SCENARIOS.items(), ("trace-down-1", "trace-down-2", "billing-1"), strict=True,
    ):
        async with drill.customer(account) as (client, token):
            for index, question in enumerate(turns, 1):
                events = []
                result = await drill.completed_chat(client, token, question, events)
                early = index < len(turns)
                tool_calls = [event for event in events if event.get("status") == "executing"
                              and event["type"] == "tool_call"]
                record = {"scenario": scenario, "turn": index, "generationId": result["generationId"],
                          "answer": result["content"], "tools": tool_calls}
                emit(output / "diagnosis.jsonl", record)
                assert result["status"] == "COMPLETED", record
                if early:
                    assert not tool_calls and any(e["type"] == "clarification_requested" for e in events), record
                    assert clarification[scenario][index - 1] in result["content"], record
                else:
                    call, = tool_calls
                    assert call["tool"] == "query_recent_call_stats", record
                    args = call["arguments"]
                    assert args["endpoint"] == "/v1/chat" and args["window"] == "explicit", record
                    assert tuple(datetime.fromisoformat(args[name]) for name in ("start_at", "end_at")) == expected_times, record
                    assert any(e.get("tool") == call["tool"] and e.get("resultStatus") == "SUCCESS" for e in events), record
                    answer = result["content"]
                    assert all(stamp.isoformat().replace("+00:00", "Z") in answer for stamp in expected_times), record
                    expected = "未查到调用记录" if scenario == "empty_window" else "HTTP 429 有 1 条"
                    assert expected in answer, record
            assert not drill.read(await client.get("/support/handoffs")), account


async def ordinary_handoff(output: Path) -> None:
    async with drill.customer("handoff-3") as (client, token):
        events = []
        snapshot = await drill.completed_chat(client, token, "我要投诉，请转人工客服。", events)
        gid = snapshot["generationId"]
        tickets = drill.read(await client.get("/support/handoffs"))
        ticket, = tickets
        assert not ticket.get("diagnosisId"), ticket
        assert ticket["generationId"] == gid and ticket["handoffId"] in snapshot["content"], snapshot
        ledger = drill.ledger("handoff-3", gid)
        assert ledger["tickets"] == [ticket["handoffId"]], ledger
        async with httpx.AsyncClient(base_url=drill.BASE + "/api/v1", trust_env=False) as anonymous:
            denied = await anonymous.get("/support/handoffs")
            assert denied.status_code == 401, denied.status_code
        async with drill.customer("handoff-before-3") as (other, _):
            foreign = await other.get(f"/support/handoffs/{ticket['handoffId']}")
            assert foreign.status_code == 404, foreign.status_code
        emit(output / "handoff.jsonl", {"scenario": "ordinary", "generationId": gid,
                                        "handoffId": ticket["handoffId"], "anonymousRead": 401, "foreignRead": 404})


async def interrupt_after_handoff(output: Path) -> dict:
    async with drill.customer("handoff-2") as (client, token):
        events = []
        snapshot = await drill.completed_chat(
            client, token, "请求 req_phaseb_002 返回429，请排查并转人工客服。", events,
        )
        gid = snapshot["generationId"]
        receipt = json.loads((drill.DATA / f"lost-{gid}.json").read_text(encoding="utf-8"))
        assert "已创建人工工单" not in snapshot["content"] and receipt["handoffId"] not in snapshot["content"], snapshot
        assert drill.ledger("handoff-2", gid)["tickets"] == [receipt["handoffId"]], receipt
        assert (drill.read(await client.get(f"/diagnoses/{receipt['diagnosisId']}")))["status"] != "HANDED_OFF"
        record = {"scenario": "restart", "generationId": gid, **receipt}
        emit(output / "handoff.jsonl", {**record, "state": "receipt_lost"})
        return record


async def verify_restart(output: Path, record: dict) -> None:
    url = f"/diagnoses/{record['diagnosisId']}"
    body = {"generationId": record["generationId"]}
    async with drill.customer("handoff-before-2") as (foreign, _):
        response = await foreign.post(url + "/resume", json=body)
        assert response.status_code == 404, response.status_code
    async with drill.customer("handoff-2") as (owner, _):
        drill.read(await owner.post(url + "/resume", json=body))
        async with asyncio.timeout(15):
            while drill.read(await owner.get(url))["status"] != "HANDED_OFF":
                await asyncio.sleep(0.2)
        tickets = drill.read(await owner.get("/support/handoffs"))
        assert [ticket["handoffId"] for ticket in tickets] == [record["handoffId"]], tickets
        assert drill.ledger("handoff-2", record["generationId"])["tickets"] == [record["handoffId"]]
    emit(output / "handoff.jsonl", {**record, "state": "confirmed", "foreignResume": 404})


async def main(output: Path, real_model: bool) -> None:
    if drill.DB.exists():
        raise RuntimeError("Use an empty drill data directory")
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError("Use an empty evidence directory")
    drill.DATA.mkdir(parents=True, exist_ok=True)
    env = {"DATABASE_URL": f"sqlite+aiosqlite:///{drill.DB.as_posix()}", "BILLING_MCP_ENABLED": "false",
           "REDIS_ENABLED": "false", "LANGFUSE_ENABLED": "false", "PHASE_B_SKIP_MCP": "1",
           "PHASE_B_BIND_HOST": "127.0.0.1", "EMBEDDING_API_KEY": "", "DIAGNOSIS_RECOVERY_ENABLED": "true"}
    if real_model:
        if not os.environ.get("LLM_API_KEY") or not os.environ.get("LLM_MODEL") or not os.environ.get("LLM_BASE_URL"):
            raise ValueError("Set LLM_API_KEY, LLM_MODEL and LLM_BASE_URL for --real-model")
    else:
        env.update(LLM_API_KEY="local-demo-fixture", LLM_BASE_URL=drill.BASE + "/_phase_b",
                   SKILLS_SEMANTIC_ROUTING_ENABLED="true", PHASE_B_DEMO_CLASSIFIER="1")
    os.environ.update(env)
    await windows.seed_windows()
    async with server(output):
        await diagnostic_demo(output)
        await ordinary_handoff(output)
        for mode in ("handoff-before", "handoff"):
            await drill.run(mode, 1, output / "handoff.jsonl")
        interrupted = await interrupt_after_handoff(output)
    async with server(output):
        await verify_restart(output, interrupted)
    audit = [line for line in (output / "server.log").read_text(encoding="utf-8").splitlines()
             if "app.support.handoff: Handoff " in line]
    (output / "handoff-audit.log").write_text("\n".join(audit) + "\n", encoding="utf-8")
    assert any("Handoff authorized" in line and "authorization=" in line for line in audit), audit
    assert any("Handoff replay" in line and interrupted["handoffId"] in line for line in audit), audit
    emit(output / "summary.jsonl", {"status": "passed", "model": "real" if real_model else "fixture",
                                    "diagnosisTurns": 11, "handoffScenarios": 4})
    print("PASS: 11 diagnostic turns and 4 handoff scenarios", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("/evidence"))
    parser.add_argument("--real-model", action="store_true")
    options = parser.parse_args()
    asyncio.run(main(options.output, options.real_model))
