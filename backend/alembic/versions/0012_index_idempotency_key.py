"""Client idempotency keys for explicit index rebuild requests."""

from alembic import op
import sqlalchemy as sa

revision = "0012_index_idempotency_key"
down_revision = "0011_pending_knowledge_metadata"
branch_labels = None
depends_on = None


def upgrade():
    if "request_key" not in {c["name"] for c in sa.inspect(op.get_bind()).get_columns("processing_jobs")}:
        op.add_column("processing_jobs", sa.Column("request_key", sa.String(64), nullable=True))
    if "uq_processing_request_key" not in {
        i["name"] for i in sa.inspect(op.get_bind()).get_indexes("processing_jobs")
    }:
        op.create_index("uq_processing_request_key", "processing_jobs", ["request_key"], unique=True)


def downgrade():
    op.drop_index("uq_processing_request_key", table_name="processing_jobs")
    with op.batch_alter_table("processing_jobs") as batch:
        batch.drop_column("request_key")
