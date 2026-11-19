"""Independent customer-entry probe and durable rollout gate."""

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sqlite3
import sys
from urllib.parse import urlsplit, urlunsplit
import uuid

import httpx
import websockets

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.trace_identity import generation_trace_id

THRESHOLD = 3
RECOVERY = 2
ROOT = "customer_service.question"


def now():
    return datetime.now(timezone.utc)


def data(response):
    response.raise_for_status()
    return response.json()["data"]


async def customer_probe(url):
    generation = None
    started = now()
    try:
        async with asyncio.timeout(35), httpx.AsyncClient(
            base_url=url + "/api/v1", timeout=8, trust_env=False,
        ) as client:
            token = data(await client.post("/users/login", json={
                "username": os.environ["PROBE_USERNAME"], "password": os.environ["PROBE_PASSWORD"],
            }))["token"]
            client.headers["Authorization"] = f"Bearer {token}"
            conversation = data(await client.post("/users/conversations"))["conversationId"]
            base = urlsplit(url)
            ws_url = urlunsplit(("wss" if base.scheme == "https" else "ws", base.netloc, base.path + "/chat", "", ""))
            async with websockets.connect(ws_url, proxy=None) as socket:
                await socket.send(json.dumps({"type": "auth", "token": token}))
                if json.loads(await socket.recv()).get("type") != "connection":
                    raise ValueError("websocket_auth")
                sent_at = now()
                await socket.send("你好")
                first_chunk_ms = None
                while True:
                    event = json.loads(await socket.recv())
                    if event.get("type") == "start":
                        generation = event["generationId"]
                    if generation and event.get("generationId") == generation:
                        if event.get("type") == "chunk" and first_chunk_ms is None:
                            first_chunk_ms = round((now() - sent_at).total_seconds() * 1000)
                        if event.get("type") == "completion":
                            break
                    if event.get("error") and not event.get("type"):
                        raise ValueError("websocket_generation_failed")
            stored = data(await client.get(f"/chat/generation/{generation}"))
            if (stored["status"] != "COMPLETED" or stored["conversationId"] != conversation
                    or not stored["content"] or stored["content"] != event.get("content")):
                raise ValueError("generation_receipt_mismatch")
            return {"generationId": generation, "businessCompleted": True, "firstChunkMs": first_chunk_ms}, started
    except (TimeoutError, httpx.HTTPError, websockets.WebSocketException, ValueError, KeyError) as exc:
        return {"generationId": generation, "businessCompleted": False,
                "outcome": "probe_failed", "detail": type(exc).__name__}, started


async def trace_probe(report, since, url, wait_seconds):
    trace_id = generation_trace_id(report["generationId"])
    report["traceId"] = trace_id
    until = asyncio.get_running_loop().time() + wait_seconds
    status = "trace_check_unavailable"
    detail = None
    async with httpx.AsyncClient(
        auth=(os.environ["LANGFUSE_PUBLIC_KEY"], os.environ["LANGFUSE_SECRET_KEY"]),
        timeout=4, trust_env=False,
    ) as client:
        while True:
            try:
                response = await client.get(url + "/api/public/v2/observations", params={
                    "traceId": trace_id, "name": ROOT, "fields": "core,basic",
                    "fromStartTime": (since - timedelta(seconds=5)).isoformat(),
                    "toStartTime": now().isoformat(),
                })
                response.raise_for_status()
                observations = response.json()["data"]
                if not isinstance(observations, list):
                    raise ValueError("unexpected_observations_payload")
                if any(item.get("traceId") == trace_id and item.get("name") == ROOT
                       and not item.get("parentObservationId") for item in observations):
                    report["outcome"] = "healthy"
                    return
                status, detail = "trace_missing", None
            except httpx.HTTPStatusError as exc:
                code = exc.response.status_code
                status = "trace_check_unavailable" if code >= 500 or code == 429 else "trace_check_error"
                detail = f"http_{code}"
                if status == "trace_check_error":
                    break
            except (httpx.RequestError, KeyError, ValueError) as exc:
                status, detail = "trace_check_unavailable", type(exc).__name__
            remaining = until - asyncio.get_running_loop().time()
            if remaining <= 0:
                break
            await asyncio.sleep(min(1, remaining))
    report.update(outcome=status, detail=detail)


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path, isolation_level="IMMEDIATE")
        self.db.execute("CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, data TEXT NOT NULL)")
        self.db.execute("INSERT OR IGNORE INTO state VALUES (1, '{}')")
        self.db.commit()

    def read(self):
        return json.loads(self.db.execute("SELECT data FROM state WHERE id=1").fetchone()[0])

    def update(self, change):
        with self.db:
            self.db.execute("UPDATE state SET data=data WHERE id=1")
            value = self.read()
            change(value)
            self.db.execute("UPDATE state SET data=? WHERE id=1", (json.dumps(value),))
        return value


