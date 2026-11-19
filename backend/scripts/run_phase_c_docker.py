"""Local notification, incident response and configuration rollback exercise."""

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
import sqlite3

import httpx

from run_phase_b_docker import (
    DATA, DB, assert_accounting, collector_app, completed_chat, customer, exercise, generation, ledger, read,
)

OPS = "http://127.0.0.1:8012"
INCIDENT = DATA / "phase-c-incident.json"


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def receiver():
    import uvicorn
    from fastapi import HTTPException

    app = collector_app()

    @app.post("/drill/notify", status_code=202)
    async def notify(payload: dict):
        if INCIDENT.exists():
            raise HTTPException(409)
        record = {**payload, "receivedAt": now()}
        save(INCIDENT, record)
        return record

    @app.post("/drill/ack")
    async def ack(payload: dict):
        record = load(INCIDENT)
        if record["incidentId"] != payload["incidentId"]:
            raise HTTPException(404)
        record.update(onCall=payload["onCall"], acknowledgedAt=now())
        save(INCIDENT, record)
        return record

    uvicorn.run(app, host="127.0.0.1", port=8012, log_level="warning")


async def probe(user, question):
    events = []
    async with customer(user) as (client, token):
        snapshot = await completed_chat(client, token, question, events)
    return snapshot, ledger(user, snapshot["generationId"])


async def find_trace(gid, seconds):
    reports = DATA / "received-traces.jsonl"
    try:
        async with asyncio.timeout(seconds):
            while True:
                if reports.exists():
                    for line in reports.read_text(encoding="utf-8").splitlines():
                        record = json.loads(line)
                        if record["generationId"] == gid:
                            return record
                await asyncio.sleep(0.1)
    except TimeoutError:
        return None


async def verify_business(trial):
    docs, docs_ledger = await probe(f"search-503-{trial}", "按文档说明查询故障演练的上传上限。")
    billing, billing_ledger = await probe(f"billing-all-{trial}", "请查询我 2026-11 的账单和用量。")
    assert "50 MB" in docs["content"] and docs["referenceMappings"], docs
    assert "金额为12" in billing["content"] and "用量为120" in billing["content"], billing
    checks = []
    for item, account in ((docs, docs_ledger), (billing, billing_ledger)):
        assert_accounting(account)
        assert not account["tickets"]
        trace = await find_trace(item["generationId"], 6)
        assert trace, item["generationId"]
        checks.append({"generationId": item["generationId"], "ledger": account, "trace": trace})
    return checks


async def baseline():
    checks = await verify_business(1)
    drill = {"events": []}
    await exercise("handoff-before", 1, drill)
    recovered = drill["recovered"]
    save(DATA / "phase-c-baseline.json", {
        "at": now(), "healthyConfig": os.environ["LANGFUSE_BASE_URL"], "checks": checks,
        "existingTicket": drill["recoveryLedger"]["tickets"][0],
        "ticketGeneration": recovered["generationId"],
        "ticketLedger": drill["recoveryLedger"],
    })


async def incident():
    checks = []
    for trial in range(1, 4):
        snap, account = await probe(f"trace-down-{trial}", "你好")
        assert_accounting(account)
        assert not account["tickets"]
        assert await find_trace(snap["generationId"], 2) is None
        checks.append({"generationId": snap["generationId"], "ledger": account, "traceMissing": True})
    notice = {"incidentId": "phase-c-isolated-1", "signal": "three_consecutive_missing_probe_traces",
              "generationIds": [item["generationId"] for item in checks], "firedAt": now()}
    async with httpx.AsyncClient(base_url=OPS, trust_env=False) as ops:
        delivered = await ops.post("/drill/notify", json=notice)
        assert delivered.status_code == 202, delivered.text
        ack = await ops.post("/drill/ack", json={"incidentId": notice["incidentId"], "onCall": "drill-operator"})
        ack.raise_for_status()
        assert ack.json()["onCall"] == "drill-operator"
    bad_url = os.environ["LANGFUSE_BASE_URL"]
    async with httpx.AsyncClient(trust_env=False) as client:
        health = await client.get("http://127.0.0.1:8000/health")
        health.raise_for_status()
        try:
            await client.get(bad_url)
        except httpx.ConnectError:
            pass
        else:
            raise AssertionError("The configured trace endpoint was reachable")
    previous = load(DATA / "phase-c-baseline.json")
    assert bad_url != previous["healthyConfig"]
    with sqlite3.connect(DB) as db, sqlite3.connect(DATA / "phase-c-pre-rollback.sqlite") as backup:
        db.backup(backup)
        assert backup.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    save(DATA / "phase-c-diagnosis.json", {
        "checkedAt": now(), "rollbackRequestedAt": now(), "affectedConfig": bad_url,
        "restoreConfig": previous["healthyConfig"], "health": health.json(),
        "checks": checks, "databaseBackupIntegrity": "ok", "reason": "trace_receiver_connection_refused",
    })


async def recovered():
    diagnosis = load(DATA / "phase-c-diagnosis.json")
    baseline_result = load(DATA / "phase-c-baseline.json")
    assert os.environ["LANGFUSE_BASE_URL"] == diagnosis["restoreConfig"]
    checks = await verify_business(2)
    async with customer("handoff-before-1") as (client, _):
        tickets = read(await client.get("/support/handoffs"))
        assert [ticket["handoffId"] for ticket in tickets] == [baseline_result["existingTicket"]]
    assert ledger("handoff-before-1", baseline_result["ticketGeneration"]) == baseline_result["ticketLedger"]
    for trial, check in enumerate(diagnosis["checks"], 1):
        name = f"trace-down-{trial}"
        assert ledger(name, check["generationId"]) == check["ledger"]
        async with customer(name) as (client, _):
            assert (await generation(client, check["generationId"]))["status"] == "COMPLETED"
    drill = {"events": []}
    await exercise("handoff", 2, drill)
    trace = await find_trace(drill["generationId"], 6)
    assert trace
    with sqlite3.connect(DB) as db:
        assert db.execute("SELECT COUNT(*) FROM llm_token_reservations WHERE status='RESERVED'").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM support_handoffs").fetchone()[0] == 2
    restored_at = now()
    seconds = (datetime.fromisoformat(restored_at) - datetime.fromisoformat(diagnosis["rollbackRequestedAt"])).total_seconds()
    save(DATA / "phase-c-result.json", {
        "baseline": baseline_result, "incident": load(INCIDENT), "diagnosis": diagnosis,
        "restoredAt": restored_at, "rollbackAndVerificationSeconds": seconds,
        "postRollbackChecks": checks, "preservedTicket": baseline_result["existingTicket"],
        "handoffRecoveryTrace": trace, "handoffRows": drill["ledger"]["tickets"],
        "handoffRetries": len(drill["retries"]), "handoffRecoverySeconds": drill["handoffRecoverySeconds"],
        "openReservations": 0, "ticketCount": 2,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("receiver", "baseline", "incident", "recovered"))
    args = parser.parse_args()
    if args.mode == "receiver":
        receiver()
    else:
        asyncio.run({"baseline": baseline, "incident": incident, "recovered": recovered}[args.mode]())
        print(f"{args.mode}: passed")
