import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.accounting.usage import usage_service
from app.db.models import Base, LLMTokenReservation, User, UserTokenRecord


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
