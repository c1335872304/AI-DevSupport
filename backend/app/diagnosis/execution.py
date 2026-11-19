"""Bounded durable read steps. SQL leases fence recovery; slow I/O holds no DB lock."""

import asyncio
import hashlib
import json
import logging
import uuid
from contextlib import suppress
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, or_, select, update

from app.agent.types import AgentToolCall
from app.core.config import get_settings
from app.core.redaction import redact_data, redact_text
from app.core.time import utcnow
from app.db.models import DiagnosisExecution, DiagnosisSession, DiagnosisStep, DiagnosisTurn, User
from app.diagnosis import service
from app.tools.base import ToolExecutionContext, ToolResult

logger = logging.getLogger(__name__)
READ_TOOLS = {
    "query_call_log",
    "query_request_observation",
    "query_api_key_status",
    "query_recent_call_stats",
    "query_error_code",
}
TTL = {
    "query_call_log": 120,
    "query_request_observation": 120,
    "query_api_key_status": 30,
    "query_recent_call_stats": 60,
    "query_error_code": 300,
}


class ExecutionBusy(RuntimeError):
    pass


class ExecutionLost(RuntimeError):
    pass


@dataclass(frozen=True)
class Lease:
    generation_id: str
    owner: str
    epoch: int


def digest(value):
    return hashlib.sha256(service.dumps(value).encode()).hexdigest()


async def db_now(db):
    clock = func.current_timestamp(6) if db.bind.dialect.name == "mysql" else func.current_timestamp()
    return await db.scalar(select(clock))


