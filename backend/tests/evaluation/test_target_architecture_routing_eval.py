from __future__ import annotations

import json
from pathlib import Path

from app.agent.routing_policy import routing_policy


ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "eval/customer_service/target_architecture.jsonl"


def test_target_architecture_routing_regression_set_is_complete_and_deterministic():
    rows = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) >= 6
    assert len({row["id"] for row in rows}) == len(rows)

    for row in rows:
        expected = row["expected"]
        decision = routing_policy.decide(row["question"], row.get("entities") or {})
        assert list(decision.selected_agents) == expected["agents"], row["id"]
        assert decision.requires_handoff_after_summary is expected["handoff"], row["id"]
        assert decision.risk_level == expected["risk"], row["id"]
