from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings
from app.tools.base import BaseTool, ToolExecutionContext
from app.tools.mcp.client import MCPRemoteClient, RemoteServerConfig
from app.tools.validation import validate_json_schema


# Input Tool names and schemas are discovered at runtime. Known result
# contracts remain narrow so arbitrary remote fields cannot enter evidence.
KNOWN_BILLING_RESULT_CONTRACTS = {
    "get_plan": "query_plan",
    "get_usage": "query_usage",
    "get_invoice": "query_bill",
}


@dataclass(frozen=True, slots=True)
class DiscoveredBillingTool:
    """A validated MCP Tool catalog entry safe to expose to the Billing LLM."""

    remote_name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None

    @property
    def local_name(self) -> str:
        return f"mcp__billing__{self.remote_name}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.local_name,
            "remoteName": self.remote_name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


class DiscoveredBillingMCPTool(BaseTool):
    """Runtime proxy for one Tool received through Billing MCP ``list_tools``."""

    dynamic_mcp = True
    read_only = True
    parallel_safe = True
    idempotent = True
    resource_group = "billing-mcp-read"
    risk_level = "low"
    required_scopes = frozenset({"tools:read"})

    def __init__(self, adapter: "BillingMCPAdapter", spec: DiscoveredBillingTool) -> None:
        self.adapter = adapter
        self.spec = spec
        self.name = spec.local_name
        self.description = f"[Billing MCP] {spec.description or spec.remote_name}"
        self.input_schema = dict(spec.input_schema)

    async def execute(self, context: ToolExecutionContext, arguments: dict[str, Any]) -> dict[str, Any]:
        remote_arguments = dict(arguments)
        # The customer identity is never exposed in the LLM schema. It is always
        # overwritten from the authenticated API user at the execution boundary.
        remote_arguments["customer_id"] = str(context.user.id)
        result = await MCPRemoteClient(self.adapter._server_config()).call_tool(self.spec.remote_name, remote_arguments)
        payload = self.adapter._unwrap_result(result)
        if self.spec.output_schema:
            validate_json_schema(payload, self.spec.output_schema, path=f"{self.spec.remote_name} result")
        return self.adapter._validate_discovered_result(self.spec.remote_name, payload)


