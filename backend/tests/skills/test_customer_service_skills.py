from __future__ import annotations

import pytest

from app.agent.runtime import AgentRuntime
from app.agent.types import AgentToolCall
from app.db.models import User
from app.agent.llm import llm_service
from app.evaluation.skills import evaluate_behavior_trace, evaluate_routing_case, load_jsonl, validate_skill_contract
from app.skill_runtime.registry import skill_registry
from app.skill_runtime.router import skill_router
from app.skill_runtime.trace import SkillTrace
from app.tools.base import ToolExecutionContext, ToolResult
from app.tools.registry import tool_registry


def _user() -> User:
    return User(id=99, username="support-skill-tester", password="x", role="USER")


def test_skill_contracts_are_customer_service_specific_and_complete():
    for name in ("customer-support", "troubleshooting", "escalation"):
        skill = skill_registry.get(name)
        result = validate_skill_contract(skill, tool_registry.names())
        assert result["pass"] is True, result
        assert skill.evals == ("eval/routing.jsonl", "eval/behavior.jsonl", "eval/answer.jsonl")
        assert len(load_jsonl(skill.root / "eval/routing.jsonl")) >= 3
        assert len(load_jsonl(skill.root / "eval/behavior.jsonl")) >= 3


def test_all_customer_service_routing_eval_cases_pass():
    for skill in skill_registry.definitions():
        for relative in skill.evals:
            if relative.endswith("routing.jsonl"):
                for case in load_jsonl(skill.root / relative):
                    score = evaluate_routing_case(case, skill_router)
                    assert score.passed, score.details


@pytest.mark.asyncio
async def test_support_quality_gate_detects_unverified_account_claim():
    ctx = ToolExecutionContext(user=_user(), active_skills=frozenset({"customer-support"}))
    result = await tool_registry.execute(
        "run_skill_script",
        {
            "skill": "customer-support",
            "script": "audit_support_answer",
            "arguments": {
                "issue_understood": True,
                "knowledge_needed": False,
                "account_specific": True,
                "account_verified": False,
                "claims_account_status": True,
                "next_step_present": True,
            },
        },
        ctx,
    )
    assert result.status == "SUCCESS"
    assert result.data["pass"] is False


@pytest.mark.asyncio
async def test_troubleshooting_gate_stops_infinite_repetition():
    ctx = ToolExecutionContext(user=_user(), active_skills=frozenset({"troubleshooting"}))
    result = await tool_registry.execute(
        "run_skill_script",
        {
            "skill": "troubleshooting",
            "script": "audit_troubleshooting",
            "arguments": {"step_count": 3, "failed_rounds": 2, "handoff_planned": False},
        },
        ctx,
    )
    assert result.status == "SUCCESS"
    assert result.data["pass"] is False
    assert any("人工" in item for item in result.data["warnings"])


@pytest.mark.asyncio
async def test_escalation_scripts_assess_and_summarize_real_handoff():
    ctx = ToolExecutionContext(user=_user(), active_skills=frozenset({"escalation"}))
    assessment = await tool_registry.execute(
        "run_skill_script",
        {
            "skill": "escalation",
            "script": "assess_escalation",
            "arguments": {"question": "我怀疑重复扣费，需要人工处理", "payment_dispute": True},
        },
        ctx,
    )
    assert assessment.status == "SUCCESS"
    assert assessment.data["shouldEscalate"] is True
    assert assessment.data["priority"] == "HIGH"

    summary = await tool_registry.execute(
        "run_skill_script",
        {
            "skill": "escalation",
            "script": "build_handoff_summary",
            "arguments": {
                "customer_goal": "核实重复扣费",
                "confirmed_facts": "客户报告账单出现两笔扣费",
                "attempted_steps": "已核对通用支付政策",
                "unresolved_issue": "缺少支付系统实时查询能力",
                "escalation_reason": "需要人工后台核验",
            },
        },
        ctx,
    )
    assert summary.status == "SUCCESS"
    assert "核实重复扣费" in summary.data["summary"]


def test_behavior_evaluator_rewards_parallel_customer_service_trace():
    case = {
        "id": "synthetic-support",
        "skill": "customer-support",
        "question": "compare two support policies",
        "expect": {
            "requiredSkills": ["customer-support"],
            "requiredTools": ["search_knowledge"],
            "requiredScripts": ["audit_support_answer"],
            "minParallelWidth": 2,
            "maxFailedToolCalls": 0,
            "passScore": 0.8,
        },
    }
    trace = SkillTrace(question=case["question"], initial_skills=["customer-support"], active_skills=["customer-support"])
    trace.record_batch(
        0,
        [AgentToolCall("q1", "search_knowledge", {"query": "refund"}), AgentToolCall("q2", "search_knowledge", {"query": "membership"})],
        [ToolResult(status="SUCCESS"), ToolResult(status="SUCCESS")],
    )
    trace.record_batch(
        1,
        [AgentToolCall("a1", "run_skill_script", {"skill": "customer-support", "script": "audit_support_answer", "arguments": {}})],
        [ToolResult(status="SUCCESS")],
    )
    score = evaluate_behavior_trace(trace.summary(), case)
    assert score.passed
    assert score.score >= 0.95


@pytest.mark.asyncio
async def test_runtime_emits_customer_service_skill_trace(monkeypatch):
    runtime = AgentRuntime()
    turns = 0

    async def fake_turn(messages, tools):
        nonlocal turns
        turns += 1
        if turns == 1:
            yield {
                "type": "tool_calls",
                "tool_calls": [
                    AgentToolCall(
                        "script-1",
                        "run_skill_script",
                        {"skill": "customer-support", "script": "classify_support_intent", "arguments": {"question": "退款政策是什么"}},
                    )
                ],
            }
        else:
            yield {"type": "content", "content": "done"}

    monkeypatch.setattr(llm_service, "stream_agent_turn", fake_turn)
    events = []

    async def append_event(payload): events.append(payload)
    async def ignore_chunk(_chunk): return None

    content, _ = await runtime.run(
        user=_user(), question="退款政策是什么", history=[], generation_id="support-trace", send_json=append_event, on_chunk=ignore_chunk
    )
    assert content == "done"
    trace_event = next(item for item in events if item.get("type") == "skill_trace")
    trace = trace_event["trace"]
    assert "customer-support" in trace["activeSkills"]
    assert "classify_support_intent" in trace["scriptsUsed"]
