from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, Mock, call
from uuid import uuid4

import pytest
from sqlalchemy.sql.dml import Delete, Update

import app.services.auth as auth_service_module
from app.core.exceptions import DuplicateResourceError, LifecycleError
from app.core.enums import RoleCode
from app.core.security import hash_password
from app.models.tenant import ActivationToken
from app.schemas.tenant import (
    TenantCreateRequest,
    TenantLogoUploadRequest,
    TenantUpdateRequest,
    TenantUsageLimitUpdate,
    TenantUserCreateRequest,
    TenantUserUpdateRequest,
)
from app.services.email import EmailDeliveryResult, EmailService
from app.services.auth import AuthService
from app.services.tenant import ACTIVATION_LINK_MAX_SENDS, ACTIVATION_TOKEN_TTL, TenantService


class DummySession:
    def __init__(self) -> None:
        self.commits = 0
        self.refreshed: list[object] = []
        self.scalar = AsyncMock()
        self.execute = AsyncMock()

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, instance: object) -> None:
        self.refreshed.append(instance)


class DummyExecuteResult:
    def __init__(self, value) -> None:  # noqa: ANN001
        self.value = value

    def scalar_one_or_none(self):  # noqa: ANN201
        return self.value


class DummyScalarListResult:
    def __init__(self, values) -> None:  # noqa: ANN001
        self.values = values

    def scalars(self):  # noqa: ANN201
        return self

    def all(self):  # noqa: ANN201
        return self.values


class DummyRowsResult:
    def __init__(self, rows) -> None:  # noqa: ANN001
        self.rows = rows

    def all(self):  # noqa: ANN201
        return self.rows


class DummyStorage:
    def __init__(self) -> None:
        self.deleted: list[str] = []
        self.saved: list[tuple] = []

    def delete(self, storage_path: str) -> None:
        self.deleted.append(storage_path)

    def save_bytes(self, tenant_id, brand_space_id, category, filename, content):  # noqa: ANN001
        self.saved.append((tenant_id, brand_space_id, category, filename, content))
        return SimpleNamespace(storage_path=f"{tenant_id}/global/{category}/{filename}", absolute_path=f"/tmp/{filename}")


