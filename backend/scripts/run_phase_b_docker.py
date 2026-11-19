"""Isolated failure drills over the customer HTTP/WebSocket and Billing MCP interfaces."""

import argparse
import asyncio
from collections import Counter
from contextlib import asynccontextmanager
import json
import logging
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys

import httpx
import websockets

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
DATA = Path(os.environ.get("PHASE_B_DATA_DIR", "/app/data")).resolve()
DB = DATA / "phase-b.sqlite"
PORT = int(os.environ.get("PHASE_B_PORT", "8000"))
BASE = f"http://127.0.0.1:{PORT}"
BALANCE = 100_000
SCENARIOS = ("disconnect", "restart", "search", "billing", "handoff",
             "first-token", "truncated", "cancel", "search-503", "search-empty",
             "billing-all", "handoff-before", "trace-down", "trace-backlog")


async def seed():
    from app.core.security import hash_password
    from app.core.time import utcnow
    from app.db.init_db import init_db
    from app.db.models import (
        DocumentVector, FileUpload, SupportApiCallLog, SupportInvoice, SupportRequestObservation,
        SupportUsageRecord, User,
    )
    from app.db.session import SessionLocal, engine
    from app.diagnosis.rules import RULE_VERSION

    await init_db()
    password = os.environ.get("PHASE_B_USER_PASSWORD") or secrets.token_urlsafe(24)
    password_hash = hash_password(password)
    llm_balance = int(os.environ.get("PHASE_B_USER_LLM_BALANCE", str(BALANCE)))
    async with SessionLocal() as db:
        for kind in SCENARIOS:
            for trial in range(1, 4):
                user = User(username=f"{kind}-{trial}", password=password_hash, role="USER",
                            llm_token_balance=llm_balance, embedding_token_balance=BALANCE)
                db.add(user)
                await db.flush()
                if kind in {"billing", "billing-all"}:
                    db.add(SupportInvoice(id=f"{kind}-invoice-{trial}", user_id=str(user.id),
                                          month="2026-11", amount=12, status="PAID"))
                    db.add(SupportUsageRecord(user_id=str(user.id), month="2026-11", call_count=120))
                if kind in {"search", "search-503", "search-empty"}:
                    md5 = f"{user.id:032x}"
                    db.add(FileUpload(user_id=str(user.id), file_md5=md5, file_name="phase-b-upload.md",
                                      status=1, process_status="COMPLETED", active_vector_version="phase-b"))
                    db.add(DocumentVector(user_id=str(user.id), file_md5=md5, chunk_id=1, page_number=1,
                                          text_content="演练文档规定单文件上传上限为 50 MB。",
                                          vector_version="phase-b", model_version="phase-b-fixture",
                                          vector_json="[1.0,0.0,0.0,0.0]"))
                if kind in {"handoff", "handoff-before"}:
                    request_id = f"req_phase{'b' if kind == 'handoff' else 'pre'}_{trial:03d}"
                    db.add(SupportApiCallLog(
                        request_id=request_id, user_id=str(user.id), app_id="app_phaseb",
                        endpoint="/v1/chat", http_status=429, created_at=utcnow(),
                    ))
                    db.add(SupportRequestObservation(
                        request_id=request_id, user_id=str(user.id), service_id="demo-api",
                        rule_version=RULE_VERSION, observations_json=json.dumps(
                            {"limiterKind": "RATE", "rateObserved": 11, "rateLimit": 10}),
                    ))
                if os.environ.get("PHASE_B_SEED_CONTEXT") == "1" and kind == "trace-down" and trial == 1:
                    for suffix in ("001", "002"):
                        request_id = f"req_context_{suffix}"
                        db.add(SupportApiCallLog(request_id=request_id, user_id=str(user.id), app_id="app_context",
                                                 endpoint="/v1/chat", http_status=429, created_at=utcnow()))
                        db.add(SupportRequestObservation(
                            request_id=request_id, user_id=str(user.id), service_id="demo-api", rule_version=RULE_VERSION,
                            observations_json=json.dumps({"limiterKind": "RATE", "rateObserved": 11, "rateLimit": 10}),
                        ))
        await db.commit()
    (DATA / "user-password").write_text(password, encoding="utf-8")
    await engine.dispose()


