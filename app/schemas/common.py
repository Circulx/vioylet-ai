# Pydantic schemas define the API contracts used by routes, services, and frontend callers.
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.core.studio import resolve_studio_panel_defaults


class APIModel(BaseModel):
    # Shared schema for apimodel; it keeps route payloads, service data, and serialized responses aligned.
    model_config = ConfigDict(from_attributes=True)


class MessageResponse(APIModel):
    # Response contract for message; routes serialize service or ORM results into this frontend-facing shape.
    message: str


class PaginatedResponse(APIModel):
    # Response contract for paginated; routes serialize service or ORM results into this frontend-facing shape.
    items: list[Any]
    total: int


class AuditMetadata(APIModel):
    # Shared schema for audit metadata; it keeps route payloads, service data, and serialized responses aligned.
    created_at: datetime
    updated_at: datetime


class StudioPanelSelection(APIModel):
    # Shared schema for studio panel selection; it keeps route payloads, service data, and serialized responses
    # aligned.
    format: str
    platform_preset: str
    file_type: str
    size: dict[str, int] | None = None
    pinned_template_id: UUID | None = None

    @model_validator(mode="after")
    def apply_defaults(self) -> "StudioPanelSelection":
        # Checks or reshapes defaults while Pydantic prepares the model for validation or serialization.
        resolved = resolve_studio_panel_defaults(self.model_dump())
        self.format = resolved["format"]
        self.platform_preset = resolved["platform_preset"]
        self.file_type = resolved["file_type"]
        self.size = resolved["size"]
        return self


class AssetReference(APIModel):
    # Shared schema for asset reference; it keeps route payloads, service data, and serialized responses
    # aligned.
    asset_id: UUID
    mime_type: str
    storage_path: str
    asset_url: str | None = None
    width: int | None = None
    height: int | None = None
    asset_role: str
