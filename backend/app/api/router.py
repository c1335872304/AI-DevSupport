"""HTTP router composition.

Transport composition lives here so ``app.main`` only owns application lifecycle,
middleware, and process-level startup/shutdown concerns.
"""

from fastapi import APIRouter

from app.api.v1 import admin, auth, chat, conversations, documents, recharge, routes, search, support, upload, users

api_router = APIRouter()

for router in (
    auth.router,
    users.router,
    upload.router,
    documents.router,
    search.router,
    conversations.router,
    chat.router,
    support.router,
    admin.router,
    recharge.router,
    routes.router,
):
    api_router.include_router(router)
