from __future__ import annotations

from pathlib import Path
import re

from app.agent.types import AgentEvidence, AgentPlan, HandoffDecision, HandoffResult, RoutingDecision, ToolBatch


def test_target_architecture_contracts_are_trace_serializable():
    decision = RoutingDecision(
        selected_agents=("api_diagnostic", "billing"),
        matched_rules=("http_429", "billing_question"),
        risk_level="MEDIUM",
    )
    plan = AgentPlan("billing", "billing", ("query_plan", "query_usage", "query_bill"), "verify billing facts")
    batch = ToolBatch("billing-1", "billing", ("call-1", "call-2"))
    evidence = AgentEvidence(
        agent="billing",
        status="completed",
        verified_facts=({"claim": "usage verified", "verified": True},),
        attempted_tools=("query_usage",),
    )

    assert decision.to_dict()["selectedAgents"] == ["api_diagnostic", "billing"]
    assert plan.to_dict()["allowedTools"] == ["query_plan", "query_usage", "query_bill"]
    assert batch.to_dict()["toolCallIds"] == ["call-1", "call-2"]
    assert evidence.to_dict()["verifiedFacts"][0]["verified"] is True
    assert HandoffResult(attempted=True, success=False, error="timeout").to_dict()["handoffId"] is None
    assert HandoffDecision(required=True, reasons=("tool_timeout",)).to_dict()["required"] is True


def test_target_architecture_contract_has_no_legacy_mode_switch():
    from app.core.config import Settings

    settings = Settings()
    assert not hasattr(settings, "agent_architecture_mode")
    assert not hasattr(settings, "routing_policy_mode")


def test_target_graph_exposes_each_architecture_node_explicitly():
    source = (Path(__file__).resolve().parents[2] / "app/agent/graph/workflow.py").read_text(encoding="utf-8")
    nodes = set(re.findall(r'graph\.add_node\("([^"]+)"', source))
    assert nodes == {
        "load_context", "extract_entities", "routing_policy", "clarify",
        "target_specialist_dispatch", "target_execute_tools", "target_evidence_join",
        "target_handoff_decision", "target_create_handoff", "target_generate_response",
        "safety", "emit_final", "persist_trace",
    }
