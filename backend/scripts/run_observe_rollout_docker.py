"""Isolated rollout drill using real Langfuse through a fault-injecting relay."""

import asyncio
import json
from pathlib import Path
import subprocess
import sys
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
import httpx
import uvicorn

relay = FastAPI()
mode = "healthy"
receipts = {}
attempts = 0
UPSTREAM = "http://paismart-langfuse:3000"
RELAY = "http://observe-relay:8012"
STATE = f"/app/data/probe-{uuid.uuid4().hex}.sqlite"


@relay.post("/drill/mode/{value}")
async def change(value: str):
    global mode
    if value not in {"healthy", "drop_ingest", "unavailable"}:
        raise HTTPException(400)
    mode = value
    return {"mode": mode}


async def forward(request: Request):
    headers = {key: value for key, value in request.headers.items()
               if key in {"authorization", "content-type", "content-encoding", "x-langfuse-ingestion-version"}}
    async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
        result = await client.request(request.method, UPSTREAM + request.url.path, params=request.query_params,
                                      headers=headers, content=await request.body())
    return Response(result.content, status_code=result.status_code, media_type=result.headers.get("content-type"))


@relay.post("/api/public/otel/v1/traces")
async def ingest(request: Request):
    if mode != "healthy":
        return Response(status_code=503)
    return await forward(request)


@relay.get("/api/public/v2/observations")
async def search(request: Request):
    if mode == "unavailable":
        return Response(status_code=503)
    return await forward(request)


@relay.post("/drill/notify", status_code=202)
async def notify(request: Request):
    global attempts
    event = await request.json()
    if request.headers.get("Idempotency-Key") != event["incidentId"]:
        raise HTTPException(400)
    attempts += 1
    receipts.setdefault(event["incidentId"], event)
    if attempts == 1:
        return Response(status_code=503)  # Delivery succeeded but its receipt was lost.
    return {"accepted": event["incidentId"]}


@relay.get("/drill/receipts")
async def delivery_history():
    return {"attempts": attempts, "receipts": list(receipts.values())}


def cli(*args, expected=0):
    result = subprocess.run(
        [sys.executable, "/app/scripts/observe_rollout.py", "--state", STATE, *args],
        capture_output=True, text=True,
    )
    assert result.returncode == expected, (args, result.returncode, result.stdout, result.stderr)
    return json.loads(result.stdout) if result.stdout else None


async def exercise():
    async with httpx.AsyncClient(base_url=RELAY, trust_env=False) as client:
        def probe(wait=8):
            return cli("probe", "--trace-wait", str(wait))

        snapshots = {}
        snapshots["baseline"] = await asyncio.to_thread(probe, 25)
        assert snapshots["baseline"]["canExpandRollout"], snapshots["baseline"]
        (await client.post("/drill/mode/drop_ingest")).raise_for_status()
        for n in (1, 2):
            state = snapshots[f"missing{n}"] = await asyncio.to_thread(probe)
            sample = state["recent"][-1]
            assert sample["businessCompleted"] and sample["outcome"] == "trace_missing", sample
            assert not state.get("incident") and not state["canExpandRollout"]
            assert (await client.get("/drill/receipts")).json()["attempts"] == 0
        (await client.post("/drill/mode/unavailable")).raise_for_status()
        third = snapshots["third"] = await asyncio.to_thread(probe)
        assert third["recent"][-1]["businessCompleted"] and third["recent"][-1]["outcome"] == "trace_check_unavailable"
        assert third["pauseRollout"] and not third["canExpandRollout"]
        incident = third["incident"]["incidentId"]
        assert not third["incident"].get("deliveredAt")
        cli("status", expected=2)
        cli("ack", "--incident", incident, "--operator", "drill-on-call", expected=2)
        pending = (await client.get("/drill/receipts")).json()
        assert pending["attempts"] == 1 and len(pending["receipts"]) == 1
        fourth = snapshots["fourth"] = await asyncio.to_thread(probe)
        assert fourth["pauseRollout"] and fourth["incident"]["deliveredAt"]
        delivery = snapshots["delivery"] = (await client.get("/drill/receipts")).json()
        assert delivery["attempts"] == 2 and len(delivery["receipts"]) == 1
        snapshots["ack"] = cli("ack", "--incident", incident, "--operator", "drill-on-call")
        assert snapshots["ack"]["incident"]["acknowledgedBy"] == "drill-on-call"
        (await client.post("/drill/mode/healthy")).raise_for_status()
        snapshots["recoveredOnce"] = await asyncio.to_thread(probe, 25)
        assert snapshots["recoveredOnce"]["healthyStreak"] == 1
        cli("resume", "--incident", incident, "--operator", "drill-on-call", expected=2)
        snapshots["recoveredTwice"] = await asyncio.to_thread(probe, 25)
        assert snapshots["recoveredTwice"]["healthyStreak"] == 2
        assert not snapshots["recoveredTwice"]["canExpandRollout"]
        snapshots["resumed"] = cli("resume", "--incident", incident, "--operator", "drill-on-call")
        assert snapshots["resumed"]["canExpandRollout"]
        cli("status", expected=0)
        snapshots["criticalHold"] = cli("hold", "--reason", "duplicate_charge")
        assert snapshots["criticalHold"]["pauseRollout"] and snapshots["criticalHold"]["healthyStreak"] == 0
        assert snapshots["criticalHold"]["incident"]["signal"] == "duplicate_charge"
        cli("status", expected=2)
        Path("/app/data/observe-rollout-verified.json").write_text(
            json.dumps(snapshots, indent=2), encoding="utf-8",
        )
        print("healthy -> missing twice -> unavailable -> delivered -> acknowledged -> recovered -> resumed -> critical hold")


if __name__ == "__main__":
    if sys.argv[1:] == ["relay"]:
        uvicorn.run(relay, host="0.0.0.0", port=8012, access_log=False)
    elif sys.argv[1:] == ["exercise"]:
        asyncio.run(exercise())
    else:
        raise SystemExit("Use relay or exercise")
