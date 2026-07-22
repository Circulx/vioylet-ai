from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brand import BrandSpace
from app.models.collaboration import BrandCapacityAlertState, UsageLimit
from app.models.content import ContentVersion, GeneratedAsset
from app.models.knowledge import KnowledgeAsset
from app.models.tenant import Tenant
from app.services.notification import InAppNotificationService
from app.utils.text import current_period_key


class BrandCapacityAllocationService:
    WARNING_THRESHOLD = 80.0

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def equal_average_usage_percent(
        usage_values: dict[str, int],
        allocated_limits: dict[str, float],
    ) -> float:
        percentages = [
            min(100.0, max(0.0, float(usage_values.get(metric_code, 0))) / limit * 100)
            for metric_code, limit in allocated_limits.items()
            if limit > 0
        ]
        return sum(percentages) / len(percentages) if percentages else 0.0

    @staticmethod
    def current_month_bounds() -> tuple[datetime, datetime]:
        now = datetime.now(timezone.utc)
        start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        end = (
            datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
            if now.month == 12
            else datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
        )
        return start, end

    async def evaluate(self, tenant_id: UUID, brand_space_id: UUID) -> float:
        usage_limit = await self.session.scalar(
            select(UsageLimit).where(UsageLimit.tenant_id == tenant_id).with_for_update()
        )
        tenant = await self.session.get(Tenant, tenant_id)
        brand = await self.session.scalar(
            select(BrandSpace).where(
                BrandSpace.id == brand_space_id,
                BrandSpace.tenant_id == tenant_id,
                BrandSpace.lifecycle_state != "deleted",
            )
        )
        if not usage_limit or not tenant or not brand:
            return 0.0

        raw_targets = (
            tenant.metadata_json.get("brand_usage_targets", {})
            if isinstance(tenant.metadata_json, dict)
            else {}
        )
        allocation_percent = max(0.0, min(100.0, float(raw_targets.get(str(brand_space_id), 0) or 0)))
        if allocation_percent <= 0:
            return 0.0

        ratio = allocation_percent / 100.0
        allocated_limits = {
            "content_generations": float(usage_limit.max_content_generations or 0) * ratio,
            "image_generations": float(usage_limit.max_image_generations or 0) * ratio,
            "ocr_pages": float(usage_limit.max_ocr_pages or 0) * ratio,
        }
        start, end = self.current_month_bounds()
        usage_values = {
            "content_generations": int(
                await self.session.scalar(
                    select(func.count(ContentVersion.id)).where(
                        ContentVersion.tenant_id == tenant_id,
                        ContentVersion.brand_space_id == brand_space_id,
                        ContentVersion.created_at >= start,
                        ContentVersion.created_at < end,
                    )
                )
                or 0
            ),
            "image_generations": int(
                await self.session.scalar(
                    select(func.count(GeneratedAsset.id)).where(
                        GeneratedAsset.tenant_id == tenant_id,
                        GeneratedAsset.brand_space_id == brand_space_id,
                        GeneratedAsset.created_at >= start,
                        GeneratedAsset.created_at < end,
                    )
                )
                or 0
            ),
            "ocr_pages": int(
                await self.session.scalar(
                    select(func.coalesce(func.sum(KnowledgeAsset.page_count), 0)).where(
                        KnowledgeAsset.tenant_id == tenant_id,
                        KnowledgeAsset.brand_space_id == brand_space_id,
                        KnowledgeAsset.created_at >= start,
                        KnowledgeAsset.created_at < end,
                    )
                )
                or 0
            ),
        }
        usage_percent = float(round(self.equal_average_usage_percent(usage_values, allocated_limits)))
        period_key = current_period_key()
        state = await self.session.scalar(
            select(BrandCapacityAlertState)
            .where(
                BrandCapacityAlertState.tenant_id == tenant_id,
                BrandCapacityAlertState.brand_space_id == brand_space_id,
                BrandCapacityAlertState.period_key == period_key,
            )
            .with_for_update()
        )
        if not state:
            state = BrandCapacityAlertState(
                tenant_id=tenant_id,
                brand_space_id=brand_space_id,
                period_key=period_key,
                last_usage_percent=0.0,
                warning_sent=False,
            )
            self.session.add(state)

        state.last_usage_percent = usage_percent
        if usage_percent >= self.WARNING_THRESHOLD and not state.warning_sent:
            await InAppNotificationService(self.session).create_brand_capacity_warning_notifications(
                tenant_id=tenant_id,
                brand_space_id=brand_space_id,
                brand_name=brand.name,
                allocation_percent=allocation_percent,
                usage_percent=usage_percent,
                period_key=period_key,
            )
            state.warning_sent = True
        await self.session.flush()
        return usage_percent
