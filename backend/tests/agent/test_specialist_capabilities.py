from app.agent.runtime import AgentRuntime
from app.db.models import Base
from app.skill_runtime.registry import skill_registry
from app.skill_runtime.router import skill_router
from app.tools.registry import tool_registry

API_TOOLS = {"query_call_log", "query_api_key_status", "query_recent_call_stats", "query_error_code"}
BILLING_TOOLS = {"query_plan", "query_usage", "query_bill"}


def _schema_names(rows):
    return {row["function"]["name"] for row in rows}


def test_original_api_diagnostic_and_billing_capabilities_are_registered_as_tools():
    names = set(tool_registry.names())
    assert API_TOOLS <= names
    assert BILLING_TOOLS <= names


def test_customer_support_skill_exposes_real_billing_tools():
    skill = skill_registry.get("customer-support")
    assert skill is not None
    assert BILLING_TOOLS <= set(skill.allowed_tools)
    visible = _schema_names(AgentRuntime().llm_tools_for_skills(["customer-support"]))
    assert BILLING_TOOLS <= visible


def test_troubleshooting_skill_exposes_api_diagnostic_tools():
    skill = skill_registry.get("troubleshooting")
    assert skill is not None
    assert API_TOOLS <= set(skill.allowed_tools)
    visible = _schema_names(AgentRuntime().llm_tools_for_skills(["customer-support", "troubleshooting"]))
    assert API_TOOLS <= visible


def test_api_incident_and_high_risk_billing_route_to_correct_specialist():
    assert skill_router.route("request_id req_demo_401 返回 401，API Key 是不是过期了？") == ["customer-support", "troubleshooting"]
    assert skill_router.route("账单太贵了，帮我降套餐并退差价") == ["customer-support", "escalation"]


def test_support_business_tables_are_part_of_current_schema():
    expected = {
        "support_applications", "support_api_keys", "support_api_call_logs", "support_error_codes",
        "support_plans", "support_subscriptions", "support_usage_records", "support_invoices",
    }
    assert expected <= set(Base.metadata.tables)

import json
import pytest
from app.agent.llm import LLMService


async def _events(service, messages, tools):
    return [event async for event in service._fallback_agent_turn(messages, tools)]


@pytest.mark.asyncio
async def test_offline_fallback_uses_request_log_then_dependency_tools():
    service = LLMService()
    tools = AgentRuntime().llm_tools_for_skills(["customer-support", "troubleshooting"])
    first = await _events(service, [{"role": "user", "content": "request_id req_demo_401 返回 401"}], tools)
    assert first[0]["type"] == "tool_calls"
    assert [call.name for call in first[0]["tool_calls"]] == ["query_call_log"]

    messages = [
        {"role": "user", "content": "request_id req_demo_401 返回 401"},
        {"role": "tool", "name": "query_call_log", "tool_call_id": "x", "content": json.dumps({"status": "SUCCESS", "data": {"found": True, "appId": "app_demo", "endpoint": "/v1/chat", "httpStatus": 401, "errorCode": "AUTH_KEY_EXPIRED"}})},
    ]
    second = await _events(service, messages, tools)
    names = {call.name for call in second[0]["tool_calls"]}
    assert names == {"query_api_key_status", "query_error_code"}


@pytest.mark.asyncio
async def test_offline_fallback_plans_independent_billing_queries_in_parallel_batch():
    service = LLMService()
    tools = AgentRuntime().llm_tools_for_skills(["customer-support"])
    events = await _events(service, [{"role": "user", "content": "为什么 2026-08 的账单费用比套餐高，帮我核对用量"}], tools)
    names = {call.name for call in events[0]["tool_calls"]}
    assert names == {"query_plan", "query_usage", "query_bill"}
    for call in events[0]["tool_calls"]:
        if call.name in {"query_usage", "query_bill"}:
            assert call.arguments == {"month": "2026-08"}
