"""Replay the same cross-window conversation through authenticated HTTP/WS."""

import argparse
import asyncio
import json
from pathlib import Path
import os
import sqlite3
import subprocess
import sys
import time

from run_phase_b_docker import DATA, DB, customer, completed_chat, read


async def send(client, token, question):
    class TimedEvents(list):
        first_chunk_ms = None

        def append(self, event):
            if self.first_chunk_ms is None and event.get("type") == "chunk":
                self.first_chunk_ms = round((time.monotonic() - started) * 1000)
            super().append(event)

    started = time.monotonic()
    events = TimedEvents()
    snapshot = await completed_chat(client, token, question, events)
    entity = next(event for event in events if event["type"] == "entities_extracted")
    context = next((event for event in events if event["type"] == "context_assembled"), None)
    shadow = next((event for event in events if event["type"] == "context_shadow"), None)
    return {"entities": entity["entities"], "sources": entity["entitySources"],
            "generationId": entity["generationId"], "context": context, "answer": snapshot["content"],
            "diagnosisId": snapshot.get("diagnosisId"), "references": snapshot.get("referenceMappings"),
            "conversationId": snapshot.get("conversationId"), "shadow": shadow,
            "clientFirstChunkMs": events.first_chunk_ms,
            "tools": [event["tool"] for event in events if event["type"] == "tool_call"
                      and event.get("status") == "executing"]}


async def exercise(output: Path, *, verify: bool):
    async with customer("trace-down-1") as (client, token):
        row = {}
        row["first"] = await send(client, token, "请排查 request_id req_context_001，接口 /v1/chat，当前 API 版本 v1。")
        for n in range(11):
            await send(client, token, f"谢谢，第 {n} 段。" + "普通交流文字" * 220)
        row["resume"] = await send(client, token, "请继续排查刚才的请求。")
        row["correct"] = await send(client, token, "刚才版本说错了，确认当前 API 版本 v2。")
        row["correctedFollowUp"] = await send(client, token, "继续排查那个请求。")
        row["switch"] = await send(client, token, "换一个请求，排查 request_id req_context_002。")
        row["switchedFollowUp"] = await send(client, token, "继续排查这个请求。")
        if verify:
            row["ambiguous"] = await send(client, token, "排查 req_context_001 和 req_context_002 哪一个？")
            read(await client.post("/users/conversations"))
            row["anotherConversation"] = await send(client, token, "继续排查刚才的请求。")
    async with customer("trace-down-2") as (client, token):
        row["otherUser"] = await send(client, token, "继续排查刚才的请求。")
    output.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    if verify:
        assert row["resume"]["entities"]["request_id"] == "req_context_001", row["resume"]
        assert row["resume"]["sources"]["request_id"] == "continuation", row["resume"]
        assert row["correctedFollowUp"]["entities"]["api_version"] == "v2", row["correctedFollowUp"]
        assert row["switchedFollowUp"]["entities"]["request_id"] == "req_context_002", row["switchedFollowUp"]
        assert "api_version" not in row["switchedFollowUp"]["entities"]
        assert "endpoint" not in row["switchedFollowUp"]["entities"]
        assert "request_id" not in row["otherUser"]["entities"]
        assert "request_id" not in row["anotherConversation"]["entities"]
        assert not row["ambiguous"]["tools"] and "多个请求号" in row["ambiguous"]["answer"]
        context = row["resume"]["context"]
        assert context["recalledMessages"] == 1
        assert context["historyMessages"] + context["recalledMessages"] <= 20
        assert context["historyChars"] + context["recalledChars"] <= 12000
        assert row["first"]["diagnosisId"] == row["resume"]["diagnosisId"] != row["switch"]["diagnosisId"], row


