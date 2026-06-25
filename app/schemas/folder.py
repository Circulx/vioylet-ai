# Pydantic schemas define the API contracts used by routes, services, and frontend callers.
from __future__ import annotations

from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel


class FolderCreateRequest(APIModel):
    # Request contract for folder create; FastAPI validates incoming JSON against these fields before service
    # code runs.
    name: str = Field(min_length=1)
    description: str | None = None


class FolderRenameRequest(APIModel):
    # Request contract for folder rename; FastAPI validates incoming JSON against these fields before service
    # code runs.
    name: str = Field(min_length=1)


class FolderMoveRequest(APIModel):
    # Request contract for folder move; FastAPI validates incoming JSON against these fields before service code
    # runs.
    content_version_id: UUID
    folder_id: UUID

