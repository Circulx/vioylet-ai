"""Compatibility merge for memory and pgvector heads.

Revision ID: 0010_merge_memory_pgvector
Revises: 0009_optional_pgvector_retrieval, 0009_conversation_memory
Create Date: 2026-06-04
"""

revision = "0010_merge_memory_pgvector"
down_revision = ("0009_optional_pgvector_retrieval", "0009_conversation_memory")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
