"""One deterministic, read-only supplement for gaps supported by prior results."""

from __future__ import annotations

import re

from app.agent.target_agents import target_specialist_agents, _call_matches_attempted_fingerprint
from app.agent.types import AgentPlan, AgentToolCall
from app.support.billing import requested_billing_month


def evidence_followup(state, registry, *, max_tools, max_steps):
    if (
        state.get("evidence_followup_count")
        or state.get("diagnosis_lease")
        or int(state.get("step") or 0) >= max_steps
    ):
        return []
    remaining = min(2, max_tools - int(state.get("executed_tool_call_count") or 0))
    if remaining <= 0:
        return []
    outcomes = list(state.get("target_tool_outcomes") or ())
    attempted = set(state.get("executed_tool_fingerprints") or ())
    from app.agent.types import tool_call_fingerprint

    attempted.update(tool_call_fingerprint(call) for call, _ in outcomes)
    calls = []
    for row in state.get("agent_plans") or ():
        plan = AgentPlan(
            row["agent"], row["skill"], tuple(row.get("allowedTools") or ()), row.get("objective", "")
        )
        own = [(call, result) for call, result in outcomes if call.source_agent == plan.agent]
        names = {call.name for call, _ in own}
        proposed = []
        if plan.agent == "api_diagnostic":
            own = [
                (call, result)
                for call, result in own
                if result.status == "SUCCESS"
                and isinstance(result.data, dict)
                and (
                    result.data.get("errorCode")
                    or str(result.data.get("httpStatus") or "").startswith(("4", "5"))
                )
            ]
            proposed = target_specialist_agents.get(plan.agent).follow_up_calls(
                AgentPlan(
                    plan.agent,
                    plan.skill,
                    ("query_api_key_status", "query_error_code", "query_recent_call_stats"),
                    plan.objective,
                ),
                own,
                names,
            )
        elif plan.agent == "billing" and any(
            call.name in {"query_bill", "mcp__billing__get_invoice"}
            and result.status == "SUCCESS"
            and isinstance(result.data, dict)
            and result.data.get("found")
            for call, result in own
        ):
            month = requested_billing_month(state["question"]) or (state.get("entities") or {}).get("month")
            usage = next(
                (name for name in ("query_usage", "mcp__billing__get_usage") if name in plan.allowed_tools),
                None,
            )
            if "用量" in state["question"] and month and usage:
                proposed = [AgentToolCall("evidence_usage", usage, {"month": month}, plan.agent, plan.skill)]
        elif plan.agent == "knowledge" and "get_document" in plan.allowed_tools:
            # A known result without an excerpt can be expanded, but no query
            # rewriting, region relaxation, or retry of denied/failed reads.
            missing = [
                (call, result)
                for call, result in own
                if call.name == "search_knowledge"
                and result.status == "SUCCESS"
                and isinstance(result.data, dict)
                and result.data.get("status") in (None, "OK")
                and not any(result.data.get(k) for k in ("conflicts", "warnings", "missingFields"))
                and result.data.get("results")
                and not any(
                    str(item.get("textContent") or item.get("text") or "").strip()
                    for item in result.data["results"]
                    if isinstance(item, dict)
                )
            ]
            proposed = target_specialist_agents.get(plan.agent).follow_up_calls(plan, missing, names)
        for call in proposed:
            if call.name == "query_api_key_status" and not any(
                result.data.get("httpStatus") in (401, 403)
                or re.search(r"AUTH|KEY", str(result.data.get("errorCode") or ""), re.I)
                for _, result in own
            ):
                continue
            if call.name == "get_document" and (
                not re.fullmatch(r"[0-9a-f]{32}", call.arguments.get("file_md5", ""))
                or ("chunk_id" in call.arguments and type(call.arguments["chunk_id"]) is not int)
            ):
                continue
            tool = registry.get(call.name)
            if (
                len(calls) < remaining
                and call.name in plan.allowed_tools
                and tool
                and tool.read_only
                and not _call_matches_attempted_fingerprint(call, attempted)
            ):
                calls.append(call)
                attempted.add(tool_call_fingerprint(call))
    return calls
