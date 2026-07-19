"""add data_version to brand_spaces for cache invalidation on re-index

Revision ID: 0014_brand_data_version
Revises: 0013_retrieval_logs_table
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa


revision = "0014_brand_data_version"
down_revision = "0013_retrieval_logs_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "brand_spaces",
        sa.Column(
            "data_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )


def downgrade() -> None:
    op.drop_column("brand_spaces", "data_version")
