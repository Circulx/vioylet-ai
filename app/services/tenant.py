# Service classes hold business workflows between the HTTP layer, repositories, and integrations.
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import delete, func, literal_column, select, update
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401
from app.core.enums import RoleCode
from app.core.exceptions import DuplicateResourceError, LifecycleError, NotFoundError
from app.db.base import Base
from app.integrations.object_storage import get_object_storage
from app.models.brand import BrandSpace, BrandSpaceMember
from app.models.collaboration import UsageLimit
from app.models.content import ContentVersion, GeneratedAsset
from app.models.knowledge import KnowledgeAsset
from app.models.tenant import ActivationToken, Tenant, User, UserRole
from app.repositories.brand import BrandMemberRepository, BrandSpaceRepository
from app.repositories.collaboration import UsageLimitRepository
from app.repositories.tenant import ActivationTokenRepository, RoleRepository, TenantRepository, UserRepository, UserRoleRepository
from app.schemas.tenant import (
    TenantCreateRequest,
    TenantLogoUploadRequest,
    TenantUpdateRequest,
    TenantUsageLimitUpdate,
    TenantUserCreateRequest,
    TenantUserUpdateRequest,
)
from app.services.analytics import AnalyticsService
from app.services.email import EmailDeliveryResult, EmailService
from app.services.notification import InAppNotificationService
from app.services.usage import UsageLimitService
from app.utils.files import decode_base64_content


USAGE_METRIC_CONTENT = "content_generations"
USAGE_METRIC_IMAGES = "image_generations"
USAGE_METRIC_OCR = "ocr_pages"
USAGE_METRIC_USERS = "users"
USAGE_METRIC_BRAND_SPACES = "brand_spaces"
ACTIVATION_TOKEN_TTL = timedelta(hours=48)
ACTIVATION_LINK_MAX_SENDS = 10


