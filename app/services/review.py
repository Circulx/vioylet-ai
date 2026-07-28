# Service classes hold business workflows between the HTTP layer, repositories, and integrations.
from __future__ import annotations

import asyncio
import logging
import secrets
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ReviewStatus, RoleCode
from app.core.exceptions import LifecycleError
from app.core.exceptions import NotFoundError
from app.models.brand import BrandSpaceMember
from app.repositories.content import ContentRepository
from app.models.collaboration import ReviewComment, ReviewLink, ReviewLinkParticipant
from app.models.tenant import Role, User, UserRole
from app.repositories.collaboration import ReviewCommentRepository, ReviewLinkParticipantRepository, ReviewLinkRepository
from app.services.email import EmailService
from app.services.notification import InAppNotificationService, email_notifications_enabled


logger = logging.getLogger(__name__)


class ReviewService:
    # Business layer for review; routes and workers pass validated inputs here and receive domain results back.
    def __init__(self, session: AsyncSession) -> None:
        # Wires the repositories and helper services this workflow reuses across its public methods.
        self.session = session
        self.links = ReviewLinkRepository(session)
        self.comments = ReviewCommentRepository(session)
        self.participants = ReviewLinkParticipantRepository(session)
        self.contents = ContentRepository(session)
        self.email = EmailService()

    async def create_link(self, tenant_id: UUID, brand_space_id: UUID, content_version_id: UUID, created_by: UUID, title: str | None, allow_external_comments: bool) -> ReviewLink:
        # Runs the link service flow and persists the resulting state before returning it to the route or
        # worker.
        content = await self.contents.get_scoped(content_version_id, tenant_id, brand_space_id)
        if not content:
            raise NotFoundError("Content version not found")
        existing_link = await self.links.get_latest_for_content(tenant_id, brand_space_id, content_version_id)
        if existing_link:
            existing_link.created_by = created_by
            existing_link.title = title or existing_link.title
            existing_link.allow_external_comments = allow_external_comments
            await self.session.commit()
            return existing_link
        review_link = ReviewLink(
            tenant_id=tenant_id,
            brand_space_id=brand_space_id,
            content_version_id=content_version_id,
            created_by=created_by,
            token=secrets.token_urlsafe(24),
            title=title,
            allow_external_comments=allow_external_comments,
            status="pending",
        )
        await self.links.add(review_link)
        await self.session.commit()
        return review_link

    async def get_by_token(self, token: str) -> tuple[ReviewLink, list[ReviewComment]]:
        # Runs the by token service flow by coordinating repositories, validators, and integrations, then
        # returns domain data.
        link = await self.links.get_by_token(token)
        if not link:
            raise NotFoundError("Review link not found")
        comments = await self.comments.list_for_link(link.id)
        return link, comments

    async def can_access_link(
        self,
        link: ReviewLink,
        user_id: UUID | None,
        role_codes: set[str] | None = None,
        brand_space_ids: set[UUID] | None = None,
    ) -> bool:
        if not user_id:
            return False
        user = await self._get_active_user(user_id)
        if not user:
            return False
        normalized_roles = role_codes or await self._get_user_role_codes(user_id)
        if user.id == link.created_by:
            return True
        participant = await self.participants.get_for_link_user(link.id, user.id)
        if participant is not None:
            return True
        if RoleCode.SUPER_ADMIN in normalized_roles:
            return False
        if user.tenant_id == link.tenant_id and RoleCode.TENANT_ADMIN in normalized_roles:
            return True
        if brand_space_ids and link.brand_space_id in brand_space_ids:
            return True
        return False

    async def list_share_access(
        self,
        link: ReviewLink,
    ) -> tuple[User | None, list[tuple[ReviewLinkParticipant, User]], list[User], dict[UUID, set[str]]]:
        owner = await self._get_active_user(link.created_by)
        participants = await self.participants.list_for_link(link.id)
        participant_pairs: list[tuple[ReviewLinkParticipant, User]] = []
        for participant in participants:
            user = await self._get_active_user(participant.user_id)
            if user:
                participant_pairs.append((participant, user))
        mentionable_users = await self._list_active_platform_users()
        user_ids = {user.id for user in mentionable_users}
        if owner:
            user_ids.add(owner.id)
        user_ids.update(user.id for _, user in participant_pairs)
        role_codes_by_user = await self._role_codes_by_user_ids(user_ids)
        return owner, participant_pairs, mentionable_users, role_codes_by_user

    async def grant_share_access(
        self,
        review_link_id: UUID,
        user_ids: list[UUID],
        mentioned_by: UUID,
        user_emails: list[str] | None = None,
    ) -> list[User]:
        link = await self.links.get(review_link_id)
        if not link:
            raise NotFoundError("Review link not found")
        normalized_emails = [
            email.strip().lower()
            for email in dict.fromkeys(user_emails or [])
            if email and email.strip()
        ]
        users_from_email = await self._list_active_platform_users_by_emails(normalized_emails)
        found_emails = {(user.email or "").strip().lower() for user in users_from_email}
        missing_emails = [email for email in normalized_emails if email not in found_emails]
        if missing_emails:
            raise LifecycleError(f"Registered user not found for: {', '.join(missing_emails)}")
        users_by_id = {
            user.id: user
            for user in await self._list_active_platform_users_by_ids(
                [user_id for user_id in dict.fromkeys(user_ids) if user_id != link.created_by]
            )
        }
        users_by_email = {user.id: user for user in users_from_email if user.id != link.created_by}
        users = list({**users_by_id, **users_by_email}.values())
        if not users:
            return []
        new_users: list[User] = []
        for user in users:
            existing = await self.participants.get_for_link_user(link.id, user.id)
            if existing:
                continue
            await self.participants.add(
                ReviewLinkParticipant(
                    tenant_id=link.tenant_id,
                    brand_space_id=link.brand_space_id,
                    review_link_id=link.id,
                    user_id=user.id,
                    mentioned_by=mentioned_by,
                    access_role="viewer",
                )
            )
            new_users.append(user)
        await self.session.commit()
        if new_users:
            try:
                await self._send_mention_notifications(link, new_users, mentioned_by)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Review mention notification failed for review_link_id=%s: %s",
                    link.id,
                    exc,
                )
        return new_users

    async def revoke_share_access(
        self,
        review_link_id: UUID,
        user_ids: list[UUID],
        removed_by: UUID,
    ) -> list[User]:
        link = await self.links.get(review_link_id)
        if not link:
            raise NotFoundError("Review link not found")
        unique_user_ids = [user_id for user_id in dict.fromkeys(user_ids) if user_id != link.created_by]
        if not unique_user_ids:
            return []
        participants = await self.participants.list_for_link_users(link.id, unique_user_ids)
        removed_users: list[User] = []
        for participant in participants:
            user = await self._get_active_user(participant.user_id)
            if user and user.tenant_id == link.tenant_id:
                removed_users.append(user)
            await self.participants.delete(participant)
        await self.session.commit()
        if removed_users:
            try:
                await self._send_access_removed_notifications(link, removed_users, removed_by)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Review access removed notification failed for review_link_id=%s: %s",
                    link.id,
                    exc,
                )
        return removed_users

    async def add_comment(
        self,
        review_link_id: UUID,
        tenant_id: UUID,
        brand_space_id: UUID,
        body: str,
        author_user_id: UUID | None = None,
        external_author_name: str | None = None,
        parent_comment_id: UUID | None = None,
        send_notifications: bool = True,
    ) -> ReviewComment:
        # Runs the comment service flow and persists the resulting state before returning it to the route or
        # worker.
        link = await self.links.get(review_link_id)
        if not link:
            raise NotFoundError("Review link not found")
        if author_user_id is None and not link.allow_external_comments:
            raise LifecycleError("External comments are disabled for this review link")
        if parent_comment_id:
            parent = await self.comments.get(parent_comment_id)
            if not parent or parent.review_link_id != review_link_id:
                raise LifecycleError("Reply target comment is invalid")
        comment = ReviewComment(
            tenant_id=tenant_id,
            brand_space_id=brand_space_id,
            review_link_id=review_link_id,
            parent_comment_id=parent_comment_id,
            author_user_id=author_user_id,
            external_author_name=external_author_name,
            body=body,
        )
        await self.comments.add(comment)
        await self.session.commit()
        if send_notifications:
            await self.send_comment_notifications_for_comment(link.id, comment.id)
        return comment

    async def send_comment_notifications_for_comment(
        self,
        review_link_id: UUID,
        comment_id: UUID,
    ) -> None:
        link = await self.links.get(review_link_id)
        comment = await self.comments.get(comment_id)
        if not link or not comment:
            return
        try:
            await self._send_comment_notifications(link, comment)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Review comment email notification failed for review_link_id=%s: %s",
                review_link_id,
                exc,
            )

    async def _send_comment_notifications(self, link: ReviewLink, comment: ReviewComment) -> None:
        recipients = await self._comment_notification_recipients(link, exclude_user_id=comment.author_user_id)
        if not recipients:
            return
        commenter_name = await self._commenter_name(comment)
        content = await self.contents.get_scoped(
            link.content_version_id,
            link.tenant_id,
            link.brand_space_id,
        )
        post_title = link.title or (content.title if content else None)
        review_url = self.email.build_review_link(link.token)
        for recipient in recipients:
            if not email_notifications_enabled(recipient):
                continue
            await asyncio.to_thread(
                self.email.send_review_comment_notification_email,
                recipient.email,
                commenter_name,
                comment.body,
                review_url,
                post_title,
            )

    async def _create_comment_in_app_notifications(self, link: ReviewLink, comment: ReviewComment) -> None:
        recipients = await self._comment_notification_recipients(link, exclude_user_id=comment.author_user_id)
        if not recipients:
            return
        commenter_name = await self._commenter_name(comment)
        comment_body = (comment.body or "").strip()
        message = (
            f'{commenter_name} commented on your content:\n"{comment_body}"'
            if comment_body
            else f"{commenter_name} commented on your content."
        )
        notification_service = InAppNotificationService(self.session)
        for recipient in recipients:
            await notification_service.create(
                recipient_user_id=recipient.id,
                tenant_id=recipient.tenant_id,
                title="New Comment",
                message=message,
                metadata={
                    "event": "review_comment_added",
                    "review_link_id": str(link.id),
                    "comment_id": str(comment.id),
                },
            )
        await self.session.commit()

    async def _create_review_approved_in_app_notifications(
        self,
        link: ReviewLink,
        reviewer_user_id: UUID | None = None,
    ) -> None:
        recipients = await self._comment_notification_recipients(link, exclude_user_id=reviewer_user_id)
        if not recipients:
            return
        reviewer_name = await self._reviewer_name(reviewer_user_id)
        notification_service = InAppNotificationService(self.session)
        for recipient in recipients:
            await notification_service.create(
                recipient_user_id=recipient.id,
                tenant_id=recipient.tenant_id,
                title="Content Approved",
                message=f"Your content has been approved by {reviewer_name}.",
                metadata={
                    "event": "review_approved",
                    "review_link_id": str(link.id),
                },
            )

    async def _send_mention_notifications(
        self,
        link: ReviewLink,
        recipients: list[User],
        mentioned_by: UUID,
    ) -> None:
        sharer_name = await self._reviewer_name(mentioned_by)
        content = await self.contents.get_scoped(
            link.content_version_id,
            link.tenant_id,
            link.brand_space_id,
        )
        post_title = link.title or (content.title if content else None)
        review_url = self.email.build_review_link(link.token)
        for recipient in recipients:
            if not email_notifications_enabled(recipient):
                continue
            await asyncio.to_thread(
                self.email.send_review_mention_notification_email,
                recipient.email,
                recipient.full_name,
                sharer_name,
                review_url,
                post_title,
            )
        await self.session.commit()

    async def _send_access_removed_notifications(
        self,
        link: ReviewLink,
        recipients: list[User],
        removed_by: UUID,
    ) -> None:
        remover_name = await self._reviewer_name(removed_by)
        content = await self.contents.get_scoped(
            link.content_version_id,
            link.tenant_id,
            link.brand_space_id,
        )
        post_title = link.title or (content.title if content else None)
        for recipient in recipients:
            if not email_notifications_enabled(recipient):
                continue
            await asyncio.to_thread(
                self.email.send_review_access_removed_notification_email,
                recipient.email,
                recipient.full_name,
                remover_name,
                post_title,
            )
        await self.session.commit()

    async def _send_review_approved_email_notifications(
        self,
        link: ReviewLink,
        reviewer_user_id: UUID | None = None,
    ) -> None:
        recipients = await self._comment_notification_recipients(link, exclude_user_id=reviewer_user_id)
        if not recipients:
            return
        reviewer_name = await self._reviewer_name(reviewer_user_id)
        content = await self.contents.get_scoped(
            link.content_version_id,
            link.tenant_id,
            link.brand_space_id,
        )
        post_title = link.title or (content.title if content else None)
        review_url = self.email.build_review_link(link.token)
        for recipient in recipients:
            if not email_notifications_enabled(recipient):
                continue
            await asyncio.to_thread(
                self.email.send_review_approved_notification_email,
                recipient.email,
                reviewer_name,
                review_url,
                post_title,
            )

    async def _reviewer_name(self, reviewer_user_id: UUID | None) -> str:
        if reviewer_user_id:
            reviewer = await self._get_active_user(reviewer_user_id)
            if reviewer:
                return reviewer.full_name or reviewer.email
        return "Reviewer"

    async def _comment_notification_recipients(
        self,
        link: ReviewLink,
        exclude_user_id: UUID | None = None,
    ) -> list[User]:
        users: list[User] = []
        sharer = await self._get_active_user(link.created_by)
        if sharer:
            users.append(sharer)
        users.extend(await self._list_active_users_by_role(link.tenant_id, RoleCode.TENANT_ADMIN))
        for participant in await self.participants.list_for_link(link.id):
            participant_user = await self._get_active_user(participant.user_id)
            if participant_user:
                users.append(participant_user)
        if exclude_user_id:
            users = [user for user in users if user.id != exclude_user_id]
        return self._dedupe_email_recipients(users)

    async def _commenter_name(self, comment: ReviewComment) -> str:
        if comment.author_user_id:
            author = await self._get_active_user(comment.author_user_id)
            if author:
                return author.full_name or author.email
        return (comment.external_author_name or "").strip() or "Reviewer"

    async def _get_active_user(self, user_id: UUID) -> User | None:
        user = await self.session.get(User, user_id)
        if not user or not user.is_active:
            return None
        return user

    async def _get_user_role_codes(self, user_id: UUID) -> set[str]:
        result = await self.session.execute(
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        return set(result.scalars().all())

    async def _get_notification_role_codes(self, user_id: UUID, brand_space_id: UUID) -> set[str]:
        role_codes = await self._get_user_role_codes(user_id)
        if role_codes:
            return role_codes
        return await self._infer_user_role_codes_from_brand_membership(user_id, brand_space_id)

    async def _infer_user_role_codes_from_brand_membership(
        self,
        user_id: UUID,
        brand_space_id: UUID,
    ) -> set[str]:
        result = await self.session.execute(
            select(BrandSpaceMember)
            .where(
                BrandSpaceMember.user_id == user_id,
                BrandSpaceMember.brand_space_id == brand_space_id,
            )
            .limit(1)
        )
        membership = result.scalar_one_or_none()
        if not membership:
            return set()
        if membership.can_manage:
            return {RoleCode.TENANT_USER}
        return {RoleCode.BRAND_USER}

    async def _list_active_users_by_role(self, tenant_id: UUID, role_code: str) -> list[User]:
        result = await self.session.execute(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                User.tenant_id == tenant_id,
                User.is_active.is_(True),
                Role.code == role_code,
            )
            .distinct()
        )
        return list(result.scalars().all())

    async def _list_active_platform_users(self) -> list[User]:
        result = await self.session.execute(
            select(User)
            .where(User.is_active.is_(True))
            .order_by(User.full_name.asc(), User.email.asc())
        )
        return list(result.scalars().all())

    async def _list_active_platform_users_by_ids(self, user_ids: list[UUID]) -> list[User]:
        if not user_ids:
            return []
        result = await self.session.execute(
            select(User)
            .where(
                User.is_active.is_(True),
                User.id.in_(user_ids),
            )
            .order_by(User.full_name.asc(), User.email.asc())
        )
        return list(result.scalars().all())

    async def _list_active_platform_users_by_emails(self, emails: list[str]) -> list[User]:
        normalized_emails = [
            email.strip().lower()
            for email in dict.fromkeys(emails)
            if email and email.strip()
        ]
        if not normalized_emails:
            return []
        result = await self.session.execute(
            select(User)
            .where(
                User.is_active.is_(True),
                func.lower(User.email).in_(normalized_emails),
            )
            .order_by(User.full_name.asc(), User.email.asc())
        )
        return list(result.scalars().all())

    async def _role_codes_by_user_ids(self, user_ids: set[UUID]) -> dict[UUID, set[str]]:
        if not user_ids:
            return {}
        result = await self.session.execute(
            select(UserRole.user_id, Role.code)
            .join(Role, Role.id == UserRole.role_id)
            .where(UserRole.user_id.in_(user_ids))
        )
        role_codes_by_user: dict[UUID, set[str]] = {}
        for user_id, role_code in result.all():
            role_codes_by_user.setdefault(user_id, set()).add(role_code)
        return role_codes_by_user

    async def _list_active_super_users_for_brand(
        self,
        tenant_id: UUID,
        brand_space_id: UUID,
    ) -> list[User]:
        managed_brand_result = await self.session.execute(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .join(BrandSpaceMember, BrandSpaceMember.user_id == User.id)
            .where(
                User.tenant_id == tenant_id,
                User.is_active.is_(True),
                Role.code == RoleCode.TENANT_USER,
                BrandSpaceMember.brand_space_id == brand_space_id,
                BrandSpaceMember.can_manage.is_(True),
            )
            .distinct()
        )
        managed_brand_super_users = list(managed_brand_result.scalars().all())
        if managed_brand_super_users:
            return managed_brand_super_users

        brand_result = await self.session.execute(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .join(BrandSpaceMember, BrandSpaceMember.user_id == User.id)
            .where(
                User.tenant_id == tenant_id,
                User.is_active.is_(True),
                Role.code == RoleCode.TENANT_USER,
                BrandSpaceMember.brand_space_id == brand_space_id,
            )
            .distinct()
        )
        brand_super_users = list(brand_result.scalars().all())
        if brand_super_users:
            return brand_super_users
        return await self._list_active_users_by_role(tenant_id, RoleCode.TENANT_USER)

    @staticmethod
    def _dedupe_email_recipients(users: list[User]) -> list[User]:
        recipients: list[User] = []
        seen_emails: set[str] = set()
        for user in users:
            email_key = (user.email or "").strip().lower()
            if not email_key or email_key in seen_emails:
                continue
            seen_emails.add(email_key)
            recipients.append(user)
        return recipients

    async def update_status(
        self,
        review_link_id: UUID,
        status: str,
        reviewer_user_id: UUID | None = None,
    ) -> ReviewLink:
        # Runs the status service flow and persists the resulting state before returning it to the route or
        # worker.
        link = await self.links.get(review_link_id)
        if not link:
            raise NotFoundError("Review link not found")
        if status not in {ReviewStatus.PENDING, ReviewStatus.APPROVED, ReviewStatus.NEEDS_CHANGES}:
            raise LifecycleError("Invalid review status")
        was_approved = link.status == ReviewStatus.APPROVED
        link.status = status
        if status == ReviewStatus.APPROVED and not was_approved:
            try:
                await self._send_review_approved_email_notifications(link, reviewer_user_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Review approval email notification failed for review_link_id=%s: %s",
                    link.id,
                    exc,
                )
        await self.session.commit()
        return link
