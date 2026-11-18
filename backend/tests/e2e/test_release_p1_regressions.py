"""Release regressions for conversation binding and durable generation ownership."""
import asyncio
import os
from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.accounting.usage import usage_service
from app.agent.chat import stream_chat
from app.agent.generation import GenerationRuntime
from app.core.config import get_settings
from app.core.time import utcnow
from app.db.models import Base, ConversationMessage, ConversationSession, GenerationState, LLMTokenReservation, User, UserTokenRecord


@pytest.fixture
async def business(tmp_path, monkeypatch):
    url = os.environ.get("P1_MYSQL_TEST_URL") or f"sqlite+aiosqlite:///{(tmp_path / 'business.sqlite').as_posix()}"
    if os.environ.get("P1_MYSQL_TEST_URL"):
        assert (make_url(url).database or "").startswith("p1_release_"), "Use a dedicated scratch database"
    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr("app.db.session.SessionLocal", sessions)
    settings = get_settings()
    monkeypatch.setattr(settings, "redis_enabled", False)
    monkeypatch.setattr(settings, "context_system_enabled", False)
    monkeypatch.setattr(settings, "context_shadow_enabled", False)
    async with sessions() as db:
        db.add(User(id=1, username="owner", password="x", llm_token_balance=100000))
        db.add_all([ConversationSession(conversation_id=cid, user_id=uid, title=cid, status=status)
                    for cid, uid, status in [("tab-a", "1", "ACTIVE"), ("tab-b", "1", "ACTIVE"),
                                             ("other", "2", "ACTIVE"), ("archived", "1", "ARCHIVED")]])
        await db.commit()
    try:
        yield sessions
    finally:
        if os.environ.get("P1_MYSQL_TEST_URL"):
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()


async def test_websocket_binds_each_tab_to_its_explicit_conversation(business, monkeypatch):
    from app.api.websocket import chat as websocket_chat
    from app.agent.runtime import agent_runtime
    from app.agent.memory import conversation_memory

    monkeypatch.setattr(websocket_chat, "SessionLocal", business)

    async def authenticate(_socket):
        async with business() as db:
            return await db.get(User, 1)

    async def no_memory(*args):
        return None

    async def run(**kwargs):
        cid = kwargs["conversation_id"]
        history = [item["content"] for item in kwargs["history"]]
        assert cid + " private history" in history
        other = "tab-b" if cid == "tab-a" else "tab-a"
        assert other + " private history" not in history
        return "Answer for " + cid, {}

    monkeypatch.setattr(websocket_chat, "_authenticate_socket", authenticate)
    monkeypatch.setattr(agent_runtime, "run", run)
    for method in ("get_entities", "replace_history", "append_message"):
        monkeypatch.setattr(conversation_memory, method, no_memory)
    app = FastAPI()
    app.include_router(websocket_chat.router)
    async with business() as db:
        db.add_all([ConversationMessage(conversation_id=cid, user_id="1", role="user",
                                        content=cid + " private history") for cid in ("tab-a", "tab-b")])
        # Tab B is the globally most recently selected conversation.
        await db.execute(update(ConversationSession).where(ConversationSession.conversation_id == "tab-b")
                         .values(updated_at=utcnow() + timedelta(seconds=10)))
        await db.commit()

    def browser_tabs():
        with TestClient(app) as client, client.websocket_connect("/chat") as tab_a, client.websocket_connect("/chat") as tab_b:
            assert tab_a.receive_json()["type"] == "connection"
            assert tab_b.receive_json()["type"] == "connection"
            for tab, cid in ((tab_a, "tab-a"), (tab_b, "tab-b")):
                tab.send_json({"type": "message", "conversationId": cid, "question": "Which conversation?"})
                while True:
                    event = tab.receive_json()
                    assert event.get("code", 0) < 400, event
                    if event.get("type") == "completion":
                        assert event["conversationId"] == cid
                        assert event["content"] == "Answer for " + cid
                        break
            for cid in ("other", "missing", "archived"):
                tab_a.send_json({"type": "message", "conversationId": cid, "question": "forbidden"})
                assert tab_a.receive_json()["code"] == 404
            tab_a.send_json({"type": "message", "question": "missing target"})
            assert tab_a.receive_json()["code"] == 422

    await asyncio.to_thread(browser_tabs)
    async with business() as db:
        rows = (await db.scalars(select(ConversationMessage).where(ConversationMessage.generation_id.is_not(None))
                                 .order_by(ConversationMessage.id))).all()
        assert [(row.conversation_id, row.role) for row in rows] == [
            ("tab-a", "user"), ("tab-a", "assistant"), ("tab-b", "user"), ("tab-b", "assistant")]


async def test_second_replica_restart_preserves_live_generation_and_recovers_expired_once(business):
    async with business() as db:
        for gid, age in (("live", 0), ("expired", 180)):
            db.add(GenerationState(generation_id=gid, conversation_id="tab-a", user_id="1",
                                   question="test", status="STREAMING", updated_at=utcnow() - timedelta(seconds=age)))
        await db.commit()
        for gid in ("live", "expired"):
            await usage_service.reserve_llm(db, 1, gid, 100, "test")
    replica_b = GenerationRuntime()
    replica_c = GenerationRuntime()
    recovered = await asyncio.gather(replica_b.recover_orphaned_states(), replica_c.recover_orphaned_states())
    assert sum(recovered) == 1
    assert await replica_b.recover_orphaned_states() == 0
    async with business() as db:
        assert (await db.get(GenerationState, "live")).status == "STREAMING"
        assert (await db.get(LLMTokenReservation, "live")).status == "RESERVED"
        assert (await db.get(GenerationState, "expired")).status == "INTERRUPTED"
        assert (await db.get(User, 1)).llm_token_balance == 99900
        assert await usage_service.settle_llm(db, "live", 40) == 40
        assert (await db.get(User, 1)).llm_token_balance == 99960
        assert len((await db.scalars(select(UserTokenRecord).where(UserTokenRecord.remark == "released_reservation:expired"))).all()) == 1


