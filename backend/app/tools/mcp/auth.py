from __future__ import annotations

import hashlib
from datetime import datetime

from sqlalchemy import select

from app.db.models import MCPAccessToken, User


def hash_mcp_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def resolve_mcp_principal(token: str) -> tuple[User, frozenset[str], MCPAccessToken] | None:
    from app.db.session import SessionLocal
    async with SessionLocal() as db:
        row = await db.scalar(select(MCPAccessToken).where(MCPAccessToken.token_hash == hash_mcp_token(token)))
        if not row or not row.enabled or (row.expires_at and row.expires_at <= datetime.utcnow()):
            return None
        user = await db.get(User, int(row.user_id))
        if not user:
            return None
        row.last_used_at = datetime.utcnow()
        await db.commit()
        principal = User(
            id=user.id, username=user.username, password="", role=user.role,
            org_tags=user.org_tags, primary_org=user.primary_org,
            token_version=user.token_version,
        )
        scopes = frozenset(x.strip() for x in (row.scopes or "").split(",") if x.strip())
        return principal, scopes, row
