"""Phase A smoke acceptance through HTTP and WebSocket inside an isolated Docker container."""

import argparse
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import secrets
import sys
import time

import httpx
import websockets

sys.path.insert(0, "/app")

from run_phase_a_graph import load_cases
from app.evaluation.answer import evaluate_answer
from app.evaluation.customer_service import evaluate_customer_service_case


PAIRS = {
    "document-account-02", "rate-limit-02", "scope-05",
    "billing-03", "handoff-privacy-02", "citation-mixed-01",
}
BASE_URL = "http://127.0.0.1:8000"
DB_PATH = Path("/app/data/phase-a.sqlite")
VECTOR = [1.0, 0.0, 0.0, 0.0]
EVIDENCE_METADATA = {
    "rate-limit.md": {"knowledge_category": "rate_limit", "knowledge_error_code": "RATE_LIMIT_EXCEEDED"},
    "429-cite.md": {"knowledge_category": "rate_limit", "knowledge_error_code": "429"},
    "plans.md": {"knowledge_plan": "Professional"},
}


def selected_cases():
    return [case for _, case in load_cases() if case["id"][8:].rsplit("-", 1)[0] in PAIRS]


async def seed(password):
    from sqlalchemy import text

    from app.core.security import hash_password
    from app.db.init_db import init_db
    from app.db.models import DocumentVector, FileUpload, SupportPlan, SupportSubscription, User
    from app.db.session import SessionLocal, engine

    if DB_PATH.exists() or os.environ.get("DATABASE_URL") != "sqlite+aiosqlite:////app/data/phase-a.sqlite":
        raise RuntimeError("Acceptance requires a fresh isolated SQLite database")
    await init_db()
    password_hash = hash_password(password)
    async with SessionLocal() as db:
        for case in selected_cases():
            user = User(username=case["id"], password=password_hash, role="USER",
                        llm_token_balance=100000, embedding_token_balance=100000)
            db.add(user)
            await db.flush()
            owner = str(user.id)
            for evidence in case.get("evidence", ()):
                db.add(FileUpload(
                    user_id=owner, file_md5=evidence["fileMd5"], file_name=evidence["fileName"],
                    status=1, process_status="COMPLETED", active_vector_version="acceptance",
                    **EVIDENCE_METADATA.get(evidence["fileName"], {}),
                ))
                db.add(DocumentVector(
                    user_id=owner, file_md5=evidence["fileMd5"], chunk_id=evidence["chunkId"],
                    page_number=evidence["pageNumber"], text_content=evidence["textContent"],
                    vector_version="acceptance", model_version="phase-a-test-embedding",
                    vector_json=json.dumps(VECTOR),
                ))
            plan = (case.get("fixtures") or {}).get("toolResults", {}).get("query_plan", {}).get("data", {})
            if plan.get("found"):
                db.add(SupportPlan(
                    id="phase-a-plan", name=plan["planName"], qps_limit=plan["qpsLimit"],
                    monthly_quota=plan["monthlyQuota"], base_price=plan["basePrice"],
                    overage_price_per_call=plan["overagePricePerCall"],
                ))
                db.add(SupportSubscription(user_id=owner, plan_id="phase-a-plan", status=plan["subscriptionStatus"]))
            if case["id"].endswith("handoff-privacy-02-restrict"):
                await db.execute(text(
                    "CREATE TRIGGER phase_a_reject_handoff BEFORE INSERT ON support_handoffs "
                    f"WHEN NEW.user_id = '{int(owner)}' "
                    "BEGIN SELECT RAISE(ABORT, 'phase_a_simulated_write_failure'); END"
                ))
        await db.commit()
    await engine.dispose()


def serve():
    import uvicorn
    from app.main import app

    @app.post("/_acceptance/embeddings")
    async def fixed_embeddings(payload: dict):
        return {"data": [{"index": i, "embedding": VECTOR} for i, _ in enumerate(payload["input"])]}

    password = secrets.token_urlsafe(24)
    asyncio.run(seed(password))
    (DB_PATH.parent / "acceptance-password").write_text(password, encoding="utf-8")
    uvicorn.run(app, host="127.0.0.1", port=8000, access_log=False)


def read(response):
    response.raise_for_status()
    value = response.json()
    assert "data" in value, value
    return value["data"]


