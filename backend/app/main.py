from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app import __version__

from app.api.router import api_router
from app.core.config import get_settings
from app.core.observability import HTTP_LATENCY, HTTP_REQUESTS, prometheus_payload, setup_otel
from app.db.init_db import init_db
from app.api.websocket.chat import router as websocket_router
from app.tools.mcp.client import register_configured_mcp_tools
from app.tools.registry import tool_registry
from app.documents.jobs import resume_processing_jobs
from app.agent.generation import generation_runtime
from app.agent.graph.engine import LANGGRAPH_AVAILABLE, LANGGRAPH_ENGINE

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_runtime_safety()
    Path("./data").mkdir(parents=True, exist_ok=True)
    await init_db()
    app.state.interrupted_generations = await generation_runtime.recover_orphaned_states()
    app.state.external_mcp_tools = await register_configured_mcp_tools(tool_registry)
    app.state.resumed_processing_jobs = await resume_processing_jobs()
    yield


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="Python/FastAPI LangGraph AI customer-service Agent + RAG knowledge base",
    lifespan=lifespan,
)
setup_otel(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    import time
    started = time.monotonic()
    response = await call_next(request)
    route = request.scope.get("route")
    path = getattr(route, "path", None) or request.url.path
    if HTTP_REQUESTS is not None:
        HTTP_REQUESTS.labels(method=request.method, path=path, status=str(response.status_code)).inc()
    if HTTP_LATENCY is not None:
        HTTP_LATENCY.labels(method=request.method, path=path).observe(time.monotonic() - started)
    return response

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"code": exc.status_code, "message": message})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"code": 422, "message": "参数校验失败", "data": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"code": 500, "message": str(exc) or "Internal server error"})


app.include_router(api_router, prefix=settings.api_prefix)
app.include_router(websocket_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.app_name}


@app.get("/health/details")
async def health_details():
    return {
        "status": "ok",
        "service": settings.app_name,
        "agentEnabled": settings.agent_enabled,
        "workflowEngine": LANGGRAPH_ENGINE,
        "langGraphAvailable": LANGGRAPH_AVAILABLE,
        "searchBackend": settings.search_backend,
        "taskMode": settings.task_mode,
        "externalMcpTools": list(getattr(app.state, "external_mcp_tools", [])),
    }


@app.get("/metrics")
async def metrics():
    if not settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="Metrics disabled")
    payload, content_type = prometheus_payload()
    return Response(content=payload, media_type=content_type)
