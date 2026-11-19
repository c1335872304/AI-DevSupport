from fastapi import APIRouter, Depends, Query

from app.core.deps import current_user
from app.core.response import ok
from app.db.models import User

router = APIRouter(prefix="/route", tags=["route"])

# Keep this in sync with frontend/src/router/elegant/routes.ts.  The old endpoint
# returned true for every arbitrary string, which made the API a fake-success stub.
KNOWN_ROUTE_NAMES = {
    "root", "not-found", "403", "404", "500", "chat", "chat-history",
    "iframe-page", "knowledge-base", "login", "model-provider",
    "org-tag", "personal-center", "recharge", "recharge-manage",
    "usage-monitor", "user",
}


@router.get("/getConstantRoutes")
async def constant_routes():
    return ok([])


@router.get("/getUserRoutes")
async def user_routes(user: User = Depends(current_user)):
    return ok({"routes": [], "home": "chat"})


@router.get("/isRouteExist")
async def route_exists(routeName: str = Query(...)):
    return ok(routeName in KNOWN_ROUTE_NAMES)
