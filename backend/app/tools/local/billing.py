from __future__ import annotations
from app.tools.base import BaseTool
from app.support import billing

class QueryPlanTool(BaseTool):
    name="query_plan"; description="Query the authenticated customer's current API plan, QPS limit, monthly quota and overage price."
    input_schema={"type":"object","properties":{},"additionalProperties":False}; required_scopes=frozenset({"tools:read"}); resource_group="billing-read"
    async def execute(self, context, arguments):
        from app.db.session import SessionLocal
        async with SessionLocal() as db: return await billing.query_plan(db,str(context.user.id))

class QueryUsageTool(BaseTool):
    name="query_usage"; description="Query the authenticated customer's API usage and overage count for a month (YYYY-MM) or all months."
    input_schema={"type":"object","properties":{"month":{"type":"string","pattern":"^\\d{4}-\\d{2}$"}},"additionalProperties":False}; required_scopes=frozenset({"tools:read"}); resource_group="billing-read"
    async def execute(self, context, arguments):
        from app.db.session import SessionLocal
        async with SessionLocal() as db: return await billing.query_usage(db,str(context.user.id),arguments.get("month"))

class QueryBillTool(BaseTool):
    name="query_bill"; description="Query the authenticated customer's invoice amount, status and itemized charges for a month (YYYY-MM) or all months."
    input_schema={"type":"object","properties":{"month":{"type":"string","pattern":"^\\d{4}-\\d{2}$"}},"additionalProperties":False}; required_scopes=frozenset({"tools:read"}); resource_group="billing-read"
    async def execute(self, context, arguments):
        from app.db.session import SessionLocal
        async with SessionLocal() as db: return await billing.query_bill(db,str(context.user.id),arguments.get("month"))
