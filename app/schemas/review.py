# Pydantic schemas define the API contracts used by routes, services, and frontend callers.
from __future__ import annotations

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


class ReviewStatusUpdateRequest(APIModel):
    # Request contract for review status update; FastAPI validates incoming JSON against these fields before
    # service code runs.
    status: str


class ReviewLinkResponse(APIModel):
    # Response contract for review link; routes serialize service or ORM results into this frontend-facing
    # shape.
    id: UUID
    token: str
    status: str
    allow_external_comments: bool


class ReviewCommentResponse(APIModel):
    # Response contract for review comment; routes serialize service or ORM results into this frontend-facing
    # shape.
    id: UUID
    body: str
    external_author_name: str | None = None
    author_user_id: UUID | None = None


class ReviewDetailContent(APIModel):
    # Shared schema for review detail content; it keeps route payloads, service data, and serialized responses
    # aligned.
    id: UUID
    title: str | None = None
    generated_payload: dict
    blueprint_payload: dict
    generation_decision: dict = Field(default_factory=dict)
    assets: list[AssetReference] = Field(default_factory=list)


class ReviewDetailResponse(APIModel):
    # Response contract for review detail; routes serialize service or ORM results into this frontend-facing
    # shape.
    link: ReviewLinkResponse
    content: ReviewDetailContent | None = None
    comments: list[ReviewCommentResponse] = Field(default_factory=list)
