"""Merge Review Link and Brand Space History migration heads.

Revision ID: 0016_merge_review_history
Revises: 0015_brand_space_history, 0015_review_link_participants
Create Date: 2026-07-23
"""

revision = "0016_merge_review_history"
down_revision = ("0015_brand_space_history", "0015_review_link_participants")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