def build_tenant(**overrides):
    payload = {
        "id": uuid4(),
        "name": "Acme",
        "slug": "acme",
        "contact_email": "team@acme.com",
        "contact_number": "+91 9000000000",
        "address": "Bengaluru",
        "logo_asset_path": None,
        "is_active": True,
        "metadata_json": {},
        "created_at": datetime.now(timezone.utc),
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def build_admin(**overrides):
    return SimpleNamespace(
        id=uuid4(),
        full_name="Admin User",
        email="admin@acme.com",
        phone_number="+91 9000000001",
        **overrides,
    )


def build_user(**overrides):
    payload = {
        "id": uuid4(),
        "tenant_id": uuid4(),
        "full_name": "Pending User",
        "email": "pending@acme.com",
        "phone_number": "+91 9000000005",
        "is_active": True,
        "is_activated": False,
        "created_at": datetime.now(timezone.utc),
        "last_login_at": None,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def assert_activation_token_expires_in_48_hours(token: ActivationToken) -> None:
    remaining = token.expires_at - datetime.now(timezone.utc)
    assert ACTIVATION_TOKEN_TTL.total_seconds() - 5 <= remaining.total_seconds() <= ACTIVATION_TOKEN_TTL.total_seconds() + 5


async def test_update_tenant_persists_metadata_and_active_flag():
    session = DummySession()
    service = TenantService(session)
    tenant = build_tenant()
    admin = build_admin()
    service.get_tenant = AsyncMock(return_value=tenant)
    service._get_primary_tenant_admin = AsyncMock(return_value=admin)
    service.update_usage_limits = AsyncMock()
    service.users.get_by_email = AsyncMock(return_value=None)

    payload = TenantUpdateRequest(
        metadata_json={"usage_window": {"start_month": "January", "end_month": "December"}},
        is_active=False,
        admin_full_name="Updated Admin",
        admin_email="updated@acme.com",
        admin_phone_number="9999999999",
    )

    updated = await service.update_tenant(tenant.id, payload)

    assert updated is tenant
    assert tenant.is_active is False
    assert tenant.metadata_json == {"usage_window": {"start_month": "January", "end_month": "December"}}
    assert admin.full_name == "Updated Admin"
    assert admin.email == "updated@acme.com"
    assert admin.phone_number == "9999999999"
    assert session.commits == 1
    assert session.refreshed == [tenant]


async def test_delete_tenant_removes_logo_and_commits():
    session = DummySession()
    service = TenantService(session)
    tenant = build_tenant(logo_asset_path="tenant-1/global/tenant-assets/logo.png")
    storage = DummyStorage()
    service.get_tenant = AsyncMock(return_value=tenant)
    service.storage = storage
    session.execute.return_value = DummyScalarListResult([])

    await service.delete_tenant(tenant.id)

    assert storage.deleted == ["tenant-1/global/tenant-assets/logo.png"]
    delete_statements = [
        call.args[0]
        for call in session.execute.await_args_list
        if isinstance(call.args[0], Delete)
    ]
    assert any(statement.table.name == "users" for statement in delete_statements)
    assert delete_statements[-1].table.name == "tenants"
    assert session.commits == 1


async def test_upload_logo_replaces_existing_storage_path():
    session = DummySession()
    service = TenantService(session)
    tenant = build_tenant(logo_asset_path="tenant-1/global/tenant-assets/old-logo.png")
    storage = DummyStorage()
    service.get_tenant = AsyncMock(return_value=tenant)
    service.storage = storage

    payload = TenantLogoUploadRequest(
        filename="tenant-logo.png",
        mime_type="image/png",
        content_base64="data:image/png;base64,aGVsbG8=",
    )

    updated = await service.upload_logo(tenant.id, payload)

    assert updated is tenant
    assert storage.deleted == ["tenant-1/global/tenant-assets/old-logo.png"]
    assert storage.saved[0][2] == "tenant-assets"
    assert storage.saved[0][3] == "tenant-logo.png"
    assert storage.saved[0][4] == b"hello"
    assert tenant.logo_asset_path.endswith("/tenant-logo.png")
    assert session.commits == 1
    assert session.refreshed == [tenant]


async def test_remove_logo_deletes_storage_and_clears_tenant_path():
    session = DummySession()
    service = TenantService(session)
    tenant = build_tenant(logo_asset_path="tenant-1/global/tenant-assets/logo.png")
    storage = DummyStorage()
    service.get_tenant = AsyncMock(return_value=tenant)
    service.storage = storage

    updated = await service.remove_logo(tenant.id)

    assert updated is tenant
    assert storage.deleted == ["tenant-1/global/tenant-assets/logo.png"]
    assert tenant.logo_asset_path is None
    assert session.commits == 1
    assert session.refreshed == [tenant]


async def test_remove_logo_is_noop_when_tenant_has_no_logo():
    session = DummySession()
    service = TenantService(session)
    tenant = build_tenant(logo_asset_path=None)
    storage = DummyStorage()
    service.get_tenant = AsyncMock(return_value=tenant)
    service.storage = storage

    updated = await service.remove_logo(tenant.id)

    assert updated is tenant
    assert storage.deleted == []
    assert session.commits == 0
    assert session.refreshed == []


async def test_get_tenant_summary_includes_primary_admin_and_last_activity():
    session = DummySession()
    service = TenantService(session)
    tenant = build_tenant(metadata_json={"usage_window": {"start_month": "2026-01", "end_month": "2026-12"}})
    admin = build_admin()
    recent_login = datetime.now(timezone.utc)
    service.get_tenant = AsyncMock(return_value=tenant)
    service.usage_limits.get_by_tenant = AsyncMock(
        return_value=SimpleNamespace(
            max_users=10,
            max_brand_spaces=5,
            max_content_generations=20,
            max_image_generations=10,
            max_ocr_pages=50,
        )
    )
    service.get_usage_summary = AsyncMock(
        return_value={
            "limits": {"max_users": 10, "max_brand_spaces": 5, "max_content_generations": 20, "max_image_generations": 10, "max_ocr_pages": 50},
            "consumption": {"users": 4, "brand_spaces": 2, "content_generations": 6, "image_generations": 3, "ocr_pages": 8},
        }
    )
    service.analytics.tenant_summary = AsyncMock(
        return_value={
            "total_users": 4,
            "number_of_brand_spaces": 2,
            "token_usage": {
                "input_tokens": 120,
                "output_tokens": 90,
                "total_tokens": 210,
                "monthly_token_usage": [
                    {"month": "2026-03", "input_tokens": 120, "output_tokens": 90, "total_tokens": 210}
                ],
            },
        }
    )
    service._get_primary_tenant_admin = AsyncMock(return_value=admin)
    session.scalar.side_effect = [4, 2, 6, 3, 8]
    session.execute.return_value = DummyExecuteResult(recent_login)

    summary = await service.get_tenant_summary(tenant.id)

    assert summary["tenant_admin_name"] == "Admin User"
    assert summary["tenant_admin_email"] == "admin@acme.com"
    assert summary["tenant_admin_phone_number"] == "+91 9000000001"
    assert summary["tenant_admin_user_id"] == admin.id
    assert summary["tenant_admin_is_active"] is True
    assert summary["tenant_admin_is_activated"] is False
    assert summary["tenant_admin_activation_link_sent_count"] == 8
    assert summary["tenant_admin_activation_link_attempts_left"] == ACTIVATION_LINK_MAX_SENDS - 8
    assert summary["last_active_at"] == recent_login
    assert summary["brand_space_count"] == 2
    assert summary["usage_consumption"]["content_generations"] == 6
    assert summary["token_usage"]["total_tokens"] == 210
    assert summary["monthly_token_usage"][0]["month"] == "2026-03"


async def test_list_tenant_brand_space_summaries_collects_usage_metrics():
    session = DummySession()
    service = TenantService(session)
    tenant_id = uuid4()
    brand_id = uuid4()
    created_at = datetime.now(timezone.utc)
    recent_login = datetime.now(timezone.utc)
    service.brand_spaces.list_by_tenant = AsyncMock(
        return_value=[
            SimpleNamespace(
                id=brand_id,
                tenant_id=tenant_id,
                name="Jiraaf",
                slug="jiraaf",
                lifecycle_state="active",
                created_at=created_at,
            )
        ]
    )
    session.execute.side_effect = [
        DummyRowsResult([(brand_id, 12)]),
        DummyRowsResult([(brand_id, 7)]),
        DummyRowsResult([(brand_id, 18)]),
        DummyRowsResult([(brand_id, recent_login)]),
    ]

    summaries = await service.list_tenant_brand_space_summaries(tenant_id)

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary["name"] == "Jiraaf"
    assert summary["content_generations"] == 12
    assert summary["visual_generations"] == 7
    assert summary["ocr_pages"] == 18
    assert summary["last_login_at"] == recent_login
    assert summary["last_active_at"] == recent_login


async def test_build_user_summaries_batches_related_data():
    session = DummySession()
    service = TenantService(session)
    first_user = build_user()
    second_user = build_user(tenant_id=first_user.tenant_id, email="second@acme.com")
    role_brand_id = uuid4()
    member_brand_id = uuid4()
    session.execute.side_effect = [
        DummyRowsResult(
            [
                (first_user.id, "tenant_user", None),
                (second_user.id, "brand_user", role_brand_id),
            ]
        ),
        DummyRowsResult([(second_user.id, member_brand_id)]),
        DummyRowsResult([(first_user.id, 2), (second_user.id, 4)]),
    ]

    summaries = await service.build_user_summaries([first_user, second_user])

    assert session.execute.await_count == 3
    assert summaries[0]["role_codes"] == ["tenant_user"]
    assert summaries[0]["activation_link_sent_count"] == 2
    assert summaries[1]["role_codes"] == ["brand_user"]
    assert summaries[1]["brand_space_ids"] == [role_brand_id, member_brand_id]
    assert summaries[1]["activation_link_sent_count"] == 4


async def test_build_user_summary_includes_activation_link_sent_count():
    session = DummySession()
    service = TenantService(session)
    user = build_user()
    service.user_roles.list_for_user = AsyncMock(return_value=[])
    service.brand_members.list_brand_ids_for_user = AsyncMock(return_value=[])
    session.scalar.return_value = 3

    summary = await service.build_user_summary(user)

    assert summary["activation_link_sent_count"] == 3
    assert summary["activation_link_attempts_left"] == ACTIVATION_LINK_MAX_SENDS - 3


async def test_create_tenant_rejects_duplicate_slug():
    session = DummySession()
    service = TenantService(session)
    service.tenants.get_by_slug = AsyncMock(return_value=build_tenant(slug="jiraaf"))
    service.users.get_by_email = AsyncMock(return_value=None)

    payload = TenantCreateRequest(
        name="Jiraaf",
        slug="jiraaf",
        contact_email="team@jiraaf.com",
        contact_number="9876543210",
        address="Bengaluru",
        admin_full_name="Jiraaf Admin",
        admin_email="admin@jiraaf.com",
        admin_phone_number="9000000002",
        usage_limits=TenantUsageLimitUpdate(
            max_users=10,
            max_brand_spaces=5,
            max_content_generations=20,
            max_image_generations=10,
            max_ocr_pages=50,
        ),
        metadata_json={},
    )

    with pytest.raises(DuplicateResourceError, match="Tenant slug 'jiraaf' already exists"):
        await service.create_tenant(payload)

    assert session.commits == 0


async def test_create_tenant_user_rejects_duplicate_email():
    session = DummySession()
    service = TenantService(session)
    tenant_id = uuid4()
    service.users.get_by_email = AsyncMock(return_value=SimpleNamespace(id=uuid4(), email="member@jiraaf.com"))

    payload = TenantUserCreateRequest(
        full_name="Existing Member",
        email="member@jiraaf.com",
        phone_number="+91 9000000003",
        role_code="brand_user",
        brand_space_ids=[],
    )

    with pytest.raises(DuplicateResourceError, match="member@jiraaf.com"):
        await service.create_tenant_user(tenant_id, payload)

    assert session.commits == 0


async def test_create_tenant_user_returns_email_delivery_status():
    session = DummySession()
    service = TenantService(session)
    tenant_id = uuid4()
    role_id = uuid4()

    async def add_user(user):  # noqa: ANN001
        if user.id is None:
            user.id = uuid4()

    service.users.get_by_email = AsyncMock(return_value=None)
    service.users.add = AsyncMock(side_effect=add_user)
    service.roles.get_by_code = AsyncMock(return_value=SimpleNamespace(id=role_id))
    service.user_roles.add = AsyncMock()
    service.tokens.add = AsyncMock()
    service.brand_members.add = AsyncMock()
    service.usage.enforce = AsyncMock()
    service.usage.increment = AsyncMock()
    service.email.send_activation_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=False,
            recipient_email="member@jiraaf.com",
            reason="SMTP authentication failed. Check the sender email password or app password.",
        )
    )

    payload = TenantUserCreateRequest(
        full_name="New Member",
        email="member@jiraaf.com",
        phone_number="+91 9000000004",
        role_code="brand_user",
        brand_space_ids=[],
    )

    user, delivery = await service.create_tenant_user(tenant_id, payload)

    assert user.email == "member@jiraaf.com"
    added_token = service.tokens.add.await_args.args[0]
    assert_activation_token_expires_in_48_hours(added_token)
    assert delivery.delivered is False
    assert delivery.recipient_email == "member@jiraaf.com"
    assert "SMTP authentication failed" in (delivery.reason or "")
    assert session.commits == 1
    assert session.refreshed == [user]


