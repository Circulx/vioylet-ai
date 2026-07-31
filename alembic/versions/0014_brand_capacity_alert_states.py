"""Add per-brand capacity allocation alert state.

Revision ID: 0014_brand_capacity_alert_states
Revises: 0013_in_app_notifications
Create Date: 2026-07-22
"""

from alembic import op
import sqlalchemy as sa


revision = "0014_brand_capacity_alert_states"
down_revision = "0013_in_app_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "brand_capacity_alert_states",
        sa.Column("period_key", sa.String(length=20), nullable=False),
        sa.Column("last_usage_percent", sa.Float(), nullable=False, server_default="0"),
        sa.Column("warning_sent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("brand_space_id", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["brand_space_id"], ["brand_spaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "brand_space_id",
            "period_key",
            name="uq_brand_capacity_alert_period",
        ),
    )
    op.create_index("ix_brand_capacity_alert_states_tenant_id", "brand_capacity_alert_states", ["tenant_id"])
    op.create_index(
        "ix_brand_capacity_alert_states_brand_space_id",
        "brand_capacity_alert_states",
        ["brand_space_id"],
    )
    op.create_index("ix_brand_capacity_alert_states_period_key", "brand_capacity_alert_states", ["period_key"])


def downgrade() -> None:
    op.drop_index("ix_brand_capacity_alert_states_period_key", table_name="brand_capacity_alert_states")
    op.drop_index("ix_brand_capacity_alert_states_brand_space_id", table_name="brand_capacity_alert_states")
    op.drop_index("ix_brand_capacity_alert_states_tenant_id", table_name="brand_capacity_alert_states")
    op.drop_table("brand_capacity_alert_states")
