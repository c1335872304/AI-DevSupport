from __future__ import annotations

import secrets
import hashlib
import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import admin_user
from app.core.response import ok
from app.core.security import hash_password
from app.core.time import utcnow
from app.db.models import ConversationMessage, InviteCode, OrganizationTag, RechargePackage, User, UserTokenRecord, MCPAccessToken
from app.db.session import get_db
from app.accounting.rate_limit import rate_limit_service

router = APIRouter(prefix="/admin", tags=["admin"])


class InviteCreate(BaseModel):
    code: str | None = None
    maxUses: int = 1
    count: int | None = None
    expiresAt: datetime | None = None


class InviteUpdate(BaseModel):
    code: str
    maxUses: int
    expiresAt: datetime | None = None


class OrgCreate(BaseModel):
    tagId: str | None = None
    name: str
    description: str | None = None
    parentTag: str | None = None
    uploadMaxSizeBytes: int | None = None


class UserOrgUpdate(BaseModel):
    orgTags: list[str]
    primaryOrg: str | None = None


class PackagePayload(BaseModel):
    packageName: str
    packagePrice: int
    packageDesc: str | None = None
    packageBenefit: str | None = None
    llmToken: int = 0
    embeddingToken: int = 0
    sortOrder: int = 10
    enabled: bool = True


class MCPTokenCreate(BaseModel):
    name: str
    userId: int
    scopes: list[str] = Field(default_factory=lambda: ["tools:read"])
    expiresAt: datetime | None = None


def org_dict(x: OrganizationTag) -> dict:
    return {
        "tagId": x.tag_id,
        "name": x.name,
        "description": x.description,
        "parentTag": x.parent_tag,
        "uploadMaxSizeBytes": x.upload_max_size_bytes,
        "createdAt": x.created_at.isoformat(),
        "updatedAt": x.updated_at.isoformat(),
    }


def build_tree(tags: list[OrganizationTag]) -> list[dict]:
    nodes = {x.tag_id: {**org_dict(x), "children": []} for x in tags}
    roots = []
    for x in tags:
        if x.parent_tag and x.parent_tag in nodes:
            nodes[x.parent_tag]["children"].append(nodes[x.tag_id])
        else:
            roots.append(nodes[x.tag_id])
    return roots


