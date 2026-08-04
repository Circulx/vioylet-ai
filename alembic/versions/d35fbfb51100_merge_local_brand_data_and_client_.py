"""merge_local_brand_data_and_client_notifications

Revision ID: d35fbfb51100
Revises: 0014_brand_data_version, 0016_brand_space_history
Create Date: 2026-07-31 12:18:24.244660
"""
from alembic import op
import sqlalchemy as sa



revision = 'd35fbfb51100'
down_revision = ('0014_brand_data_version', '0016_brand_space_history')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

