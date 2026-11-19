"""Separate stable document handles from source checksums and active source objects."""

from alembic import op
import sqlalchemy as sa

revision = "0013_source_document_revisions"
down_revision = "0012_index_idempotency_key"
branch_labels = None
depends_on = None


def upgrade():
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("file_upload")}
    for col in [
        sa.Column("source_md5", sa.String(32)),
        sa.Column("active_source_key", sa.String(1000)),
        sa.Column("active_file_name", sa.String(255)),
    ]:
        if col.name not in existing:
            op.add_column("file_upload", col)


def downgrade():
    with op.batch_alter_table("file_upload") as batch:
        for name in ["source_md5", "active_source_key", "active_file_name"]:
            batch.drop_column(name)
