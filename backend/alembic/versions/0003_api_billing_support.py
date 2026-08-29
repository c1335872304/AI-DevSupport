"""API diagnostic and billing support domain tables.

Revision ID: 0003_api_billing
Revises: 0002_support
"""
from alembic import op
from app.db.models import Base
revision="0003_api_billing"
down_revision="0002_support"
branch_labels=None
depends_on=None
TABLES=["support_applications","support_api_keys","support_api_call_logs","support_error_codes","support_plans","support_subscriptions","support_usage_records","support_invoices"]
def upgrade():
    bind=op.get_bind()
    for name in TABLES: Base.metadata.tables[name].create(bind=bind,checkfirst=True)
def downgrade():
    bind=op.get_bind()
    for name in reversed(TABLES): Base.metadata.tables[name].drop(bind=bind,checkfirst=True)
