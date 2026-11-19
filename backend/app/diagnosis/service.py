"""Transactional case state, generation fencing and current-user reads."""

import json
import re
import uuid
from datetime import timedelta

import jwt
from sqlalchemy import select, update

from app.agent.entities import topic_changed
from app.core.redaction import redact_text
from app.core.time import utcnow
from app.db.models import (
    ConversationSession,
    DiagnosisEvidence,
    DiagnosisExecution,
    DiagnosisSession,
    DiagnosisStep,
    DiagnosisTransition,
    DiagnosisTurn,
    FileUpload,
    SupportHandoff,
    User,
)
from app.db.session import SessionLocal
from app.diagnosis.evidence import citation_evidence, freshness, reported_evidence, tool_evidence
from app.support.api_diagnostics import parse_time, timestamp

TERMINAL = {"RESOLVED", "CLOSED_UNRESOLVED", "HANDED_OFF"}
STATES = {"COLLECTING", "VERIFYING", "WAITING_USER_ACTION", "WAITING_RECHECK", *TERMINAL}
EDGES = {
    "COLLECTING": {"VERIFYING", "WAITING_RECHECK", "CLOSED_UNRESOLVED", "HANDED_OFF"},
    "VERIFYING": {"COLLECTING", "WAITING_USER_ACTION", "WAITING_RECHECK", "CLOSED_UNRESOLVED", "HANDED_OFF"},
    "WAITING_USER_ACTION": {"VERIFYING", "COLLECTING", "WAITING_RECHECK", "CLOSED_UNRESOLVED", "HANDED_OFF"},
    "WAITING_RECHECK": {
        "VERIFYING",
        "COLLECTING",
        "WAITING_USER_ACTION",
        "RESOLVED",
        "CLOSED_UNRESOLVED",
        "HANDED_OFF",
    },
}


def dumps(value):
    return json.dumps(value, ensure_ascii=False, default=str)


def transition(db, case, target, reason, generation_id, evidence=(), *, handoff_confirmed=False):
    """Only program-supplied, scope checked evidence may unlock terminal states."""
    if target == case.status:
        return
    if target not in EDGES.get(case.status, set()):
        raise ValueError(f"Invalid diagnosis transition {case.status} -> {target}")
    if target == "HANDED_OFF" and not handoff_confirmed:
        raise ValueError("Handoff requires a persisted successful handoff")
    if target == "RESOLVED":
        # Only an explicit internally correlated recheck can unlock this edge.
        # Phase 2 does not generate this correlation from chat text.
        now = utcnow()
        valid = []
        for item in evidence:
            try:
                event = parse_time(item.get("eventAt"))
            except (TypeError, ValueError, AttributeError):
                continue
            facts = item.get("facts") or [{}]
            valid.append(
                item.get("verified")
                and item.get("sourceType") == "BUSINESS_QUERY"
                and item.get("tool") == "query_call_log"
                and item.get("ownerUserId") == case.user_id
                and bool(case.app_id)
                and item.get("appId") == case.app_id
                and bool(item.get("requestId"))
                and item.get("requestId") == facts[0].get("requestId")
                and item.get("requestId") != json.loads(case.entities_json).get("request_id")
                and item.get("recheckForDiagnosisId") == case.diagnosis_id
                and "recheck_success" in item.get("supportsClaims", [])
                and case.created_at <= event <= now
                and now - event <= timedelta(minutes=5)
                and facts[0].get("found")
                and 200 <= int(facts[0].get("httpStatus") or 0) < 300
            )
        if not any(valid):
            raise ValueError("Resolution requires a fresh, correlated business recheck")
    db.add(
        DiagnosisTransition(
            diagnosis_id=case.diagnosis_id,
            generation_id=generation_id,
            from_status=case.status,
            to_status=target,
            reason=reason[:255],
            evidence_ids_json=dumps([e["evidenceId"] for e in evidence]),
        )
    )
    case.status, case.updated_at = target, utcnow()
    case.revision += 1
    if target in TERMINAL:
        case.end_reason = reason[:255]


async def lock_conversation(db, user_id, conversation_id):
    # A DB write lock, also effective on SQLite, serializes case creation per chat.
    result = await db.execute(
        update(ConversationSession)
        .where(
            ConversationSession.conversation_id == conversation_id,
            ConversationSession.user_id == str(user_id),
            ConversationSession.status == "ACTIVE",
        )
        .values(status=ConversationSession.status)
    )
    return result.rowcount == 1


