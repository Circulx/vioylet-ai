# Service classes hold business workflows between the HTTP layer, repositories, and integrations.
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import asyncio
import logging
import secrets
from urllib.parse import quote
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RoleCode
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_token,
    decode_token,
    generate_totp_secret,
    hash_password,
    verify_password,
    verify_totp_code,
)
from app.models.tenant import ActivationToken, Role, UserRole
from app.repositories.tenant import ActivationTokenRepository, UserRepository, UserRoleRepository
from app.schemas.auth import (
    CurrentUserResponse,
    PasswordResetResponse,
    TokenPairResponse,
    TwoFactorChallengeResponse,
    TwoFactorSetupResponse,
)
from app.services.email import EmailService
from app.services.notification import InAppNotificationService
from app.services.notification_preferences import email_notifications_enabled, in_app_notifications_enabled


logger = logging.getLogger(__name__)


class AuthService:
    # Business layer for auth; routes and workers pass validated inputs here and receive domain results back.
    TWO_FACTOR_ENABLED_KEY = "two_factor_enabled"
    TWO_FACTOR_SECRET_KEY = "two_factor_secret"
    TWO_FACTOR_PENDING_SECRET_KEY = "two_factor_pending_secret"
    TWO_FACTOR_VERIFIED_AT_KEY = "two_factor_verified_at"
    TWO_FACTOR_FAILED_ATTEMPTS_KEY = "two_factor_failed_attempts"
    TWO_FACTOR_LOCKED_UNTIL_KEY = "two_factor_locked_until"
    TWO_FACTOR_MAX_FAILED_ATTEMPTS = 5
    TWO_FACTOR_LOCKOUT_MINUTES = 30
    TWO_FACTOR_LOCKOUT_MESSAGE = (
        "Too many incorrect verification attempts. Your account has been temporarily locked. "
        "Please try again after 30 minutes."
    )

    def __init__(self, session: AsyncSession) -> None:
        # Wires the repositories and helper services this workflow reuses across its public methods.
        self.session = session
        self.users = UserRepository(session)
        self.user_roles = UserRoleRepository(session)
        self.tokens = ActivationTokenRepository(session)
        self.email = EmailService()

    async def login(
        self,
        email: str,
        password: str,
        *,
        ip_address: str | None = None,
        device_info: str | None = None,
    ) -> TokenPairResponse | TwoFactorChallengeResponse:
        # Runs the login service flow by coordinating repositories, validators, and integrations, then returns
        # domain data.
        user = await self.users.get_by_email(email)
        if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
            if await self._is_platform_owner_login_attempt(email, user):
                self._dispatch_platform_owner_login_attempt_email(
                    user,
                    successful=False,
                    ip_address=ip_address,
                    device_info=device_info,
                )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        is_platform_owner = await self._is_platform_owner(user.id)
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
        if self.is_two_factor_enabled(user):
            ticket = create_token(
                subject=str(user.id),
                expires_delta=timedelta(minutes=10),
                extra={
                    "tenant_id": str(user.tenant_id) if user.tenant_id else None,
                    "typ": "two_factor",
                },
            )
            return TwoFactorChallengeResponse(two_factor_ticket=ticket, email=user.email)
        response = await self._complete_login(user)
        if is_platform_owner:
            self._dispatch_platform_owner_login_attempt_email(
                user,
                successful=True,
                ip_address=ip_address,
                device_info=device_info,
            )
        return response

    async def verify_two_factor_login(
        self,
        ticket: str,
        code: str,
        *,
        ip_address: str | None = None,
        device_info: str | None = None,
    ) -> TokenPairResponse:
        # Runs the two factor login service flow by coordinating repositories, validators, and integrations,
        # then returns domain data.
        try:
            payload = decode_token(ticket)
            if payload.get("typ") != "two_factor":
                raise ValueError("Invalid token type")
            user_id = UUID(payload["sub"])
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid 2FA challenge") from exc
        user = await self.users.get(user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        is_platform_owner = await self._is_platform_owner(user.id)
        if is_platform_owner:
            await self._enforce_two_factor_lockout(user)
        secret = self.get_two_factor_secret(user)
        if not secret or not verify_totp_code(secret, code):
            if is_platform_owner:
                await self._record_two_factor_failure(user)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code")
        if is_platform_owner:
            self._clear_two_factor_lockout(user)
        response = await self._complete_login(user)
        if is_platform_owner:
            self._dispatch_platform_owner_login_attempt_email(
                user,
                successful=True,
                ip_address=ip_address,
                device_info=device_info,
            )
        return response

    async def refresh_access_token(self, refresh_token: str) -> TokenPairResponse:
        # Runs the refresh access token service flow by coordinating repositories, validators, and integrations,
        # then returns domain data.
        try:
            payload = decode_token(refresh_token)
            token_type = str(payload.get("typ") or "").strip().lower()
            if token_type and token_type != "refresh":
                raise ValueError("Invalid token type")
            user_id = UUID(payload["sub"])
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

        user = await self.users.get(user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")

        return await self._complete_login(user)

    async def get_two_factor_status(self, user_id) -> TwoFactorSetupResponse:
        # Runs the two factor status service flow by coordinating repositories, validators, and integrations,
        # then returns domain data.
        user = await self.users.get(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        metadata = user.metadata_json or {}
        return TwoFactorSetupResponse(
            enabled=self.is_two_factor_enabled(user),
            pending_setup=bool(metadata.get(self.TWO_FACTOR_PENDING_SECRET_KEY)),
        )

    async def initiate_two_factor_setup(self, user_id) -> TwoFactorSetupResponse:
        # Runs the initiate two factor setup service flow and persists the resulting state before returning it
        # to the route or worker.
        user = await self.users.get(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        secret = generate_totp_secret()
        metadata = {
            **(user.metadata_json or {}),
            self.TWO_FACTOR_PENDING_SECRET_KEY: secret,
        }
        user.metadata_json = metadata
        await self.session.commit()
        otpauth_url = self.build_otpauth_url(user.email, secret)
        return TwoFactorSetupResponse(
            enabled=self.is_two_factor_enabled(user),
            pending_setup=True,
            secret=secret,
            otpauth_url=otpauth_url,
            qr_code_url=self.build_qr_code_url(otpauth_url),
        )

    async def enable_two_factor(
        self,
        user_id,
        code: str,
        actor_role_codes: set[str] | None = None,
    ) -> TwoFactorSetupResponse:
        # Runs the two factor service flow and persists the resulting state before returning it to the route or
        # worker.
        user = await self.users.get(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        metadata = user.metadata_json or {}
        pending_secret = metadata.get(self.TWO_FACTOR_PENDING_SECRET_KEY)
        if not pending_secret:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Two-factor setup has not been started")
        if not verify_totp_code(pending_secret, code):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code")
        user.metadata_json = {
            **metadata,
            self.TWO_FACTOR_SECRET_KEY: pending_secret,
            self.TWO_FACTOR_ENABLED_KEY: True,
            self.TWO_FACTOR_VERIFIED_AT_KEY: datetime.now(timezone.utc).isoformat(),
            self.TWO_FACTOR_PENDING_SECRET_KEY: None,
        }
        await self.session.commit()
        await self.session.refresh(user)
        self._send_platform_owner_two_factor_email(user, enabled=True, actor_role_codes=actor_role_codes)
        return TwoFactorSetupResponse(enabled=True, pending_setup=False)

    async def disable_two_factor(
        self,
        user_id,
        code: str,
        actor_role_codes: set[str] | None = None,
    ) -> TwoFactorSetupResponse:
        # Runs the two factor service flow and persists the resulting state before returning it to the route or
        # worker.
        user = await self.users.get(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        secret = self.get_two_factor_secret(user)
        if not secret or not verify_totp_code(secret, code):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code")
        metadata = {
            **(user.metadata_json or {}),
            self.TWO_FACTOR_SECRET_KEY: None,
            self.TWO_FACTOR_ENABLED_KEY: False,
            self.TWO_FACTOR_PENDING_SECRET_KEY: None,
        }
        user.metadata_json = metadata
        await self.session.commit()
        await self.session.refresh(user)
        self._send_platform_owner_two_factor_email(user, enabled=False, actor_role_codes=actor_role_codes)
        return TwoFactorSetupResponse(enabled=False, pending_setup=False)

    async def _is_platform_owner_login_attempt(self, email: str, user) -> bool:
        if user:
            return await self._is_platform_owner(user.id)
        normalized_email = (email or "").strip().lower()
        platform_owner_emails = {
            (self.email.settings.platform_owner_two_factor_email_recipient or "").strip().lower(),
            (self.email.settings.demo_owner_email or "").strip().lower(),
        }
        platform_owner_emails.discard("")
        return normalized_email in platform_owner_emails

    def _platform_owner_login_attempt_recipient(self, user) -> str | None:
        override_email = (self.email.settings.platform_owner_two_factor_email_recipient or "").strip()
        if override_email:
            return override_email
        if user and getattr(user, "email", None):
            return user.email
        return (self.email.settings.demo_owner_email or "").strip() or None

    def _dispatch_platform_owner_login_attempt_email(
        self,
        user,
        *,
        successful: bool,
        ip_address: str | None,
        device_info: str | None,
    ) -> None:
        recipient_email = self._platform_owner_login_attempt_recipient(user)
        if not recipient_email:
            return
        attempted_at = datetime.now(timezone.utc)
        asyncio.create_task(
            asyncio.to_thread(
                self._send_platform_owner_login_attempt_email,
                recipient_email,
                successful,
                attempted_at,
                ip_address,
                device_info,
            )
        )

    def _send_platform_owner_login_attempt_email(
        self,
        recipient_email: str,
        successful: bool,
        attempted_at: datetime,
        ip_address: str | None,
        device_info: str | None,
    ) -> None:
        try:
            self.email.send_platform_owner_login_attempt_email(
                recipient_email,
                successful=successful,
                attempted_at=attempted_at,
                ip_address=ip_address,
                device_info=device_info,
            )
        except Exception:
            logger.exception("Failed to send Platform Owner login attempt email.")

    def _send_platform_owner_two_factor_email(
        self,
        user,
        *,
        enabled: bool,
        actor_role_codes: set[str] | None,
    ) -> None:
        # Restricts 2FA security email notices to the Platform Owner performing the action.
        if RoleCode.SUPER_ADMIN.value not in {str(role_code) for role_code in (actor_role_codes or set())}:
            return
        override_email = (self.email.settings.platform_owner_two_factor_email_recipient or "").strip()
        recipient_email = override_email or user.email
        self.email.send_two_factor_security_email(recipient_email, user.full_name, enabled=enabled)

    async def _is_platform_owner(self, user_id: UUID) -> bool:
        result = await self.session.execute(
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        return RoleCode.SUPER_ADMIN.value in {str(code) for code in result.scalars().all()}

    @classmethod
    def _parse_two_factor_lockout_until(cls, value: object) -> datetime | None:
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            locked_until = datetime.fromisoformat(value)
        except ValueError:
            return None
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        return locked_until

    @classmethod
    def _two_factor_lockout_detail(cls) -> str:
        return cls.TWO_FACTOR_LOCKOUT_MESSAGE

    async def _enforce_two_factor_lockout(self, user) -> None:
        metadata = dict(user.metadata_json or {})
        locked_until = self._parse_two_factor_lockout_until(metadata.get(self.TWO_FACTOR_LOCKED_UNTIL_KEY))
        now = datetime.now(timezone.utc)
        if locked_until and locked_until > now:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=self._two_factor_lockout_detail(),
            )
        if locked_until and locked_until <= now:
            metadata.pop(self.TWO_FACTOR_FAILED_ATTEMPTS_KEY, None)
            metadata.pop(self.TWO_FACTOR_LOCKED_UNTIL_KEY, None)
            user.metadata_json = metadata
            await self.session.commit()
            await self.session.refresh(user)

    async def _record_two_factor_failure(self, user) -> None:
        metadata = dict(user.metadata_json or {})
        try:
            failed_attempts = int(metadata.get(self.TWO_FACTOR_FAILED_ATTEMPTS_KEY) or 0) + 1
        except (TypeError, ValueError):
            failed_attempts = 1
        metadata[self.TWO_FACTOR_FAILED_ATTEMPTS_KEY] = failed_attempts
        if failed_attempts >= self.TWO_FACTOR_MAX_FAILED_ATTEMPTS:
            metadata[self.TWO_FACTOR_LOCKED_UNTIL_KEY] = (
                datetime.now(timezone.utc) + timedelta(minutes=self.TWO_FACTOR_LOCKOUT_MINUTES)
            ).isoformat()
            user.metadata_json = metadata
            await self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=self._two_factor_lockout_detail(),
            )
        user.metadata_json = metadata
        await self.session.commit()

    def _clear_two_factor_lockout(self, user) -> None:
        metadata = dict(user.metadata_json or {})
        metadata.pop(self.TWO_FACTOR_FAILED_ATTEMPTS_KEY, None)
        metadata.pop(self.TWO_FACTOR_LOCKED_UNTIL_KEY, None)
        user.metadata_json = metadata

    async def _complete_login(self, user) -> TokenPairResponse:
        # Internal helper for complete login; it keeps the public service method focused on orchestration
        # instead of low-level shaping.
        user.last_login_at = datetime.now(timezone.utc)
        await self.session.commit()
        access = create_access_token(user.id, extra={"tenant_id": str(user.tenant_id) if user.tenant_id else None})
        refresh = create_refresh_token(user.id, extra={"tenant_id": str(user.tenant_id) if user.tenant_id else None})
        return TokenPairResponse(access_token=access, refresh_token=refresh)

    async def activate(self, token: str, password: str) -> TokenPairResponse:
        # Runs the activate service flow and persists the resulting state before returning it to the route or
        # worker.
        activation = await self.tokens.get_by_token(token)
        if not activation or activation.used_at or activation.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid activation token")
        user = await self.users.get(activation.user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid activation token")
        was_already_activated = bool(user.is_activated)
        user.hashed_password = hash_password(password)
        user.is_activated = True
        activation.used_at = datetime.now(timezone.utc)
        if not was_already_activated:
            await InAppNotificationService(self.session).create_activation_notifications(user)
        await self.session.commit()
        access = create_access_token(user.id, extra={"tenant_id": str(user.tenant_id) if user.tenant_id else None})
        refresh = create_refresh_token(user.id, extra={"tenant_id": str(user.tenant_id) if user.tenant_id else None})
        return TokenPairResponse(access_token=access, refresh_token=refresh)

    async def forgot_password(self, email: str) -> PasswordResetResponse:
        # Runs the forgot password service flow and persists the resulting state before returning it to the
        # route or worker.
        user = await self.users.get_by_email(email)
        if not user or not user.is_active:
            return PasswordResetResponse(message="If the email exists, a reset token has been issued.", reset_token=None)
        token_value = secrets.token_urlsafe(24)
        await self.tokens.add(
            ActivationToken(
                user_id=user.id,
                token=token_value,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
                used_at=None,
            )
        )
        await self.session.commit()
        delivery = self.email.send_password_reset_email(user.email, user.full_name, token_value)
        return PasswordResetResponse(
            message="If the email exists, a reset link has been sent.",
            reset_token=token_value if not delivery.delivered else None,
        )

    async def reset_password(self, token: str, password: str) -> TokenPairResponse:
        # Runs the reset password service flow by coordinating repositories, validators, and integrations, then
        # returns domain data.
        return await self.activate(token, password)

    async def update_profile(
        self,
        user_id,
        full_name: str | None,
        email: str | None,
        phone_number: str | None,
        notifications_enabled: bool | None,
        email_notifications_preference: bool | None = None,
        in_app_notifications_preference: bool | None = None,
    ):
        # Runs the profile service flow and persists the resulting state before returning it to the route or
        # worker.
        user = await self.users.get(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        profile_changed = False
        if full_name is not None:
            profile_changed = profile_changed or full_name != user.full_name
            user.full_name = full_name
        if email is not None and email != user.email:
            existing = await self.users.get_by_email(email)
            if existing and existing.id != user.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email address is already in use")
            profile_changed = True
            user.email = email
        if phone_number is not None:
            profile_changed = profile_changed or phone_number != user.phone_number
            user.phone_number = phone_number
        if notifications_enabled is not None:
            user.metadata_json = {
                **(user.metadata_json or {}),
                "notifications_enabled": notifications_enabled,
            }
        if email_notifications_preference is not None:
            user.metadata_json = {
                **(user.metadata_json or {}),
                "email_notifications_enabled": email_notifications_preference,
            }
        if in_app_notifications_preference is not None:
            user.metadata_json = {
                **(user.metadata_json or {}),
                "in_app_notifications_enabled": in_app_notifications_preference,
            }
        if profile_changed:
            await InAppNotificationService(self.session).create_own_profile_updated_notification(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def change_password(
        self,
        user_id,
        current_password: str,
        new_password: str,
        actor_role_codes: set[str] | None = None,
    ) -> PasswordResetResponse:
        # Runs the change password service flow and persists the resulting state before returning it to the
        # route or worker.
        user = await self.users.get(user_id)
        if not user or not user.hashed_password:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is invalid")
        user.hashed_password = hash_password(new_password)
        await InAppNotificationService(self.session).create_password_changed_notification(user)
        await self.session.commit()
        self._send_password_changed_confirmation_email(user, actor_role_codes)
        return PasswordResetResponse(message="Password updated successfully.")

    def _send_password_changed_confirmation_email(
        self,
        user,
        actor_role_codes: set[str] | None,
    ) -> None:
        normalized_role_codes = {str(role_code) for role_code in (actor_role_codes or set())}
        supported_role_codes = {
            RoleCode.TENANT_ADMIN.value,
            RoleCode.TENANT_USER.value,
            RoleCode.BRAND_USER.value,
        }
        if not normalized_role_codes.intersection(supported_role_codes):
            return
        self.email.send_password_changed_confirmation_email(user.email, user.full_name)

    async def delete_profile(self, user_id) -> PasswordResetResponse:
        # Runs the profile service flow and persists the resulting state before returning it to the route or
        # worker.
        user = await self.users.get(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        user.is_active = False
        await self.session.commit()
        return PasswordResetResponse(message="Account deleted successfully.")

    async def build_current_user_response(self, user_id, role_codes: list[str], brand_space_ids: list) -> CurrentUserResponse:
        # Runs the current user response service flow by coordinating repositories, validators, and
        # integrations, then returns domain data.
        user = await self.users.get(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return CurrentUserResponse(
            user_id=user.id,
            tenant_id=user.tenant_id,
            email=user.email,
            full_name=user.full_name,
            role_codes=role_codes,
            assigned_brand_space_ids=brand_space_ids,
            extra={
                "phone_number": user.phone_number,
                "notifications_enabled": (user.metadata_json or {}).get("notifications_enabled", True),
                "email_notifications_enabled": email_notifications_enabled(getattr(user, "metadata_json", None)),
                "in_app_notifications_enabled": in_app_notifications_enabled(getattr(user, "metadata_json", None)),
                "two_factor_enabled": self.is_two_factor_enabled(user),
            },
        )

    def is_two_factor_enabled(self, user) -> bool:
        # Runs the is two factor enabled service flow by coordinating repositories, validators, and
        # integrations, then returns domain data.
        metadata = user.metadata_json or {}
        return bool(metadata.get(self.TWO_FACTOR_ENABLED_KEY) and metadata.get(self.TWO_FACTOR_SECRET_KEY))

    def get_two_factor_secret(self, user) -> str | None:
        # Runs the two factor secret service flow by coordinating repositories, validators, and integrations,
        # then returns domain data.
        metadata = user.metadata_json or {}
        secret = metadata.get(self.TWO_FACTOR_SECRET_KEY)
        return secret if isinstance(secret, str) else None

    @staticmethod
    def build_otpauth_url(email: str, secret: str) -> str:
        # Runs the otpauth URL service flow by coordinating repositories, validators, and integrations, then
        # returns domain data.
        issuer = "Violyt"
        return (
            f"otpauth://totp/{quote(issuer)}:{quote(email)}"
            f"?secret={quote(secret)}&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30"
        )

    @staticmethod
    def build_qr_code_url(otpauth_url: str) -> str:
        # Runs the qr code URL service flow by coordinating repositories, validators, and integrations, then
        # returns domain data.
        return f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={quote(otpauth_url, safe='')}"
