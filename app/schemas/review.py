# Pydantic schemas define the API contracts used by routes, services, and frontend callers.
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel, AssetReference


class ShareLinkCreateRequest(APIModel):
    # Request contract for share link create; FastAPI validates incoming JSON against these fields before
    # service code runs.
    content_version_id: UUID
    title: str | None = None
    allow_external_comments: bool = True


class ReviewCommentCreateRequest(APIModel):
    # Request contract for review comment create; FastAPI validates incoming JSON against these fields before
    # service code runs.
    body: str = Field(min_length=1)
    external_author_name: str | None = None
    parent_comment_id: UUID | None = None


class ReviewStatusUpdateRequest(APIModel):
    # Request contract for review status update; FastAPI validates incoming JSON against these fields before
    # service code runs.
    status: str


class ReviewShareAccessUpdateRequest(APIModel):
    user_ids: list[UUID] = Field(default_factory=list)


class ReviewLinkResponse(APIModel):
    # Response contract for review link; routes serialize service or ORM results into this frontend-facing
    # shape.
    id: UUID
    token: str
    status: str
    allow_external_comments: bool
    created_by_name: str | None = None


class ReviewCommentResponse(APIModel):
    # Response contract for review comment; routes serialize service or ORM results into this frontend-facing
    # shape.
    id: UUID
    body: str
    parent_comment_id: UUID | None = None
    external_author_name: str | None = None
    author_user_id: UUID | None = None
    created_at: datetime


class ReviewDetailContent(APIModel):
    # Shared schema for review detail content; it keeps route payloads, service data, and serialized responses
    # aligned.
    id: UUID
    title: str | None = None
    brand_name: str | None = None
    generated_payload: dict
    blueprint_payload: dict
    generation_decision: dict = Field(default_factory=dict)
    assets: list[AssetReference] = Field(default_factory=list)
    display_assets: list[AssetReference] = Field(default_factory=list)


class ReviewDetailResponse(APIModel):
    # Response contract for review detail; routes serialize service or ORM results into this frontend-facing
    # shape.
    link: ReviewLinkResponse
    content: ReviewDetailContent | None = None
    comments: list[ReviewCommentResponse] = Field(default_factory=list)


class ReviewUserSummary(APIModel):
    id: UUID
    full_name: str
    email: str
    role_codes: list[str] = Field(default_factory=list)


class ReviewParticipantResponse(ReviewUserSummary):
    access_role: str = "viewer"
    is_owner: bool = False


class ReviewShareAccessResponse(APIModel):
    owner: ReviewParticipantResponse | None = None
    participants: list[ReviewParticipantResponse] = Field(default_factory=list)
    mentionable_users: list[ReviewUserSummary] = Field(default_factory=list)
