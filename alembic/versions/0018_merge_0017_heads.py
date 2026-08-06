"""Merge the duplicate 0017 Alembic heads.

Revision ID: 0018_merge_0017_heads
Revises: 0017_merge_brand_heads, 0017_merge_current_heads
"""

from collections.abc import Sequence


revision: str = "0018_merge_0017_heads"
down_revision: tuple[str, str] = (
    "0017_merge_brand_heads",
    "0017_merge_current_heads",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