async def test_create_tenant_user_assigns_super_user_role():
    session = DummySession()
    service = TenantService(session)
    tenant_id = uuid4()
    role_id = uuid4()

    async def add_user(user):  # noqa: ANN001
        if user.id is None:
            user.id = uuid4()

    service.users.get_by_email = AsyncMock(return_value=None)
    service.users.add = AsyncMock(side_effect=add_user)
    service.roles.get_by_code = AsyncMock(return_value=SimpleNamespace(id=role_id))
    service.user_roles.add = AsyncMock()
    service.tokens.add = AsyncMock()
    service.brand_members.add = AsyncMock()
    service.usage.enforce = AsyncMock()
    service.usage.increment = AsyncMock()
    service.email.send_activation_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email="super-user@jiraaf.com",
        )
    )

    payload = TenantUserCreateRequest(
        full_name="New Super User",
        email="super-user@jiraaf.com",
        phone_number="+91 9000000005",
        role_code=RoleCode.TENANT_USER,
        brand_space_ids=[],
    )

    user, _delivery = await service.create_tenant_user(tenant_id, payload)

    service.roles.get_by_code.assert_awaited_once_with(RoleCode.TENANT_USER)
    assigned_role = service.user_roles.add.await_args.args[0]
    assert assigned_role.user_id == user.id
    assert assigned_role.role_id == role_id


async def test_create_tenant_user_notifies_admin_about_new_user():
    session = DummySession()
    service = TenantService(session)
    tenant_id = uuid4()
    role_id = uuid4()

    async def add_user(user):  # noqa: ANN001
        if user.id is None:
            user.id = uuid4()

    service.users.get_by_email = AsyncMock(return_value=None)
    service.users.add = AsyncMock(side_effect=add_user)
    service.roles.get_by_code = AsyncMock(return_value=SimpleNamespace(id=role_id))
    service.user_roles.add = AsyncMock()
    service.tokens.add = AsyncMock()
    service.brand_members.add = AsyncMock()
    service.usage.enforce = AsyncMock()
    service.usage.increment = AsyncMock()
    service.email.send_activation_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email="member@jiraaf.com",
        )
    )
    service.email.send_user_created_notification_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email="tenant-admin@jiraaf.com",
        )
    )

    payload = TenantUserCreateRequest(
        full_name="New Member",
        email="member@jiraaf.com",
        phone_number="+91 9000000004",
        role_code="brand_user",
        brand_space_ids=[],
    )

    user, delivery = await service.create_tenant_user(
        tenant_id,
        payload,
        created_by_admin_email="tenant-admin@jiraaf.com",
    )

    service.email.send_activation_email.assert_called_once()
    service.email.send_user_created_notification_email.assert_called_once_with(
        "tenant-admin@jiraaf.com",
        user.full_name,
        user.email,
        "Brand User",
        delivery,
        ANY,
        ANY,
        1,
    )
    assert session.commits == 1


def test_admin_user_created_notification_email_does_not_include_activation_link():
    service = EmailService()
    service._send_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email="tenant-admin@jiraaf.com",
        )
    )

    service.send_user_created_notification_email(
        "tenant-admin@jiraaf.com",
        "New Member",
        "member@jiraaf.com",
        "Brand User",
        EmailDeliveryResult(attempted=True, delivered=True, recipient_email="member@jiraaf.com"),
        datetime(2026, 7, 2, 9, 30, tzinfo=timezone.utc),
        datetime(2026, 7, 4, 9, 30, tzinfo=timezone.utc),
        2,
    )

    recipient_email, subject, text_body, html_body = service._send_email.call_args.args
    assert recipient_email == "tenant-admin@jiraaf.com"
    assert subject == "Activation email sent to New Member"
    assert "Activation email notification" in text_body
    assert "member@jiraaf.com" in text_body
    assert "Activation email sent at: 02/07/2026 09:30 UTC" in text_body
    assert "Activation link valid until: 04/07/2026 09:30 UTC" in text_body
    assert "Total activation email attempts done: 2" in text_body
    assert "/auth/activate" not in text_body
    assert "/auth/activate" not in html_body
    assert "Activate Account" not in html_body
    assert "<a " not in html_body


def test_password_changed_confirmation_email_matches_required_copy():
    service = EmailService()
    service._send_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email="member@violyt.ai",
        )
    )

    service.send_password_changed_confirmation_email("member@violyt.ai", "Team Member")

    recipient_email, subject, text_body, html_body = service._send_email.call_args.args
    assert recipient_email == "member@violyt.ai"
    assert subject == "Your Violyt Password Has Been Changed"
    assert "Hello Team Member," in text_body
    assert "This is a confirmation that the password for your Violyt account has been changed successfully." in text_body
    assert "If you made this change, no further action is required." in text_body
    assert (
        "If you did not change your password, please contact your administrator immediately and "
        "secure your account as soon as possible."
    ) in text_body
    assert "Regards,\nViolyt Team" in text_body
    assert "This is a confirmation that the password for your Violyt account has been changed successfully." in html_body


