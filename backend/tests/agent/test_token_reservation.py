import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.accounting.usage import usage_service
from app.agent.generation import GenerationRuntime
from app.db.models import Base, GenerationState, LLMTokenReservation, User, UserTokenRecord


@pytest.mark.asyncio
async def test_llm_reservation_settles_unused_budget_and_is_idempotent():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as db:
            db.add(User(id=101, username="reservation-user", password="x", llm_token_balance=1000))
            await db.commit()
            assert await usage_service.reserve_llm(db, 101, "generation-reserve-1", 100, "test") == 100
            assert await usage_service.settle_llm(db, "generation-reserve-1", 40, "test") == 40
            user = await db.get(User, 101)
            assert user is not None and user.llm_token_balance == 960
            records = list((await db.scalars(select(UserTokenRecord))).all())
            assert sum(int(row.amount or 0) for row in records if row.change_type == "CONSUME") == -40
            assert await usage_service.settle_llm(db, "generation-reserve-1", 90, "test") == 40
            reservation = await db.get(LLMTokenReservation, "generation-reserve-1")
            assert reservation is not None and reservation.status == "SETTLED"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_llm_reservation_is_returned_on_failure():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as db:
            db.add(User(id=102, username="release-user", password="x", llm_token_balance=1000))
            await db.commit()
            await usage_service.reserve_llm(db, 102, "generation-release-1", 100, "test")
            assert await usage_service.release_llm(db, "generation-release-1", "test_failure") == 100
            user = await db.get(User, 102)
            assert user is not None and user.llm_token_balance == 1000
            reservation = await db.get(LLMTokenReservation, "generation-release-1")
            assert reservation is not None and reservation.status == "RELEASED"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_llm_settlement_charges_provider_overage_instead_of_silently_dropping_it():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as db:
            db.add(User(id=103, username="overage-user", password="x", llm_token_balance=1000))
            await db.commit()
            await usage_service.reserve_llm(db, 103, "generation-overage-1", 100, "test")
            assert await usage_service.settle_llm(db, "generation-overage-1", 120, "test") == 120
            user = await db.get(User, 103)
            assert user is not None and user.llm_token_balance == 880
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_generation_transaction_can_roll_back_uncommitted_settlement():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as db:
            db.add(User(id=104, username="rollback-user", password="x", llm_token_balance=1000))
            await db.commit()
            await usage_service.reserve_llm(db, 104, "rollback-generation", 100, "test")
            await usage_service.settle_llm(db, "rollback-generation", 40, commit=False)
            await db.flush()
            await db.rollback()
        async with sessions() as db:
            reservation = await db.get(LLMTokenReservation, "rollback-generation")
            assert reservation.status == "RESERVED" and reservation.settled_tokens == 0
            assert await usage_service.release_llm(db, "rollback-generation") == 100
            assert (await db.get(User, 104)).llm_token_balance == 1000
            assert not (await db.scalars(select(UserTokenRecord).where(UserTokenRecord.change_type == "CONSUME"))).all()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_restart_releases_legacy_stranded_reservation_once(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr("app.db.session.SessionLocal", sessions)
    gid = "legacy-interrupted-generation"
    try:
        async with sessions() as db:
            db.add(User(id=105, username="interrupted-user", password="x", llm_token_balance=1000))
            db.add(GenerationState(generation_id=gid, conversation_id="conversation", user_id="105",
                                   question="test", status="STREAMING"))
            await db.commit()
            await usage_service.reserve_llm(db, 105, gid, 100, "test")
            generation = await db.get(GenerationState, gid)
            generation.status = "INTERRUPTED"
            await db.commit()
        runtime = GenerationRuntime()
        for _ in range(2):
            assert await runtime.recover_orphaned_states() == 0
        async with sessions() as db:
            assert (await db.get(User, 105)).llm_token_balance == 1000
            assert (await db.get(LLMTokenReservation, gid)).status == "RELEASED"
            records = (await db.scalars(select(UserTokenRecord).where(UserTokenRecord.change_type == "REFUND"))).all()
            assert len(records) == 1 and records[0].amount == 100
    finally:
        await engine.dispose()
