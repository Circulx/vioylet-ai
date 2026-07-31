# Core application plumbing lives here: settings, security helpers, dependency gates, and shared errors.
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RoleCode
from app.core.security import decode_token
from app.db.session import get_db_session
from app.models.brand import BrandSpaceMember
from app.models.tenant import Role, User, UserRole


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@dataclass
class CurrentPrincipal:
    # Core runtime shape for current principal; dependency and security helpers share this instead of passing
    # loose dictionaries.
    user_id: UUID
    tenant_id: UUID | None
    email: str
    role_codes: set[str] = field(default_factory=set)
    brand_space_ids: set[UUID] = field(default_factory=set)

    def has_any_role(self, *roles: str) -> bool:
        # Handles request access rules so protected tenant or brand data is not touched too early.
        return any(role in self.role_codes for role in roles)

    def is_tenant_admin(self) -> bool:
        # Handles is tenant admin for shared backend configuration, dependency injection, or error handling.
        return self.has_any_role(RoleCode.SUPER_ADMIN, RoleCode.TENANT_ADMIN)


async def get_current_principal(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> CurrentPrincipal:
    # Returns shared current principal used by dependency injection and service initialization.
    try:
        payload = decode_token(token)
        user_id = UUID(payload["sub"])
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = await session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")

    stmt = (
        select(UserRole, Role)
        .join(Role, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user.id)
    )
    result = await session.execute(stmt)
    rows = result.all()
    role_codes = {row[1].code for row in rows}
    brand_space_ids = {row[0].brand_space_id for row in rows if row[0].brand_space_id}
    member_rows = await session.execute(
        select(BrandSpaceMember.brand_space_id).where(BrandSpaceMember.user_id == user.id)
    )
    brand_space_ids.update(member_rows.scalars().all())

    return CurrentPrincipal(
        user_id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        role_codes=role_codes,
        brand_space_ids=brand_space_ids,
    )


def require_roles(*role_codes: str):
    # Handles request access rules so protected tenant or brand data is not touched too early.
    async def checker(principal: CurrentPrincipal = Depends(get_current_principal)) -> CurrentPrincipal:
        # Handles checker for shared backend configuration, dependency injection, or error handling.
        if not principal.has_any_role(*role_codes):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return principal

    return checker


async def get_brand_scope_header(x_brand_space_id: str | None = Header(default=None)) -> UUID | None:
    # Fetches request access rules so protected tenant or brand data is not touched too early.
    return UUID(x_brand_space_id) if x_brand_space_id else None


def require_brand_scope(brand_scope: UUID | None) -> UUID:
    # Handles request access rules so protected tenant or brand data is not touched too early.
    if not brand_scope:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Brand-Space-Id header is required",
        )
    return brand_scope


def assert_tenant_access(principal: CurrentPrincipal, tenant_id: UUID) -> None:
    # Handles request access rules so protected tenant or brand data is not touched too early.
    if principal.has_any_role(RoleCode.SUPER_ADMIN):
        return
    if principal.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def assert_brand_access(principal: CurrentPrincipal, brand_space_id: UUID) -> None:
    # Handles request access rules so protected tenant or brand data is not touched too early.
    forbid_super_admin_brand_access(principal)
    if principal.is_tenant_admin():
        return
    if principal.has_any_role(RoleCode.BRAND_USER):
        if brand_space_id not in principal.brand_space_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return
    if principal.brand_space_ids and brand_space_id not in principal.brand_space_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def assert_brand_manage_access(principal: CurrentPrincipal) -> None:
    # Only Tenant Admins can create, edit, publish, archive, delete, or mutate Brand Space files.
    if not principal.has_any_role(RoleCode.TENANT_ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def forbid_super_admin_brand_access(principal: CurrentPrincipal) -> None:
    # Handles request access rules so protected tenant or brand data is not touched too early.
    if principal.has_any_role(RoleCode.SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin cannot access Brand Space content",
        )