async def test_profile_change_password_sends_confirmation_email_to_requesting_scoped_user(monkeypatch):
    class DummyNotificationService:
        def __init__(self, session):  # noqa: ANN001
            self.session = session

        async def create_password_changed_notification(self, user):  # noqa: ANN001
            return None

    monkeypatch.setattr(auth_service_module, "InAppNotificationService", DummyNotificationService)
    service = AuthService(DummySession())
    user = build_user(
        email="member@violyt.ai",
        full_name="Team Member",
        hashed_password=hash_password("OldPass123!"),
        metadata_json={"email_notifications_enabled": False},
    )
    service.users.get = AsyncMock(return_value=user)
    service.email.send_password_changed_confirmation_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email="member@violyt.ai",
        )
    )

    response = await service.change_password(
        user.id,
        "OldPass123!",
        "NewPass123!",
        actor_role_codes={RoleCode.TENANT_USER.value},
    )

    assert response.message == "Password updated successfully."
    service.email.send_password_changed_confirmation_email.assert_called_once_with(
        "member@violyt.ai",
        "Team Member",
    )
    assert service.session.commits == 1


async def test_profile_change_password_does_not_send_confirmation_email_to_platform_owner(monkeypatch):
    class DummyNotificationService:
        def __init__(self, session):  # noqa: ANN001
            self.session = session

        async def create_password_changed_notification(self, user):  # noqa: ANN001
            return None

    monkeypatch.setattr(auth_service_module, "InAppNotificationService", DummyNotificationService)
    service = AuthService(DummySession())
    user = build_user(
        email="owner@violyt.ai",
        full_name="Platform Owner",
        hashed_password=hash_password("OldPass123!"),
    )
    service.users.get = AsyncMock(return_value=user)
    service.email.send_password_changed_confirmation_email = Mock()

    await service.change_password(
        user.id,
        "OldPass123!",
        "NewPass123!",
        actor_role_codes={RoleCode.SUPER_ADMIN.value},
    )

    service.email.send_password_changed_confirmation_email.assert_not_called()


def test_two_factor_enabled_email_matches_security_copy():
    service = EmailService()
    service._send_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email="owner@violyt.ai",
        )
    )

    service.send_two_factor_security_email("owner@violyt.ai", "Platform Owner", enabled=True)

    recipient_email, subject, text_body, html_body = service._send_email.call_args.args
    assert recipient_email == "owner@violyt.ai"
    assert subject == "Two-Factor Authentication Enabled"
    assert "Hello Platform Owner," in text_body
    assert "Two-factor authentication has been successfully enabled for your Violyt account." in text_body
    assert "Your account now has an additional layer of security." in text_body
    assert "If you performed this action, no further action is required." in text_body
    assert (
        "If you did not enable two-factor authentication, please contact your administrator "
        "or support team immediately."
    ) in text_body
    assert "Regards,\nViolyt Team" in text_body
    assert "Two-factor authentication has been successfully enabled for your Violyt account." in html_body


def test_two_factor_disabled_email_matches_security_copy():
    service = EmailService()
    service._send_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email="owner@violyt.ai",
        )
    )

    service.send_two_factor_security_email("owner@violyt.ai", "Platform Owner", enabled=False)

    recipient_email, subject, text_body, html_body = service._send_email.call_args.args
    assert recipient_email == "owner@violyt.ai"
    assert subject == "Two-Factor Authentication Disabled"
    assert "Hello Platform Owner," in text_body
    assert "Two-factor authentication has been disabled for your Violyt account." in text_body
    assert "Your account is no longer protected by two-factor authentication." in text_body
    assert "If you performed this action, no further action is required." in text_body
    assert (
        "If you did not disable two-factor authentication, please contact your administrator "
        "or support team immediately."
    ) in text_body
    assert "Regards,\nViolyt Team" in text_body
    assert "Two-factor authentication has been disabled for your Violyt account." in html_body


def test_two_factor_security_email_is_platform_owner_only():
    service = AuthService(DummySession())
    service.email.settings = SimpleNamespace(platform_owner_two_factor_email_recipient=None)
    service.email.send_two_factor_security_email = Mock()
    user = SimpleNamespace(email="owner@violyt.ai", full_name="Platform Owner")

    service._send_platform_owner_two_factor_email(
        user,
        enabled=True,
        actor_role_codes={RoleCode.TENANT_ADMIN.value, RoleCode.TENANT_USER.value},
    )
    service.email.send_two_factor_security_email.assert_not_called()

    service._send_platform_owner_two_factor_email(
        user,
        enabled=True,
        actor_role_codes={RoleCode.SUPER_ADMIN.value},
    )
    service.email.send_two_factor_security_email.assert_called_once_with(
        "owner@violyt.ai",
        "Platform Owner",
        enabled=True,
    )


def test_two_factor_security_email_uses_configured_platform_owner_recipient():
    service = AuthService(DummySession())
    service.email.settings = SimpleNamespace(
        platform_owner_two_factor_email_recipient="shruthimerine271@gmail.com"
    )
    service.email.send_two_factor_security_email = Mock()
    user = SimpleNamespace(email="owner@violyt.ai", full_name="Platform Owner")

    service._send_platform_owner_two_factor_email(
        user,
        enabled=True,
        actor_role_codes={RoleCode.SUPER_ADMIN.value},
    )

    service.email.send_two_factor_security_email.assert_called_once_with(
        "shruthimerine271@gmail.com",
        "Platform Owner",
        enabled=True,
    )


def test_account_deactivated_email_matches_required_copy():
    service = EmailService()
    service._send_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email="super-user@violyt.ai",
        )
    )

    service.send_account_deactivated_email("super-user@violyt.ai", "Super User")

    recipient_email, subject, text_body, html_body = service._send_email.call_args.args
    assert recipient_email == "super-user@violyt.ai"
    assert subject == "Your Violyt Account Has Been Deactivated"
    assert "Hello Super User," in text_body
    assert "Your Violyt account has been deactivated by your Tenant Admin." in text_body
    assert "You will no longer be able to access your account until it is reactivated." in text_body
    assert "If you believe this was done in error, please contact your Tenant Administrator." in text_body
    assert "Regards,\nViolyt Team" in text_body
    assert "Your Violyt account has been deactivated by your Tenant Admin." in html_body


def test_platform_owner_deactivated_tenant_admin_email_matches_required_copy():
    service = EmailService()
    service._send_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email="admin@violyt.ai",
        )
    )

    service.send_account_deactivated_email(
        "admin@violyt.ai",
        "Tenant Admin",
        deactivated_by_platform_owner=True,
    )

    recipient_email, subject, text_body, html_body = service._send_email.call_args.args
    assert recipient_email == "admin@violyt.ai"
    assert subject == "Your Violyt Account Has Been Deactivated"
    assert "Hello Tenant Admin," in text_body
    assert "Your Violyt account has been deactivated by the Platform Owner." in text_body
    assert "If you believe this was done in error, please contact the Platform Owner." in text_body
    assert "Your Violyt account has been deactivated by the Platform Owner." in html_body


