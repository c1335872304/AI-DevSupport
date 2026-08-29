"""Customer-service handoff tickets.

Revision ID: 0002_support
Revises: 0001_v8
"""
from __future__ import annotations

from alembic import op
from app.db.models import Base

revision = "0002_support"
down_revision = "0001_v8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.tables["support_handoffs"].create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.tables["support_handoffs"].drop(bind=bind, checkfirst=True)
