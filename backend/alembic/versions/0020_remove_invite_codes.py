"""Remove the retired invitation code table."""

import sqlalchemy as sa
from alembic import op

revision = "0020_remove_invite_codes"
down_revision = "0019_support_approval_actions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("invite_codes"):
        op.drop_table("invite_codes")


def downgrade() -> None:
    # Recreate the legacy schema. Dropped codes cannot be recovered by downgrade.
    op.create_table(
        "invite_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=False),
        sa.Column("used_count", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_invite_codes_code", "invite_codes", ["code"], unique=True)
