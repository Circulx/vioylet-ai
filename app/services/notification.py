from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RoleCode
from app.models.collaboration import InAppNotification
from app.models.tenant import Role, Tenant, User, UserRole
from app.repositories.collaboration import InAppNotificationRepository
from app.services.notification_preferences import in_app_notifications_enabled


class InAppNotificationService:
    USAGE_CAPACITY_LABELS = {
        "content_generations": "content-generation",
        "image_generations": "visual-generation",
        "ocr_pages": "OCR-page",
        "users": "user",
        "brand_spaces": "Brand Space",
    }
    USAGE_EXHAUSTED_MESSAGES = {
        "content_generations": (
            "content-generation",
            "Some content-generation features may be restricted until additional capacity is available.",
        ),
        "image_generations": (
            "visual-generation",
            "Some visual-generation features may be restricted until additional capacity is available.",
        ),
        "ocr_pages": (
            "OCR-page",
            "Some OCR-processing features may be restricted until additional capacity is available.",
        ),
        "users": (
            "user",
            "Additional users cannot be added until additional capacity is available.",
        ),
        "brand_spaces": (
            "Brand Space",
            "Additional Brand Spaces cannot be created until additional capacity is available.",
        ),
    }

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.notifications = InAppNotificationRepository(session)

    async def create(
        self,
        *,
        recipient_user_id: UUID,
        title: str,
        message: str,
        tenant_id: UUID | None = None,
        metadata: dict | None = None,
    ) -> InAppNotification | None:
        if not await self._notifications_enabled_for_user(recipient_user_id):
            return None

        notification = InAppNotification(
            recipient_user_id=recipient_user_id,
            tenant_id=tenant_id,
            title=title,
            message=message,
            is_read=False,
            metadata_json=metadata or {},
        )
        return await self.notifications.add(notification)

    async def _notifications_enabled_for_user(self, user_id: UUID) -> bool:
        user = await self.session.get(User, user_id)
        if not user or not user.is_active:
            return False
        return in_app_notifications_enabled(getattr(user, "metadata_json", None))

    async def create_usage_threshold_notifications(
        self,
        *,
        tenant_id: UUID,
        metric_code: str,
        period_key: str,
        previous_usage: int,
        current_usage: int,
        configured_limit: int,
        threshold: int = 80,
    ) -> None:
        capacity_label = self.USAGE_CAPACITY_LABELS.get(str(metric_code))
        if not capacity_label:
            return

        tenant = await self.session.get(Tenant, tenant_id)
        if not tenant:
            return

        metadata = {
            "event": "usage_threshold_crossed",
            "metric_code": str(metric_code),
            "threshold": threshold,
            "period_key": period_key,
            "previous_usage": previous_usage,
            "current_usage": current_usage,
            "configured_limit": configured_limit,
        }
        organization_message = f"Your organization has used {threshold}% of its {capacity_label} capacity."
        owner_message = f"{tenant.name} has used {threshold}% of its {capacity_label} capacity."

        tenant_roles = (RoleCode.TENANT_ADMIN, RoleCode.TENANT_USER)
        for recipient in await self._active_users_by_roles(tenant_roles, tenant_id=tenant_id):
            await self.create(
                recipient_user_id=recipient.id,
                tenant_id=tenant_id,
                title="Usage Warning",
                message=organization_message,
                metadata=metadata,
            )
        for recipient in await self._active_users_by_role(RoleCode.SUPER_ADMIN):
            await self.create(
                recipient_user_id=recipient.id,
                tenant_id=tenant_id,
                title="Usage Warning",
                message=owner_message,
                metadata=metadata,
            )

    async def create_usage_exhausted_notifications(
        self,
        *,
        tenant_id: UUID,
        metric_code: str,
        period_key: str,
        previous_usage: int,
        current_usage: int,
        configured_limit: int,
    ) -> None:
        message_parts = self.USAGE_EXHAUSTED_MESSAGES.get(str(metric_code))
        if not message_parts:
            return
        capacity_label, restriction_message = message_parts
        tenant = await self.session.get(Tenant, tenant_id)
        if not tenant:
            return

        metadata = {
            "event": "usage_exhausted",
            "metric_code": str(metric_code),
            "threshold": 100,
            "period_key": period_key,
            "previous_usage": previous_usage,
            "current_usage": current_usage,
            "configured_limit": configured_limit,
        }
        organization_message = (
            f"Your organization has reached its allocated {capacity_label} limit. "
            f"{restriction_message}"
        )
        owner_message = f"{tenant.name} has reached its allocated {capacity_label} limit."

        tenant_roles = (RoleCode.TENANT_ADMIN, RoleCode.TENANT_USER)
        for recipient in await self._active_users_by_roles(tenant_roles, tenant_id=tenant_id):
            await self.create(
                recipient_user_id=recipient.id,
                tenant_id=tenant_id,
                title="Usage Exhausted",
                message=organization_message,
                metadata=metadata,
            )
        for recipient in await self._active_users_by_role(RoleCode.SUPER_ADMIN):
            await self.create(
                recipient_user_id=recipient.id,
                tenant_id=tenant_id,
                title="Usage Exhausted",
                message=owner_message,
                metadata=metadata,
            )

    async def create_brand_capacity_warning_notifications(
        self,
        *,
        tenant_id: UUID,
        brand_space_id: UUID,
        brand_name: str,
        allocation_percent: float,
        usage_percent: float,
        period_key: str,
    ) -> None:
        metadata = {
            "event": "brand_capacity_allocation_warning",
            "brand_space_id": str(brand_space_id),
            "brand_name": brand_name,
            "allocation_percent": allocation_percent,
            "usage_percent": round(usage_percent, 2),
            "threshold": 80,
            "period_key": period_key,
        }
        message = (
            f'"{brand_name}" has reached 80% of its assigned capacity allocation. '
            "This is an informational update to help you monitor usage distribution across Brand Spaces."
        )
        recipient_roles = (
            RoleCode.TENANT_ADMIN,
            RoleCode.TENANT_USER,
            RoleCode.BRAND_USER,
        )
        for recipient in await self._active_users_by_roles(recipient_roles, tenant_id=tenant_id):
            await self.create(
                recipient_user_id=recipient.id,
                tenant_id=tenant_id,
                title="Capacity Allocation Warning",
                message=message,
                metadata=metadata,
            )

    async def list_for_user(self, user_id: UUID) -> list[InAppNotification]:
        return await self.notifications.list_for_user(user_id)

    async def unread_count_for_user(self, user_id: UUID) -> int:
        return await self.notifications.count_unread_for_user(user_id)

    async def mark_all_read_for_user(self, user_id: UUID) -> int:
        updated_count = await self.notifications.mark_all_read_for_user(user_id)
        if updated_count:
            await self.session.commit()
        return updated_count

    async def clear_for_user(self, user_id: UUID) -> None:
        await self.notifications.delete_for_user(user_id)
        await self.session.commit()

    async def delete_for_user(self, user_id: UUID, notification_id: UUID) -> bool:
        deleted = await self.notifications.delete_one_for_user(user_id, notification_id)
        if deleted:
            await self.session.commit()
        return deleted

    async def create_activation_notifications(self, user: User) -> None:
        role_codes = await self._role_codes_for_user(user.id)
        if RoleCode.TENANT_ADMIN in role_codes:
            await self._notify_tenant_admin_activation(user)
        elif RoleCode.TENANT_USER in role_codes:
            await self._notify_tenant_user_activation(user)
        elif RoleCode.BRAND_USER in role_codes:
            await self._notify_brand_user_activation(user)

    async def create_password_changed_notification(self, user: User) -> None:
        role_codes = await self._role_codes_for_user(user.id)
        password_notification_roles = {
            RoleCode.TENANT_ADMIN,
            RoleCode.TENANT_USER,
            RoleCode.BRAND_USER,
        }
        if not role_codes.intersection(password_notification_roles):
            return
        await self.create(
            recipient_user_id=user.id,
            tenant_id=user.tenant_id,
            title="Password Changed",
            message=(
                "Your password has been changed successfully. If you did not perform this action, "
                "please contact your administrator immediately."
            ),
            metadata={"event": "password_changed"},
        )

    async def create_profile_updated_by_admin_notification(
        self,
        user: User,
        actor_role_codes: set[str],
        target_role_codes: set[str] | None = None,
    ) -> None:
        actor_role_codes = self._normalized_role_codes(actor_role_codes)
        target_role_codes = (
            self._normalized_role_codes(target_role_codes)
            if target_role_codes is not None
            else await self._role_codes_for_user(user.id)
        )
        super_admin = RoleCode.SUPER_ADMIN.value
        tenant_admin = RoleCode.TENANT_ADMIN.value
        tenant_user = RoleCode.TENANT_USER.value
        brand_user = RoleCode.BRAND_USER.value
        should_notify = (
            super_admin in actor_role_codes
            and tenant_admin in target_role_codes
        ) or (
            tenant_admin in actor_role_codes
            and bool(target_role_codes.intersection({tenant_user, brand_user}))
        )
        if not should_notify:
            return
        await self.create(
            recipient_user_id=user.id,
            tenant_id=user.tenant_id,
            title="Profile Updated",
            message="Your profile information has been updated by an administrator.",
            metadata={"event": "profile_updated_by_admin"},
        )

    async def create_own_profile_updated_notification(self, user: User) -> None:
        role_codes = await self._role_codes_for_user(user.id)
        if not role_codes.intersection(
            {RoleCode.TENANT_ADMIN.value, RoleCode.TENANT_USER.value, RoleCode.BRAND_USER.value}
        ):
            return
        await self.create(
            recipient_user_id=user.id,
            tenant_id=user.tenant_id,
            title="Profile Updated",
            message="Your profile information has been updated successfully.",
            metadata={"event": "profile_updated"},
        )

    async def create_role_updated_notification(
        self,
        user: User,
        *,
        old_role_code: str,
        new_role_code: str,
        actor_role_codes: set[str],
    ) -> None:
        actor_role_codes = self._normalized_role_codes(actor_role_codes)
        supported_role_codes = {RoleCode.TENANT_USER.value, RoleCode.BRAND_USER.value}
        if RoleCode.TENANT_ADMIN.value not in actor_role_codes:
            return
        if {old_role_code, new_role_code} != supported_role_codes:
            return
        old_role_label = self._role_label(old_role_code)
        new_role_label = self._role_label(new_role_code)
        await self.create(
            recipient_user_id=user.id,
            tenant_id=user.tenant_id,
            title="Role Updated",
            message=(
                f"Your role has been changed from {old_role_label} to {new_role_label} by your Tenant Admin. "
                "Your permissions have been updated accordingly."
            ),
            metadata={
                "event": "role_updated",
                "old_role_code": old_role_code,
                "new_role_code": new_role_code,
            },
        )

    async def create_user_account_status_notification(
        self,
        user: User,
        *,
        recipient_user_id: UUID,
        actor_role_codes: set[str],
        target_role_codes: set[str] | None,
        is_active: bool,
    ) -> None:
        actor_role_codes = self._normalized_role_codes(actor_role_codes)
        target_role_codes = (
            self._normalized_role_codes(target_role_codes)
            if target_role_codes is not None
            else await self._role_codes_for_user(user.id)
        )
        if RoleCode.TENANT_ADMIN.value not in actor_role_codes:
            return
        if not target_role_codes.intersection({RoleCode.TENANT_USER.value, RoleCode.BRAND_USER.value}):
            return
        user_name = (user.full_name or user.email or "User").strip()
        action = "reactivated" if is_active else "deactivated"
        title = "User Account Reactivated" if is_active else "User Account Deactivated"
        await self.create(
            recipient_user_id=recipient_user_id,
            tenant_id=user.tenant_id,
            title=title,
            message=f"{user_name}'s account has been {action} successfully.",
            metadata={
                "event": f"user_account_{action}",
                "target_user_id": str(user.id),
            },
        )

    async def create_brand_space_access_notifications(
        self,
        user: User,
        *,
        assigned_brand_space_names: list[str],
        removed_brand_space_names: list[str],
        actor_role_codes: set[str],
        target_role_code: str | None,
    ) -> None:
        actor_role_codes = self._normalized_role_codes(actor_role_codes)
        if RoleCode.TENANT_ADMIN.value not in actor_role_codes:
            return
        if target_role_code != RoleCode.BRAND_USER.value:
            return
        if assigned_brand_space_names:
            await self.create(
                recipient_user_id=user.id,
                tenant_id=user.tenant_id,
                title="Brand Space Assigned",
                message=(
                    f"You have been granted access to the "
                    f"{self._brand_space_phrase(assigned_brand_space_names)}."
                ),
                metadata={
                    "event": "brand_space_assigned",
                    "brand_space_names": assigned_brand_space_names,
                },
            )
        if removed_brand_space_names:
            await self.create(
                recipient_user_id=user.id,
                tenant_id=user.tenant_id,
                title="Brand Space Access Removed",
                message=(
                    f"Your access to the {self._brand_space_phrase(removed_brand_space_names)} "
                    "has been removed."
                ),
                metadata={
                    "event": "brand_space_removed",
                    "brand_space_names": removed_brand_space_names,
                },
            )

    async def create_brand_space_created_notification(
        self,
        *,
        recipient_user_id: UUID,
        tenant_id: UUID,
        brand_space_name: str | None,
        actor_role_codes: set[str],
    ) -> None:
        actor_role_codes = self._normalized_role_codes(actor_role_codes)
        if RoleCode.TENANT_ADMIN.value not in actor_role_codes:
            return
        normalized_name = (brand_space_name or "").strip()
        message = (
            f'A new Brand Space "{normalized_name}" has been created successfully.'
            if normalized_name
            else "A new Brand Space Draft has been created successfully."
        )
        await self._create_brand_space_notification_for_tenant_admin_and_super_users(
            recipient_user_id=recipient_user_id,
            tenant_id=tenant_id,
            title="Brand Space Created",
            message=message,
            metadata={"event": "brand_space_created"},
        )

    async def create_brand_space_published_notification(
        self,
        *,
        recipient_user_id: UUID,
        tenant_id: UUID,
        brand_space_name: str | None,
        actor_role_codes: set[str],
    ) -> None:
        actor_role_codes = self._normalized_role_codes(actor_role_codes)
        if RoleCode.TENANT_ADMIN.value not in actor_role_codes:
            return
        normalized_name = (brand_space_name or "").strip()
        message = (
            f'The Brand Space "{normalized_name}" has been published and is now available for use.'
            if normalized_name
            else "A Brand Space has been published and is now available for use."
        )
        await self._create_brand_space_notification_for_tenant_admin_and_super_users(
            recipient_user_id=recipient_user_id,
            tenant_id=tenant_id,
            title="Brand Space Published",
            message=message,
            metadata={"event": "brand_space_published"},
        )

    async def create_brand_space_deleted_notification(
        self,
        *,
        recipient_user_id: UUID,
        tenant_id: UUID,
        brand_space_name: str | None,
        actor_role_codes: set[str],
    ) -> None:
        actor_role_codes = self._normalized_role_codes(actor_role_codes)
        if RoleCode.TENANT_ADMIN.value not in actor_role_codes:
            return
        normalized_name = (brand_space_name or "").strip()
        message = (
            f'The Brand Space "{normalized_name}" has been deleted successfully.'
            if normalized_name
            else "The Brand Space Draft has been deleted successfully."
        )
        await self._create_brand_space_notification_for_tenant_admin_and_super_users(
            recipient_user_id=recipient_user_id,
            tenant_id=tenant_id,
            title="Brand Space Deleted",
            message=message,
            metadata={"event": "brand_space_deleted"},
        )

    async def _create_brand_space_notification_for_tenant_admin_and_super_users(
        self,
        *,
        recipient_user_id: UUID,
        tenant_id: UUID,
        title: str,
        message: str,
        metadata: dict | None = None,
    ) -> None:
        recipient_ids = [recipient_user_id]
        seen_recipient_ids = {recipient_user_id}
        for recipient in await self._active_users_by_role(RoleCode.TENANT_USER, tenant_id=tenant_id):
            if recipient.id in seen_recipient_ids:
                continue
            seen_recipient_ids.add(recipient.id)
            recipient_ids.append(recipient.id)

        for user_id in recipient_ids:
            await self.create(
                recipient_user_id=user_id,
                tenant_id=tenant_id,
                title=title,
                message=message,
                metadata=metadata,
            )

    async def create_brand_space_archived_notification(
        self,
        *,
        recipient_user_id: UUID,
        tenant_id: UUID,
        brand_space_name: str | None,
        actor_role_codes: set[str],
    ) -> None:
        actor_role_codes = self._normalized_role_codes(actor_role_codes)
        if RoleCode.TENANT_ADMIN.value not in actor_role_codes:
            return
        normalized_name = (brand_space_name or "").strip()
        message = (
            f'The Brand Space "{normalized_name}" has been archived successfully.'
            if normalized_name
            else "The Brand Space has been archived successfully."
        )
        await self.create(
            recipient_user_id=recipient_user_id,
            tenant_id=tenant_id,
            title="Brand Space Archived",
            message=message,
            metadata={"event": "brand_space_archived"},
        )

    async def create_brand_space_restored_notification(
        self,
        *,
        recipient_user_id: UUID,
        tenant_id: UUID,
        brand_space_name: str | None,
        actor_role_codes: set[str],
    ) -> None:
        actor_role_codes = self._normalized_role_codes(actor_role_codes)
        if RoleCode.TENANT_ADMIN.value not in actor_role_codes:
            return
        normalized_name = (brand_space_name or "").strip()
        message = (
            f'The Brand Space "{normalized_name}" has been restored successfully.'
            if normalized_name
            else "The Brand Space has been restored successfully."
        )
        await self.create(
            recipient_user_id=recipient_user_id,
            tenant_id=tenant_id,
            title="Brand Space Restored",
            message=message,
            metadata={"event": "brand_space_restored"},
        )

    async def _notify_tenant_admin_activation(self, user: User) -> None:
        message = f"{user.full_name} has activated their Tenant Admin account and can now access Violyt."
        for recipient in await self._active_users_by_role(RoleCode.SUPER_ADMIN):
            await self.create(
                recipient_user_id=recipient.id,
                tenant_id=None,
                title="Tenant Admin Activated",
                message=message,
                metadata={"event": "tenant_admin_activated", "activated_user_id": str(user.id)},
            )
        await self._create_welcome_notification(user)

    async def _notify_tenant_user_activation(self, user: User) -> None:
        if not user.tenant_id:
            await self._create_welcome_notification(user)
            return
        message = f"{user.full_name} has activated their account and can now access Violyt as a Super User."
        for recipient in await self._active_users_by_role(RoleCode.TENANT_ADMIN, tenant_id=user.tenant_id):
            await self.create(
                recipient_user_id=recipient.id,
                tenant_id=user.tenant_id,
                title="Super User Activated",
                message=message,
                metadata={"event": "super_user_activated", "activated_user_id": str(user.id)},
            )
        await self._create_welcome_notification(user)

    async def _notify_brand_user_activation(self, user: User) -> None:
        if not user.tenant_id:
            await self._create_welcome_notification(user)
            return
        message = f"{user.full_name} has activated their account and can now access Violyt as a Brand User."
        for recipient in await self._active_users_by_role(RoleCode.TENANT_ADMIN, tenant_id=user.tenant_id):
            await self.create(
                recipient_user_id=recipient.id,
                tenant_id=user.tenant_id,
                title="Brand User Activated",
                message=message,
                metadata={"event": "brand_user_activated", "activated_user_id": str(user.id)},
            )
        await self._create_welcome_notification(user)

    async def _create_welcome_notification(self, user: User) -> None:
        await self.create(
            recipient_user_id=user.id,
            tenant_id=user.tenant_id,
            title="Welcome to Violyt",
            message="Your account has been activated successfully. You can now access Violyt.",
            metadata={"event": "account_activated"},
        )

    async def _role_codes_for_user(self, user_id: UUID) -> set[str]:
        result = await self.session.execute(
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        return self._normalized_role_codes(set(result.scalars().all()))

    @staticmethod
    def _normalized_role_codes(role_codes: set[str]) -> set[str]:
        return {str(role_code) for role_code in role_codes}

    @staticmethod
    def _role_label(role_code: str) -> str:
        labels = {
            RoleCode.TENANT_USER.value: "Super User",
            RoleCode.BRAND_USER.value: "Brand User",
        }
        return labels.get(role_code, role_code)

    @classmethod
    def _brand_space_phrase(cls, brand_space_names: list[str]) -> str:
        label = "Brand Space" if len(brand_space_names) == 1 else "Brand Spaces"
        return f'{label} {cls._quoted_name_list(brand_space_names)}'

    @staticmethod
    def _quoted_name_list(names: list[str]) -> str:
        quoted_names = [f'"{name}"' for name in names]
        if len(quoted_names) <= 1:
            return quoted_names[0] if quoted_names else ""
        if len(quoted_names) == 2:
            return f"{quoted_names[0]} and {quoted_names[1]}"
        if len(quoted_names) == 3:
            return f"{', '.join(quoted_names[:-1])}, and {quoted_names[-1]}"
        first_three = ", ".join(quoted_names[:3])
        return f"{first_three}, and {len(quoted_names) - 3} more"

    async def _active_users_by_role(self, role_code: str, tenant_id: UUID | None = None) -> list[User]:
        return await self._active_users_by_roles((role_code,), tenant_id=tenant_id)

    async def _active_users_by_roles(
        self,
        role_codes: tuple[str, ...],
        tenant_id: UUID | None = None,
    ) -> list[User]:
        stmt = (
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(User.is_active.is_(True), Role.code.in_(role_codes))
            .distinct()
        )
        if tenant_id:
            stmt = stmt.where(User.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
