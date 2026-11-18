import asyncio
import os
from datetime import timedelta

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.agent.entities import resolve_entities
from app.agent.types import AgentToolCall
from app.api.v1.diagnoses import router
from app.core.deps import current_user
from app.core.time import utcnow
from app.db.models import (
    Base,
    ConversationSession,
    DiagnosisEvidence,
    DiagnosisSession,
    DiagnosisTransition,
    DiagnosisTurn,
    FileUpload,
    SupportApiCallLog,
    SupportHandoff,
    User,
)
from app.db.session import get_db
from app.diagnosis import service
from app.diagnosis.evidence import freshness, tool_evidence
from app.knowledge.citations import issue_citation
from app.support.api_diagnostics import query_call_log, query_recent_call_stats, timestamp
from app.tools.base import ToolResult


@pytest.fixture
async def setup_case(tmp_path, monkeypatch):
    engine = create_async_engine(
        os.environ.get("PHASE2_TEST_MYSQL_URL") or f"sqlite+aiosqlite:///{(tmp_path / 'cases.db').as_posix()}"
    )
    async with engine.begin() as db:
        await db.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(service, "SessionLocal", sessions)
    async with sessions() as db:
        user = User(username="owner", password="x", role="USER", org_tags="team")
        other = User(username="other", password="x", role="ADMIN", org_tags="")
        db.add_all([user, other])
        await db.flush()
        db.add(ConversationSession(conversation_id="conversation", user_id=str(user.id)))
        await db.commit()
    yield sessions, user, other
    async with sessions() as db:
        owners = [str(user.id), str(other.id)]
        case_ids = select(DiagnosisSession.diagnosis_id).where(DiagnosisSession.user_id.in_(owners))
        for table in (DiagnosisEvidence, DiagnosisTransition, DiagnosisTurn):
            await db.execute(delete(table).where(table.diagnosis_id.in_(case_ids)))
        await db.execute(delete(DiagnosisSession).where(DiagnosisSession.user_id.in_(owners)))
        for table in (ConversationSession, FileUpload, SupportApiCallLog, SupportHandoff):
            await db.execute(delete(table).where(table.user_id.in_(owners)))
        await db.execute(delete(User).where(User.id.in_([user.id, other.id])))
        await db.commit()
    await engine.dispose()


async def begin(user, generation="g1", entities=None, question="请求 req_one 返回429", diagnostic=True):
    entities = entities if entities is not None else {"request_id": "req_one"}
    return await service.begin_turn(
        user_id=str(user.id),
        conversation_id="conversation",
        generation_id=generation,
        question=question,
        entities=entities,
        sources={key: "current" for key in entities},
        diagnostic=diagnostic,
    )


def log_result(request="req_one", **changes):
    data = {
        "found": True,
        "requestId": request,
        "appId": "app_one",
        "httpStatus": 429,
        "endpoint": "/v1/chat",
        "calledAt": timestamp(utcnow() - timedelta(days=1)),
        "queriedAt": timestamp(utcnow()),
    }
    data.update(changes)
    return (
        AgentToolCall("log", "query_call_log", {"request_id": request}, source_agent="api_diagnostic"),
        ToolResult("SUCCESS", data=data),
    )


async def finish(user, generation="g1", outcomes=None, **kwargs):
    return await service.finish_turn(
        user_id=str(user.id),
        conversation_id="conversation",
        generation_id=generation,
        outcomes=outcomes if outcomes is not None else [log_result()],
        references=kwargs.pop("references", []),
        question=kwargs.pop("question", "继续排查"),
        **kwargs,
    )


async def test_durable_case_reused_and_finished_turn_idempotent(setup_case):
    sessions, user, _ = setup_case
    case_id = await begin(user)
    assert await begin(user) == case_id
    await finish(user)
    first = await service.read_detail(user, case_id)
    assert first["status"] == "WAITING_USER_ACTION"
    assert first["entities"]["app_id"] == "app_one"
    assert first["entitySources"]["app_id"].startswith("tool:")
    await finish(user)
    assert len((await service.read_detail(user, case_id))["evidence"]) == len(first["evidence"])
    assert await begin(user, "g2", {"request_id": "req_one"}, "那为什么？") == case_id
    await finish(user, "g2")
    result = await service.read_detail(user, case_id)
    assert result["generationIds"] == ["g1", "g2"]
    assert all(
        e["freshness"] == "HISTORICAL_ONLY" for e in result["evidence"] if e.get("tool") == "query_call_log"
    )


