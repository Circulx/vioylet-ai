"""Merge conversation memory and pgvector retrieval migration heads.

Revision ID: 0010_merge_memory_pgvector
Revises: 0009_conversation_memory, 0009_optional_pgvector_retrieval
Create Date: 2026-06-03

"""

revision = "0010_merge_memory_pgvector"
down_revision = ("0009_conversation_memory", "0009_optional_pgvector_retrieval")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
