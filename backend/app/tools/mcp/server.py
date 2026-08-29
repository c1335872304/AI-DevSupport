from __future__ import annotations

from pydantic import AnyHttpUrl

from app.core.config import get_settings
from app.db.models import User
from app.db.session import SessionLocal
from app.tools.mcp.auth import resolve_mcp_principal
from app.tools.base import ToolExecutionContext
from app.tools.registry import tool_registry

try:
    from mcp.server import MCPServer
    from mcp.server.auth.middleware.auth_context import get_access_token
    from mcp.server.auth.provider import AccessToken, TokenVerifier
    from mcp.server.auth.settings import AuthSettings
except ImportError as exc:  # pragma: no cover
    raise RuntimeError('MCP support requires the "mcp>=2,<3" package') from exc

settings = get_settings()


class PaiSmartTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        resolved = await resolve_mcp_principal(token)
        if not resolved:
            return None
        user, scopes, record = resolved
        return AccessToken(
            token=token,
            client_id=record.name,
            scopes=sorted(scopes),
            subject=str(user.id),
            claims={"username": user.username, "role": user.role},
        )


server_kwargs = {
    "instructions": (
        "PaiSmart MCP exposes permission-checked tools from the same ToolRegistry as the in-app Agent Runtime. "
        "Streamable HTTP uses per-client bearer tokens; stdio uses the explicitly configured MCP_SERVICE_USERNAME."
    )
}
if settings.mcp_auth_enabled:
    server_kwargs.update(
        token_verifier=PaiSmartTokenVerifier(),
        auth=AuthSettings(
            issuer_url=AnyHttpUrl(settings.mcp_auth_issuer_url),
            resource_server_url=AnyHttpUrl(settings.mcp_resource_server_url),
            required_scopes=[settings.mcp_required_scope],
        ),
    )
mcp = MCPServer("PaiSmart Knowledge Tools", **server_kwargs)


async def _service_user() -> User:
    username = settings.mcp_service_username.strip()
    if not username:
        raise RuntimeError("MCP_SERVICE_USERNAME is required for stdio/in-memory MCP access")
    async with SessionLocal() as db:
        from sqlalchemy import select
        user = await db.scalar(select(User).where(User.username == username))
        if not user:
            raise RuntimeError(f"MCP service user not found: {username}")
        return User(id=user.id, username=user.username, password="", role=user.role, org_tags=user.org_tags, primary_org=user.primary_org, token_version=user.token_version)


async def _principal() -> tuple[User, frozenset[str]]:
    access = get_access_token()
    if access is not None and access.subject:
        async with SessionLocal() as db:
            user = await db.get(User, int(access.subject))
            if not user:
                raise PermissionError("MCP principal no longer exists")
            principal = User(id=user.id, username=user.username, password="", role=user.role, org_tags=user.org_tags, primary_org=user.primary_org, token_version=user.token_version)
            return principal, frozenset(access.scopes or [])
    # HTTP auth never reaches here when auth is enabled. This fallback is intentionally
    # limited to stdio/in-memory transports, whose security boundary is the launcher.
    return await _service_user(), frozenset({"*"})


async def _execute(name: str, arguments: dict):
    user, scopes = await _principal()
    result = await tool_registry.execute(name, arguments, ToolExecutionContext(user=user, generation_id="mcp", scopes=scopes, source="mcp"))
    return result.as_payload()


@mcp.tool()
async def search_knowledge(query: str, top_k: int = 6) -> dict:
    """Search knowledge-base content visible to the authenticated PaiSmart principal."""
    return await _execute("search_knowledge", {"query": query, "top_k": top_k})


@mcp.tool()
async def list_documents(keyword: str = "", limit: int = 20) -> dict:
    """List knowledge-base documents visible to the authenticated PaiSmart principal."""
    return await _execute("list_documents", {"keyword": keyword, "limit": limit})


@mcp.tool()
async def get_document(file_md5: str, chunk_id: int | None = None, max_chars: int = 5000) -> dict:
    """Read one accessible PaiSmart document or context around a known child chunk."""
    arguments = {"file_md5": file_md5, "max_chars": max_chars}
    if chunk_id is not None:
        arguments["chunk_id"] = chunk_id
    return await _execute("get_document", arguments)
