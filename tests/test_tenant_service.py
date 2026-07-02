from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.sql.dml import Delete, Update

from app.core.exceptions import DuplicateResourceError, LifecycleError
from app.models.tenant import ActivationToken
from app.schemas.tenant import (
    TenantCreateRequest,
    TenantLogoUploadRequest,
    TenantUpdateRequest,
    TenantUsageLimitUpdate,
    TenantUserCreateRequest,
)
from app.services.email import EmailDeliveryResult, EmailService
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
        admin_phone_number="+91 9999999999",
    )

    updated = await service.update_tenant(tenant.id, payload)

    assert updated is tenant
    assert tenant.is_active is False
    assert tenant.metadata_json == {"usage_window": {"start_month": "January", "end_month": "December"}}
    assert admin.full_name == "Updated Admin"
    assert admin.email == "updated@acme.com"
    assert admin.phone_number == "+91 9999999999"
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
    session.scalar.side_effect = [12, 7, 18, recent_login]

    summaries = await service.list_tenant_brand_space_summaries(tenant_id)

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary["name"] == "Jiraaf"
    assert summary["content_generations"] == 12
    assert summary["visual_generations"] == 7
    assert summary["ocr_pages"] == 18
    assert summary["last_login_at"] == recent_login
    assert summary["last_active_at"] == recent_login


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
        contact_number="+91 9876543210",
        address="Bengaluru",
        admin_full_name="Jiraaf Admin",
        admin_email="admin@jiraaf.com",
        admin_phone_number="+91 9000000002",
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
        contact_number="+91 9876543210",
        address="Bengaluru",
        admin_full_name="Jiraaf Admin",
        admin_email="admin@jiraaf.com",
        admin_phone_number="+91 9000000002",
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
    user = build_user(tenant_id=tenant_id)
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
    user = build_user(tenant_id=tenant_id)
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