async def begin_turn(
    *,
    user_id,
    conversation_id,
    generation_id,
    question,
    entities,
    sources,
    diagnostic,
    recheck_case_id=None,
    expected_revision=None,
):
    if not conversation_id:
        return None
    async with SessionLocal() as db:
        if not await lock_conversation(db, user_id, conversation_id):
            return None
        existing_turn = await db.get(DiagnosisTurn, generation_id)
        if existing_turn:
            previous = await db.get(DiagnosisSession, existing_turn.diagnosis_id)
            if recheck_case_id and previous and previous.user_id == str(user_id):
                execution = await db.get(DiagnosisExecution, generation_id)
                if (
                    previous.diagnosis_id != recheck_case_id
                    or not execution
                    or json.loads(execution.context_json).get("requestId") != entities.get("request_id")
                ):
                    raise ValueError("Idempotency key reused for another request")
            return (
                previous.diagnosis_id
                if previous
                and previous.user_id == str(user_id)
                and previous.conversation_id == conversation_id
                else None
            )
        case = await db.scalar(
            select(DiagnosisSession)
            .where(
                DiagnosisSession.user_id == str(user_id),
                DiagnosisSession.conversation_id == conversation_id,
                DiagnosisSession.status.not_in(TERMINAL),
            )
            .order_by(DiagnosisSession.created_at.desc())
        )
        current = {k: v for k, v in entities.items() if sources.get(k) == "current"}
        input_entities = dict(entities)
        old = json.loads(case.entities_json) if case else {}
        if expected_revision is not None and (not case or case.revision != expected_revision):
            raise ValueError("Diagnostic revision changed")
        rechecking = bool(
            case
            and old.get("request_id")
            and case.status in {"WAITING_RECHECK", "WAITING_USER_ACTION", "COLLECTING"}
            and current.get("request_id")
            and current["request_id"] != old.get("request_id")
            and (not current.get("app_id") or current["app_id"] == old.get("app_id"))
            and (
                recheck_case_id == case.diagnosis_id
                or re.search(r"复查|重新核查|重试|已修改|已修正|已调整|修正后", question)
            )
        )
        if recheck_case_id and (not case or case.diagnosis_id != recheck_case_id or not rechecking):
            raise ValueError("Diagnosis cannot accept this recheck")
        changed = (
            case
            and any(current.get(k) and old.get(k) and current[k] != old[k] for k in ("app_id", "request_id"))
            and not rechecking
        )
        continuation = (
            case
            and not topic_changed(question)
            and bool(re.search(r"转人工|人工客服|已经|已修改|已修正|已恢复|重试|还是|继续|刚才|这个|那个", question))
        )
        if case and (changed or topic_changed(question) or (not diagnostic and not continuation)):
            transition(
                db, case, "CLOSED_UNRESOLVED", "NEW_INCIDENT" if changed else "TOPIC_SWITCH", generation_id
            )
            case = None
        if not diagnostic and not continuation:
            await db.commit()
            return None
        if case is None:
            case = DiagnosisSession(
                diagnosis_id=uuid.uuid4().hex,
                user_id=str(user_id),
                conversation_id=conversation_id,
                symptom=redact_text(question)[:2000],
                entities_json=dumps(entities),
                entity_sources_json=dumps(sources),
                status="COLLECTING",
                revision=1,
                last_generation_id=generation_id,
            )
            db.add(case)
            db.add(
                DiagnosisTransition(
                    diagnosis_id=case.diagnosis_id,
                    generation_id=generation_id,
                    from_status=None,
                    to_status="COLLECTING",
                    reason="INCIDENT_STARTED",
                )
            )
            await db.flush()
        else:
            scoped = json.loads(case.entities_json)
            # Use the persisted case only, never global history from another topic.
            if not rechecking:
                scoped.update(entities)
            entities = scoped
            sources = (
                json.loads(case.entity_sources_json)
                if rechecking
                else {**json.loads(case.entity_sources_json), **sources}
            )
        workflow = json.loads(case.workflow_json or "{}")
        if rechecking:
            workflow["pendingRecheck"] = {
                "requestId": current["request_id"],
                "generationId": generation_id,
                "reportedAt": timestamp(utcnow()),
                "association": "explicit_user_recheck",
            }
            transition(db, case, "WAITING_RECHECK", "RECHECK_SUBMITTED", generation_id)
        if re.search(r"已修改|已修正|已调整|已经.*(?:修复|修改)|已恢复|恢复了|好了", question):
            workflow["userActionReport"] = {
                "text": redact_text(question)[:500],
                "reportedAt": timestamp(utcnow()),
            }
        case.workflow_json = dumps(workflow)
        case.entities_json, case.entity_sources_json = dumps(entities), dumps(sources)
        case.app_id = entities.get("app_id")
        case.last_generation_id = generation_id
        case.revision += 1
        case.updated_at = utcnow()
        if case.status != "WAITING_RECHECK" and (
            entities.get("request_id") or entities.get("app_id") or entities.get("endpoint")
        ):
            transition(db, case, "VERIFYING", "TURN_STARTED", generation_id)
            case.next_action = "正在核查请求与对应时间范围"
        report = reported_evidence(
            user_id, generation_id, question, input_entities if rechecking else entities
        )
        db.add(
            DiagnosisEvidence(
                evidence_id=report["evidenceId"],
                diagnosis_id=case.diagnosis_id,
                generation_id=generation_id,
                payload_json=dumps(report),
            )
        )
        db.add(DiagnosisTurn(generation_id=generation_id, diagnosis_id=case.diagnosis_id))
        request_id = current.get("request_id") if rechecking else entities.get("request_id")
        db.add(
            DiagnosisExecution(
                generation_id=generation_id,
                diagnosis_id=case.diagnosis_id,
                context_json=dumps(
                    {
                        "question": redact_text(question)[:2000],
                        "requestId": request_id,
                        "recheck": rechecking,
                        "conversationId": conversation_id,
                        "entities": entities,
                    }
                ),
            )
        )
        await db.commit()
        return case.diagnosis_id


