# Repository classes isolate SQLAlchemy queries so service code works with intent-level operations.
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brand import BrandConfigurationSection, BrandSpace, BrandSpaceMember, Guardrail, Objective, Persona
from app.repositories.base import Repository


class BrandSpaceRepository(Repository[BrandSpace]):
    # Data-access helper for brand space; services call this class instead of repeating SQLAlchemy filters
    # inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds BrandSpaceRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, BrandSpace)

    async def list_by_tenant(self, tenant_id: UUID) -> list[BrandSpace]:
        # Returns matching by tenant records with repository scope applied; services assemble responses from
        # these rows.
        result = await self.session.execute(select(BrandSpace).where(BrandSpace.tenant_id == tenant_id))
        return list(result.scalars().all())

    async def get_scoped(self, tenant_id: UUID, brand_space_id: UUID) -> BrandSpace | None:
        # Fetches the requested scoped record or None, leaving not-found handling to the calling service.
        result = await self.session.execute(
            select(BrandSpace).where(
                BrandSpace.id == brand_space_id,
                BrandSpace.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()


class BrandSectionRepository(Repository[BrandConfigurationSection]):
    # Data-access helper for brand section; services call this class instead of repeating SQLAlchemy filters
    # inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds BrandSectionRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, BrandConfigurationSection)

    async def list_current_sections(
        self,
        brand_space_id: UUID,
        tenant_id: UUID | None = None,
    ) -> list[BrandConfigurationSection]:
        # Returns matching current sections records with repository scope applied; services assemble responses
        # from these rows.
        stmt = select(BrandConfigurationSection).where(
            BrandConfigurationSection.brand_space_id == brand_space_id,
            BrandConfigurationSection.is_current.is_(True),
        )
        if tenant_id:
            stmt = stmt.where(BrandConfigurationSection.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class PersonaRepository(Repository[Persona]):
    # Data-access helper for persona; services call this class instead of repeating SQLAlchemy filters inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds PersonaRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, Persona)

    async def list_by_brand(self, brand_space_id: UUID, tenant_id: UUID | None = None) -> list[Persona]:
        # Returns matching by brand records with repository scope applied; services assemble responses from
        # these rows.
        stmt = select(Persona).where(Persona.brand_space_id == brand_space_id)
        if tenant_id:
            stmt = stmt.where(Persona.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class GuardrailRepository(Repository[Guardrail]):
    # Data-access helper for guardrail; services call this class instead of repeating SQLAlchemy filters inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds GuardrailRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, Guardrail)

    async def list_by_brand(self, brand_space_id: UUID, tenant_id: UUID | None = None) -> list[Guardrail]:
        # Returns matching by brand records with repository scope applied; services assemble responses from
        # these rows.
        stmt = select(Guardrail).where(Guardrail.brand_space_id == brand_space_id)
        if tenant_id:
            stmt = stmt.where(Guardrail.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ObjectiveRepository(Repository[Objective]):
    # Data-access helper for objective; services call this class instead of repeating SQLAlchemy filters inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds ObjectiveRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, Objective)

    async def list_by_brand(self, brand_space_id: UUID, tenant_id: UUID | None = None) -> list[Objective]:
        # Returns matching by brand records with repository scope applied; services assemble responses from
        # these rows.
        stmt = select(Objective).where(Objective.brand_space_id == brand_space_id)
        if tenant_id:
            stmt = stmt.where(Objective.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class BrandMemberRepository(Repository[BrandSpaceMember]):
    # Data-access helper for brand member; services call this class instead of repeating SQLAlchemy filters
    # inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds BrandMemberRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, BrandSpaceMember)

    async def list_brand_ids_for_user(self, user_id: UUID) -> list[UUID]:
        # Returns matching brand IDs for user records with repository scope applied; services assemble responses
        # from these rows.
        result = await self.session.execute(select(BrandSpaceMember.brand_space_id).where(BrandSpaceMember.user_id == user_id))
        return list(result.scalars().all())

    async def list_for_user(self, user_id: UUID, tenant_id: UUID | None = None) -> list[BrandSpaceMember]:
        # Returns matching for user records with repository scope applied; services assemble responses from
        # these rows.
        stmt = select(BrandSpaceMember).where(BrandSpaceMember.user_id == user_id)
        if tenant_id:
            stmt = stmt.where(BrandSpaceMember.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
