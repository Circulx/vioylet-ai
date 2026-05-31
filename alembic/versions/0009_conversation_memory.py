"""Add conversation memory entries table."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0009_conversation_memory"
down_revision = "0008_brand_legal_cta_tables"
branch_labels = None
depends_on = None


UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "conversation_memory_entries"):
        op.create_table(
            "conversation_memory_entries",
            sa.Column("id", UUID, primary_key=True, nullable=False),
            sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("brand_space_id", UUID, sa.ForeignKey("brand_spaces.id", ondelete="CASCADE"), nullable=True),
            sa.Column("session_id", UUID, sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("chat_message_id", UUID, sa.ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=True),
            sa.Column("content_version_id", UUID, sa.ForeignKey("content_history.id", ondelete="CASCADE"), nullable=True),
            sa.Column("generated_asset_id", UUID, sa.ForeignKey("generated_assets.id", ondelete="CASCADE"), nullable=True),
            sa.Column("source_key", sa.String(length=255), nullable=False),
            sa.Column("entry_type", sa.String(length=80), nullable=False),
            sa.Column("role", sa.String(length=50), nullable=True),
            sa.Column("asset_role", sa.String(length=100), nullable=True),
            sa.Column("storage_path", sa.String(length=512), nullable=True),
            sa.Column("memory_text", sa.Text(), nullable=False),
            sa.Column("metadata_json", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("source_key", name="uq_conversation_memory_entries_source_key"),
        )

    inspector = sa.inspect(bind)
    for index_name, columns in (
        ("ix_conversation_memory_entries_session_id", ["session_id"]),
        ("ix_conversation_memory_entries_source_key", ["source_key"]),
        ("ix_conversation_memory_entries_entry_type", ["entry_type"]),
        ("ix_conversation_memory_entries_generated_asset_id", ["generated_asset_id"]),
        ("ix_conversation_memory_entries_content_version_id", ["content_version_id"]),
        ("ix_conversation_memory_entries_chat_message_id", ["chat_message_id"]),
        ("ix_conversation_memory_entries_asset_role", ["asset_role"]),
    ):
        if not _has_index(inspector, "conversation_memory_entries", index_name):
            op.create_index(index_name, "conversation_memory_entries", columns)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _has_table(inspector, "conversation_memory_entries"):
        for index_name in (
            "ix_conversation_memory_entries_asset_role",
            "ix_conversation_memory_entries_chat_message_id",
            "ix_conversation_memory_entries_content_version_id",
            "ix_conversation_memory_entries_generated_asset_id",
            "ix_conversation_memory_entries_entry_type",
            "ix_conversation_memory_entries_source_key",
            "ix_conversation_memory_entries_session_id",
        ):
            if _has_index(inspector, "conversation_memory_entries", index_name):
                op.drop_index(index_name, table_name="conversation_memory_entries")
        op.drop_table("conversation_memory_entries")
