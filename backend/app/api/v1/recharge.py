from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import current_user
from app.core.response import ok
from app.db.models import RechargeOrder, RechargePackage, User
from app.db.session import get_db

router = APIRouter(prefix="/recharge", tags=["recharge"])


class CreateOrderRequest(BaseModel):
    packageId: int | None = None
    customAmount: float | None = None


def package_dict(x: RechargePackage) -> dict:
    return {"id": x.id, "packageName": x.package_name, "packagePrice": x.package_price, "packageDesc": x.package_desc, "packageBenefit": x.package_benefit, "llmToken": x.llm_token, "embeddingToken": x.embedding_token, "sortOrder": x.sort_order, "enabled": x.enabled}


def order_dict(x: RechargeOrder) -> dict:
    return {"id": x.id, "tradeNo": x.trade_no, "userId": x.user_id, "packageId": x.package_id, "amount": x.amount, "llmToken": x.llm_token, "embeddingToken": x.embedding_token, "status": x.status, "description": x.description, "createdAt": x.created_at.isoformat(), "updatedAt": x.updated_at.isoformat()}


@router.get("/packages")
async def packages(db: AsyncSession = Depends(get_db)):
    rows = list((await db.scalars(select(RechargePackage).where(RechargePackage.enabled.is_(True), RechargePackage.deleted.is_(False)).order_by(RechargePackage.sort_order))).all())
    return ok([package_dict(x) for x in rows])


@router.post("/create-order")
async def create_order(payload: CreateOrderRequest, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if payload.packageId:
        package = await db.get(RechargePackage, payload.packageId)
        if not package or not package.enabled or package.deleted:
            raise HTTPException(status_code=404, detail="Package not found")
        amount, llm, emb, package_id = package.package_price, package.llm_token, package.embedding_token, package.id
    elif payload.customAmount and payload.customAmount > 0:
        amount = int(round(payload.customAmount * 100))
        llm, emb, package_id = amount * 2500, amount * 1000, 0
    else:
        raise HTTPException(status_code=400, detail="packageId or customAmount is required")
    order = RechargeOrder(trade_no="PY" + uuid.uuid4().hex[:24].upper(), user_id=str(user.id), package_id=package_id, amount=amount, llm_token=llm, embedding_token=emb, status="NOT_PAY", description="Python edition demo order")
    db.add(order)
    await db.commit()
    await db.refresh(order)
    # Payment integration intentionally not auto-enabled. Return an order compatible with frontend.
    return ok({**order_dict(order), "codeUrl": None, "payUrl": None})


@router.get("/orders")
async def orders(status: str | None = None, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(RechargeOrder).where(RechargeOrder.user_id == str(user.id)).order_by(RechargeOrder.id.desc())
    if status:
        stmt = stmt.where(RechargeOrder.status == status)
    return ok([order_dict(x) for x in (await db.scalars(stmt)).all()])


@router.get("/orders/{trade_no}")
async def order_detail(trade_no: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    item = await db.scalar(select(RechargeOrder).where(RechargeOrder.trade_no == trade_no, RechargeOrder.user_id == str(user.id)))
    if not item:
        raise HTTPException(status_code=404, detail="Order not found")
    return ok(order_dict(item))
