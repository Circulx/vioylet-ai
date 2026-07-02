"""Add optional pgvector retrieval table

Revision ID: 0009_optional_pgvector_retrieval
Revises: 0008_brand_legal_cta_tables
Create Date: 2026-06-02

"""

from alembic import op
import sqlalchemy as sa


revision = "0009_optional_pgvector_retrieval"
down_revision = "0008_brand_legal_cta_tables"
branch_labels = None
depends_on = None


TABLE_NAME = "retrieval_vector_documents"


def _pgvector_available(bind) -> bool:
    if bind.dialect.name != "postgresql":
        return False
    return bool(
        bind.execute(
            sa.text(
                "SELECT EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vector')"
            )
        ).scalar()
    )


def upgrade():
    bind = op.get_bind()
    if not _pgvector_available(bind):
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            namespace TEXT NOT NULL,
            chunk_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
            embedding vector NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (namespace, chunk_id)
        )
        """
    )
    op.execute(f"CREATE INDEX IF NOT EXISTS ix_{TABLE_NAME}_namespace ON {TABLE_NAME} (namespace)")
    op.execute(f"CREATE INDEX IF NOT EXISTS ix_{TABLE_NAME}_source ON {TABLE_NAME} (namespace, source_id)")


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
