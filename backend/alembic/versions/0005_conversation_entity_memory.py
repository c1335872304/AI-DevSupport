"""Persist structured conversation entities for multi-turn routing.

Revision ID: 0005_conversation_entity_memory
Revises: 0004_knowledge_metadata
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0005_conversation_entity_memory"
down_revision = "0004_knowledge_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Development startup can add this column through create_all's lightweight
    # compatibility migration before Alembic is run.
    if any(column["name"] == "collected_entities_json" for column in sa.inspect(op.get_bind()).get_columns("conversation_sessions")):
        return
    with op.batch_alter_table("conversation_sessions") as batch:
        batch.add_column(sa.Column("collected_entities_json", sa.Text(), nullable=False, server_default="{}"))


def downgrade() -> None:
    if not any(column["name"] == "collected_entities_json" for column in sa.inspect(op.get_bind()).get_columns("conversation_sessions")):
        return
    with op.batch_alter_table("conversation_sessions") as batch:
        batch.drop_column("collected_entities_json")
