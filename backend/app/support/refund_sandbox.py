"""Adapter for the isolated, synthetic payment service."""
from decimal import Decimal, InvalidOperation

import httpx
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RefundApprovalPreview, RefundSandboxIntent


class SandboxReceipt(BaseModel):
    model_config = ConfigDict(strict=True)
    refundId: str = Field(min_length=1, max_length=64)
    paymentId: str
    requestId: str
    amountMinor: int
    currency: str
    status: str


def minor_units(amount: float) -> int:
    try:
        minor = Decimal(str(amount)) * 100
        if minor.is_finite() and 0 < minor <= 10**12 and minor == minor.to_integral_value():
            return int(minor)
    except InvalidOperation:
        pass
    raise ValueError("Invalid synthetic invoice amount")


async def reconcile(
    db: AsyncSession, row: RefundApprovalPreview, sandbox_url: str, *, allow_submit: bool,
) -> tuple[str, SandboxReceipt | None]:
    intent = await db.get(RefundSandboxIntent, row.request_id)
    if not intent or not sandbox_url or row.decision != "approve":
        return "APPROVED_PREVIEW" if row.decision == "approve" else "REJECTED", None
    expected = {"paymentId": intent.payment_id, "requestId": intent.request_id,
                "amountMinor": intent.amount_minor, "currency": "CNY"}
    request_id = intent.request_id
    refund_id = intent.refund_id
    if intent.rejection:
        return "SANDBOX_REJECTED", None
    await db.commit()
    headers = {"Idempotency-Key": request_id}
    path = f"refunds/{request_id}"
    rejected = False
    try:
        async with httpx.AsyncClient(base_url=sandbox_url.rstrip("/") + "/", timeout=3, trust_env=False) as client:
            lookup = await client.get(path)
            if lookup.status_code == 404 and allow_submit and not refund_id:
                try:
                    submitted = await client.post("refunds", json=expected, headers=headers)
                    rejected = submitted.status_code in {404, 409, 422}
                except httpx.RequestError:
                    pass
                # Confirm via the provider's query API even if submit times out.
                lookup = await client.get(path)
            if lookup.status_code == 404 and rejected:
                await db.execute(
                    update(RefundSandboxIntent)
                    .where(RefundSandboxIntent.request_id == request_id, RefundSandboxIntent.refund_id.is_(None))
                    .values(rejection="provider_rejected")
                )
                await db.commit()
                return "SANDBOX_REJECTED", None
            lookup.raise_for_status()
            receipt = SandboxReceipt.model_validate(lookup.json())
    except (httpx.HTTPError, ValueError):
        if refund_id:
            return "SANDBOX_REFUNDED", SandboxReceipt(**expected, refundId=refund_id, status="SUCCEEDED")
        return "REFUND_RECONCILING", None
    if (
        any(getattr(receipt, key) != value for key, value in expected.items())
        or receipt.status != "SUCCEEDED"
        or (refund_id and refund_id != receipt.refundId)
    ):
        return "REFUND_RECONCILING", None
    result = await db.execute(
        update(RefundSandboxIntent)
        .where(RefundSandboxIntent.request_id == request_id,
               RefundSandboxIntent.refund_id.is_(None) | (RefundSandboxIntent.refund_id == receipt.refundId))
        .values(refund_id=receipt.refundId)
    )
    if not result.rowcount:
        await db.rollback()
        return "REFUND_RECONCILING", None
    await db.commit()
    return "SANDBOX_REFUNDED", receipt
