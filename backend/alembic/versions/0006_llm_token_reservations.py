"""Add durable LLM token reservations for precharge and settlement."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0006_llm_token_reservations"
down_revision = "0005_conversation_entity_memory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "llm_token_reservations" not in inspector.get_table_names():
        op.create_table(
            "llm_token_reservations",
            sa.Column("generation_id", sa.String(length=64), primary_key=True),
            sa.Column("user_id", sa.String(length=64), nullable=False),
            sa.Column("reserved_tokens", sa.BigInteger(), nullable=False),
            sa.Column("settled_tokens", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="RESERVED"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_llm_token_reservations_user_id", "llm_token_reservations", ["user_id"])
        op.create_index("ix_llm_token_reservations_status", "llm_token_reservations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_llm_token_reservations_status", table_name="llm_token_reservations")
    op.drop_index("ix_llm_token_reservations_user_id", table_name="llm_token_reservations")
    op.drop_table("llm_token_reservations")