def sse(delta=None, usage=None):
    return "data: " + json.dumps(
        {"choices": [{"delta": delta}] if delta else [], "usage": usage}, ensure_ascii=False,
    ) + "\n\n"


def serve():
    import uvicorn
    from fastapi.responses import JSONResponse, StreamingResponse
    from app.accounting.usage import usage_service
    from app.main import app
    from app.support import handoff

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if os.environ.get("DATABASE_URL") != f"sqlite+aiosqlite:///{DB.as_posix()}":
        raise RuntimeError("The failure harness requires its own isolated SQLite database")
    if not DB.exists():
        asyncio.run(seed())
    elif not (DATA / "user-password").is_file():
        raise RuntimeError("Existing database is missing the isolated drill seed marker")
    original_attach = handoff.attach_diagnostic_handoff

    async def lose_receipt_after_commit(db, row):
        marker = DATA / f"lost-{row.generation_id}.json"
        if row.diagnosis_id and not marker.exists() and not (DATA / "normal-handoff").exists():
            marker.write_text(json.dumps({"handoffId": row.handoff_id, "diagnosisId": row.diagnosis_id}),
                              encoding="utf-8")
            raise OSError("phase_b_post_commit_receipt_lost")
        return await original_attach(db, row)

    handoff.attach_diagnostic_handoff = lose_receipt_after_commit
    original_release = usage_service.release_llm

    async def fail_first_recovery_release(db, generation_id, reason, **kwargs):
        trigger = DATA / "fail-recovery-release"
        if reason == "server_restart_recovery" and trigger.exists():
            trigger.unlink()
            (DATA / f"recovery-failure-{generation_id}").touch()
            raise OSError("phase_b_restart_during_reservation_recovery")
        return await original_release(db, generation_id, reason, **kwargs)

    usage_service.release_llm = fail_first_recovery_release

    @app.post("/_phase_b/embeddings")
    async def stalled_embedding(payload: dict):
        if (DATA / "search-503").exists():
            return JSONResponse({"error": "fixture unavailable"}, status_code=503)
        if (DATA / "timeout-search").exists():
            await asyncio.sleep(10)
        return {"data": [{"index": i, "embedding": [1.0, 0.0, 0.0, 0.0]}
                         for i, _ in enumerate(payload["input"])]}

    @app.post("/_phase_b/chat/completions")
    async def fixture_model(payload: dict):
        last = payload["messages"][-1]["content"]
        if os.environ.get("PHASE_B_DEMO_CLASSIFIER") == "1" and payload.get("stream") is False:
            questions = [message["content"] for message in payload["messages"] if message["role"] == "user"]
            diagnostic = any(
                marker in question for question in questions
                for marker in ("接口一直失败", "/v1/", "请求号", "req_phase")
            )
            classification = {
                "intent": "api_diagnostic" if diagnostic else "general",
                "skills": ["api-diagnostic"] if diagnostic else [],
                "diagnostic_scope": (
                    "unspecified" if last == "我的接口一直失败，帮我查原因。" else "incident" if diagnostic else "none"
                ),
                "confidence": 1.0,
                "needs_human": "转人工" in last,
                "is_follow_up": len(questions) > 1,
                "entities": {},
            }
            return {"choices": [{"message": {"content": json.dumps(classification)}}],
                    "usage": {"prompt_tokens": 7, "completion_tokens": 4, "total_tokens": 11}}
        answer_input = {}
        try:
            answer_input = json.loads(last)
        except (TypeError, ValueError):
            pass

        async def respond():
            tools = {tool["function"]["name"] for tool in payload.get("tools") or ()}
            if tools:
                if "故障演练" in last and "search_knowledge" in tools:
                    calls = {"search_knowledge": {"query": last}}
                elif "账单" in last and "用量" in last and "mcp__billing__get_invoice" in tools:
                    calls = {name: {"month": "2026-11"} for name in
                             ("mcp__billing__get_invoice", "mcp__billing__get_usage")}
                else:
                    calls = {}
                yield sse({"tool_calls": [
                    {"index": i, "id": f"fixture-{i}", "function": {"name": name, "arguments": json.dumps(args)}}
                    for i, (name, args) in enumerate(calls.items())
                ]})
            else:
                question = answer_input.get("question", "") if isinstance(answer_input, dict) else ""
                if question in {"你好", "谢谢"}:
                    if (DATA / "first-token").exists():
                        (DATA / "first-token").unlink()
                        (DATA / "first-token-injected").touch()
                        await asyncio.sleep(10)
                    yield sse({"content": "收到。\n"})
                    if (DATA / "truncated").exists():
                        return
                    while (DATA / "pause-model").exists():
                        await asyncio.sleep(0.05)
                    reply = "可以继续。"
                else:
                    reply = "当前依赖未返回可用证据，暂时无法确认。"
                    for excerpt in (answer_input.get("evidenceSummary") or {}).get("knowledgeExcerpts", ()):
                        number = excerpt["source"]["referenceNumber"]
                        reply = f"{excerpt['text']}（来源#{number}）"
                        break
                yield sse({"content": reply})
            yield sse(usage={"prompt_tokens": 7, "completion_tokens": 4, "total_tokens": 11})
            yield "data: [DONE]\n\n"

        return StreamingResponse(respond(), media_type="text/event-stream")

    mcp_child = None if os.environ.get("PHASE_B_SKIP_MCP") == "1" else subprocess.Popen(
        [sys.executable, __file__, "mcp"]
    )
    try:
        uvicorn.run(app, host=os.environ.get("PHASE_B_BIND_HOST", "127.0.0.1"), port=PORT, access_log=False)
    finally:
        if mcp_child:
            mcp_child.terminate()
            mcp_child.wait(timeout=10)