async def run_case(case, password, row):
    started = time.monotonic()
    async with httpx.AsyncClient(base_url=BASE_URL + "/api/v1", trust_env=False) as client:
        login = read(await client.post("/users/login", json={"username": case["id"], "password": password}))
        token = login["token"]
        client.headers["Authorization"] = "Bearer " + token
        conversation = read(await client.post("/users/conversations"))["conversationId"]
        read(await client.put(f"/users/conversations/{conversation}/switch"))
        events = row["events"]
        async with websockets.connect("ws://127.0.0.1:8000/chat", proxy=None, max_size=8 * 1024 * 1024) as socket:
            await socket.send(json.dumps({"type": "auth", "token": token}))
            assert json.loads(await socket.recv())["type"] == "connection"
            await socket.send(case["question"])
            async with asyncio.timeout(90):
                while True:
                    event = json.loads(await socket.recv())
                    events.append(event)
                    if event.get("type") == "error" or ("error" in event and "type" not in event):
                        raise RuntimeError(str(event))
                    if event.get("type") == "completion":
                        generation = event["generationId"]
                        break
        snapshot = row["snapshot"] = read(await client.get("/chat/generation/" + generation))
        assert snapshot["conversationId"] == conversation and snapshot["status"] == "COMPLETED", snapshot
        calls = {}
        for event in events:
            if event.get("type") != "tool_call":
                continue
            call = calls.setdefault(event["toolCallId"], {"id": event["toolCallId"], "name": event["tool"]})
            if event["status"] == "executing":
                call.update(arguments=event["arguments"], step=event["agentStep"])
            else:
                call.update(status=event["resultStatus"], error=event.get("error"), durationMs=event.get("durationMs"))
        trace = next(event["trace"] for event in reversed(events) if event.get("type") == "skill_trace")
        refs = snapshot.get("referenceMappings") or {}
        artifacts = row["artifact"] = {
            "answer": snapshot["content"], "references": refs, "toolCalls": list(calls.values()),
            "trace": trace, "timing": {"totalMs": (time.monotonic() - started) * 1000},
        }
        row["citations"] = []
        sources = {(item["fileMd5"], item["chunkId"]): item for item in case.get("evidence", ())}
        for number, ref in refs.items():
            citation = await client.get("/documents/citation", params={"citationId": ref["citationId"]})
            data = read(citation)
            assert data["fileMd5"] == ref["fileMd5"] and data["chunkId"] == ref["chunkId"], data
            expected_source = sources[(data["fileMd5"], data["chunkId"])]
            assert (data["pageNumber"], data["textContent"]) == (expected_source["pageNumber"], expected_source["textContent"])
            row["citations"].append({"referenceNumber": number, "source": data})
        handoffs = row["handoffs"] = read(await client.get("/support/handoffs"))
        grading_case = deepcopy(case)
        if case["id"].endswith("handoff-privacy-02-allow"):
            assert len(handoffs) == 1 and handoffs[0]["generationId"] == generation, handoffs
            receipt = trace["handoffResult"]
            assert receipt["success"] and receipt["handoffId"] == handoffs[0]["handoffId"], receipt
            # The fixture's placeholder is replaced by the confirmed receipt for this generation.
            grading_case["rubric"]["requiredFacts"][0]["anyOf"] = [receipt["handoffId"]]
        else:
            assert not handoffs, handoffs
        if case["id"].endswith(("document-account-02-restrict", "citation-mixed-01-restrict")):
            assert "无法确认" in snapshot["content"], snapshot
        if case["id"].endswith("handoff-privacy-02-restrict"):
            assert "未能确认人工工单创建成功" in snapshot["content"], snapshot
            assert "退款" not in snapshot["content"], snapshot
            assert trace["handoffResult"]["attempted"] and not trace["handoffResult"]["success"]
            assert any(call["name"] == "create_support_handoff" and call["status"] == "ERROR" for call in calls.values())
        stream = ""
        public_updates = 0
        for event in events:
            if event["type"] == "chunk":
                stream += event["chunk"]
            elif event["type"] == "answer_replace":
                stream = event["content"]
            else:
                continue
            public_updates += 1
            forbidden = evaluate_answer(stream, grading_case, references=refs).details["hallucination"]["forbiddenHits"]
            assert not forbidden, forbidden
        assert public_updates and stream == snapshot["content"], "Public stream differs from the saved answer"
        row["publicUpdatesChecked"] = public_updates
        score = evaluate_customer_service_case(grading_case, artifacts)
        row["automatedPass"] = score.passed
        row["layers"] = {name: {"passed": layer.passed, "details": layer.details} for name, layer in score.layers.items()}


async def run(output):
    password = (DB_PATH.parent / "acceptance-password").read_text(encoding="utf-8")
    cases = selected_cases()
    assert len(cases) == 2 * len(PAIRS) == 12
    passed = set()
    with output.open("x", encoding="utf-8") as file:
        for case in cases:
            row = {"caseId": case["id"], "events": [], "automatedPass": False}
            try:
                await run_case(case, password, row)
            except Exception as error:
                row["error"] = repr(error)
            if row["automatedPass"]:
                passed.add(case["id"])
            print(case["id"], row["automatedPass"], row.get("error", ""), flush=True)
            file.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
            file.flush()
    pairs = sum(all(f"phase-a-{pair}-{side}" in passed for side in ("allow", "restrict")) for pair in PAIRS)
    print(f"cases={len(cases)} passed={len(passed)} pairs_passed={pairs}/{len(PAIRS)}")
    return len(passed) == len(cases) and pairs == len(PAIRS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("serve", "run"))
    parser.add_argument("--output", type=Path, default=Path("/app/data/acceptance.jsonl"))
    args = parser.parse_args()
    if args.mode == "serve":
        serve()
    else:
        raise SystemExit(0 if asyncio.run(run(args.output)) else 2)
