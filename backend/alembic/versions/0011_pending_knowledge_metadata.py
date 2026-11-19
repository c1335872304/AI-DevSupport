"""Keep desired knowledge metadata separate until its build is published."""

from alembic import op
import sqlalchemy as sa

revision = "0011_pending_knowledge_metadata"
down_revision = "0010_index_request_revision"
branch_labels = None
depends_on = None


def upgrade():
    if "desired_metadata_json" not in {
        c["name"] for c in sa.inspect(op.get_bind()).get_columns("file_upload")
    }:
        op.add_column("file_upload", sa.Column("desired_metadata_json", sa.Text()))


def downgrade():
    with op.batch_alter_table("file_upload") as batch:
        batch.drop_column("desired_metadata_json")
