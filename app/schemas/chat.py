# Pydantic schemas define the API contracts used by routes, services, and frontend callers.
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel, StudioPanelSelection


class ChatSessionCreateRequest(APIModel):
    # Request contract for chat session create; FastAPI validates incoming JSON against these fields before
    # service code runs.
    title: str | None = None
    studio_panel: StudioPanelSelection


class ChatSessionUpdateRequest(APIModel):
    # Request contract for chat session update; FastAPI validates incoming JSON against these fields before
    # service code runs.
    title: str | None = Field(default=None, max_length=255)


class ChatMessageCreateRequest(APIModel):
    # Request contract for chat message create; FastAPI validates incoming JSON against these fields before
    # service code runs.
    message: str = Field(min_length=1)
    studio_panel: StudioPanelSelection | None = None
    persona_id: UUID | None = None
    objective_id: UUID | None = None
    template_id: UUID | None = None
    reference_asset_ids: list[UUID] = Field(default_factory=list)
    generate_image: bool = True


class ChatSessionResponse(APIModel):
    # Response contract for chat session; routes serialize service or ORM results into this frontend-facing
    # shape.
    id: UUID
    brand_space_id: UUID | None = None
    title: str | None = None
    session_kind: str
    studio_panel: dict
    conversational_context: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ChatMessageResponse(APIModel):
    # Response contract for chat message; routes serialize service or ORM results into this frontend-facing
    # shape.
    id: UUID
    session_id: UUID
    user_id: UUID | None = None
    content_version_id: UUID | None = None
    role: str
    message_text: str
    structured_payload: dict
    citations: list[dict]
    created_at: datetime


class ChatSendResponse(APIModel):
    # Response contract for chat send; routes serialize service or ORM results into this frontend-facing shape.
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
