"""Add review link participants.

Revision ID: 0015_review_link_participants
Revises: 0014_brand_capacity_alert_states
Create Date: 2026-07-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0015_review_link_participants"
down_revision = "0014_brand_capacity_alert_states"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "review_link_participants",
        sa.Column("review_link_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("mentioned_by", sa.UUID(), nullable=True),
        sa.Column("access_role", sa.String(length=50), nullable=False, server_default="viewer"),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("brand_space_id", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["brand_space_id"], ["brand_spaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mentioned_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["review_link_id"], ["review_links.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("review_link_id", "user_id", name="uq_review_link_participant_user"),
    )
    op.create_index("ix_review_link_participants_brand_space_id", "review_link_participants", ["brand_space_id"])
    op.create_index("ix_review_link_participants_mentioned_by", "review_link_participants", ["mentioned_by"])
    op.create_index("ix_review_link_participants_review_link_id", "review_link_participants", ["review_link_id"])
    op.create_index("ix_review_link_participants_tenant_id", "review_link_participants", ["tenant_id"])
    op.create_index("ix_review_link_participants_user_id", "review_link_participants", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_review_link_participants_user_id", table_name="review_link_participants")
    op.drop_index("ix_review_link_participants_tenant_id", table_name="review_link_participants")
    op.drop_index("ix_review_link_participants_review_link_id", table_name="review_link_participants")
    op.drop_index("ix_review_link_participants_mentioned_by", table_name="review_link_participants")
    op.drop_index("ix_review_link_participants_brand_space_id", table_name="review_link_participants")
    op.drop_table("review_link_participants")
