"""Seed a tenant + tenant admin + brand space for local Layer 1 testing.

Creates a brand space with the same UUID as the remote server's
"WWE Universe Content Studio" so Pinecone namespace data matches.
"""
from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.core.security import hash_password
from app.core.enums import RoleCode
from app.models.tenant import Tenant, User, UserRole, Role, RolePermission, Permission
from app.models.brand import BrandSpace


TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
ADMIN_USER_ID = uuid.UUID("f0008726-089e-47f8-9a2f-9f5c3a1b7e04")  # matches remote
BRAND_ID = uuid.UUID("f5072038-e3b5-40de-8d49-c074fe5015d6")  # matches remote WWE brand

ADMIN_EMAIL = "skush@indosakura.com"
ADMIN_PASSWORD = "Kushals@1992003"
ADMIN_NAME = "Kushal"

BRAND_NAME = "WWE Universe Content Studio"
BRAND_SLUG = "wwe-universe-content-studio"


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        # 1. Seed RBAC (roles + permissions) if not already
        from app.services.bootstrap import seed_rbac
        await seed_rbac(session)

        # 2. Create tenant
        tenant = (
            await session.execute(select(Tenant).where(Tenant.id == TENANT_ID))
        ).scalar_one_or_none()
        if not tenant:
            tenant = Tenant(
                id=TENANT_ID,
                name="Indo Sakura",
                slug="indo-sakura",
                contact_email=ADMIN_EMAIL,
                is_active=True,
            )
            session.add(tenant)
            await session.flush()
            print(f"Created tenant: {tenant.name} ({tenant.id})")
        else:
            print(f"Tenant already exists: {tenant.name}")

        # 3. Create tenant admin user
        user = (
            await session.execute(select(User).where(User.email == ADMIN_EMAIL))
        ).scalar_one_or_none()
        if not user:
            user = User(
                id=ADMIN_USER_ID,
                tenant_id=TENANT_ID,
                email=ADMIN_EMAIL,
                full_name=ADMIN_NAME,
                hashed_password=hash_password(ADMIN_PASSWORD),
                is_active=True,
                is_activated=True,
                metadata_json={},
            )
            session.add(user)
            await session.flush()
            print(f"Created user: {user.email} ({user.id})")
        else:
            user.hashed_password = hash_password(ADMIN_PASSWORD)
            user.is_active = True
            user.is_activated = True
            print(f"User already exists, updated password: {user.email}")

        # 4. Assign tenant_admin role
        admin_role = (
            await session.execute(select(Role).where(Role.code == RoleCode.TENANT_ADMIN))
        ).scalar_one()
        existing_role = (
            await session.execute(
                select(UserRole).where(
                    UserRole.user_id == user.id,
                    UserRole.role_id == admin_role.id,
                    UserRole.brand_space_id.is_(None),
                )
            )
        ).scalar_one_or_none()
        if not existing_role:
            session.add(UserRole(user_id=user.id, role_id=admin_role.id, brand_space_id=None))
            print(f"Assigned TENANT_ADMIN role to {user.email}")

        # 5. Create brand space with same UUID as remote
        brand = (
            await session.execute(select(BrandSpace).where(BrandSpace.id == BRAND_ID))
        ).scalar_one_or_none()
        if not brand:
            brand = BrandSpace(
                id=BRAND_ID,
                tenant_id=TENANT_ID,
                name=BRAND_NAME,
                slug=BRAND_SLUG,
                description="WWE Universe Content Studio brand space",
                lifecycle_state="active",
            )
            session.add(brand)
            await session.flush()
            print(f"Created brand: {brand.name} ({brand.id})")
        else:
            print(f"Brand already exists: {brand.name}")

        # 6. Assign user to brand space
        brand_role = (
            await session.execute(select(Role).where(Role.code == RoleCode.TENANT_ADMIN))
        ).scalar_one()
        existing_brand_role = (
            await session.execute(
                select(UserRole).where(
                    UserRole.user_id == user.id,
                    UserRole.role_id == brand_role.id,
                    UserRole.brand_space_id == brand.id,
                )
            )
        ).scalar_one_or_none()
        if not existing_brand_role:
            session.add(UserRole(user_id=user.id, role_id=brand_role.id, brand_space_id=brand.id))
            print(f"Assigned user to brand: {brand.name}")

        await session.commit()
        print("\nSeed complete!")
        print(f"  Login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        print(f"  Brand: {BRAND_NAME} (ID: {BRAND_ID})")


if __name__ == "__main__":
    asyncio.run(seed())
