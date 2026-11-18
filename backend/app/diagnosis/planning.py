"""Stop redundant API planning only after versioned event evidence is sufficient."""

from app.diagnosis.evidence import tool_evidence
from app.diagnosis.rules import analyze


def api_planning_complete(user_id, generation_id, entities, outcomes):
    request = entities.get("request_id")
    if not request:
        return False
    records = tool_evidence(user_id, generation_id, outcomes)
    log = next(
        (
            r
            for r in records
            if r.get("tool") == "query_call_log"
            and r.get("verified")
            and r.get("requestId") == request
            and (r.get("facts") or [{}])[0].get("found")
        ),
        None,
    )
    if not log:
        return False
    facts = log["facts"][0]
    if entities.get("http_status") and str(facts.get("httpStatus")) != str(entities["http_status"]):
        return False
    if any(
        entities.get(key) and entities[key] != facts.get(field)
        for key, field in (("error_code", "errorCode"), ("endpoint", "endpoint"))
    ):
        return False
    return analyze(records, request_id=request, app_id=entities.get("app_id"))["causeConfirmed"]
