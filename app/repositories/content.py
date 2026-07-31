# Repository classes isolate SQLAlchemy queries so service code works with intent-level operations.
from __future__ import annotations

from uuid import UUID

from datetime import datetime
from sqlalchemy import and_, select
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import ChatMessage, ContentFolder, ContentSession, ContentVersion, GeneratedAsset
from app.repositories.base import Repository


class SessionRepository(Repository[ContentSession]):
    # Data-access helper for session; services call this class instead of repeating SQLAlchemy filters inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds SessionRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, ContentSession)

    async def list_by_brand(
        self,
        brand_space_id: UUID,
        session_kind: str | None = None,
        tenant_id: UUID | None = None,
    ) -> list[ContentSession]:
        # Returns matching by brand records with repository scope applied; services assemble responses from
        # these rows.
        stmt = select(ContentSession).where(ContentSession.brand_space_id == brand_space_id)
        if tenant_id:
            stmt = stmt.where(ContentSession.tenant_id == tenant_id)
        stmt = stmt.order_by(ContentSession.updated_at.desc())
        if session_kind:
            stmt = stmt.where(ContentSession.session_kind == session_kind)
        result = await self.session.execute(
            stmt
        )
        return list(result.scalars().all())

    async def get_scoped(
        self,
        session_id: UUID,
        tenant_id: UUID,
        brand_space_id: UUID | None = None,
    ) -> ContentSession | None:
        # Fetches the requested scoped record or None, leaving not-found handling to the calling service.
        stmt = select(ContentSession).where(
            ContentSession.id == session_id,
            ContentSession.tenant_id == tenant_id,
        )
        if brand_space_id:
            stmt = stmt.where(ContentSession.brand_space_id == brand_space_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class FolderRepository(Repository[ContentFolder]):
    # Data-access helper for folder; services call this class instead of repeating SQLAlchemy filters inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds FolderRepository to the current async session, giving every query method the same DB transaction
        # context.
        super().__init__(session, ContentFolder)

    async def list_by_brand(self, brand_space_id: UUID, tenant_id: UUID | None = None) -> list[ContentFolder]:
        # Returns matching by brand records with repository scope applied; services assemble responses from
        # these rows.
        stmt = select(ContentFolder).where(ContentFolder.brand_space_id == brand_space_id)
        if tenant_id:
            stmt = stmt.where(ContentFolder.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_scoped(self, folder_id: UUID, tenant_id: UUID, brand_space_id: UUID | None = None) -> ContentFolder | None:
        # Fetches the requested scoped record or None, leaving not-found handling to the calling service.
        stmt = select(ContentFolder).where(
            ContentFolder.id == folder_id,
            ContentFolder.tenant_id == tenant_id,
        )
        if brand_space_id:
            stmt = stmt.where(ContentFolder.brand_space_id == brand_space_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class ContentRepository(Repository[ContentVersion]):
    # Data-access helper for content; services call this class instead of repeating SQLAlchemy filters inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds ContentRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, ContentVersion)

    async def list_by_brand(self, brand_space_id: UUID, tenant_id: UUID | None = None) -> list[ContentVersion]:
        # Returns matching by brand records with repository scope applied; services assemble responses from
        # these rows.
        stmt = select(ContentVersion).where(
            ContentVersion.brand_space_id == brand_space_id,
            ContentVersion.deleted_at.is_(None),
            ContentVersion.lifecycle_state != "archived",
        )
        if tenant_id:
            stmt = stmt.where(ContentVersion.tenant_id == tenant_id)
        stmt = stmt.order_by(ContentVersion.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_scoped(self, content_id: UUID, tenant_id: UUID, brand_space_id: UUID | None = None) -> ContentVersion | None:
        # Fetches the requested scoped record or None, leaving not-found handling to the calling service.
        stmt = select(ContentVersion).where(
            ContentVersion.id == content_id,
            ContentVersion.tenant_id == tenant_id,
        )
        if brand_space_id:
            stmt = stmt.where(ContentVersion.brand_space_id == brand_space_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_session(
        self,
        session_id: UUID,
        tenant_id: UUID | None = None,
        limit: int | None = None,
    ) -> list[ContentVersion]:
        # Returns matching by session records with repository scope applied; services assemble responses from
        # these rows.
        stmt = select(ContentVersion).where(
            ContentVersion.session_id == session_id,
            ContentVersion.deleted_at.is_(None),
            ContentVersion.lifecycle_state != "archived",
        )
        if tenant_id:
            stmt = stmt.where(ContentVersion.tenant_id == tenant_id)
        stmt = stmt.order_by(ContentVersion.created_at.desc())
        if limit:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class AssetRepository(Repository[GeneratedAsset]):
    # Data-access helper for asset; services call this class instead of repeating SQLAlchemy filters inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds AssetRepository to the current async session, giving every query method the same DB transaction
        # context.
        super().__init__(session, GeneratedAsset)

    async def list_by_content(self, content_version_id: UUID) -> list[GeneratedAsset]:
        # Returns matching by content records with repository scope applied; services assemble responses from
        # these rows.
        result = await self.session.execute(select(GeneratedAsset).where(GeneratedAsset.content_version_id == content_version_id))
        return list(result.scalars().all())

    async def get_scoped(self, asset_id: UUID, tenant_id: UUID, brand_space_id: UUID | None = None) -> GeneratedAsset | None:
        # Fetches the requested scoped record or None, leaving not-found handling to the calling service.
        stmt = select(GeneratedAsset).where(
            GeneratedAsset.id == asset_id,
            GeneratedAsset.tenant_id == tenant_id,
        )
        if brand_space_id:
            stmt = stmt.where(GeneratedAsset.brand_space_id == brand_space_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_content_and_roles(self, content_version_id: UUID, roles: list[str]) -> list[GeneratedAsset]:
        # Returns matching by content and roles records with repository scope applied; services assemble
        # responses from these rows.
        result = await self.session.execute(
            select(GeneratedAsset).where(
                GeneratedAsset.content_version_id == content_version_id,
                GeneratedAsset.asset_role.in_(roles),
            )
        )
        return list(result.scalars().all())

    async def get_by_content_storage_role(
        self,
        content_version_id: UUID,
        storage_path: str,
        asset_role: str,
    ) -> GeneratedAsset | None:
        # Fetches the requested by content storage role record or None, leaving not-found handling to the
        # calling service.
        result = await self.session.execute(
            select(GeneratedAsset).where(
                GeneratedAsset.content_version_id == content_version_id,
                GeneratedAsset.storage_path == storage_path,
                GeneratedAsset.asset_role == asset_role,
            )
        )
        return result.scalar_one_or_none()


class ChatMessageRepository(Repository[ChatMessage]):
    # Data-access helper for chat message; services call this class instead of repeating SQLAlchemy filters
    # inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds ChatMessageRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, ChatMessage)

    async def list_by_session(self, session_id: UUID) -> list[ChatMessage]:
        # Returns matching by session records with repository scope applied; services assemble responses from
        # these rows.
        result = await self.session.execute(
            select(ChatMessage)
            .outerjoin(ContentVersion, ChatMessage.content_version_id == ContentVersion.id)
            .where(ChatMessage.session_id == session_id)
            .where(
                or_(
                    ChatMessage.content_version_id.is_(None),
                    ContentVersion.deleted_at.is_(None),
                )
            )
            .where(
                or_(
                    ChatMessage.content_version_id.is_(None),
                    ContentVersion.lifecycle_state != "archived",
                )
            )
            .order_by(ChatMessage.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_latest_assistant_by_content(
        self,
        content_version_id: UUID,
        tenant_id: UUID,
        brand_space_id: UUID,
    ) -> ChatMessage | None:
        # Returns the assistant message that carried the displayed asset payload for this content version.
        result = await self.session.execute(
            select(ChatMessage)
            .where(
                ChatMessage.content_version_id == content_version_id,
                ChatMessage.tenant_id == tenant_id,
                ChatMessage.brand_space_id == brand_space_id,
                ChatMessage.role == "assistant",
            )
            .order_by(ChatMessage.created_at.desc())
        )
        return result.scalars().first()

    async def list_recent_by_session(
        self,
        session_id: UUID,
        limit: int = 8,
        before_created_at: datetime | None = None,
        before_id: UUID | None = None,
    ) -> list[ChatMessage]:
        # Returns matching recent by session records with repository scope applied; services assemble responses
        # from these rows.
        cursor_filter = None
        # This branch separates the special case from the normal path so later logic can work with cleaner
        # assumptions.
        if before_created_at and before_id:
            cursor_filter = or_(
                ChatMessage.created_at < before_created_at,
                and_(ChatMessage.created_at == before_created_at, ChatMessage.id < before_id),
            )
        elif before_created_at:
            cursor_filter = ChatMessage.created_at < before_created_at

        stmt = (
            select(ChatMessage)
            .outerjoin(ContentVersion, ChatMessage.content_version_id == ContentVersion.id)
            .where(ChatMessage.session_id == session_id)
            .where(
                or_(
                    ChatMessage.content_version_id.is_(None),
                    ContentVersion.deleted_at.is_(None),
                )
            )
            .where(
                or_(
                    ChatMessage.content_version_id.is_(None),
                    ContentVersion.lifecycle_state != "archived",
                )
            )
        )
        if cursor_filter is not None:
            stmt = stmt.where(cursor_filter)
        result = await self.session.execute(
            stmt
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        return list(reversed(list(result.scalars().all())))
