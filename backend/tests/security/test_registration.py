import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.admin import router as admin_router
from app.api.v1.users import router as users_router
from app.db.models import Base
from app.db.session import get_db


@pytest.mark.asyncio
async def test_registration_and_login_without_invitation():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    app = FastAPI()
    app.include_router(users_router)
    app.include_router(admin_router)

    async def test_db():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = test_db
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            credentials = {"username": "alice", "password": "hello123"}
            assert (await client.post("/users/register", json=credentials)).status_code == 200
            assert (await client.post("/users/register", json=credentials)).status_code == 409

            login = await client.post("/users/login", json=credentials)
            assert login.status_code == 200
            token = login.json()["data"]["token"]
            identity = await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
            assert identity.json()["data"]["role"] == "USER"
            assert identity.json()["data"]["primaryOrg"] == "default"
            assert (await client.get("/admin/invite-codes")).status_code == 404
    finally:
        await engine.dispose()
