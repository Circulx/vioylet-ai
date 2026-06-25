# Repository classes isolate SQLAlchemy queries so service code works with intent-level operations.
from __future__ import annotations

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession


ModelT = TypeVar("ModelT")


class Repository(Generic[ModelT]):
    # Data-access helper for repository; services call this class instead of repeating SQLAlchemy filters
    # inline.
    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        # Binds Repository to the current async session, giving every query method the same DB transaction
        # context.
        self.session = session
        self.model = model

    async def get(self, entity_id: UUID) -> ModelT | None:
        # Fetches the requested get record or None, leaving not-found handling to the calling service.
        return await self.session.get(self.model, entity_id)

    async def list(self, statement: Select[tuple[ModelT]] | None = None) -> list[ModelT]:
        # Returns matching list records with repository scope applied; services assemble responses from these
        # rows.
        statement = statement or select(self.model)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def add(self, entity: ModelT) -> ModelT:
        # Adds add through SQLAlchemy and returns ORM objects or counts for the service layer to consume.
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        # Removes persisted delete rows at the DB boundary so services do not issue raw delete statements.
        await self.session.delete(entity)
        await self.session.flush()

