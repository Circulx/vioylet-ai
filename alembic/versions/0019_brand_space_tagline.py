"""Add tagline to Brand Spaces.

Revision ID: 0019_brand_space_tagline
Revises: 0018_merge_0017_heads
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0019_brand_space_tagline"
down_revision: str = "0018_merge_0017_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("brand_spaces", sa.Column("tagline", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("brand_spaces", "tagline")