class BillingMCPAdapter:
    """Read-only MCP adapter for stable billing Tool contracts only."""

    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def enabled(self) -> bool:
        return self.settings.billing_mcp_enabled

    def validate_configuration(self) -> None:
        """Fail closed before serving traffic when Billing MCP is enabled."""
        if not self.enabled:
            return
        self._server_config()

    def _server_config(self) -> RemoteServerConfig:
        url = self.settings.billing_mcp_url.strip()
        if not url:
            raise RuntimeError("BILLING_MCP_URL is required when BILLING_MCP_ENABLED=true")
        token_env = self.settings.billing_mcp_bearer_token_env.strip()
        if not token_env:
            raise RuntimeError("BILLING_MCP_BEARER_TOKEN_ENV is required")
        return RemoteServerConfig(
            name="billing",
            url=url,
            bearer_token=os.getenv(token_env, ""),
            allowed_tools=frozenset(),
            read_only=True,
            timeout_seconds=max(1.0, float(self.settings.billing_mcp_timeout_seconds)),
        )

    async def discover_tools(self) -> tuple[DiscoveredBillingMCPTool, ...]:
        """Load the Billing MCP catalog and turn it into safe LLM Tool proxies.

        The MCP server supplies Tool names, descriptions and schemas at runtime.
        The client removes the internal ``customer_id`` field before exposing a
        schema to the LLM and restores it only from authenticated request context.
        """
        if not self.enabled:
            return ()
        raw_tools = await MCPRemoteClient(self._server_config()).list_tools()
        specs: list[DiscoveredBillingTool] = []
        seen: set[str] = set()
        for raw_tool in raw_tools:
            spec = self._discovered_spec(raw_tool)
            if spec.remote_name in seen:
                raise RuntimeError(f"Billing MCP returned duplicate Tool: {spec.remote_name}")
            seen.add(spec.remote_name)
            specs.append(spec)
        if not specs:
            raise RuntimeError("Billing MCP returned no usable Tools")
        return tuple(DiscoveredBillingMCPTool(self, spec) for spec in specs)

    @staticmethod
    def _field(value: Any, *names: str) -> Any:
        for name in names:
            if isinstance(value, dict) and name in value:
                return value[name]
            if hasattr(value, name):
                return getattr(value, name)
        return None

    @classmethod
    def _as_dict(cls, value: Any) -> dict[str, Any] | None:
        if isinstance(value, dict):
            return dict(value)
        if hasattr(value, "model_dump"):
            dumped = value.model_dump(mode="json")
            return dict(dumped) if isinstance(dumped, dict) else None
        if hasattr(value, "__dict__"):
            return dict(vars(value))
        return None

    @classmethod
    def _discovered_spec(cls, raw_tool: Any) -> DiscoveredBillingTool:
        remote_name = str(cls._field(raw_tool, "name") or "").strip()
        if not remote_name or not remote_name.replace("_", "").isalnum() or remote_name.startswith("_"):
            raise RuntimeError("Billing MCP returned an invalid Tool name")
        annotations = cls._as_dict(cls._field(raw_tool, "annotations")) or {}
        read_only = annotations.get("readOnlyHint", annotations.get("read_only_hint"))
        if read_only is not True:
            raise RuntimeError(f"Billing MCP Tool {remote_name} is not explicitly read-only")
        schema = cls._as_dict(cls._field(raw_tool, "inputSchema", "input_schema"))
        if not schema or schema.get("type") != "object":
            raise RuntimeError(f"Billing MCP Tool {remote_name} requires an object input schema")
        properties = schema.get("properties")
        if not isinstance(properties, dict) or not isinstance(properties.get("customer_id"), dict):
            raise RuntimeError(f"Billing MCP Tool {remote_name} must declare customer_id")
        required = schema.get("required") or []
        if "customer_id" not in required:
            raise RuntimeError(f"Billing MCP Tool {remote_name} must require customer_id")
        agent_schema = dict(schema)
        agent_schema["properties"] = {key: value for key, value in properties.items() if key != "customer_id"}
        agent_schema["required"] = [key for key in required if key != "customer_id"]
        # The LLM must never pass unmodeled fields to the customer-scoped MCP.
        agent_schema["additionalProperties"] = False
        output_schema = cls._as_dict(cls._field(raw_tool, "outputSchema", "output_schema"))
        return DiscoveredBillingTool(
            remote_name=remote_name,
            description=str(cls._field(raw_tool, "description") or "").strip(),
            input_schema=agent_schema,
            output_schema=output_schema,
        )

    @classmethod
    def _validate_discovered_result(cls, remote_name: str, result: Any) -> dict[str, Any]:
        local_name = KNOWN_BILLING_RESULT_CONTRACTS.get(remote_name)
        if local_name:
            return cls._validate_result(local_name, result)
        if not isinstance(result, dict):
            raise RuntimeError(f"Billing MCP {remote_name} returned a non-object result")
        return result

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
                except json.JSONDecodeError as exc:
                    raise RuntimeError("Billing MCP result must contain JSON structured content") from exc
        return result

    @classmethod
    def _validate_result(cls, local_tool_name: str, result: Any) -> dict[str, Any]:
        if not isinstance(result, dict) or not isinstance(result.get("found"), bool):
            raise RuntimeError(f"Billing MCP {local_tool_name} returned an invalid result contract")
        if local_tool_name == "query_plan":
            cls._require_exact_keys(
                result,
                {"found", "reason", "subscriptionStatus", "planId", "planName", "qpsLimit", "monthlyQuota", "basePrice", "overagePricePerCall"},
            )
            if not result["found"] and not isinstance(result.get("reason"), str):
                raise RuntimeError("Billing MCP query_plan not-found result requires reason")
            if result["found"]:
                cls._require_fields(
                    result,
                    {"subscriptionStatus", "planId", "planName", "qpsLimit", "monthlyQuota", "basePrice", "overagePricePerCall"},
                    "Billing MCP query_plan result",
                )
            return result
        if local_tool_name == "query_usage":
            cls._require_exact_keys(result, {"found", "usage"})
            usage = result.get("usage")
            if not isinstance(usage, list):
                raise RuntimeError("Billing MCP query_usage result requires usage list")
            for item in usage:
                if not isinstance(item, dict):
                    raise RuntimeError("Billing MCP query_usage contains an invalid usage item")
                cls._require_exact_keys(item, {"month", "callCount", "overageCount"})
                cls._require_fields(item, {"month", "callCount", "overageCount"}, "Billing MCP usage item")
            return result
        if local_tool_name == "query_bill":
            cls._require_exact_keys(result, {"found", "bills"})
            bills = result.get("bills")
            if not isinstance(bills, list):
                raise RuntimeError("Billing MCP query_bill result requires bills list")
            for item in bills:
                if not isinstance(item, dict):
                    raise RuntimeError("Billing MCP query_bill contains an invalid invoice")
                cls._require_exact_keys(item, {"invoiceId", "month", "amount", "status", "items"})
                cls._require_fields(item, {"invoiceId", "month", "amount", "status", "items"}, "Billing MCP invoice")
                if not isinstance(item.get("items"), dict):
                    raise RuntimeError("Billing MCP invoice items must be an object")
            return result
        raise RuntimeError(f"Unsupported billing MCP tool: {local_tool_name}")

    @staticmethod
    def _require_exact_keys(value: dict[str, Any], allowed: set[str]) -> None:
        unknown = set(value) - allowed
        if unknown:
            raise RuntimeError(f"Billing MCP result contains unsupported fields: {', '.join(sorted(unknown))}")

    @staticmethod
    def _require_fields(value: dict[str, Any], required: set[str], context: str) -> None:
        missing = required - set(value)
        if missing:
            raise RuntimeError(f"{context} is missing required fields: {', '.join(sorted(missing))}")


billing_mcp_adapter = BillingMCPAdapter()
