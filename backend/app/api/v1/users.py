from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import current_user, user_orgs
from app.core.response import ok
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.core.time import utcnow
from app.db.models import InviteCode, OrganizationTag, User, UserTokenRecord
from app.db.session import get_db
from app.accounting.rate_limit import rate_limit_service
from app.accounting.usage import usage_service

router = APIRouter(prefix="/users", tags=["users"])


class UserRequest(BaseModel):
    username: str
    password: str
    inviteCode: str | None = None


class PrimaryOrgRequest(BaseModel):
    primaryOrg: str | None = None
    orgTag: str | None = None


@router.post("/register")
async def register(payload: UserRequest, request: Request = None, db: AsyncSession = Depends(get_db)):
    # Keep direct service-level callers compatible with the old (payload, db)
    # signature while FastAPI still injects Request and the database normally.
    if request is not None and not hasattr(request, "client") and hasattr(request, "execute"):
        db = request  # type: ignore[assignment]
        request = None
    client_host = request.client.host if request and request.client else "unknown"
    await rate_limit_service.check(db, "register", client_host)
    username = payload.username.strip()
    invite_code = (payload.inviteCode or "").strip()
    if not username or not payload.password:
        raise HTTPException(status_code=400, detail="Username and password cannot be empty")
    if not invite_code:
        raise HTTPException(status_code=400, detail="INVITE_CODE_REQUIRED")
    if await db.scalar(select(User).where(User.username == username)):
        raise HTTPException(status_code=409, detail="Username already exists")

    invite = await db.scalar(select(InviteCode).where(InviteCode.code == invite_code))
    if not invite or not invite.enabled:
        raise HTTPException(status_code=400, detail="INVITE_CODE_INVALID")
    if invite.expires_at and invite.expires_at <= utcnow():
        raise HTTPException(status_code=400, detail="INVITE_CODE_EXPIRED")
    if invite.used_count >= invite.max_uses:
        raise HTTPException(status_code=400, detail="INVITE_CODE_EXHAUSTED")

    # Consume the code atomically so two concurrent registrations cannot both use
    # the final remaining slot. The user insert and invite consumption commit together.
    consumed = await db.execute(
        update(InviteCode)
        .where(
            InviteCode.id == invite.id,
            InviteCode.enabled.is_(True),
            InviteCode.used_count < InviteCode.max_uses,
        )
        .values(used_count=InviteCode.used_count + 1)
    )
    if consumed.rowcount != 1:
        await db.rollback()
        raise HTTPException(status_code=400, detail="INVITE_CODE_EXHAUSTED")

    user = User(
        username=username,
        password=hash_password(payload.password),
        role="USER",
        org_tags="default",
        primary_org="default",
    )
    db.add(user)
    await db.commit()
    return ok(message="User registered successfully")


@router.post("/login")
async def login(payload: UserRequest, request: Request, db: AsyncSession = Depends(get_db)):
    client = request.client.host if request.client else "unknown"
    await rate_limit_service.check(db, "login", f"{client}:{payload.username.strip().lower()}")
    user = await db.scalar(select(User).where(User.username == payload.username))
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return ok(
        {
            "token": create_access_token(user.username, user.id, user.role, user.token_version),
            "refreshToken": create_refresh_token(user.username, user.id, user.role, user.token_version),
        },
        "Login successful",
    )


@router.get("/me")
async def me(user: User = Depends(current_user)):
    return ok(
        {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "orgTags": sorted(user_orgs(user)),
            "primaryOrg": user.primary_org,
            "createdAt": user.created_at.isoformat(),
            "updatedAt": user.updated_at.isoformat(),
        },
        "Get user detail successful",
    )


@router.get("/org-tags")
async def get_org_tags(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    orgs = user_orgs(user)
    tags = list((await db.scalars(select(OrganizationTag))).all())
    data = [
        {
            "tagId": item.tag_id,
            "name": item.name,
            "description": item.description,
            "parentTag": item.parent_tag,
            "uploadMaxSizeBytes": item.upload_max_size_bytes,
        }
        for item in tags
        if item.tag_id in orgs or user.role == "ADMIN"
    ]
    return ok(data)


@router.get("/upload-orgs")
async def upload_orgs(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return await get_org_tags(user, db)


@router.put("/primary-org")
async def set_primary_org(payload: PrimaryOrgRequest, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    tag = payload.primaryOrg or payload.orgTag
    if not tag:
        raise HTTPException(status_code=400, detail="Primary organization tag cannot be empty")
    if tag not in user_orgs(user) and user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="No permission for this organization")
    user.primary_org = tag
    await db.commit()
    return ok(message="Primary organization set successfully")


@router.get("/usage")
async def usage(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return ok(await usage_service.summary_for_user(db, user))


@router.get("/token-records")
async def token_records(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = list(
        (
            await db.scalars(
                select(UserTokenRecord).where(UserTokenRecord.user_id == str(user.id)).order_by(UserTokenRecord.id.desc())
            )
        ).all()
    )
    data = [
        {
            "id": r.id,
            "recordDate": r.record_date.isoformat(),
            "tokenType": r.token_type,
            "changeType": r.change_type,
            "amount": r.amount,
            "balanceBefore": r.balance_before,
            "balanceAfter": r.balance_after,
            "reason": r.reason,
            "remark": r.remark,
            "createdAt": r.created_at.isoformat(),
        }
        for r in rows
    ]
    return ok(data)


@router.post("/logout")
async def logout(user: User = Depends(current_user)):
    # Stateless JWT: client discards token. Add Redis blacklist if strict revocation is needed.
    return ok(message="Logout successful")


@router.post("/logout-all")
async def logout_all(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    user.token_version = int(user.token_version or 0) + 1
    await db.commit()
    return ok(message="Logout from all devices successful")
