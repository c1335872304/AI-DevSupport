from __future__ import annotations

from contextlib import asynccontextmanager
import asyncio
import logging
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__

from app.api.router import api_router
from app.core.config import get_settings
from app.core.deps import protected_ops_user
from app.core.redaction import redact_text
from app.db.init_db import init_db
from app.db.session import engine
from app.api.websocket.chat import router as websocket_router
from app.knowledge.elasticsearch import elasticsearch_service
from app.tools.mcp.billing import billing_mcp_adapter
from app.tools.registry import tool_registry
from app.documents.jobs import maintenance_loop
from app.agent.generation import generation_runtime
from app.agent.graph.engine import LANGGRAPH_AVAILABLE, LANGGRAPH_ENGINE

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_runtime_safety()
    Path("./data").mkdir(parents=True, exist_ok=True)
    await init_db()
    app.state.interrupted_generations = await generation_runtime.recover_orphaned_states()
    generation_recovery_task = asyncio.create_task(generation_runtime.recovery_loop(), name="generation-recovery")
    billing_mcp_adapter.validate_configuration()
    index_task = asyncio.create_task(maintenance_loop(), name="index-maintenance")
    from app.diagnosis.execution import recovery_loop
    diagnostic_task = asyncio.create_task(recovery_loop(), name="diagnosis-recovery")
    app.state.resumed_processing_jobs = []
    privacy_task = None
    if settings.privacy_auto_maintenance_enabled:
        from app.privacy.maintenance import run_once

        async def privacy_loop() -> None:
            while True:
                try:
                    await run_once()
                except Exception:
                    logger.exception("[PRIVACY] scheduled maintenance failed")
                await asyncio.sleep(max(3600, settings.privacy_maintenance_interval_seconds))

        privacy_task = asyncio.create_task(privacy_loop(), name="privacy-maintenance")
        app.state.privacy_maintenance_task = privacy_task
    try:
        yield
    finally:
        generation_recovery_task.cancel()
        try:
            await generation_recovery_task
        except asyncio.CancelledError:
            pass
        diagnostic_task.cancel()
        try:
            await diagnostic_task
        except asyncio.CancelledError:
            pass
        index_task.cancel()
        try:
            await index_task
        except asyncio.CancelledError:
            pass
        if privacy_task and not privacy_task.done():
            privacy_task.cancel()
            try:
                await privacy_task
            except asyncio.CancelledError:
                pass
        await elasticsearch_service.close()
        await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="Python/FastAPI LangGraph AI customer-service Agent + RAG knowledge base",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"code": exc.status_code, "message": message})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("[HTTP 422] %s %s errors=%s", request.method, request.url.path, exc.errors())
    return JSONResponse(status_code=422, content={"code": 422, "message": "参数校验失败", "data": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("[HTTP 500] %s %s error=%s", request.method, request.url.path, redact_text(str(exc)))
    return JSONResponse(status_code=500, content={"code": 500, "message": "服务器内部错误，请稍后重试"})


app.include_router(api_router, prefix=settings.api_prefix)
app.include_router(websocket_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.app_name}


@app.get("/health/details")
async def health_details(_ops_user=Depends(protected_ops_user)):
    return {
        "status": "ok",
        "service": settings.app_name,
        "customerServiceWorkflow": "target",
        "workflowEngine": LANGGRAPH_ENGINE,
        "langGraphAvailable": LANGGRAPH_AVAILABLE,
        "searchBackend": settings.search_backend,
        "taskMode": settings.task_mode,
        "billingMcpEnabled": billing_mcp_adapter.enabled,
    }
