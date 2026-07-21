# Repository classes isolate SQLAlchemy queries so service code works with intent-level operations.
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import ActivationToken, Permission, Role, Tenant, User, UserRole
from app.repositories.base import Repository


class TenantRepository(Repository[Tenant]):
    # Data-access helper for tenant; services call this class instead of repeating SQLAlchemy filters inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds TenantRepository to the current async session, giving every query method the same DB transaction
        # context.
        super().__init__(session, Tenant)

    async def get_by_slug(self, slug: str) -> Tenant | None:
        # Fetches the requested by slug record or None, leaving not-found handling to the calling service.
        result = await self.session.execute(select(Tenant).where(Tenant.slug == slug))
        return result.scalar_one_or_none()


class UserRepository(Repository[User]):
    # Data-access helper for user; services call this class instead of repeating SQLAlchemy filters inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds UserRepository to the current async session, giving every query method the same DB transaction
        # context.
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        # Fetches the requested by email record or None, leaving not-found handling to the calling service.
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def list_by_tenant(self, tenant_id: UUID) -> list[User]:
        # Returns matching by tenant records with repository scope applied; services assemble responses from
        # these rows.
        result = await self.session.execute(select(User).where(User.tenant_id == tenant_id))
        return list(result.scalars().all())

    async def list_by_tenant_role_codes(
        self,
        tenant_id: UUID,
        role_codes: set[str],
        exclude_role_codes: set[str] | None = None,
    ) -> list[User]:
        # Returns tenant users whose assigned roles match the requested role codes.
        stmt = (
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(User.tenant_id == tenant_id, Role.code.in_(role_codes))
            .distinct()
        )
        if exclude_role_codes:
            excluded_user_ids = (
                select(UserRole.user_id)
                .join(Role, Role.id == UserRole.role_id)
                .where(Role.code.in_(exclude_role_codes))
            )
            stmt = stmt.where(~User.id.in_(excluded_user_ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class RoleRepository(Repository[Role]):
    # Data-access helper for role; services call this class instead of repeating SQLAlchemy filters inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds RoleRepository to the current async session, giving every query method the same DB transaction
        # context.
        super().__init__(session, Role)

    async def get_by_code(self, code: str) -> Role | None:
        # Fetches the requested by code record or None, leaving not-found handling to the calling service.
        result = await self.session.execute(select(Role).where(Role.code == code))
        return result.scalar_one_or_none()


class UserRoleRepository(Repository[UserRole]):
    # Data-access helper for user role; services call this class instead of repeating SQLAlchemy filters inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds UserRoleRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, UserRole)

    async def list_for_user(self, user_id: UUID) -> list[UserRole]:
        # Returns matching for user records with repository scope applied; services assemble responses from
        # these rows.
        result = await self.session.execute(select(UserRole).where(UserRole.user_id == user_id))
        return list(result.scalars().all())

    async def list_for_user_in_tenant(self, user_id: UUID, brand_space_ids: list[UUID] | None = None) -> list[UserRole]:
        # Returns matching for user in tenant records with repository scope applied; services assemble responses
        # from these rows.
        stmt = select(UserRole).where(UserRole.user_id == user_id)
        if brand_space_ids is not None:
            stmt = stmt.where((UserRole.brand_space_id.is_(None)) | (UserRole.brand_space_id.in_(brand_space_ids)))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ActivationTokenRepository(Repository[ActivationToken]):
    # Data-access helper for activation token; services call this class instead of repeating SQLAlchemy filters
    # inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds ActivationTokenRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, ActivationToken)

    async def get_by_token(self, token: str) -> ActivationToken | None:
        # Fetches the requested by token record or None, leaving not-found handling to the calling service.
        result = await self.session.execute(select(ActivationToken).where(ActivationToken.token == token))
        return result.scalar_one_or_none()


class PermissionRepository(Repository[Permission]):
    # Data-access helper for permission; services call this class instead of repeating SQLAlchemy filters
    # inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds PermissionRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, Permission)