async def locked(db, generation_id):
    execution = await db.get(DiagnosisExecution, generation_id)
    case = await db.get(DiagnosisSession, execution.diagnosis_id) if execution else None
    if not case or not await service.lock_conversation(db, case.user_id, case.conversation_id):
        raise ExecutionLost("Diagnostic conversation unavailable")
    execution = await db.scalar(
        select(DiagnosisExecution)
        .where(DiagnosisExecution.generation_id == generation_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    case = await db.scalar(
        select(DiagnosisSession)
        .where(DiagnosisSession.diagnosis_id == execution.diagnosis_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    turn = await db.get(DiagnosisTurn, generation_id, populate_existing=True)
    if (
        case.status in service.TERMINAL
        or case.last_generation_id != generation_id
        or not turn
        or (turn.finished and execution.status != "HANDOFF_PENDING")
    ):
        raise ExecutionLost("Diagnostic turn superseded or finished")
    return execution, case


async def guard(db, lease):
    execution, case = await locked(db, lease.generation_id)
    now = await db_now(db)
    if (
        execution.owner != lease.owner
        or execution.epoch != lease.epoch
        or not execution.lease_until
        or execution.lease_until <= now
        or execution.status not in {"RUNNING", "READY", "HANDOFF_PENDING"}
    ):
        raise ExecutionLost("Diagnostic execution lease lost")
    return execution, case, now


async def claim(generation_id, user_id):
    async with service.SessionLocal() as db:
        execution, case = await locked(db, generation_id)
        if case.user_id != str(user_id):
            raise ExecutionLost("Diagnostic owner mismatch")
        now = await db_now(db)
        if execution.lease_until and execution.lease_until > now and execution.owner:
            raise ExecutionBusy("Diagnostic turn already running")
        handoff_only = execution.status == "HANDOFF_PENDING"
        execution.epoch += 1
        execution.owner = uuid.uuid4().hex
        execution.lease_until = now + timedelta(seconds=max(30, get_settings().diagnosis_lease_seconds))
        execution.status, execution.error = ("HANDOFF_PENDING" if handoff_only else "RUNNING"), None
        lease = Lease(generation_id, execution.owner, execution.epoch)
        context = json.loads(execution.context_json)
        context["handoffOnly"] = handoff_only
        await db.commit()
        return lease, context


async def renew(lease):
    async with service.SessionLocal() as db:
        execution, _, now = await guard(db, lease)
        execution.lease_until = now + timedelta(seconds=max(30, get_settings().diagnosis_lease_seconds))
        await db.commit()


async def release_pending_handoff(lease):
    """Let recovery reconcile a completed write attempt with an uncertain receipt."""
    async with service.SessionLocal() as db:
        await db.execute(
            update(DiagnosisExecution)
            .where(
                DiagnosisExecution.generation_id == lease.generation_id,
                DiagnosisExecution.epoch == lease.epoch,
                DiagnosisExecution.owner == lease.owner,
                DiagnosisExecution.status == "HANDOFF_PENDING",
            )
            .values(owner=None, lease_until=await db_now(db))
        )
        await db.commit()


def restored(payload):
    data = json.loads(payload)
    return ToolResult(
        data["status"],
        data.get("data"),
        data.get("error"),
        data.get("durationMs"),
        data.get("metadata") or {},
    )


def classify(result):
    if result.status == "SUCCESS":
        return (
            "NOT_FOUND" if isinstance(result.data, dict) and result.data.get("found") is False else "SUCCESS"
        )
    if result.status == "TIMEOUT":
        return "TRANSIENT_TIMEOUT"
    if result.status == "INVALID_ARGUMENT":
        return "BAD_ARGUMENT"
    if result.status == "DENIED":
        return "PERMISSION_DENIED"
    if result.status == "ERROR" and not str(result.error or "").startswith("Unknown tool"):
        return "TRANSIENT_SERVICE"
    return "UNAVAILABLE"


async def run_step(lease, call, executor, *, after_call=None, after_checkpoint=None):
    if call.name not in READ_TOOLS:
        raise ValueError("Only allowlisted diagnostic reads have resumable checkpoints")
    fingerprint = digest([call.name, json.dumps(call.arguments, sort_keys=True, ensure_ascii=False)])
    step_id = digest([lease.generation_id, fingerprint])
    settings = get_settings()
    while True:
        async with service.SessionLocal() as db:
            execution, case, now = await guard(db, lease)
            step = await db.get(DiagnosisStep, step_id)
            if step is None:
                step = DiagnosisStep(
                    step_id=step_id,
                    diagnosis_id=case.diagnosis_id,
                    generation_id=lease.generation_id,
                    tool_name=call.name,
                    arguments_json=service.dumps(call.arguments),
                    fingerprint=fingerprint,
                )
                db.add(step)
                await db.flush()
            # Cache is case/owner scoped; documents and writes are never cached here.
            cache = await db.scalar(
                select(DiagnosisStep)
                .where(
                    DiagnosisStep.diagnosis_id == case.diagnosis_id,
                    DiagnosisStep.fingerprint == fingerprint,
                    DiagnosisStep.status == "SUCCEEDED",
                    DiagnosisStep.expires_at > now,
                )
                .order_by(DiagnosisStep.updated_at.desc())
                .limit(1)
            )
            if cache and cache.result_json:
                result = restored(cache.result_json)
                result.metadata = {**result.metadata, "checkpointCache": True}
                step.status, step.result_json, step.expires_at = (
                    "SUCCEEDED",
                    service.dumps(result.as_payload()),
                    cache.expires_at,
                )
                await db.commit()
                return result
            if step.status in {"FAILED", "SUCCEEDED"} and step.result_json:
                prior = restored(step.result_json)
                if step.status == "SUCCEEDED" and classify(prior) == "NOT_FOUND":
                    return prior
                if step.status == "FAILED" and classify(prior) not in {
                    "TRANSIENT_TIMEOUT",
                    "TRANSIENT_SERVICE",
                }:
                    return prior
            state = json.loads(case.workflow_json or "{}")
            used = int(state.get("toolAttemptsUsed", 0))
            exhausted = (
                step.attempts >= max(1, settings.diagnosis_step_attempts)
                or execution.attempts_used >= max(1, settings.diagnosis_turn_attempt_budget)
                or used >= max(1, settings.diagnosis_case_attempt_budget)
            )
            if exhausted:
                result = ToolResult(
                    "BUDGET_EXHAUSTED",
                    error="Diagnostic read/retry budget reached",
                    metadata={"failureKind": "BUDGET"},
                )
                step.status, step.result_json = "FAILED", service.dumps(result.as_payload())
                state["budgetReached"] = True
                case.workflow_json = service.dumps(state)
                await db.commit()
                return result
            # Reserve an attempt BEFORE I/O; a crash/unknown result cannot erase cost.
            step.attempts += 1
            step.status = "RUNNING"
            execution.attempts_used += 1
            state["toolAttemptsUsed"] = used + 1
            case.workflow_json = service.dumps(state)
            await db.commit()
        result = await executor(call)
        if result.status == "SUCCESS" and isinstance(result.data, dict):
            if result.data.get("ownerUserId") is not None and str(result.data["ownerUserId"]) != case.user_id:
                result = ToolResult("DENIED", error="Business evidence scope mismatch")
        if after_call:
            await after_call(call, result)
        result.error = redact_text(result.error or "")[:500] or None
        result.data = redact_data(result.data)
        kind = classify(result)
        result.metadata = {**result.metadata, "failureKind": kind}
        async with service.SessionLocal() as db:
            _, _, now = await guard(db, lease)
            step = await db.get(DiagnosisStep, step_id)
            step.status = "SUCCEEDED" if result.status == "SUCCESS" else "FAILED"
            step.result_json = service.dumps(result.as_payload())
            step.expires_at = now + timedelta(seconds=TTL[call.name]) if kind == "SUCCESS" else None
            if step.expires_at and isinstance(result.data, dict) and result.data.get("queriedAt"):
                from app.support.api_diagnostics import parse_time

                try:
                    step.expires_at = min(
                        step.expires_at,
                        parse_time(result.data["queriedAt"]) + timedelta(seconds=TTL[call.name]),
                    )
                except (ValueError, TypeError, AttributeError):
                    step.expires_at = None
            step.updated_at = utcnow()
            await db.commit()
        if after_checkpoint:
            await after_checkpoint(call, result)
        if kind not in {"TRANSIENT_TIMEOUT", "TRANSIENT_SERVICE"}:
            return result
        # Bound both retries and delay. No retries for missing/invalid/denied data.
        await asyncio.sleep(0.05)


def diagnostic_call(name, arguments):
    return AgentToolCall(
        digest([name, json.dumps(arguments, sort_keys=True)]),
        name,
        arguments,
        source_agent="api_diagnostic",
        source_skill="api-diagnostic",
    )


async def run_turn(
    generation_id,
    user,
    registry,
    *,
    finalize=False,
    after_call=None,
    after_checkpoint=None,
    after_finalize=None,
    executor_override=None,
):
    lease, context = await claim(generation_id, user.id)
    runner = asyncio.current_task()

    async def heartbeat():
        try:
            while True:
                await asyncio.sleep(max(2, get_settings().diagnosis_lease_seconds // 3))
                await renew(lease)
        except ExecutionLost:
            runner.cancel()

    heartbeat_task = asyncio.create_task(heartbeat())

    async def executor(call):
        tool = registry.get(call.name)
        if tool and not tool.read_only:
            return ToolResult("DENIED", error="Diagnostic checkpoint requires a read-only tool")
        if executor_override:
            return await executor_override(call)
        return await registry.execute(
            call.name,
            call.arguments,
            ToolExecutionContext(
                user=user,
                generation_id=generation_id,
                active_skills=frozenset({"api-diagnostic"}),
                source="diagnosis",
            ),
        )

    outcomes = []
    try:
        if context.get("handoffOnly"):
            await fulfill_handoff(lease, user)
            return lease, []
        request = context.get("requestId")
        if request:
            log_call = diagnostic_call("query_call_log", {"request_id": request})
            log_result = await run_step(
                lease, log_call, executor, after_call=after_call, after_checkpoint=after_checkpoint
            )
            outcomes.append((log_call, log_result))
            data = (
                log_result.data
                if log_result.status == "SUCCESS" and isinstance(log_result.data, dict)
                else {}
            )
            if data.get("found") and data.get("httpStatus") in {401, 429}:
                calls = [diagnostic_call("query_request_observation", {"request_id": request})]
                if data.get("appId"):
                    calls.append(diagnostic_call("query_api_key_status", {"app_id": data["appId"]}))
                if data.get("httpStatus") == 429:
                    calls.append(
                        diagnostic_call(
                            "query_recent_call_stats",
                            {
                                "request_id": request,
                                "window": "incident",
                                "endpoint": data["endpoint"],
                                "app_id": data["appId"],
                                "minutes": 60,
                            },
                        )
                    )
                tasks = [
                    asyncio.create_task(
                        run_step(
                            lease, call, executor, after_call=after_call, after_checkpoint=after_checkpoint
                        )
                    )
                    for call in calls
                ]
                try:
                    results = await asyncio.gather(*tasks)
                finally:
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                outcomes.extend(zip(calls, results, strict=True))
        async with service.SessionLocal() as db:
            execution, _, _ = await guard(db, lease)
            execution.status = "READY"
            await db.commit()
        if finalize:
            await service.finish_turn(
                user_id=str(user.id),
                conversation_id=context["conversationId"],
                generation_id=generation_id,
                outcomes=outcomes,
                references=[],
                question=context.get("question", ""),
                execution_epoch=lease.epoch,
            )
            if after_finalize:
                await after_finalize()
            await fulfill_handoff(lease, user)
        return lease, outcomes
    finally:
        heartbeat_task.cancel()
        with suppress(asyncio.CancelledError):
            await heartbeat_task


async def recover_execution(generation_id, registry=None):
    from app.tools.registry import tool_registry

    async with service.SessionLocal() as db:
        execution = await db.get(DiagnosisExecution, generation_id)
        case = await db.get(DiagnosisSession, execution.diagnosis_id) if execution else None
        user = await db.get(User, int(case.user_id)) if case and case.user_id.isdigit() else None
        if not user and execution and execution.status not in {"COMPLETED", "CANCELLED"}:
            execution.status, execution.owner, execution.lease_until = "CANCELLED", None, None
            await db.commit()
    if not user:
        return False
    try:
        await run_turn(generation_id, user, registry or tool_registry, finalize=True)
        return True
    except ExecutionBusy:
        return False
    except ExecutionLost:
        async with service.SessionLocal() as db:
            execution = await db.get(DiagnosisExecution, generation_id)
            case = await db.get(DiagnosisSession, execution.diagnosis_id) if execution else None
            if (
                execution
                and execution.status not in {"COMPLETED", "CANCELLED"}
                and (not case or case.status in service.TERMINAL or case.last_generation_id != generation_id)
            ):
                execution.status, execution.owner, execution.lease_until = "CANCELLED", None, None
                await db.commit()
        return False


async def recover_once(registry=None):
    async with service.SessionLocal() as db:
        now = await db_now(db)
        candidates = list(
            (
                await db.scalars(
                    select(DiagnosisExecution.generation_id)
                    .where(
                        or_(
                            (DiagnosisExecution.status == "PENDING")
                            & (DiagnosisExecution.created_at < now - timedelta(seconds=5)),
                            DiagnosisExecution.status.in_(["RUNNING", "READY", "HANDOFF_PENDING"])
                            & (DiagnosisExecution.lease_until <= now),
                        )
                    )
                    .order_by(DiagnosisExecution.created_at)
                    .limit(10)
                )
            ).all()
        )
    return sum([await recover_execution(item, registry) for item in candidates])


async def recovery_loop():
    while True:
        try:
            if get_settings().diagnosis_recovery_enabled:
                await recover_once()
        except Exception:
            logger.exception("Diagnostic checkpoint recovery failed")
        await asyncio.sleep(10)


async def fulfill_handoff(lease, user):
    """Complete only a persisted handoff intent; no model, no replayed document text."""
    from app.support.handoff import create_handoff

    async with service.SessionLocal() as db:
        execution = await db.get(DiagnosisExecution, lease.generation_id)
        if not execution or execution.status != "HANDOFF_PENDING":
            return None
        row = await create_handoff(
            db,
            user,
            generation_id=lease.generation_id,
            diagnosis_lease=lease,
        )
        return row.handoff_id