def mcp():
    from app.support import billing
    from app.tools.mcp.billing_server import mcp

    query_usage = billing.query_usage
    query_bill = billing.query_bill

    async def timeout_usage(*args, **kwargs):
        if (DATA / "timeout-billing").exists() or (DATA / "billing-all").exists():
            await asyncio.sleep(10)
        return await query_usage(*args, **kwargs)

    billing.query_usage = timeout_usage

    async def timeout_bill(*args, **kwargs):
        if (DATA / "billing-all").exists():
            await asyncio.sleep(10)
        return await query_bill(*args, **kwargs)

    billing.query_bill = timeout_bill
    mcp.run("streamable-http", host="127.0.0.1", port=8011, stateless_http=True, json_response=True)


def collector_app():
    from fastapi import FastAPI, Request
    from fastapi.responses import Response
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest

    receiver = FastAPI()

    @receiver.post("/api/public/otel/v1/traces")
    async def receive(request: Request):
        payload = ExportTraceServiceRequest.FromString(await request.body())
        if (DATA / "trace-backlog").exists():
            (DATA / "collector-blocked").touch()
            while (DATA / "trace-backlog").exists():
                await asyncio.sleep(0.05)
        with (DATA / "received-traces.jsonl").open("a") as stream:
            for resource in payload.resource_spans:
                for scope in resource.scope_spans:
                    for span in scope.spans:
                        for attr in span.attributes:
                            if attr.key == "langfuse.trace.metadata.generation_id":
                                event = {"generationId": attr.value.string_value, "traceId": span.trace_id.hex()}
                                prefix = "langfuse.trace.metadata.context_"
                                context = {item.key.removeprefix(prefix): getattr(item.value, item.value.WhichOneof("value"))
                                           for item in span.attributes if item.key.startswith(prefix)
                                           and item.value.WhichOneof("value") in
                                           {"int_value", "bool_value", "double_value", "string_value"}}
                                if context:
                                    event["context"] = context
                                stream.write(json.dumps(event) + "\n")
        return Response(content=b"", media_type="application/x-protobuf")

    return receiver


