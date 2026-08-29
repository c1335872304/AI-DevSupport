"""PaiSmart production runtime schema.

Revision ID: 0001_v8
Revises: None
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.db.models import Base

revision = "0001_v8"
down_revision = None
branch_labels = None
depends_on = None


def _columns(inspector, table: str) -> set[str]:
    return {item["name"] for item in inspector.get_columns(table)} if table in inspector.get_table_names() else set()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # A fresh install can use model metadata as the baseline; existing installs are
    # upgraded below without dropping user data.
    if not tables:
        Base.metadata.create_all(bind=bind)
        return

    if "users" in tables and "token_version" not in _columns(inspector, "users"):
        with op.batch_alter_table("users") as batch:
            batch.add_column(sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))

    if "file_upload" in tables and "active_vector_version" not in _columns(inspector, "file_upload"):
        with op.batch_alter_table("file_upload") as batch:
            batch.add_column(sa.Column("active_vector_version", sa.String(length=64), nullable=True))
            batch.create_index("ix_file_upload_active_vector_version", ["active_vector_version"])
        op.execute(sa.text("UPDATE file_upload SET active_vector_version='legacy' WHERE active_vector_version IS NULL"))

    if "document_vectors" in tables and "vector_version" not in _columns(inspector, "document_vectors"):
        with op.batch_alter_table("document_vectors") as batch:
            batch.add_column(sa.Column("vector_version", sa.String(length=64), nullable=False, server_default="legacy"))
            batch.create_index("ix_document_vectors_vector_version", ["vector_version"])

    if "document_parent_chunks" in tables and "vector_version" not in _columns(inspector, "document_parent_chunks"):
        uniques = {u.get("name") for u in inspector.get_unique_constraints("document_parent_chunks")}
        with op.batch_alter_table("document_parent_chunks") as batch:
            if "uk_parent_chunk_file_user_id" in uniques:
                batch.drop_constraint("uk_parent_chunk_file_user_id", type_="unique")
            batch.add_column(sa.Column("vector_version", sa.String(length=64), nullable=False, server_default="legacy"))
            batch.create_index("ix_document_parent_chunks_vector_version", ["vector_version"])
            batch.create_unique_constraint("uk_parent_chunk_file_user_ver_id", ["file_md5", "user_id", "vector_version", "parent_chunk_id"])

    # Audit/config tables are check-first to keep this migration safe for
    # installations that used create_all during development before adopting Alembic.
    for name in ["chat_feedback", "agent_runs", "tool_executions", "rate_limit_policies", "mcp_access_tokens", "processing_jobs"]:
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)


def downgrade() -> None:
    # Data-destructive downgrade is intentionally limited to tables added by this revision.
    bind = op.get_bind()
    for name in ["processing_jobs", "mcp_access_tokens", "rate_limit_policies", "tool_executions", "agent_runs", "chat_feedback"]:
        Base.metadata.tables[name].drop(bind=bind, checkfirst=True)
