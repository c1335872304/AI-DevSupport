import asyncio
import json
import os
import uuid
from collections import Counter
from datetime import timedelta
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.time import utcnow
from app.db import session as db_module
from app.db.models import (
    Base,
    ConversationSession,
    DiagnosisEvidence,
    DiagnosisExecution,
    DiagnosisSession,
    DiagnosisStep,
    DiagnosisTransition,
    DiagnosisTurn,
    FileUpload,
    SupportApiCallLog,
    SupportApiKey,
    SupportHandoff,
    SupportRequestObservation,
    User,
)
from app.diagnosis import execution, service
from app.diagnosis.rules import RULE_VERSION
from app.tools.base import ToolResult
from app.tools.local.api_support import (
    QueryApiKeyStatusTool,
    QueryCallLogTool,
    QueryErrorCodeTool,
    QueryRecentCallStatsTool,
    QueryRequestObservationTool,
)
from app.tools.registry import ToolRegistry


class Registry(ToolRegistry):
    def __init__(self):
        super().__init__(
            [
                QueryCallLogTool(),
                QueryApiKeyStatusTool(),
                QueryErrorCodeTool(),
                QueryRecentCallStatsTool(),
                QueryRequestObservationTool(),
            ]
        )
        self.counts = Counter()
        self.failures = {}

    async def execute(self, name, arguments, context):
        self.counts[name] += 1
        if self.failures.get(name):
            return self.failures[name].pop(0)
        return await super().execute(name, arguments, context)


@pytest.fixture
async def env(tmp_path, monkeypatch):
    engine = create_async_engine(
        os.environ.get("PHASE3_TEST_MYSQL_URL") or f"sqlite+aiosqlite:///{(tmp_path / 'loop.db').as_posix()}"
    )
    async with engine.begin() as db:
        await db.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(service, "SessionLocal", sessions)
    monkeypatch.setattr(db_module, "SessionLocal", sessions)
    monkeypatch.setattr(get_settings(), "diagnosis_recovery_enabled", False)
    tag = uuid.uuid4().hex[:12]
    async with sessions() as db:
        user = User(username="loop_" + tag, password="x", role="USER", org_tags="team")
        other = User(username="foreign_" + tag, password="x", role="ADMIN", org_tags="")
        db.add_all([user, other])
        await db.flush()
        conversation = "loop_" + tag
        db.add(ConversationSession(conversation_id=conversation, user_id=str(user.id)))
        db.add(
            SupportApiKey(
                id="key_" + tag,
                user_id=str(user.id),
                app_id="app_main",
                key_masked="demo-***",
                status="ACTIVE",
            )
        )
        await db.commit()
    e = SimpleNamespace(
        sessions=sessions,
        user=user,
        other=other,
        conversation=conversation,
        tag=tag,
        registry=Registry(),
        original="req_" + tag + "_old",
    )
    yield e
    async with sessions() as db:
        owners = [str(user.id), str(other.id)]
        ids = select(DiagnosisSession.diagnosis_id).where(DiagnosisSession.user_id.in_(owners))
        for model in (
            DiagnosisEvidence,
            DiagnosisExecution,
            DiagnosisStep,
            DiagnosisTransition,
            DiagnosisTurn,
        ):
            await db.execute(delete(model).where(model.diagnosis_id.in_(ids)))
        await db.execute(delete(DiagnosisSession).where(DiagnosisSession.user_id.in_(owners)))
        for model in (
            ConversationSession,
            FileUpload,
            SupportApiCallLog,
            SupportApiKey,
            SupportHandoff,
            SupportRequestObservation,
        ):
            await db.execute(delete(model).where(model.user_id.in_(owners)))
        await db.execute(delete(User).where(User.id.in_([user.id, other.id])))
        await db.commit()
    await engine.dispose()


