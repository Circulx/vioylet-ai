from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.core.enums import RoleCode
from app.services.email import EmailDeliveryResult, EmailService
from app.services.review import ReviewService


class DummySession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


def build_user(**overrides):
    payload = {
        "id": uuid4(),
        "tenant_id": uuid4(),
        "email": "user@acme.com",
        "full_name": "User",
        "is_active": True,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def build_link(**overrides):
    payload = {
        "id": uuid4(),
        "tenant_id": uuid4(),
        "brand_space_id": uuid4(),
        "content_version_id": uuid4(),
        "created_by": uuid4(),
        "token": "review-token",
        "title": "Campaign Review",
        "allow_external_comments": True,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


@pytest.mark.asyncio
async def test_create_link_reused_thread_tracks_current_sharer() -> None:
    session = DummySession()
    service = ReviewService(session)  # type: ignore[arg-type]
    tenant_id = uuid4()
    brand_space_id = uuid4()
    content_version_id = uuid4()
    first_sharer_id = uuid4()
    current_sharer_id = uuid4()
    existing_link = build_link(
        tenant_id=tenant_id,
        brand_space_id=brand_space_id,
        content_version_id=content_version_id,
        created_by=first_sharer_id,
        title="First Share",
    )
    service.contents = SimpleNamespace(get_scoped=AsyncMock(return_value=SimpleNamespace()))
    service.links = SimpleNamespace(get_latest_for_content=AsyncMock(return_value=existing_link))

    link = await service.create_link(
        tenant_id,
        brand_space_id,
        content_version_id,
        current_sharer_id,
        "Current Share",
        True,
    )

    assert link is existing_link
    assert existing_link.created_by == current_sharer_id
    assert existing_link.title == "Current Share"
    assert session.commits == 1


@pytest.mark.asyncio
async def test_comment_notification_recipients_tenant_admin_only_gets_sharer() -> None:
    service = ReviewService(DummySession())  # type: ignore[arg-type]
    sharer = build_user(email="admin@acme.com")
    link = build_link(created_by=sharer.id, tenant_id=sharer.tenant_id)
    service._get_active_user = AsyncMock(return_value=sharer)  # type: ignore[method-assign]
    service._get_notification_role_codes = AsyncMock(  # type: ignore[method-assign]
        return_value={RoleCode.TENANT_ADMIN}
    )

    recipients = await service._comment_notification_recipients(link)  # type: ignore[arg-type]

    assert recipients == [sharer]


@pytest.mark.asyncio
async def test_comment_notification_recipients_super_user_only_gets_sharer() -> None:
    service = ReviewService(DummySession())  # type: ignore[arg-type]
    sharer = build_user(email="super@acme.com")
    link = build_link(created_by=sharer.id, tenant_id=sharer.tenant_id)
    service._get_active_user = AsyncMock(return_value=sharer)  # type: ignore[method-assign]
    service._get_notification_role_codes = AsyncMock(  # type: ignore[method-assign]
        return_value={RoleCode.TENANT_USER}
    )

    recipients = await service._comment_notification_recipients(link)  # type: ignore[arg-type]

    assert recipients == [sharer]


@pytest.mark.asyncio
async def test_comment_notification_recipients_brand_user_only_gets_sharer() -> None:
    service = ReviewService(DummySession())  # type: ignore[arg-type]
    tenant_id = uuid4()
    brand_space_id = uuid4()
    sharer = build_user(tenant_id=tenant_id, email="brand@acme.com")
    link = build_link(
        created_by=sharer.id,
        tenant_id=tenant_id,
        brand_space_id=brand_space_id,
    )
    service._get_active_user = AsyncMock(return_value=sharer)  # type: ignore[method-assign]
    service._get_notification_role_codes = AsyncMock(  # type: ignore[method-assign]
        return_value={RoleCode.BRAND_USER}
    )

    recipients = await service._comment_notification_recipients(link)  # type: ignore[arg-type]

    assert [user.email for user in recipients] == [
        "brand@acme.com",
    ]


@pytest.mark.asyncio
async def test_legacy_brand_user_membership_without_role_rows_only_gets_sharer() -> None:
    service = ReviewService(DummySession())  # type: ignore[arg-type]
    tenant_id = uuid4()
    brand_space_id = uuid4()
    sharer = build_user(tenant_id=tenant_id, email="brand@acme.com")
    link = build_link(
        created_by=sharer.id,
        tenant_id=tenant_id,
        brand_space_id=brand_space_id,
    )
    service._get_active_user = AsyncMock(return_value=sharer)  # type: ignore[method-assign]
    service._get_user_role_codes = AsyncMock(return_value=set())  # type: ignore[method-assign]
    service._infer_user_role_codes_from_brand_membership = AsyncMock(  # type: ignore[method-assign]
        return_value={RoleCode.BRAND_USER}
    )

    recipients = await service._comment_notification_recipients(link)  # type: ignore[arg-type]

    assert [user.email for user in recipients] == [
        "brand@acme.com",
    ]
    service._infer_user_role_codes_from_brand_membership.assert_awaited_once_with(
        sharer.id,
        brand_space_id,
    )


@pytest.mark.asyncio
async def test_add_comment_sends_notifications_after_new_comment_commit() -> None:
    session = DummySession()
    service = ReviewService(session)  # type: ignore[arg-type]
    link = build_link()
    service.links = SimpleNamespace(get=AsyncMock(return_value=link))
    service.comments = SimpleNamespace(add=AsyncMock())
    service.send_comment_notifications_for_comment = AsyncMock()  # type: ignore[method-assign]

    comment = await service.add_comment(
        link.id,
        link.tenant_id,
        link.brand_space_id,
        "Looks good",
        external_author_name="Reviewer",
    )

    assert comment.body == "Looks good"
    assert session.commits == 1
    service.send_comment_notifications_for_comment.assert_awaited_once_with(link.id, comment.id)


@pytest.mark.asyncio
async def test_add_comment_can_defer_notifications_for_background_delivery() -> None:
    session = DummySession()
    service = ReviewService(session)  # type: ignore[arg-type]
    link = build_link()
    service.links = SimpleNamespace(get=AsyncMock(return_value=link))
    service.comments = SimpleNamespace(add=AsyncMock())
    service.send_comment_notifications_for_comment = AsyncMock()  # type: ignore[method-assign]

    comment = await service.add_comment(
        link.id,
        link.tenant_id,
        link.brand_space_id,
        "Looks good",
        external_author_name="Reviewer",
        send_notifications=False,
    )

    assert comment.body == "Looks good"
    assert session.commits == 1
    service.send_comment_notifications_for_comment.assert_not_awaited()


def test_review_comment_notification_email_includes_comment_context() -> None:
    service = EmailService()
    service._send_email = Mock(  # type: ignore[method-assign]
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email="admin@acme.com",
        )
    )

    service.send_review_comment_notification_email(
        "admin@acme.com",
        "Mira Reviewer",
        "Please adjust the headline.",
        "https://app.example.com/review/token",
        "Campaign Review",
    )

    recipient_email, subject, text_body, html_body = service._send_email.call_args.args
    assert recipient_email == "admin@acme.com"
    assert subject == "New comment on Campaign Review"
    assert "Mira Reviewer" in text_body
    assert "Please adjust the headline." in text_body
    assert "Campaign Review" in text_body
    assert "https://app.example.com/review/token" in text_body
    assert html_body

@pytest.mark.asyncio
async def test_comment_email_skips_recipient_with_email_notifications_disabled() -> None:
    service = ReviewService(DummySession())  # type: ignore[arg-type]
    link = build_link()
    comment = SimpleNamespace(author_user_id=uuid4(), body="Please review", id=uuid4())
    recipient = build_user(metadata_json={"email_notifications_enabled": False})
    service._comment_notification_recipients = AsyncMock(return_value=[recipient])
    service._commenter_name = AsyncMock(return_value="Reviewer")
    service.contents = SimpleNamespace(get_scoped=AsyncMock(return_value=SimpleNamespace(title="Campaign")))
    service.email.build_review_link = Mock(return_value="https://example.test/review")
    service.email.send_review_comment_notification_email = Mock()

    await service._send_comment_notifications(link, comment)

    service.email.send_review_comment_notification_email.assert_not_called()
