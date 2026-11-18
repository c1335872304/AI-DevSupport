from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import SupportInvoice, SupportPlan, SupportSubscription, SupportUsageRecord


BILLING_TOOL_ALIASES = {
    "mcp__billing__get_plan": "query_plan",
    "mcp__billing__get_usage": "query_usage",
    "mcp__billing__get_invoice": "query_bill",
}

MONTH_RESULT_FIELDS = {
    "query_usage": "usage",
    "query_bill": "bills",
    "mcp__billing__get_usage": "usage",
    "mcp__billing__get_invoice": "bills",
}
_BILLING_TIMEZONE = timezone(timedelta(hours=8))


def requested_billing_month(question: str, *, now: datetime | None = None) -> str | None:
    """Resolve a single explicit or current-month request in the Demo billing timezone."""
    months = set(re.findall(r"\b20\d{2}-(?:0[1-9]|1[0-2])\b", question))
    current = re.search(r"本月|当月|这个月|\bthis month\b", question, re.IGNORECASE)
    other_relative = re.search(r"上月|上个月|下月|下个月|\b(?:last|next) month\b", question, re.IGNORECASE)
    if len(months) > 1 or (current and (months or other_relative)):
        return None
    if months:
        return months.pop()
    if current:
        return (now or datetime.now(timezone.utc)).astimezone(_BILLING_TIMEZONE).strftime("%Y-%m")
    return None


def scope_billing_rows(tool_name: str, month: str | None, data: dict) -> dict | None:
    field = MONTH_RESULT_FIELDS.get(tool_name)
    if not field or not month:
        return data
    rows = data.get(field)
    if isinstance(rows, list) and rows:
        if data.get("found") is not True:
            return None
        matching = [row for row in rows if isinstance(row, dict) and row.get("month") == month]
        return {**data, field: matching} if matching else None
    return data if data.get("found") is False else None


async def query_plan(db: AsyncSession, user_id: str) -> dict:
    sub = await db.get(SupportSubscription, user_id)
    if not sub:
        return {"found": False, "reason": "subscription not found"}
    plan = await db.get(SupportPlan, sub.plan_id)
    if not plan:
        return {"found": False, "reason": "plan not found"}
    return {"found": True, "subscriptionStatus": sub.status, "planId": plan.id, "planName": plan.name, "qpsLimit": plan.qps_limit, "monthlyQuota": plan.monthly_quota, "basePrice": plan.base_price, "overagePricePerCall": plan.overage_price_per_call}


async def query_usage(db: AsyncSession, user_id: str, month: str | None = None) -> dict:
    stmt=select(SupportUsageRecord).where(SupportUsageRecord.user_id == user_id)
    if month: stmt=stmt.where(SupportUsageRecord.month == month)
    rows=list((await db.scalars(stmt.order_by(SupportUsageRecord.month))).all())
    return {"found": bool(rows), "usage": [{"month":r.month,"callCount":r.call_count,"overageCount":r.overage_count} for r in rows]}


async def query_bill(db: AsyncSession, user_id: str, month: str | None = None) -> dict:
    stmt=select(SupportInvoice).where(SupportInvoice.user_id == user_id)
    if month: stmt=stmt.where(SupportInvoice.month == month)
    rows=list((await db.scalars(stmt.order_by(SupportInvoice.month))).all())
    bills=[]
    for r in rows:
        try: items=json.loads(r.items_json or '{}')
        except Exception: items={}
        bills.append({"invoiceId":r.id,"month":r.month,"amount":r.amount,"status":r.status,"items":items})
    return {"found": bool(rows), "bills": bills}
