from __future__ import annotations

from collections import defaultdict
from datetime import timezone
from uuid import UUID

from sqlalchemy import func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brand import BrandSpace
from app.models.collaboration import JobRecord, ReviewLink
from app.models.content import ContentSession, ContentVersion
from app.models.knowledge import KnowledgeAsset, Template
from app.models.tenant import Tenant, User
from app.services.usage import UsageLimitService


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.usage = UsageLimitService(session)

    @staticmethod
    def summarize_token_usage(records: list[tuple[object, dict | None]]) -> dict:
        totals = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }
        monthly: dict[str, dict[str, int]] = defaultdict(
            lambda: {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        )
        for created_at, metadata in records:
            if not metadata or not isinstance(metadata, dict):
                continue
            usage = metadata.get("token_usage")
            if not isinstance(usage, dict):
                continue
            input_tokens = int(usage.get("input_tokens") or 0)
            output_tokens = int(usage.get("output_tokens") or 0)
            total_tokens = int(usage.get("total_tokens") or (input_tokens + output_tokens))
            totals["input_tokens"] += input_tokens
            totals["output_tokens"] += output_tokens
            totals["total_tokens"] += total_tokens
            if created_at is None:
                continue
            timestamp = created_at.astimezone(timezone.utc) if hasattr(created_at, "astimezone") else None
            if not timestamp:
                continue
            month_key = timestamp.strftime("%Y-%m")
            monthly[month_key]["input_tokens"] += input_tokens
            monthly[month_key]["output_tokens"] += output_tokens
            monthly[month_key]["total_tokens"] += total_tokens

        monthly_usage = [
            {"month": month, **values}
            for month, values in sorted(monthly.items())
        ][-12:]
        return {
            **totals,
            "monthly_token_usage": monthly_usage,
        }

    async def _token_usage_metrics(
        self,
        *,
        tenant_id: UUID | None = None,
        brand_space_id: UUID | None = None,
    ) -> dict:
        filters = []
        if tenant_id is not None:
            filters.append(ContentVersion.tenant_id == tenant_id)
        if brand_space_id is not None:
            filters.append(ContentVersion.brand_space_id == brand_space_id)

        input_tokens = func.coalesce(ContentVersion.token_input_tokens, 0)
        output_tokens = func.coalesce(ContentVersion.token_output_tokens, 0)
        total_tokens = func.coalesce(ContentVersion.token_total_tokens, input_tokens + output_tokens)

        totals_query = select(
            func.coalesce(func.sum(input_tokens), 0),
            func.coalesce(func.sum(output_tokens), 0),
            func.coalesce(func.sum(total_tokens), 0),
        )
        if filters:
            totals_query = totals_query.where(*filters)
        input_total, output_total, total = (await self.session.execute(totals_query)).one()

        month_expr = func.date_trunc(literal_column("'month'"), ContentVersion.created_at)
        monthly_query = (
            select(
                month_expr,
                func.coalesce(func.sum(input_tokens), 0),
                func.coalesce(func.sum(output_tokens), 0),
                func.coalesce(func.sum(total_tokens), 0),
            )
            .where(ContentVersion.created_at.is_not(None), *filters)
            .group_by(month_expr)
            .order_by(month_expr)
        )
        monthly_records = (await self.session.execute(monthly_query)).all()
        monthly_usage = [
            {
                "month": created_at.strftime("%Y-%m") if hasattr(created_at, "strftime") else str(created_at)[:7],
                "input_tokens": int(month_input or 0),
                "output_tokens": int(month_output or 0),
                "total_tokens": int(month_total or 0),
            }
            for created_at, month_input, month_output, month_total in monthly_records
        ][-12:]

        return {
            "input_tokens": int(input_total or 0),
            "output_tokens": int(output_total or 0),
            "total_tokens": int(total or 0),
            "monthly_token_usage": monthly_usage,
        }

    async def tenant_summary(self, tenant_id: UUID) -> dict:
        brand_spaces = await self.session.scalar(select(func.count(BrandSpace.id)).where(BrandSpace.tenant_id == tenant_id))
        users = await self.session.scalar(select(func.count(User.id)).where(User.tenant_id == tenant_id))
        content_generations = await self.session.scalar(select(func.count(ContentVersion.id)).where(ContentVersion.tenant_id == tenant_id))
        knowledge_assets = await self.session.scalar(select(func.count(KnowledgeAsset.id)).where(KnowledgeAsset.tenant_id == tenant_id))
        templates = await self.session.scalar(select(func.count(Template.id)).where(Template.tenant_id == tenant_id))
        review_links = await self.session.scalar(select(func.count(ReviewLink.id)).where(ReviewLink.tenant_id == tenant_id))
        chat_sessions = await self.session.scalar(select(func.count(ContentSession.id)).where(ContentSession.tenant_id == tenant_id))
        pending_jobs = await self.session.scalar(
            select(func.count(JobRecord.id)).where(
                JobRecord.tenant_id == tenant_id,
                JobRecord.status.in_(["queued", "processing"]),
            )
        )
        usage = await self.usage.summary(tenant_id)
        token_usage = await self._token_usage_metrics(tenant_id=tenant_id)
        return {
            "number_of_brand_spaces": brand_spaces or 0,
            "total_users": users or 0,
            "content_generations": content_generations or 0,
            "knowledge_assets": knowledge_assets or 0,
            "templates": templates or 0,
            "review_links": review_links or 0,
            "chat_sessions": chat_sessions or 0,
            "pending_jobs": pending_jobs or 0,
            "usage": usage,
            "token_usage": token_usage,
        }

    async def brand_summary(self, tenant_id: UUID, brand_space_id: UUID) -> dict:
        content_generations = await self.session.scalar(
            select(func.count(ContentVersion.id)).where(
                ContentVersion.tenant_id == tenant_id,
                ContentVersion.brand_space_id == brand_space_id,
            )
        )
        knowledge_assets = await self.session.scalar(
            select(func.count(KnowledgeAsset.id)).where(
                KnowledgeAsset.tenant_id == tenant_id,
                KnowledgeAsset.brand_space_id == brand_space_id,
            )
        )
        templates = await self.session.scalar(
            select(func.count(Template.id)).where(
                Template.tenant_id == tenant_id,
                Template.brand_space_id == brand_space_id,
            )
        )
        review_links = await self.session.scalar(
            select(func.count(ReviewLink.id)).where(
                ReviewLink.tenant_id == tenant_id,
                ReviewLink.brand_space_id == brand_space_id,
            )
        )
        chat_sessions = await self.session.scalar(
            select(func.count(ContentSession.id)).where(
                ContentSession.tenant_id == tenant_id,
                ContentSession.brand_space_id == brand_space_id,
            )
        )
        token_usage = await self._token_usage_metrics(tenant_id=tenant_id, brand_space_id=brand_space_id)
        return {
            "content_generations": content_generations or 0,
            "knowledge_assets": knowledge_assets or 0,
            "templates": templates or 0,
            "review_links": review_links or 0,
            "chat_sessions": chat_sessions or 0,
            "token_usage": token_usage,
        }

    async def platform_summary(self) -> dict:
        tenants = await self.session.scalar(select(func.count(Tenant.id)))
        active_tenants = await self.session.scalar(
            select(func.count(Tenant.id)).where(Tenant.is_active.is_(True))
        )
        brand_spaces = await self.session.scalar(select(func.count(BrandSpace.id)))
        active_brand_spaces = await self.session.scalar(
            select(func.count(BrandSpace.id)).where(BrandSpace.lifecycle_state == "active")
        )
        users = await self.session.scalar(select(func.count(User.id)))
        content_generations = await self.session.scalar(select(func.count(ContentVersion.id)))
        knowledge_assets = await self.session.scalar(select(func.count(KnowledgeAsset.id)))
        templates = await self.session.scalar(select(func.count(Template.id)))
        review_links = await self.session.scalar(select(func.count(ReviewLink.id)))
        chat_sessions = await self.session.scalar(select(func.count(ContentSession.id)))
        pending_jobs = await self.session.scalar(
            select(func.count(JobRecord.id)).where(JobRecord.status.in_(["queued", "processing"]))
        )
        token_usage = await self._token_usage_metrics()
        return {
            "tenants": tenants or 0,
            "active_tenants": active_tenants or 0,
            "brand_spaces": brand_spaces or 0,
            "active_brand_spaces": active_brand_spaces or 0,
            "users": users or 0,
            "content_generations": content_generations or 0,
            "knowledge_assets": knowledge_assets or 0,
            "templates": templates or 0,
            "review_links": review_links or 0,
            "chat_sessions": chat_sessions or 0,
            "pending_jobs": pending_jobs or 0,
            "token_usage": token_usage,
        }