def collector():
    import uvicorn

    uvicorn.run(collector_app(), host="127.0.0.1", port=8012, log_level="warning")


def read(response):
    response.raise_for_status()
    return response.json()["data"]


@asynccontextmanager
async def customer(name):
    async with httpx.AsyncClient(base_url=BASE + "/api/v1", trust_env=False) as client:
        password = (DATA / "user-password").read_text(encoding="utf-8")
        token = read(await client.post("/users/login", json={"username": name, "password": password}))["token"]
        client.headers["Authorization"] = "Bearer " + token
        yield client, token


@asynccontextmanager
async def socket_for(token):
    async with websockets.connect(f"ws://127.0.0.1:{PORT}/chat", proxy=None) as socket:
        await socket.send(json.dumps({"type": "auth", "token": token}))
        assert json.loads(await socket.recv())["type"] == "connection"
        yield socket


async def until(socket, kind, events):
    async with asyncio.timeout(50):
        while True:
            event = json.loads(await socket.recv())
            events.append(event)
            if event.get("type") == kind:
                return event
            if "error" in event and "type" not in event:
                raise AssertionError(event)


def ledger(name, generation):
    with sqlite3.connect(DB) as db:
        db.row_factory = sqlite3.Row
        user = db.execute("SELECT id,llm_token_balance FROM users WHERE username=?", (name,)).fetchone()
        reservation = db.execute("SELECT status, settled_tokens, reserved_tokens FROM llm_token_reservations "
                                 "WHERE generation_id=?", (generation,)).fetchone()
        records = db.execute("SELECT change_type, amount FROM user_token_record "
                             "WHERE user_id=? AND token_type='LLM' AND remark LIKE ?",
                             (str(user["id"]), "%:" + generation)).fetchall()
        messages = db.execute("SELECT role FROM conversation_messages WHERE generation_id=?", (generation,)).fetchall()
        tickets = db.execute("SELECT handoff_id FROM support_handoffs WHERE user_id=?", (str(user["id"]),)).fetchall()
    return {"reservation": dict(reservation) if reservation else None,
            "records": [dict(record) for record in records], "balance": user["llm_token_balance"],
            "messages": dict(Counter(row["role"] for row in messages)), "tickets": [row[0] for row in tickets]}


def assert_accounting(data, *, interrupted=False, prior_debit=0):
    reservation = data["reservation"]
    assert reservation["status"] == ("RELEASED" if interrupted else "SETTLED"), data
    consumed = [row for row in data["records"] if row["change_type"] == "CONSUME"]
    assert len(consumed) == (0 if interrupted else 1), data
    charge = sum(-row["amount"] for row in consumed)
    assert charge == reservation["settled_tokens"] and data["balance"] == BALANCE - prior_debit - charge, data
    assert data["messages"] == ({"user": 1} if interrupted else {"user": 1, "assistant": 1}), data
    return charge


async def generation(client, generation_id):
    return read(await client.get(f"/chat/generation/{generation_id}"))


async def completed_chat(client, token, question, events):
    async with socket_for(token) as socket:
        await socket.send(question)
        gid = (await until(socket, "start", events))["generationId"]
        receipt = await until(socket, "completion", events)
    snapshot = await generation(client, gid)
    assert snapshot["status"] == "COMPLETED" and receipt["content"] == snapshot["content"]
    assert receipt["referenceMappings"] == snapshot["referenceMappings"]
    return snapshot