@router.get("/org-tags/tree")
async def org_tree(admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    return ok(build_tree(list((await db.scalars(select(OrganizationTag))).all())))


@router.get("/org-tags")
async def org_list(admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    return ok([org_dict(x) for x in (await db.scalars(select(OrganizationTag))).all()])


@router.post("/org-tags")
async def create_org(payload: OrgCreate, admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    tag_id = payload.tagId or secrets.token_hex(6)
    if await db.get(OrganizationTag, tag_id):
        raise HTTPException(status_code=409, detail="Tag already exists")
    item = OrganizationTag(
        tag_id=tag_id,
        name=payload.name,
        description=payload.description,
        parent_tag=payload.parentTag,
        upload_max_size_bytes=payload.uploadMaxSizeBytes,
        created_by=admin.id,
    )
    db.add(item)
    await db.commit()
    return ok(org_dict(item))


@router.put("/users/{user_id}/org-tags")
async def update_user_orgs(user_id: int, payload: UserOrgUpdate, admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.org_tags = ",".join(payload.orgTags)
    user.primary_org = payload.primaryOrg or (payload.orgTags[0] if payload.orgTags else None)
    await db.commit()
    return ok(message="Updated")


@router.get("/users/list")
@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=200),
    admin: User = Depends(admin_user),
    db: AsyncSession = Depends(get_db),
):
    users = list((await db.scalars(select(User).order_by(User.id.desc()))).all())
    total = len(users)
    rows = users[(page - 1) * size : page * size]
    data = [
        {
            "id": u.id,
            "userId": u.id,
            "username": u.username,
            "role": u.role,
            "orgTags": [x for x in (u.org_tags or "").split(",") if x],
            "primaryOrg": u.primary_org,
            "llmTokenBalance": u.llm_token_balance,
            "embeddingTokenBalance": u.embedding_token_balance,
            "createdAt": u.created_at.isoformat(),
        }
        for u in rows
    ]
    return ok({"content": data, "data": data, "number": page, "size": size, "totalElements": total})


@router.post("/invite-codes")
async def create_invite(payload: InviteCreate, admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    count = max(1, payload.count or 1)
    created = []
    for _ in range(count):
        code = payload.code if count == 1 and payload.code else secrets.token_urlsafe(8)
        item = InviteCode(code=code, max_uses=payload.maxUses, expires_at=payload.expiresAt)
        db.add(item)
        created.append(item)
    await db.commit()
    return ok([{"id": x.id, "code": x.code, "maxUses": x.max_uses} for x in created])


@router.get("/invite-codes")
async def list_invites(
    page: int = Query(1, ge=1), size: int = Query(10, ge=1), admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)
):
    items = list((await db.scalars(select(InviteCode).order_by(InviteCode.id.desc()))).all())
    total = len(items)
    rows = items[(page - 1) * size : page * size]
    data = [
        {
            "id": x.id,
            "code": x.code,
            "maxUses": x.max_uses,
            "usedCount": x.used_count,
            "enabled": x.enabled,
            "expiresAt": x.expires_at.isoformat() if x.expires_at else None,
            "createdAt": x.created_at.isoformat(),
        }
        for x in rows
    ]
    return ok({"content": data, "data": data, "number": page, "size": size, "totalElements": total})


@router.patch("/invite-codes/{invite_id}/disable")
async def disable_invite(invite_id: int, admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    item = await db.get(InviteCode, invite_id)
    if not item:
        raise HTTPException(status_code=404, detail="Invite code not found")
    item.enabled = False
    await db.commit()
    return ok(message="Disabled")


@router.delete("/invite-codes/{invite_id}")
async def delete_invite(invite_id: int, admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    item = await db.get(InviteCode, invite_id)
    if item:
        await db.delete(item)
        await db.commit()
    return ok(message="Deleted")


@router.put("/invite-codes/{invite_id}")
async def update_invite(invite_id: int, payload: InviteUpdate, admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    item = await db.get(InviteCode, invite_id)
    if not item:
        raise HTTPException(status_code=404, detail="Invite code not found")
    item.code = payload.code
    item.max_uses = payload.maxUses
    item.expires_at = payload.expiresAt
    await db.commit()
    return ok(message="Updated")


@router.get("/conversation")
async def admin_conversation(
    userid: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    admin: User = Depends(admin_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ConversationMessage).order_by(ConversationMessage.id)
    # The remote user select can briefly serialize an empty/undefined value
    # while its options load. Treat it as "all users" instead of returning a
    # 422 for an administrative read-only filter.
    normalized_user_id = str(userid or "").strip()
    if normalized_user_id.isdigit() and int(normalized_user_id) > 0:
        stmt = stmt.where(ConversationMessage.user_id == normalized_user_id)
    rows = list((await db.scalars(stmt)).all())
    if start_date:
        rows = [x for x in rows if x.created_at.date().isoformat() >= start_date]
    if end_date:
        rows = [x for x in rows if x.created_at.date().isoformat() <= end_date]
    user_ids = {x.user_id for x in rows}
    users = {str(u.id): u.username for u in (await db.scalars(select(User))).all() if str(u.id) in user_ids}
    data = []
    import json
    for row in rows:
        data.append({
            "role": row.role,
            "content": row.content,
            "timestamp": row.created_at.isoformat(),
            "conversationId": row.conversation_id,
            "generationId": row.generation_id,
            "username": users.get(row.user_id),
            "referenceMappings": json.loads(row.reference_mappings_json) if row.reference_mappings_json else None,
            "status": "finished" if row.role == "assistant" else None,
        })
    return ok(data)


@router.get("/usage/overview")
async def usage_overview(days: int = Query(7, ge=1, le=90), admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    """Return the usage-monitor contract consumed by the admin UI.

    Token records are a ledger, so reservations and refunds must not be
    counted as consumption.  Only settled ``CONSUME`` records are used here.
    """
    start = utcnow().date() - timedelta(days=days - 1)
    rows = list((await db.scalars(select(UserTokenRecord).where(UserTokenRecord.record_date >= start))).all())
    user_rows = list((await db.scalars(select(User))).all())
    users = {str(u.id): u for u in user_rows}

    def empty_day(day: str) -> dict:
        return {
            "day": day,
            "chatRequestCount": 0,
            "llmUsedTokens": 0,
            "llmRequestCount": 0,
            "embeddingUsedTokens": 0,
            "embeddingRequestCount": 0,
        }

    # Always return a continuous series.  Otherwise a quiet day disappears
    # from the chart and makes a seven-day view look like a one-day view.
    by_date = {
        (start + timedelta(days=offset)).isoformat(): empty_day((start + timedelta(days=offset)).isoformat())
        for offset in range(days)
    }
    by_scope_user: dict[str, dict[str, dict[str, int]]] = {"llm": {}, "embedding": {}}
    for row in rows:
        day = row.record_date.isoformat()
        item = by_date.setdefault(day, empty_day(day))
        consumed = abs(min(0, int(row.amount or 0))) if row.change_type == "CONSUME" else 0
        if not consumed:
            continue
        if row.token_type.upper() == "LLM":
            item["llmUsedTokens"] += consumed
            item["llmRequestCount"] += int(row.request_count or 0)
            item["chatRequestCount"] += int(row.request_count or 0)
            aggregate = by_scope_user["llm"].setdefault(row.user_id, {"tokens": 0, "requests": 0})
        elif row.token_type.upper() == "EMBEDDING":
            item["embeddingUsedTokens"] += consumed
            item["embeddingRequestCount"] += int(row.request_count or 0)
            aggregate = by_scope_user["embedding"].setdefault(row.user_id, {"tokens": 0, "requests": 0})
        else:
            continue
        aggregate["tokens"] += consumed
        aggregate["requests"] += int(row.request_count or 0)

    trends = [by_date[key] for key in sorted(by_date)]
    today_key = utcnow().date().isoformat()
    today = by_date.get(today_key, empty_day(today_key))

    def rankings(scope: str) -> list[dict]:
        result = []
        for user_id, aggregate in by_scope_user[scope].items():
            user = users.get(user_id)
            remaining = int(
                (user.llm_token_balance if scope == "llm" else user.embedding_token_balance) if user else 0
            )
            used = aggregate["tokens"]
            result.append({
                "userId": user_id,
                "username": user.username if user else f"已删除用户 ({user_id})",
                "scope": scope,
                "usedTokens": used,
                # The ledger has no immutable per-period quota.  This value is
                # deliberately a current available-total snapshot, not a claim
                # about a subscription plan.
                "limitTokens": used + max(0, remaining),
                "remainingTokens": remaining,
                "requestCount": aggregate["requests"],
            })
        return sorted(result, key=lambda item: item["usedTokens"], reverse=True)[:10]

    llm_rankings = rankings("llm")
    embedding_rankings = rankings("embedding")
    alerts = []
    for item in [*llm_rankings, *embedding_rankings]:
        limit = item["limitTokens"]
        ratio = item["usedTokens"] / limit if limit else 1.0
        if item["remainingTokens"] <= 0:
            level, message = "critical", "余额已耗尽"
        elif ratio >= 0.8:
            level, message = "warning", "可用余额不足 20%"
        else:
            continue
        alerts.append({**item, "level": level, "usageRatio": ratio, "message": message})

    return ok({
        "days": days,
        "today": today,
        "trends": trends,
        "llmRankings": llm_rankings,
        "embeddingRankings": embedding_rankings,
        "alerts": alerts,
    })


@router.get("/rate-limits")
async def rate_limits(admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    return ok(await rate_limit_service.get_policies(db))


@router.put("/rate-limits")
async def update_rate_limits(payload: dict, admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    return ok(await rate_limit_service.set_policies(db, payload), "Rate limits updated")


@router.get("/model-providers")
async def model_providers(admin: User = Depends(admin_user)):
    from app.core.config import get_settings

    s = get_settings()

    def provider_item(*, scope: str, model: str, base_url: str, dimension: int | None, api_key: str) -> dict:
        """Expose the active deployment provider without ever returning its secret."""
        masked_key = ""
        if api_key:
            masked_key = f"{api_key[:3]}***{api_key[-4:]}" if len(api_key) > 7 else "***"
        return {
            "provider": "openai-compatible",
            "displayName": "OpenAI Compatible",
            "apiStyle": "openai-compatible",
            "apiBaseUrl": base_url,
            "model": model,
            "dimension": dimension,
            "enabled": True,
            "active": True,
            "hasApiKey": bool(api_key),
            "maskedApiKey": masked_key,
        }

    llm = provider_item(
        scope="llm",
        model=s.llm_model,
        base_url=s.llm_base_url,
        dimension=None,
        api_key=s.llm_api_key,
    )
    embedding = provider_item(
        scope="embedding",
        model=s.embedding_model,
        base_url=s.embedding_base_url,
        dimension=s.embedding_dimension,
        api_key=s.embedding_api_key,
    )
    return ok(
        {
            "llm": {"scope": "llm", "activeProvider": llm["provider"], "providers": [llm]},
            "embedding": {
                "scope": "embedding",
                "activeProvider": embedding["provider"],
                "providers": [embedding],
            },
        }
    )


@router.put("/model-providers/{scope}")
async def update_model_provider(scope: str, payload: dict, admin: User = Depends(admin_user)):
    # Provider settings remain deployment
    # secrets and must be changed through env/secret management followed by restart.
    raise HTTPException(status_code=501, detail="Provider persistence is disabled; update deployment secrets/environment instead")


@router.post("/model-providers/{scope}/test")
async def test_model_provider(scope: str, payload: dict, admin: User = Depends(admin_user)):
    import httpx
    import time
    from app.core.config import get_settings
    s = get_settings()
    if scope not in {"llm", "embedding"}:
        raise HTTPException(status_code=404, detail="Unknown provider scope")
    base_url = str(payload.get("apiBaseUrl") or (s.llm_base_url if scope == "llm" else s.embedding_base_url)).rstrip("/")
    api_key = str(payload.get("apiKey") or (s.llm_api_key if scope == "llm" else s.embedding_api_key)).strip()
    if not api_key:
        raise HTTPException(status_code=422, detail="API key is required to test provider connectivity")
    try:
        started = time.monotonic()
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(base_url + "/models", headers={"Authorization": f"Bearer {api_key}"})
            response.raise_for_status()
        return ok(
            {
                "success": True,
                "scope": scope,
                "statusCode": response.status_code,
                "message": "Provider connection succeeded",
                "latencyMs": int((time.monotonic() - started) * 1000),
            },
            "Provider connection succeeded",
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Provider connection failed: {str(exc)[:300]}") from exc


@router.post("/mcp-tokens")
async def create_mcp_token(payload: MCPTokenCreate, admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    user = await db.get(User, payload.userId)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    raw = "psmcp_" + secrets.token_urlsafe(32)
    scopes = sorted({x.strip() for x in payload.scopes if x.strip()})
    if not scopes:
        raise HTTPException(status_code=422, detail="At least one scope is required")
    row = MCPAccessToken(
        token_hash=hashlib.sha256(raw.encode("utf-8")).hexdigest(), name=payload.name.strip() or "MCP client",
        user_id=str(user.id), scopes=",".join(scopes), expires_at=payload.expiresAt, enabled=True,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    # Plaintext is intentionally returned exactly once. Only the SHA-256 hash is stored.
    return ok({"id": row.id, "token": raw, "name": row.name, "userId": row.user_id, "scopes": scopes, "expiresAt": row.expires_at.isoformat() if row.expires_at else None})


@router.get("/mcp-tokens")
async def list_mcp_tokens(admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    rows = list((await db.scalars(select(MCPAccessToken).order_by(MCPAccessToken.id.desc()))).all())
    return ok([{
        "id": row.id, "name": row.name, "userId": row.user_id,
        "scopes": [x for x in row.scopes.split(",") if x], "enabled": row.enabled,
        "expiresAt": row.expires_at.isoformat() if row.expires_at else None,
        "lastUsedAt": row.last_used_at.isoformat() if row.last_used_at else None,
        "createdAt": row.created_at.isoformat(),
    } for row in rows])


@router.delete("/mcp-tokens/{token_id}")
async def revoke_mcp_token(token_id: int, admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    row = await db.get(MCPAccessToken, token_id)
    if not row:
        raise HTTPException(status_code=404, detail="MCP token not found")
    row.enabled = False
    await db.commit()
    return ok(message="MCP token revoked")


@router.get("/recharge-packages")
async def admin_packages(admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    items = list((await db.scalars(select(RechargePackage).order_by(RechargePackage.sort_order))).all())
    return ok([_package_dict(x) for x in items])


def _package_dict(x: RechargePackage) -> dict:
    return {"id": x.id, "packageName": x.package_name, "packagePrice": x.package_price, "packageDesc": x.package_desc, "packageBenefit": x.package_benefit, "llmToken": x.llm_token, "embeddingToken": x.embedding_token, "sortOrder": x.sort_order, "enabled": x.enabled, "deleted": x.deleted}


@router.post("/recharge-packages")
async def create_package(payload: PackagePayload, admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    item = RechargePackage(package_name=payload.packageName, package_price=payload.packagePrice, package_desc=payload.packageDesc, package_benefit=payload.packageBenefit, llm_token=payload.llmToken, embedding_token=payload.embeddingToken, sort_order=payload.sortOrder, enabled=payload.enabled)
    db.add(item)
    await db.commit()
    return ok(_package_dict(item))


@router.put("/recharge-packages/{package_id}")
async def update_package(package_id: int, payload: PackagePayload, admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    item = await db.get(RechargePackage, package_id)
    if not item:
        raise HTTPException(status_code=404, detail="Package not found")
    for field, value in {"package_name": payload.packageName, "package_price": payload.packagePrice, "package_desc": payload.packageDesc, "package_benefit": payload.packageBenefit, "llm_token": payload.llmToken, "embedding_token": payload.embeddingToken, "sort_order": payload.sortOrder, "enabled": payload.enabled}.items():
        setattr(item, field, value)
    await db.commit()
    return ok(_package_dict(item))


@router.delete("/recharge-packages/{package_id}")
async def delete_package(package_id: int, admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    item = await db.get(RechargePackage, package_id)
    if item:
        item.deleted = True
        item.enabled = False
        await db.commit()
    return ok(message="Deleted")

@router.get("/agent-runs")
async def list_agent_runs(
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(admin_user),
    db: AsyncSession = Depends(get_db),
):
    from app.db.models import AgentRun
    rows = list((await db.scalars(select(AgentRun).order_by(AgentRun.started_at.desc()).limit(limit))).all())
    return ok([{
        "runId": row.run_id,
        "generationId": row.generation_id,
        "userId": row.user_id,
        "question": row.question,
        "status": row.status,
        "activeSkills": json.loads(row.active_skills_json) if row.active_skills_json else [],
        "trace": json.loads(row.trace_json) if row.trace_json else None,
        "error": row.error,
        "startedAt": row.started_at.isoformat(),
        "completedAt": row.completed_at.isoformat() if row.completed_at else None,
    } for row in rows])


@router.get("/agent-runs/{run_id}")
async def get_agent_run(run_id: str, admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    from app.db.models import AgentRun, ToolExecution
    row = await db.get(AgentRun, run_id)
    if not row:
        raise HTTPException(status_code=404, detail="Agent run not found")
    tools = list((await db.scalars(
        select(ToolExecution).where(ToolExecution.run_id == run_id).order_by(ToolExecution.id.asc())
    )).all())
    return ok({
        "runId": row.run_id,
        "generationId": row.generation_id,
        "userId": row.user_id,
        "question": row.question,
        "status": row.status,
        "activeSkills": json.loads(row.active_skills_json) if row.active_skills_json else [],
        "trace": json.loads(row.trace_json) if row.trace_json else None,
        "error": row.error,
        "startedAt": row.started_at.isoformat(),
        "completedAt": row.completed_at.isoformat() if row.completed_at else None,
        "tools": [{
            "toolCallId": item.tool_call_id,
            "tool": item.tool_name,
            "step": item.step,
            "status": item.status,
            "durationMs": item.duration_ms,
            "arguments": json.loads(item.arguments_json) if item.arguments_json else {},
            "error": item.error,
            "createdAt": item.created_at.isoformat(),
        } for item in tools],
    })
