import pytest

from app.agent.agent_skill_policy import validate_target_skill_contracts
from app.agent.graph.answer_content import ensure_reference_citations
from app.agent.graph.answer_safety import safe_quality_gate_answer
from app.agent.routing_policy import routing_policy
from app.db.models import User
from app.evaluation.skills import validate_skill_contract
from app.skill_runtime.registry import skill_registry
from app.tools.base import ToolExecutionContext
from app.tools.registry import tool_registry


def _user() -> User:
    return User(id=99, username="support-skill-tester", password="x", role="USER")


def test_target_and_shared_skill_contracts_are_complete():
    validate_target_skill_contracts(skill_registry)
    for skill in skill_registry.definitions():
        assert validate_skill_contract(skill, tool_registry.names())["pass"] is True


def test_quality_gate_fails_closed_for_unfinished_high_risk_request():
    question = "我想申请退款"
    answer = safe_quality_gate_answer(
        {"question": question, "routing_decision": routing_policy.decide(question).to_dict(), "handoff_success": False},
        ["billing:audit_billing_safety"],
    )
    assert "不能确认" in answer


def test_grounded_answer_gets_stable_citations_before_knowledge_quality_gate():
    answer = ensure_reference_citations(
        "退款申请需要先核验订单和账单事实。",
        [{"fileName": "refund-policy.md", "pageNumber": 1}],
    )

    assert answer.endswith("来源#1: refund-policy.md | 第1页")


@pytest.mark.asyncio
async def test_escalation_script_assesses_real_handoff_need():
    result = await tool_registry.execute(
        "run_skill_script",
        {"skill": "escalation", "script": "assess_escalation", "arguments": {"question": "我怀疑重复扣费，需要人工处理", "payment_dispute": True}},
        ToolExecutionContext(user=_user(), active_skills=frozenset({"escalation"})),
    )
    assert result.status == "SUCCESS"
    assert result.data["shouldEscalate"] is True
