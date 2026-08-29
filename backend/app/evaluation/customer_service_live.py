from __future__ import annotations

import json
import time
from typing import Any

from app.accounting.llm_usage import capture_llm_usage
from app.agent.types import AgentToolCall
from app.skill_runtime.registry import skill_registry
from app.skill_runtime.router import skill_router
from app.tools.registry import tool_registry


BUSINESS_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "mcp__commerce__get_refund_status",
            "description": "Read the authenticated customer's refund status. Use for customer-specific refund-state questions; never infer this from policy documents.",
            "parameters": {"type": "object", "properties": {"refund_id": {"type": "string"}}, "required": ["refund_id"], "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mcp__commerce__get_order_status",
            "description": "Read the authenticated customer's order and shipment status.",
            "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"], "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mcp__billing__get_payment_status",
            "description": "Read the authenticated customer's payment/charge status.",
            "parameters": {"type": "object", "properties": {"payment_id": {"type": "string"}}, "required": ["payment_id"], "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mcp__account__get_account_status",
            "description": "Read the authenticated customer's account state. Never use this for another customer's account.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
]


def _fixture_for(case: dict[str, Any], call: AgentToolCall, call_index: int) -> dict[str, Any]:
    fixtures = (case.get("fixtures") or {}).get("toolResults") or {}
    configured = fixtures.get(call.name)
    if isinstance(configured, list):
        configured = configured[min(call_index, len(configured) - 1)] if configured else None
    if isinstance(configured, dict):
        return dict(configured)
    if call.name == "search_knowledge":
        return {"status": "SUCCESS", "durationMs": 120, "data": {"results": [dict(item) for item in case.get("evidence") or []]}}
    if call.name == "create_support_handoff":
        return {"status": "SUCCESS", "durationMs": 180, "data": {"handoffId": "CS_EVAL_001", "status": "OPEN", "priority": call.arguments.get("priority", "NORMAL")}}
    if call.name == "get_support_handoff":
        return {"status": "SUCCESS", "durationMs": 80, "data": {"found": True, "handoff": {"handoffId": "CS_EVAL_001", "status": "OPEN"}}}
    if call.name == "read_skill_reference":
        return {"status": "SUCCESS", "durationMs": 10, "data": {"content": "Customer-service evaluation fixture reference."}}
    if call.name == "run_skill_script":
        return {"status": "SUCCESS", "durationMs": 15, "data": {"pass": True, "classification": "eval", "warnings": []}}
    if call.name == "activate_skill":
        return {"status": "SUCCESS", "durationMs": 5, "data": {"skill": call.arguments.get("skill")}}
    return {"status": "SUCCESS", "durationMs": 100, "data": {"ok": True}}


def _attach_references(data: dict[str, Any], references: dict[str, dict[str, Any]]) -> None:
    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list):
        return
    for raw in results:
        if not isinstance(raw, dict):
            continue
        source_id = int(raw.get("sourceId") or (len(references) + 1))
        key = str(source_id)
        references[key] = {
            "sourceId": source_id,
            "fileMd5": raw.get("fileMd5"),
            "fileName": raw.get("fileName"),
            "pageNumber": raw.get("pageNumber"),
            "chunkId": raw.get("chunkId"),
            "textContent": raw.get("textContent") or raw.get("text") or "",
        }
        raw["referenceNumber"] = source_id
        raw["citation"] = f"来源#{source_id}: {raw.get('fileName') or raw.get('fileMd5') or '知识库'}"


def _tools_for(active_skills: list[str], with_skill: bool) -> list[dict[str, Any]]:
    if not with_skill:
        # A fair No-Skill baseline keeps the same business capabilities and removes
        # only Skill instructions/meta-tools. Otherwise the comparison would measure
        # missing tools instead of the value of the Skill workflow.
        names = {
            name for name in tool_registry.names()
            if name not in {"activate_skill", "read_skill_reference", "run_skill_script"}
        }
        return tool_registry.llm_tools(names) + BUSINESS_TOOL_SCHEMAS
    allowed = {"activate_skill"}
    for name in active_skills:
        definition = skill_registry.get(name)
        if definition:
            allowed.update(definition.allowed_tools)
    return tool_registry.llm_tools(allowed) + BUSINESS_TOOL_SCHEMAS