OBS = {
    "AUTH_MISSING": (401, {"authPresent": False}),
    "AUTH_FORMAT": (401, {"authPresent": True, "authSchemeValid": False}),
    "KEY_INVALID": (401, {"authPresent": True, "authSchemeValid": True, "keyStateAtCall": "REVOKED"}),
    "KEY_EXPIRED": (401, {"authPresent": True, "authSchemeValid": True, "keyStateAtCall": "EXPIRED"}),
    "APP_MISMATCH": (
        401,
        {
            "authPresent": True,
            "authSchemeValid": True,
            "keyStateAtCall": "ACTIVE",
            "keyAppIdAtCall": "app_other",
        },
    ),
    "RATE_LIMIT": (429, {"limiterKind": "RATE", "rateObserved": 11, "rateLimit": 10}),
    "CONCURRENCY_LIMIT": (
        429,
        {"limiterKind": "CONCURRENCY", "concurrencyObserved": 6, "concurrencyLimit": 5},
    ),
    "QUOTA_LIMIT": (429, {"limiterKind": "QUOTA", "quotaRemaining": 0}),
}


async def seed(
    e,
    request=None,
    *,
    cause="RATE_LIMIT",
    status=None,
    observations=True,
    when=None,
    app="app_main",
    endpoint="/v1/chat",
    owner=None,
    version=RULE_VERSION,
):
    request = request or e.original
    code, obs = OBS.get(cause, (200, {}))
    async with e.sessions() as db:
        db.add(
            SupportApiCallLog(
                request_id=request,
                user_id=str(owner or e.user.id),
                app_id=app,
                endpoint=endpoint,
                http_status=status if status is not None else code,
                created_at=when or utcnow() - timedelta(minutes=10),
            )
        )
        if observations:
            db.add(
                SupportRequestObservation(
                    request_id=request,
                    user_id=str(owner or e.user.id),
                    service_id="demo-api",
                    rule_version=version,
                    observations_json=json.dumps(obs),
                )
            )
        await db.commit()
    return request


async def begin(e, generation="g1", *, request=None, question=None, entities=None):
    request = request or e.original
    entities = entities or {"request_id": request}
    return await service.begin_turn(
        user_id=str(e.user.id),
        conversation_id=e.conversation,
        generation_id=e.tag + generation,
        question=question or f"核查请求 {request}",
        entities=entities,
        sources={k: "current" for k in entities},
        diagnostic=True,
    )


async def run(e, generation="g1", **kwargs):
    return await execution.run_turn(e.tag + generation, e.user, e.registry, finalize=True, **kwargs)


async def detail(e, case):
    return await service.read_detail(e.user, case)


async def expire(e, generation="g1"):
    async with e.sessions() as db:
        row = await db.get(DiagnosisExecution, e.tag + generation)
        row.lease_until = utcnow() - timedelta(hours=1)
        await db.commit()


@pytest.mark.parametrize("cause", list(OBS))
async def test_at_call_observations_distinguish_eight_causes(env, cause):
    e = env
    await seed(e, cause=cause)
    case = await begin(e)
    await run(e)
    result = await detail(e, case)
    supported = [c for c in result["candidates"] if c["status"] == "SUPPORTED"]
    assert [c["cause"] for c in supported] == [cause]
    assert supported[0]["supportingEvidenceIds"]
    assert result["workflow"]["actions"][0]["evidenceIds"] == supported[0]["supportingEvidenceIds"]
    assert result["status"] == "WAITING_USER_ACTION"
    assert e.registry.counts["query_call_log"] == 1


@pytest.mark.parametrize("options", [{"observations": False}, {"version": "unknown"}])
async def test_http_or_current_key_does_not_prove_root_cause(env, options):
    e = env
    await seed(e, **options)
    case = await begin(e)
    await run(e)
    result = await detail(e, case)
    assert all(c["status"] == "UNDETERMINED" for c in result["candidates"])
    assert not result["workflow"]["actions"]


