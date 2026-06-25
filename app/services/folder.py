# Service classes hold business workflows between the HTTP layer, repositories, and integrations.
from __future__ import annotations

from uuid import UUID

from app.core.exceptions import NotFoundError
from app.models.content import ContentFolder
from app.repositories.content import ContentRepository, FolderRepository
from sqlalchemy.ext.asyncio import AsyncSession


class FolderService:
    # Business layer for folder; routes and workers pass validated inputs here and receive domain results back.
    def __init__(self, session: AsyncSession) -> None:
        # Wires the repositories and helper services this workflow reuses across its public methods.
        self.session = session
        self.folders = FolderRepository(session)
        self.contents = ContentRepository(session)

    async def create(self, tenant_id: UUID, brand_space_id: UUID, created_by: UUID, name: str, description: str | None = None) -> ContentFolder:
        # Runs the create service flow and persists the resulting state before returning it to the route or
        # worker.
        folder = ContentFolder(
            tenant_id=tenant_id,
            brand_space_id=brand_space_id,
            name=name,
            description=description,
            created_by=created_by,
        )
        await self.folders.add(folder)
        await self.session.commit()
        return folder

    async def rename(self, folder_id: UUID, name: str) -> ContentFolder:
        # Runs the rename service flow and persists the resulting state before returning it to the route or
        # worker.
        folder = await self.folders.get(folder_id)
        if not folder:
            raise NotFoundError("Folder not found")
        folder.name = name
        await self.session.commit()
        return folder

    async def rename_scoped(self, tenant_id: UUID, brand_space_id: UUID, folder_id: UUID, name: str) -> ContentFolder:
        # Runs the rename scoped service flow and persists the resulting state before returning it to the route
        # or worker.
        folder = await self.folders.get_scoped(folder_id, tenant_id, brand_space_id)
        if not folder:
            raise NotFoundError("Folder not found")
        folder.name = name
        await self.session.commit()
        return folder

    async def delete(self, folder_id: UUID) -> None:
        # Runs the delete service flow and persists the resulting state before returning it to the route or
        # worker.
        folder = await self.folders.get(folder_id)
        if not folder:
            raise NotFoundError("Folder not found")
        await self.folders.delete(folder)
        await self.session.commit()

    async def delete_scoped(self, tenant_id: UUID, brand_space_id: UUID, folder_id: UUID) -> None:
        # Runs the scoped service flow and persists the resulting state before returning it to the route or
        # worker.
        folder = await self.folders.get_scoped(folder_id, tenant_id, brand_space_id)
        if not folder:
            raise NotFoundError("Folder not found")
        await self.folders.delete(folder)
        await self.session.commit()

    async def move_content(self, content_version_id: UUID, folder_id: UUID) -> None:
        # Runs the move content service flow and persists the resulting state before returning it to the route
        # or worker.
        content = await self.contents.get(content_version_id)
        folder = await self.folders.get(folder_id)
        if not content or not folder:
            raise NotFoundError("Content or folder not found")
        content.folder_id = folder_id
        content.lifecycle_state = "organized"
        await self.session.commit()

    async def move_content_scoped(self, tenant_id: UUID, brand_space_id: UUID, content_version_id: UUID, folder_id: UUID) -> None:
        # Runs the move content scoped service flow and persists the resulting state before returning it to the
        # route or worker.
        content = await self.contents.get_scoped(content_version_id, tenant_id, brand_space_id)
        folder = await self.folders.get_scoped(folder_id, tenant_id, brand_space_id)
        if not content or not folder:
            raise NotFoundError("Content or folder not found")
        content.folder_id = folder_id
        content.lifecycle_state = "organized"
        await self.session.commit()

    async def list(self, tenant_id: UUID, brand_space_id: UUID) -> list[ContentFolder]:
        # Runs the list service flow by coordinating repositories, validators, and integrations, then returns
        # domain data.
        return await self.folders.list_by_brand(brand_space_id, tenant_id)
