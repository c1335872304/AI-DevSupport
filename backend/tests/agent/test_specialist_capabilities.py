from app.agent.agent_skill_policy import TARGET_AGENT_TOOLS, build_target_agent_plans
from app.agent.routing_policy import routing_policy
from app.agent.types import RoutingDecision
from app.db.models import Base
from app.skill_runtime.registry import skill_registry
from app.tools.registry import tool_registry


API_TOOLS = {"query_call_log", "query_api_key_status", "query_recent_call_stats", "query_error_code"}
BILLING_TOOLS = {"query_plan", "query_usage", "query_bill"}


def test_target_capabilities_are_registered_and_bound_to_three_agents():
    assert API_TOOLS | BILLING_TOOLS <= set(tool_registry.names())
    plans = build_target_agent_plans(
        RoutingDecision(selected_agents=("api_diagnostic", "billing", "knowledge")),
        skill_registry,
    )
    assert {plan.agent for plan in plans} == {"api_diagnostic", "billing", "knowledge"}
    assert set(TARGET_AGENT_TOOLS["api_diagnostic"]) >= API_TOOLS
    assert TARGET_AGENT_TOOLS["billing"] == ("query_plan", "query_usage", "query_bill")


def test_routing_policy_selects_api_and_high_risk_billing_agents():
    api = routing_policy.decide("request_id req_demo_401 返回 401，API Key 是不是过期了？")
    assert api.selected_agents == ("api_diagnostic", "knowledge")
    high_risk = routing_policy.decide("账单太贵了，帮我降套餐并退差价")
    assert high_risk.selected_agents == ("billing",)
    assert high_risk.requires_handoff_after_summary is True


def test_support_business_tables_are_part_of_current_schema():
    expected = {
        "support_applications", "support_api_keys", "support_api_call_logs", "support_error_codes",
        "support_plans", "support_subscriptions", "support_usage_records", "support_invoices",
    }
    assert expected <= set(Base.metadata.tables)
