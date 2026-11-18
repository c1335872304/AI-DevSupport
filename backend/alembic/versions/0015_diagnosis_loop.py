"""Demo observations, durable diagnostic execution and case-scoped handoff identity."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME

revision = "0015_diagnosis_loop"
down_revision = "0014_diagnosis_sessions"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if "workflow_json" not in {c["name"] for c in sa.inspect(bind).get_columns("diagnosis_sessions")}:
        op.add_column(
            "diagnosis_sessions",
            sa.Column("workflow_json", sa.Text(), nullable=False, server_default=sa.text("('{}')")),
        )
    if "diagnosis_id" not in {c["name"] for c in sa.inspect(bind).get_columns("support_handoffs")}:
        op.add_column("support_handoffs", sa.Column("diagnosis_id", sa.String(64)))
        op.create_index("ix_support_handoffs_diagnosis_id", "support_handoffs", ["diagnosis_id"], unique=True)
    clock = sa.DateTime().with_variant(DATETIME(fsp=6), "mysql")
    if bind.dialect.name == "mysql":
        op.alter_column("support_api_call_logs", "created_at", type_=DATETIME(fsp=6), existing_nullable=False)
    tables = set(sa.inspect(bind).get_table_names())
    definitions = {
        "diagnosis_executions": [
            sa.Column("generation_id", sa.String(64), primary_key=True),
            sa.Column("diagnosis_id", sa.String(64), nullable=False, index=True),
            sa.Column("status", sa.String(24), nullable=False, index=True),
            sa.Column("context_json", sa.Text(), nullable=False),
            sa.Column("owner", sa.String(64)),
            sa.Column("lease_until", clock),
            sa.Column("epoch", sa.Integer(), nullable=False),
            sa.Column("attempts_used", sa.Integer(), nullable=False),
            sa.Column("error", sa.String(500)),
            sa.Column("created_at", clock, nullable=False),
            sa.Column("updated_at", clock, nullable=False),
        ],
        "diagnosis_steps": [
            sa.Column("step_id", sa.String(64), primary_key=True),
            sa.Column("diagnosis_id", sa.String(64), nullable=False, index=True),
            sa.Column("generation_id", sa.String(64), nullable=False, index=True),
            sa.Column("tool_name", sa.String(64), nullable=False),
            sa.Column("arguments_json", sa.Text(), nullable=False),
            sa.Column("fingerprint", sa.String(64), nullable=False, index=True),
            sa.Column("status", sa.String(24), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("result_json", sa.Text()),
            sa.Column("expires_at", clock),
            sa.Column("created_at", clock, nullable=False),
            sa.Column("updated_at", clock, nullable=False),
        ],
        "support_request_observations": [
            sa.Column("request_id", sa.String(64), primary_key=True),
            sa.Column("user_id", sa.String(64), nullable=False, index=True),
            sa.Column("service_id", sa.String(64), nullable=False),
            sa.Column("rule_version", sa.String(64), nullable=False),
            sa.Column("observations_json", sa.Text(), nullable=False),
        ],
    }
    for name, columns in definitions.items():
        if name not in tables:
            op.create_table(name, *columns)


def downgrade():
    if op.get_bind().dialect.name == "mysql":
        op.alter_column("support_api_call_logs", "created_at", type_=sa.DateTime(), existing_nullable=False)
    for name in ["diagnosis_steps", "diagnosis_executions", "support_request_observations"]:
        op.drop_table(name)
    op.drop_index("ix_support_handoffs_diagnosis_id", table_name="support_handoffs")
    with op.batch_alter_table("support_handoffs") as batch:
        batch.drop_column("diagnosis_id")
    with op.batch_alter_table("diagnosis_sessions") as batch:
        batch.drop_column("workflow_json")
