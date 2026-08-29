from __future__ import annotations

from app.db.models import User


def user_orgs(user: User) -> set[str]:
    """Return normalized organization memberships without importing request/DB dependencies."""
    return {x.strip() for x in (user.org_tags or "").split(",") if x.strip()}
