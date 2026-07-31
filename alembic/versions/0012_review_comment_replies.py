"""Add threaded review comment replies.

Revision ID: 0012_review_comment_replies
Revises: 0011_content_token_columns
Create Date: 2026-07-09
"""

from alembic import op
import sqlalchemy as sa


revision = "0012_review_comment_replies"
down_revision = "0011_content_token_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "review_comments",
        sa.Column("parent_comment_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_review_comments_parent_comment_id",
        "review_comments",
        "review_comments",
        ["parent_comment_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_review_comments_parent_comment_id",
        "review_comments",
        ["parent_comment_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_review_comments_parent_comment_id", table_name="review_comments")
    op.drop_constraint("fk_review_comments_parent_comment_id", "review_comments", type_="foreignkey")
    op.drop_column("review_comments", "parent_comment_id")
