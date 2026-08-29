from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import ok
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.db.models import User
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


class RefreshRequest(BaseModel):
    refreshToken: str


@router.post("/refreshToken")
async def refresh_token(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        claims = decode_token(payload.refreshToken, "refresh")
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc
    user = await db.scalar(select(User).where(User.username == claims.get("sub")))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if int(claims.get("ver", 0)) != int(user.token_version or 0):
        raise HTTPException(status_code=401, detail="Refresh token revoked")
    data = {
        "token": create_access_token(user.username, user.id, user.role, user.token_version),
        "refreshToken": create_refresh_token(user.username, user.id, user.role, user.token_version),
    }
    return ok(data, "Token refreshed")


@router.get("/error")
async def custom_error(code: str = "500", msg: str = "error"):
    return {"code": int(code), "message": msg}
