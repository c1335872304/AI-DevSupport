"""Store sandbox refund requests and confirmed receipts."""

from alembic import op

from app.db.models import RefundSandboxIntent

revision = "0018_refund_sandbox_intent"
down_revision = "0017_refund_approval_preview"
branch_labels = None
depends_on = None


def upgrade():
    RefundSandboxIntent.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    RefundSandboxIntent.__table__.drop(op.get_bind(), checkfirst=True)
