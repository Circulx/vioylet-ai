# Pydantic schemas define the API contracts used by routes, services, and frontend callers.
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.schemas.common import APIModel


class JobResponse(APIModel):
    # Response contract for job; routes serialize service or ORM results into this frontend-facing shape.
    id: UUID
    tenant_id: UUID
    brand_space_id: UUID | None = None
    job_type: str
    status: str
    payload: dict
    result_payload: dict
    error_message: str | None = None
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None
    heartbeat_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