def test_user_deactivated_confirmation_email_matches_required_copy():
    service = EmailService()
    service._send_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email="tenant-admin@violyt.ai",
        )
    )

    service.send_user_deactivated_confirmation_email(
        "tenant-admin@violyt.ai",
        "Tenant Admin",
        "Shruthi",
        "Super User",
    )

    recipient_email, subject, text_body, html_body = service._send_email.call_args.args
    assert recipient_email == "tenant-admin@violyt.ai"
    assert subject == "User Account Deactivated"
    assert "Hello Tenant Admin," in text_body
    assert '"Shruthi" (Super User) has been successfully deactivated.' in text_body
    assert '"Shruthi" (Super User) has been successfully deactivated.' in html_body


def test_platform_owner_user_deactivated_email_matches_required_copy():
    service = EmailService()
    service._send_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email="owner@violyt.ai",
        )
    )

    service.send_platform_owner_user_deactivated_email(
        "owner@violyt.ai",
        "Platform Owner",
        "Shruthi",
        "Brand User",
        "Tenant Admin",
        "Acme",
    )

    recipient_email, subject, text_body, html_body = service._send_email.call_args.args
    assert recipient_email == "owner@violyt.ai"
    assert subject == "User Account Deactivated"
    assert "Hello Platform Owner," in text_body
    assert '"Shruthi" (Brand User) has been deactivated by Tenant Admin "Tenant Admin".' in text_body
    assert "Tenant:\nAcme" in text_body
    assert '"Shruthi" (Brand User) has been deactivated by Tenant Admin "Tenant Admin".' in html_body


def test_tenant_admin_deactivated_confirmation_email_matches_required_copy():
    service = EmailService()
    service._send_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email="owner@violyt.ai",
        )
    )

    service.send_tenant_admin_deactivated_confirmation_email(
        "owner@violyt.ai",
        "Platform Owner",
        "Tenant Admin",
        "Acme",
    )

    recipient_email, subject, text_body, html_body = service._send_email.call_args.args
    assert recipient_email == "owner@violyt.ai"
    assert subject == "Tenant Admin Account Deactivated"
    assert "Hello Platform Owner," in text_body
    assert 'Tenant Admin "Tenant Admin" has been successfully deactivated.' in text_body
    assert "Tenant:\nAcme" in text_body
    assert 'Tenant Admin "Tenant Admin" has been successfully deactivated.' in html_body


async def test_user_deactivation_emails_follow_tenant_admin_recipient_rules():
    service = TenantService(DummySession())
    service.email.send_account_deactivated_email = Mock()
    service.email.send_user_deactivated_confirmation_email = Mock()
    service.email.send_platform_owner_user_deactivated_email = Mock()
    service.email.settings = SimpleNamespace(platform_owner_two_factor_email_recipient=None)
    actor = build_user(email="tenant-admin@violyt.ai", full_name="Tenant Admin")
    owner = build_user(email="owner@violyt.ai", full_name="Platform Owner")
    user = build_user(email="member@violyt.ai", full_name="Team Member", metadata_json={"email_notifications_enabled": False})
    tenant = build_tenant(name="Acme")
    service.users.get = AsyncMock(return_value=actor)
    service._active_platform_owners = AsyncMock(return_value=[owner])

    await service._send_user_deactivation_emails(
        user,
        actor.id,
        actor_role_codes={RoleCode.SUPER_ADMIN.value},
        target_role_code=RoleCode.TENANT_USER.value,
        tenant=tenant,
    )
    await service._send_user_deactivation_emails(
        user,
        actor.id,
        actor_role_codes={RoleCode.TENANT_ADMIN.value},
        target_role_code=RoleCode.TENANT_ADMIN.value,
        tenant=tenant,
    )
    service.email.send_account_deactivated_email.assert_not_called()

    await service._send_user_deactivation_emails(
        user,
        actor.id,
        actor_role_codes={RoleCode.TENANT_ADMIN.value},
        target_role_code=RoleCode.TENANT_USER.value,
        tenant=tenant,
    )
    await service._send_user_deactivation_emails(
        user,
        actor.id,
        actor_role_codes={RoleCode.TENANT_ADMIN.value},
        target_role_code=RoleCode.BRAND_USER.value,
        tenant=tenant,
    )

    assert service.email.send_account_deactivated_email.call_args_list == [
        call("member@violyt.ai", "Team Member"),
        call("member@violyt.ai", "Team Member"),
    ]
    assert service.email.send_user_deactivated_confirmation_email.call_args_list == [
        call("tenant-admin@violyt.ai", "Tenant Admin", "Team Member", "Super User"),
        call("tenant-admin@violyt.ai", "Tenant Admin", "Team Member", "Brand User"),
    ]
    assert service.email.send_platform_owner_user_deactivated_email.call_args_list == [
        call("owner@violyt.ai", "Platform Owner", "Team Member", "Super User", "Tenant Admin", "Acme"),
        call("owner@violyt.ai", "Platform Owner", "Team Member", "Brand User", "Tenant Admin", "Acme"),
    ]


async def test_user_deactivation_emails_follow_platform_owner_recipient_rules():
    service = TenantService(DummySession())
    service.email.send_account_deactivated_email = Mock()
    service.email.send_tenant_admin_deactivated_confirmation_email = Mock()
    service.email.settings = SimpleNamespace(platform_owner_two_factor_email_recipient=None)
    actor = build_user(email="owner@violyt.ai", full_name="Platform Owner")
    user = build_user(email="tenant-admin@violyt.ai", full_name="Tenant Admin")
    tenant = build_tenant(name="Acme")
    service.users.get = AsyncMock(return_value=actor)

    await service._send_user_deactivation_emails(
        user,
        actor.id,
        actor_role_codes={RoleCode.SUPER_ADMIN.value},
        target_role_code=RoleCode.TENANT_ADMIN.value,
        tenant=tenant,
    )

    service.email.send_account_deactivated_email.assert_called_once_with(
        "tenant-admin@violyt.ai",
        "Tenant Admin",
        deactivated_by_platform_owner=True,
    )
    service.email.send_tenant_admin_deactivated_confirmation_email.assert_called_once_with(
        "owner@violyt.ai",
        "Platform Owner",
        "Tenant Admin",
        "Acme",
    )


async def test_platform_owner_deactivation_confirmation_uses_actor_email_fallback():
    service = TenantService(DummySession())
    service.email.send_account_deactivated_email = Mock()
    service.email.send_tenant_admin_deactivated_confirmation_email = Mock()
    service.email.settings = SimpleNamespace(platform_owner_two_factor_email_recipient=None)
    user = build_user(email="tenant-admin@violyt.ai", full_name="Tenant Admin")
    tenant = build_tenant(name="Acme")
    service.users.get = AsyncMock(return_value=None)

    await service._send_user_deactivation_emails(
        user,
        uuid4(),
        actor_role_codes={RoleCode.SUPER_ADMIN.value},
        target_role_code=RoleCode.TENANT_ADMIN.value,
        tenant=tenant,
        actor_email="owner@violyt.ai",
    )

    service.email.send_account_deactivated_email.assert_called_once_with(
        "tenant-admin@violyt.ai",
        "Tenant Admin",
        deactivated_by_platform_owner=True,
    )
    service.email.send_tenant_admin_deactivated_confirmation_email.assert_called_once_with(
        "owner@violyt.ai",
        "Platform Owner",
        "Tenant Admin",
        "Acme",
    )


