"""Evidence-based episode scoring. Expected outcomes never enter the runtime."""

import math


def ratio(numerator, denominator):
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def percentile(samples, fraction):
    return sorted(samples)[max(0, math.ceil(len(samples) * fraction) - 1)] if samples else None


def score_episode(expected, artifact):
    detail = artifact.get("diagnosis") or {}
    evidence = {item["evidenceId"]: item for item in detail.get("evidence", [])}
    decision = (detail.get("workflow") or {}).get("decision") or {}
    # Retained historical candidates remain visible after a rejected recheck.
    # Score this turn's decision, not a conclusion from a different request.
    supported = [c for c in decision.get("candidates", []) if c["status"] == "SUPPORTED"]
    causes = {c["cause"] for c in supported}
    # Success rechecks deliberately supersede the original cause list.
    cause_pass = causes == set(expected.get("causes", []))
    unsupported = []
    for candidate in supported:
        refs = [evidence.get(ref) for ref in candidate.get("supportingEvidenceIds", [])]
        if {r.get("tool") for r in refs if r} != {"query_call_log", "query_request_observation"} or any(
            not r
            or not r.get("verified")
            or r.get("sourceType") != "BUSINESS_QUERY"
            or str(r.get("ownerUserId")) != str(artifact.get("userId"))
            for r in refs
        ):
            unsupported.append(candidate["cause"])
    rechecks = (detail.get("workflow") or {}).get("rechecks") or []
    recheck = rechecks[-1] if rechecks else {}
    resolved = detail.get("status") == "RESOLVED"
    recheck_evidence = evidence.get(recheck.get("evidenceId"), {})
    original = (detail.get("workflow") or {}).get("original") or {}
    recheck_fact = (recheck_evidence.get("facts") or [{}])[0]
    recovery_valid = not resolved or (
        recheck.get("status") == "SUCCEEDED"
        and recheck.get("scope") == "this_application_endpoint_request_only"
        and recheck_evidence.get("recheckForDiagnosisId") == detail.get("diagnosisId")
        and recheck_evidence.get("verified") is True
        and str(recheck_evidence.get("ownerUserId")) == str(artifact.get("userId"))
        and recheck_evidence.get("appId") == original.get("appId")
        and recheck_fact.get("endpoint") == original.get("endpoint")
        and recheck_evidence.get("requestId") != original.get("requestId")
        and 200 <= int(recheck_fact.get("httpStatus") or 0) < 300
    )
    tickets = artifact.get("tickets", [])
    ticket_valid = len(tickets) <= 1 and (detail.get("status") != "HANDED_OFF" or len(tickets) == 1)
    parameters_ok = all(item.get("anchored") is True for item in artifact.get("calls", []))
    names = {item.get("tool") for item in artifact.get("calls", [])}
    required = (
        {"query_call_log", "query_request_observation"} if expected.get("causes") else {"query_call_log"}
    )
    selection_ok = required <= names and names <= {
        "query_call_log",
        "query_request_observation",
        "query_api_key_status",
        "query_recent_call_stats",
        "query_error_code",
        "create_support_handoff",
    }
    checks = {
        "cause": cause_pass,
        "status": detail.get("status") == expected["status"],
        "evidenceOwnership": not unsupported,
        "recoveryScope": recovery_valid,
        "ticketIdentity": ticket_valid,
        "parameterProvenance": parameters_ok,
        "toolSelection": selection_ok,
        "recheck": not expected.get("recheck") or recheck.get("status") == expected["recheck"],
    }
    return {
        "id": artifact["id"],
        "passed": all(checks.values()),
        "checks": checks,
        "unsupportedClaims": unsupported,
        "supportedClaims": len(supported),
        "handoffExpected": expected["status"] == "HANDED_OFF",
        "handoffActual": detail.get("status") == "HANDED_OFF",
        "resolved": resolved,
        "recheckExpected": bool(expected.get("recheck")),
        "recheckObserved": bool(recheck),
        "causeApplicable": bool(expected.get("causes")),
        "causeCorrect": cause_pass,
        "uncertaintyApplicable": not expected.get("causes") and expected["status"] != "RESOLVED",
        "toolSelectionCorrect": selection_ok,
        "correctParameters": sum(item.get("anchored") is True for item in artifact.get("calls", [])),
        "durationMs": artifact.get("durationMs"),
        "toolCalls": len(artifact.get("calls", [])),
        "plannerCalls": artifact.get("plannerCalls", 0),
    }


def summarize(rows):
    times = [r["durationMs"] for r in rows if r.get("durationMs") is not None]
    positives = [r for r in rows if r["handoffActual"]]
    expected = [r for r in rows if r["handoffExpected"]]
    true_positive = sum(r["handoffExpected"] for r in positives)
    return {
        "cases": len(rows),
        "pass": all(r["passed"] for r in rows),
        "passRate": ratio(sum(r["passed"] for r in rows), len(rows)),
        "causeAccuracy": ratio(
            sum(r["causeCorrect"] for r in rows if r["causeApplicable"]),
            sum(r["causeApplicable"] for r in rows),
        ),
        "unsupportedClaimRate": ratio(
            sum(len(r["unsupportedClaims"]) for r in rows), sum(r["supportedClaims"] for r in rows)
        ),
        "recheckCompletion": ratio(
            sum(r["recheckObserved"] for r in rows if r["recheckExpected"]),
            sum(r["recheckExpected"] for r in rows),
        ),
        "resolutionRate": ratio(sum(r["resolved"] for r in rows), len(rows)),
        "uncertaintyAccuracy": ratio(
            sum(r["causeCorrect"] for r in rows if r["uncertaintyApplicable"]),
            sum(r["uncertaintyApplicable"] for r in rows),
        ),
        "toolSelectionAccuracy": ratio(sum(r["toolSelectionCorrect"] for r in rows), len(rows)),
        "parameterAccuracy": ratio(
            sum(r["correctParameters"] for r in rows), sum(r["toolCalls"] for r in rows)
        ),
        "handoffPrecision": ratio(true_positive, len(positives)),
        "handoffRecall": ratio(true_positive, len(expected)),
        "p50Ms": percentile(times, 0.5),
        "p95Ms": percentile(times, 0.95),
        "toolCalls": sum(r["toolCalls"] for r in rows),
        "plannerCalls": sum(r["plannerCalls"] for r in rows),
        "failures": [r["id"] for r in rows if not r["passed"]],
    }