async def finish_turn(
    *,
    user_id,
    conversation_id,
    generation_id,
    outcomes,
    references,
    question,
    handoff=None,
    blocked=False,
    execution_epoch=None,
):
    async with SessionLocal() as db:
        if not await lock_conversation(db, user_id, conversation_id):
            return None
        turn = await db.get(DiagnosisTurn, generation_id)
        if not turn:
            return None
        case = await db.get(DiagnosisSession, turn.diagnosis_id)
        if not case or case.user_id != str(user_id) or case.conversation_id != conversation_id:
            return None
        if turn.finished or case.status in TERMINAL or case.last_generation_id != generation_id:
            return case.diagnosis_id  # A late generation cannot mutate the latest case.
        execution = await db.get(DiagnosisExecution, generation_id, populate_existing=True)
        if execution and execution.epoch:
            from app.diagnosis.execution import db_now

            if (
                execution_epoch != execution.epoch
                or not execution.lease_until
                or execution.lease_until <= await db_now(db)
            ):
                return None
        execution_context = json.loads(execution.context_json) if execution else {}
        records = tool_evidence(user_id, generation_id, outcomes) + citation_evidence(
            user_id, generation_id, references
        )
        entities = json.loads(case.entities_json)
        sources = json.loads(case.entity_sources_json)
        missing, conflict, found_log = [], [], False
        for record in records:
            if record.get("tool") != "query_call_log" or not record.get("verified"):
                continue
            fact = (record.get("facts") or [{}])[0]
            if not fact.get("found"):
                missing.append("valid_request_id")
                continue
            if entities.get("request_id") != fact.get("requestId"):
                if execution_context.get("recheck") and execution_context.get("requestId") == fact.get(
                    "requestId"
                ):
                    continue
                record["verified"] = False
                record["scope"] = "different_request"
                continue
            found_log = True
            for key, name in [
                ("app_id", "appId"),
                ("http_status", "httpStatus"),
                ("error_code", "errorCode"),
                ("endpoint", "endpoint"),
            ]:
                value = str(fact.get(name) or "")
                if entities.get(key) and value and entities[key] != value:
                    conflict.append(key)
                elif value:
                    entities[key], sources[key] = value, f"tool:{record['evidenceId']}"
            case.app_id = entities.get("app_id")
        if conflict:
            missing += [f"confirm_{key}" for key in conflict]
        if not found_log and not entities.get("request_id"):
            missing.append("request_id_or_incident_time")
        if any(
            r.get("resultStatus")
            in {"ERROR", "TIMEOUT", "DENIED", "SCOPE_MISMATCH", "INVALID_ARGUMENT", "BUDGET_EXHAUSTED"}
            for r in records
        ):
            missing.append("business_evidence_unavailable")
        case.entities_json, case.entity_sources_json = dumps(entities), dumps(sources)
        from app.diagnosis.loop import assess

        workflow, decision = assess(case, execution, records, question, conflict=conflict)
        case.workflow_json = dumps(workflow)
        if not decision.get("recheck") or decision["recheck"]["status"] != "REJECTED":
            case.candidates_json = dumps(decision["candidates"])
        case.missing_fields_json = dumps(list(dict.fromkeys(missing)))
        for record in records:
            db.add(
                DiagnosisEvidence(
                    evidence_id=record["evidenceId"],
                    diagnosis_id=case.diagnosis_id,
                    generation_id=generation_id,
                    payload_json=dumps(record),
                )
            )
        handoff_row = (
            await db.get(SupportHandoff, handoff.get("handoffId"))
            if handoff and handoff.get("success") and handoff.get("handoffId")
            else None
        )
        confirmed_handoff = bool(
            handoff_row
            and handoff_row.user_id == str(user_id)
            and handoff_row.conversation_id == conversation_id
            and (handoff_row.generation_id == generation_id or handoff_row.diagnosis_id == case.diagnosis_id)
        )
        if confirmed_handoff:
            target, reason, action = "HANDED_OFF", "PERSISTED_HANDOFF", "等待人工核查"
        elif (
            decision.get("recheck")
            and decision["recheck"]["status"] == "SUCCEEDED"
            and not decision.get("handoffRequired")
        ):
            target, reason, action = "RESOLVED", "BUSINESS_RECHECK_SUCCESS", decision["nextAction"]
        elif decision.get("recheck") and decision["recheck"]["status"] == "REJECTED":
            target, reason, action = "COLLECTING", decision["recheck"]["reason"], decision["nextAction"]
            missing.append(reason)
        elif decision.get("recheck") and decision["recheck"]["status"] == "STILL_FAILING":
            target, reason, action = "WAITING_USER_ACTION", "RECHECK_STILL_FAILING", decision["nextAction"]
        elif blocked or missing:
            target, reason = "COLLECTING", "EVIDENCE_GAP"
            action = (
                "用户描述与请求记录不一致，请核对请求号、应用和发生时间"
                if conflict
                else "未找到该请求，请核对请求号、应用和发生时间"
                if "valid_request_id" in missing
                else "部分业务查询未成功，请稍后重试或补充脱敏日志"
                if "business_evidence_unavailable" in missing
                else "补充脱敏请求号或故障发生时间，无需提供完整 Key"
            )
        elif case.status == "WAITING_RECHECK" or re.search(
            r"已修改|已修正|已经.*(?:修改|修复)|(?:已恢复|恢复了|修复好了|现在好了|已经好了)", question
        ):
            target, reason, action = (
                "WAITING_RECHECK",
                "USER_REPORTED_ACTION",
                "提供修正后的新 request_id，反馈不等于工具确认恢复",
            )
        elif found_log:
            target, reason, action = (
                "WAITING_USER_ACTION",
                "EVENT_CHECKED",
                "补充已尝试的处理动作；若已调整，请提供新的请求号",
            )
        else:
            target, reason, action = (
                "COLLECTING",
                "PERSONAL_FACTS_UNCONFIRMED",
                "补充可核查的请求号或故障发生时间",
            )
        if decision.get("causeConfirmed") or decision.get("handoffRequired"):
            action = decision["nextAction"]
        case.missing_fields_json = dumps(list(dict.fromkeys(missing)))
        transition(db, case, target, reason, generation_id, records, handoff_confirmed=confirmed_handoff)
        case.next_action = action
        case.updated_at = utcnow()
        turn.finished = True
        if execution:
            execution.status = (
                "HANDOFF_PENDING"
                if decision.get("handoffRequired") and target not in TERMINAL
                else "COMPLETED"
            )
            if not execution.owner:
                execution.lease_until = utcnow()
            if execution.status == "COMPLETED":
                execution.owner, execution.lease_until = None, None
        await db.commit()
        return case.diagnosis_id


