"""Standalone payment provider simulator. Only fixed synthetic payments exist."""
import os
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import aiosqlite
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

PAYMENTS = {"sandbox-paid-1": 1500}


def database() -> Path:
    return Path(os.environ.get("REFUND_SIM_DB", "data/refund-simulator.sqlite"))


@asynccontextmanager
async def lifespan(_app):
    path = database()
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(path) as db:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS refunds (requestId TEXT PRIMARY KEY, paymentId TEXT UNIQUE NOT NULL, "
            "amountMinor INTEGER NOT NULL, currency TEXT NOT NULL, refundId TEXT UNIQUE NOT NULL)"
        )
        await db.commit()
    yield


app = FastAPI(lifespan=lifespan, title="Synthetic payment sandbox")


class Submission(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    requestId: str = Field(min_length=1, max_length=64)
    paymentId: str
    amountMinor: int = Field(gt=0)
    currency: str


def receipt(row) -> dict:
    return {**dict(row), "status": "SUCCEEDED"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/sandbox/refunds")
async def create(body: Submission, idempotency_key: str = Header()):
    if idempotency_key != body.requestId:
        raise HTTPException(422, "Idempotency key mismatch")
    if PAYMENTS.get(body.paymentId) != body.amountMinor or body.currency != "CNY":
        raise HTTPException(422, "Unknown synthetic payment or amount mismatch")
    async with aiosqlite.connect(database()) as db:
        db.row_factory = aiosqlite.Row
        inserted = await db.execute(
            "INSERT INTO refunds VALUES (?,?,?,?,?) ON CONFLICT DO NOTHING",
            (body.requestId, body.paymentId, body.amountMinor, body.currency, "rf_demo_" + uuid4().hex),
        )
        async with db.execute("SELECT * FROM refunds WHERE requestId = ?", (body.requestId,)) as query:
            row = await query.fetchone()
        if row is None or any(row[key] != value for key, value in body.model_dump().items()):
            raise HTTPException(409, "Payment already refunded or request payload changed")
        await db.commit()
        if inserted.rowcount and os.environ.get("REFUND_SIM_DROP_FIRST_RECEIPT") == "1":
            raise HTTPException(503, "Simulated receipt loss after commit")
    return receipt(row)


@app.get("/sandbox/refunds/{request_id}")
async def find(request_id: str):
    async with aiosqlite.connect(database()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM refunds WHERE requestId = ?", (request_id,)) as query:
            row = await query.fetchone()
    if row is None:
        raise HTTPException(404, "Refund not found")
    return receipt(row)
