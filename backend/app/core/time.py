"""Time helpers shared by persistence and business logic."""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return a naive UTC datetime for existing database columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
