# Pydantic schemas define the API contracts used by routes, services, and frontend callers.
from __future__ import annotations

from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel, AssetReference


class RenderLayoutRequest(APIModel):
    # Request contract for render layout; FastAPI validates incoming JSON against these fields before service
    # code runs.
    content_version_id: UUID
    blueprint_payload: dict | None = None
    studio_panel: dict
    template_id: UUID | None = None


class RenderPreviewRequest(APIModel):
    # Request contract for render preview; FastAPI validates incoming JSON against these fields before service
    # code runs.
    content_version_id: UUID
    blueprint_payload: dict | None = None
    studio_panel: dict
    template_id: UUID | None = None


class RenderExportRequest(APIModel):
    # Request contract for render export; FastAPI validates incoming JSON against these fields before service
    # code runs.
    content_version_id: UUID
    studio_panel: dict
    export_format: str
    blueprint_payload: dict | None = None
    template_id: UUID | None = None


class RenderResponse(APIModel):
    # Response contract for render; routes serialize service or ORM results into this frontend-facing shape.
    content_version_id: UUID
    preview_asset: AssetReference | None = None
    export_assets: list[AssetReference] = Field(default_factory=list)
    renderer_metadata: dict
