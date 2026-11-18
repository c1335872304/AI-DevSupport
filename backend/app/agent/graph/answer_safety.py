from __future__ import annotations

import logging
import re
import time
from typing import TYPE_CHECKING

from app.agent.graph.answer_content import ensure_reference_citations, retrieval_unavailable_answer
from app.agent.graph.state import CustomerServiceState
from app.agent.streaming import remove_credential_output_examples
from app.core.redaction import redact_text
from app.skill_runtime.registry import skill_registry

if TYPE_CHECKING:
    from app.agent.runtime import SendJson

logger = logging.getLogger(__name__)


_HANDOFF_SUCCESS_PATTERNS = (
    "已创建人工工单",
    "已经创建人工工单",
    "已成功创建人工工单",
    "已成功转人工",
    "已经转接人工",
    "已为您转接人工",
)


def handoff_required(state: CustomerServiceState) -> bool:
    """Use the same policy/evidence decision as the write node and final gate.

    The classifier is a planning hint; it cannot override a completed decision.
    Preserve independent policy and execution risk checks, including failed writes.
    """
    routing = state.get("routing_decision") or {}
    decision = (state.get("evidence_summary") or {}).get("handoffDecision") or {}
    return bool(
        str(routing.get("riskLevel") or "").upper() == "HIGH"
        or routing.get("requiresHandoffAfterSummary")
        or decision.get("required")
        or state.get("handoff_attempted")
        or (state.get("diagnosis_decision") or {}).get("handoffRequired")
        or ("required" not in decision and (state.get("intent_classification") or {}).get("needs_human"))
    )


def safe_quality_gate_answer(state: CustomerServiceState, failed_gates: list[str]) -> str:
    """Fail closed when the final answer does not satisfy a declared gate."""
    if handoff_required(state):
        rules = (state.get("routing_decision") or {}).get("matchedRules") or ()
        if "high_risk_billing_or_contract_operation" not in rules:
            if state.get("handoff_success"):
                return "相关请求已提交人工客服处理，具体结果需等待人工核验。"
            return "本次未能确认人工工单创建成功。请稍后重试，或通过官方人工客服渠道联系。"
        if state.get("handoff_success"):
            return "相关请求已提交人工客服处理，但退款、扣费或套餐结果仍需人工核验，当前不能自动确认业务结果。"
        return "该请求涉及退款、扣费或账户操作，本轮安全校验未通过，暂不能确认处理结果；人工工单也尚未确认创建成功，请稍后重试或通过官方人工渠道处理。"
    if retrieval_answer := retrieval_unavailable_answer(state):
        return retrieval_answer
    if any("knowledge" in name for name in failed_gates):
        return "当前知识库证据不足或引用校验未通过，暂时不能安全确认这个结论。请补充问题细节，或稍后重试获取可核验的知识库依据。"
    if any("api" in name for name in failed_gates):
        return "当前 API 诊断结果未通过安全校验，暂时不能确认原因。请提供 request_id、接口路径或错误码，以便继续核验。"
    return "当前回答未通过安全校验，暂时不能确认结论，请稍后重试。"


def remove_unsupported_rate_limit_claims(answer: str) -> str:
    """Delete ungrounded personal rate-limit claims without composing new facts.

    The quality gate is deliberately a filter, not a second answer generator.
    This is called only after the API gate established that the answer contains
    an unsupported personal claim and no scoped log/statistics support exists.
    """
    kept: list[str] = []
    removed = False
    for line in re.split(r"(?<=[\n。！？；])", answer):
        normalized = re.sub(r"\s+", "", line).lower()
        is_empty_confirmation_header = normalized in {"已核验：", "已确认：", "**当前已确认的信息：**"}
        claims_verified_rate_limit = any(
            marker in normalized for marker in (
                "已核验错误码为rate_limit_exceeded", "已确认错误码为rate_limit_exceeded",
            )
        )
        claims_customer_incident = any(
            token in normalized
            for token in (
                "本次调用触发了限流",
                "本次或近期调用触发了限流",
                "该请求触发了限流",
                "该请求返回http429",
            )
        )
        claims_unanchored_diagnostic_query = any(
            token in normalized
            for token in ("当前已确认的信息", "我查询了错误码", "没有找到与该错误码相关的记录")
        )
        if is_empty_confirmation_header or claims_verified_rate_limit or claims_customer_incident or claims_unanchored_diagnostic_query:
            removed = True
            continue
        kept.append(line)

    filtered = re.sub(r"\n{3,}", "\n\n", "".join(kept)).strip()
    if not removed:
        return answer
    non_citation_lines = [line for line in filtered.splitlines() if line.strip() and not line.lstrip().startswith("来源#")]
    if non_citation_lines:
        return filtered
    citations = [line for line in filtered.splitlines() if line.lstrip().startswith("来源#")]
    fallback = "暂时无法核验具体请求是否被限流；请提供 request_id、HTTP 状态/错误码、接口地址或发生时间。"
    return "\n\n".join([fallback, "\n".join(citations)] if citations else [fallback])


