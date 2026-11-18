import asyncio
import socket
import sqlite3
from contextlib import closing

import httpx
import pytest
import uvicorn
from fastapi import FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.api.v1.refund_preview as refund_api
from app.api.v1.refund_preview import router
from app.core.config import get_settings
from app.core.deps import admin_user, current_user
from app.db.models import Base, RefundApprovalPreview, SupportInvoice, User
from app.db.session import get_db
from app.support.refund_sandbox_server import app as sandbox_app


def api(sessions):
    app = FastAPI()
    app.include_router(router)

    async def database():
        async with sessions() as db:
            yield db

    def approver():
        return User(id=10, role="ADMIN")

    app.dependency_overrides.update({get_db: database, current_user: lambda: User(id=1), admin_user: approver})
    return app


async def test_refund_approval_resumes_saved_checkpoint_after_app_recreation(tmp_path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "refund_preview_enabled", True)
    checkpoint = tmp_path / "graph.sqlite"
    monkeypatch.setattr(settings, "refund_checkpoint_path", checkpoint)
    url = f"sqlite+aiosqlite:///{(tmp_path / 'business.sqlite').as_posix()}"
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as db:
            db.add(SupportInvoice(id="paid-1", user_id="1", month="2026-11", status="PAID", amount=15))
            await db.commit()
        app = api(sessions)
        request = {"invoiceId": "paid-1", "requestKey": "first", "reason": "Test approval"}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            created = (await client.post("/support/refund-requests", json=request)).json()["data"]
            assert created["status"] == "PENDING_APPROVAL"
            assert checkpoint.is_file()
            assert (await client.post("/support/refund-requests", json=request)).json()["data"] == created
            assert (await client.post("/support/refund-requests", json={**request, "reason": "Changed"})).status_code == 409
    finally:
        await engine.dispose()

    engine = create_async_engine(url)
    try:
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        app = api(sessions)
        owner_path = f"/support/refund-requests/{created['requestId']}"
        decision_path = f"/support/admin/refund-requests/{created['requestId']}/decision"
        decision = {"decision": "approve", "note": "Approved for technical preview"}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            original_admin = app.dependency_overrides[admin_user]

            def denied():
                raise HTTPException(403)

            app.dependency_overrides[admin_user] = denied
            assert (await client.post(decision_path, json=decision)).status_code == 403
            app.dependency_overrides[admin_user] = original_admin
            original_advance = refund_api.advance
            advances = 0

            async def interrupt_delivery(*args):
                nonlocal advances
                advances += 1
                if advances == 2:
                    raise HTTPException(503, "Simulated interruption after durable decision")
                return await original_advance(*args)

            monkeypatch.setattr(refund_api, "advance", interrupt_delivery)
            assert (await client.post(decision_path, json=decision)).status_code == 503
            review = (await client.get(decision_path.removesuffix("/decision"))).json()["data"]
            assert review["decision"] == "approve" and review["decisionId"]
            monkeypatch.setattr(refund_api, "advance", original_advance)

            responses = await asyncio.gather(*(client.post(decision_path, json=decision) for _ in range(2)))
            assert all(response.json()["data"]["status"] == "APPROVED_PREVIEW" for response in responses)
            assert (await client.post(decision_path, json={**decision, "decision": "reject"})).status_code == 409
            assert (await client.get(owner_path)).json()["data"]["status"] == "APPROVED_PREVIEW"
            app.dependency_overrides[current_user] = lambda: User(id=2)
            assert (await client.get(owner_path)).status_code == 404
            assert (await client.post("/support/refund-requests", json=request)).status_code == 404
        async with sessions() as db:
            row = (await db.scalars(select(RefundApprovalPreview))).one()
            assert row.decided_by == "10" and row.decision_id
            assert (await db.get(SupportInvoice, "paid-1")).amount == 15
    finally:
        await engine.dispose()


