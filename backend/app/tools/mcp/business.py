from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings
from app.tools.base import ToolExecutionContext
from app.tools.mcp.client import MCPRemoteClient, get_remote_server_config


DEFAULT_USER_ARGUMENTS = {
    "query_call_log": "customer_id",
    "query_api_key_status": "customer_id",
    "query_recent_call_stats": "customer_id",
    "query_error_code": None,
    "query_plan": "customer_id",
    "query_usage": "customer_id",
    "query_bill": "customer_id",
}

DEFAULT_REMOTE_NAMES = {
    "query_call_log": "query_call_log",
    "query_api_key_status": "query_api_key_status",
    "query_recent_call_stats": "query_recent_call_stats",
    "query_error_code": "query_error_code",
    "query_plan": "query_plan",
    "query_usage": "query_usage",
    "query_bill": "query_bill",
}


@dataclass(frozen=True, slots=True)
class BusinessToolRoute:
    remote_tool: str
    user_argument: str | None


class BusinessMCPAdapter:
    """Stable local Tool facade backed by either local services or remote MCP.

    Agent prompts keep using names such as ``query_bill``. In production operators can
    switch BUSINESS_TOOL_BACKEND=mcp and map those names to a CRM/API-gateway/billing MCP
    server without changing LangGraph, Skill files, or benchmark contracts.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def enabled(self) -> bool:
        return self.settings.business_tool_backend.strip().lower() == "mcp"

    def _routes(self) -> dict[str, BusinessToolRoute]:
        raw = self.settings.business_mcp_tool_map_json.strip() or "{}"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("BUSINESS_MCP_TOOL_MAP_JSON must be valid JSON") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("BUSINESS_MCP_TOOL_MAP_JSON must be a JSON object")
        routes: dict[str, BusinessToolRoute] = {}
        for local_name, default_remote in DEFAULT_REMOTE_NAMES.items():
            item = payload.get(local_name, default_remote)
            default_user_arg = DEFAULT_USER_ARGUMENTS.get(local_name)
            if default_user_arg and self.settings.business_mcp_default_user_argument.strip():
                default_user_arg = self.settings.business_mcp_default_user_argument.strip()
            if isinstance(item, str):
                routes[local_name] = BusinessToolRoute(
                    remote_tool=item,
                    user_argument=default_user_arg,
                )
            elif isinstance(item, dict):
                remote = str(item.get("tool") or item.get("remoteTool") or default_remote).strip()
                user_arg = item.get("userArgument", default_user_arg)
                user_arg = str(user_arg).strip() if user_arg not in (None, False, "") else None
                routes[local_name] = BusinessToolRoute(remote_tool=remote, user_argument=user_arg)
            else:
                raise RuntimeError(f"Invalid business MCP mapping for {local_name}")
        return routes

    def route_for(self, local_tool_name: str) -> BusinessToolRoute:
        if local_tool_name not in DEFAULT_REMOTE_NAMES:
            raise RuntimeError(f"Unsupported business MCP tool: {local_tool_name}")
        return self._routes()[local_tool_name]

    async def call(self, local_tool_name: str, context: ToolExecutionContext, arguments: dict[str, Any]) -> Any:
        server_name = self.settings.business_mcp_server.strip()
        if not server_name:
            raise RuntimeError("BUSINESS_MCP_SERVER is required when BUSINESS_TOOL_BACKEND=mcp")
        server = get_remote_server_config(server_name)
        if server is None:
            raise RuntimeError(f"Configured business MCP server not found: {server_name}")
        route = self.route_for(local_tool_name)
        remote_arguments = dict(arguments)
        if route.user_argument:
            # The remote business service must still authenticate/authorize this customer;
            # this field is routing context, not a substitute for MCP bearer auth.
            remote_arguments.setdefault(route.user_argument, str(context.user.id))
        result = await MCPRemoteClient(server).call_tool(route.remote_tool, remote_arguments)
        return self._unwrap_result(result)

    @staticmethod
    def _unwrap_result(result: Any) -> Any:
        if not isinstance(result, dict):
            return result
        structured = result.get("structuredContent") or result.get("structured_content")
        if structured is not None:
            return structured
        content = result.get("content")
        if isinstance(content, list) and len(content) == 1 and isinstance(content[0], dict):
            text = content[0].get("text")
            if isinstance(text, str):
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"text": text}
        return result


business_mcp_adapter = BusinessMCPAdapter()
