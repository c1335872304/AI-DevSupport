"""Persist diagnostic cases, generation links, evidence and guarded transitions."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME

revision = "0014_diagnosis_sessions"
down_revision = "0013_source_document_revisions"
branch_labels = None
depends_on = None


def upgrade():
    timestamp_type = sa.DateTime().with_variant(DATETIME(fsp=6), "mysql")
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    definitions = {
        "diagnosis_sessions": [
            sa.Column("diagnosis_id", sa.String(64), primary_key=True),
            sa.Column("user_id", sa.String(64), nullable=False, index=True),
            sa.Column("conversation_id", sa.String(64), nullable=False, index=True),
            sa.Column("app_id", sa.String(64)),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("symptom", sa.Text(), nullable=False),
            *[sa.Column(name, sa.Text(), nullable=False) for name in
              ["entities_json", "entity_sources_json", "candidates_json", "missing_fields_json"]],
            sa.Column("next_action", sa.String(500), nullable=False),
            sa.Column("end_reason", sa.String(255)),
            sa.Column("last_generation_id", sa.String(64), nullable=False),
            sa.Column("revision", sa.Integer(), nullable=False),
            sa.Column("created_at", timestamp_type, nullable=False),
            sa.Column("updated_at", timestamp_type, nullable=False),
        ],
        "diagnosis_turns": [
            sa.Column("generation_id", sa.String(64), primary_key=True),
            sa.Column("diagnosis_id", sa.String(64), nullable=False, index=True),
            sa.Column("finished", sa.Boolean(), nullable=False),
            sa.Column("created_at", timestamp_type, nullable=False),
        ],
        "diagnosis_evidence": [
            sa.Column("evidence_id", sa.String(64), primary_key=True),
            sa.Column("diagnosis_id", sa.String(64), nullable=False, index=True),
            sa.Column("generation_id", sa.String(64), nullable=False, index=True),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("created_at", timestamp_type, nullable=False),
        ],
        "diagnosis_transitions": [
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("diagnosis_id", sa.String(64), nullable=False, index=True),
            sa.Column("generation_id", sa.String(64), nullable=False),
            sa.Column("from_status", sa.String(32)),
            sa.Column("to_status", sa.String(32), nullable=False),
            sa.Column("reason", sa.String(255), nullable=False),
            sa.Column("evidence_ids_json", sa.Text(), nullable=False),
            sa.Column("created_at", timestamp_type, nullable=False),
        ],
    }
    for name, columns in definitions.items():
        if name not in tables:
            op.create_table(name, *columns)


def downgrade():
    for name in ["diagnosis_transitions", "diagnosis_evidence", "diagnosis_turns", "diagnosis_sessions"]:
        op.drop_table(name)
