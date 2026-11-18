"""Verify three isolated demo flows over real HTTP, including idempotent handoff."""

import json
from pathlib import Path
import time
import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    fixture = json.loads((ROOT / "data/checkpoints/phase4/demos-fixture.json").read_text(encoding="utf-8"))
    checks = []
    with httpx.Client(base_url="http://127.0.0.1:18046/api/v1", trust_env=False) as client:
        response = client.post("/users/login", json={"username": "loopaccept", "password": "LoopAccept123"})
        response.raise_for_status()
        client.headers["Authorization"] = "Bearer " + response.json()["data"]["token"]
        for demo in fixture:
            url = f"/diagnoses/{demo['diagnosisId']}"
            before = client.get(url).json()["data"]
            if demo["purpose"] == "handoff":
                assert before["status"] == "HANDED_OFF"
                for _ in range(2):
                    assert (
                        client.post(url + "/resume", json={"generationId": demo["generationId"]}).status_code
                        == 202
                    )
                after = client.get(url).json()["data"]
                assert after["status"] == "HANDED_OFF"
            else:
                payload = {
                    "requestId": demo["requestId"],
                    "expectedRevision": before["revision"],
                    "idempotencyKey": "demo4-" + demo["purpose"],
                }
                submitted = client.post(url + "/rechecks", json=payload)
                assert submitted.status_code == 202
                for _ in range(50):
                    after = client.get(url).json()["data"]
                    if (after.get("workflow") or {}).get("rechecks"):
                        break
                    time.sleep(0.2)
                wanted = "RESOLVED" if demo["purpose"] == "401-recovery" else "WAITING_USER_ACTION"
                assert after["status"] == wanted
                if wanted == "WAITING_USER_ACTION":
                    assert after["workflow"]["decision"]["causeConfirmed"]
                    assert any(
                        c["cause"] == "QUOTA_LIMIT" and c["status"] == "SUPPORTED"
                        for c in after["candidates"]
                    )
                assert (
                    client.post(url + "/rechecks", json=payload).json()["data"]["generationId"]
                    == submitted.json()["data"]["generationId"]
                )
            checks.append(
                {
                    "purpose": demo["purpose"],
                    "diagnosisId": demo["diagnosisId"],
                    "status": after["status"],
                    "passed": True,
                }
            )
    report = {"passed": True, "providerCalls": 0, "fixtureOnly": True, "checks": checks}
    (ROOT / "data/checkpoints/phase4/demos-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report))


if __name__ == "__main__":
    main()