async def test_supported_cause_is_withheld_on_user_log_conflict(env):
    e = env
    await seed(e)
    case = await begin(e, entities={"request_id": e.original, "http_status": "401"})
    await run(e)
    result = await detail(e, case)
    assert result["status"] == "COLLECTING"
    assert "confirm_http_status" in result["missingFields"]
    assert not result["workflow"]["decision"]["causeConfirmed"]


async def test_user_report_alone_is_not_recovery(env):
    e = env
    await seed(e)
    case = await begin(e, question="已经修复好了")
    await run(e)
    assert (await detail(e, case))["status"] == "WAITING_RECHECK"


async def test_correlated_new_success_resolves_only_the_matching_scope(env):
    e = env
    await seed(e)
    case = await begin(e)
    await run(e)
    new = "req_" + e.tag + "_new"
    await seed(e, new, cause="SUCCESS", when=utcnow())
    assert await begin(e, "g2", request=new, question=f"已调整，复查 {new}") == case
    await run(e, "g2")
    result = await detail(e, case)
    assert result["status"] == "RESOLVED"
    assert result["workflow"]["rechecks"][-1]["scope"] == "this_application_endpoint_request_only"
    assert result["entities"]["request_id"] == e.original
    evidence = next(x for x in result["evidence"] if "recheck_success" in x["supportsClaims"])
    assert evidence["requestId"] == new and evidence["recheckForDiagnosisId"] == case
    assert result["workflow"]["decisionHistory"][0]["decision"]["causeConfirmed"]


@pytest.mark.parametrize("bad", ["owner", "app", "endpoint", "time"])
async def test_unrelated_recheck_never_resolves(env, bad):
    e = env
    await seed(e)
    case = await begin(e)
    await run(e)
    new = "req_" + e.tag + "_bad"
    kwargs = (
        {"owner": e.other.id}
        if bad == "owner"
        else {"app": "app_other"}
        if bad == "app"
        else {"endpoint": "/v1/other"}
        if bad == "endpoint"
        else {"when": utcnow() - timedelta(hours=1)}
    )
    await seed(e, new, cause="SUCCESS", when=kwargs.pop("when", utcnow()), **kwargs)
    await begin(e, "g2", request=new, question=f"复查 {new}")
    await run(e, "g2")
    result = await detail(e, case)
    assert result["status"] == "COLLECTING"
    assert result["workflow"]["rechecks"][-1]["status"] == "REJECTED"


async def test_failed_recheck_keeps_new_causes_and_old_history(env):
    e = env
    await seed(e)
    case = await begin(e)
    await run(e)
    new = "req_" + e.tag + "_failure"
    await seed(e, new, cause="CONCURRENCY_LIMIT", when=utcnow())
    await begin(e, "g2", request=new, question=f"已调整后复查 {new}")
    await run(e, "g2")
    result = await detail(e, case)
    assert result["status"] == "WAITING_USER_ACTION"
    assert result["workflow"]["rechecks"][-1]["status"] == "STILL_FAILING"
    assert [c["cause"] for c in result["candidates"] if c["status"] == "SUPPORTED"] == ["CONCURRENCY_LIMIT"]


async def test_timeout_is_retried_but_not_found_and_denied_are_not(env):
    e = env
    await seed(e)
    e.registry.failures["query_call_log"] = [ToolResult("TIMEOUT", error="temporary timeout")]
    case = await begin(e)
    await run(e)
    assert e.registry.counts["query_call_log"] == 2
    assert (await detail(e, case))["status"] == "WAITING_USER_ACTION"
    async with e.sessions() as db:
        step = await db.scalar(
            select(DiagnosisStep).where(
                DiagnosisStep.generation_id == e.tag + "g1", DiagnosisStep.tool_name == "query_call_log"
            )
        )
        assert step.attempts == 2


async def test_unknown_request_stops_without_retry(env):
    e = env
    case = await begin(e)
    await run(e)
    assert e.registry.counts["query_call_log"] == 1
    result = await detail(e, case)
    assert "valid_request_id" in result["missingFields"]


