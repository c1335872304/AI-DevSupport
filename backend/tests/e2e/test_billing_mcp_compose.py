from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete

from app.db.models import SupportInvoice, SupportPlan, SupportSubscription, SupportUsageRecord
from app.db.session import SessionLocal, engine
from app.tools.mcp.client import MCPRemoteClient, RemoteServerConfig


pytestmark = pytest.mark.skipif(
    os.getenv("BILLING_MCP_COMPOSE_E2E") != "true",
    reason="requires the Compose mysql and billing-mcp services",
)


@pytest_asyncio.fixture(autouse=True)
async def _isolate_global_db_pool():
    """Avoid reusing aiomysql connections across pytest event loops."""
    await engine.dispose()
    yield
    await engine.dispose()


def _structured(result: object) -> dict:
    if not isinstance(result, dict):
        raise AssertionError(f"unexpected MCP response: {result!r}")
    payload = result.get("structuredContent", result.get("structured_content", result))
    assert isinstance(payload, dict)
    return payload


async def _catalog(client: MCPRemoteClient) -> list[object]:
    """Give the independent MCP container a bounded startup window."""
    last_error: Exception | None = None
    for _attempt in range(20):
        try:
            return await client.list_tools()
        except Exception as exc:  # pragma: no cover - exercised only in Compose
            last_error = exc
            await asyncio.sleep(0.5)
    raise AssertionError("billing-mcp did not become ready") from last_error


@pytest.mark.asyncio
async def test_compose_billing_mcp_lists_and_reads_only_its_seeded_facts():
    """Exercise the real HTTP MCP boundary against the Compose MySQL service."""
    suffix = uuid4().hex
    user_id = f"compose-e2e-user-{suffix}"
    plan_id = f"compose-e2e-plan-{suffix}"
    invoice_id = f"compose-e2e-invoice-{suffix}"
    month = "2026-08"

    async with SessionLocal() as db:
        db.add(SupportPlan(
            id=plan_id,
            name="Compose E2E",
            qps_limit=12,
            monthly_quota=1200,
            base_price=19.9,
            overage_price_per_call=0.02,
        ))
        db.add(SupportSubscription(user_id=user_id, plan_id=plan_id, status="ACTIVE"))
        db.add(SupportUsageRecord(user_id=user_id, month=month, call_count=1300, overage_count=100))
        db.add(SupportInvoice(
            id=invoice_id,
            user_id=user_id,
            month=month,
            items_json='{"base": 19.9, "overage": 2.0}',
            amount=21.9,
            status="ISSUED",
        ))
        await db.commit()

    client = MCPRemoteClient(RemoteServerConfig(
        name="compose-billing",
        url=os.getenv("BILLING_MCP_COMPOSE_URL", "http://billing-mcp:8011/mcp"),
        read_only=True,
        timeout_seconds=5,
    ))
    try:
        tools = await _catalog(client)
        assert {getattr(tool, "name", None) for tool in tools} == {"get_plan", "get_usage", "get_invoice"}
        for tool in tools:
            annotations = getattr(tool, "annotations", None)
            assert getattr(annotations, "read_only_hint", getattr(annotations, "readOnlyHint", None)) is True

        plan = _structured(await client.call_tool("get_plan", {"customer_id": user_id}))
        usage = _structured(await client.call_tool("get_usage", {"customer_id": user_id, "month": month}))
        invoice = _structured(await client.call_tool("get_invoice", {"customer_id": user_id, "month": month}))

        assert plan["found"] is True and plan["planId"] == plan_id
        assert usage == {"found": True, "usage": [{"month": month, "callCount": 1300, "overageCount": 100}]}
        assert invoice["found"] is True
        assert invoice["bills"] == [{
            "invoiceId": invoice_id,
            "month": month,
            "amount": 21.9,
            "status": "ISSUED",
            "items": {"base": 19.9, "overage": 2.0},
        }]
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(SupportInvoice).where(SupportInvoice.id == invoice_id))
            await db.execute(delete(SupportUsageRecord).where(SupportUsageRecord.user_id == user_id))
            await db.execute(delete(SupportSubscription).where(SupportSubscription.user_id == user_id))
            await db.execute(delete(SupportPlan).where(SupportPlan.id == plan_id))
            await db.commit()
