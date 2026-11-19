"""Link approval requests to chat and support tickets."""

import sqlalchemy as sa
from alembic import op

revision = "0019_support_approval_actions"
down_revision = "0018_refund_sandbox_intent"
branch_labels = None
depends_on = None
TABLE = "refund_approval_previews"


def upgrade():
    columns = {column["name"]: column for column in sa.inspect(op.get_bind()).get_columns(TABLE)}
    with op.batch_alter_table(TABLE) as batch:
        if not columns["invoice_id"]["nullable"]:
            batch.alter_column("invoice_id", existing_type=sa.String(64), nullable=True)
        if "conversation_id" not in columns:
            batch.add_column(sa.Column("conversation_id", sa.String(64), nullable=True))
            batch.create_index("ix_refund_approval_previews_conversation_id", ["conversation_id"])
        if "handoff_id" not in columns:
            batch.add_column(sa.Column("handoff_id", sa.String(64), nullable=True))
        if "closure_status" not in columns:
            batch.add_column(sa.Column("closure_status", sa.String(24), nullable=True))


def downgrade():
    if op.get_bind().scalar(sa.text(f"SELECT COUNT(*) FROM {TABLE} WHERE invoice_id IS NULL")):
        raise RuntimeError("Archive and reconcile ticket closure approvals before downgrading")
    with op.batch_alter_table(TABLE) as batch:
        batch.drop_index("ix_refund_approval_previews_conversation_id")
        batch.drop_column("conversation_id")
        batch.drop_column("handoff_id")
        batch.drop_column("closure_status")
        batch.alter_column("invoice_id", existing_type=sa.String(64), nullable=False)