async def test_account_status_platform_owner_email_uses_configured_recipient_for_tenant_admin_flow():
    service = TenantService(DummySession())
    service.email.send_account_deactivated_email = Mock()
    service.email.send_user_deactivated_confirmation_email = Mock()
    service.email.send_platform_owner_user_deactivated_email = Mock()
    service.email.settings = SimpleNamespace(
        platform_owner_two_factor_email_recipient="shruthimerine271@gmail.com"
    )
    actor = build_user(email="tenant-admin@violyt.ai", full_name="Tenant Admin")
    user = build_user(email="member@violyt.ai", full_name="Team Member", metadata_json={"email_notifications_enabled": False})
    tenant = build_tenant(name="Acme")
    service.users.get = AsyncMock(return_value=actor)
    service._active_platform_owners = AsyncMock()

    await service._send_user_deactivation_emails(
        user,
        actor.id,
        actor_role_codes={RoleCode.TENANT_ADMIN.value},
        target_role_code=RoleCode.TENANT_USER.value,
        tenant=tenant,
    )

    service._active_platform_owners.assert_not_called()
    service.email.send_platform_owner_user_deactivated_email.assert_called_once_with(
        "shruthimerine271@gmail.com",
        "Platform Owner",
        "Team Member",
        "Super User",
        "Tenant Admin",
        "Acme",
    )


async def test_account_status_platform_owner_confirmation_uses_configured_recipient():
    service = TenantService(DummySession())
    service.email.send_account_deactivated_email = Mock()
    service.email.send_tenant_admin_deactivated_confirmation_email = Mock()
    service.email.settings = SimpleNamespace(
        platform_owner_two_factor_email_recipient="shruthimerine271@gmail.com"
    )
    actor = build_user(email="owner@violyt.ai", full_name="Platform Owner")
    user = build_user(email="tenant-admin@violyt.ai", full_name="Tenant Admin")
    tenant = build_tenant(name="Acme")
    service.users.get = AsyncMock(return_value=actor)

    await service._send_user_deactivation_emails(
        user,
        actor.id,
        actor_role_codes={RoleCode.SUPER_ADMIN.value},
        target_role_code=RoleCode.TENANT_ADMIN.value,
        tenant=tenant,
    )

    service.email.send_tenant_admin_deactivated_confirmation_email.assert_called_once_with(
        "shruthimerine271@gmail.com",
        "Platform Owner",
        "Tenant Admin",
        "Acme",
    )


def test_account_reactivated_email_matches_required_copy():
    service = EmailService()
    service._send_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email="super-user@violyt.ai",
        )
    )

    service.send_account_reactivated_email("super-user@violyt.ai", "Super User")

    recipient_email, subject, text_body, html_body = service._send_email.call_args.args
    assert recipient_email == "super-user@violyt.ai"
    assert subject == "Your Violyt Account Has Been Reactivated"
    assert "Hello Super User," in text_body
    assert "Your Violyt account has been reactivated by your Tenant Admin." in text_body
    assert "You can now sign in and access your account again." in text_body
    assert "Regards,\nViolyt Team" in text_body
    assert "Your Violyt account has been reactivated by your Tenant Admin." in html_body


def test_platform_owner_reactivated_tenant_admin_email_matches_required_copy():
    service = EmailService()
    service._send_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email="admin@violyt.ai",
        )
    )

    service.send_account_reactivated_email(
        "admin@violyt.ai",
        "Tenant Admin",
        reactivated_by_platform_owner=True,
    )

    recipient_email, subject, text_body, html_body = service._send_email.call_args.args
    assert recipient_email == "admin@violyt.ai"
    assert subject == "Your Violyt Account Has Been Reactivated"
    assert "Hello Tenant Admin," in text_body
    assert "Your Violyt account has been reactivated by the Platform Owner." in text_body
    assert "You can now sign in and access your account again." in text_body
    assert "Your Violyt account has been reactivated by the Platform Owner." in html_body


def test_user_reactivated_confirmation_email_matches_required_copy():
    service = EmailService()
    service._send_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email="tenant-admin@violyt.ai",
        )
    )

    service.send_user_reactivated_confirmation_email(
        "tenant-admin@violyt.ai",
        "Tenant Admin",
        "Shruthi",
        "Super User",
    )

    recipient_email, subject, text_body, html_body = service._send_email.call_args.args
    assert recipient_email == "tenant-admin@violyt.ai"
    assert subject == "User Account Reactivated"
    assert "Hello Tenant Admin," in text_body
    assert '"Shruthi" (Super User) has been successfully reactivated.' in text_body
    assert '"Shruthi" (Super User) has been successfully reactivated.' in html_body


def test_platform_owner_user_reactivated_email_matches_required_copy():
    service = EmailService()
    service._send_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email="owner@violyt.ai",
        )
    )

    service.send_platform_owner_user_reactivated_email(
        "owner@violyt.ai",
        "Platform Owner",
        "Shruthi",
        "Brand User",
        "Tenant Admin",
        "Acme",
    )

    recipient_email, subject, text_body, html_body = service._send_email.call_args.args
    assert recipient_email == "owner@violyt.ai"
    assert subject == "User Account Reactivated"
    assert "Hello Platform Owner," in text_body
    assert '"Shruthi" (Brand User) has been reactivated by Tenant Admin "Tenant Admin".' in text_body
    assert "Tenant:\nAcme" in text_body
    assert '"Shruthi" (Brand User) has been reactivated by Tenant Admin "Tenant Admin".' in html_body


def test_tenant_admin_reactivated_confirmation_email_matches_required_copy():
    service = EmailService()
    service._send_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email="owner@violyt.ai",
        )
    )

    service.send_tenant_admin_reactivated_confirmation_email(
        "owner@violyt.ai",
        "Platform Owner",
        "Tenant Admin",
        "Acme",
    )

    recipient_email, subject, text_body, html_body = service._send_email.call_args.args
    assert recipient_email == "owner@violyt.ai"
    assert subject == "Tenant Admin Account Reactivated"
    assert "Hello Platform Owner," in text_body
    assert 'Tenant Admin "Tenant Admin" has been successfully reactivated.' in text_body
    assert "Tenant:\nAcme" in text_body
    assert 'Tenant Admin "Tenant Admin" has been successfully reactivated.' in html_body


