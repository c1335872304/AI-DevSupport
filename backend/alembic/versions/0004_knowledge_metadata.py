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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    # Recover databases initialized by the pre-Alembic baseline, where only
    # the alembic_version row existed and this table was never created.
    if "file_upload" not in inspector.get_table_names():
        from app.db.models import Base

        Base.metadata.create_all(bind=bind)
        return
    existing_columns = {column["name"] for column in inspector.get_columns("file_upload")}
    existing_indexes = {index["name"] for index in inspector.get_indexes("file_upload")}
    with op.batch_alter_table("file_upload") as batch:
        for name, type_ in COLUMNS:
            if name not in existing_columns:
                batch.add_column(sa.Column(name, type_, nullable=True))
            if f"ix_file_upload_{name}" not in existing_indexes:
                batch.create_index(f"ix_file_upload_{name}", [name], unique=False)


def downgrade() -> None:
    if "file_upload" not in sa.inspect(op.get_bind()).get_table_names():
        return
    with op.batch_alter_table("file_upload") as batch:
        for name, _ in reversed(COLUMNS):
            batch.drop_index(f"ix_file_upload_{name}")
            batch.drop_column(name)
