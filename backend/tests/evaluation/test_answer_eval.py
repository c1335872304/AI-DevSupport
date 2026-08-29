from __future__ import annotations

import pytest

from app.agent.types import AgentToolCall
from app.evaluation.answer import evaluate_answer, parse_judge_json, run_live_answer_case, validate_answer_case
from app.agent.llm import llm_service
from app.evaluation.skills import load_jsonl
from app.skill_runtime.registry import skill_registry
from app.tools.registry import tool_registry


def _case(skill: str, case_id: str):
    definition = skill_registry.get(skill)
    rows = load_jsonl(definition.root / "eval/answer.jsonl")
    return next(row for row in rows if row["id"] == case_id)


def test_all_customer_service_answer_eval_datasets_are_valid():
    for name in ("customer-support", "troubleshooting", "escalation"):
        skill = skill_registry.get(name)
        assert "eval/answer.jsonl" in skill.evals
        rows = load_jsonl(skill.root / "eval/answer.jsonl")
        assert len(rows) >= 3
        for case in rows:
            result = validate_answer_case(case)
            assert result["pass"], result


def test_grounded_refund_answer_passes():
    case = _case("customer-support", "cs-answer-1")
    answer = "退款规则：符合条件的购买可在支付后 7 天内提交退款申请（来源#1: refund-policy.md）。是否退款成功仍要按政策条件审核。"
    result = evaluate_answer(answer, case)
    assert result.passed
    assert result.metrics["groundedness"] == 1.0


def test_customer_specific_order_status_must_not_be_invented():
    case = _case("customer-support", "cs-answer-2")
    bad = "你的订单已经发货。下一步请等待物流更新（来源#1: account-data-boundary.md）。"
    result = evaluate_answer(bad, case)
    assert not result.passed
    assert result.details["hallucination"]["forbiddenHits"]


def test_failed_handoff_must_not_be_reported_as_success():
    case = _case("escalation", "es-answer-3")
    result = evaluate_answer("已创建人工工单，请等待。", case)
    assert not result.passed
    assert result.details["hallucination"]["forbiddenHits"]


def test_llm_judge_json_parser_accepts_fenced_json():
    raw = '''```json
    {"factualCorrectness":0.9,"groundedness":0.8,"completeness":0.7,"citationQuality":1.0,"instructionFollowing":0.9,"uncertaintyCalibration":0.8,"rationale":"ok"}
    ```'''
    parsed = parse_judge_json(raw)
    assert parsed["citationQuality"] == 1.0


@pytest.mark.asyncio
async def test_live_answer_sandbox_captures_customer_service_citation(monkeypatch):
    case = _case("customer-support", "cs-answer-1")
    turn = 0

    async def fake_agent_turn(messages, tools):
        nonlocal turn
        turn += 1
        if turn == 1:
            yield {"type": "tool_calls", "tool_calls": [AgentToolCall("q1", "search_knowledge", {"query": "退款政策"})]}
        else:
            yield {"type": "content", "content": "符合条件的购买可在支付后 7 天内提交退款申请（来源#1: refund-policy.md）。"}

    monkeypatch.setattr(llm_service, "stream_agent_turn", fake_agent_turn)
    artifact = await run_live_answer_case(case, registry=skill_registry, llm_service=llm_service, tool_registry=tool_registry, with_skill=True)
    assert set(artifact["references"]) == {"1"}
    assert "customer-support" in artifact["trace"]["activeSkills"]
    result = evaluate_answer(artifact["answer"], case, evidence=artifact["evidence"], references=artifact["references"])
    assert result.passed
