from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.tools.mcp.billing import BillingMCPAdapter


def _tool(name: str, *, read_only: bool = True):
    return SimpleNamespace(
        name=name,
        description=f"{name} description",
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "month": {"type": "string"},
            },
            "required": ["customer_id"],
        },
        annotations=SimpleNamespace(read_only_hint=read_only),
    )


@pytest.mark.asyncio
async def test_billing_mcp_discovers_read_only_tools_and_hides_customer_id(monkeypatch):
    import app.tools.mcp.billing as billing_module

    adapter = BillingMCPAdapter()
    monkeypatch.setattr(adapter.settings, "billing_mcp_enabled", True)
    monkeypatch.setattr(adapter.settings, "billing_mcp_url", "http://billing-mcp:8011/mcp")

    async def fake_list_tools(self):
        return [_tool("get_plan"), _tool("get_invoice")]

    captured = {}

    async def fake_call(self, name, arguments):
        captured.update(name=name, arguments=arguments)
        return {"structuredContent": {"found": True, "bills": []}}

    monkeypatch.setattr(billing_module.MCPRemoteClient, "list_tools", fake_list_tools)
    monkeypatch.setattr(billing_module.MCPRemoteClient, "call_tool", fake_call)
    tools = await adapter.discover_tools()

    assert [tool.name for tool in tools] == ["mcp__billing__get_plan", "mcp__billing__get_invoice"]
    invoice = tools[1]
    assert "customer_id" not in invoice.input_schema["properties"]
    assert invoice.input_schema["additionalProperties"] is False
    context = SimpleNamespace(user=SimpleNamespace(id=42))
    assert await invoice.execute(context, {"month": "2026-08"}) == {"found": True, "bills": []}
    assert captured == {"name": "get_invoice", "arguments": {"month": "2026-08", "customer_id": "42"}}


@pytest.mark.asyncio
async def test_billing_mcp_rejects_writable_discovered_tool(monkeypatch):
    import app.tools.mcp.billing as billing_module

    adapter = BillingMCPAdapter()
    monkeypatch.setattr(adapter.settings, "billing_mcp_enabled", True)
    monkeypatch.setattr(adapter.settings, "billing_mcp_url", "http://billing-mcp:8011/mcp")

    async def fake_list_tools(self):
        return [_tool("change_plan", read_only=False)]

    monkeypatch.setattr(billing_module.MCPRemoteClient, "list_tools", fake_list_tools)
    with pytest.raises(RuntimeError, match="not explicitly read-only"):
        await adapter.discover_tools()


def test_billing_mcp_rejects_unknown_result_fields():
    with pytest.raises(RuntimeError, match="unsupported fields"):
        BillingMCPAdapter._validate_result("query_bill", {"found": True, "bills": [], "raw": "secret"})


def test_billing_mcp_rejects_missing_endpoint(monkeypatch):
    adapter = BillingMCPAdapter()
    monkeypatch.setattr(adapter.settings, "billing_mcp_enabled", True)
    with pytest.raises(RuntimeError, match="BILLING_MCP_URL"):
        adapter.validate_configuration()
