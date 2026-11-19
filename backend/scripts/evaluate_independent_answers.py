"""Frozen, single-attempt real retrieval and answer evaluation client."""

import argparse
import asyncio
import hashlib
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
import websockets

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/checkpoints/independent-answer-eval-20261020"
DATASET = ROOT / "eval/independent_answers_v1.json"
FIXTURE_CONTAINER = None
PHASE_TAG = None


async def main():
    frozen = json.loads((OUT / "frozen-inputs.json").read_text())
    assert hashlib.sha256(DATASET.read_bytes()).hexdigest() == frozen["datasetSha256"]
    identity = json.loads((OUT / "private/identity.json").read_text())
    cases = json.loads(DATASET.read_text(encoding="utf-8"))["cases"]
    for case in cases:
        for source in case["sources"]:
            assert (
                hashlib.sha256((ROOT / "vendor_knowledge" / source["file"]).read_bytes()).hexdigest()
                == source["sha256"]
            )
    with httpx.Client(base_url="http://127.0.0.1:18870/api/v1", trust_env=False, timeout=45) as client:
        login = client.post("/users/login", json={k: identity[k] for k in ("username", "password")})
        login.raise_for_status()
        token = login.json()["data"]["token"]
        client.headers["Authorization"] = "Bearer " + token
        conversations = {}
        for case in cases:
            case = dict(case)
            if case.get("questionTemplate"):
                case["question"] = case["questionTemplate"].replace("{phase}", PHASE_TAG or OUT.name)
            path = OUT / (case["id"] + ".json")
            if path.exists():
                previous = json.loads(path.read_text(encoding="utf8"))
                if case.get("conversationGroup") and previous.get("snapshot"):
                    conversations[case["conversationGroup"]] = previous["snapshot"]["conversationId"]
                print(case["id"], "existing first attempt retained", flush=True)
                continue
            row = {
                "case": case,
                "startedAt": datetime.now(UTC).isoformat(),
                "events": [],
                "citations": [],
            }
            started = time.perf_counter()
            try:
                if case.get("fixtureBeforeSend"):
                    assert FIXTURE_CONTAINER and OUT.name in {"baseline", "final"}
                    label = case["fixtureBeforeSend"]
                    assert label in {"fixed", "quota"}
                    await asyncio.to_thread(
                        subprocess.run,
                        [
                            "docker",
                            "exec",
                            FIXTURE_CONTAINER,
                            "python",
                            "/evaluation/fixture.py",
                            "recheck",
                            label,
                            PHASE_TAG or OUT.name,
                        ],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                conversation = conversations.get(case.get("conversationGroup"))
                if not conversation:
                    response = client.post("/users/conversations")
                    response.raise_for_status()
                    conversation = response.json()["data"]["conversationId"]
                    if case.get("conversationGroup"):
                        conversations[case["conversationGroup"]] = conversation
                if FIXTURE_CONTAINER:
                    sessions = client.get("/users/conversations")
                    sessions.raise_for_status()
                    for session in sessions.json()["data"]:
                        if session["conversationId"] != conversation and session["status"] == "ACTIVE":
                            client.put(
                                "/users/conversations/" + session["conversationId"] + "/archive"
                            ).raise_for_status()
                client.put(f"/users/conversations/{conversation}/switch").raise_for_status()
                row["requestedConversationId"] = conversation
                async with websockets.connect(
                    "ws://127.0.0.1:18870/chat",
                    proxy=None,
                    additional_headers={"X-Eval-Case": case["id"]},
                    max_size=8 * 1024 * 1024,
                ) as socket:
                    await socket.send(json.dumps({"type": "auth", "token": token}))
                    assert json.loads(await socket.recv())["type"] == "connection"
                    await socket.send(case["question"])
                    async with asyncio.timeout(240):
                        while True:
                            event = json.loads(await socket.recv())
                            row["events"].append(event)
                            if (
                                event.get("type") in ("chunk", "content", "message")
                                and "firstContentMs" not in row
                            ):
                                row["firstContentMs"] = round((time.perf_counter() - started) * 1000, 2)
                            if event.get("type") == "error":
                                raise RuntimeError(str(event))
                            if event.get("type") == "completion":
                                row["snapshot"] = client.get(
                                    "/chat/generation/" + event["generationId"]
                                ).json()["data"]
                                break
                row["status"] = row["snapshot"]["status"]
                if FIXTURE_CONTAINER:
                    assert row["snapshot"]["conversationId"] == conversation, (
                        "Unexpected conversation selected by server"
                    )
                if row["snapshot"].get("diagnosisId"):
                    detail = client.get("/diagnoses/" + row["snapshot"]["diagnosisId"])
                    detail.raise_for_status()
                    row["diagnosis"] = detail.json()["data"]
                mappings = row["snapshot"].get("referenceMappings") or {}

                def collect(value, target=row):
                    if isinstance(value, dict):
                        if value.get("citationId"):
                            citation = client.get(
                                "/documents/citation", params={"citationId": value["citationId"]}
                            )
                            target["citations"].append(
                                {
                                    "mapping": value,
                                    "status": citation.status_code,
                                    "response": citation.json(),
                                }
                            )
                        for child in value.values():
                            collect(child)
                    elif isinstance(value, list):
                        for child in value:
                            collect(child)

                collect(mappings)
            except Exception as exc:  # noqa: BLE001 - preserve every failed first attempt as evidence
                row["status"] = "ERROR"
                row["error"] = repr(exc)
            row["elapsedMs"] = round((time.perf_counter() - started) * 1000, 2)
            path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
            print(
                case["id"],
                row["status"],
                row["elapsedMs"],
                "ms",
                len(row["citations"]),
                "citations",
                flush=True,
            )
        usage = client.get("/users/usage")
        (OUT / "application-usage.json").write_text(usage.text, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, default=OUT)
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--demo-fixture-container")
    parser.add_argument("--phase-tag")
    args = parser.parse_args()
    OUT = args.checkpoint.resolve()
    DATASET = args.dataset.resolve()
    FIXTURE_CONTAINER = args.demo_fixture_container
    PHASE_TAG = args.phase_tag
    asyncio.run(main())
