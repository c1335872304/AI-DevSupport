import asyncio
from dataclasses import replace

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.sql.dml import Update

from app.db.models import Base, GenerationState, SupportHandoff, User
from app.support.handoff import HandoffPayloadConflict, create_handoff
from app.support.handoff_contract import authorize_handoff


@pytest.fixture
async def handoff_sessions(tmp_path):
    database = (tmp_path / "handoff.db").as_posix()
    engine = create_async_engine(f"sqlite+aiosqlite:///{database}")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as db:
            db.add(GenerationState(
                generation_id="handoff-test", conversation_id="conversation-test",
                user_id="1", question="转人工", status="STREAMING",
            ))
            await db.commit()
        yield sessions
    finally:
        await engine.dispose()


async def submit(sessions, *, user_id=1, generation_id="handoff-test", summary="Customer requests human support",
                 authorized=True, mutate=None):
    arguments = {"reason": "Customer request", "summary": summary}
    authorization = authorize_handoff(str(user_id), generation_id, arguments) if authorized and generation_id else None
    if mutate:
        authorization = mutate(authorization)
    async with sessions() as db:
        return await create_handoff(
            db, User(id=user_id), generation_id=generation_id, authorization=authorization, **arguments,
        )


@pytest.mark.parametrize("user_id,generation_id", [(2, "handoff-test"), (1, None), (1, "unknown")])
async def test_handoff_requires_owned_durable_generation(handoff_sessions, user_id, generation_id):
    with pytest.raises(PermissionError):
        await submit(handoff_sessions, user_id=user_id, generation_id=generation_id)
    async with handoff_sessions() as db:
        assert await db.scalar(select(func.count()).select_from(SupportHandoff)) == 0


async def test_same_generation_concurrent_replay_and_payload_conflict(handoff_sessions):
    first, replay = await asyncio.gather(
        submit(handoff_sessions),
        submit(handoff_sessions, summary="  Customer requests human support  "),
    )
    assert first.handoff_id == replay.handoff_id
    assert first.conversation_id == "conversation-test"
    with pytest.raises(HandoffPayloadConflict):
        await submit(handoff_sessions, summary="Different customer request")
    async with handoff_sessions() as db:
        rows = (await db.scalars(select(SupportHandoff))).all()
        assert len(rows) == 1
        assert rows[0].handoff_id == first.handoff_id
        assert rows[0].summary == "Customer requests human support"


@pytest.mark.parametrize("mutation", [{"expires_at": 0}, {"user_id": "other"}, {"generation_id": "other"},
                                     {"action": "change_plan"}, {"fingerprint": "other"}])
async def test_action_authorization_is_scoped_and_expires(handoff_sessions, mutation):
    with pytest.raises(PermissionError, match="authorization"):
        await submit(handoff_sessions, mutate=lambda auth: replace(auth, **mutation))
    with pytest.raises(PermissionError, match="authorization"):
        await submit(handoff_sessions, authorized=False)
    async with handoff_sessions() as db:
        assert await db.scalar(select(func.count()).select_from(SupportHandoff)) == 0


async def test_lost_commit_acknowledgement_recovers_persisted_ticket(handoff_sessions, monkeypatch):
    session_type = handoff_sessions.class_
    original_commit = session_type.commit
    lost = False

    async def commit(session):
        nonlocal lost
        writes_ticket = any(isinstance(row, SupportHandoff) for row in session.new)
        await original_commit(session)
        if writes_ticket and not lost:
            lost = True
            raise ConnectionError("ticket committed before acknowledgement was lost")

    monkeypatch.setattr(session_type, "commit", commit)
    recovered = await submit(handoff_sessions)
    assert lost
    assert (await submit(handoff_sessions)).handoff_id == recovered.handoff_id
    async with handoff_sessions() as db:
        assert await db.scalar(select(func.count()).select_from(SupportHandoff)) == 1


@pytest.mark.parametrize("has_receipt", [False, True])
async def test_terminal_generation_can_replay_only_an_existing_receipt(handoff_sessions, has_receipt):
    first = await submit(handoff_sessions) if has_receipt else None
    async with handoff_sessions() as db:
        generation = await db.get(GenerationState, "handoff-test")
        generation.status = "CANCELLED"
        await db.commit()
    if first:
        assert (await submit(handoff_sessions)).handoff_id == first.handoff_id
    else:
        with pytest.raises(PermissionError, match="not active"):
            await submit(handoff_sessions)


async def test_cancellation_between_authorization_and_write_prevents_insert(handoff_sessions, monkeypatch):
    session_type = handoff_sessions.class_
    original_execute = session_type.execute
    checked = asyncio.Event()
    cancelled = asyncio.Event()

    async def execute(session, statement, *args, **kwargs):
        if isinstance(statement, Update) and statement.table.name == "generation_states":
            checked.set()
            await cancelled.wait()
        return await original_execute(session, statement, *args, **kwargs)

    monkeypatch.setattr(session_type, "execute", execute)
    async with asyncio.timeout(5):
        pending = asyncio.create_task(submit(handoff_sessions))
        try:
            await checked.wait()
            async with handoff_sessions() as db:
                generation = await db.get(GenerationState, "handoff-test")
                generation.status = "CANCELLED"
                await db.commit()
        finally:
            cancelled.set()
        with pytest.raises(PermissionError, match="not active"):
            await pending
    async with handoff_sessions() as db:
        assert await db.scalar(select(func.count()).select_from(SupportHandoff)) == 0
