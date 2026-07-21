from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from app.core.enums import RoleCode
from app.schemas.brand import BrandSectionUpsertRequest, BrandSectionsUpsertRequest, BrandUpdateRequest
from app.services.brand import BrandSpaceService
from app.services.email import EmailDeliveryResult, EmailService


class DummySession:
    def __init__(self) -> None:
        self.commits = 0
        self.refreshed: list[object] = []

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, instance: object) -> None:
        self.refreshed.append(instance)


class ScalarResult:
    def __init__(self, items: list[object]) -> None:
        self.items = items

    def scalars(self) -> "ScalarResult":
        return self

    def all(self) -> list[object]:
        return self.items


def build_brand(**overrides):
    payload = {
        "id": uuid4(),
        "tenant_id": uuid4(),
        "name": "Acme",
        "slug": "acme",
        "description": "Original description",
        "industry_category": "Technology",
        "lifecycle_state": "draft",
        "is_finalized": False,
        "overview_snapshot": {},
        "resolved_brand_context": {},
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def build_user(**overrides):
    payload = {
        "id": uuid4(),
        "tenant_id": uuid4(),
        "email": "user@violyt.ai",
        "full_name": "User",
        "is_active": True,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


async def test_refresh_context_commits_and_refreshes_brand() -> None:
    session = DummySession()
    service = BrandSpaceService(session)
    brand = build_brand()
    snapshot = SimpleNamespace(id=uuid4(), context_json={"identity": {"brand_name": "Acme"}})
    service.validator.refresh_brand_context = AsyncMock(return_value=(brand, snapshot))

    refreshed = await service.refresh_context(brand.id)

    assert refreshed is brand
    service.validator.refresh_brand_context.assert_awaited_once_with(brand.id)


async def test_update_brand_commits_and_refreshes_brand() -> None:
    session = DummySession()
    service = BrandSpaceService(session)
    brand = build_brand()
    service.brands.get_scoped = AsyncMock(return_value=brand)

    updated = await service.update_brand(
        brand.tenant_id,
        brand.id,
        BrandUpdateRequest(
            description="Updated description",
            overview_snapshot={"foundations": {"brand_mission": "Grow"}},
        ),
    )

    assert updated is brand
    assert brand.description == "Updated description"
    assert brand.overview_snapshot == {"foundations": {"brand_mission": "Grow"}}
    assert session.commits == 1
    assert session.refreshed == [brand]


async def test_upsert_guardrails_filters_section_only_metadata_for_orm_write() -> None:
    session = DummySession()
    service = BrandSpaceService(session)
    brand = build_brand()
    captured_section = None
    captured_guardrail = None

    async def capture_section(section):
        nonlocal captured_section
        captured_section = section
        return section

    async def capture_guardrail(guardrail):
        nonlocal captured_guardrail
        captured_guardrail = guardrail
        return guardrail

    service.brands.get_scoped = AsyncMock(return_value=brand)
    service.sections.list_current_sections = AsyncMock(return_value=[])
    service.sections.add = AsyncMock(side_effect=capture_section)
    service.guardrails.list_by_brand = AsyncMock(return_value=[])
    service.guardrails.add = AsyncMock(side_effect=capture_guardrail)
    service.refresh_context = AsyncMock(return_value=brand)

    payload = BrandSectionUpsertRequest(
        section_code="guardrails",
        payload={
            "positive_word_bank": ["clear", "confident"],
            "replaceable_words": ["cheap"],
            "negative_word_bank": ["spammy"],
            "dos": ["Be direct"],
            "donts": ["Use slang"],
            "restricted_topics": ["Politics"],
            "restricted_claims": ["Guaranteed returns"],
            "blocked_words": ["best ever"],
            "custom_rules": ["Avoid hype claims"],
            "positive_word_bank_asset_ids": [str(uuid4())],
            "word_bank_assets": {"positive": [{"name": "approved-words.pdf"}]},
        },
        completion_percent=100,
    )

    updated = await service.upsert_section(brand.tenant_id, brand.id, payload)

    assert updated is brand
    assert captured_section is not None
    assert captured_section.payload["positive_word_bank_asset_ids"]
    assert captured_section.payload["word_bank_assets"]["positive"][0]["name"] == "approved-words.pdf"
    assert captured_guardrail is not None
    assert captured_guardrail.positive_word_bank == ["clear", "confident"]
    assert captured_guardrail.custom_rules == ["Avoid hype claims"]
    assert not hasattr(captured_guardrail, "positive_word_bank_asset_ids")
    assert not hasattr(captured_guardrail, "word_bank_assets")
    assert session.commits == 1
    service.refresh_context.assert_awaited_once_with(brand.id)


async def test_publish_brand_only_requires_identity_section() -> None:
    session = DummySession()
    service = BrandSpaceService(session)
    brand = build_brand()
    identity_section = SimpleNamespace(section_code="identity", payload={"brand_name": "Acme"}, completion_percent=40)
    service.brands.get_scoped = AsyncMock(return_value=brand)
    service.sections.list_current_sections = AsyncMock(return_value=[identity_section])
    service.refresh_context = AsyncMock(return_value=brand)

    published = await service.publish_brand(brand.tenant_id, brand.id)

    assert published is brand
    assert brand.lifecycle_state == "active"
    assert brand.is_finalized is True
    service.refresh_context.assert_awaited_once_with(brand.id)


async def test_unpublish_brand_returns_to_draft() -> None:
    session = DummySession()
    service = BrandSpaceService(session)
    brand = build_brand(lifecycle_state="active", is_finalized=True)
    service.brands.get_scoped = AsyncMock(return_value=brand)

    unpublished = await service.unpublish_brand(brand.tenant_id, brand.id)

    assert unpublished is brand
    assert brand.lifecycle_state == "draft"


def test_brand_space_updated_email_matches_required_copy() -> None:
    service = EmailService()
    service._send_email = Mock(
        return_value=EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email="member@violyt.ai",
        )
    )

    service.send_brand_space_updated_email("member@violyt.ai", "Team Member", "Marketing Assets")

    recipient_email, subject, text_body, html_body = service._send_email.call_args.args
    assert recipient_email == "member@violyt.ai"
    assert subject == "Brand Space Updated"
    assert "Hello Team Member," in text_body
    assert 'The Brand Space "Marketing Assets" has been updated.' in text_body
    assert "latest changes will be applied to all future creative outputs" in text_body
    assert "please sign in to Violyt" in text_body
    assert 'The Brand Space "Marketing Assets" has been updated.' in html_body


async def test_published_brand_space_update_email_recipients_include_all_super_users() -> None:
    session = DummySession()
    service = BrandSpaceService(session)
    tenant_id = uuid4()
    brand_id = uuid4()
    actor = build_user(id=uuid4(), tenant_id=tenant_id, email="admin@violyt.ai", full_name="Tenant Admin")
    assigned_super_user = build_user(
        id=uuid4(),
        tenant_id=tenant_id,
        email="assigned-super@violyt.ai",
        full_name="Assigned Super User",
    )
    tenant_super_user = build_user(
        id=uuid4(),
        tenant_id=tenant_id,
        email="tenant-super@violyt.ai",
        full_name="Tenant Super User",
    )
    brand_user = build_user(id=uuid4(), tenant_id=tenant_id, email="brand@violyt.ai", full_name="Brand User")
    duplicate_brand_user = build_user(id=uuid4(), tenant_id=tenant_id, email="BRAND@violyt.ai", full_name="Duplicate")
    session.execute = AsyncMock(
        side_effect=[
            ScalarResult([actor]),
            ScalarResult([assigned_super_user, tenant_super_user]),
            ScalarResult([brand_user, duplicate_brand_user]),
        ]
    )

    recipients = await service._brand_space_update_email_recipients(tenant_id, brand_id, actor.id)

    assert [recipient.email for recipient in recipients] == [
        "admin@violyt.ai",
        "assigned-super@violyt.ai",
        "tenant-super@violyt.ai",
        "brand@violyt.ai",
    ]


async def test_upsert_sections_dispatches_email_for_published_brand_space_updated_by_tenant_admin() -> None:
    session = DummySession()
    service = BrandSpaceService(session)
    brand = build_brand(lifecycle_state="active")
    service.brands.get_scoped = AsyncMock(return_value=brand)
    service.sections.list_current_sections = AsyncMock(return_value=[])
    service.refresh_context = AsyncMock(return_value=brand)
    service._dispatch_published_brand_space_updated_emails = AsyncMock()

    updated = await service.upsert_sections(
        brand.tenant_id,
        brand.id,
        BrandSectionsUpsertRequest(sections=[]),
        uuid4(),
        {RoleCode.TENANT_ADMIN.value},
    )

    assert updated is brand
    assert session.commits == 1
    service._dispatch_published_brand_space_updated_emails.assert_awaited_once()


async def test_upsert_sections_skips_email_for_draft_brand_space() -> None:
    session = DummySession()
    service = BrandSpaceService(session)
    brand = build_brand(lifecycle_state="draft")
    service.brands.get_scoped = AsyncMock(return_value=brand)
    service.sections.list_current_sections = AsyncMock(return_value=[])
    service.refresh_context = AsyncMock(return_value=brand)
    service._dispatch_published_brand_space_updated_emails = AsyncMock()

    await service.upsert_sections(
        brand.tenant_id,
        brand.id,
        BrandSectionsUpsertRequest(sections=[]),
        uuid4(),
        {RoleCode.TENANT_ADMIN.value},
    )

    service._dispatch_published_brand_space_updated_emails.assert_not_awaited()
