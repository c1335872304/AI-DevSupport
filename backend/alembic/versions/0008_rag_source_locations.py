"""Document applicability end date and source block locations."""

from alembic import op
import sqlalchemy as sa

revision = "0008_rag_source_locations"
down_revision = "0007_rag_build_coordination"
branch_labels = None
depends_on = None


def upgrade():
    fields = {
        "file_upload": [
            sa.Column("knowledge_effective_until", sa.Date()),
            sa.Column("knowledge_superseded_by", sa.String(255)),
        ],
        "document_vectors": [sa.Column("location_json", sa.Text())],
        "document_parent_chunks": [sa.Column("location_json", sa.Text())],
    }
    for table, columns in fields.items():
        existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}
        for column in columns:
            if column.name not in existing:
                op.add_column(table, column)


def downgrade():
    for table, names in {
        "file_upload": ["knowledge_effective_until", "knowledge_superseded_by"],
        "document_vectors": ["location_json"],
        "document_parent_chunks": ["location_json"],
    }.items():
        with op.batch_alter_table(table) as batch:
            for name in names:
                batch.drop_column(name)
