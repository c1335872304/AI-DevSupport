"""Persist bounded and scoped continuation state."""

from alembic import op

from app.db.models import ConversationContextState

revision = "0016_conversation_context_state"
down_revision = "0015_diagnosis_loop"
branch_labels = None
depends_on = None


def upgrade():
    ConversationContextState.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    ConversationContextState.__table__.drop(op.get_bind(), checkfirst=True)
