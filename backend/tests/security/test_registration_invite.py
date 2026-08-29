from __future__ import annotations

import pytest

aiosqlite = pytest.importorskip("aiosqlite")

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.users import UserRequest, register
from app.db.models import Base, InviteCode


@pytest.mark.asyncio
async def test_registration_consumes_invite_code_once():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with Session() as db:
            db.add(InviteCode(code="ONLY-ONCE", max_uses=1))
            await db.commit()

            await register(UserRequest(username="alice", password="hello123", inviteCode="ONLY-ONCE"), db)
            invite = await db.scalar(select(InviteCode).where(InviteCode.code == "ONLY-ONCE"))
            assert invite is not None and invite.used_count == 1

            with pytest.raises(HTTPException) as exc:
                await register(UserRequest(username="bob", password="hello123", inviteCode="ONLY-ONCE"), db)
            assert exc.value.detail == "INVITE_CODE_EXHAUSTED"
    finally:
        await engine.dispose()