async def test_permission_failure_preserves_event_and_creates_one_real_handoff(env):
    e = env
    await seed(e)
    e.registry.failures["query_request_observation"] = [ToolResult("DENIED", error="forbidden")]
    case = await begin(e)
    await run(e)
    result = await detail(e, case)
    assert e.registry.counts["query_request_observation"] == 1
    assert result["status"] == "HANDED_OFF"
    assert any(x.get("tool") == "query_call_log" and x["verified"] for x in result["evidence"])
    async with e.sessions() as db:
        tickets = (await db.scalars(select(SupportHandoff).where(SupportHandoff.diagnosis_id == case))).all()
        assert len(tickets) == 1 and "unresolved" in tickets[0].summary


class Crash(RuntimeError):
    pass


@pytest.mark.parametrize("point", ["after_call", "after_checkpoint"])
async def test_restart_recovers_known_or_unknown_read_without_duplicate_publication(env, point):
    e = env
    await seed(e)
    case = await begin(e)

    async def crash(call, result):
        if call.name == "query_call_log":
            raise Crash("simulated process interruption")

    with pytest.raises(Crash):
        await run(e, **{point: crash})
    before = e.registry.counts["query_call_log"]
    assert not await execution.recover_execution(e.tag + "g1", e.registry)  # healthy lease isn't stolen
    await expire(e)
    assert await execution.recover_execution(e.tag + "g1", e.registry)
    assert e.registry.counts["query_call_log"] == before + (1 if point == "after_call" else 0)
    result = await detail(e, case)
    assert result["status"] == "WAITING_USER_ACTION"
    assert len([x for x in result["transitions"] if x["reason"] == "EVENT_CHECKED"]) == 1


async def test_cached_reads_are_case_scoped_and_current_snapshots_expire(env):
    e = env
    await seed(e)
    case = await begin(e)
    await run(e)
    first = dict(e.registry.counts)
    await begin(e, "g2", question="继续")
    await run(e, "g2")
    assert dict(e.registry.counts) == first
    async with e.sessions() as db:
        rows = (
            await db.scalars(
                select(DiagnosisStep).where(
                    DiagnosisStep.diagnosis_id == case, DiagnosisStep.tool_name == "query_api_key_status"
                )
            )
        ).all()
        for row in rows:
            row.expires_at = utcnow() - timedelta(seconds=10)
        await db.commit()
    await begin(e, "g3", question="继续")
    await run(e, "g3")
    assert e.registry.counts["query_call_log"] == first["query_call_log"]
    assert e.registry.counts["query_api_key_status"] == first["query_api_key_status"] + 1


async def test_stale_worker_cannot_overwrite_takeover(env):
    e = env
    await seed(e)
    case = await begin(e)
    entered, release = asyncio.Event(), asyncio.Event()
    original = e.registry.execute
    first = True

    async def gated(name, args, context):
        nonlocal first
        if name == "query_call_log" and first:
            first = False
            entered.set()
            await release.wait()
        return await original(name, args, context)

    e.registry.execute = gated
    old = asyncio.create_task(run(e))
    await asyncio.wait_for(entered.wait(), 10)
    await expire(e)
    await run(e)
    release.set()
    with pytest.raises(execution.ExecutionLost):
        await old
    assert (await detail(e, case))["status"] == "WAITING_USER_ACTION"


