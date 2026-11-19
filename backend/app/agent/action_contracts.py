"""Checks at the boundary between planned actions and business evidence."""

from dataclasses import replace
from math import isfinite
from typing import Any

from app.agent.types import AgentToolCall, HandoffResult
from app.support.billing import BILLING_TOOL_ALIASES, MONTH_RESULT_FIELDS, scope_billing_rows
from app.support.handoff_contract import HANDOFF_CREATE
from app.tools.base import ToolResult


BILLING_ACTIONS = frozenset(MONTH_RESULT_FIELDS) | {"query_plan", "mcp__billing__get_plan"}
_ACCOUNT_ACTIONS = BILLING_ACTIONS | {
    "query_call_log", "query_request_observation", "query_api_key_status", "query_recent_call_stats",
}


def bind_request_scope(call: AgentToolCall, billing_month: str | None) -> AgentToolCall:
    if billing_month and call.name in MONTH_RESULT_FIELDS:
        return replace(call, arguments={**call.arguments, "month": billing_month})
    return call


def handoff_receipt(result: ToolResult) -> HandoffResult:
    if result.status != "SUCCESS":
        return HandoffResult(attempted=True, error=result.error or result.status)
    data = result.data if isinstance(result.data, dict) else {}
    raw_id = data.get("handoffId")
    if type(raw_id) in (str, int) and str(raw_id).strip():
        return HandoffResult(attempted=True, success=True, handoff_id=str(raw_id).strip())
    return HandoffResult(attempted=True, error="missing_handoff_id")


def validate_action_result(
    call: AgentToolCall, result: ToolResult, *, user_id: str, generation_id: str,
) -> ToolResult:
    """Discard invalid data before traces, evidence assembly, or model input use it."""
    if result.status != "SUCCESS":
        return result

    def failure(status: str, error: str) -> ToolResult:
        return ToolResult(status=status, error=error, duration_ms=result.duration_ms)

    if call.name == HANDOFF_CREATE:
        if not handoff_receipt(result).success:
            return failure("ERROR", "Missing creation receipt")
        owner = result.data.get("userId")
        if owner is not None and str(owner) != user_id:
            return failure("DENIED", "Handoff receipt scope mismatch")
        receipt_generation = result.data.get("generationId")
        # The support service may return the existing handoff for this diagnosis
        # when an idempotent create is retried on a later turn.
        if receipt_generation and receipt_generation != generation_id and not result.data.get("diagnosisId"):
            return failure("ERROR", "Handoff receipt belongs to a different generation")
    elif call.name in _ACCOUNT_ACTIONS:
        if not isinstance(result.data, dict):
            if call.name in BILLING_ACTIONS:
                return failure("ERROR", "Invalid billing evidence")
            return result
        owner = result.data.get("ownerUserId")
        if owner is not None and str(owner) != user_id:
            return failure("DENIED", "Business evidence scope mismatch")
        scoped = scope_billing_rows(call.name, call.arguments.get("month"), result.data)
        if scoped is None:
            return failure("ERROR", "Billing period mismatch")
        if scoped is not result.data:
            return replace(result, data=scoped)
    return result


def render_action_answer(
    *,
    specialists: tuple[str, ...],
    handoff: dict[str, Any],
    billing_month: str | None,
    evidence: dict[str, Any],
    attempted_tools: set[str],
    offline: bool = False,
) -> str | None:
    """Render bounded action results directly from the verified evidence."""
    if not specialists and handoff.get("attempted"):
        if handoff.get("success") and handoff.get("handoffId"):
            return f"已创建人工工单 {handoff['handoffId']}。后续进展以人工客服更新为准。"
        return "本次未能确认人工工单创建成功。请稍后重试，或通过官方人工客服渠道联系。"
    if specialists != ("billing",) or handoff.get("attempted"):
        return None
    if not attempted_tools or not attempted_tools <= BILLING_ACTIONS:
        return None
    if not offline and (not billing_month or not attempted_tools.intersection(MONTH_RESULT_FIELDS)):
        return None
    attempted_tools = {BILLING_TOOL_ALIASES.get(tool, tool) for tool in attempted_tools}

    labels = {"usage": "已计费调用量", "bills": "账单金额"}
    values = {"usage": "callCount", "bills": "amount"}
    facts = evidence.get("verifiedFacts") or ()
    lines = []
    for field in ("usage", "bills"):
        tools = {tool for tool in attempted_tools if MONTH_RESULT_FIELDS.get(tool) == field}
        if not tools:
            continue
        scoped_facts = [fact for fact in facts if fact.get("tool") in tools]
        rows = [row for fact in scoped_facts for row in fact.get(field, ())
                if row.get("month") and (not billing_month or row["month"] == billing_month)]
        rendered = []
        for row in rows:
            value = row.get(values[field])
            if type(value) not in (int, float) or (type(value) is float and not isfinite(value)):
                continue
            suffix = " 次" if field == "usage" else "（未提供币种）"
            rendered.append(f"{row['month']} {labels[field]}为{value}{suffix}。")
        if rendered:
            lines.extend(dict.fromkeys(rendered))
        elif scoped_facts and all(fact.get("found") is False for fact in scoped_facts):
            lines.append(f"未查到所查询账期的{labels[field]}记录。")
        else:
            lines.append(f"暂时无法核实所查询账期的{labels[field]}，请稍后重试。")
    plan_tools = attempted_tools - MONTH_RESULT_FIELDS.keys()
    if plan_tools:
        plans = [fact for fact in facts if fact.get("tool") in plan_tools and fact.get("found")]
        plan_fields = {"planName": "套餐", "subscriptionStatus": "订阅状态", "qpsLimit": "QPS 上限",
                       "monthlyQuota": "月配额", "basePrice": "基础价格", "overagePricePerCall": "每次超额价格"}
        fields = [f"{label} {plan[key]}" for plan in plans for key, label in plan_fields.items() if key in plan]
        if fields:
            lines.append("已核实的套餐信息：" + "，".join(fields) + "。")
        elif not plans:
            lines.append("暂时无法核实套餐信息。")
    return "\n".join(lines) or None
