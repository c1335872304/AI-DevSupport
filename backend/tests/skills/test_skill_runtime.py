import pytest

from app.agent.agent_skill_policy import SHARED_NODE_SKILLS, TARGET_AGENT_SKILLS
from app.agent.routing_policy import routing_policy
from app.db.models import User
from app.skill_runtime.registry import skill_registry
from app.tools.base import ToolExecutionContext
from app.tools.registry import tool_registry


def _user() -> User:
    return User(id=1, username="skill-tester", password="x", role="USER")


def test_only_target_and_shared_skills_are_discovered():
    assert set(skill_registry.names()) == {"customer-support", "escalation", "api-diagnostic", "billing", "knowledge"}
    assert set(TARGET_AGENT_SKILLS.values()) == {"api-diagnostic", "billing", "knowledge"}
    assert set(SHARED_NODE_SKILLS.values()) == {"customer-support", "escalation"}


def test_routing_policy_is_the_only_specialist_selection_contract():
    assert routing_policy.decide("登录一直报错，验证码收不到").selected_agents == ("knowledge",)
    assert routing_policy.decide("别排查了，直接帮我转人工客服").requires_handoff_after_summary is True
    assert routing_policy.decide("不用人工了，问题已经解决").requires_handoff_after_summary is False


@pytest.mark.asyncio
async def test_reference_tool_requires_declared_target_skill():
    denied = await tool_registry.execute(
        "read_skill_reference",
        {"skill": "api-diagnostic", "reference": "references/api-evidence-order.md"},
        ToolExecutionContext(user=_user()),
    )
    assert denied.status == "DENIED"
    allowed = await tool_registry.execute(
        "read_skill_reference",
        {"skill": "api-diagnostic", "reference": "references/api-evidence-order.md"},
        ToolExecutionContext(user=_user(), active_skills=frozenset({"api-diagnostic"})),
    )
    assert allowed.status == "SUCCESS"