async def test_persisted_handoff_intent_survives_interruption_and_is_unique(env):
    from app.support.handoff import create_handoff

    e = env
    await seed(e)
    case = await begin(e, question="转人工客服处理")

    async def stop():
        raise Crash("after intent commit, before ticket")

    with pytest.raises(Crash):
        await run(e, after_finalize=stop)
    generation_id = e.tag + "g1"
    async with e.sessions() as db:
        record = await db.get(DiagnosisExecution, generation_id)
        old_lease = execution.Lease(generation_id, record.owner, record.epoch)
        with pytest.raises(PermissionError, match="requires its execution lease"):
            await create_handoff(db, e.user, generation_id=generation_id)
    await expire(e)
    async with e.sessions() as db:
        with pytest.raises(PermissionError, match="lease unavailable"):
            await create_handoff(db, e.user, generation_id=generation_id, diagnosis_lease=old_lease)
    counts = dict(e.registry.counts)
    assert await execution.recover_execution(e.tag + "g1", e.registry)
    assert dict(e.registry.counts) == counts
    assert (await detail(e, case))["status"] == "HANDED_OFF"
    assert not await execution.recover_execution(e.tag + "g1", e.registry)
    async with e.sessions() as db:
        assert (
            len((await db.scalars(select(SupportHandoff).where(SupportHandoff.diagnosis_id == case))).all())
            == 1
        )


async def test_no_progress_and_budget_have_finite_handoff_paths(env, monkeypatch):
    e = env
    await seed(e)
    monkeypatch.setattr(get_settings(), "diagnosis_turn_attempt_budget", 1)
    case = await begin(e)
    await run(e)
    result = await detail(e, case)
    assert result["status"] == "HANDED_OFF"
    assert result["workflow"]["toolAttemptsUsed"] == 1


async def test_lost_ticket_commit_acknowledgement_reuses_case_identity(env, monkeypatch):
    e = env
    await seed(e)
    case = await begin(e, question="请转人工客服")
    session_type = e.sessions.class_
    original = session_type.commit
    lost = False

    async def commit(self):
        nonlocal lost
        ticket = any(isinstance(row, SupportHandoff) for row in self.new)
        await original(self)
        if ticket and not lost:
            lost = True
            raise ConnectionError("committed, acknowledgement lost")

    monkeypatch.setattr(session_type, "commit", commit)
    await run(e)
    assert lost
    assert (await detail(e, case))["status"] == "HANDED_OFF"
    async with e.sessions() as db:
        assert (
            len((await db.scalars(select(SupportHandoff).where(SupportHandoff.diagnosis_id == case))).all())
            == 1
        )


async def test_duplicate_case_handoff_across_generations_is_one_ticket(env):
    from app.support.handoff import create_handoff

    e = env
    await seed(e)
    case = await begin(e, question="请转人工")
    await run(e)
    async with e.sessions() as db:
        row = await db.get(DiagnosisSession, case)
        row.last_generation_id = e.tag + "g2"
        db.add(DiagnosisTurn(generation_id=e.tag + "g2", diagnosis_id=case))
        await db.commit()

    async def create():
        async with e.sessions() as db:
            return (
                await create_handoff(
                    db, e.user, generation_id=e.tag + "g2", reason="repeat", summary="same case repeat"
                )
            ).handoff_id

    ids = await asyncio.gather(create(), create())
    assert ids[0] == ids[1]
    async with e.sessions() as db:
        assert (
            len((await db.scalars(select(SupportHandoff).where(SupportHandoff.diagnosis_id == case))).all())
            == 1
        )


async def test_http_recheck_idempotency_revision_and_cross_user_guards(env):
    from app.api.v1.diagnoses import router
    from app.core.deps import current_user
    from app.db.session import get_db

    e = env
    await seed(e)
    case = await begin(e)
    await run(e)
    new = "req_" + e.tag + "_api"
    await seed(e, new, cause="SUCCESS", when=utcnow())
    snapshot = await detail(e, case)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[current_user] = lambda: e.user

    async def session_override():
        async with e.sessions() as db:
            yield db

    app.dependency_overrides[get_db] = session_override
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        body = {"requestId": new, "expectedRevision": snapshot["revision"], "idempotencyKey": "same-request"}
        stale = await client.post(f"/diagnoses/{case}/rechecks", json={**body, "expectedRevision": 1})
        assert stale.status_code == 409
        first = await client.post(f"/diagnoses/{case}/rechecks", json=body)
        assert first.status_code == 202
        after = (await client.get(f"/diagnoses/{case}")).json()["data"]
        assert after["status"] == "RESOLVED"
        duplicate = await client.post(f"/diagnoses/{case}/rechecks", json=body)
        assert (
            duplicate.status_code == 202
            and duplicate.json()["data"]["generationId"] == first.json()["data"]["generationId"]
        )
        conflict = await client.post(
            f"/diagnoses/{case}/rechecks", json={**body, "requestId": "req_different"}
        )
        assert conflict.status_code == 409
        app.dependency_overrides[current_user] = lambda: e.other
        assert (await client.post(f"/diagnoses/{case}/rechecks", json=body)).status_code == 404
        assert (
            await client.post(f"/diagnoses/{case}/resume", json={"generationId": e.tag + "g1"})
        ).status_code == 404


