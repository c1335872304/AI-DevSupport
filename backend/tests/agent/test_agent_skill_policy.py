from __future__ import annotations

from app.agent.agent_skill_policy import (
    SHARED_NODE_SKILLS,
    TARGET_AGENT_SKILLS,
    TARGET_AGENT_TOOLS,
    build_target_agent_plans,
    validate_target_skill_contracts,
)
from app.agent.types import RoutingDecision
from app.skill_runtime.registry import skill_registry


def test_target_agents_have_one_explicit_professional_skill_each():
    assert TARGET_AGENT_SKILLS == {
        "api_diagnostic": "api-diagnostic",
        "billing": "billing",
        "knowledge": "knowledge",
    }


def test_target_tool_contracts_are_narrower_than_the_underlying_skills():
    plans = build_target_agent_plans(
        RoutingDecision(selected_agents=("api_diagnostic", "billing", "knowledge")),
        skill_registry,
    )

    by_agent = {plan.agent: plan for plan in plans}
    assert by_agent["billing"].allowed_tools == ("query_plan", "query_usage", "query_bill")
    assert "create_support_handoff" not in by_agent["billing"].allowed_tools
    assert by_agent["api_diagnostic"].allowed_tools == TARGET_AGENT_TOOLS["api_diagnostic"]


def test_target_and_shared_skill_contracts_have_controlled_resources():
    validate_target_skill_contracts(skill_registry)
    assert SHARED_NODE_SKILLS == {
        "handoff_decision": "escalation",
        "create_support_handoff": "escalation",
        "generate_customer_response": "customer-support",
    }