async def run_live_customer_service_case(case: dict[str, Any], *, llm_service: Any, with_skill: bool = True) -> dict[str, Any]:
    question = str(case.get("question") or "")
    active_skills = list(dict.fromkeys(skill_router.route(question))) if with_skill else []
    messages = llm_service.build_agent_messages(
        question,
        [],
        skill_catalog=skill_registry.catalog_prompt() if with_skill else "",
        skill_context=skill_registry.build_prompt(active_skills) if active_skills else "",
    )
    tool_calls: list[dict[str, Any]] = []
    references: dict[str, dict[str, Any]] = {}
    final_parts: list[str] = []
    per_tool_count: dict[str, int] = {}
    started = time.monotonic()
    first_token_ms = 0.0

    with capture_llm_usage() as usage_meter:
        max_steps = max(1, min(10, int(case.get("liveMaxSteps") or 6)))
        for step in range(1, max_steps + 1):
            calls: list[AgentToolCall] = []
            turn_parts: list[str] = []
            async for event in llm_service.stream_agent_turn(messages, _tools_for(active_skills, with_skill)):
                if event.get("type") == "content":
                    chunk = str(event.get("content") or "")
                    if chunk:
                        turn_parts.append(chunk)
                elif event.get("type") == "tool_calls":
                    calls = list(event.get("tool_calls") or [])
            if turn_parts and not calls:
                if not first_token_ms:
                    first_token_ms = (time.monotonic() - started) * 1000
                final_parts.extend(turn_parts)
                break
            if not calls:
                break

            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": call.id, "type": "function", "function": {"name": call.name, "arguments": json.dumps(call.arguments, ensure_ascii=False)}}
                    for call in calls
                ],
            })
            for call in calls:
                index = per_tool_count.get(call.name, 0)
                per_tool_count[call.name] = index + 1
                fixture = _fixture_for(case, call, index)
                status = str(fixture.get("status") or "SUCCESS").upper()
                data = dict(fixture.get("data") or {}) if isinstance(fixture.get("data"), dict) else fixture.get("data")
                duration_ms = int(fixture.get("durationMs") or 1)
                if call.name == "search_knowledge" and status == "SUCCESS" and isinstance(data, dict):
                    _attach_references(data, references)
                if call.name == "activate_skill" and status == "SUCCESS" and with_skill:
                    skill_name = str(call.arguments.get("skill") or "")
                    if skill_registry.get(skill_name) and skill_name not in active_skills:
                        # Keep the product invariant: default support + at most one specialist.
                        specialists = [name for name in active_skills if name != "customer-support"]
                        if specialists and skill_name != "customer-support":
                            active_skills.remove(specialists[0])
                        active_skills.append(skill_name)
                        messages[0]["content"] += "\n\n" + skill_registry.build_prompt([skill_name])
                tool_calls.append({
                    "id": call.id,
                    "step": step,
                    "name": call.name,
                    "arguments": dict(call.arguments),
                    "status": status,
                    "durationMs": duration_ms,
                    "error": fixture.get("error"),
                })
                payload = {"status": status, "data": data, "durationMs": duration_ms}
                if fixture.get("error"):
                    payload["error"] = fixture.get("error")
                messages.append({"role": "tool", "tool_call_id": call.id, "name": call.name, "content": json.dumps(payload, ensure_ascii=False)})
        if not final_parts:
            async for chunk in llm_service.stream_messages(messages, force_no_tools=True):
                if not first_token_ms:
                    first_token_ms = (time.monotonic() - started) * 1000
                final_parts.append(str(chunk))

    total_ms = (time.monotonic() - started) * 1000
    evidence_used = [references[key] for key in sorted(references, key=lambda x: int(x))]
    return {
        "caseId": case.get("id"),
        "question": question,
        "answer": "".join(final_parts).strip(),
        "activeSkills": active_skills,
        "toolCalls": tool_calls,
        "references": references,
        "evidence": evidence_used or list(case.get("evidence") or []),
        "timing": {"totalMs": round(total_ms, 2), "firstTokenMs": round(first_token_ms, 2)},
        "usage": {"promptTokens": usage_meter.prompt_tokens, "completionTokens": usage_meter.completion_tokens, "totalTokens": usage_meter.total_tokens},
        "fixtureMode": True,
    }