async def test_knowledge_update_and_revocation_do_not_replay_old_text(env):
    from app.knowledge.citations import issue_citation

    e = env
    await seed(e)
    handle = e.tag.ljust(32, "a")
    async with e.sessions() as db:
        db.add(
            FileUpload(
                file_md5=handle,
                user_id=str(e.other.id),
                file_name="private-source.md",
                storage_key="fixture",
                org_tag="team",
                active_vector_version="old-build",
            )
        )
        await db.commit()
    case = await begin(e)
    lease, outcomes = await execution.run_turn(e.tag + "g1", e.user, e.registry)
    await service.finish_turn(
        user_id=str(e.user.id),
        conversation_id=e.conversation,
        generation_id=e.tag + "g1",
        question="排查请求",
        outcomes=outcomes,
        references=[
            {
                "fileMd5": handle,
                "indexVersion": "old-build",
                "citationId": issue_citation(str(e.other.id), handle, "old-build", 0),
            }
        ],
        execution_epoch=lease.epoch,
    )
    before = await detail(e, case)
    reference = next(x for x in before["evidence"] if x.get("source"))
    assert reference["freshness"] == "AUTHORIZED_ACTIVE_DOCUMENT"
    async with e.sessions() as db:
        file = await db.scalar(select(FileUpload).where(FileUpload.file_md5 == handle))
        file.active_vector_version = "new-build"
        member = await db.get(User, e.user.id)
        member.org_tags = ""
        await db.commit()
    after = await detail(e, case)
    invalid = next(x for x in after["evidence"] if x["evidenceId"] == reference["evidenceId"])
    assert invalid["freshness"] == "DOCUMENT_UNAVAILABLE" and "source" not in invalid
    await begin(e, "g2", question="继续")
    await run(e, "g2")
    async with e.sessions() as db:
        checkpoints = (
            await db.scalars(select(DiagnosisStep).where(DiagnosisStep.diagnosis_id == case))
        ).all()
        assert checkpoints and all(
            s.tool_name in execution.READ_TOOLS and "private-source.md" not in (s.result_json or "")
            for s in checkpoints
        )
    assert (await detail(e, case))["workflow"]["decision"][
        "causeConfirmed"
    ]  # local at-call observations, not revoked text


async def test_two_inconclusive_rounds_create_actual_handoff(env):
    e = env
    await seed(e, observations=False)
    case = await begin(e)
    await run(e)
    assert (await detail(e, case))["status"] != "HANDED_OFF"
    await begin(e, "g2", question="继续核查")
    await run(e, "g2")
    result = await detail(e, case)
    assert result["status"] == "HANDED_OFF"
    assert "NO_PROGRESS_OR_RECHECK_LIMIT" in result["workflow"]["decision"]["handoffReasons"]
    async with e.sessions() as db:
        tickets = (await db.scalars(select(SupportHandoff).where(SupportHandoff.diagnosis_id == case))).all()
        assert len(tickets) == 1


async def test_permanent_invalid_argument_is_not_retried(env):
    e = env
    await seed(e)
    e.registry.failures["query_call_log"] = [ToolResult("INVALID_ARGUMENT", error="invalid fixture argument")]
    case = await begin(e)
    await run(e)
    assert e.registry.counts["query_call_log"] == 1
    assert not (await detail(e, case))["workflow"]["decision"]["causeConfirmed"]


