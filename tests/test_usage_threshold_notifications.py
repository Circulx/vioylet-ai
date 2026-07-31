from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.core.enums import RoleCode, UsageMetricCode
from app.services.notification import InAppNotificationService
from app.services.usage import UsageLimitService


@pytest.mark.asyncio
async def test_increment_notifies_only_when_metric_crosses_threshold() -> None:
    session = SimpleNamespace(flush=AsyncMock())
    service = UsageLimitService(session)
    tenant_id = uuid4()
    metric = SimpleNamespace(consumed=79)
    service.limits.get_by_tenant_for_update = AsyncMock(
        return_value=SimpleNamespace(max_content_generations=100)
    )
    service.consumption.get_metric_for_update = AsyncMock(return_value=metric)
    service.limits.get_by_tenant = AsyncMock(
        return_value=SimpleNamespace(max_content_generations=100)
    )

    with patch(
        "app.services.usage.InAppNotificationService.create_usage_threshold_notifications",
        new_callable=AsyncMock,
    ) as create_notifications:
        await service.increment(tenant_id, UsageMetricCode.CONTENT_GENERATIONS)

    assert metric.consumed == 80
    create_notifications.assert_awaited_once()
    call = create_notifications.await_args.kwargs
    assert call["metric_code"] == UsageMetricCode.CONTENT_GENERATIONS.value
    assert call["previous_usage"] == 79
    assert call["current_usage"] == 80
    assert call["configured_limit"] == 100


@pytest.mark.asyncio
@pytest.mark.parametrize("starting_usage", [80, 85])
async def test_increment_does_not_repeat_alert_above_threshold(starting_usage: int) -> None:
    session = SimpleNamespace(flush=AsyncMock())
    service = UsageLimitService(session)
    metric = SimpleNamespace(consumed=starting_usage)
    service.limits.get_by_tenant_for_update = AsyncMock(
        return_value=SimpleNamespace(max_content_generations=100)
    )
    service.consumption.get_metric_for_update = AsyncMock(return_value=metric)
    service.limits.get_by_tenant = AsyncMock(
        return_value=SimpleNamespace(max_content_generations=100)
    )

    with patch(
        "app.services.usage.InAppNotificationService.create_usage_threshold_notifications",
        new_callable=AsyncMock,
    ) as create_notifications:
        await service.increment(uuid4(), UsageMetricCode.CONTENT_GENERATIONS)

    create_notifications.assert_not_awaited()


@pytest.mark.asyncio
async def test_stateful_increment_replaces_stale_brand_space_counter() -> None:
    session = SimpleNamespace(flush=AsyncMock())
    service = UsageLimitService(session)
    metric = SimpleNamespace(consumed=10)
    usage_limit = SimpleNamespace(max_brand_spaces=5)
    service.limits.get_by_tenant_for_update = AsyncMock(return_value=usage_limit)
    service.limits.get_by_tenant = AsyncMock(return_value=usage_limit)
    service.consumption.get_metric_for_update = AsyncMock(return_value=metric)

    with (
        patch(
            "app.services.usage.InAppNotificationService.create_usage_threshold_notifications",
            new_callable=AsyncMock,
        ) as create_warning,
        patch(
            "app.services.usage.InAppNotificationService.create_usage_exhausted_notifications",
            new_callable=AsyncMock,
        ) as create_exhausted,
    ):
        await service.increment(
            uuid4(),
            UsageMetricCode.BRAND_SPACES,
            current_usage=3,
        )

    assert metric.consumed == 4
    create_warning.assert_awaited_once()
    create_exhausted.assert_not_awaited()


@pytest.mark.asyncio
async def test_limit_reduction_can_trigger_crossing() -> None:
    session = SimpleNamespace()
    service = UsageLimitService(session)
    service.limits.get_by_tenant = AsyncMock(
        return_value=SimpleNamespace(max_users=100)
    )

    with patch(
        "app.services.usage.InAppNotificationService.create_usage_threshold_notifications",
        new_callable=AsyncMock,
    ) as create_notifications:
        await service.notify_if_threshold_crossed(
            tenant_id=uuid4(),
            metric_code=UsageMetricCode.USERS,
            previous_usage=80,
            current_usage=80,
            previous_limit=101,
            current_limit=100,
        )

    create_notifications.assert_awaited_once()


@pytest.mark.asyncio
async def test_warning_does_not_trigger_at_one_hundred_percent() -> None:
    session = SimpleNamespace()
    service = UsageLimitService(session)
    service.limits.get_by_tenant = AsyncMock(
        return_value=SimpleNamespace(max_brand_spaces=3)
    )

    with patch(
        "app.services.usage.InAppNotificationService.create_usage_threshold_notifications",
        new_callable=AsyncMock,
    ) as create_notifications:
        await service.notify_if_threshold_crossed(
            tenant_id=uuid4(),
            metric_code=UsageMetricCode.BRAND_SPACES,
            previous_usage=3,
            current_usage=3,
            previous_limit=4,
            current_limit=3,
        )

    create_notifications.assert_not_awaited()


