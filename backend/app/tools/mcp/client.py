from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
import json
from typing import Any

@dataclass(slots=True)
class RemoteServerConfig:
    name: str
    url: str
    bearer_token: str = ""
    allowed_tools: frozenset[str] = frozenset()
    read_only: bool = True
    timeout_seconds: float = 30.0

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
            result = result.model_dump(mode="json")
        if isinstance(result, dict):
            # MCP servers may return structured data either in
            # structuredContent/structured_content or as JSON text in a
            # content item.  Normalize the latter at the client boundary so
            # callers can consume one stable response shape.
            structured = result.get("structuredContent") or result.get("structured_content")
            if structured is None:
                content = result.get("content")
                if isinstance(content, list):
                    for item in content:
                        if not isinstance(item, dict) or item.get("type") != "text":
                            continue
                        text = item.get("text")
                        if not isinstance(text, str):
                            continue
                        try:
                            candidate = json.loads(text)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(candidate, dict):
                            structured = candidate
                            break
            if structured is not None:
                result.setdefault("structuredContent", structured)
                result.setdefault("structured_content", structured)
        return result
