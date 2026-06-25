# Repository classes isolate SQLAlchemy queries so service code works with intent-level operations.
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import ConversationMemoryEntry
from app.repositories.base import Repository


class ConversationMemoryRepository(Repository[ConversationMemoryEntry]):
    # Data-access helper for conversation memory; services call this class instead of repeating SQLAlchemy
    # filters inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds ConversationMemoryRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, ConversationMemoryEntry)

    async def get_by_source_key(self, source_key: str) -> ConversationMemoryEntry | None:
        # Fetches the requested by source key record or None, leaving not-found handling to the calling service.
        result = await self.session.execute(
            select(ConversationMemoryEntry).where(ConversationMemoryEntry.source_key == source_key)
        )
        return result.scalar_one_or_none()

    async def list_by_ids(self, entry_ids: list[UUID]) -> list[ConversationMemoryEntry]:
        # Returns matching by IDs records with repository scope applied; services assemble responses from these
        # rows.
        if not entry_ids:
            return []
        result = await self.session.execute(
            select(ConversationMemoryEntry).where(ConversationMemoryEntry.id.in_(entry_ids))
        )
        return list(result.scalars().all())

    async def list_image_entries(
        self,
        *,
        tenant_id: UUID,
        brand_space_id: UUID,
        session_id: UUID | None = None,
        limit: int = 40,
    ) -> list[ConversationMemoryEntry]:
        # Returns matching image entries records with repository scope applied; services assemble responses from
        # these rows.
        stmt = (
            select(ConversationMemoryEntry)
            .where(
                ConversationMemoryEntry.tenant_id == tenant_id,
                ConversationMemoryEntry.brand_space_id == brand_space_id,
                ConversationMemoryEntry.entry_type == "generated_image",
            )
            .order_by(ConversationMemoryEntry.created_at.desc())
            .limit(limit)
        )
        if session_id is not None:
            stmt = stmt.where(ConversationMemoryEntry.session_id == session_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
