# Pydantic schemas define the API contracts used by routes, services, and frontend callers.
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel


class BrandAttachmentUploadRequest(APIModel):
    # Request contract for brand attachment upload; FastAPI validates incoming JSON against these fields before
    # service code runs.
    name: str
    filename: str
    mime_type: str
    content_base64: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    desired_category: str | None = None
    skip_processing: bool = False


class AssetCategoryRoutingResponse(APIModel):
    # Response contract for asset category routing; routes serialize service or ORM results into this frontend-
    # facing shape.
    requested_field_key: str
    requested_category: str | None = None
    routed_category: str
    classifier: str | None = None
    confidence: float | None = None
    routing_reason: str | None = None
    decision_json: dict[str, Any] = Field(default_factory=dict)


class AssetProcessingStatusResponse(APIModel):
    # Response contract for asset processing status; routes serialize service or ORM results into this frontend-
    # facing shape.
    field_key: str
    lifecycle_state: str
    processor_name: str | None = None
    progress_current: int = 0
    progress_total: int = 0
    status_message: str | None = None
    raw_status_json: dict[str, Any] = Field(default_factory=dict)


class AssetValidationResultResponse(APIModel):
    # Response contract for asset validation result; routes serialize service or ORM results into this frontend-
    # facing shape.
    field_key: str
    validation_state: str
    trust_level: str | None = None
    warnings: list[str] = Field(default_factory=list)
    exclusion_reason: str | None = None
    resolved_payload: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = None


class ReusableBrandAssetResponse(APIModel):
    # Response contract for reusable brand asset; routes serialize service or ORM results into this frontend-
    # facing shape.
    id: UUID
    knowledge_asset_id: UUID
    asset_kind: str
    review_class: str | None = None
    review_status: str | None = None
    review_reason: str | None = None
    label: str | None = None
    mime_type: str
    storage_path: str
    asset_url: str | None = None
    width: int | None = None
    height: int | None = None
    confidence: float | None = None
    is_active: bool = True
    source_metadata_json: dict[str, Any] = Field(default_factory=dict)
    normalized_metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class BrandAttachmentResponse(APIModel):
    # Response contract for brand attachment; routes serialize service or ORM results into this frontend-facing
    # shape.
    id: UUID
    tenant_id: UUID
    brand_space_id: UUID | None = None
    name: str
    original_filename: str
    mime_type: str
    storage_path: str
    asset_url: str | None = None
    lifecycle_state: str
    channel: str
    field_key: str | None = None
    asset_category: str | None = None
    classification_confidence: float | None = None
    page_count: int
    is_active: bool
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    structured_data_json: dict[str, Any] = Field(default_factory=dict)
    normalized_data_json: dict[str, Any] = Field(default_factory=dict)
    processing_error: str | None = None
    validation_state: str = "pending"
    validation_summary_json: dict[str, Any] = Field(default_factory=dict)
    processing_status: AssetProcessingStatusResponse | None = None
    validation_result: AssetValidationResultResponse | None = None
    routing: AssetCategoryRoutingResponse | None = None
    reusable_assets: list[ReusableBrandAssetResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class BrandAttachmentListResponse(APIModel):
    # Response contract for brand attachment list; routes serialize service or ORM results into this frontend-
    # facing shape.
    field_key: str
    assets: list[BrandAttachmentResponse] = Field(default_factory=list)


class BrandAttachmentStatusUpdateResponse(APIModel):
    # Response contract for brand attachment status update; routes serialize service or ORM results into this
    # frontend-facing shape.
    asset: BrandAttachmentResponse
    message: str


class DataConflictResponse(APIModel):
    # Response contract for data conflict; routes serialize service or ORM results into this frontend-facing
    # shape.
    id: UUID
    conflict_type: str
    severity: str
    field_keys: list[str] = Field(default_factory=list)
    knowledge_asset_ids: list[str] = Field(default_factory=list)
    details_json: dict[str, Any] = Field(default_factory=dict)
    resolution_status: str
    resolved_payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ResolvedBrandContextResponse(APIModel):
    # Response contract for resolved brand context; routes serialize service or ORM results into this frontend-
    # facing shape.
    brand_space_id: UUID
    snapshot_id: UUID | None = None
    snapshot_kind: str = "validated"
    status: str = "active"
    warnings: list[str] = Field(default_factory=list)
    excluded_asset_ids: list[str] = Field(default_factory=list)
    context_json: dict[str, Any] = Field(default_factory=dict)


class ValidationSummaryResponse(APIModel):
    # Response contract for validation summary; routes serialize service or ORM results into this frontend-
    # facing shape.
    brand_space_id: UUID
    warnings: list[str] = Field(default_factory=list)
    conflicts: list[DataConflictResponse] = Field(default_factory=list)
    excluded_assets: list[str] = Field(default_factory=list)
    validation_results: list[AssetValidationResultResponse] = Field(default_factory=list)
    latest_snapshot: ResolvedBrandContextResponse | None = None


class BrandLegalAssetResponse(APIModel):
    # Response contract for brand legal asset; routes serialize service or ORM results into this frontend-facing
    # shape.
    id: UUID
    brand_space_id: UUID
    asset_type: str
    text_template: str
    applies_to_formats: list[str] = Field(default_factory=list)
    position: str = "footer"
    font_size: int = 8
    text_color: str = "#666666"
    confidence: float = 1.0
    source_asset_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class BrandCTATemplateResponse(APIModel):
    # Response contract for brand CTAtemplate; routes serialize service or ORM results into this frontend-facing
    # shape.
    id: UUID
    brand_space_id: UUID
    template_name: str
    headline_template: str | None = None
    body_template: str | None = None
    button_text: str
    button_color: str
    button_text_color: str = "#FFFFFF"
    button_style: str = "rounded"
    icon_hint: str | None = None
    visual_theme: str | None = None
    is_default: bool = False
    created_at: datetime
    updated_at: datetime
