from __future__ import annotations

from uuid import UUID

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import (
    BrandScopedMixin,
    SoftDeleteMixin,
    TenantScopedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class ContentSession(UUIDPrimaryKeyMixin, TenantScopedMixin, BrandScopedMixin, TimestampMixin, Base):
    __tablename__ = "sessions"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    session_kind: Mapped[str] = mapped_column(String(50), nullable=False, default="chat")
    studio_panel: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    conversational_context: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ChatMessage(UUIDPrimaryKeyMixin, TenantScopedMixin, BrandScopedMixin, TimestampMixin, Base):
    __tablename__ = "chat_messages"

    session_id: Mapped[UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    content_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("content_history.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    citations: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)


class ContentFolder(UUIDPrimaryKeyMixin, TenantScopedMixin, BrandScopedMixin, TimestampMixin, Base):
    __tablename__ = "content_folders"
    __table_args__ = (UniqueConstraint("brand_space_id", "name", name="uq_brand_folder_name"),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))


class ContentVersion(
    UUIDPrimaryKeyMixin,
    TenantScopedMixin,
    BrandScopedMixin,
    TimestampMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "content_history"

    session_id: Mapped[UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    folder_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("content_folders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    parent_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("content_history.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    lifecycle_state: Mapped[str] = mapped_column(String(50), nullable=False, default="generated", index=True)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False, default="content")
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    selected_persona_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("personas.id", ondelete="SET NULL"),
        nullable=True,
    )
    selected_template_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    objective_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("objectives.id", ondelete="SET NULL"),
        nullable=True,
    )
    studio_panel: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    generated_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    blueprint_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    explainability_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    token_input_tokens: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    token_output_tokens: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    token_total_tokens: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    tone_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tone_feedback: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class GeneratedAsset(
    UUIDPrimaryKeyMixin,
    TenantScopedMixin,
    BrandScopedMixin,
    TimestampMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "generated_assets"

    content_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("content_history.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    template_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    asset_role: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


def _token_count(value: object) -> int:
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, int):
        return max(value, 0)
    if isinstance(value, float):
        return max(int(value), 0)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return 0


def _sync_content_version_token_columns(
    _mapper: object,
    _connection: object,
    target: ContentVersion,
) -> None:
    metadata = target.explainability_metadata if isinstance(target.explainability_metadata, dict) else {}
    usage = metadata.get("token_usage") if isinstance(metadata.get("token_usage"), dict) else {}

    input_tokens = _token_count(usage.get("input_tokens") or usage.get("prompt_tokens"))
    output_tokens = _token_count(usage.get("output_tokens") or usage.get("completion_tokens"))
    total_tokens = _token_count(usage.get("total_tokens"))
    if total_tokens == 0 and (input_tokens or output_tokens):
        total_tokens = input_tokens + output_tokens

    target.token_input_tokens = input_tokens
    target.token_output_tokens = output_tokens
    target.token_total_tokens = total_tokens


event.listen(ContentVersion, "before_insert", _sync_content_version_token_columns)
event.listen(ContentVersion, "before_update", _sync_content_version_token_columns)
