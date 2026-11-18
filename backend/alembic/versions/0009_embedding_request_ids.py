"""Provider request ids support usage reconciliation."""

from alembic import op
import sqlalchemy as sa

revision = "0009_embedding_request_ids"
down_revision = "0008_rag_source_locations"
branch_labels = None
depends_on = None


def upgrade():
    if "provider_request_ids_json" not in {
        c["name"] for c in sa.inspect(op.get_bind()).get_columns("embedding_attempts")
    }:
        op.add_column("embedding_attempts", sa.Column("provider_request_ids_json", sa.Text()))


def downgrade():
    with op.batch_alter_table("embedding_attempts") as batch:
        batch.drop_column("provider_request_ids_json")
