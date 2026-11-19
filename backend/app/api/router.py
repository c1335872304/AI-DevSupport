"""HTTP router composition.

Transport composition lives here so ``app.main`` only owns application lifecycle,
middleware, and process-level startup/shutdown concerns.
"""

from fastapi import APIRouter

from app.api.v1 import admin, auth, chat, conversations, documents, recharge, routes, search, support, upload, users
from app.api.v1.refund_preview import discovery_router as approval_discovery_router
from app.api.v1.refund_preview import router as refund_preview_router

api_router = APIRouter()

from app.api.v1.provider_usage import router as provider_usage_router
api_router.include_router(provider_usage_router)

from app.api.v1.diagnoses import router as diagnosis_router
api_router.include_router(diagnosis_router)

for router in (
    auth.router,
    users.router,
    upload.router,
    documents.router,
    search.router,
    conversations.router,
    chat.router,
    support.router,
    refund_preview_router,
    approval_discovery_router,
    admin.router,
    recharge.router,
    routes.router,
):
    api_router.include_router(router)
