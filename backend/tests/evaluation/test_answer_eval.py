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
    for name in ("customer-support", "api-diagnostic", "billing", "knowledge", "escalation"):
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


@pytest.mark.parametrize(("clause_citation", "passed"), [
    ("", False), ("（来源#2）", False), ("（来源#1）", True),
])
def test_high_score_cannot_mask_a_missing_required_claim_citation(clause_citation, passed):
    case = {"id": "clause-citations", "evidence": [
                {"sourceId": 1, "textContent": "最多三次。仅适用于 v2。"},
                {"sourceId": 2, "textContent": "认证使用访问令牌。"},
            ],
            "rubric": {"requiredFacts": [{"anyOf": ["最多三次"], "sourceIds": [1]}]}}
    result = evaluate_answer(f"最多三次{clause_citation}；仅适用于 v2（来源#1）。\n\n来源#1: doc.md", case)
    assert result.score >= result.details["passScore"]
    assert result.passed is passed
    assert result.details["citations"]["passedFactCount"] == int(passed)


def test_whole_answer_fact_match_does_not_borrow_a_navigation_citation():
    case = {"id": "navigation", "evidence": [{"sourceId": 1, "textContent": "每批支持十行。每行上限是百字。"}],
            "rubric": {"requiredFacts": [{"allOf": ["十行", "百字"], "sourceIds": [1]}]}}
    result = evaluate_answer("每批支持十行。每行上限是百字。\n\n来源#1: doc.md", case)
    assert result.details["facts"][0]["matched"]
    assert not result.details["facts"][0]["citationPass"]
    assert not result.passed


def test_later_explicitly_cited_restating_unit_satisfies_required_fact():
    case = {"id": "restated-claim",
            "evidence": [{"sourceId": 1, "textContent": "请配置环境变量。"}],
            "rubric": {"requiredFacts": [{"anyOf": ["环境变量"], "sourceIds": [1]}]}}
    answer = "先说明环境变量的设置方式。\n\n配置环境变量（来源#1）。"
    result = evaluate_answer(answer, case)
    assert result.passed
    assert result.details["facts"][0]["unitCitations"] == [1]


def test_source_list_title_cannot_satisfy_a_required_fact():
    case = {"id": "source-title",
            "evidence": [{"sourceId": 1, "textContent": "请配置环境变量。"}],
            "rubric": {"requiredFacts": [{"anyOf": ["环境变量"], "sourceIds": [1]}]}}
    answer = "先说明配置方式。\n\n- 来源#1: 环境变量.md"
    result = evaluate_answer(answer, case)
    assert not result.passed
    assert not result.details["facts"][0]["matched"]


def test_same_line_post_punctuation_citation_only_applies_to_preceding_clause():
    case = {"id": "post-punctuation",
            "evidence": [{"sourceId": 1, "textContent": "支持重试三次。"}],
            "rubric": {"requiredFacts": [
                {"anyOf": ["重试三次"], "sourceIds": [1]},
                {"anyOf": ["适用于 v2"], "sourceIds": [1]},
            ]}}
    result = evaluate_answer("支持重试三次。 （来源#1）仅适用于 v2。\n\n来源#1: guide.md", case)
    assert [fact["citationPass"] for fact in result.details["facts"]] == [True, False]
    assert not result.passed


def test_material_date_accepts_equivalent_month_format_but_not_a_different_month():
    case = {"id": "date-format", "rubric": {}}
    evidence = [{"textContent": "规则于2026年10月生效。"}]
    known = evaluate_answer("规则于 2026 年 10 月生效。", case, evidence=evidence)
    changed = evaluate_answer("规则于 2026 年 11 月生效。", case, evidence=evidence)
    assert known.details["hallucination"]["unsupportedMaterialNumbers"] == []
    assert changed.details["hallucination"]["unsupportedMaterialNumbers"] == ["2026-11"]


def test_strict_document_reads_derive_only_from_frozen_evidence():
    from app.evaluation.customer_service_live import _fixture_for

    file_md5 = "a" * 32
    case = {"strictToolFixtures": True, "evidence": [
        {"fileMd5": file_md5, "fileName": "guide.md", "chunkId": 7,
         "pageNumber": 2, "textContent": "The frozen excerpt."},
    ]}
    listing = _fixture_for(case, AgentToolCall("list", "list_documents", {"keyword": "guide"}), 0)
    assert listing["data"]["documents"] == [{"fileMd5": file_md5, "fileName": "guide.md"}]
    read = _fixture_for(case, AgentToolCall("read", "get_document", {"file_md5": file_md5, "chunk_id": 7}), 0)
    assert read["data"]["text"] == "The frozen excerpt."
    denied = _fixture_for(case, AgentToolCall("other", "get_document", {"file_md5": "b" * 32}), 0)
    assert denied["status"] == "DENIED"


@pytest.mark.parametrize(("page", "unsupported"), [(1, []), (9, ["9页"])])
def test_only_verified_citation_page_is_excluded_from_business_numbers(page, unsupported):
    references = {"1": {"pageNumber": 1, "textContent": "文档说明应使用指数退避。"}}
    result = evaluate_answer(
        f"文档说明应使用指数退避（来源#1: retry.md | 第{page}页）。",
        {"id": "citation-page", "rubric": {}},
        evidence=list(references.values()),
        references=references,
    )
    assert result.details["hallucination"]["unsupportedMaterialNumbers"] == unsupported


@pytest.mark.parametrize(("source", "groundedness"), [(1, 1.0), (2, 0.0)])
def test_bullet_group_uses_matching_tail_citation(source, groundedness):
    result = evaluate_answer(
        f"- 每批最多 10 行。\n- 支持 256 维。\n\n（来源#{source}）",
        {"id": "group", "rubric": {"requiredFacts": [
            {"anyOf": ["10 行"], "sourceIds": [1]},
            {"anyOf": ["256 维"], "sourceIds": [1]},
        ]}},
        references={"1": {"textContent": "每批最多 10 行，支持 256 维。"}, "2": {"textContent": "认证配置。"}},
    )
    assert result.metrics["groundedness"] == groundedness


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