async def test_new_request_and_topic_switch_preserve_old_cases(setup_case):
    _, user, _ = setup_case
    first = await begin(user)
    second = await begin(user, "g2", {"request_id": "req_two"}, "另一个请求 req_two")
    assert first != second
    assert (await service.read_detail(user, first))["endReason"] == "NEW_INCIDENT"
    assert await begin(user, "g3", {}, "介绍退款政策", False) is None
    assert (await service.read_detail(user, second))["status"] == "CLOSED_UNRESOLVED"


async def test_late_generation_cannot_overwrite_latest_state(setup_case):
    _, user, _ = setup_case
    case_id = await begin(user)
    await begin(user, "g2", {"request_id": "req_one"}, "继续")
    await finish(user, "g2", outcomes=[log_result(found=False)])
    before = await service.read_detail(user, case_id)
    await finish(user, "g1")
    after = await service.read_detail(user, case_id)
    assert after == before


async def test_unknown_request_rule_and_report_never_become_personal_event(setup_case):
    _, user, _ = setup_case
    case_id = await begin(user)
    rule = (
        AgentToolCall("rule", "query_error_code", {"code": "RATE_LIMIT"}),
        ToolResult("SUCCESS", data={"found": True, "code": "RATE_LIMIT", "cause": "limit"}),
    )
    await finish(user, outcomes=[log_result(found=False), rule])
    result = await service.read_detail(user, case_id)
    assert result["status"] == "COLLECTING"
    assert "valid_request_id" in result["missingFields"]
    assert all(not e["verified"] for e in result["evidence"] if e["sourceType"] != "BUSINESS_QUERY")
    assert not any("request_event" in e["supportsClaims"] for e in result["evidence"])


async def test_user_report_of_recovery_is_not_resolved(setup_case):
    _, user, _ = setup_case
    case_id = await begin(user)
    await finish(user, question="已经修复好了")
    result = await service.read_detail(user, case_id)
    assert result["status"] == "WAITING_RECHECK"
    assert "新 request_id" in result["nextAction"]
    await begin(user, "g2", {"request_id": "req_one"}, "继续")
    await finish(user, "g2")
    assert (await service.read_detail(user, case_id))["status"] == "WAITING_RECHECK"


async def test_conflicting_user_status_is_retained_as_gap(setup_case):
    _, user, _ = setup_case
    case_id = await begin(user, entities={"request_id": "req_one", "http_status": "401"})
    await finish(user)
    result = await service.read_detail(user, case_id)
    assert result["entities"]["http_status"] == "401"
    assert "confirm_http_status" in result["missingFields"]
    assert result["status"] == "COLLECTING"


async def test_current_and_incident_stats_are_bounded_by_user_app_and_end(setup_case):
    sessions, user, other = setup_case
    now = utcnow()
    async with sessions() as db:
        for rid, owner, app, status, when in [
            ("old", user.id, "app_one", 429, now - timedelta(days=1)),
            ("after-old", user.id, "app_one", 200, now - timedelta(hours=23)),
            ("current", user.id, "app_one", 200, now - timedelta(minutes=2)),
            ("other-app", user.id, "app_two", 429, now - timedelta(minutes=1)),
            ("foreign", other.id, "app_one", 429, now - timedelta(minutes=1)),
            ("future", user.id, "app_one", 429, now + timedelta(hours=1)),
        ]:
            db.add(
                SupportApiCallLog(
                    request_id=rid,
                    user_id=str(owner),
                    app_id=app,
                    endpoint="/v1/chat",
                    http_status=status,
                    created_at=when,
                )
            )
        await db.commit()
        current = await query_recent_call_stats(db, str(user.id), app_id="app_one", endpoint="/v1/chat")
        assert current["total"] == 1 and current["rateLimitedCount"] == 0
        assert current["windowType"] == "current" and "anchorAt" not in current
        past = await query_recent_call_stats(db, str(user.id), request_id="old", window="incident")
        assert past["total"] == 1 and past["rateLimitedCount"] == 1
        assert past["windowType"] == "incident" and past["appId"] == "app_one"
        explicit = await query_recent_call_stats(
            db,
            str(user.id),
            app_id="app_one",
            window="explicit",
            start_at=timestamp(now - timedelta(minutes=3)),
            end_at=timestamp(now),
        )
        assert explicit["total"] == 1
        assert (await query_call_log(db, str(user.id), "foreign"))["found"] is False
        assert (await query_recent_call_stats(db, str(user.id), window="incident", request_id="foreign"))[
            "found"
        ] is False
        with pytest.raises(ValueError):
            await query_recent_call_stats(
                db, str(user.id), window="incident", request_id="old", app_id="app_two"
            )
        with pytest.raises(ValueError):
            await query_recent_call_stats(
                db,
                str(user.id),
                window="explicit",
                start_at=timestamp(now),
                end_at=timestamp(now - timedelta(hours=1)),
            )


