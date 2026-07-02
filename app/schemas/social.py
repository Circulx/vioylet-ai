# Pydantic schemas define the API contracts used by routes, services, and frontend callers.
from __future__ import annotations

from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel


class SocialConnectRequest(APIModel):
    # Request contract for social connect; FastAPI validates incoming JSON against these fields before service
    # code runs.
    platform: str
    account_name: str | None = None
    account_identifier: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    scopes: list[str] = Field(default_factory=list)


class SocialPublishRequest(APIModel):
    # Request contract for social publish; FastAPI validates incoming JSON against these fields before service
    # code runs.
    content_version_id: UUID
    platform: str
    caption_override: str | None = None
    media_asset_ids: list[UUID] = Field(default_factory=list)
    publish_now: bool = Field(default=True)


class SocialConnectionResponse(APIModel):
    # Response contract for social connection; routes serialize service or ORM results into this frontend-facing
    # shape.
    id: UUID
    platform: str
    account_name: str | None = None
    account_identifier: str | None = None
    is_connected: bool