async def audit_answer(state: CustomerServiceState, *, send_json: SendJson, preview: bool = False) -> dict:
    """Check a streaming preview or the final answer against the same evidence gates."""
    generation_label = (state.get("generation_id") or "-")[:8]
    answer = str(state.get("draft_answer") or "").strip()
    if not answer:
        answer = "当前信息不足，暂时无法安全确认该问题。"
    sanitized = remove_credential_output_examples(answer)
    credential_example_filtered = sanitized != answer
    answer = redact_text(sanitized)
    evidence_summary = dict(state.get("evidence_summary") or {})
    verified_facts = [item for item in (evidence_summary.get("verifiedFacts") or []) if isinstance(item, dict)]
    answer = ensure_reference_citations(answer, list((state.get("references") or {}).values()))

    # Runtime-level transactional guard: a model may only claim a successful human
    # handoff after the real write Tool returned SUCCESS. This complements the system
    # prompt with a deterministic customer-service safety boundary.
    changed = answer != str(state.get("draft_answer") or "").strip()
    if not state.get("handoff_success"):
        claimed = any(token in answer for token in _HANDOFF_SUCCESS_PATTERNS)
        if claimed:
            for token in _HANDOFF_SUCCESS_PATTERNS:
                answer = answer.replace(token, "人工工单尚未确认创建成功")
            if state.get("handoff_attempted"):
                answer += "\n\n当前人工转接操作未确认成功，请稍后重试或使用其他官方人工渠道。"
            changed = True
    quality_gate_results: dict[str, dict] = {}
    repair_payloads: dict[str, tuple[str, str, dict]] = {}
    trace = state.get("skill_trace")
    tool_counts = (trace.summary().get("toolCounts") if trace else {}) or {}
    tool_results = [{"tool": name, "count": count} for name, count in tool_counts.items()]
    target_handoff = dict(evidence_summary.get("handoffDecision") or {})
    high_risk = str((state.get("routing_decision") or {}).get("riskLevel") or "").upper() == "HIGH"
    should_escalate = handoff_required(state)
    references = list((state.get("references") or {}).values())
    for skill_name in list(state.get("active_skills") or []):
        skill = skill_registry.get(skill_name)
        if not skill or not skill.quality_gate:
            continue
        payload = {
            "answer": answer,
            "toolResults": tool_results,
            "verifiedFacts": verified_facts,
            "diagnosisDecision": state.get("diagnosis_decision") or {},
            "entities": dict(state.get("entities") or {}),
            "results": references,
            "highRisk": high_risk,
            "handoffId": state.get("handoff_id"),
            "requiresEvidence": skill_name == "knowledge",
            "issue_understood": bool(state.get("question")),
            # The bounded diagnosis renderer uses matched local service rules,
            # not retrieved document claims. Do not label those as RAG-verified.
            "knowledge_needed": not bool(state.get("diagnosis_decision")) and (skill_name == "knowledge" or "search_knowledge" in tool_counts),
            "knowledge_verified": bool(references),
            "account_specific": bool(state.get("entities")),
            "account_verified": bool(tool_counts),
            "claims_account_status": False,
            "next_step_present": bool(answer),
            "should_escalate": should_escalate,
            "handoff_needed": should_escalate,
            "handoff_created": bool(state.get("handoff_success")),
            "summary": f"客户诉求：{state.get('question') or ''}\n客服答复：{answer}",
            "step_count": len((trace.summary().get("toolBatches") if trace else []) or []),
            "failed_rounds": 0,
            "handoff_planned": bool(target_handoff.get("required")),
            "explicit_handoff": "explicit_handoff_request" in ((state.get("routing_decision") or {}).get("matchedRules") or []),
            "unsafe_action": False,
        }
        started = time.monotonic()
        print(f"[GEN {generation_label}] quality_gate_start skill={skill_name} gate={skill.quality_gate}", flush=True)
        try:
            result = await skill_registry.run_script(skill_name, skill.quality_gate, payload)
            result = result if isinstance(result, dict) else {"passed": False, "warnings": ["invalid_gate_result"]}
        except Exception as exc:
            result = {"passed": False, "warnings": [f"gate_error:{type(exc).__name__}"]}
            logger.warning("[GEN %s] quality gate failed skill=%s gate=%s: %s", generation_label, skill_name, skill.quality_gate, exc)
        passed = result.get("passed", result.get("pass")) is True
        result = {**result, "passed": passed, "skill": skill_name, "gate": skill.quality_gate, "durationMs": int((time.monotonic() - started) * 1000)}
        key = f"{skill_name}:{skill.quality_gate}"
        quality_gate_results[key] = result
        if skill_name == "api-diagnostic" and not result.get("passed"):
            repair_payloads[key] = (skill_name, skill.quality_gate, payload)
        if trace and not preview:
            trace.record_quality_gate(skill_name, skill.quality_gate, result)
        print(
            f"[GEN {generation_label}] quality_gate_end skill={skill_name} gate={skill.quality_gate} "
            f"passed={passed} warnings={result.get('warnings') or []}",
            flush=True,
        )
        if not preview:
            await send_json(
                {
                    "type": "quality_gate",
                    "skill": skill_name,
                    "gate": skill.quality_gate,
                    "passed": bool(result.get("passed")),
                    "warnings": result.get("warnings") or [],
                    "generationId": state.get("generation_id"),
                    "timestamp": int(time.time() * 1000),
                }
            )
    failed_gate_keys = [key for key, item in quality_gate_results.items() if not bool(item.get("passed"))]
    repairable_reasons = {
        "unsupported_personal_rate_limit_claim",
        "unsupported_unanchored_diagnostic_query_claim",
    }
    repaired_gates = []
    quality_gate_action = "passed"
    for key, (skill_name, gate, payload) in repair_payloads.items():
        reasons = quality_gate_results[key].get("blockingWarnings")
        if not isinstance(reasons, list) or not reasons or any(reason not in repairable_reasons for reason in reasons):
            continue
        filtered = remove_unsupported_rate_limit_claims(answer)
        if filtered == answer:
            continue
        candidate = ensure_reference_citations(filtered, references)
        try:
            result = await skill_registry.run_script(skill_name, gate, {**payload, "answer": candidate})
        except Exception:
            logger.warning("Quality gate recheck failed: %s", key)
            continue
        if isinstance(result, dict) and result.get("passed") is True:
            answer = candidate
            changed = True
            quality_gate_results[key]["filtered"] = True
            repaired_gates.append(key)
    remaining_failed_gate_keys = [key for key in failed_gate_keys if key not in repaired_gates]
    quality_gate_blocked = bool(remaining_failed_gate_keys)
    if repaired_gates and not quality_gate_blocked:
        quality_gate_action = "filtered_unsupported_claims"
        if not preview:
            await send_json(
                {
                    "type": "quality_gate_filtered",
                    "gates": repaired_gates,
                    "action": quality_gate_action,
                    "generationId": state.get("generation_id"),
                    "timestamp": int(time.time() * 1000),
                }
            )
    if quality_gate_blocked:
        answer = safe_quality_gate_answer(state, remaining_failed_gate_keys)
        changed = True
        quality_gate_action = "fail_closed"
        print(
            f"[GEN {generation_label}] quality_gate_blocked "
            f"gates={remaining_failed_gate_keys} action={quality_gate_action}",
            flush=True,
        )
        if not preview:
            await send_json(
                {
                    "type": "quality_gate_blocked",
                    "gates": remaining_failed_gate_keys,
                    "action": quality_gate_action,
                    "generationId": state.get("generation_id"),
                    "timestamp": int(time.time() * 1000),
                }
            )
    from app.diagnosis.evidence import expired_current_facts
    if expired_current_facts(verified_facts):
        answer = "部分当前状态证据已过期，暂时不能确认当前状态或恢复情况，请重新查询后再判断。"
        if state.get("handoff_success"):
            answer += "人工工单已确认创建，后续由人工核查。"
        changed, quality_gate_blocked, quality_gate_action = True, True, "expired_current_evidence"
        quality_gate_results["evidence_freshness"] = {"passed": False, "gate": "evidence_freshness"}
    if credential_example_filtered:
        quality_gate_results["credential_example"] = {
            "passed": True, "filtered": True, "warnings": ["credential_example_output_removed"],
        }
        if quality_gate_action == "passed":
            quality_gate_action = "filtered_credential_example"
    return {
        "final_answer": answer,
        "final_chunks": [answer] if changed else list(state.get("final_chunks") or [answer]),
        "quality_gate_results": quality_gate_results,
        "quality_gate_blocked": quality_gate_blocked,
        "quality_gate_action": quality_gate_action,
    }
