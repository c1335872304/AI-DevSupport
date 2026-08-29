from __future__ import annotations

import pytest

from app.agent.runtime import AgentRuntime
from app.db.models import User
from app.agent.llm import llm_service
from app.skill_runtime.registry import skill_registry
from app.skill_runtime.router import skill_router
from app.tools.base import ToolExecutionContext
from app.tools.registry import tool_registry


def _user() -> User:
    return User(id=1, username="skill-tester", password="x", role="USER")


def test_customer_service_skills_are_discovered_and_default_support_is_always_active():
    assert set(skill_registry.names()) == {"customer-support", "troubleshooting", "escalation"}
    assert skill_router.route("你好") == ["customer-support"]
    assert skill_router.route("退款政策是什么") == ["customer-support"]


def test_specialist_routing_keeps_customer_support_as_base_skill():
    assert skill_router.route("登录一直报错，验证码收不到") == ["customer-support", "troubleshooting"]
    assert skill_router.route("别排查了，直接帮我转人工客服") == ["customer-support", "escalation"]
    assert skill_router.route("不用人工了，问题已经解决") == ["customer-support"]


def test_skill_prompt_is_progressive_not_reference_dump():
    prompt = skill_registry.build_prompt(["customer-support"])
    assert "Customer Support" in prompt
    assert "references/account-data-boundary.md" in prompt
    assert "订单状态必须由" not in prompt


@pytest.mark.asyncio
async def test_reference_tool_requires_active_customer_support_skill():
    denied = await tool_registry.execute(
        "read_skill_reference",
        {"skill": "customer-support", "reference": "references/account-data-boundary.md"},
        ToolExecutionContext(user=_user()),
    )
    assert denied.status == "DENIED"

    allowed = await tool_registry.execute(
        "read_skill_reference",
        {"skill": "customer-support", "reference": "references/account-data-boundary.md"},
        ToolExecutionContext(user=_user(), active_skills=frozenset({"customer-support"})),
    )
    assert allowed.status == "SUCCESS"
    assert "账户特定事实" in allowed.data["content"]


@pytest.mark.asyncio
async def test_declared_customer_support_script_runs_as_controlled_tool():
    result = await tool_registry.execute(
        "run_skill_script",
        {
            "skill": "customer-support",
            "script": "classify_support_intent",
            "arguments": {"question": "我的订单是否发货了？"},
        },
        ToolExecutionContext(user=_user(), active_skills=frozenset({"customer-support"})),
    )
    assert result.status == "SUCCESS"
    assert result.data["category"] == "order"
    assert result.data["requiresPrivateData"] is True


@pytest.mark.asyncio
async def test_agent_injects_customer_support_and_only_relevant_tools(monkeypatch):
    runtime = AgentRuntime()
    seen = {}

    async def fake_turn(messages, tools):
        seen["system"] = messages[0]["content"]
        seen["tool_names"] = {item["function"]["name"] for item in tools}
        yield {"type": "content", "content": "done"}

    monkeypatch.setattr(llm_service, "stream_agent_turn", fake_turn)
    events = []

    async def append_event(payload):
        events.append(payload)

    async def append_chunk(_chunk):
        return None

    content, _ = await runtime.run(
        user=_user(),
        question="退款政策是什么？",
        history=[],
        generation_id="support-g1",
        send_json=append_event,
        on_chunk=append_chunk,
    )

    assert content == "done"
    assert "PaiSmart AI 客服" in seen["system"]
    assert "Skill: customer-support" in seen["system"]
    assert {"search_knowledge", "get_support_handoff", "read_skill_reference", "run_skill_script"} <= seen["tool_names"]
    assert "create_support_handoff" not in seen["tool_names"]
    assert any(event.get("type") == "skill_selected" and "customer-support" in event.get("skills", []) for event in events)


@pytest.mark.asyncio
async def test_escalation_exposes_real_handoff_tool(monkeypatch):
    runtime = AgentRuntime()
    seen = {}

    async def fake_turn(messages, tools):
        seen["tool_names"] = {item["function"]["name"] for item in tools}
        yield {"type": "content", "content": "done"}

    monkeypatch.setattr(llm_service, "stream_agent_turn", fake_turn)

    async def noop(_value):
        return None

    await runtime.run(
        user=_user(),
        question="请直接转人工客服",
        history=[],
        generation_id="support-g2",
        send_json=noop,
        on_chunk=noop,
    )
    assert "create_support_handoff" in seen["tool_names"]
    assert "customer-support" in skill_router.route("请直接转人工客服")
    assert "escalation" in skill_router.route("请直接转人工客服")

@pytest.mark.asyncio
async def test_escalation_can_replace_troubleshooting_when_skill_limit_is_full():
    result = await tool_registry.execute(
        "activate_skill",
        {"skill": "escalation"},
        ToolExecutionContext(
            user=_user(),
            active_skills=frozenset({"customer-support", "troubleshooting"}),
        ),
    )
    assert result.status == "SUCCESS"
    assert result.data["replaceSkill"] == "troubleshooting"
