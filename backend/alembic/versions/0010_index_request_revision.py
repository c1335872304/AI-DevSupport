"""Bind processing requests to their expected input revision."""

from alembic import op
import sqlalchemy as sa

revision = "0010_index_request_revision"
down_revision = "0009_embedding_request_ids"
branch_labels = None
depends_on = None


def upgrade():
    if "input_revision" not in {c["name"] for c in sa.inspect(op.get_bind()).get_columns("processing_jobs")}:
        op.add_column(
            "processing_jobs", sa.Column("input_revision", sa.Integer(), nullable=False, server_default="0")
        )


def downgrade():
    with op.batch_alter_table("processing_jobs") as batch:
        batch.drop_column("input_revision")
