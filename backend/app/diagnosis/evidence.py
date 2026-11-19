"""Narrow provenance contracts. No document or user report proves personal state."""

import uuid
from datetime import timedelta

from app.agent.evidence import _raw_facts_for
from app.core.redaction import redact_data, redact_text
from app.core.time import utcnow
from app.support.api_diagnostics import parse_time, timestamp

SNAPSHOT_TTL = {
    "query_api_key_status": 30,
    "query_recent_call_stats": 60,
    "query_plan": 300,
    "query_usage": 60,
    "query_bill": 60,
    "mcp__billing__get_plan": 300,
    "mcp__billing__get_usage": 60,
    "mcp__billing__get_invoice": 60,
}


def envelope(source, user_id, generation_id, *, now=None):
    now = now or utcnow()
    return {
        "evidenceId": uuid.uuid4().hex,
        "sourceType": source,
        "ownerUserId": str(user_id),
        "generationId": generation_id,
        "appId": None,
        "requestId": None,
        "eventAt": None,
        "queriedAt": timestamp(now),
        "validUntil": None,
        "scope": "unconfirmed",
        "supportsClaims": [],
        "verified": False,
    }


def reported_evidence(user_id, generation_id, question, entities):
    record = envelope("USER_REPORT", user_id, generation_id)
    record.update(
        {
            "summary": redact_text(question)[:1200],
            "appId": entities.get("app_id"),
            "requestId": entities.get("request_id"),
            "supportsClaims": ["reported_symptom"],
        }
    )
    return record


def tool_evidence(user_id, generation_id, outcomes):
    records = []
    for call, result in outcomes:
        data = result.data if isinstance(result.data, dict) else {}
        if call.name in {"search_knowledge", "get_document", "list_documents"}:
            continue  # References are captured separately without document excerpts.
        rule = call.name == "query_error_code"
        record = envelope("DOCUMENT_RULE" if rule else "BUSINESS_QUERY", user_id, generation_id)
        record.update(
            {
                "tool": call.name,
                "toolCallId": call.id,
                "resultStatus": result.status,
                "sourceSystem": data.get("sourceSystem", "demo_business"),
            }
        )
        if data.get("ownerUserId") is not None and str(data["ownerUserId"]) != str(user_id):
            record.update({"resultStatus": "SCOPE_MISMATCH", "summary": "工具结果归属不匹配"})
            records.append(record)
            continue
        facts = _raw_facts_for(call.name, data) if result.status == "SUCCESS" else []
        record["facts"] = redact_data(facts)
        record["queriedAt"] = data.get("queriedAt") or record["queriedAt"]
        record["appId"] = data.get("appId") or call.arguments.get("app_id")
        record["requestId"] = data.get("requestId") or call.arguments.get("request_id")
        record["eventAt"] = data.get("calledAt")
        record["windowStart"], record["windowEnd"] = data.get("windowStart"), data.get("windowEnd")
        record["windowType"] = data.get("windowType")
        record["verified"] = bool(facts) and result.status == "SUCCESS" and not rule
        if rule:
            record.update({"scope": "general_rule", "supportsClaims": ["error_code_definition"]})
        elif call.name in {"query_call_log", "query_request_observation"}:
            record.update(
                {
                    "scope": "historical_event",
                    "supportsClaims": ["request_event"] if data.get("found") else ["request_not_found"],
                }
            )
        elif call.name in SNAPSHOT_TTL:
            ttl = SNAPSHOT_TTL[call.name]
            try:
                record["validUntil"] = timestamp(parse_time(record["queriedAt"]) + timedelta(seconds=ttl))
            except (ValueError, TypeError):
                record["verified"] = False
            record.update(
                {
                    "scope": "historical_window"
                    if data.get("windowType") in {"incident", "explicit"}
                    else "current_snapshot",
                    "supportsClaims": ["bounded_statistics"]
                    if call.name == "query_recent_call_stats"
                    else ["queried_business_state"],
                }
            )
        else:
            record["verified"] = False
        records.append(record)
    return records


def citation_evidence(user_id, generation_id, references):
    records = []
    for reference in references:
        record = envelope("DOCUMENT_RULE", user_id, generation_id)
        record.update(
            {
                "scope": "general_rule",
                "supportsClaims": ["document_rule"],
                "source": {
                    key: reference[key]
                    for key in [
                        "citationId",
                        "fileMd5",
                        "indexVersion",
                        "chunkId",
                        "sourceLocation",
                        "pageNumber",
                    ]
                    if key in reference
                },
            }
        )
        # No title/excerpt is persisted here: authorization can later be revoked.
        records.append(record)
    return records


def freshness(record, *, now=None):
    now = now or utcnow()
    if record["sourceType"] == "USER_REPORT":
        return "REPORTED_ONLY"
    if record["sourceType"] == "DOCUMENT_RULE":
        return "REQUIRES_DOCUMENT_REVALIDATION"
    if not record.get("verified"):
        return "UNVERIFIED"
    if record.get("scope") in {"historical_event", "historical_window"}:
        return "HISTORICAL_ONLY"
    try:
        if not record.get("validUntil") or parse_time(record["validUntil"]) < now:
            return "EXPIRED"
    except (ValueError, TypeError):
        return "EXPIRED"
    return "CURRENT"


def expired_current_facts(facts):
    """Check again immediately before emission, after potentially slow generation."""
    for fact in facts:
        context = fact.get("evidenceContext") or {}
        if context.get("scope") != "current_snapshot" or not context.get("validUntil"):
            continue
        try:
            if parse_time(context["validUntil"]) < utcnow():
                return True
        except (ValueError, TypeError, AttributeError):
            return True
    return False
