"""Run the refund demo through two isolated HTTP servers and print the receipts."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import secrets
import socket
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
import uvicorn
from fastapi import FastAPI

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def show(step: str, body: dict) -> None:
    print(json.dumps({"step": step, **body}, ensure_ascii=False), flush=True)


async def run(root: Path, listeners: tuple[socket.socket, socket.socket], *, serve: bool) -> None:
    api_socket, provider_socket = listeners
    api_url, provider_url = (f"http://127.0.0.1:{item.getsockname()[1]}" for item in listeners)
    business_db = root / "billing.sqlite"
    provider_db = root / "provider.sqlite"
    os.environ.update(
        DATABASE_URL=f"sqlite+aiosqlite:///{business_db.as_posix()}",
        JWT_SECRET=secrets.token_hex(32),
        REDIS_ENABLED="false",
        LLM_API_KEY="",
        EMBEDDING_API_KEY="",
        LANGFUSE_ENABLED="false",
        BILLING_MCP_ENABLED="false",
        SEARCH_BACKEND="database",
        REFUND_PREVIEW_ENABLED="true",
        REFUND_CHECKPOINT_PATH=str(root / "checkpoints.sqlite"),
        REFUND_SANDBOX_URL=provider_url + "/sandbox",
        REFUND_SIM_DB=str(provider_db),
        REFUND_SIM_DROP_FIRST_RECEIPT="1",
    )
    from app.api.router import api_router
    from app.core.security import hash_password
    from app.api.websocket.chat import router as websocket_router
    from app.db.models import Base, ConversationSession, SupportHandoff, SupportInvoice, User
    from app.db.session import SessionLocal, engine
    from app.support.refund_sandbox_server import app as provider_app

    api = FastAPI()
    api.include_router(api_router, prefix="/api/v1")
    api.include_router(websocket_router)

    @api.get("/health")
    async def health():
        return {"status": "ok"}
    password = os.environ.get("REFUND_DEMO_PASSWORD") if serve else secrets.token_urlsafe(18)
    if not password:
        raise ValueError("Set REFUND_DEMO_PASSWORD for browser mode")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        password_hash = hash_password(password)
        owner = User(username="refund-customer", password=password_hash, role="USER")
        db.add_all([owner, User(username="refund-reviewer", password=password_hash, role="ADMIN")])
        await db.flush()
        db.add(ConversationSession(conversation_id="demo-support-chat", user_id=str(owner.id), title="客服演示"))
        db.add(SupportHandoff(handoff_id="demo-support-ticket", user_id=str(owner.id),
                             conversation_id="demo-support-chat", reason="合成测试", summary="待确认关闭的演示工单"))
        db.add(SupportInvoice(id="sandbox-paid-1", user_id=str(owner.id), month="2026-11",
                              status="PAID", amount=15))
        await db.commit()

    servers = [uvicorn.Server(uvicorn.Config(app, log_level="error")) for app in (api, provider_app)]
    tasks = [asyncio.create_task(server.serve(sockets=[listener]))
             for server, listener in zip(servers, (api_socket, provider_socket), strict=True)]
    try:
        async with asyncio.timeout(12):
            while not all(server.started for server in servers):
                for task in tasks:
                    if task.done():
                        await task
                        raise RuntimeError("A demo server exited during startup")
                await asyncio.sleep(.02)
        if serve:
            show("ready", {"api": api_url, "customer": "refund-customer", "reviewer": "refund-reviewer"})
            await asyncio.gather(*tasks)
            return
        async with httpx.AsyncClient(base_url=api_url + "/api/v1/", timeout=10, trust_env=False) as client:
            customer = await login(client, "refund-customer", password)
            reviewer = await login(client, "refund-reviewer", password)
            pending = unwrap(await client.post("support/refund-requests", headers=customer, json={
                "invoiceId": "sandbox-paid-1", "requestKey": "demo-once", "reason": "合成退款演示",
                "conversationId": "demo-support-chat",
            }))
            request_id = pending["requestId"]
            assert pending["status"] == "PENDING_APPROVAL"
            show("等待人工审批", pending)
            provider_path = provider_url + f"/sandbox/refunds/{request_id}"
            assert (await client.get(provider_path)).status_code == 404
            path = f"support/admin/refund-requests/{request_id}/decision"
            decision = {"decision": "approve", "note": "批准合成支付演示"}
            approved = unwrap(await client.post(path, headers=reviewer, json=decision))
            assert approved["status"] == "SANDBOX_REFUNDED", approved
            show("人工批准后完成沙箱退款", approved)
            repeated = unwrap(await client.post(path, headers=reviewer, json=decision))
            provider = (await client.get(provider_path)).raise_for_status().json()
            customer_view = unwrap(await client.get(f"support/refund-requests/{request_id}", headers=customer))
            assert provider == repeated["receipt"] == approved["receipt"] == customer_view["receipt"]
            saved = unwrap(await client.get("support/refund-requests", headers=customer,
                                            params={"conversationId": "demo-support-chat"}))
            assert saved[0]["receipt"]["refundId"] == provider["refundId"]
            with closing(sqlite3.connect(provider_db)) as db:
                count = db.execute("SELECT COUNT(*) FROM refunds").fetchone()[0]
            assert count == 1
            show("沙箱独立查询与重复审批", {"refundId": provider["refundId"], "providerRefundCount": count,
                                            "initialSubmitReceiptLost": True})
            submitted = unwrap(await client.post("support/refund-requests", headers=customer, json={
                "handoffId": "demo-support-ticket", "requestKey": "close-once", "reason": "客服已经解决问题",
                "conversationId": "demo-support-chat",
            }))
            path = f"support/admin/refund-requests/{submitted['requestId']}/decision"
            assert submitted["status"] == "PENDING_APPROVAL"
            assert unwrap((await client.get("support/handoffs/demo-support-ticket", headers=customer)))["status"] == "OPEN"
            closed = unwrap(await client.post(path, headers=reviewer, json=decision))
            assert closed["status"] == "TICKET_CLOSED"
            assert unwrap(await client.post(path, headers=reviewer, json=decision)) == closed
            ticket = unwrap(await client.get("support/handoffs/demo-support-ticket", headers=customer))
            assert ticket["status"] == "CLOSED"
            show("批准关闭原工单", {"handoffId": ticket["handoffId"], "status": ticket["status"]})
    finally:
        for server in servers:
            server.should_exit = True
        await asyncio.gather(*tasks, return_exceptions=True)
        await engine.dispose()


def unwrap(response: httpx.Response) -> dict:
    return response.raise_for_status().json()["data"]


async def login(client: httpx.AsyncClient, account: str, password: str) -> dict:
    token = unwrap(await client.post("users/login", json={"username": account, "password": password}))["token"]
    return {"Authorization": f"Bearer {token}"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", type=int, metavar="PORT", help="Keep an isolated API running for browser demos")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="refund-sandbox-") as directory, socket.socket() as api, socket.socket() as provider:
        api.bind(("127.0.0.1", args.serve or 0))
        provider.bind(("127.0.0.1", 0))
        asyncio.run(run(Path(directory), (api, provider), serve=args.serve is not None))