async def test_planner_can_stop_only_for_matching_versioned_observations(env):
    from copy import deepcopy
    from app.diagnosis.planning import api_planning_complete
    e = env
    await seed(e)
    await begin(e)
    _, outcomes = await execution.run_turn(e.tag+"g1", e.user, e.registry)
    entities = {"request_id": e.original, "http_status": "429"}
    assert api_planning_complete(str(e.user.id), e.tag+"g1", entities, outcomes)
    assert not api_planning_complete(str(e.user.id), e.tag+"g1", {**entities, "http_status": "401"}, outcomes)
    assert not api_planning_complete(str(e.other.id), e.tag+"g1", entities, outcomes)
    assert not api_planning_complete(str(e.user.id), e.tag+"g1", entities, [(c,r) for c,r in outcomes if c.name != "query_request_observation"])
    invalid = deepcopy(outcomes)
    next(r for c,r in invalid if c.name == "query_request_observation").data["ruleVersion"] = "unknown"
    assert not api_planning_complete(str(e.user.id), e.tag+"g1", entities, invalid)


def test_counter_booleans_and_inconsistent_instrumentation_are_unknown():
    from app.diagnosis.rules import _evaluate

    assert _evaluate("AUTH_MISSING", {"authPresent": "false"}, "app") is None
    assert (
        _evaluate(
            "KEY_EXPIRED", {"authPresent": True, "authSchemeValid": True, "keyStateAtCall": "UNKNOWN"}, "app"
        )
        is None
    )

    assert _evaluate("QUOTA_LIMIT", {"limiterKind": "QUOTA", "quotaRemaining": False}, "app") is None
    assert _evaluate("RATE_LIMIT", {"limiterKind": "RATE", "rateObserved": 1, "rateLimit": 10}, "app") is None


async def test_full_graph_diagnoses_and_rechecks_without_model_inventing_conclusions(env, monkeypatch):
    from app.agent.llm import llm_service
    from app.agent.runtime import AgentRuntime
    from app.tools.local.support import CreateSupportHandoffTool

    e = env
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_api_key", "")
    monkeypatch.setattr(settings, "skills_semantic_routing_enabled", False)
    monkeypatch.setattr(settings, "redis_enabled", False)

    async def no_plan(*args, **kwargs):
        if False:
            yield {}

    async def forbidden_model_answer(*args, **kwargs):
        raise AssertionError("incident conclusions must come from the validated decision")
        yield ""

    monkeypatch.setattr(llm_service, "stream_agent_turn", no_plan)
    monkeypatch.setattr(llm_service, "stream_messages", forbidden_model_answer)
    e.registry.register(CreateSupportHandoffTool())
    runtime = AgentRuntime(e.registry)
    await seed(e, cause="KEY_EXPIRED")
    events = []

    async def send(event):
        events.append(event)

    async def chunk(_):
        pass

    question = f"请求 {e.original} 返回401"
    answer, _ = await runtime.run(
        user=e.user,
        question=question,
        history=[],
        conversation_id=e.conversation,
        generation_id=e.tag + "g1",
        send_json=send,
        on_chunk=chunk,
    )
    assert "Key 在请求时已过期" in answer
    initial = next(event["diagnosis"] for event in reversed(events) if event.get("type") == "diagnosis_state")
    new = "req_" + e.tag + "_graph"
    await seed(e, new, cause="SUCCESS", when=utcnow())
    answer, _ = await runtime.run(
        user=e.user,
        question=f"已调整，复查 {new}",
        history=[{"role": "user", "content": question}],
        conversation_id=e.conversation,
        generation_id=e.tag + "g2",
        send_json=send,
        on_chunk=chunk,
    )
    assert "新请求范围内恢复" in answer
    final = await detail(e, initial["diagnosisId"])
    assert final["status"] == "RESOLVED" and len(final["generationIds"]) == 2
