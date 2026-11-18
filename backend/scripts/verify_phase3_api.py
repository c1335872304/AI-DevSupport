"""Real HTTP acceptance against the explicitly isolated P3 fixture only."""

import json
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    fixture = json.loads((ROOT / "data/checkpoints/phase3-ui-fixture.json").read_text())
    case = next(c for c in fixture["cases"] if c["purpose"] == "http")
    url = f"/diagnoses/{case['diagnosisId']}"
    with httpx.Client(base_url="http://127.0.0.1:18036/api/v1", trust_env=False) as client:
        assert client.get(url).status_code in {401, 403}
        login = client.post("/users/login", json={"username": "loopaccept", "password": "LoopAccept123"})
        login.raise_for_status()
        credentials = login.json()["data"]
        client.headers["Authorization"] = "Bearer " + (credentials.get("token") or credentials["accessToken"])
        before = client.get(url).json()["data"]
        assert before["status"] == "WAITING_USER_ACTION"
        assert [c["cause"] for c in before["candidates"] if c["status"] == "SUPPORTED"] == ["RATE_LIMIT"]
        payload = {
            "requestId": case["requestId"],
            "expectedRevision": before["revision"],
            "idempotencyKey": "http-acceptance",
        }
        assert client.post(url + "/rechecks", json={**payload, "expectedRevision": 1}).status_code == 409
        submitted = client.post(url + "/rechecks", json=payload)
        assert submitted.status_code == 202
        for _ in range(50):
            after = client.get(url).json()["data"]
            if after["status"] == "RESOLVED":
                break
            time.sleep(0.2)
        assert after["status"] == "RESOLVED", after
        assert after["workflow"]["rechecks"][-1]["scope"] == "this_application_endpoint_request_only"
        replay = client.post(url + "/rechecks", json=payload)
        assert (
            replay.status_code == 202
            and replay.json()["data"]["generationId"] == submitted.json()["data"]["generationId"]
        )
        assert client.post(url + "/rechecks", json={**payload, "requestId": "req_other"}).status_code == 409
        assert client.get("/diagnoses/not-existing").status_code == 404
        assert len(after["workflow"]["rechecks"]) == 1
    report = {
        "passed": True,
        "fixtureOnly": True,
        "providerCalls": 0,
        "checks": [
            "authentication",
            "observed_cause",
            "revision_conflict",
            "async_recheck",
            "scoped_recovery",
            "idempotent_replay",
            "key_payload_conflict",
            "unknown_404",
            "single_recheck",
        ],
    }
    (ROOT / "data/checkpoints/phase3-http-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report))


if __name__ == "__main__":
    main()
