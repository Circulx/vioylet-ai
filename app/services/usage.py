# Service classes hold business workflows between the HTTP layer, repositories, and integrations.
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UsageMetricCode
from app.core.exceptions import UsageLimitExceededError
from app.models.collaboration import UsageConsumption
from app.repositories.collaboration import UsageConsumptionRepository, UsageLimitRepository
from app.services.notification import InAppNotificationService
from app.utils.text import current_period_key


class UsageLimitService:
    ALERT_THRESHOLD = 80
    # Business layer for usage limit; routes and workers pass validated inputs here and receive domain results
    # back.
    FIELD_MAP = {
        UsageMetricCode.USERS: "max_users",
        UsageMetricCode.BRAND_SPACES: "max_brand_spaces",
        UsageMetricCode.CONTENT_GENERATIONS: "max_content_generations",
        UsageMetricCode.IMAGE_GENERATIONS: "max_image_generations",
        UsageMetricCode.OCR_PAGES: "max_ocr_pages",
    }

    def __init__(self, session: AsyncSession) -> None:
        # Wires the repositories and helper services this workflow reuses across its public methods.
        self.session = session
        self.limits = UsageLimitRepository(session)
        self.consumption = UsageConsumptionRepository(session)

    async def enforce(self, tenant_id: UUID, metric_code: str, amount: int = 1) -> None:
        # Runs the enforce service flow by coordinating repositories, validators, and integrations, then returns
        # domain data.
        usage_limit = await self.limits.get_by_tenant(tenant_id)
        if not usage_limit:
            return
        limit_field = self.FIELD_MAP[metric_code]
        limit_value = getattr(usage_limit, limit_field)
        period_key = current_period_key()
        consumption = await self.consumption.get_metric(tenant_id, metric_code, period_key)
        current_value = consumption.consumed if consumption else 0
        if current_value + amount > limit_value:
            raise UsageLimitExceededError(f"Usage limit exceeded for {metric_code}")

    async def increment(self, tenant_id: UUID, metric_code: str, amount: int = 1) -> None:
        # Runs the increment service flow and persists the resulting state before returning it to the route or
        # worker.
        period_key = current_period_key()
        # The limits row always exists for configured tenants and serializes even first-time metric increments.
        usage_limit = await self.limits.get_by_tenant_for_update(tenant_id)
        metric = await self.consumption.get_metric_for_update(tenant_id, metric_code, period_key)
        if not metric:
            metric = UsageConsumption(
                tenant_id=tenant_id,
                metric_code=metric_code,
                period_key=period_key,
                consumed=0,
                metadata_json={},
            )
            await self.consumption.add(metric)
        previous_usage = int(metric.consumed or 0)
        metric.consumed = previous_usage + amount
        await self.session.flush()
        await self.notify_if_threshold_crossed(
            tenant_id=tenant_id,
            metric_code=metric_code,
            previous_usage=previous_usage,
            current_usage=metric.consumed,
            period_key=period_key,
            current_limit=(
                int(getattr(usage_limit, self.FIELD_MAP[metric_code]) or 0)
                if usage_limit and metric_code in self.FIELD_MAP
                else None
            ),
        )
        await self.notify_if_exhausted(
            tenant_id=tenant_id,
            metric_code=metric_code,
            previous_usage=previous_usage,
            current_usage=metric.consumed,
            period_key=period_key,
            current_limit=(
                int(getattr(usage_limit, self.FIELD_MAP[metric_code]) or 0)
                if usage_limit and metric_code in self.FIELD_MAP
                else None
            ),
        )

    async def notify_if_threshold_crossed(
        self,
        *,
        tenant_id: UUID,
        metric_code: str,
        previous_usage: int,
        current_usage: int,
        period_key: str | None = None,
        previous_limit: int | None = None,
        current_limit: int | None = None,
    ) -> None:
        usage_limit = await self.limits.get_by_tenant(tenant_id)
        if not usage_limit or metric_code not in self.FIELD_MAP:
            return
        limit_field = self.FIELD_MAP[metric_code]
        current_limit = int(current_limit if current_limit is not None else getattr(usage_limit, limit_field) or 0)
        previous_limit = int(previous_limit if previous_limit is not None else current_limit)
        if previous_limit <= 0 or current_limit <= 0:
            return
        threshold = self.ALERT_THRESHOLD
        was_below = previous_usage * 100 < previous_limit * threshold
        is_exact_threshold = current_usage * 100 == current_limit * threshold
        if not (was_below and is_exact_threshold):
            return
        await InAppNotificationService(self.session).create_usage_threshold_notifications(
            tenant_id=tenant_id,
            metric_code=str(metric_code),
            period_key=period_key or current_period_key(),
            previous_usage=previous_usage,
            current_usage=current_usage,
            configured_limit=current_limit,
            threshold=threshold,
        )
        return

    async def notify_if_exhausted(
        self,
        *,
        tenant_id: UUID,
        metric_code: str,
        previous_usage: int,
        current_usage: int,
        period_key: str | None = None,
        previous_limit: int | None = None,
        current_limit: int | None = None,
    ) -> None:
        usage_limit = await self.limits.get_by_tenant(tenant_id)
        if not usage_limit or metric_code not in self.FIELD_MAP:
            return
        limit_field = self.FIELD_MAP[metric_code]
        current_limit = int(current_limit if current_limit is not None else getattr(usage_limit, limit_field) or 0)
        previous_limit = int(previous_limit if previous_limit is not None else current_limit)
        if previous_limit <= 0 or current_limit <= 0:
            return
        was_below = previous_usage < previous_limit
        is_exact_limit = current_usage == current_limit
        if not (was_below and is_exact_limit):
            return
        await InAppNotificationService(self.session).create_usage_exhausted_notifications(
            tenant_id=tenant_id,
            metric_code=str(metric_code),
            period_key=period_key or current_period_key(),
            previous_usage=previous_usage,
            current_usage=current_usage,
            configured_limit=current_limit,
        )

    async def notify_for_limit_changes(
        self,
        tenant_id: UUID,
        previous_limits: dict[str, int],
        current_limits: dict[str, int],
        usage_by_metric: dict[str, int] | None = None,
    ) -> None:
        period_key = current_period_key()
        for metric_code, limit_field in self.FIELD_MAP.items():
            if usage_by_metric is None:
                metric = await self.consumption.get_metric(tenant_id, metric_code, period_key)
                current_usage = int(metric.consumed or 0) if metric else 0
            else:
                current_usage = int(usage_by_metric.get(str(metric_code), 0) or 0)
            await self.notify_if_threshold_crossed(
                tenant_id=tenant_id,
                metric_code=metric_code,
                previous_usage=current_usage,
                current_usage=current_usage,
                period_key=period_key,
                previous_limit=int(previous_limits.get(limit_field, 0)),
                current_limit=int(current_limits.get(limit_field, 0)),
            )
            await self.notify_if_exhausted(
                tenant_id=tenant_id,
                metric_code=metric_code,
                previous_usage=current_usage,
                current_usage=current_usage,
                period_key=period_key,
                previous_limit=int(previous_limits.get(limit_field, 0)),
                current_limit=int(current_limits.get(limit_field, 0)),
            )

    async def decrement(self, tenant_id: UUID, metric_code: str, amount: int = 1) -> None:
        # Runs the decrement service flow and persists the resulting state before returning it to the route or
        # worker.
        period_key = current_period_key()
        metric = await self.consumption.get_metric(tenant_id, metric_code, period_key)
        if not metric:
            return
        metric.consumed = max(0, int(metric.consumed or 0) - max(0, int(amount or 0)))
        await self.session.flush()

    async def summary(self, tenant_id: UUID) -> dict[str, int]:
        # Runs the summary service flow by coordinating repositories, validators, and integrations, then returns
        # domain data.
        period_key = current_period_key()
        values: dict[str, int] = {}
        for metric_code in self.FIELD_MAP:
            metric = await self.consumption.get_metric(tenant_id, metric_code, period_key)
            values[metric_code] = metric.consumed if metric else 0
        return values

