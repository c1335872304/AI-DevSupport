from __future__ import annotations

import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import SupportInvoice, SupportPlan, SupportSubscription, SupportUsageRecord


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
