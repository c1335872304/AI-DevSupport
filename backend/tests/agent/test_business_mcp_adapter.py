from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.tools.mcp.business import BusinessMCPAdapter


def test_business_mcp_mapping_keeps_stable_local_tool_names(monkeypatch):
    adapter = BusinessMCPAdapter()
    monkeypatch.setattr(adapter.settings, "business_mcp_tool_map_json", json.dumps({
        "query_bill": {"tool": "get_invoice", "userArgument": "customer_id"},
        "query_error_code": {"tool": "lookup_error", "userArgument": None},
    }))
    route = adapter.route_for("query_bill")
    assert route.remote_tool == "get_invoice"
    assert route.user_argument == "customer_id"
    route = adapter.route_for("query_error_code")
    assert route.remote_tool == "lookup_error"
    assert route.user_argument is None


def test_business_mcp_default_mapping_uses_same_remote_name(monkeypatch):
    adapter = BusinessMCPAdapter()
    monkeypatch.setattr(adapter.settings, "business_mcp_tool_map_json", "{}")
    monkeypatch.setattr(adapter.settings, "business_mcp_default_user_argument", "customer_id")
    route = adapter.route_for("query_usage")
    assert route.remote_tool == "query_usage"
    assert route.user_argument == "customer_id"


def test_business_mcp_unwraps_structured_content():
    payload = {"structuredContent": {"month": "2026-08", "amount": 424}}
    assert BusinessMCPAdapter._unwrap_result(payload) == {"month": "2026-08", "amount": 424}

@pytest.mark.asyncio
async def test_business_mcp_call_injects_customer_context_and_maps_remote_tool(monkeypatch):
    import app.tools.mcp.business as business_module

    adapter = BusinessMCPAdapter()
    monkeypatch.setattr(adapter.settings, "business_tool_backend", "mcp")
    monkeypatch.setattr(adapter.settings, "business_mcp_server", "business")
    monkeypatch.setattr(adapter.settings, "business_mcp_tool_map_json", json.dumps({
        "query_bill": {"tool": "get_invoice", "userArgument": "customer_id"}
    }))
    fake_server = SimpleNamespace(name="business")
    monkeypatch.setattr(business_module, "get_remote_server_config", lambda name: fake_server)

    captured = {}

    async def fake_call(self, name, arguments):
        captured["name"] = name
        captured["arguments"] = arguments
        return {"structuredContent": {"amount": 424}}

    monkeypatch.setattr(business_module.MCPRemoteClient, "call_tool", fake_call)
    context = SimpleNamespace(user=SimpleNamespace(id=42))
    result = await adapter.call("query_bill", context, {"month": "2026-08"})
    assert captured == {"name": "get_invoice", "arguments": {"month": "2026-08", "customer_id": "42"}}
    assert result == {"amount": 424}