@pytest.mark.parametrize("terminal", ["CANCELLED", "INTERRUPTED"])
async def test_late_completion_cannot_overwrite_remote_stop_or_recovery(business, monkeypatch, terminal):
    from app.agent.runtime import agent_runtime
    from app.agent.memory import conversation_memory

    async def no_memory(*args):
        return None

    for method in ("get_entities", "replace_history", "append_message"):
        monkeypatch.setattr(conversation_memory, method, no_memory)

    async def run(**kwargs):
        gid = kwargs["generation_id"]
        async with business() as remote:
            if terminal == "CANCELLED":
                await remote.execute(update(GenerationState).where(GenerationState.generation_id == gid)
                                     .values(status="CANCELLED"))
                await usage_service.release_llm(remote, gid, commit=False)
                await remote.commit()
            else:
                await remote.execute(update(GenerationState).where(GenerationState.generation_id == gid)
                                     .values(updated_at=utcnow() - timedelta(seconds=180)))
                await remote.commit()
        if terminal == "INTERRUPTED":
            assert await GenerationRuntime().recover_orphaned_states() == 1
        return "Late answer", {}

    monkeypatch.setattr(agent_runtime, "run", run)
    events = []

    async def send(event):
        events.append(event)

    async with business() as db:
        user = await db.get(User, 1)
        with pytest.raises(asyncio.CancelledError):
            await stream_chat(db, user, "Question", send, generation_id="late", conversation_id="tab-a")
    async with business() as db:
        assert (await db.get(GenerationState, "late")).status == terminal
        assert (await db.get(LLMTokenReservation, "late")).status == "RELEASED"
        assert (await db.get(User, 1)).llm_token_balance == 100000
        assert not (await db.scalars(select(ConversationMessage).where(ConversationMessage.role == "assistant"))).all()
        assert not (await db.scalars(select(UserTokenRecord).where(UserTokenRecord.change_type == "CONSUME"))).all()
    assert not any(event.get("type") == "completion" for event in events)


async def test_concurrent_reservation_settle_and_release_are_exactly_once(business):
    async with business() as db:
        await usage_service.reserve_llm(db, 1, "race", 100, "test")

    async def settle():
        async with business() as db:
            # Simulate a cached reservation loaded before the competing transaction.
            await db.get(LLMTokenReservation, "race")
            return await usage_service.settle_llm(db, "race", 40)

    async def release():
        async with business() as db:
            await db.get(LLMTokenReservation, "race")
            return await usage_service.release_llm(db, "race")

    await asyncio.gather(settle(), release(), release(), settle())
    async with business() as db:
        reservation = await db.get(LLMTokenReservation, "race")
        assert (await db.get(User, 1)).llm_token_balance == (99960 if reservation.status == "SETTLED" else 100000)
        rows = (await db.scalars(select(UserTokenRecord).where(UserTokenRecord.change_type != "RESERVE"))).all()
        assert len(rows) == (2 if reservation.status == "SETTLED" else 1)


async def test_heartbeat_renews_long_running_generation_across_replica_start(business, monkeypatch):
    monkeypatch.setattr("app.agent.generation.HEARTBEAT_INTERVAL_SECONDS", 0.01)
    async with business() as db:
        db.add(GenerationState(generation_id="long", conversation_id="tab-a", user_id="1", question="test",
                               status="STREAMING", updated_at=utcnow() - timedelta(seconds=180)))
        await db.commit()
    owner = GenerationRuntime()
    heartbeat = asyncio.create_task(owner.heartbeat("long"))
    try:
        async with asyncio.timeout(5):
            while True:
                async with business() as db:
                    generation = await db.get(GenerationState, "long")
                    if generation.updated_at > utcnow() - timedelta(seconds=1):
                        break
                await asyncio.sleep(0.01)
        assert await GenerationRuntime().recover_orphaned_states() == 0
        async with business() as db:
            await db.execute(update(GenerationState).where(GenerationState.generation_id == "long").values(status="COMPLETED"))
            await db.commit()
        await asyncio.wait_for(heartbeat, timeout=5)
    finally:
        heartbeat.cancel()
        await asyncio.gather(heartbeat, return_exceptions=True)


async def test_stopped_generation_cannot_create_a_new_reservation(business):
    async with business() as db:
        db.add(GenerationState(generation_id="stopped", conversation_id="tab-a", user_id="1",
                               question="test", status="CANCELLED"))
        await db.commit()
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as error:
            await usage_service.reserve_llm(db, 1, "stopped", 100, "test")
        assert error.value.status_code == 409
        assert not await db.get(LLMTokenReservation, "stopped")
        assert (await db.get(User, 1)).llm_token_balance == 100000