async def test_user_reactivation_emails_follow_tenant_admin_recipient_rules():
    service = TenantService(DummySession())
    service.email.send_account_reactivated_email = Mock()
    service.email.send_user_reactivated_confirmation_email = Mock()
    service.email.send_platform_owner_user_reactivated_email = Mock()
    service.email.settings = SimpleNamespace(platform_owner_two_factor_email_recipient=None)
    actor = build_user(email="tenant-admin@violyt.ai", full_name="Tenant Admin")
    owner = build_user(email="owner@violyt.ai", full_name="Platform Owner")
    user = build_user(email="member@violyt.ai", full_name="Team Member", metadata_json={"email_notifications_enabled": False})
    tenant = build_tenant(name="Acme")
    service.users.get = AsyncMock(return_value=actor)
    service._active_platform_owners = AsyncMock(return_value=[owner])

    await service._send_user_reactivation_emails(
        user,
        actor.id,
        actor_role_codes={RoleCode.SUPER_ADMIN.value},
        target_role_code=RoleCode.TENANT_USER.value,
        tenant=tenant,
    )
    await service._send_user_reactivation_emails(
        user,
        actor.id,
        actor_role_codes={RoleCode.TENANT_ADMIN.value},
        target_role_code=RoleCode.TENANT_ADMIN.value,
        tenant=tenant,
    )
    service.email.send_account_reactivated_email.assert_not_called()

    await service._send_user_reactivation_emails(
        user,
        actor.id,
        actor_role_codes={RoleCode.TENANT_ADMIN.value},
        target_role_code=RoleCode.TENANT_USER.value,
        tenant=tenant,
    )
    await service._send_user_reactivation_emails(
        user,
        actor.id,
        actor_role_codes={RoleCode.TENANT_ADMIN.value},
        target_role_code=RoleCode.BRAND_USER.value,
        tenant=tenant,
    )

    assert service.email.send_account_reactivated_email.call_args_list == [
        call("member@violyt.ai", "Team Member"),
        call("member@violyt.ai", "Team Member"),
    ]
    assert service.email.send_user_reactivated_confirmation_email.call_args_list == [
        call("tenant-admin@violyt.ai", "Tenant Admin", "Team Member", "Super User"),
        call("tenant-admin@violyt.ai", "Tenant Admin", "Team Member", "Brand User"),
    ]
    assert service.email.send_platform_owner_user_reactivated_email.call_args_list == [
        call("owner@violyt.ai", "Platform Owner", "Team Member", "Super User", "Tenant Admin", "Acme"),
        call("owner@violyt.ai", "Platform Owner", "Team Member", "Brand User", "Tenant Admin", "Acme"),
    ]


async def test_user_reactivation_emails_follow_platform_owner_recipient_rules():
    service = TenantService(DummySession())
    service.email.send_account_reactivated_email = Mock()
    service.email.send_tenant_admin_reactivated_confirmation_email = Mock()
    service.email.settings = SimpleNamespace(platform_owner_two_factor_email_recipient=None)
    actor = build_user(email="owner@violyt.ai", full_name="Platform Owner")
    user = build_user(email="tenant-admin@violyt.ai", full_name="Tenant Admin")
    tenant = build_tenant(name="Acme")
    service.users.get = AsyncMock(return_value=actor)

    await service._send_user_reactivation_emails(
        user,
        actor.id,
        actor_role_codes={RoleCode.SUPER_ADMIN.value},
        target_role_code=RoleCode.TENANT_ADMIN.value,
        tenant=tenant,
    )

    service.email.send_account_reactivated_email.assert_called_once_with(
        "tenant-admin@violyt.ai",
        "Tenant Admin",
        reactivated_by_platform_owner=True,
    )
    service.email.send_tenant_admin_reactivated_confirmation_email.assert_called_once_with(
        "owner@violyt.ai",
        "Platform Owner",
        "Tenant Admin",
        "Acme",
    )


async def test_platform_owner_reactivation_confirmation_uses_actor_email_fallback():
    service = TenantService(DummySession())
    service.email.send_account_reactivated_email = Mock()
    service.email.send_tenant_admin_reactivated_confirmation_email = Mock()
    service.email.settings = SimpleNamespace(platform_owner_two_factor_email_recipient=None)
    user = build_user(email="tenant-admin@violyt.ai", full_name="Tenant Admin")
    tenant = build_tenant(name="Acme")
    service.users.get = AsyncMock(return_value=None)

    await service._send_user_reactivation_emails(
        user,
        uuid4(),
        actor_role_codes={RoleCode.SUPER_ADMIN.value},
        target_role_code=RoleCode.TENANT_ADMIN.value,
        tenant=tenant,
        actor_email="owner@violyt.ai",
    )

    service.email.send_account_reactivated_email.assert_called_once_with(
        "tenant-admin@violyt.ai",
        "Tenant Admin",
        reactivated_by_platform_owner=True,
    )
    service.email.send_tenant_admin_reactivated_confirmation_email.assert_called_once_with(
        "owner@violyt.ai",
        "Platform Owner",
        "Tenant Admin",
        "Acme",
    )


async def test_reactivation_platform_owner_email_uses_configured_recipient_for_tenant_admin_flow():
    service = TenantService(DummySession())
    service.email.send_account_reactivated_email = Mock()
    service.email.send_user_reactivated_confirmation_email = Mock()
    service.email.send_platform_owner_user_reactivated_email = Mock()
    service.email.settings = SimpleNamespace(
        platform_owner_two_factor_email_recipient="shruthimerine271@gmail.com"
    )
    actor = build_user(email="tenant-admin@violyt.ai", full_name="Tenant Admin")
    user = build_user(email="member@violyt.ai", full_name="Team Member", metadata_json={"email_notifications_enabled": False})
    tenant = build_tenant(name="Acme")
    service.users.get = AsyncMock(return_value=actor)
    service._active_platform_owners = AsyncMock()

    await service._send_user_reactivation_emails(
        user,
        actor.id,
        actor_role_codes={RoleCode.TENANT_ADMIN.value},
        target_role_code=RoleCode.TENANT_USER.value,
        tenant=tenant,
    )

    service._active_platform_owners.assert_not_called()
    service.email.send_platform_owner_user_reactivated_email.assert_called_once_with(
        "shruthimerine271@gmail.com",
        "Platform Owner",
        "Team Member",
        "Super User",
        "Tenant Admin",
        "Acme",
    )


async def test_reactivation_platform_owner_confirmation_uses_configured_recipient():
    service = TenantService(DummySession())
    service.email.send_account_reactivated_email = Mock()
    service.email.send_tenant_admin_reactivated_confirmation_email = Mock()
    service.email.settings = SimpleNamespace(
        platform_owner_two_factor_email_recipient="shruthimerine271@gmail.com"
    )
    actor = build_user(email="owner@violyt.ai", full_name="Platform Owner")
    user = build_user(email="tenant-admin@violyt.ai", full_name="Tenant Admin")
    tenant = build_tenant(name="Acme")
    service.users.get = AsyncMock(return_value=actor)

    await service._send_user_reactivation_emails(
        user,
        actor.id,
        actor_role_codes={RoleCode.SUPER_ADMIN.value},
        target_role_code=RoleCode.TENANT_ADMIN.value,
        tenant=tenant,
    )

    service.email.send_tenant_admin_reactivated_confirmation_email.assert_called_once_with(
        "shruthimerine271@gmail.com",
        "Platform Owner",
        "Tenant Admin",
        "Acme",
    )


