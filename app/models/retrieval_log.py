from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import BrandScopedMixin, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class RetrievalLog(
    UUIDPrimaryKeyMixin,
    TenantScopedMixin,
    BrandScopedMixin,
    TimestampMixin,
    Base,
):
    """Persisted audit log for Layer 1 brand context retrieval runs."""

    __tablename__ = "retrieval_logs"

    query: Mapped[str] = mapped_column(Text, nullable=False)
    namespace: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    isolation_status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(nullable=False)
    total_chunks: Mapped[int] = mapped_column(Integer, nullable=False)
    chunks: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
