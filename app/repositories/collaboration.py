# Repository classes isolate SQLAlchemy queries so service code works with intent-level operations.
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collaboration import (
    AnalyticsSnapshot,
    InAppNotification,
    JobRecord,
    ReviewComment,
    ReviewLink,
    ReviewLinkParticipant,
    SocialConnection,
    UsageConsumption,
    UsageLimit,
)
from app.repositories.base import Repository


class ReviewLinkRepository(Repository[ReviewLink]):
    # Data-access helper for review link; services call this class instead of repeating SQLAlchemy filters
    # inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds ReviewLinkRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, ReviewLink)

    async def get_by_token(self, token: str) -> ReviewLink | None:
        # Fetches the requested by token record or None, leaving not-found handling to the calling service.
        result = await self.session.execute(select(ReviewLink).where(ReviewLink.token == token))
        return result.scalar_one_or_none()

    async def get_latest_for_content(
        self,
        tenant_id: UUID,
        brand_space_id: UUID,
        content_version_id: UUID,
    ) -> ReviewLink | None:
        # Reuses the review thread for the same generated content so comments remain attached across opens.
        # If older duplicate links already exist, prefer the one that has comments instead of an empty token.
        result = await self.session.execute(
            select(ReviewLink)
            .outerjoin(ReviewComment, ReviewComment.review_link_id == ReviewLink.id)
            .where(
                ReviewLink.tenant_id == tenant_id,
                ReviewLink.brand_space_id == brand_space_id,
                ReviewLink.content_version_id == content_version_id,
            )
            .group_by(ReviewLink.id)
            .order_by(func.count(ReviewComment.id).desc(), ReviewLink.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


class ReviewCommentRepository(Repository[ReviewComment]):
    # Data-access helper for review comment; services call this class instead of repeating SQLAlchemy filters
    # inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds ReviewCommentRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, ReviewComment)

    async def list_for_link(self, review_link_id: UUID) -> list[ReviewComment]:
        # Returns matching for link records with repository scope applied; services assemble responses from
        # these rows.
        result = await self.session.execute(
            select(ReviewComment)
            .where(ReviewComment.review_link_id == review_link_id)
            .order_by(ReviewComment.created_at.asc())
        )
        return list(result.scalars().all())


class ReviewLinkParticipantRepository(Repository[ReviewLinkParticipant]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ReviewLinkParticipant)

    async def list_for_link(self, review_link_id: UUID) -> list[ReviewLinkParticipant]:
        result = await self.session.execute(
            select(ReviewLinkParticipant)
            .where(ReviewLinkParticipant.review_link_id == review_link_id)
            .order_by(ReviewLinkParticipant.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_for_link_user(
        self,
        review_link_id: UUID,
        user_id: UUID,
    ) -> ReviewLinkParticipant | None:
        result = await self.session.execute(
            select(ReviewLinkParticipant).where(
                ReviewLinkParticipant.review_link_id == review_link_id,
                ReviewLinkParticipant.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()


class InAppNotificationRepository(Repository[InAppNotification]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InAppNotification)

    async def list_for_user(self, user_id: UUID, limit: int = 50) -> list[InAppNotification]:
        result = await self.session.execute(
            select(InAppNotification)
            .where(InAppNotification.recipient_user_id == user_id)
            .order_by(InAppNotification.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_unread_for_user(self, user_id: UUID) -> int:
        result = await self.session.scalar(
            select(func.count(InAppNotification.id)).where(
                InAppNotification.recipient_user_id == user_id,
                InAppNotification.is_read.is_(False),
            )
        )
        return int(result or 0)

    async def mark_all_read_for_user(self, user_id: UUID) -> int:
        result = await self.session.execute(
            update(InAppNotification)
            .where(
                InAppNotification.recipient_user_id == user_id,
                InAppNotification.is_read.is_(False),
            )
            .values(is_read=True)
        )
        return int(result.rowcount or 0)

    async def delete_for_user(self, user_id: UUID) -> None:
        notifications = await self.list_for_user(user_id, limit=500)
        for notification in notifications:
            await self.delete(notification)

    async def delete_one_for_user(self, user_id: UUID, notification_id: UUID) -> bool:
        notification = await self.get(notification_id)
        if not notification or notification.recipient_user_id != user_id:
            return False
        await self.delete(notification)
        return True


class SocialConnectionRepository(Repository[SocialConnection]):
    # Data-access helper for social connection; services call this class instead of repeating SQLAlchemy filters
    # inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds SocialConnectionRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, SocialConnection)

    async def get_by_platform(self, brand_space_id: UUID, platform: str) -> SocialConnection | None:
        # Fetches the requested by platform record or None, leaving not-found handling to the calling service.
        result = await self.session.execute(
            select(SocialConnection).where(
                SocialConnection.brand_space_id == brand_space_id,
                SocialConnection.platform == platform,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_brand(self, tenant_id: UUID, brand_space_id: UUID) -> list[SocialConnection]:
        # Returns matching by brand records with repository scope applied; services assemble responses from
        # these rows.
        result = await self.session.execute(
            select(SocialConnection).where(
                SocialConnection.tenant_id == tenant_id,
                SocialConnection.brand_space_id == brand_space_id,
            )
        )
        return list(result.scalars().all())


class AnalyticsRepository(Repository[AnalyticsSnapshot]):
    # Data-access helper for analytics; services call this class instead of repeating SQLAlchemy filters inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds AnalyticsRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, AnalyticsSnapshot)

    async def list_by_scope(self, tenant_id: UUID, brand_space_id: UUID | None = None) -> list[AnalyticsSnapshot]:
        # Returns matching by scope records with repository scope applied; services assemble responses from
        # these rows.
        stmt = select(AnalyticsSnapshot).where(AnalyticsSnapshot.tenant_id == tenant_id)
        if brand_space_id:
            stmt = stmt.where(AnalyticsSnapshot.brand_space_id == brand_space_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class UsageLimitRepository(Repository[UsageLimit]):
    # Data-access helper for usage limit; services call this class instead of repeating SQLAlchemy filters
    # inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds UsageLimitRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, UsageLimit)

    async def get_by_tenant(self, tenant_id: UUID) -> UsageLimit | None:
        # Fetches the requested by tenant record or None, leaving not-found handling to the calling service.
        result = await self.session.execute(select(UsageLimit).where(UsageLimit.tenant_id == tenant_id))
        return result.scalar_one_or_none()

    async def get_by_tenant_for_update(self, tenant_id: UUID) -> UsageLimit | None:
        """Lock the tenant's limits row to serialize usage increments, including the first one."""
        result = await self.session.execute(
            select(UsageLimit).where(UsageLimit.tenant_id == tenant_id).with_for_update()
        )
        return result.scalar_one_or_none()


class UsageConsumptionRepository(Repository[UsageConsumption]):
    # Data-access helper for usage consumption; services call this class instead of repeating SQLAlchemy filters
    # inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds UsageConsumptionRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, UsageConsumption)

    async def get_metric(self, tenant_id: UUID, metric_code: str, period_key: str) -> UsageConsumption | None:
        # Fetches the requested metric record or None, leaving not-found handling to the calling service.
        result = await self.session.execute(
            select(UsageConsumption).where(
                UsageConsumption.tenant_id == tenant_id,
                UsageConsumption.metric_code == metric_code,
                UsageConsumption.period_key == period_key,
            )
        )
        return result.scalar_one_or_none()

    async def get_metric_for_update(
        self,
        tenant_id: UUID,
        metric_code: str,
        period_key: str,
    ) -> UsageConsumption | None:
        """Return and lock a usage row so threshold crossings are evaluated once per transaction."""
        result = await self.session.execute(
            select(UsageConsumption)
            .where(
                UsageConsumption.tenant_id == tenant_id,
                UsageConsumption.metric_code == metric_code,
                UsageConsumption.period_key == period_key,
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()


class JobRepository(Repository[JobRecord]):
    # Data-access helper for job; services call this class instead of repeating SQLAlchemy filters inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds JobRepository to the current async session, giving every query method the same DB transaction
        # context.
        super().__init__(session, JobRecord)

    async def list_by_tenant(self, tenant_id: UUID) -> list[JobRecord]:
        # Returns matching by tenant records with repository scope applied; services assemble responses from
        # these rows.
        result = await self.session.execute(select(JobRecord).where(JobRecord.tenant_id == tenant_id))
        return list(result.scalars().all())

    async def get_scoped(self, job_id: UUID, tenant_id: UUID) -> JobRecord | None:
        # Fetches the requested scoped record or None, leaving not-found handling to the calling service.
        result = await self.session.execute(
            select(JobRecord).where(
                JobRecord.id == job_id,
                JobRecord.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_pending(self, limit: int) -> list[JobRecord]:
        # Returns matching pending records with repository scope applied; services assemble responses from these
        # rows.
        result = await self.session.execute(
            select(JobRecord)
            .where(JobRecord.status.in_(["queued", "processing"]))
            .order_by(JobRecord.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def claim_available(
        self,
        *,
        worker_id: str,
        limit: int,
        now: datetime,
        lease_expires_at: datetime,
    ) -> list[JobRecord]:
        # Claims available through SQLAlchemy and returns ORM objects or counts for the service layer to
        # consume.
        result = await self.session.execute(
            select(JobRecord)
            .where(
                or_(
                    JobRecord.status == "queued",
                    and_(
                        JobRecord.status == "processing",
                        or_(
                            JobRecord.lease_expires_at.is_(None),
                            JobRecord.lease_expires_at < now,
                        ),
                    ),
                )
            )
            .order_by(JobRecord.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        jobs = list(result.scalars().all())
        # Builds the grouped response or persistence payload one record at a time because later steps expect
        # this exact shape.
        for job in jobs:
            job.status = "processing"
            job.lease_owner = worker_id
            job.lease_expires_at = lease_expires_at
            job.heartbeat_at = now
            job.started_at = job.started_at or now
            job.finished_at = None
        await self.session.flush()
        return jobs
