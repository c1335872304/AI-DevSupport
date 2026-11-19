"""Add the refund approval preview record."""

from alembic import op

from app.db.models import RefundApprovalPreview

revision = "0017_refund_approval_preview"
down_revision = "0016_conversation_context_state"
branch_labels = None
depends_on = None


def upgrade():
    RefundApprovalPreview.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    RefundApprovalPreview.__table__.drop(op.get_bind(), checkfirst=True)
