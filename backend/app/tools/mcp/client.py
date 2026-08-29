from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings
from app.tools.base import BaseTool, ToolExecutionContext


@dataclass(slots=True)
class RemoteServerConfig:
    name: str
    url: str
    bearer_token: str = ""
    allowed_tools: frozenset[str] = frozenset()
    read_only: bool = True
    timeout_seconds: float = 30.0


def configured_servers() -> list[RemoteServerConfig]:
    raw = get_settings().mcp_remote_servers_json.strip() or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("MCP_REMOTE_SERVERS_JSON must be valid JSON") from exc
    output = []
    for name, item in (data.items() if isinstance(data, dict) else []):
        if not isinstance(item, dict) or not str(item.get("url") or "").strip():
            continue
        token = str(item.get("bearerToken") or "")
        env_name = str(item.get("bearerTokenEnv") or "").strip()
        if env_name:
            token = os.getenv(env_name, "")
        output.append(RemoteServerConfig(
            name=str(name), url=str(item["url"]).strip(), bearer_token=token,
            allowed_tools=frozenset(str(x) for x in (item.get("allowedTools") or [])),
            read_only=bool(item.get("readOnly", True)),
            timeout_seconds=float(item.get("timeoutSeconds", 30.0)),
        ))
    return output


def get_remote_server_config(name: str) -> RemoteServerConfig | None:
    wanted = str(name or "").strip()
    return next((item for item in configured_servers() if item.name == wanted), None)


class MCPRemoteClient:
    def __init__(self, config: RemoteServerConfig) -> None:
        self.config = config

    @asynccontextmanager
    async def connected(self):
        try:
            from mcp import Client
        except ImportError as exc:
            raise RuntimeError('External MCP tools require the "mcp>=2,<3" package') from exc
        if not self.config.bearer_token:
            async with Client(self.config.url, read_timeout_seconds=self.config.timeout_seconds) as client:
                yield client
            return
        try:
            import httpx2
            from mcp.client.streamable_http import streamable_http_client
        except ImportError as exc:
            raise RuntimeError("Authenticated MCP client requires MCP v2 transport dependencies") from exc
        async with httpx2.AsyncClient(
            headers={"Authorization": f"Bearer {self.config.bearer_token}"},
            follow_redirects=True,
        ) as http_client:
            transport = streamable_http_client(self.config.url, http_client=http_client)
            async with Client(transport, read_timeout_seconds=self.config.timeout_seconds) as client:
                yield client

    async def list_tools(self) -> list[Any]:
        async with self.connected() as client:
            result = await client.list_tools()
            return list(getattr(result, "tools", result) or [])

    async def call_tool(self, name: str, arguments: dict) -> Any:
        async with self.connected() as client:
            result = await client.call_tool(name, arguments)
        if hasattr(result, "model_dump"):
            return result.model_dump(mode="json")
        return result


class MCPRemoteTool(BaseTool):
    def __init__(self, server: RemoteServerConfig, remote_name: str, description: str, input_schema: dict) -> None:
        self.server = server
        self.remote_name = remote_name
        self.name = f"mcp__{server.name}__{remote_name}"
        self.description = f"[{server.name} MCP] {description or remote_name}"
        self.input_schema = input_schema or {"type": "object", "properties": {}}
        self.timeout_seconds = server.timeout_seconds
        self.parallel_safe = server.read_only
        self.read_only = server.read_only
        self.idempotent = server.read_only
        self.resource_group = f"mcp:{server.name}"
        self.risk_level = "low" if server.read_only else "medium"

    async def execute(self, context: ToolExecutionContext, arguments: dict[str, Any]) -> Any:
        return await MCPRemoteClient(self.server).call_tool(self.remote_name, arguments)


async def register_configured_mcp_tools(registry) -> list[str]:
    registered: list[str] = []
    for server in configured_servers():
        client = MCPRemoteClient(server)
        try:
            tools = await client.list_tools()
        except Exception:
            # A remote integration should not prevent PaiSmart from starting. Operators can
            # see absence in /health/details and logs/metrics and repair the server later.
            continue
        for item in tools:
            name = str(getattr(item, "name", "") or "")
            if not name or (server.allowed_tools and name not in server.allowed_tools):
                continue
            description = str(getattr(item, "description", "") or "")
            schema = getattr(item, "inputSchema", None) or getattr(item, "input_schema", None) or {"type": "object", "properties": {}}
            if hasattr(schema, "model_dump"):
                schema = schema.model_dump(mode="json")
            tool = MCPRemoteTool(server, name, description, dict(schema))
            if registry.get(tool.name) is None:
                registry.register(tool)
                registered.append(tool.name)
    return registered