async def trace_drill(mode, name, client, token, row):
    flag = DATA / "trace-backlog"
    blocked = DATA / "collector-blocked"
    reports = DATA / "received-traces.jsonl"
    blocked.unlink(missing_ok=True)

    def trace_for(gid):
        return next((record for line in reports.read_text().splitlines()
                     if (record := json.loads(line))["generationId"] == gid), None) if reports.exists() else None

    def start_receiver():
        return subprocess.Popen([sys.executable, __file__, "collector"])

    receiver = None
    try:
        if mode == "trace-backlog":
            flag.touch()
            receiver = start_receiver()
            await asyncio.sleep(1)
        start = asyncio.get_running_loop().time()
        snapshot = row["snapshot"] = await completed_chat(client, token, "你好", row["events"])
        row["ledger"] = ledger(name, snapshot["generationId"])
        prior_debit = assert_accounting(row["ledger"])
        async with asyncio.timeout(8):
            if mode == "trace-backlog":
                while not blocked.exists():
                    await asyncio.sleep(0.05)
                row["backlog"] = []
                for _ in range(3):
                    events = []
                    item = await completed_chat(client, token, "谢谢", events)
                    account = ledger(name, item["generationId"])
                    prior_debit += assert_accounting(account, prior_debit=prior_debit)
                    assert not account["tickets"]
                    row["backlog"].append({"generation": item, "ledger": account, "events": events})
                assert blocked.exists() and flag.exists()
                assert not any(trace_for(item["generation"]["generationId"]) for item in row["backlog"])
            else:
                try:
                    await asyncio.open_connection("127.0.0.1", 8012)
                except ConnectionRefusedError:
                    row["receiverConnectionRefused"] = True
                else:
                    raise AssertionError("Receiver was reachable during the outage")
                await asyncio.sleep(4)
            assert trace_for(snapshot["generationId"]) is None
        row["secondsWithoutTrace"] = asyncio.get_running_loop().time() - start
        flag.unlink(missing_ok=True)
        if receiver is None:
            receiver = start_receiver()
        await asyncio.sleep(4)
        recovered = row["recovered"] = await completed_chat(client, token, "谢谢", row.setdefault("recoveryEvents", []))
        row["recoveryLedger"] = ledger(name, recovered["generationId"])
        assert_accounting(row["recoveryLedger"], prior_debit=prior_debit)
        assert not row["ledger"]["tickets"] and not row["recoveryLedger"]["tickets"]
        async with asyncio.timeout(8):
            while not (receipt := trace_for(recovered["generationId"])):
                await asyncio.sleep(0.1)
        row["traceReceipt"] = receipt
        row["missingAfterRecovery"] = [
            gid for gid in [snapshot["generationId"], *(item["generation"]["generationId"]
                 for item in row.get("backlog", []))] if not trace_for(gid)
        ]
    finally:
        flag.unlink(missing_ok=True)
        if receiver is not None:
            receiver.terminate()
            receiver.wait(timeout=5)


