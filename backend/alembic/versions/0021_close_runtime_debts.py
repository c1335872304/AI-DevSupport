"""Shared approval persistence, execution queue and operations audit ledgers."""

import sqlalchemy as sa
from alembic import op

revision = "0021_close_runtime_debts"
down_revision = "0020_remove_invite_codes"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("approval_checkpoints"):
        op.create_table("approval_checkpoints",
            sa.Column("thread_id", sa.String(length=128), primary_key=True, nullable=False),
            sa.Column("checkpoint_ns", sa.String(length=128), primary_key=True, nullable=False),
            sa.Column("checkpoint_id", sa.String(length=64), primary_key=True, nullable=False),
            sa.Column("parent_id", sa.String(length=64), primary_key=False, nullable=True),
            sa.Column("value_json", sa.Text(), primary_key=False, nullable=False),
            sa.Column("metadata_json", sa.Text(), primary_key=False, nullable=False),
        )
    if not inspector.has_table("approval_writes"):
        op.create_table("approval_writes",
            sa.Column("thread_id", sa.String(length=128), primary_key=True, nullable=False),
            sa.Column("checkpoint_ns", sa.String(length=128), primary_key=True, nullable=False),
            sa.Column("checkpoint_id", sa.String(length=64), primary_key=True, nullable=False),
            sa.Column("task_id", sa.String(length=128), primary_key=True, nullable=False),
            sa.Column("idx", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("channel", sa.String(length=128), primary_key=False, nullable=False),
            sa.Column("value_json", sa.Text(), primary_key=False, nullable=False),
        )
    if not inspector.has_table("approval_executions"):
        op.create_table("approval_executions",
            sa.Column("request_id", sa.String(length=64), primary_key=True, nullable=False),
            sa.Column("status", sa.String(length=24), primary_key=False, nullable=False),
            sa.Column("owner", sa.String(length=64), primary_key=False, nullable=True),
            sa.Column("lease_until", sa.DateTime(), primary_key=False, nullable=True),
            sa.Column("next_attempt_at", sa.DateTime(), primary_key=False, nullable=False),
            sa.Column("attempts", sa.Integer(), primary_key=False, nullable=False),
            sa.Column("outcome", sa.String(length=32), primary_key=False, nullable=True),
            sa.Column("last_error", sa.String(length=500), primary_key=False, nullable=True),
            sa.Column("created_at", sa.DateTime(), primary_key=False, nullable=False),
            sa.Column("updated_at", sa.DateTime(), primary_key=False, nullable=False),
        )
        op.create_index("ix_approval_executions_status", "approval_executions", ['status'], unique=False)
    if not inspector.has_table("support_handoff_audits"):
        op.create_table("support_handoff_audits",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("handoff_id", sa.String(length=64), primary_key=False, nullable=False),
            sa.Column("actor_id", sa.String(length=64), primary_key=False, nullable=False),
            sa.Column("source", sa.String(length=32), primary_key=False, nullable=False),
            sa.Column("before_json", sa.Text(), primary_key=False, nullable=False),
            sa.Column("after_json", sa.Text(), primary_key=False, nullable=False),
            sa.Column("created_at", sa.DateTime(), primary_key=False, nullable=False),
        )
        op.create_index("ix_support_handoff_audits_handoff_id", "support_handoff_audits", ['handoff_id'], unique=False)
    if not inspector.has_table("provider_attempts"):
        op.create_table("provider_attempts",
            sa.Column("attempt_id", sa.String(length=64), primary_key=True, nullable=False),
            sa.Column("user_id", sa.String(length=64), primary_key=False, nullable=True),
            sa.Column("generation_id", sa.String(length=64), primary_key=False, nullable=True),
            sa.Column("kind", sa.String(length=16), primary_key=False, nullable=False),
            sa.Column("model", sa.String(length=128), primary_key=False, nullable=False),
            sa.Column("request_hash", sa.String(length=64), primary_key=False, nullable=False),
            sa.Column("provider_request_id", sa.String(length=255), primary_key=False, nullable=True),
            sa.Column("status", sa.String(length=24), primary_key=False, nullable=False),
            sa.Column("prompt_tokens", sa.BigInteger(), primary_key=False, nullable=True),
            sa.Column("completion_tokens", sa.BigInteger(), primary_key=False, nullable=True),
            sa.Column("total_tokens", sa.BigInteger(), primary_key=False, nullable=True),
            sa.Column("error_code", sa.String(length=64), primary_key=False, nullable=True),
            sa.Column("evidence_ref", sa.String(length=500), primary_key=False, nullable=True),
            sa.Column("reconciled_by", sa.String(length=64), primary_key=False, nullable=True),
            sa.Column("reconciled_at", sa.DateTime(), primary_key=False, nullable=True),
            sa.Column("created_at", sa.DateTime(), primary_key=False, nullable=False),
            sa.Column("updated_at", sa.DateTime(), primary_key=False, nullable=False),
        )
        op.create_index("ix_provider_attempts_generation_id", "provider_attempts", ['generation_id'], unique=False)
        op.create_index("ix_provider_attempts_provider_request_id", "provider_attempts", ['provider_request_id'], unique=False)
        op.create_index("ix_provider_attempts_status", "provider_attempts", ['status'], unique=False)
        op.create_index("ix_provider_attempts_user_id", "provider_attempts", ['user_id'], unique=False)
    if not inspector.has_table("provider_reconciliations"):
        op.create_table("provider_reconciliations",
            sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
            sa.Column("attempt_id", sa.String(length=64), primary_key=False, nullable=False),
            sa.Column("actor_id", sa.String(length=64), primary_key=False, nullable=False),
            sa.Column("evidence_ref", sa.String(length=500), primary_key=False, nullable=False),
            sa.Column("statement_hash", sa.String(length=64), primary_key=False, nullable=False),
            sa.Column("receipt_key", sa.String(length=64), primary_key=False, nullable=False),
            sa.Column("before_json", sa.Text(), primary_key=False, nullable=False),
            sa.Column("after_json", sa.Text(), primary_key=False, nullable=False),
            sa.Column("created_at", sa.DateTime(), primary_key=False, nullable=False),
            sa.UniqueConstraint('attempt_id'),
            sa.UniqueConstraint('receipt_key'),
            sa.UniqueConstraint('statement_hash'),
        )
    if not inspector.has_table("user_role_audits"):
        op.create_table("user_role_audits",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("user_id", sa.String(length=64), primary_key=False, nullable=False),
            sa.Column("actor_id", sa.String(length=64), primary_key=False, nullable=False),
            sa.Column("previous_role", sa.String(length=20), primary_key=False, nullable=False),
            sa.Column("new_role", sa.String(length=20), primary_key=False, nullable=False),
            sa.Column("created_at", sa.DateTime(), primary_key=False, nullable=False),
        )
        op.create_index("ix_user_role_audits_user_id", "user_role_audits", ['user_id'], unique=False)


def downgrade():
    op.drop_table("user_role_audits")
    op.drop_table("provider_reconciliations")
    op.drop_table("provider_attempts")
    op.drop_table("support_handoff_audits")
    op.drop_table("approval_executions")
    op.drop_table("approval_writes")
    op.drop_table("approval_checkpoints")