@pytest.mark.asyncio
async def test_warning_triggers_when_usage_crosses_above_eighty_percent() -> None:
    session = SimpleNamespace()
    service = UsageLimitService(session)
    service.limits.get_by_tenant = AsyncMock(
        return_value=SimpleNamespace(max_content_generations=100)
    )

    with patch(
        "app.services.usage.InAppNotificationService.create_usage_threshold_notifications",
        new_callable=AsyncMock,
    ) as create_notifications:
        await service.notify_if_threshold_crossed(
            tenant_id=uuid4(),
            metric_code=UsageMetricCode.CONTENT_GENERATIONS,
            previous_usage=79,
            current_usage=85,
        )

    create_notifications.assert_awaited_once()


@pytest.mark.asyncio
async def test_limit_change_uses_dashboard_usage_instead_of_stale_counter() -> None:
    session = SimpleNamespace()
    service = UsageLimitService(session)
    service.notify_if_threshold_crossed = AsyncMock()
    service.notify_if_exhausted = AsyncMock()

    await service.notify_for_limit_changes(
        uuid4(),
        previous_limits={"max_ocr_pages": 177},
        current_limits={"max_ocr_pages": 176},
        usage_by_metric={UsageMetricCode.OCR_PAGES.value: 141},
    )

    ocr_call = next(
        call
        for call in service.notify_if_threshold_crossed.await_args_list
        if call.kwargs["metric_code"] == UsageMetricCode.OCR_PAGES
    )
    assert ocr_call.kwargs["previous_usage"] == 141
    assert ocr_call.kwargs["current_usage"] == 141
    assert ocr_call.kwargs["previous_limit"] == 177
    assert ocr_call.kwargs["current_limit"] == 176


@pytest.mark.asyncio
async def test_usage_alert_messages_are_role_specific() -> None:
    tenant_id = uuid4()
    tenant_admin = SimpleNamespace(id=uuid4())
    super_user = SimpleNamespace(id=uuid4())
    platform_owner = SimpleNamespace(id=uuid4())
    session = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(name="Acme Corp")))
    service = InAppNotificationService(session)
    service._active_users_by_roles = AsyncMock(return_value=[tenant_admin, super_user])
    service._active_users_by_role = AsyncMock(return_value=[platform_owner])
    service.create = AsyncMock()

    await service.create_usage_threshold_notifications(
        tenant_id=tenant_id,
        metric_code=UsageMetricCode.IMAGE_GENERATIONS,
        period_key="2026-07",
        previous_usage=79,
        current_usage=80,
        configured_limit=100,
    )

    service._active_users_by_roles.assert_awaited_once_with(
        (RoleCode.TENANT_ADMIN, RoleCode.TENANT_USER), tenant_id=tenant_id
    )
    messages = [call.kwargs["message"] for call in service.create.await_args_list]
    assert all(call.kwargs["title"] == "Usage Warning" for call in service.create.await_args_list)
    assert messages == [
        "Your organization has used 80% of its visual-generation capacity.",
        "Your organization has used 80% of its visual-generation capacity.",
        "Acme Corp has used 80% of its visual-generation capacity.",
    ]


@pytest.mark.asyncio
async def test_exact_limit_creates_usage_exhausted_notification() -> None:
    session = SimpleNamespace()
    service = UsageLimitService(session)
    service.limits.get_by_tenant = AsyncMock(
        return_value=SimpleNamespace(max_ocr_pages=100)
    )

    with patch(
        "app.services.usage.InAppNotificationService.create_usage_exhausted_notifications",
        new_callable=AsyncMock,
    ) as create_notifications:
        await service.notify_if_exhausted(
            tenant_id=uuid4(),
            metric_code=UsageMetricCode.OCR_PAGES,
            previous_usage=99,
            current_usage=100,
        )

    create_notifications.assert_awaited_once()


@pytest.mark.asyncio
async def test_usage_above_limit_creates_exhausted_notification() -> None:
    session = SimpleNamespace()
    service = UsageLimitService(session)
    service.limits.get_by_tenant = AsyncMock(
        return_value=SimpleNamespace(max_ocr_pages=100)
    )

    with patch(
        "app.services.usage.InAppNotificationService.create_usage_exhausted_notifications",
        new_callable=AsyncMock,
    ) as create_notifications:
        await service.notify_if_exhausted(
            tenant_id=uuid4(),
            metric_code=UsageMetricCode.OCR_PAGES,
            previous_usage=99,
            current_usage=105,
        )

    create_notifications.assert_awaited_once()


@pytest.mark.asyncio
async def test_usage_exhausted_messages_are_role_specific() -> None:
    tenant_id = uuid4()
    tenant_admin = SimpleNamespace(id=uuid4())
    platform_owner = SimpleNamespace(id=uuid4())
    session = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(name="Acme Corp")))
    service = InAppNotificationService(session)
    service._active_users_by_roles = AsyncMock(return_value=[tenant_admin])
    service._active_users_by_role = AsyncMock(return_value=[platform_owner])
    service.create = AsyncMock()

    await service.create_usage_exhausted_notifications(
        tenant_id=tenant_id,
        metric_code=UsageMetricCode.OCR_PAGES,
        period_key="2026-07",
        previous_usage=99,
        current_usage=100,
        configured_limit=100,
    )

    calls = service.create.await_args_list
    assert calls[0].kwargs["title"] == "Usage Exhausted"
    assert calls[0].kwargs["message"] == (
        "Your organization has reached its allocated OCR-page limit. "
        "Some OCR-processing features may be restricted until additional capacity is available."
    )
    assert calls[1].kwargs["title"] == "Usage Exhausted"
    assert calls[1].kwargs["message"] == "Acme Corp has reached its allocated OCR-page limit."