async def remaining_business_drill(mode, trial, name, client, token, row):
    search = mode.startswith("search-")
    handoff = mode == "handoff-before"
    marker = DATA / mode
    if mode == "search-empty":
        with sqlite3.connect(DB) as db:
            db.execute("UPDATE document_vectors SET model_version='phase-b-incompatible' WHERE user_id="
                       "(SELECT id FROM users WHERE username=?)", (name,))
    elif handoff:
        with sqlite3.connect(DB) as db:
            db.execute("CREATE TRIGGER phase_b_reject_handoff BEFORE INSERT ON support_handoffs "
                       "BEGIN SELECT RAISE(ABORT, 'phase_b_before_commit'); END")
        (DATA / "normal-handoff").touch()
    else:
        marker.touch()
    question = ("按文档说明查询故障演练的上传上限。" if search else
                f"请求 req_phasepre_{trial:03d} 返回429，请排查并转人工客服。" if handoff else
                "请查询我 2026-11 的账单和用量。")
    try:
        snapshot = row["snapshot"] = await completed_chat(client, token, question, row["events"])
        row["ledger"] = ledger(name, snapshot["generationId"])
        assert_accounting(row["ledger"])
        assert not row["ledger"]["tickets"]
        public = [snapshot["content"], *(event.get("chunk") or event.get("content") or ""
                  for event in row["events"] if event["type"] in {"chunk", "answer_replace", "completion"})]
        if search:
            assert not snapshot["referenceMappings"] and all("来源#" not in text for text in public), public
            expected = "暂不可用" if mode == "search-503" else "未找到"
            assert expected in snapshot["content"], snapshot
        elif handoff:
            assert "工单" in snapshot["content"] and "未能确认" in snapshot["content"], snapshot
            assert all("已创建人工工单" not in text and "已成功转人工" not in text for text in public), public
        else:
            outcomes = {event.get("tool"): event.get("resultStatus") for event in row["events"]
                        if event.get("resultStatus")}
            assert all(outcomes.get("mcp__billing__get_" + item) == "TIMEOUT"
                       for item in ("invoice", "usage")), outcomes
            assert snapshot["content"].count("暂时无法核实") == 2, snapshot
            assert all("为12" not in text and "为120" not in text for text in public), public
    finally:
        marker.unlink(missing_ok=True)
        with sqlite3.connect(DB) as db:
            if handoff:
                db.execute("DROP TRIGGER IF EXISTS phase_b_reject_handoff")
            elif mode == "search-empty":
                db.execute("UPDATE document_vectors SET model_version='phase-b-fixture' WHERE user_id="
                           "(SELECT id FROM users WHERE username=?)", (name,))
    recovery_events = row["recoveryEvents"] = []
    try:
        recovered = row["recovered"] = await completed_chat(client, token, question, recovery_events)
    finally:
        if handoff:
            (DATA / "normal-handoff").unlink(missing_ok=True)
    row["recoveryLedger"] = ledger(name, recovered["generationId"])
    assert_accounting(row["recoveryLedger"], prior_debit=row["ledger"]["reservation"]["settled_tokens"])
    if handoff:
        tickets = row["recoveryLedger"]["tickets"]
        assert len(tickets) == 1 and tickets[0] in recovered["content"], recovered
        assert [ticket["handoffId"] for ticket in read(await client.get("/support/handoffs"))] == tickets
    else:
        assert not row["recoveryLedger"]["tickets"]
        if search:
            assert "50 MB" in recovered["content"] and recovered["referenceMappings"], recovered
        else:
            assert "金额为12" in recovered["content"] and "用量为120" in recovered["content"], recovered


