"""Add Brand Space activity history.

Revision ID: 0015_brand_space_history
Revises: 0014_brand_capacity_alert_states
Create Date: 2026-07-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0015_brand_space_history"
down_revision = "0014_brand_capacity_alert_states"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "brand_space_history",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("brand_space_id", sa.UUID(), nullable=False),
        sa.Column("activity_type", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("performed_by", sa.UUID(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["brand_space_id"], ["brand_spaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["performed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_brand_space_history_tenant_id", "brand_space_history", ["tenant_id"])
    op.create_index("ix_brand_space_history_brand_space_id", "brand_space_history", ["brand_space_id"])
    op.create_index("ix_brand_space_history_activity_type", "brand_space_history", ["activity_type"])
    op.create_index("ix_brand_space_history_performed_by", "brand_space_history", ["performed_by"])


def downgrade() -> None:
    op.drop_index("ix_brand_space_history_performed_by", table_name="brand_space_history")
    op.drop_index("ix_brand_space_history_activity_type", table_name="brand_space_history")
    op.drop_index("ix_brand_space_history_brand_space_id", table_name="brand_space_history")
    op.drop_index("ix_brand_space_history_tenant_id", table_name="brand_space_history")
    op.drop_table("brand_space_history")
