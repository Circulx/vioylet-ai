"""Merge the current Alembic migration heads."""

from collections.abc import Sequence


revision: str = "0017_merge_current_heads"
down_revision: tuple[str, str] = (
    "0014_brand_data_version",
    "0016_brand_space_history",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
