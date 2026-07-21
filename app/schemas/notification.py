# Pydantic schemas define the notification API contracts used by routes, services, and frontend callers.
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.schemas.common import APIModel


class InAppNotificationResponse(APIModel):
    id: UUID
    title: str
    message: str
    created_at: datetime
    unread: bool
