"""Fetch a concise, credential-safe audit summary for one persisted agent run."""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

import httpx


def _data(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("data")
    return value if isinstance(value, dict) else {}


async def main(args: argparse.Namespace) -> None:
    async with httpx.AsyncClient(base_url=args.api_url.rstrip("/"), timeout=30.0) as client:
        login = await client.post("/api/v1/users/login", json={"username": args.username, "password": args.password})
        login.raise_for_status()
        token = str(_data(login.json()).get("token") or "")
        if not token:
            raise RuntimeError("Login succeeded without an access token")
        response = await client.get(f"/api/v1/admin/agent-runs/{args.run_id}", headers={"Authorization": f"Bearer {token}"})
        response.raise_for_status()
        run = _data(response.json())

    trace = run.get("trace") if isinstance(run.get("trace"), dict) else {}
    summary = {
        "runId": run.get("runId"),
        "generationId": run.get("generationId"),
        "status": run.get("status"),
        "startedAt": run.get("startedAt"),
        "completedAt": run.get("completedAt"),
        "activeSkills": run.get("activeSkills", []),
        "traceKeys": sorted(trace.keys()),
        "routing": trace.get("routing") or trace.get("routingDecision"),
        "handoff": {
            "attempted": trace.get("handoffAttempted"),
            "id": trace.get("handoffId"),
            "success": trace.get("handoffSuccess"),
            "result": trace.get("handoffResult"),
        },
        "qualityGates": {
            "action": trace.get("qualityGateAction"),
            "blocked": trace.get("qualityGateBlocked"),
            "coverage": trace.get("qualityGateCoverage"),
            "failed": trace.get("qualityGatesFailed"),
            "missing": trace.get("qualityGatesMissing"),
            "recommended": trace.get("qualityGatesRecommended"),
            "used": trace.get("qualityGatesUsed"),
            "results": trace.get("qualityGateResults"),
        },
        "referencesRead": trace.get("referencesRead"),
        "toolBatches": trace.get("toolBatches"),
        "toolExecutions": [
            {key: item.get(key) for key in ("tool", "step", "status", "durationMs", "error")}
            for item in run.get("tools", [])
            if isinstance(item, dict)
        ],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    asyncio.run(main(parser.parse_args()))