async def detail(db, user, diagnosis_id):
    case = await db.get(DiagnosisSession, diagnosis_id)
    if not case or case.user_id != str(user.id):
        return None
    # Refresh memberships before checking persisted document references.
    current_user = await db.get(User, user.id, populate_existing=True)
    rows = list(
        (
            await db.scalars(
                select(DiagnosisEvidence)
                .where(DiagnosisEvidence.diagnosis_id == diagnosis_id)
                .order_by(DiagnosisEvidence.created_at.desc())
                .limit(100)
            )
        ).all()
    )
    evidence = []
    for row in reversed(rows):
        record = json.loads(row.payload_json)
        record["freshness"] = freshness(record)
        if record["sourceType"] == "DOCUMENT_RULE" and record.get("source"):
            from app.knowledge.citations import decode_citation
            from app.knowledge.rag import rag_service

            source = record["source"]
            try:
                binding = decode_citation(source.get("citationId", ""))
                file = await db.scalar(
                    select(FileUpload).where(
                        FileUpload.file_md5 == binding["md5"],
                        FileUpload.deleted_at.is_(None),
                        FileUpload.user_id == str(binding["owner"]),
                        FileUpload.active_vector_version == binding["build"],
                        rag_service._database_permission_filter(current_user),
                    )
                )
                if not file:
                    raise ValueError("Citation invalidated")
                record["freshness"] = "AUTHORIZED_ACTIVE_DOCUMENT"
            except (ValueError, KeyError, TypeError, jwt.PyJWTError):
                record.pop("source", None)
                record["freshness"] = "DOCUMENT_UNAVAILABLE"
        evidence.append(record)
    events = list(
        (
            await db.scalars(
                select(DiagnosisTransition)
                .where(DiagnosisTransition.diagnosis_id == diagnosis_id)
                .order_by(DiagnosisTransition.id.desc())
                .limit(100)
            )
        ).all()
    )
    turns = list(
        (
            await db.scalars(
                select(DiagnosisTurn.generation_id).where(DiagnosisTurn.diagnosis_id == diagnosis_id)
            )
        ).all()
    )
    executions = list(
        (
            await db.scalars(
                select(DiagnosisExecution)
                .where(DiagnosisExecution.diagnosis_id == diagnosis_id)
                .order_by(DiagnosisExecution.created_at.desc())
                .limit(20)
            )
        ).all()
    )
    steps = list(
        (
            await db.scalars(
                select(DiagnosisStep)
                .where(DiagnosisStep.diagnosis_id == diagnosis_id)
                .order_by(DiagnosisStep.created_at.desc())
                .limit(50)
            )
        ).all()
    )
    return {
        "diagnosisId": diagnosis_id,
        "conversationId": case.conversation_id,
        "status": case.status,
        "appId": case.app_id,
        "symptom": case.symptom,
        "entities": json.loads(case.entities_json),
        "entitySources": json.loads(case.entity_sources_json),
        "candidates": json.loads(case.candidates_json),
        "workflow": json.loads(case.workflow_json or "{}"),
        "executions": [
            {
                "generationId": x.generation_id,
                "status": x.status,
                "attemptsUsed": x.attempts_used,
                "updatedAt": timestamp(x.updated_at),
            }
            for x in executions
        ],
        "steps": [
            {
                "tool": x.tool_name,
                "status": x.status,
                "attempts": x.attempts,
                "failureKind": (json.loads(x.result_json).get("metadata") or {}).get("failureKind")
                if x.result_json
                else None,
            }
            for x in steps
        ],
        "missingFields": json.loads(case.missing_fields_json),
        "nextAction": case.next_action,
        "endReason": case.end_reason,
        "revision": case.revision,
        "lastGenerationId": case.last_generation_id,
        "generationIds": turns,
        "createdAt": timestamp(case.created_at),
        "updatedAt": timestamp(case.updated_at),
        "evidence": evidence,
        "transitions": [
            {
                "from": e.from_status,
                "to": e.to_status,
                "reason": e.reason,
                "generationId": e.generation_id,
                "evidenceIds": json.loads(e.evidence_ids_json),
                "createdAt": timestamp(e.created_at),
            }
            for e in reversed(events)
        ],
    }


async def read_detail(user, diagnosis_id):
    async with SessionLocal() as db:
        return await detail(db, user, diagnosis_id)
