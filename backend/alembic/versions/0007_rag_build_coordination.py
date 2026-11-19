"""Durable RAG build coordination and lifecycle records."""

from alembic import op
import sqlalchemy as sa

revision = "0007_rag_build_coordination"
down_revision = "0006_llm_token_reservations"
branch_labels = None
depends_on = None


def upgrade():
    from app.db.models import DocumentRevision, EmbeddingAttempt, IndexBuild, IndexOutbox

    for table, columns in {
        "file_upload": [
            sa.Column("write_epoch", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("input_revision", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("lease_owner", sa.String(64)),
            sa.Column("lease_until", sa.DateTime()),
            sa.Column("deleted_at", sa.DateTime()),
        ],
        "processing_jobs": [sa.Column("lease_owner", sa.String(64)), sa.Column("lease_until", sa.DateTime())],
    }.items():
        existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}
        for column in columns:
            if column.name not in existing:
                op.add_column(table, column)
    for model in (DocumentRevision, IndexBuild, IndexOutbox, EmbeddingAttempt):
        model.__table__.create(bind=op.get_bind(), checkfirst=True)
    bind = op.get_bind()
    files = bind.execute(
        sa.text("SELECT id, active_vector_version FROM file_upload WHERE active_vector_version IS NOT NULL")
    ).all()
    for file_id, version in files:
        if not bind.execute(
            sa.text("SELECT build_id FROM index_builds WHERE build_id=:version"), {"version": version}
        ).first():
            bind.execute(
                IndexBuild.__table__.insert().values(
                    build_id=version,
                    file_id=file_id,
                    owner="migration",
                    epoch=0,
                    input_revision=0,
                    revision_id="legacy",
                    profile_id="legacy",
                    status="PUBLISHED",
                    manifest_json='{"migrated": true}',
                    completed_chunks=0,
                )
            )


def downgrade():
    # Roll back only after stopping new workers; old workers do not enforce fencing.
    for table in ("embedding_attempts", "index_outbox", "index_builds", "document_revisions"):
        op.drop_table(table)
    for table, columns in {
        "processing_jobs": ["lease_until", "lease_owner"],
        "file_upload": ["deleted_at", "lease_until", "lease_owner", "input_revision", "write_epoch"],
    }.items():
        with op.batch_alter_table(table) as batch:
            for column in columns:
                batch.drop_column(column)