async def test_create_tenant_returns_email_delivery_status():
    session = DummySession()
    service = TenantService(session)
    tenant_id = uuid4()
    role_id = uuid4()

    async def add_tenant(tenant):  # noqa: ANN001
        tenant.id = tenant_id

    async def add_user(user):  # noqa: ANN001
        if user.id is None:
            user.id = uuid4()

    service.tenants.get_by_slug = AsyncMock(return_value=None)
    service.users.get_by_email = AsyncMock(return_value=None)
    service.tenants.add = AsyncMock(side_effect=add_tenant)
    service.users.add = AsyncMock(side_effect=add_user)
    service.roles.get_by_code = AsyncMock(return_value=SimpleNamespace(id=role_id))
    service.user_roles.add = AsyncMock()
    service.tokens.add = AsyncMock()
    service.usage_limits.add = AsyncMock()
    service.usage.increment = AsyncMock()
    service.email.send_activation_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=False,
            recipient_email="admin@jiraaf.com",
            reason="SMTP authentication failed. Check the sender email password or app password.",
        )
    )

    payload = TenantCreateRequest(
        name="Jiraaf",
        slug="jiraaf-new",
        contact_email="team@jiraaf.com",
        contact_number="9876543210",
        address="Bengaluru",
        admin_full_name="Jiraaf Admin",
        admin_email="admin@jiraaf.com",
        admin_phone_number="9000000002",
        usage_limits=TenantUsageLimitUpdate(
            max_users=10,
            max_brand_spaces=5,
            max_content_generations=20,
            max_image_generations=10,
            max_ocr_pages=50,
        ),
        metadata_json={},
    )

    tenant, delivery = await service.create_tenant(payload)

    assert tenant.id == tenant_id
    added_token = service.tokens.add.await_args.args[0]
    assert_activation_token_expires_in_48_hours(added_token)
    assert delivery.delivered is False
    assert delivery.recipient_email == "admin@jiraaf.com"
    assert "SMTP authentication failed" in (delivery.reason or "")
    assert session.commits == 1
    assert session.refreshed == [tenant]


async def test_resend_activation_link_refreshes_token_and_sends_email():
    session = DummySession()
    service = TenantService(session)
    tenant_id = uuid4()
    user = build_user(tenant_id=tenant_id, metadata_json={"email_notifications_enabled": False})
    service.users.get = AsyncMock(return_value=user)
    service.tokens.add = AsyncMock()
    session.scalar.return_value = 1
    service.email.send_activation_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email=user.email,
        )
    )

    delivery = await service.resend_activation_link(tenant_id, user.id)

    update_statements = [
        call.args[0]
        for call in session.execute.await_args_list
        if isinstance(call.args[0], Update)
    ]
    assert len(update_statements) == 1
    added_token = service.tokens.add.await_args.args[0]
    assert isinstance(added_token, ActivationToken)
    assert added_token.user_id == user.id
    assert_activation_token_expires_in_48_hours(added_token)
    service.email.send_activation_email.assert_called_once_with(user.email, user.full_name, added_token.token)
    assert delivery.delivered is True
    assert session.commits == 1


async def test_resend_activation_link_notifies_admin_with_total_attempts():
    session = DummySession()
    service = TenantService(session)
    tenant_id = uuid4()
    user = build_user(tenant_id=tenant_id, metadata_json={"email_notifications_enabled": False})
    service.users.get = AsyncMock(return_value=user)
    service.tokens.add = AsyncMock()
    session.scalar.return_value = 3
    service.email.send_activation_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email=user.email,
        )
    )
    service.email.send_user_created_notification_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email="tenant-admin@jiraaf.com",
        )
    )

    delivery = await service.resend_activation_link(
        tenant_id,
        user.id,
        triggered_by_admin_email="tenant-admin@jiraaf.com",
    )

    added_token = service.tokens.add.await_args.args[0]
    service.email.send_activation_email.assert_called_once_with(user.email, user.full_name, added_token.token)
    service.email.send_user_created_notification_email.assert_called_once_with(
        "tenant-admin@jiraaf.com",
        user.full_name,
        user.email,
        "User",
        delivery,
        ANY,
        added_token.expires_at,
        4,
    )


async def test_resend_activation_link_rejects_when_attempt_limit_reached():
    session = DummySession()
    service = TenantService(session)
    tenant_id = uuid4()
    user = build_user(tenant_id=tenant_id)
    service.users.get = AsyncMock(return_value=user)
    session.scalar.return_value = ACTIVATION_LINK_MAX_SENDS

    with pytest.raises(LifecycleError, match="attempt limit"):
        await service.resend_activation_link(tenant_id, user.id)

    assert session.commits == 0


async def test_resend_activation_link_rejects_already_activated_user():
    session = DummySession()
    service = TenantService(session)
    tenant_id = uuid4()
    user = build_user(tenant_id=tenant_id, is_activated=True)
    service.users.get = AsyncMock(return_value=user)

    with pytest.raises(LifecycleError, match="pending users"):
        await service.resend_activation_link(tenant_id, user.id)

    assert session.commits == 0


async def test_deactivate_user_rejects_pending_user():
    session = DummySession()
    service = TenantService(session)
    tenant_id = uuid4()
    user = build_user(tenant_id=tenant_id, is_active=True, is_activated=False)
    service.users.get = AsyncMock(return_value=user)

    with pytest.raises(LifecycleError, match="before account activation"):
        await service.deactivate_user(tenant_id, user.id)

    assert user.is_active is True
    assert session.commits == 0


async def test_update_tenant_user_rejects_pending_user_account_status_change():
    session = DummySession()
    service = TenantService(session)
    tenant_id = uuid4()
    user = build_user(tenant_id=tenant_id, is_active=False, is_activated=False)
    service.users.get = AsyncMock(return_value=user)

    with pytest.raises(LifecycleError, match="before activation"):
        await service.update_tenant_user(
            tenant_id,
            user.id,
            TenantUserUpdateRequest(is_active=True),
        )

    assert user.is_active is False
    assert session.commits == 0


async def test_update_profile_persists_notification_channels_independently():
    session = DummySession()
    service = AuthService(session)
    user = build_user(metadata_json={"notifications_enabled": True})
    service.users.get = AsyncMock(return_value=user)

    updated = await service.update_profile(
        user.id,
        None,
        None,
        None,
        None,
        email_notifications_preference=False,
        in_app_notifications_preference=True,
    )

    assert updated.metadata_json["notifications_enabled"] is True
    assert updated.metadata_json["email_notifications_enabled"] is False
    assert updated.metadata_json["in_app_notifications_enabled"] is True
    assert session.commits == 1
    assert session.refreshed == [user]

async def test_password_reset_request_sends_email_when_email_notifications_are_disabled():
    session = DummySession()
    service = AuthService(session)
    user = build_user(
        email="member@violyt.ai",
        full_name="Team Member",
        metadata_json={"email_notifications_enabled": False},
    )
    service.users.get_by_email = AsyncMock(return_value=user)
    service.tokens.add = AsyncMock()
    service.email.send_password_reset_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email=user.email,
        )
    )

    response = await service.forgot_password(user.email)

    assert response.message == "If the email exists, a reset link has been sent."
    service.email.send_password_reset_email.assert_called_once_with(user.email, user.full_name, ANY)
    assert session.commits == 1