def test_explicit_entities_win_and_new_incident_drops_stale_anchors():
    history = [{"role": "user", "content": "请求 req_old 返回401，app_one"}]
    resolved, sources = resolve_entities(
        "继续查 req_new",
        history,
        {"request_id": "req_old"},
        {"request_id": "req_old", "app_id": "app_one"},
        True,
    )
    assert resolved == {"request_id": "req_new"} and sources["request_id"] == "current"
    resolved, _ = resolve_entities("换个应用 app_two", history, follow_up=True)
    assert resolved == {"app_id": "app_two"}
    resolved, _ = resolve_entities("退款政策呢", history, follow_up=True)
    assert resolved == {}
    history += [{"role": "user", "content": "请介绍退款政策"}]
    assert resolve_entities("那为什么？", history, remembered_entities={"request_id": "req_old"})[0] == {}


def test_same_incident_quota_question_keeps_request():
    entities, _ = resolve_entities(
        "刚才的限流是不是套餐配额问题？", [{"role": "user", "content": "请求 req_one 返回429"}]
    )
    assert entities["request_id"] == "req_one"


def test_freshness_and_foreign_result_cannot_support_current_state():
    call = AgentToolCall("key", "query_api_key_status", {"app_id": "app_one"})
    result = ToolResult(
        "SUCCESS",
        data={
            "found": True,
            "keys": [],
            "queriedAt": timestamp(utcnow() - timedelta(minutes=1)),
            "ownerUserId": "1",
        },
    )
    record = tool_evidence("1", "g", [(call, result)])[0]
    assert freshness(record) == "EXPIRED"
    record = tool_evidence("2", "g", [(call, result)])[0]
    assert not record["verified"] and record["resultStatus"] == "SCOPE_MISMATCH"


def test_expired_snapshots_are_excluded_from_answer_facts():
    from app.agent.evidence import _facts_for
    from app.diagnosis.evidence import expired_current_facts

    expired = timestamp(utcnow() - timedelta(minutes=2))
    assert _facts_for("query_api_key_status", {"found": True, "keys": [], "queriedAt": expired}) == []
    assert expired_current_facts([{"evidenceContext": {"scope": "current_snapshot", "validUntil": expired}}])
    assert not expired_current_facts(
        [{"evidenceContext": {"scope": "historical_event", "validUntil": expired}}]
    )


def test_digits_inside_ids_are_not_http_status_evidence():
    from app.agent.entities import extract_entities

    assert "http_status" not in extract_entities("检查 req_abc401x 和 app_429code")


async def test_foreign_business_payload_is_blocked_before_agent_planning():
    from app.agent.runtime import AgentRuntime
    from app.tools.base import BaseTool
    from app.tools.registry import ToolRegistry

    class ForeignLog(BaseTool):
        name = "query_call_log"
        description = "scope fixture"
        input_schema = {"type": "object", "properties": {}}

        async def execute(self, context, arguments):
            return {"found": True, "ownerUserId": "other", "httpStatus": 200}

    events = []

    async def send(event):
        events.append(event)

    user = User(id=1, username="fixture", password="x", role="USER")
    result = await AgentRuntime(ToolRegistry([ForeignLog()]))._execute_parallel(
        calls=[AgentToolCall("foreign", "query_call_log", {})],
        user=user,
        generation_id="scope-fixture",
        send_json=send,
        step=0,
        active_skills=frozenset(),
    )
    assert result[0].status == "DENIED" and result[0].data is None
    assert events[-1]["resultStatus"] == "DENIED"