async def cache_probe(mode, output):
    async with customer("trace-down-3") as (client, token):
        if mode == "prime":
            await send(client, token, "排查 request_id req_cache_test，当前版本 v3。")
        elif mode == "restored":
            rebuilt = await send(client, token, "继续排查刚才的请求。")
            assert rebuilt["context"]["restoredFrom"] == "database" and rebuilt["entities"]["api_version"] == "v3"
        row = await send(client, token, "继续排查刚才的请求。")
        assert row["entities"]["request_id"] == "req_cache_test"
        assert row["entities"]["api_version"] == "v3"
        assert row["context"]["restoredFrom"] == ("database" if mode == "offline" else "redis_versioned")
    output.write_text(json.dumps(row, ensure_ascii=False), encoding="utf-8")


async def billing_probe(output):
    question = "请查询我 2026-11 的账单和用量。"
    async with customer("billing-all-1") as (client, token):
        first = await send(client, token, question)
        assert "120" in first["answer"] and "mcp__billing__get_usage" in first["tools"], first
        with sqlite3.connect(DB) as db:
            changed = db.execute("UPDATE support_usage_records SET call_count=175 WHERE user_id="
                                 "(SELECT id FROM users WHERE username='billing-all-1')")
            assert changed.rowcount == 1
        second = await send(client, token, "继续查刚才账期的账单和用量。")
        assert second["entities"]["month"] == "2026-11" and second["sources"]["month"] == "continuation"
        assert "175" in second["answer"] and "mcp__billing__get_usage" in second["tools"], second
    output.write_text(json.dumps({"first": first, "afterChange": second}, ensure_ascii=False), encoding="utf-8")


async def knowledge_probe(output):
    with sqlite3.connect(DB) as db:
        changed = db.execute(
            "UPDATE document_vectors SET text_content=? WHERE user_id="
            "(SELECT id FROM users WHERE username='search-503-1')",
            ("故障演练文档规定单文件上传上限为 50 MB。压缩归档上传不适用这个限制。",),
        )
        assert changed.rowcount == 1
    async with customer("search-503-1") as (client, token):
        for n in range(11):
            await send(client, token, f"谢谢，第 {n} 段。" + "普通交流文字" * 220)
        row = await send(client, token, "按故障演练文档说明，单文件上传上限和例外是什么？")
        assert "50 MB" in row["answer"] and "压缩归档" in row["answer"], row
        assert "search_knowledge" in row["tools"] and row["references"], row
        citation = next(iter(row["references"].values()))["citationId"]
        record = read(await client.get("/documents/citation", params={"citationId": citation}))
        assert record["fileName"] == "phase-b-upload.md", record
        row["citationAccessVerified"] = True
        assert row["context"]["trimmedMessages"] > 0
    output.write_text(json.dumps(row, ensure_ascii=False), encoding="utf-8")


async def progress_probe(output, enabled):
    steps = (
        "继续排查这个请求，我已尝试降低并发。",
        "继续排查这个请求，我已尝试切换备用网关。",
        "继续排查这个请求，我已尝试调整退避间隔。",
        "继续排查这个请求，我已尝试恢复原配置，回退后请求仍然报错。",
        "继续排查这个请求，还没检查出口代理。",
    )
    async with customer("trace-down-1") as (client, token):
        await send(client, token, "请排查 request_id req_context_001，接口 /v1/chat。")
        for step in steps:
            await send(client, token, step)
        for n in range(11):
            await send(client, token, f"谢谢，第 {n} 段。" + "普通交流文字" * 220)
        result = await send(client, token, "继续排查这个请求，请列出排障进展和接下来待查的下一步。")
        visible = {key: key in result["answer"] for key in ("降低并发", "切换备用网关", "调整退避间隔", "恢复原配置", "出口代理")}
        assert result["entities"]["request_id"] == "req_context_001"
        if enabled:
            assert all(visible.values()), (visible, result)
            assert "此前反馈" in result["answer"]
        else:
            assert not visible["切换备用网关"] and not visible["出口代理"], result
        frame = result["context"]
        assert sum(frame.get(key, 0) for key in ("historyChars", "recalledChars", "progressChars")) <= 12000
        assert sum(frame.get(key, 0) for key in ("historyMessages", "recalledMessages", "progressMessages")) <= 20
    output.write_text(json.dumps({"enabled": enabled, "result": result, "stepCoverage": visible},
                                ensure_ascii=False, indent=2), encoding="utf-8")


