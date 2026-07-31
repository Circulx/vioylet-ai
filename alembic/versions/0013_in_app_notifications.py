"""Add in-app notifications.

Revision ID: 0013_in_app_notifications
Revises: 0012_review_comment_replies
Create Date: 2026-07-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0013_in_app_notifications"
down_revision = "0012_review_comment_replies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "in_app_notifications",
        sa.Column("recipient_user_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_in_app_notifications_recipient_user_id", "in_app_notifications", ["recipient_user_id"], unique=False)
    op.create_index("ix_in_app_notifications_tenant_id", "in_app_notifications", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_in_app_notifications_tenant_id", table_name="in_app_notifications")
    op.drop_index("ix_in_app_notifications_recipient_user_id", table_name="in_app_notifications")
    op.drop_table("in_app_notifications")
