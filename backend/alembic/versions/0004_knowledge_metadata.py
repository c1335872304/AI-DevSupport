"""Customer-service knowledge metadata for filtered Hybrid RAG.

Revision ID: 0004_knowledge_metadata
Revises: 0003_api_billing
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004_knowledge_metadata"
down_revision = "0003_api_billing"
branch_labels = None
depends_on = None

COLUMNS = [
    ("knowledge_category", sa.String(255)),
    ("knowledge_product", sa.String(255)),
    ("knowledge_region", sa.String(255)),
    ("knowledge_channel", sa.String(255)),
    ("knowledge_effective_date", sa.Date()),
    ("knowledge_version", sa.String(255)),
    ("knowledge_error_code", sa.String(255)),
    ("knowledge_plan", sa.String(255)),
]


def upgrade() -> None:
    with op.batch_alter_table("file_upload") as batch:
        for name, type_ in COLUMNS:
            batch.add_column(sa.Column(name, type_, nullable=True))
            batch.create_index(f"ix_file_upload_{name}", [name], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("file_upload") as batch:
        for name, _ in reversed(COLUMNS):
            batch.drop_index(f"ix_file_upload_{name}")
            batch.drop_column(name)