async def exercise(mode, trial, row):
    scenario = "restart" if mode == "after-restart" else mode
    name = f"{scenario}-{trial}"
    events = row["events"]
    marker = DATA / f"restart-{trial}.json"
    pause = DATA / "pause-model"
    async with customer(name) as (client, token):
        if mode in {"trace-down", "trace-backlog"}:
            await trace_drill(mode, name, client, token, row)
            return
        if mode in {"search-503", "search-empty", "billing-all", "handoff-before"}:
            await remaining_business_drill(mode, trial, name, client, token, row)
            return
        if mode == "after-restart":
            before = json.loads(marker.read_text(encoding="utf-8"))
            gid = before["generationId"]
            snapshot = row["interrupted"] = await generation(client, gid)
            row["recoveryFaultInjected"] = (DATA / f"recovery-failure-{gid}").exists()
            assert row["recoveryFaultInjected"], "The second failure was not injected"
            assert snapshot["status"] == "INTERRUPTED" and snapshot["content"] == before["content"], snapshot
            row["interruptedLedger"] = ledger(name, gid)
            assert_accounting(row["interruptedLedger"], interrupted=True)
            active = await client.get("/chat/active-generation")
            active.raise_for_status()
            assert active.json().get("data") is None, active.json()
            pause.unlink(missing_ok=True)

        if mode in {"disconnect", "restart"}:
            pause.touch()
        if mode == "cancel":
            pause.touch()
        if mode in {"first-token", "truncated"}:
            (DATA / mode).touch()
        timeout_flag = DATA / f"timeout-{mode}"
        if mode in {"search", "billing"}:
            timeout_flag.touch()
        question = {
            "disconnect": "你好", "restart": "你好", "after-restart": "谢谢",
            "first-token": "你好", "truncated": "你好", "cancel": "你好",
            "search": "按文档说明查询故障演练的上传上限。",
            "billing": "请查询我 2026-11 的账单和用量。",
            "handoff": f"请求 req_phaseb_{trial:03d} 返回429，请排查并转人工客服。",
        }[mode]
        async with socket_for(token) as socket:
            await socket.send(question)
            gid = (await until(socket, "start", events))["generationId"]
            row["generationId"] = gid
            if mode == "cancel":
                await until(socket, "chunk", events)
                stop = json.dumps({"type": "stop", "generationId": gid})
                async with customer(f"disconnect-{trial}") as (_, other_token), socket_for(other_token) as other:
                    await other.send(stop)
                    denied = row["foreignStop"] = json.loads(await asyncio.wait_for(other.recv(), 5))
                    assert denied.get("code") == 404, denied
                assert (await generation(client, gid))["status"] == "STREAMING"
                await socket.send(stop)
                await until(socket, "stop", events)
                pause.unlink()
            elif mode == "truncated":
                async with asyncio.timeout(10):
                    while True:
                        event = json.loads(await socket.recv())
                        events.append(event)
                        assert event.get("type") != "completion", event
                        if event.get("code") == 500:
                            assert "中断" in event["error"], event
                            break
                (DATA / mode).unlink()
            elif mode in {"disconnect", "restart"}:
                await until(socket, "chunk", events)
                async with asyncio.timeout(5):
                    while not (before := await generation(client, gid))["content"]:
                        await asyncio.sleep(0.05)
                assert before["status"] == "STREAMING", before
                assert ledger(name, gid)["reservation"]["status"] == "RESERVED"
                row["checkpoint"] = before
                if mode == "restart":
                    marker.write_text(json.dumps(before, ensure_ascii=False), encoding="utf-8")
                    return
            else:
                await until(socket, "completion", events)

        if mode == "disconnect":
            async with socket_for(token) as socket:
                resumed = await until(socket, "resume", events)
                assert resumed["generationId"] == gid and resumed["content"] == before["content"], resumed
                pause.unlink()
                await until(socket, "completion", events)

        snapshot = row["snapshot"] = await generation(client, gid)
        if mode in {"cancel", "truncated"}:
            assert snapshot["status"] == ("CANCELLED" if mode == "cancel" else "FAILED"), snapshot
            assert "收到。" in snapshot["content"], snapshot
            row["ledger"] = ledger(name, gid)
            assert_accounting(row["ledger"], interrupted=True)
            assert not row["ledger"]["tickets"]
            assert not any(event.get("type") == "completion" for event in events), events
            async with socket_for(token) as retry:
                await retry.send("谢谢")
                new_gid = (await until(retry, "start", row.setdefault("recoveryEvents", [])))["generationId"]
                await until(retry, "completion", row["recoveryEvents"])
            row["recovered"] = await generation(client, new_gid)
            assert row["recovered"]["status"] == "COMPLETED" and new_gid != gid
            row["recoveryLedger"] = ledger(name, new_gid)
            assert_accounting(row["recoveryLedger"])
            return
        assert snapshot["status"] == "COMPLETED", snapshot
        assert sum(event.get("type") == "completion" for event in events) == 1
        row["ledger"] = ledger(name, gid)
        assert_accounting(row["ledger"])
        if mode == "first-token":
            assert (DATA / "first-token-injected").exists()
            (DATA / "first-token-injected").unlink()
            assert snapshot["content"].count("收到。") == 1 and "可以继续。" in snapshot["content"]
            assert row["ledger"]["reservation"]["settled_tokens"] == 11
        if mode in {"disconnect", "after-restart"}:
            assert row["ledger"]["reservation"]["settled_tokens"] == 11
        if mode == "search":
            assert any(event.get("tool") == "search_knowledge" and event.get("resultStatus") == "TIMEOUT"
                       for event in events), events
            assert "无法确认" in snapshot["content"] and "来源#" not in snapshot["content"], snapshot
        if mode == "billing":
            assert any(event.get("tool") == "mcp__billing__get_invoice" and event.get("resultStatus") == "SUCCESS"
                       for event in events), events
            assert any(event.get("tool") == "mcp__billing__get_usage" and event.get("resultStatus") in {"TIMEOUT", "ERROR"}
                       for event in events), events
            assert "金额为12" in snapshot["content"] and "暂时无法核实" in snapshot["content"], snapshot
        if mode == "handoff":
            receipt = json.loads((DATA / f"lost-{gid}.json").read_text(encoding="utf-8"))
            assert receipt["diagnosisId"] == snapshot["diagnosisId"], receipt
            assert receipt["handoffId"] not in snapshot["content"] and "已创建人工工单" not in snapshot["content"], snapshot
            public_text = "".join(event.get("chunk", "") for event in events if event["type"] == "chunk")
            assert receipt["handoffId"] not in public_text and "已创建人工工单" not in public_text, public_text
            assert row["ledger"]["tickets"] == [receipt["handoffId"]]
            url = f"/diagnoses/{receipt['diagnosisId']}"
            retry_started = asyncio.get_running_loop().time()
            row["retries"] = await asyncio.gather(*(
                client.post(url + "/resume", json={"generationId": gid}) for _ in range(3)
            ), return_exceptions=False)
            row["retries"] = [read(response) for response in row["retries"]]
            async with asyncio.timeout(50):
                while (detail := read(await client.get(url)))["status"] != "HANDED_OFF":
                    await asyncio.sleep(0.25)
            row["handoffRecoverySeconds"] = asyncio.get_running_loop().time() - retry_started
            row["diagnosis"] = detail
            tickets = row["handoffs"] = read(await client.get("/support/handoffs"))
            assert [ticket["handoffId"] for ticket in tickets] == [receipt["handoffId"]], tickets
            assert ledger(name, gid) == row["ledger"]
        else:
            assert not row["ledger"]["tickets"], row["ledger"]
        if mode in {"search", "billing"}:
            timeout_flag.unlink()
            recovery_events = row["recoveryEvents"] = []
            async with socket_for(token) as socket:
                await socket.send(question)
                new_gid = (await until(socket, "start", recovery_events))["generationId"]
                await until(socket, "completion", recovery_events)
            assert new_gid != gid
            recovered = row["recovered"] = await generation(client, new_gid)
            assert recovered["status"] == "COMPLETED", recovered
            row["recoveryLedger"] = ledger(name, new_gid)
            assert_accounting(row["recoveryLedger"], prior_debit=row["ledger"]["reservation"]["settled_tokens"])
            if mode == "search":
                assert "50 MB" in recovered["content"] and recovered["referenceMappings"], recovered
            else:
                assert "金额为12" in recovered["content"] and "用量为120" in recovered["content"], recovered


async def run(mode, trial, output):
    row = {"scenario": mode, "trial": trial, "events": [], "passed": False}
    try:
        await exercise(mode, trial, row)
        row["passed"] = True
    except Exception as error:
        row["error"] = repr(error)
        raise
    finally:
        with output.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"{mode} {trial}: passed", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("serve", "mcp", "collector", "after-restart", *SCENARIOS))
    parser.add_argument("--trial", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--output", type=Path, default=DATA / "phase-b-results.jsonl")
    args = parser.parse_args()
    if args.mode == "serve":
        serve()
    elif args.mode == "mcp":
        mcp()
    elif args.mode == "collector":
        collector()
    else:
        asyncio.run(run(args.mode, args.trial, args.output))