async def test_case_detail_rechecks_document_acl_and_active_build(setup_case):
    sessions, user, other = setup_case
    handle = "a" * 32
    async with sessions() as db:
        db.add(
            FileUpload(
                file_md5=handle,
                user_id=str(other.id),
                file_name="secret.md",
                total_size=1,
                storage_key="test",
                active_vector_version="b1",
                org_tag="team",
            )
        )
        await db.commit()
    case_id = await begin(user)
    reference = {
        "fileMd5": handle,
        "indexVersion": "b1",
        "citationId": issue_citation(str(other.id), handle, "b1", 0),
    }
    await finish(user, references=[reference])
    before = await service.read_detail(user, case_id)
    document = next(e for e in before["evidence"] if e.get("source"))
    assert document["freshness"] == "AUTHORIZED_ACTIVE_DOCUMENT"
    async with sessions() as db:
        member = await db.get(User, user.id)
        member.org_tags = ""
        await db.commit()
    after = await service.read_detail(user, case_id)
    document = next(e for e in after["evidence"] if e["evidenceId"] == document["evidenceId"])
    assert document["freshness"] == "DOCUMENT_UNAVAILABLE"
    assert "source" not in document


async def test_owner_scoped_http_list_detail_generation_even_for_admin(setup_case):
    sessions, user, other = setup_case
    case_id = await begin(user)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[current_user] = lambda: user

    async def db_override():
        async with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = db_override
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get(f"/diagnoses/{case_id}")).status_code == 200
        assert (await client.get("/diagnoses/by-generation/g1")).status_code == 200
        app.dependency_overrides[current_user] = lambda: other
        assert (await client.get(f"/diagnoses/{case_id}")).status_code == 404
        assert (await client.get("/diagnoses/by-generation/g1")).status_code == 404
        assert (await client.get("/diagnoses")).json()["data"] == []
        assert await begin(other, "foreign") is None


async def test_concurrent_same_generation_creates_one_case(setup_case):
    sessions, user, _ = setup_case
    ids = await asyncio.gather(begin(user), begin(user))
    assert ids[0] == ids[1]
    async with sessions() as db:
        assert len(list((await db.scalars(select(DiagnosisSession))).all())) == 1


async def test_terminal_states_require_real_handoff_and_recheck(setup_case):
    sessions, user, _ = setup_case
    case_id = await begin(user)
    async with sessions() as db:
        case = await db.get(DiagnosisSession, case_id)
        with pytest.raises(ValueError):
            service.transition(db, case, "HANDED_OFF", "MODEL_SAID_SO", "g1")
        with pytest.raises(ValueError):
            service.transition(db, case, "RESOLVED", "USER_SAID_SO", "g1")
        db.add(
            SupportHandoff(
                handoff_id="ticket",
                user_id=str(user.id),
                conversation_id="conversation",
                generation_id="g1",
                reason="requested",
                summary="safe",
            )
        )
        await db.commit()
    await finish(user, handoff={"success": True, "handoffId": "ticket"})
    assert (await service.read_detail(user, case_id))["status"] == "HANDED_OFF"
    async with sessions() as db:
        transitions = (await db.scalars(select(DiagnosisTransition))).all()
        assert transitions[-1].reason == "PERSISTED_HANDOFF"


async def test_partial_failure_retains_successful_event(setup_case):
    _, user, _ = setup_case
    case_id = await begin(user)
    failure = (AgentToolCall("key", "query_api_key_status", {"app_id": "app_one"}), ToolResult("TIMEOUT"))
    await finish(user, outcomes=[log_result(), failure])
    result = await service.read_detail(user, case_id)
    assert result["status"] == "COLLECTING"
    assert any(e.get("tool") == "query_call_log" and e["verified"] for e in result["evidence"])
    assert "business_evidence_unavailable" in result["missingFields"]