async def rollout_probe(output, phase):
    state_path = DATA / "context-rollout.json"
    evidence = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    async with customer("trace-down-1") as (client, token):
        if phase == "shadow":
            evidence["first"] = await send(client, token, "请排查 request_id req_context_001，接口 /v1/chat，当前 API 版本 v1。")
            for n in range(11):
                await send(client, token, f"谢谢，第 {n} 段。" + "普通交流文字" * 220)
        result = evidence[phase] = await send(client, token, "请继续排查刚才的请求。")
        if phase == "shadow":
            assert not result["entities"].get("request_id") and result["context"] is None
            assert result["shadow"]["scopeDifferent"] and result["shadow"]["candidateContinued"]
            assert not any(tool == "query_call_log" for tool in result["tools"])
        elif phase in {"active", "restarted", "restored"}:
            assert result["entities"]["request_id"] == "req_context_001"
            assert result["context"] and result["shadow"] is None
        elif phase == "rollback":
            assert result["context"] is None and result["shadow"] is None
            assert not result["entities"].get("request_id")
            params = {"conversationId": evidence["first"]["conversationId"]}
            originals = read(await client.get("/users/conversation", params=params))
            assert any(item["generationId"] == evidence["first"]["generationId"] and item["role"] == "user"
                       and "req_context_001" in item["content"] for item in originals)
            evidence["originalMessagePreserved"] = True
            gate = [sys.executable, "/app/scripts/observe_rollout.py", "--state", str(DATA / "context-gate.sqlite")]
            status = subprocess.run([*gate, "status"], capture_output=True, text=True)
            hold = evidence["hold"] = json.loads(status.stdout)
            assert status.returncode == 2 and not hold["canExpandRollout"]
            assert hold["incident"]["signal"] == "context_scope_violation" and hold["pauseRollout"]
            evidence["holdStatusExitCode"] = status.returncode
    if os.environ.get("LANGFUSE_BASE_URL") and phase in {"shadow", "active", "restarted", "restored"}:
        reports = DATA / "received-traces.jsonl"
        async with asyncio.timeout(12):
            while True:
                traces = [json.loads(line) for line in reports.read_text().splitlines()] if reports.exists() else []
                if trace := next((item for item in traces if item["generationId"] == result["generationId"]), None):
                    meta = trace["context"]
                    assert meta.get("shadow_scopeDifferent" if phase == "shadow" else "inheritedFields"), trace
                    assert "req_context_001" not in json.dumps(meta) and "v1" not in json.dumps(meta)
                    result["trace"] = trace
                    break
                await asyncio.sleep(0.15)
    state_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    if output != state_path:
        output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--cache", choices=("prime", "offline", "restored"))
    parser.add_argument("--billing", action="store_true")
    parser.add_argument("--knowledge", action="store_true")
    parser.add_argument("--progress", choices=("off", "on"))
    parser.add_argument("--rollout", choices=("shadow", "active", "restarted", "rollback", "restored"))
    parser.add_argument("--output", type=Path, default=DATA / "context-drill.json")
    args = parser.parse_args()
    if args.cache:
        asyncio.run(cache_probe(args.cache, args.output))
    elif args.billing:
        asyncio.run(billing_probe(args.output))
    elif args.knowledge:
        asyncio.run(knowledge_probe(args.output))
    elif args.progress:
        asyncio.run(progress_probe(args.output, args.progress == "on"))
    elif args.rollout:
        asyncio.run(rollout_probe(args.output, args.rollout))
    else:
        asyncio.run(exercise(args.output, verify=args.verify))
