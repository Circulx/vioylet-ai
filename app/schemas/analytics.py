# Pydantic schemas define the API contracts used by routes, services, and frontend callers.
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.schemas.common import APIModel


class AnalyticsResponse(APIModel):
    # Response contract for analytics; routes serialize service or ORM results into this frontend-facing shape.
    scope: str
    tenant_id: UUID | None = None
    brand_space_id: UUID | None = None
    metrics: dict[str, Any]
