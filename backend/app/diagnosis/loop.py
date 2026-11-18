"""Pure, bounded cause/action/recheck decisions consumed by the existing workflow."""

import json
import re
from datetime import timedelta

from app.core.redaction import redact_text
from app.core.time import utcnow
from app.diagnosis.rules import analyze
from app.support.api_diagnostics import parse_time, timestamp


def assess(case, execution, records, question, *, conflict=()):
    workflow = json.loads(case.workflow_json or "{}")
    entities = json.loads(case.entities_json)
    context = json.loads(execution.context_json) if execution else {}
    pending = workflow.get("pendingRecheck") or {}
    rechecking = pending.get("generationId") == case.last_generation_id
    request = (
        pending.get("requestId") if rechecking else (context.get("requestId") or entities.get("request_id"))
    )
    event = next(
        (
            e
            for e in records
            if e.get("tool") == "query_call_log"
            and e.get("verified")
            and e.get("requestId") == request
            and (e.get("facts") or [{}])[0].get("found")
        ),
        None,
    )
    original = workflow.get("original")
    if event and not original and not rechecking:
        fact = event["facts"][0]
        original = {
            "requestId": request,
            "appId": event.get("appId"),
            "endpoint": fact.get("endpoint"),
            "eventAt": event.get("eventAt"),
            "httpStatus": fact.get("httpStatus"),
        }
        workflow["original"] = original
    original = original or {}
    analysis = analyze(records, request_id=request, app_id=case.app_id, endpoint=original.get("endpoint"))
    result = None
    if rechecking:
        reason = None
        fact = event["facts"][0] if event else {}
        if not event:
            reason = "RECHECK_NOT_FOUND"
        elif (
            not original.get("appId")
            or event.get("appId") != original.get("appId")
            or fact.get("endpoint") != original.get("endpoint")
            or request == original.get("requestId")
        ):
            reason = "RECHECK_SCOPE_MISMATCH"
        else:
            try:
                when = parse_time(event.get("eventAt"))
                previous = parse_time(original.get("eventAt"))
                now = utcnow()
                if not (max(previous, case.created_at) < when <= now and now - when <= timedelta(minutes=5)):
                    reason = "RECHECK_TIME_MISMATCH"
            except (ValueError, TypeError, AttributeError):
                reason = "RECHECK_TIME_UNKNOWN"
        if conflict:
            reason = "RECHECK_CONFLICT"
        if reason:
            result = {
                "requestId": request,
                "status": "REJECTED",
                "reason": reason,
                "scope": "no_recovery_confirmation",
            }
            analysis = {
                **analysis,
                "causeConfirmed": False,
                "actions": [],
                "candidates": [],
                "missing": [reason],
            }
        elif 200 <= int(fact.get("httpStatus") or 0) < 300:
            event["recheckForDiagnosisId"] = case.diagnosis_id
            event["supportsClaims"] = [*event["supportsClaims"], "recheck_success"]
            result = {
                "requestId": request,
                "status": "SUCCEEDED",
                "httpStatus": fact["httpStatus"],
                "eventAt": event["eventAt"],
                "evidenceId": event["evidenceId"],
                "scope": "this_application_endpoint_request_only",
            }
        else:
            result = {
                "requestId": request,
                "status": "STILL_FAILING",
                "httpStatus": fact.get("httpStatus"),
                "eventAt": event.get("eventAt"),
                "evidenceId": event["evidenceId"],
            }
        workflow["rechecks"] = [*(workflow.get("rechecks") or []), result][-10:]
        workflow.pop("pendingRecheck", None)
    else:
        workflow["noProgressCount"] = (
            0 if analysis["causeConfirmed"] else int(workflow.get("noProgressCount", 0)) + 1
        )
    for candidate in analysis["candidates"]:
        candidate["updatedAt"] = timestamp(utcnow())
    if conflict:
        for candidate in analysis["candidates"]:
            candidate["status"] = "UNDETERMINED"
            candidate["missing"] = ["resolve_user_log_conflict"]
        analysis["actions"], analysis["causeConfirmed"] = [], False
    failed = any(r.get("resultStatus") in {"BUDGET_EXHAUSTED", "DENIED"} for r in records)
    reasons = []
    if re.search(r"转人工|人工客服|人工处理|停止排查|不用排查", question):
        reasons.append("USER_REQUESTED_HANDOFF")
    if workflow.get("budgetReached") or failed:
        reasons.append("BUDGET_OR_PERMISSION")
    if workflow.get("noProgressCount", 0) >= 2 or len(workflow.get("rechecks", [])) >= 3:
        reasons.append("NO_PROGRESS_OR_RECHECK_LIMIT")
    if result and result["status"] == "SUCCEEDED":
        reasons = [r for r in reasons if r == "USER_REQUESTED_HANDOFF"]
    decision = {**analysis, "recheck": result, "handoffRequired": bool(reasons), "handoffReasons": reasons}
    if result and result["status"] == "SUCCEEDED":
        decision["nextAction"] = "新请求在同一应用和接口范围内已成功；这不代表所有接口或账户状态均已恢复"
    elif result and result["status"] == "REJECTED":
        decision["nextAction"] = "复查请求归属或时间不匹配，请提供同一应用、接口的近期新请求号"
    elif reasons:
        decision["nextAction"] = "已达到人工核查条件，等待真实工单创建结果"
    elif analysis["actions"]:
        decision["nextAction"] = analysis["actions"][0]["instruction"] + "；完成后提供新请求号复查"
    else:
        decision["nextAction"] = "细分原因尚未确定，请补充请求时的脱敏观测信息；无需提供完整密钥"
    if workflow.get("decision"):
        workflow["decisionHistory"] = [
            *(workflow.get("decisionHistory") or []),
            {"recordedAt": timestamp(utcnow()), "decision": workflow["decision"]},
        ][-10:]
    workflow["decision"] = decision
    workflow["actions"] = analysis["actions"]
    return workflow, decision


def handoff_summary(case):
    state = json.loads(case.workflow_json or "{}")
    decision = state.get("decision") or {}
    return redact_text(
        json.dumps(
            {
                "diagnosisId": case.diagnosis_id,
                "symptom": case.symptom,
                "original": state.get("original"),
                "candidates": json.loads(case.candidates_json),
                "attemptedAction": state.get("userActionReport"),
                "unresolved": decision.get("missing"),
                "rechecks": state.get("rechecks", []),
                "toolAttempts": state.get("toolAttemptsUsed", 0),
                "handoffReasons": decision.get("handoffReasons"),
            },
            ensure_ascii=False,
        )
    )[:6000]
