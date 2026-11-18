"""Check the dedicated UI fixture API, never the application database."""

import json
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    fixture = json.loads((ROOT / "data/checkpoints/phase2-ui-fixture.json").read_text(encoding="utf-8"))
    with httpx.Client(base_url="http://127.0.0.1:18026/api/v1", trust_env=False) as client:
        assert client.get(f"/diagnoses/{fixture['diagnosisId']}").status_code in {401, 403}
        login = client.post(
            "/users/login", json={"username": "diagnosisaccept", "password": "DiagnosisAccept123"}
        )
        login.raise_for_status()
        payload = login.json()["data"]
        token = payload.get("token") or payload.get("accessToken")
        assert token, "Login did not return a token"
        client.headers["Authorization"] = f"Bearer {token}"
        detail = client.get(f"/diagnoses/{fixture['diagnosisId']}")
        detail.raise_for_status()
        data = detail.json()["data"]
        assert data["status"] == "WAITING_USER_ACTION"
        assert any(e["sourceType"] == "USER_REPORT" and not e["verified"] for e in data["evidence"])
        assert all(
            e["freshness"] == "HISTORICAL_ONLY"
            for e in data["evidence"]
            if e["sourceType"] == "BUSINESS_QUERY"
        )
        linked = client.get(f"/diagnoses/by-generation/{fixture['generationId']}")
        assert linked.json()["data"]["diagnosisId"] == fixture["diagnosisId"]
        messages = client.get("/users/conversation", params={"conversationId": fixture["conversationId"]})
        assert any(m.get("diagnosisId") == fixture["diagnosisId"] for m in messages.json()["data"])
        snapshot = client.get(f"/chat/generation/{fixture['generationId']}")
        assert snapshot.json()["data"]["diagnosisId"] == fixture["diagnosisId"]
        assert client.get("/diagnoses/not-existing").status_code == 404
    report = {
        "passed": True,
        "providerCalls": 0,
        "fixtureOnly": True,
        "checks": [
            "no_auth_denied",
            "login",
            "case_detail",
            "report_is_unverified",
            "historical_scope",
            "generation_link",
            "history_reload_link",
            "generation_snapshot",
            "unknown_404",
        ],
    }
    (ROOT / "data/checkpoints/phase2-http-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report))


if __name__ == "__main__":
    main()
