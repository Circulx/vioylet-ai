# Pydantic schemas define the API contracts used by routes, services, and frontend callers.
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import APIModel


PhoneNumber = Annotated[str, Field(pattern=r"^\d{10}$")]


class TenantUsageLimitUpdate(APIModel):
    # Shared schema for tenant usage limit update; it keeps route payloads, service data, and serialized
    # responses aligned.
    max_users: int = Field(ge=0)
    max_brand_spaces: int = Field(ge=0)
    max_content_generations: int = Field(ge=0)
    max_image_generations: int = Field(ge=0)
    max_ocr_pages: int = Field(ge=0)


class TenantCreateRequest(APIModel):
    # Request contract for tenant create; FastAPI validates incoming JSON against these fields before service
    # code runs.
    name: str
    slug: str
    contact_email: EmailStr
    contact_number: PhoneNumber | None = None
    address: str | None = None
    admin_full_name: str
    admin_email: EmailStr
    admin_phone_number: PhoneNumber | None = None
    usage_limits: TenantUsageLimitUpdate
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class TenantUpdateRequest(APIModel):
    # Request contract for tenant update; FastAPI validates incoming JSON against these fields before service
    # code runs.
    name: str | None = None
    slug: str | None = None
    contact_email: EmailStr | None = None
    contact_number: PhoneNumber | None = None
    address: str | None = None
    admin_full_name: str | None = None
    admin_email: EmailStr | None = None
    admin_phone_number: PhoneNumber | None = None
    usage_limits: TenantUsageLimitUpdate | None = None
    metadata_json: dict[str, Any] | None = None
    is_active: bool | None = None


class TenantBrandUsageTargetsUpdate(APIModel):
    # Shared schema for tenant brand usage targets update; it keeps route payloads, service data, and serialized
    # responses aligned.
    brand_usage_targets: dict[str, float] = Field(default_factory=dict)

    @field_validator("brand_usage_targets")
    @classmethod
    def validate_brand_usage_targets(cls, value: dict[str, float]) -> dict[str, float]:
        # Checks or reshapes brand usage targets while Pydantic prepares the model for validation or
        # serialization.
        normalized: dict[str, float] = {}
        total = 0.0
        for brand_id, target in value.items():
            try:
                UUID(str(brand_id))
                numeric_target = float(target)
            except (TypeError, ValueError) as exc:
                raise ValueError("Brand usage targets must use valid brand IDs and numeric percentages.") from exc
            if numeric_target < 0 or numeric_target > 100:
                raise ValueError("Brand usage target percentages must be between 0 and 100.")
            normalized[str(brand_id)] = numeric_target
            total += numeric_target
        if total > 100:
            raise ValueError("Brand usage allocation cannot exceed 100%.")
        return normalized


class TenantBrandUsageTargetsResponse(APIModel):
    # Response contract for tenant brand usage targets; routes serialize service or ORM results into this
    # frontend-facing shape.
    brand_usage_targets: dict[str, float] = Field(default_factory=dict)


class TenantLogoUploadRequest(APIModel):
    # Request contract for tenant logo upload; FastAPI validates incoming JSON against these fields before
    # service code runs.
    filename: str
    mime_type: str
    content_base64: str


class TenantResponse(APIModel):
    # Response contract for tenant; routes serialize service or ORM results into this frontend-facing shape.
    id: UUID
    name: str
    slug: str
    contact_email: EmailStr
    contact_number: str | None = None
    address: str | None = None
    logo_asset_path: str | None = None
    is_active: bool
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class TenantCreateResponse(TenantResponse):
    # Response contract for tenant create; routes serialize service or ORM results into this frontend-facing
    # shape.
    activation_email: ActivationEmailStatus


class TenantSummaryResponse(TenantResponse):
    # Response contract for tenant summary; routes serialize service or ORM results into this frontend-facing
    # shape.
    total_users: int = 0
    brand_space_count: int = 0
    usage_limits: TenantUsageLimitUpdate | None = None
    usage_consumption: dict[str, int] = Field(default_factory=dict)
    token_usage: dict[str, int] = Field(default_factory=dict)
    monthly_token_usage: list[dict[str, int | str]] = Field(default_factory=list)
    tenant_admin_name: str | None = None
    tenant_admin_email: EmailStr | None = None
    tenant_admin_phone_number: str | None = None
    tenant_admin_user_id: UUID | None = None
    tenant_admin_is_active: bool | None = None
    tenant_admin_is_activated: bool | None = None
    tenant_admin_activation_link_sent_count: int = 0
    tenant_admin_activation_link_attempts_left: int = 0
    last_active_at: datetime | None = None


class TenantUserCreateRequest(APIModel):
    # Request contract for tenant user create; FastAPI validates incoming JSON against these fields before
    # service code runs.
    full_name: str
    email: EmailStr
    phone_number: str | None = None
    role_code: str
    brand_space_ids: list[UUID] = Field(default_factory=list)


class TenantUserUpdateRequest(APIModel):
    # Request contract for tenant user update; FastAPI validates incoming JSON against these fields before
    # service code runs.
    full_name: str | None = None
    email: EmailStr | None = None
    phone_number: str | None = None
    role_code: str | None = None
    brand_space_ids: list[UUID] | None = None
    is_active: bool | None = None


class TenantUserResponse(APIModel):
    # Response contract for tenant user; routes serialize service or ORM results into this frontend-facing
    # shape.
    id: UUID
    tenant_id: UUID | None = None
    email: EmailStr
    full_name: str
    phone_number: str | None = None
    is_active: bool
    is_activated: bool
    role_codes: list[str]
    brand_space_ids: list[UUID]
    created_at: datetime
    last_login_at: datetime | None = None
    activation_link_sent_count: int = 0
    activation_link_attempts_left: int = 0


class ActivationEmailStatus(APIModel):
    # Shared schema for activation email status; it keeps route payloads, service data, and serialized responses
    # aligned.
    attempted: bool
    delivered: bool
    recipient_email: EmailStr
    reason: str | None = None


class TenantUserCreateResponse(TenantUserResponse):
    # Response contract for tenant user create; routes serialize service or ORM results into this frontend-
    # facing shape.
    activation_email: ActivationEmailStatus


class TenantBrandSpaceSummaryResponse(APIModel):
    # Response contract for tenant brand space summary; routes serialize service or ORM results into this
    # frontend-facing shape.
    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    lifecycle_state: str
    created_at: datetime
    last_active_at: datetime | None = None
    last_login_at: datetime | None = None
    content_generations: int = 0
    visual_generations: int = 0
    ocr_pages: int = 0


class TenantUsageMonthResponse(APIModel):
    # Response contract for tenant usage month; routes serialize service or ORM results into this frontend-
    # facing shape.
    month: str
    content_generations: int = 0
    image_generations: int = 0
    ocr_pages: int = 0


class TenantBrandUsageResponse(APIModel):
    # Response contract for tenant brand usage; routes serialize service or ORM results into this frontend-
    # facing shape.
    id: UUID
    name: str
    allocation_percent: float = 0
    content_generations: int = 0
    image_generations: int = 0
    ocr_pages: int = 0
    monthly_usage: list[TenantUsageMonthResponse] = Field(default_factory=list)


class TenantUsageSummary(APIModel):
    # Shared schema for tenant usage summary; it keeps route payloads, service data, and serialized responses
    # aligned.
    tenant_id: UUID
    limits: TenantUsageLimitUpdate
    consumption: dict[str, int]
    monthly_usage: list[TenantUsageMonthResponse] = Field(default_factory=list)
    brand_usage: list[TenantBrandUsageResponse] = Field(default_factory=list)
