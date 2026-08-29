from __future__ import annotations
from app.tools.base import BaseTool, ToolExecutionContext
from app.tools.mcp.business import business_mcp_adapter
from app.support import api_diagnostics

class QueryCallLogTool(BaseTool):
    name="query_call_log"; description="Query the authenticated customer's API call log by request_id for HTTP status, error code, endpoint and latency."
    input_schema={"type":"object","properties":{"request_id":{"type":"string","minLength":3,"maxLength":64}},"required":["request_id"],"additionalProperties":False}
    required_scopes=frozenset({"tools:read"}); resource_group="api-support-read"
    async def execute(self, context, arguments):
        if business_mcp_adapter.enabled:
            return await business_mcp_adapter.call(self.name, context, arguments)
        from app.db.session import SessionLocal
        async with SessionLocal() as db: return await api_diagnostics.query_call_log(db,str(context.user.id),str(arguments["request_id"]))

class QueryApiKeyStatusTool(BaseTool):
    name="query_api_key_status"; description="Query API Key status/expiry for the authenticated customer by app_id or api_key_id. Returned keys are masked only."
    input_schema={"type":"object","properties":{"app_id":{"type":"string","maxLength":64},"api_key_id":{"type":"string","maxLength":64}},"additionalProperties":False}
    required_scopes=frozenset({"tools:read"}); resource_group="api-support-read"
    async def execute(self, context, arguments):
        if business_mcp_adapter.enabled:
            return await business_mcp_adapter.call(self.name, context, arguments)
        from app.db.session import SessionLocal
        async with SessionLocal() as db: return await api_diagnostics.query_api_key_status(db,str(context.user.id),app_id=arguments.get("app_id"),api_key_id=arguments.get("api_key_id"))

class QueryRecentCallStatsTool(BaseTool):
    name="query_recent_call_stats"; description="Query recent API status-code distribution for the authenticated customer; useful for diagnosing 429/rate-limit incidents."
    input_schema={"type":"object","properties":{"endpoint":{"type":"string","maxLength":255},"minutes":{"type":"integer","minimum":1,"maximum":1440,"default":60}},"additionalProperties":False}
    required_scopes=frozenset({"tools:read"}); resource_group="api-support-read"
    async def execute(self, context, arguments):
        if business_mcp_adapter.enabled:
            return await business_mcp_adapter.call(self.name, context, arguments)
        from app.db.session import SessionLocal
        async with SessionLocal() as db: return await api_diagnostics.query_recent_call_stats(db,str(context.user.id),endpoint=arguments.get("endpoint"),minutes=int(arguments.get("minutes") or 60))

class QueryErrorCodeTool(BaseTool):
    name="query_error_code"; description="Look up a known platform API error code and return its cause and deterministic repair steps."
    input_schema={"type":"object","properties":{"code":{"type":"string","minLength":2,"maxLength":64}},"required":["code"],"additionalProperties":False}
    required_scopes=frozenset({"tools:read"}); resource_group="api-support-read"
    async def execute(self, context, arguments):
        if business_mcp_adapter.enabled:
            return await business_mcp_adapter.call(self.name, context, arguments)
        from app.db.session import SessionLocal
        async with SessionLocal() as db: return await api_diagnostics.query_error_code(db,str(arguments["code"]))