async def test_generation_collision_never_attaches_another_user_case(setup_case):
    sessions, user, other = setup_case
    case_id = await begin(user)
    async with sessions() as db:
        db.add(ConversationSession(conversation_id="other-conversation", user_id=str(other.id)))
        await db.commit()
    result = await service.begin_turn(
        user_id=str(other.id),
        conversation_id="other-conversation",
        generation_id="g1",
        question="req_one",
        entities={"request_id": "req_one"},
        sources={},
        diagnostic=True,
    )
    assert result is None
    assert (
        await service.finish_turn(
            user_id=str(other.id),
            conversation_id="other-conversation",
            generation_id="g1",
            outcomes=[log_result()],
            references=[],
            question="继续",
        )
        is None
    )
    assert (await service.read_detail(user, case_id))["status"] == "VERIFYING"


async def test_only_correlated_fresh_success_can_unlock_resolution(setup_case):
    sessions, user, _ = setup_case
    case_id = await begin(user)
    async with sessions() as db:
        case = await db.get(DiagnosisSession, case_id)
        case.app_id = "app_one"
        case.status = "WAITING_RECHECK"
        record = tool_evidence(
            str(user.id), "g1", [log_result("req_recheck", httpStatus=200, calledAt=timestamp(utcnow()))]
        )[0]
        with pytest.raises(ValueError):
            service.transition(db, case, "RESOLVED", "UNRELATED_SUCCESS", "g1", [record])
        record["recheckForDiagnosisId"] = case_id
        record["supportsClaims"] = ["recheck_success"]
        service.transition(db, case, "RESOLVED", "CORRELATED_BUSINESS_RECHECK", "g1", [record])
        await db.commit()
    assert (await service.read_detail(user, case_id))["status"] == "RESOLVED"


async def test_workflow_attaches_case_to_actual_conversation(setup_case, monkeypatch):
    from app.agent.runtime import AgentRuntime
    from app.agent.llm import llm_service
    from app.core.config import get_settings
    from app.db import session as db_module
    from app.tools.local.api_support import (
        QueryCallLogTool,
        QueryRecentCallStatsTool,
        QueryApiKeyStatusTool,
        QueryErrorCodeTool,
    )
    from app.tools.registry import ToolRegistry

    sessions, user, _ = setup_case
    monkeypatch.setattr(db_module, "SessionLocal", sessions)
    settings = get_settings()
    monkeypatch.setattr(settings, "skills_semantic_routing_enabled", False)
    monkeypatch.setattr(settings, "llm_api_key", "")
    monkeypatch.setattr(settings, "redis_enabled", False)

    async def no_plan(*args, **kwargs):
        if False:
            yield {}

    async def final_response(*args, **kwargs):
        yield "该请求在记录时间返回 HTTP 429；当前恢复情况仍需核查。"

    monkeypatch.setattr(llm_service, "stream_agent_turn", no_plan)
    monkeypatch.setattr(llm_service, "stream_messages", final_response)
    async with sessions() as db:
        db.add(
            SupportApiCallLog(
                request_id="req_one",
                user_id=str(user.id),
                app_id="app_one",
                endpoint="/v1/chat",
                http_status=429,
                created_at=utcnow() - timedelta(days=1),
            )
        )
        await db.commit()
    registry = ToolRegistry(
        [QueryCallLogTool(), QueryRecentCallStatsTool(), QueryApiKeyStatusTool(), QueryErrorCodeTool()]
    )
    runtime = AgentRuntime(registry)
    events, chunks = [], []

    async def send(event):
        events.append(event)

    async def on_chunk(chunk):
        chunks.append(chunk)

    await runtime.run(
        user=user,
        question="请求 req_one 返回429",
        history=[],
        conversation_id="conversation",
        generation_id="workflow-g1",
        send_json=send,
        on_chunk=on_chunk,
    )
    updates = [e["diagnosis"] for e in events if e.get("type") == "diagnosis_state"]
    assert len(updates) == 2
    assert updates[0]["status"] == "VERIFYING"
    assert updates[-1]["status"] in {"COLLECTING", "WAITING_USER_ACTION"}
    assert updates[-1]["generationIds"] == ["workflow-g1"]
    stats = next(e for e in updates[-1]["evidence"] if e.get("tool") == "query_recent_call_stats")
    assert stats["scope"] == "historical_window"
    assert stats["appId"] == "app_one"
