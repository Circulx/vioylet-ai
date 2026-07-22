from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.enums import RoleCode
from app.services.brand_capacity import BrandCapacityAllocationService
from app.services.notification import InAppNotificationService


def test_brand_capacity_uses_equal_average_without_weights() -> None:
    usage_percent = BrandCapacityAllocationService.equal_average_usage_percent(
        {
            "content_generations": 3000,
            "image_generations": 4500,
            "ocr_pages": 36,
        },
        {
            "content_generations": 5000,
            "image_generations": 5000,
            "ocr_pages": 44,
        },
    )

    assert usage_percent == pytest.approx((60 + 90 + (36 / 44 * 100)) / 3)


def test_brand_capacity_excludes_metrics_without_an_allocated_limit() -> None:
    usage_percent = BrandCapacityAllocationService.equal_average_usage_percent(
        {"content_generations": 80, "image_generations": 40, "ocr_pages": 999},
        {"content_generations": 100, "image_generations": 100, "ocr_pages": 0},
    )

    assert usage_percent == 60


@pytest.mark.asyncio
async def test_brand_capacity_warning_notifies_all_active_tenant_user_roles() -> None:
    tenant_id = uuid4()
    recipients = [SimpleNamespace(id=uuid4()) for _ in range(3)]
    service = InAppNotificationService(SimpleNamespace())
    service._active_users_by_roles = AsyncMock(return_value=recipients)
    service.create = AsyncMock()

    await service.create_brand_capacity_warning_notifications(
        tenant_id=tenant_id,
        brand_space_id=uuid4(),
        brand_name="Jiraaf",
        allocation_percent=25,
        usage_percent=82.4,
        period_key="2026-07",
    )

    service._active_users_by_roles.assert_awaited_once_with(
        (RoleCode.TENANT_ADMIN, RoleCode.TENANT_USER, RoleCode.BRAND_USER),
        tenant_id=tenant_id,
    )
    assert service.create.await_count == 3
    assert all(call.kwargs["title"] == "Capacity Allocation Warning" for call in service.create.await_args_list)
    assert all('"Jiraaf" has reached 80%' in call.kwargs["message"] for call in service.create.await_args_list)


@pytest.mark.asyncio
async def test_two_brands_produce_independent_named_notifications() -> None:
    tenant_id = uuid4()
    recipient = SimpleNamespace(id=uuid4())
    service = InAppNotificationService(SimpleNamespace())
    service._active_users_by_roles = AsyncMock(return_value=[recipient])
    service.create = AsyncMock()

    for brand_name in ("Jiraaf", "Niroggi"):
        await service.create_brand_capacity_warning_notifications(
            tenant_id=tenant_id,
            brand_space_id=uuid4(),
            brand_name=brand_name,
            allocation_percent=25,
            usage_percent=80,
            period_key="2026-07",
        )

    messages = [call.kwargs["message"] for call in service.create.await_args_list]
    assert '"Jiraaf" has reached 80%' in messages[0]
    assert '"Niroggi" has reached 80%' in messages[1]