def open_incident(state, reason, *, escalate=False):
    previous = state.get("incident")
    if not previous or previous.get("resumedAt") or (escalate and previous["signal"] != reason):
        if previous:
            state["incidentHistory"] = [*state.get("incidentHistory", []), previous][-10:]
        state["incident"] = {
            "incidentId": uuid.uuid4().hex, "signal": reason, "firedAt": now().isoformat(),
            "probes": state.get("recent", [])[-THRESHOLD:],
        }
    state["pauseRollout"] = True


def record(state, report, max_age):
    recent = state.get("recent", [])
    if recent and (datetime.fromisoformat(report["checkedAt"]) -
                   datetime.fromisoformat(recent[-1]["checkedAt"])).total_seconds() > max_age:
        recent = []
        state["healthyStreak"] = state["badStreak"] = 0
    state["recent"] = [*recent, report][-THRESHOLD:]
    healthy = report["outcome"] == "healthy"
    state["healthyStreak"] = state.get("healthyStreak", 0) + 1 if healthy else 0
    state["badStreak"] = 0 if healthy else state.get("badStreak", 0) + 1
    if state["badStreak"] >= THRESHOLD:
        open_incident(state, "three_consecutive_failed_or_unobservable_probes")


async def notify(store, url):
    incident = store.read().get("incident")
    if not incident or incident.get("deliveredAt"):
        return
    incident_id = incident["incidentId"]
    payload = {key: incident[key] for key in ("incidentId", "signal", "firedAt", "probes")}
    headers = {"Idempotency-Key": incident_id}
    if token := os.environ.get("PROBE_NOTIFY_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    try:
        async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError:
        return  # Durable pending incident; the next independent probe retries.

    def delivered(state):
        if state.get("incident", {}).get("incidentId") == incident_id:
            state["incident"].setdefault("deliveredAt", now().isoformat())
    store.update(delivered)


def can_expand(state, max_age):
    recent = state.get("recent") or []
    return bool(recent and recent[-1]["outcome"] == "healthy" and not state.get("pauseRollout")
                and (now() - datetime.fromisoformat(recent[-1]["checkedAt"])).total_seconds() <= max_age)


def actions(store, command, args):
    def change(state):
        if command == "hold":
            open_incident(state, args.reason, escalate=True)
            state["healthyStreak"] = 0
            return
        incident = state.get("incident")
        if not incident or incident["incidentId"] != args.incident or incident.get("resumedAt"):
            raise ValueError("No matching active incident")
        if command == "ack":
            if not incident.get("deliveredAt"):
                raise ValueError("Notification is still pending")
            if not incident.get("acknowledgedAt"):
                incident.update(acknowledgedBy=args.operator, acknowledgedAt=now().isoformat())
        else:
            if not incident.get("acknowledgedAt") or state.get("healthyStreak", 0) < RECOVERY:
                raise ValueError("Require on-call acknowledgement and two healthy probes")
            if not can_expand({**state, "pauseRollout": False}, args.max_age):
                raise ValueError("Require a fresh healthy probe")
            incident.update(resumedBy=args.operator, resumedAt=now().isoformat())
            state["pauseRollout"] = False
    return store.update(change)


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--max-age", type=int, default=300)
    sub = parser.add_subparsers(dest="command", required=True)
    probe = sub.add_parser("probe")
    probe.add_argument("--trace-wait", type=float, default=30)
    sub.add_parser("status")
    hold = sub.add_parser("hold")
    hold.add_argument("--reason", required=True, choices=("duplicate_charge", "duplicate_handoff",
                      "false_write_success", "unauthorized_access", "credential_leak", "metrics_threshold",
                      "context_scope_violation", "stale_context_fact", "context_correction_lost"))
    for name in ("ack", "resume"):
        action = sub.add_parser(name)
        action.add_argument("--incident", required=True)
        action.add_argument("--operator", required=True)
    args = parser.parse_args()
    store = Store(args.state)
    if args.command == "probe":
        report, since = await customer_probe(os.environ["PROBE_APP_URL"].rstrip("/"))
        if report["businessCompleted"]:
            await trace_probe(report, since, os.environ["PROBE_LANGFUSE_URL"].rstrip("/"), args.trace_wait)
        report["checkedAt"] = now().isoformat()
        store.update(lambda state: record(state, report, args.max_age))
        await notify(store, os.environ["PROBE_NOTIFY_URL"])
    elif args.command != "status":
        try:
            actions(store, args.command, args)
        except ValueError as exc:
            parser.error(str(exc))
        if args.command == "hold":
            await notify(store, os.environ["PROBE_NOTIFY_URL"])
    state = store.read()
    permitted = can_expand(state, args.max_age)
    print(json.dumps({**state, "canExpandRollout": permitted}))
    return 2 if args.command == "status" and not permitted else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
