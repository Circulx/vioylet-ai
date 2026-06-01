from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import BrandScopedMixin, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ConversationMemoryEntry(
    UUIDPrimaryKeyMixin,
    TenantScopedMixin,
    BrandScopedMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "conversation_memory_entries"

    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chat_message_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    content_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("content_history.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    generated_asset_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("generated_assets.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    source_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    entry_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    asset_role: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    storage_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    memory_text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
