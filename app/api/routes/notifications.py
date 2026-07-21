from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentPrincipal, get_current_principal
from app.db.session import get_db_session
from app.schemas.common import MessageResponse
from app.schemas.notification import InAppNotificationResponse, InAppNotificationUnreadCountResponse
from app.services.notification import InAppNotificationService


router = APIRouter()


@router.get("", response_model=list[InAppNotificationResponse])
async def list_notifications(
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> list[InAppNotificationResponse]:
    notifications = await InAppNotificationService(session).list_for_user(principal.user_id)
    return [
        InAppNotificationResponse(
            id=notification.id,
            title=notification.title,
            message=notification.message,
            created_at=notification.created_at,
            unread=not notification.is_read,
        )
        for notification in notifications
    ]


@router.get("/unread-count", response_model=InAppNotificationUnreadCountResponse)
async def unread_notification_count(
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> InAppNotificationUnreadCountResponse:
    unread_count = await InAppNotificationService(session).unread_count_for_user(principal.user_id)
    return InAppNotificationUnreadCountResponse(unread_count=unread_count)


@router.patch("/read", response_model=MessageResponse)
async def mark_notifications_read(
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    await InAppNotificationService(session).mark_all_read_for_user(principal.user_id)
    return MessageResponse(message="Notifications marked as read")


@router.delete("", response_model=MessageResponse)
async def clear_notifications(
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    await InAppNotificationService(session).clear_for_user(principal.user_id)
    return MessageResponse(message="Notifications cleared")


@router.delete("/{notification_id}", response_model=MessageResponse)
async def delete_notification(
    notification_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    await InAppNotificationService(session).delete_for_user(principal.user_id, notification_id)
    return MessageResponse(message="Notification removed")