class TenantService:
    # Business layer for tenant; routes and workers pass validated inputs here and receive domain results back.
    def __init__(self, session: AsyncSession) -> None:
        # Wires the repositories and helper services this workflow reuses across its public methods.
        self.session = session
        self.tenants = TenantRepository(session)
        self.users = UserRepository(session)
        self.roles = RoleRepository(session)
        self.user_roles = UserRoleRepository(session)
        self.tokens = ActivationTokenRepository(session)
        self.usage_limits = UsageLimitRepository(session)
        self.brand_members = BrandMemberRepository(session)
        self.brand_spaces = BrandSpaceRepository(session)
        self.usage = UsageLimitService(session)
        self.analytics = AnalyticsService(session)
        self.storage = get_object_storage()
        self.email = EmailService()

    async def _ensure_unique_tenant_slug(self, slug: str, *, current_tenant_id: UUID | None = None) -> None:
        # Internal helper for unique tenant slug; it keeps the public service method focused on orchestration
        # instead of low-level shaping.
        existing = await self.tenants.get_by_slug(slug)
        if existing and existing.id != current_tenant_id:
            raise DuplicateResourceError(f"Tenant slug '{slug}' already exists. Use a different slug.")

    async def _ensure_unique_user_email(self, email: str, *, current_user_id: UUID | None = None) -> None:
        # Internal helper for unique user email; it keeps the public service method focused on orchestration
        # instead of low-level shaping.
        existing = await self.users.get_by_email(email)
        if existing and existing.id != current_user_id:
            raise DuplicateResourceError(f"A user with email '{email}' already exists.")

    async def create_tenant(self, payload: TenantCreateRequest) -> tuple[Tenant, EmailDeliveryResult]:
        # Runs the tenant service flow and persists the resulting state before returning it to the route or
        # worker.
        await self._ensure_unique_tenant_slug(payload.slug)
        await self._ensure_unique_user_email(payload.admin_email)
        tenant = Tenant(
            name=payload.name,
            slug=payload.slug,
            contact_email=payload.contact_email,
            contact_number=payload.contact_number,
            address=payload.address,
            metadata_json=payload.metadata_json or {},
        )
        await self.tenants.add(tenant)
        admin = User(
            tenant_id=tenant.id,
            email=payload.admin_email,
            full_name=payload.admin_full_name,
            phone_number=payload.admin_phone_number,
            is_active=True,
            is_activated=False,
        )
        await self.users.add(admin)
        tenant_admin_role = await self.roles.get_by_code(RoleCode.TENANT_ADMIN)
        if not tenant_admin_role:
            raise NotFoundError("Tenant admin role not seeded")
        await self.user_roles.add(UserRole(user_id=admin.id, role_id=tenant_admin_role.id, brand_space_id=None))
        activation_token = str(uuid4())
        await self.tokens.add(
            ActivationToken(
                user_id=admin.id,
                token=activation_token,
                expires_at=datetime.now(timezone.utc) + ACTIVATION_TOKEN_TTL,
            )
        )
        await self.usage_limits.add(
            UsageLimit(
                tenant_id=tenant.id,
                max_users=payload.usage_limits.max_users,
                max_brand_spaces=payload.usage_limits.max_brand_spaces,
                max_content_generations=payload.usage_limits.max_content_generations,
                max_image_generations=payload.usage_limits.max_image_generations,
                max_ocr_pages=payload.usage_limits.max_ocr_pages,
            )
        )
        await self.usage.increment(tenant.id, "users", 1)
        await self.session.commit()
        await self.session.refresh(tenant)
        delivery = self.email.send_activation_email(admin.email, admin.full_name, activation_token)
        return tenant, delivery

    async def create_tenant_user(
        self,
        tenant_id: UUID,
        payload: TenantUserCreateRequest,
        *,
        created_by_admin_email: str | None = None,
    ) -> tuple[User, EmailDeliveryResult]:
        # Runs the tenant user service flow and persists the resulting state before returning it to the route or
        # worker.
        await self._ensure_unique_user_email(payload.email)
        await self.usage.enforce(tenant_id, "users")
        role = await self.roles.get_by_code(payload.role_code)
        if not role:
            raise NotFoundError("Role not found")
        user = User(
            tenant_id=tenant_id,
            email=payload.email,
            full_name=payload.full_name,
            phone_number=payload.phone_number,
            is_active=True,
            is_activated=False,
        )
        await self.users.add(user)
        await self.user_roles.add(UserRole(user_id=user.id, role_id=role.id, brand_space_id=None))
        # Builds the grouped response or persistence payload one record at a time because later steps expect
        # this exact shape.
        for brand_space_id in payload.brand_space_ids:
            await self.brand_members.add(
                __import__("app.models.brand", fromlist=["BrandSpaceMember"]).BrandSpaceMember(
                    tenant_id=tenant_id,
                    brand_space_id=brand_space_id,
                    user_id=user.id,
                    can_manage=False,
                )
            )
        activation_token = str(uuid4())
        activation_sent_at = datetime.now(timezone.utc)
        activation_expires_at = activation_sent_at + ACTIVATION_TOKEN_TTL
        await self.tokens.add(
            ActivationToken(
                user_id=user.id,
                token=activation_token,
                expires_at=activation_expires_at,
            )
        )
        await self.usage.increment(tenant_id, "users")
        await self.session.commit()
        await self.session.refresh(user)
        delivery = self.email.send_activation_email(user.email, user.full_name, activation_token)
        if created_by_admin_email:
            role_label = "Brand User" if payload.role_code == RoleCode.BRAND_USER else "Tenant User"
            self.email.send_user_created_notification_email(
                created_by_admin_email,
                user.full_name,
                user.email,
                role_label,
                delivery,
                activation_sent_at,
                activation_expires_at,
                1,
            )
        return user, delivery

    async def _get_primary_tenant_admin(self, tenant_id: UUID) -> User | None:
        # Internal helper for primary tenant admin; it keeps the public service method focused on orchestration
        # instead of low-level shaping.
        users = await self.users.list_by_tenant(tenant_id)
        for user in users:
            roles = await self.user_roles.list_for_user(user.id)
            for item in roles:
                role = await self.roles.get(item.role_id)
                if role and role.code == RoleCode.TENANT_ADMIN:
                    return user
        return None

    async def list_users(self, tenant_id: UUID) -> list[User]:
        # Runs the users service flow by coordinating repositories, validators, and integrations, then returns
        # domain data.
        return await self.users.list_by_tenant(tenant_id)

    async def list_tenants(self) -> list[Tenant]:
        # Runs the tenants service flow by coordinating repositories, validators, and integrations, then returns
        # domain data.
        return await self.tenants.list()

    async def get_tenant(self, tenant_id: UUID) -> Tenant:
        # Runs the tenant service flow by coordinating repositories, validators, and integrations, then returns
        # domain data.
        tenant = await self.tenants.get(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant not found")
        return tenant

    @staticmethod
    def _month_key(value: object) -> str:
        # Internal helper for month key; it keeps the public service method focused on orchestration instead of
        # low-level shaping.
        if isinstance(value, datetime):
            return value.strftime("%Y-%m")
        return str(value)[:7]

    @staticmethod
    def _brand_usage_targets(tenant: Tenant | None) -> dict[str, float]:
        # Internal helper for brand usage targets; it keeps the public service method focused on orchestration
        # instead of low-level shaping.
        if not tenant or not isinstance(tenant.metadata_json, dict):
            return {}
        raw_targets = tenant.metadata_json.get("brand_usage_targets")
        if not isinstance(raw_targets, dict):
            return {}
        targets: dict[str, float] = {}
        for key, value in raw_targets.items():
            try:
                targets[str(key)] = max(0.0, min(100.0, float(value)))
            except (TypeError, ValueError):
                continue
        return targets

    @staticmethod
    def _usage_limit_values(usage_limit: UsageLimit) -> dict[str, int]:
        # Internal helper for usage limit values; it keeps the public service method focused on orchestration
        # instead of low-level shaping.
        return {
            "max_users": usage_limit.max_users,
            "max_brand_spaces": usage_limit.max_brand_spaces,
            "max_content_generations": usage_limit.max_content_generations,
            "max_image_generations": usage_limit.max_image_generations,
            "max_ocr_pages": usage_limit.max_ocr_pages,
        }

    async def _real_usage_consumption(self, tenant_id: UUID) -> dict[str, int]:
        # Internal helper for real usage consumption; it keeps the public service method focused on
        # orchestration instead of low-level shaping.
        users = int(
            await self.session.scalar(select(func.count(User.id)).where(User.tenant_id == tenant_id))
            or 0
        )
        brand_spaces = int(
            await self.session.scalar(
                select(func.count(BrandSpace.id)).where(
                    BrandSpace.tenant_id == tenant_id,
                    BrandSpace.lifecycle_state != "deleted",
                )
            )
            or 0
        )
        content_generations = int(
            await self.session.scalar(
                select(func.count(ContentVersion.id)).where(ContentVersion.tenant_id == tenant_id)
            )
            or 0
        )
        image_generations = int(
            await self.session.scalar(
                select(func.count(GeneratedAsset.id)).where(GeneratedAsset.tenant_id == tenant_id)
            )
            or 0
        )
        ocr_pages = int(
            await self.session.scalar(
                select(func.coalesce(func.sum(KnowledgeAsset.page_count), 0)).where(
                    KnowledgeAsset.tenant_id == tenant_id
                )
            )
            or 0
        )
        return {
            USAGE_METRIC_USERS: users,
            USAGE_METRIC_BRAND_SPACES: brand_spaces,
            USAGE_METRIC_CONTENT: content_generations,
            USAGE_METRIC_IMAGES: image_generations,
            USAGE_METRIC_OCR: ocr_pages,
        }

    async def _monthly_usage(self, tenant_id: UUID) -> list[dict[str, int | str]]:
        # Internal helper for monthly usage; it keeps the public service method focused on orchestration instead
        # of low-level shaping.
        rows_by_month: dict[str, dict[str, int | str]] = {}

        async def add_month_rows(query, metric_key: str) -> None:
            # Runs the month rows service flow by coordinating repositories, validators, and integrations, then
            # returns domain data.
            result = await self.session.execute(query)
            for month_value, amount in result.all():
                month_key = self._month_key(month_value)
                row = rows_by_month.setdefault(
                    month_key,
                    {
                        "month": month_key,
                        USAGE_METRIC_CONTENT: 0,
                        USAGE_METRIC_IMAGES: 0,
                        USAGE_METRIC_OCR: 0,
                    },
                )
                row[metric_key] = int(amount or 0)

        content_month = func.date_trunc(literal_column("'month'"), ContentVersion.created_at)
        generated_asset_month = func.date_trunc(literal_column("'month'"), GeneratedAsset.created_at)
        knowledge_asset_month = func.date_trunc(literal_column("'month'"), KnowledgeAsset.created_at)

        await add_month_rows(
            select(content_month, func.count(ContentVersion.id))
            .where(ContentVersion.tenant_id == tenant_id)
            .group_by(content_month)
            .order_by(content_month),
            USAGE_METRIC_CONTENT,
        )
        await add_month_rows(
            select(generated_asset_month, func.count(GeneratedAsset.id))
            .where(GeneratedAsset.tenant_id == tenant_id)
            .group_by(generated_asset_month)
            .order_by(generated_asset_month),
            USAGE_METRIC_IMAGES,
        )
        await add_month_rows(
            select(
                knowledge_asset_month,
                func.coalesce(func.sum(KnowledgeAsset.page_count), 0),
            )
            .where(KnowledgeAsset.tenant_id == tenant_id)
            .group_by(knowledge_asset_month)
            .order_by(knowledge_asset_month),
            USAGE_METRIC_OCR,
        )

        return [rows_by_month[key] for key in sorted(rows_by_month)]

    async def _brand_usage(self, tenant_id: UUID, tenant: Tenant | None) -> list[dict[str, object]]:
        # Internal helper for brand usage; it keeps the public service method focused on orchestration instead
        # of low-level shaping.
        brands = await self.brand_spaces.list_by_tenant(tenant_id)
        targets = self._brand_usage_targets(tenant)
        rows: list[dict[str, object]] = []
        # Builds the grouped response or persistence payload one record at a time because later steps expect
        # this exact shape.
        for brand in brands:
            if brand.lifecycle_state == "deleted":
                continue
            content_generations = int(
                await self.session.scalar(
                    select(func.count(ContentVersion.id)).where(
                        ContentVersion.tenant_id == tenant_id,
                        ContentVersion.brand_space_id == brand.id,
                    )
                )
                or 0
            )
            image_generations = int(
                await self.session.scalar(
                    select(func.count(GeneratedAsset.id)).where(
                        GeneratedAsset.tenant_id == tenant_id,
                        GeneratedAsset.brand_space_id == brand.id,
                    )
                )
                or 0
            )
            ocr_pages = int(
                await self.session.scalar(
                    select(func.coalesce(func.sum(KnowledgeAsset.page_count), 0)).where(
                        KnowledgeAsset.tenant_id == tenant_id,
                        KnowledgeAsset.brand_space_id == brand.id,
                    )
                )
                or 0
            )
            monthly_rows: dict[str, dict[str, int | str]] = {}

            async def add_brand_month_rows(query, metric_key: str) -> None:
                # Runs the brand month rows service flow by coordinating repositories, validators, and
                # integrations, then returns domain data.
                result = await self.session.execute(query)
                for month_value, amount in result.all():
                    month_key = self._month_key(month_value)
                    row = monthly_rows.setdefault(
                        month_key,
                        {
                            "month": month_key,
                            USAGE_METRIC_CONTENT: 0,
                            USAGE_METRIC_IMAGES: 0,
                            USAGE_METRIC_OCR: 0,
                        },
                    )
                    row[metric_key] = int(amount or 0)

            brand_content_month = func.date_trunc(literal_column("'month'"), ContentVersion.created_at)
            brand_generated_asset_month = func.date_trunc(literal_column("'month'"), GeneratedAsset.created_at)
            brand_knowledge_asset_month = func.date_trunc(literal_column("'month'"), KnowledgeAsset.created_at)

            await add_brand_month_rows(
                select(brand_content_month, func.count(ContentVersion.id))
                .where(
                    ContentVersion.tenant_id == tenant_id,
                    ContentVersion.brand_space_id == brand.id,
                )
                .group_by(brand_content_month),
                USAGE_METRIC_CONTENT,
            )
            await add_brand_month_rows(
                select(brand_generated_asset_month, func.count(GeneratedAsset.id))
                .where(
                    GeneratedAsset.tenant_id == tenant_id,
                    GeneratedAsset.brand_space_id == brand.id,
                )
                .group_by(brand_generated_asset_month),
                USAGE_METRIC_IMAGES,
            )
            await add_brand_month_rows(
                select(
                    brand_knowledge_asset_month,
                    func.coalesce(func.sum(KnowledgeAsset.page_count), 0),
                )
                .where(
                    KnowledgeAsset.tenant_id == tenant_id,
                    KnowledgeAsset.brand_space_id == brand.id,
                )
                .group_by(brand_knowledge_asset_month),
                USAGE_METRIC_OCR,
            )
            rows.append(
                {
                    "id": brand.id,
                    "name": brand.name,
                    "allocation_percent": targets.get(str(brand.id), 0.0),
                    USAGE_METRIC_CONTENT: content_generations,
                    USAGE_METRIC_IMAGES: image_generations,
                    USAGE_METRIC_OCR: ocr_pages,
                    "monthly_usage": [monthly_rows[key] for key in sorted(monthly_rows)],
                }
            )
        return rows

    async def get_usage_summary(self, tenant_id: UUID) -> dict:
        # Runs the usage summary service flow by coordinating repositories, validators, and integrations, then
        # returns domain data.
        usage_limit = await self.usage_limits.get_by_tenant(tenant_id)
        if not usage_limit:
            raise NotFoundError("Usage limit record not found")
        tenant = await self.tenants.get(tenant_id)
        return {
            "tenant_id": tenant_id,
            "limits": self._usage_limit_values(usage_limit),
            "consumption": await self._real_usage_consumption(tenant_id),
            "monthly_usage": await self._monthly_usage(tenant_id),
            "brand_usage": await self._brand_usage(tenant_id, tenant),
        }

    async def get_tenant_summary(self, tenant_id: UUID) -> dict:
        # Runs the tenant summary service flow by coordinating repositories, validators, and integrations, then
        # returns domain data.
        tenant = await self.get_tenant(tenant_id)
        usage_limit = await self.usage_limits.get_by_tenant(tenant_id)
        usage_limits = self._usage_limit_values(usage_limit) if usage_limit else None
        usage_consumption = await self._real_usage_consumption(tenant_id)
        metrics = await self.analytics.tenant_summary(tenant_id)
        admin_user = await self._get_primary_tenant_admin(tenant_id)
        last_login_result = await self.session.execute(
            select(func.max(User.last_login_at)).where(User.tenant_id == tenant_id)
        )
        last_login_at = last_login_result.scalar_one_or_none()
        active_threshold = datetime.now(timezone.utc) - timedelta(days=30)
        last_active_at = last_login_at if last_login_at and last_login_at >= active_threshold else None
        token_usage = metrics.get("token_usage", {})
        admin_activation_link_sent_count = (
            await self._activation_link_sent_count(admin_user.id) if admin_user else 0
        )
        return {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "contact_email": tenant.contact_email,
            "contact_number": tenant.contact_number,
            "address": tenant.address,
            "logo_asset_path": tenant.logo_asset_path,
            "is_active": tenant.is_active,
            "metadata_json": tenant.metadata_json or {},
            "created_at": tenant.created_at,
            "total_users": metrics["total_users"],
            "brand_space_count": metrics["number_of_brand_spaces"],
            "usage_limits": usage_limits,
            "usage_consumption": usage_consumption,
            "token_usage": {
                "input_tokens": int(token_usage.get("input_tokens") or 0),
                "output_tokens": int(token_usage.get("output_tokens") or 0),
                "total_tokens": int(token_usage.get("total_tokens") or 0),
            },
            "monthly_token_usage": token_usage.get("monthly_token_usage", []),
            "tenant_admin_name": admin_user.full_name if admin_user else None,
            "tenant_admin_email": admin_user.email if admin_user else None,
            "tenant_admin_phone_number": admin_user.phone_number if admin_user else None,
            "tenant_admin_user_id": admin_user.id if admin_user else None,
            "tenant_admin_is_active": admin_user.is_active if admin_user else None,
            "tenant_admin_is_activated": admin_user.is_activated if admin_user else None,
            "tenant_admin_activation_link_sent_count": admin_activation_link_sent_count,
            "tenant_admin_activation_link_attempts_left": self._activation_link_attempts_left(
                admin_activation_link_sent_count
            ),
            "last_active_at": last_active_at,
        }

    async def list_tenant_brand_space_summaries(self, tenant_id: UUID) -> list[dict]:
        # Runs the tenant brand space summaries service flow by coordinating repositories, validators, and
        # integrations, then returns domain data.
        brands = await self.brand_spaces.list_by_tenant(tenant_id)
        active_threshold = datetime.now(timezone.utc) - timedelta(days=30)
        summaries: list[dict] = []

        # Builds the grouped response or persistence payload one record at a time because later steps expect
        # this exact shape.
        for brand in brands:
            content_generations = await self.session.scalar(
                select(func.count(ContentVersion.id)).where(
                    ContentVersion.tenant_id == tenant_id,
                    ContentVersion.brand_space_id == brand.id,
                )
            )
            visual_generations = await self.session.scalar(
                select(func.count(GeneratedAsset.id)).where(
                    GeneratedAsset.tenant_id == tenant_id,
                    GeneratedAsset.brand_space_id == brand.id,
                )
            )
            ocr_pages = await self.session.scalar(
                select(func.coalesce(func.sum(KnowledgeAsset.page_count), 0)).where(
                    KnowledgeAsset.tenant_id == tenant_id,
                    KnowledgeAsset.brand_space_id == brand.id,
                )
            )
            last_login_at = await self.session.scalar(
                select(func.max(User.last_login_at))
                .select_from(BrandSpaceMember)
                .join(User, User.id == BrandSpaceMember.user_id)
                .where(
                    BrandSpaceMember.tenant_id == tenant_id,
                    BrandSpaceMember.brand_space_id == brand.id,
                )
            )
            last_active_at = last_login_at if last_login_at and last_login_at >= active_threshold else None

            summaries.append(
                {
                    "id": brand.id,
                    "tenant_id": brand.tenant_id,
                    "name": brand.name,
                    "slug": brand.slug,
                    "lifecycle_state": brand.lifecycle_state,
                    "created_at": brand.created_at,
                    "last_active_at": last_active_at,
                    "last_login_at": last_login_at,
                    "content_generations": content_generations or 0,
                    "visual_generations": visual_generations or 0,
                    "ocr_pages": int(ocr_pages or 0),
                }
            )

        return summaries

    async def build_user_summary(self, user: User) -> dict:
        # Runs the user summary service flow by coordinating repositories, validators, and integrations, then
        # returns domain data.
        roles = await self.user_roles.list_for_user(user.id)
        role_codes: list[str] = []
        brand_space_ids: list[UUID] = []
        for item in roles:
            role = await self.roles.get(item.role_id)
            if role:
                role_codes.append(role.code)
            if item.brand_space_id:
                brand_space_ids.append(item.brand_space_id)
        member_brand_ids = await self.brand_members.list_brand_ids_for_user(user.id)
        brand_space_ids.extend(item for item in member_brand_ids if item not in brand_space_ids)
        activation_link_sent_count = await self._activation_link_sent_count(user.id)
        return {
            "id": user.id,
            "tenant_id": user.tenant_id,
            "email": user.email,
            "full_name": user.full_name,
            "phone_number": user.phone_number,
            "is_active": user.is_active,
            "is_activated": user.is_activated,
            "role_codes": sorted(set(role_codes)),
            "brand_space_ids": brand_space_ids,
            "created_at": user.created_at,
            "last_login_at": user.last_login_at,
            "activation_link_sent_count": activation_link_sent_count,
            "activation_link_attempts_left": self._activation_link_attempts_left(activation_link_sent_count),
        }

    async def _activation_link_sent_count(self, user_id: UUID) -> int:
        # Counts activation links issued to a user so UI and notification emails can show resend tracking.
        return int(
            await self.session.scalar(
                select(func.count(ActivationToken.id)).where(ActivationToken.user_id == user_id)
            )
            or 0
        )

    @staticmethod
    def _activation_link_attempts_left(sent_count: int) -> int:
        # Keeps the resend policy centralized for service checks, API summaries, and notification copy.
        return max(0, ACTIVATION_LINK_MAX_SENDS - sent_count)

    async def get_user_summary(self, tenant_id: UUID, user_id: UUID) -> dict:
        # Runs the user summary service flow by coordinating repositories, validators, and integrations, then
        # returns domain data.
        user = await self.users.get(user_id)
        if not user or user.tenant_id != tenant_id:
            raise NotFoundError("User not found")
        return await self.build_user_summary(user)

    async def deactivate_user(
        self,
        tenant_id: UUID,
        user_id: UUID,
        actor_user_id: UUID | None = None,
        actor_role_codes: set[str] | None = None,
    ) -> User:
        # Runs the deactivate user service flow and persists the resulting state before returning it to the
        # route or worker.
        user = await self.users.get(user_id)
        if not user or user.tenant_id != tenant_id:
            raise NotFoundError("User not found")
        was_active = user.is_active
        role_code = await self._primary_user_role_code(user.id)
        user.is_active = False
        if was_active and actor_user_id and actor_user_id != user.id and actor_role_codes:
            await InAppNotificationService(self.session).create_user_account_status_notification(
                user,
                recipient_user_id=actor_user_id,
                actor_role_codes=actor_role_codes,
                target_role_codes={role_code} if role_code else None,
                is_active=False,
            )
        await self.session.commit()
        return user

    async def resend_activation_link(
        self,
        tenant_id: UUID,
        user_id: UUID,
        *,
        triggered_by_admin_email: str | None = None,
    ) -> EmailDeliveryResult:
        # Runs the activation resend flow for pending users and persists a fresh token before sending email.
        user = await self.users.get(user_id)
        if not user or user.tenant_id != tenant_id:
            raise NotFoundError("User not found")
        if not user.is_active:
            raise LifecycleError("Cannot resend activation link to an inactive user.")
        if user.is_activated:
            raise LifecycleError("Activation link can only be resent to pending users.")
        sent_count = await self._activation_link_sent_count(user.id)
        if self._activation_link_attempts_left(sent_count) <= 0:
            raise LifecycleError("Activation email attempt limit reached for this user.")

        now = datetime.now(timezone.utc)
        activation_token = str(uuid4())
        activation_expires_at = now + ACTIVATION_TOKEN_TTL
        await self.session.execute(
            update(ActivationToken)
            .where(ActivationToken.user_id == user.id, ActivationToken.used_at.is_(None))
            .values(used_at=now)
        )
        await self.tokens.add(
            ActivationToken(
                user_id=user.id,
                token=activation_token,
                expires_at=activation_expires_at,
            )
        )
        await self.session.commit()
        delivery = self.email.send_activation_email(user.email, user.full_name, activation_token)
        if triggered_by_admin_email:
            new_sent_count = sent_count + 1
            self.email.send_user_created_notification_email(
                triggered_by_admin_email,
                user.full_name,
                user.email,
                "User",
                delivery,
                now,
                activation_expires_at,
                new_sent_count,
            )
        return delivery

    async def update_tenant(
        self,
        tenant_id: UUID,
        payload: TenantUpdateRequest,
        actor_role_codes: set[str] | None = None,
    ) -> Tenant:
        # Runs the tenant service flow and persists the resulting state before returning it to the route or
        # worker.
        tenant = await self.get_tenant(tenant_id)
        if payload.slug is not None and payload.slug != tenant.slug:
            await self._ensure_unique_tenant_slug(payload.slug, current_tenant_id=tenant.id)
        if payload.name is not None:
            tenant.name = payload.name
        if payload.slug is not None:
            tenant.slug = payload.slug
        if payload.contact_email is not None:
            tenant.contact_email = payload.contact_email
        if payload.contact_number is not None:
            tenant.contact_number = payload.contact_number
        if payload.address is not None:
            tenant.address = payload.address
        if getattr(payload, "metadata_json", None) is not None:
            tenant.metadata_json = payload.metadata_json
        if payload.is_active is not None:
            tenant.is_active = payload.is_active

        admin_user = await self._get_primary_tenant_admin(tenant_id)
        # This branch separates the special case from the normal path so later logic can work with cleaner
        # assumptions.
        if admin_user:
            admin_profile_changed = False
            if payload.admin_email is not None and payload.admin_email != admin_user.email:
                await self._ensure_unique_user_email(payload.admin_email, current_user_id=admin_user.id)
            if payload.admin_full_name is not None:
                admin_profile_changed = admin_profile_changed or payload.admin_full_name != admin_user.full_name
                admin_user.full_name = payload.admin_full_name
            if payload.admin_email is not None:
                admin_profile_changed = admin_profile_changed or payload.admin_email != admin_user.email
                admin_user.email = payload.admin_email
            if payload.admin_phone_number is not None:
                admin_profile_changed = admin_profile_changed or payload.admin_phone_number != admin_user.phone_number
                admin_user.phone_number = payload.admin_phone_number
            if actor_role_codes and admin_profile_changed:
                await InAppNotificationService(self.session).create_profile_updated_by_admin_notification(
                    admin_user,
                    actor_role_codes,
                    {RoleCode.TENANT_ADMIN.value},
                )

        if payload.usage_limits is not None:
            await self.update_usage_limits(tenant_id, payload.usage_limits, auto_commit=False)

        await self.session.commit()
        await self.session.refresh(tenant)
        return tenant

    async def update_brand_usage_targets(self, tenant_id: UUID, targets: dict[str, float]) -> dict[str, float]:
        # Runs the brand usage targets service flow and persists the resulting state before returning it to the
        # route or worker.
        tenant = await self.get_tenant(tenant_id)
        brand_ids = set(
            str(brand_id)
            for brand_id in (
                await self.session.execute(
                    select(BrandSpace.id).where(
                        BrandSpace.tenant_id == tenant_id,
                        BrandSpace.lifecycle_state != "deleted",
                    )
                )
            )
            .scalars()
            .all()
        )
        unknown_brand_ids = [brand_id for brand_id in targets if brand_id not in brand_ids]
        if unknown_brand_ids:
            raise NotFoundError("One or more brand spaces were not found")

        metadata = dict(tenant.metadata_json or {})
        metadata["brand_usage_targets"] = targets
        tenant.metadata_json = metadata
        await self.session.commit()
        return targets

    async def delete_tenant(self, tenant_id: UUID) -> None:
        # Runs the tenant service flow and persists the resulting state before returning it to the route or
        # worker.
        tenant = await self.get_tenant(tenant_id)
        if tenant.logo_asset_path:
            self.storage.delete(tenant.logo_asset_path)

        user_ids = list(
            (await self.session.execute(select(User.id).where(User.tenant_id == tenant_id)))
            .scalars()
            .all()
        )
        brand_space_ids = list(
            (await self.session.execute(select(BrandSpace.id).where(BrandSpace.tenant_id == tenant_id)))
            .scalars()
            .all()
        )

        if user_ids:
            await self.session.execute(
                delete(ActivationToken).where(ActivationToken.user_id.in_(user_ids))
            )
            await self.session.execute(delete(UserRole).where(UserRole.user_id.in_(user_ids)))
        if brand_space_ids:
            await self.session.execute(
                delete(UserRole).where(UserRole.brand_space_id.in_(brand_space_ids))
            )

        await self.session.execute(
            update(BrandSpace)
            .where(BrandSpace.tenant_id == tenant_id)
            .values(default_persona_id=None)
        )

        for table in reversed(Base.metadata.sorted_tables):
            if table.name == Tenant.__tablename__ or "tenant_id" not in table.c:
                continue
            await self.session.execute(
                table.delete().where(table.c.tenant_id == tenant_id)
            )

        await self.session.execute(delete(Tenant).where(Tenant.id == tenant_id))
        await self.session.commit()

    async def upload_logo(self, tenant_id: UUID, payload: TenantLogoUploadRequest) -> Tenant:
        # Runs the logo service flow and persists the resulting state before returning it to the route or
        # worker.
        tenant = await self.get_tenant(tenant_id)
        content = decode_base64_content(payload.content_base64)
        if tenant.logo_asset_path:
            self.storage.delete(tenant.logo_asset_path)
        stored = self.storage.save_bytes(tenant.id, None, "tenant-assets", payload.filename, content)
        tenant.logo_asset_path = stored.storage_path
        await self.session.commit()
        await self.session.refresh(tenant)
        return tenant

    async def _primary_user_role_code(self, user_id: UUID) -> str | None:
        role_codes: set[str] = set()
        for user_role in await self.user_roles.list_for_user(user_id):
            role = await self.roles.get(user_role.role_id)
            if role:
                role_codes.add(role.code)
        for role_code in (RoleCode.TENANT_ADMIN.value, RoleCode.TENANT_USER.value, RoleCode.BRAND_USER.value):
            if role_code in role_codes:
                return role_code
        return next(iter(role_codes), None)

    async def _brand_space_names_by_id(self, tenant_id: UUID, brand_space_ids: list[UUID]) -> dict[UUID, str]:
        if not brand_space_ids:
            return {}
        result = await self.session.execute(
            select(BrandSpace.id, BrandSpace.name).where(
                BrandSpace.tenant_id == tenant_id,
                BrandSpace.id.in_(list(dict.fromkeys(brand_space_ids))),
            )
        )
        return {brand_space_id: name for brand_space_id, name in result.all()}

    async def update_tenant_user(
        self,
        tenant_id: UUID,
        user_id: UUID,
        payload: TenantUserUpdateRequest,
        actor_user_id: UUID | None = None,
        actor_role_codes: set[str] | None = None,
    ) -> User:
        # Runs the tenant user service flow and persists the resulting state before returning it to the route or
        # worker.
        user = await self.users.get(user_id)
        if not user or user.tenant_id != tenant_id:
            raise NotFoundError("User not found")
        old_role_code = await self._primary_user_role_code(user.id)
        old_brand_space_ids = await self.brand_members.list_brand_ids_for_user(user.id)
        was_active = user.is_active
        profile_changed = False
        if payload.email is not None and payload.email != user.email:
            await self._ensure_unique_user_email(payload.email, current_user_id=user.id)
        if payload.full_name is not None:
            profile_changed = profile_changed or payload.full_name != user.full_name
            user.full_name = payload.full_name
        if payload.email is not None:
            profile_changed = profile_changed or payload.email != user.email
            user.email = payload.email
        if payload.phone_number is not None:
            profile_changed = profile_changed or payload.phone_number != user.phone_number
            user.phone_number = payload.phone_number
        if payload.is_active is not None:
            user.is_active = payload.is_active

        new_role_code = old_role_code
        if payload.role_code is not None:
            role = await self.roles.get_by_code(payload.role_code)
            if not role:
                raise NotFoundError("Role not found")
            await self.session.execute(delete(UserRole).where(UserRole.user_id == user.id))
            self.session.add(UserRole(user_id=user.id, role_id=role.id, brand_space_id=None))
            new_role_code = payload.role_code

        # This branch enforces tenant, brand, or role boundaries before shared data can be read or changed.
        brand_space_ids = old_brand_space_ids
        assigned_brand_space_ids: list[UUID] = []
        removed_brand_space_ids: list[UUID] = []
        if payload.brand_space_ids is not None:
            brand_space_ids = list(dict.fromkeys(payload.brand_space_ids))
            old_brand_space_id_set = set(old_brand_space_ids)
            new_brand_space_id_set = set(brand_space_ids)
            assigned_brand_space_ids = [
                brand_space_id
                for brand_space_id in brand_space_ids
                if brand_space_id not in old_brand_space_id_set
            ]
            removed_brand_space_ids = [
                brand_space_id
                for brand_space_id in old_brand_space_ids
                if brand_space_id not in new_brand_space_id_set
            ]
            if brand_space_ids:
                existing_brand_ids = set(
                    (
                        await self.session.execute(
                            select(BrandSpace.id).where(
                                BrandSpace.tenant_id == tenant_id,
                                BrandSpace.id.in_(brand_space_ids),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                if len(existing_brand_ids) != len(brand_space_ids):
                    raise NotFoundError("One or more brand spaces were not found")

            await self.session.execute(
                delete(BrandSpaceMember).where(
                    BrandSpaceMember.user_id == user.id,
                    BrandSpaceMember.tenant_id == tenant_id,
                )
            )
            self.session.add_all(
                [
                    BrandSpaceMember(
                        tenant_id=tenant_id,
                        brand_space_id=brand_space_id,
                        user_id=user.id,
                        can_manage=False,
                    )
                    for brand_space_id in brand_space_ids
                ]
            )

        if actor_role_codes and actor_user_id != user.id and profile_changed:
            await InAppNotificationService(self.session).create_profile_updated_by_admin_notification(
                user,
                actor_role_codes,
                {new_role_code},
            )
        if (
            actor_role_codes
            and actor_user_id != user.id
            and old_role_code
            and new_role_code
            and old_role_code != new_role_code
        ):
            await InAppNotificationService(self.session).create_role_updated_notification(
                user,
                old_role_code=old_role_code,
                new_role_code=new_role_code,
                actor_role_codes=actor_role_codes,
            )

        if actor_role_codes and actor_user_id != user.id and (assigned_brand_space_ids or removed_brand_space_ids):
            brand_space_names = await self._brand_space_names_by_id(
                tenant_id,
                [*assigned_brand_space_ids, *removed_brand_space_ids],
            )
            await InAppNotificationService(self.session).create_brand_space_access_notifications(
                user,
                assigned_brand_space_names=[
                    brand_space_names[brand_space_id]
                    for brand_space_id in assigned_brand_space_ids
                    if brand_space_id in brand_space_names
                ],
                removed_brand_space_names=[
                    brand_space_names[brand_space_id]
                    for brand_space_id in removed_brand_space_ids
                    if brand_space_id in brand_space_names
                ],
                actor_role_codes=actor_role_codes,
                target_role_code=new_role_code,
            )

        if (
            payload.is_active is not None
            and payload.is_active != was_active
            and actor_role_codes
            and actor_user_id
            and actor_user_id != user.id
        ):
            await InAppNotificationService(self.session).create_user_account_status_notification(
                user,
                recipient_user_id=actor_user_id,
                actor_role_codes=actor_role_codes,
                target_role_codes={new_role_code} if new_role_code else None,
                is_active=payload.is_active,
            )

        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_usage_limits(
        self,
        tenant_id: UUID,
        payload: TenantUsageLimitUpdate,
        *,
        auto_commit: bool = True,
    ) -> UsageLimit:
        # Runs the usage limits service flow and persists the resulting state before returning it to the route
        # or worker.
        usage_limit = await self.usage_limits.get_by_tenant(tenant_id)
        if not usage_limit:
            raise NotFoundError("Usage limit record not found")
        previous_limits = {
            field_name: int(getattr(usage_limit, field_name) or 0)
            for field_name in self.usage.FIELD_MAP.values()
        }
        usage_limit.max_users = payload.max_users
        usage_limit.max_brand_spaces = payload.max_brand_spaces
        usage_limit.max_content_generations = payload.max_content_generations
        usage_limit.max_image_generations = payload.max_image_generations
        usage_limit.max_ocr_pages = payload.max_ocr_pages
        current_limits = {
            field_name: int(getattr(usage_limit, field_name) or 0)
            for field_name in self.usage.FIELD_MAP.values()
        }
        # Limit-change alerts must use the same consumption values shown in the tenant dashboard.
        dashboard_usage = await self._real_usage_consumption(tenant_id)
        await self.usage.notify_for_limit_changes(
            tenant_id,
            previous_limits,
            current_limits,
            usage_by_metric=dashboard_usage,
        )
        if auto_commit:
            await self.session.commit()
        return usage_limit
