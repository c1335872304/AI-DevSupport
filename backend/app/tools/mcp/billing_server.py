from __future__ import annotations

"""Local, read-only Billing MCP Server for the Docker demo topology.

This server deliberately does not share the knowledge MCP registry. It exposes
only billing facts and is reachable only on the Compose network by default.
"""

import re

from app.db.session import SessionLocal
from app.support import billing

try:
    from mcp.server import MCPServer
    from mcp.types import ToolAnnotations
except ImportError as exc:  # pragma: no cover
    raise RuntimeError('MCP support requires the "mcp>=2,<3" package') from exc


mcp = MCPServer(
    "API Assistant Billing MCP",
    instructions=(
        "Read-only Billing MCP for the local API Assistant demo. "
        "It exposes plan, usage and invoice facts only; it never performs refunds, "
        "plan changes, cancellations or other writes."
    ),
)


def _customer_id(value: str) -> str:
    customer_id = str(value or "").strip()
    if not customer_id or len(customer_id) > 64:
        raise ValueError("customer_id must be a non-empty value up to 64 characters")
    return customer_id


def _month(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    month = str(value).strip()
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        raise ValueError("month must use YYYY-MM")
    return month


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
async def get_plan(customer_id: str) -> dict:
    """Read the current plan, QPS limit and quota for one customer."""
    async with SessionLocal() as db:
        return await billing.query_plan(db, _customer_id(customer_id))


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
async def get_usage(customer_id: str, month: str | None = None) -> dict:
    """Read monthly API usage and overage count for one customer."""
    async with SessionLocal() as db:
        return await billing.query_usage(db, _customer_id(customer_id), _month(month))


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
async def get_invoice(customer_id: str, month: str | None = None) -> dict:
    """Read invoice totals and itemized charges for one customer."""
    async with SessionLocal() as db:
        return await billing.query_bill(db, _customer_id(customer_id), _month(month))