@pytest.mark.parametrize("drop_receipt", [False, True])
async def test_approved_refund_queries_same_sandbox_receipt(tmp_path, monkeypatch, drop_receipt):
    settings = get_settings()
    monkeypatch.setattr(settings, "refund_preview_enabled", True)
    monkeypatch.setattr(settings, "refund_checkpoint_path", tmp_path / "checkpoint.sqlite")
    sandbox_db = tmp_path / "provider.sqlite"
    monkeypatch.setenv("REFUND_SIM_DB", str(sandbox_db))
    monkeypatch.setenv("REFUND_SIM_DROP_FIRST_RECEIPT", str(int(drop_receipt)))
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'billing.sqlite').as_posix()}")
    server = uvicorn.Server(uvicorn.Config(sandbox_app, log_level="error"))
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        endpoint = f"http://127.0.0.1:{listener.getsockname()[1]}/sandbox"
        monkeypatch.setattr(settings, "refund_sandbox_url", endpoint)
        running = asyncio.create_task(server.serve(sockets=[listener]))
        try:
            async with asyncio.timeout(8):
                while not server.started:
                    if running.done():
                        await running
                        raise RuntimeError("Sandbox failed to start")
                    await asyncio.sleep(0.01)
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            async with sessions() as db:
                db.add(SupportInvoice(id="sandbox-paid-1", user_id="1", month="2026-11", status="PAID", amount=15))
                await db.commit()
            app = api(sessions)
            async with (
                httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://app") as business,
                httpx.AsyncClient(base_url=endpoint + "/", trust_env=False) as provider,
            ):
                request_path = "/support/refund-requests"
                submitted = await business.post(request_path, json={
                    "invoiceId": "sandbox-paid-1", "requestKey": "test", "reason": "Demo",
                })
                pending = submitted.json()["data"]
                assert pending["status"] == "PENDING_APPROVAL"
                request_id = pending["requestId"]
                assert (await provider.get(f"refunds/{request_id}")).status_code == 404
                endpoint_path = f"/support/admin/refund-requests/{request_id}/decision"
                decision = {"decision": "approve", "note": "Approved for sandbox"}
                responses = await asyncio.gather(*(business.post(endpoint_path, json=decision) for _ in range(2)))
                results = [response.json()["data"] for response in responses]
                assert results[0] == results[1]
                assert results[0]["status"] == "SANDBOX_REFUNDED"
                queried = (await provider.get(f"refunds/{request_id}")).json()
                assert results[0]["receipt"] == queried
                assert (await business.get(f"{request_path}/{request_id}")).json()["data"] == results[0]
                assert queried["refundId"].startswith("rf_demo_") and queried["amountMinor"] == 1500
                denied = await business.post(request_path, json={
                    "invoiceId": "sandbox-paid-1", "requestKey": "reject-it", "reason": "Demo denial",
                })
                rejected_id = denied.json()["data"]["requestId"]
                rejected = await business.post(f"/support/admin/refund-requests/{rejected_id}/decision",
                                               json={"decision": "reject", "note": "Denied"})
                assert rejected.json()["data"]["status"] == "REJECTED"
                assert (await provider.get(f"refunds/{rejected_id}")).status_code == 404
                duplicate = await business.post(request_path, json={
                    "invoiceId": "sandbox-paid-1", "requestKey": "different-request", "reason": "Duplicate",
                })
                duplicate_id = duplicate.json()["data"]["requestId"]
                rejected = await business.post(f"/support/admin/refund-requests/{duplicate_id}/decision",
                                               json=decision)
                assert rejected.json()["data"]["status"] == "SANDBOX_REJECTED"
                assert (await business.get(f"{request_path}/{duplicate_id}")).json()["data"]["status"] == "SANDBOX_REJECTED"
            with closing(sqlite3.connect(sandbox_db)) as provider_db:
                assert provider_db.execute("SELECT COUNT(*) FROM refunds").fetchone() == (1,)
        finally:
            server.should_exit = True
            await running
            await engine.dispose()
