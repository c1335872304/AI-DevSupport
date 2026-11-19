from __future__ import annotations

from app.support import api_diagnostics
from app.tools.base import BaseTool


class QueryCallLogTool(BaseTool):
    name="query_call_log"; description="Query the authenticated customer's API call log by request_id for HTTP status, error code, endpoint and latency."
    input_schema={"type":"object","properties":{"request_id":{"type":"string","minLength":3,"maxLength":64}},"required":["request_id"],"additionalProperties":False}
    required_scopes=frozenset({"tools:read"}); resource_group="api-support-read"
    async def execute(self, context, arguments):
        from app.db.session import SessionLocal
        async with SessionLocal() as db: return await api_diagnostics.query_call_log(db,str(context.user.id),str(arguments["request_id"]))

class QueryApiKeyStatusTool(BaseTool):
    name="query_api_key_status"; description="Query API Key status/expiry for the authenticated customer by app_id or api_key_id. Returned keys are masked only."
    input_schema={"type":"object","properties":{"app_id":{"type":"string","maxLength":64},"api_key_id":{"type":"string","maxLength":64}},"additionalProperties":False}
    required_scopes=frozenset({"tools:read"}); resource_group="api-support-read"
    dependencies=("query_call_log",)
    async def execute(self, context, arguments):
        from app.db.session import SessionLocal
        async with SessionLocal() as db: return await api_diagnostics.query_api_key_status(db,str(context.user.id),app_id=arguments.get("app_id"),api_key_id=arguments.get("api_key_id"))

class QueryRecentCallStatsTool(BaseTool):
    name="query_recent_call_stats"; description="Query status distribution with explicit UTC bounds. Default current window ends now. Historical incident requires request_id; explicit requires start_at/end_at. app_id limits the application; customer-wide counts do not prove one application state."
    input_schema={"type":"object","properties":{
        "endpoint":{"type":"string","maxLength":255},
        "app_id":{"type":"string","maxLength":64},
        "minutes":{"type":"integer","minimum":1,"maximum":1440,"default":60},
        "window":{"type":"string","enum":["current","incident","explicit"],"default":"current"},
        "request_id":{"type":"string","maxLength":64},
        "start_at":{"type":"string","format":"date-time"},
        "end_at":{"type":"string","format":"date-time"}},"additionalProperties":False}
    required_scopes=frozenset({"tools:read"}); resource_group="api-support-read"
    dependencies=("query_call_log",)
    async def execute(self, context, arguments):
        from app.db.session import SessionLocal
        async with SessionLocal() as db: return await api_diagnostics.query_recent_call_stats(db,str(context.user.id),endpoint=arguments.get("endpoint"), app_id=arguments.get("app_id"), minutes=int(arguments.get("minutes") or 60), window=arguments.get("window", "current"), request_id=arguments.get("request_id"), start_at=arguments.get("start_at"), end_at=arguments.get("end_at"))

class QueryErrorCodeTool(BaseTool):
    name="query_error_code"; description="Look up a known platform API error code and return its cause and deterministic repair steps."
    input_schema={"type":"object","properties":{"code":{"type":"string","minLength":2,"maxLength":64}},"required":["code"],"additionalProperties":False}
    required_scopes=frozenset({"tools:read"}); resource_group="api-support-read"
    dependencies=("query_call_log",)
    async def execute(self, context, arguments):
        from app.db.session import SessionLocal
        async with SessionLocal() as db: return await api_diagnostics.query_error_code(db,str(arguments["code"]))


class QueryRequestObservationTool(BaseTool):
    name = "query_request_observation"
    description = "Query sanitized at-call observations of the separate Demo API by verified request_id. Never queries vendor accounts."
    input_schema = {"type": "object", "properties": {"request_id": {"type": "string", "minLength": 3, "maxLength": 64}}, "required": ["request_id"], "additionalProperties": False}
    required_scopes = frozenset({"tools:read"})
    resource_group = "api-support-read"
    dependencies = ("query_call_log",)

    async def execute(self, context, arguments):
        from app.db.session import SessionLocal
        async with SessionLocal() as db:
            return await api_diagnostics.query_request_observation(db, str(context.user.id), arguments["request_id"])
