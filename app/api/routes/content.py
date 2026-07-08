# FastAPI route handlers live here; they validate request inputs, call services, and return response schemas.
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    CurrentPrincipal,
    assert_brand_access,
    get_brand_scope_header,
    get_current_principal,
    require_brand_scope,
)
from app.db.session import get_db_session
from app.repositories.content import AssetRepository, ContentRepository
from app.schemas.content import ContentCopyRequest, ContentExportRequest, ContentGenerateRequest, ContentImageEditApplyRequest, ContentImageEditStateRequest, ContentImageEditStateResponse, ContentImageEditVariant, ContentRewriteRequest, ContentVersionResponse, ToneCheckRequest, ToneEvaluationResponse
from app.schemas.common import AssetReference
from app.schemas.render import RenderResponse
from app.services.content import ContentService


router = APIRouter()
_IMAGE_EDIT_STATES: dict[str, ContentImageEditStateResponse] = {}
_IMAGE_EDIT_TARGET_STYLES: dict[str, dict[str, str]] = {
    "background": {"filter": "brightness(1.04) saturate(0.92) hue-rotate(8deg)"},
    "text": {"filter": "contrast(1.14) brightness(0.98)"},
    "color": {"filter": "saturate(1.28) hue-rotate(16deg)"},
    "logo placement": {"filter": "drop-shadow(0 10px 14px rgba(59, 45, 145, 0.22))"},
    "layout": {"filter": "brightness(1.02) contrast(1.06)"},
}


def _image_edit_key(content_version_id: UUID, source_asset: AssetReference) -> str:
    return f"{content_version_id}:{source_asset.asset_id}"


def _image_edit_original_variant(source_asset: AssetReference) -> ContentImageEditVariant:
    return ContentImageEditVariant(
        id="original",
        label="Original",
        target="Original",
        instructions="Original generated image",
        asset=source_asset,
        preview_style={},
        created_at=datetime.now(timezone.utc),
        is_original=True,
    )


def _image_edit_state(payload: ContentImageEditStateRequest) -> ContentImageEditStateResponse:
    key = _image_edit_key(payload.content_version_id, payload.source_asset)
    state = _IMAGE_EDIT_STATES.get(key)
    if state:
        return state
    state = ContentImageEditStateResponse(
        content_version_id=payload.content_version_id,
        source_asset_id=payload.source_asset.asset_id,
        variants=[_image_edit_original_variant(payload.source_asset)],
    )
    _IMAGE_EDIT_STATES[key] = state
    return state


def _image_edit_style(target: str, variant_count: int) -> dict[str, str]:
    normalized = target.strip().lower()
    style = dict(_IMAGE_EDIT_TARGET_STYLES.get(normalized, {"filter": "brightness(1.03) contrast(1.04)"}))
    style["variant_tone"] = str(variant_count)
    return style


async def _resolve_image_edit_payload(
    payload: ContentImageEditStateRequest,
    principal: CurrentPrincipal,
    brand_scope: UUID,
    session: AsyncSession,
) -> ContentImageEditStateRequest:
    content_repo = ContentRepository(session)
    content = await content_repo.get_scoped(payload.content_version_id, principal.tenant_id, brand_scope)
    if content:
        return payload

    asset = await AssetRepository(session).get_scoped(payload.source_asset.asset_id, principal.tenant_id, brand_scope)
    if asset and asset.content_version_id:
        content = await content_repo.get_scoped(asset.content_version_id, principal.tenant_id, brand_scope)
        if content:
            return payload.model_copy(update={"content_version_id": asset.content_version_id})

    raise HTTPException(status_code=404, detail="Content version not found")


def attach_assets(content, assets) -> ContentVersionResponse:
    # Builds API response data from service or ORM objects, keeping persistence details out of route returns.
    response = ContentVersionResponse.model_validate(content)
    explainability = content.explainability_metadata or {}
    response.generation_decision = explainability.get("layout_decision", {})
    response.scene_graph = explainability.get("scene_graph", {})
    response.creative_decision = explainability.get("creative_decision", {}) or response.generation_decision
    response.validation_report = explainability.get("validation_report", {})
    response.repair_attempts = int(explainability.get("repair_attempts", 0) or 0)
    response.assets = [
        AssetReference(
            asset_id=item.id,
            mime_type=item.mime_type,
            storage_path=item.storage_path,
            width=item.width,
            height=item.height,
            asset_role=item.asset_role,
        )
        for item in assets
    ]
    return response



@router.post("/image-edits/state", response_model=ContentImageEditStateResponse)
async def image_edit_state(
    payload: ContentImageEditStateRequest,
    brand_scope: UUID = Depends(get_brand_scope_header),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> ContentImageEditStateResponse:
    brand_scope = require_brand_scope(brand_scope)
    assert_brand_access(principal, brand_scope)
    resolved_payload = await _resolve_image_edit_payload(payload, principal, brand_scope, session)
    return _image_edit_state(resolved_payload)


@router.post("/image-edits/apply", response_model=ContentImageEditStateResponse)
async def apply_image_edit(
    payload: ContentImageEditApplyRequest,
    brand_scope: UUID = Depends(get_brand_scope_header),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> ContentImageEditStateResponse:
    brand_scope = require_brand_scope(brand_scope)
    assert_brand_access(principal, brand_scope)
    resolved_payload = await _resolve_image_edit_payload(payload, principal, brand_scope, session)
    state = _image_edit_state(resolved_payload)
    edited_count = len([item for item in state.variants if not item.is_original]) + 1
    state.variants.append(
        ContentImageEditVariant(
            id=str(uuid4()),
            label=f"Edited {edited_count}",
            target=payload.target.strip(),
            instructions=payload.instructions.strip(),
            asset=resolved_payload.source_asset,
            preview_style=_image_edit_style(payload.target, edited_count),
            created_at=datetime.now(timezone.utc),
            is_original=False,
        )
    )
    _IMAGE_EDIT_STATES[_image_edit_key(resolved_payload.content_version_id, resolved_payload.source_asset)] = state
    return state

@router.post("/generate", response_model=ContentVersionResponse)
async def generate_content(
    payload: ContentGenerateRequest,
    brand_scope: UUID = Depends(get_brand_scope_header),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> ContentVersionResponse:
    # Serves the content generation endpoint; it checks brand scope, delegates work to services, and returns the
    # response schema.
    brand_scope = require_brand_scope(brand_scope)
    assert_brand_access(principal, brand_scope)

    service = ContentService(session)
    content = await service.generate(principal.tenant_id, brand_scope, principal.user_id, payload)
    assets = await AssetRepository(session).list_by_content(content.id)

    return attach_assets(content, assets)


@router.post("/rewrite", response_model=ContentVersionResponse)
async def rewrite_content(
    payload: ContentRewriteRequest,
    brand_scope: UUID = Depends(get_brand_scope_header),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> ContentVersionResponse:
    # Serves the content rewrite endpoint; it checks brand scope, delegates work to services, and returns the
    # response schema.
    brand_scope = require_brand_scope(brand_scope)
    assert_brand_access(principal, brand_scope)

    content = await ContentService(session).rewrite(principal.tenant_id, brand_scope, principal.user_id, payload)
    assets = await AssetRepository(session).list_by_content(content.id)

    return attach_assets(content, assets)


@router.post("/tone-check", response_model=ToneEvaluationResponse)
async def tone_check(
    payload: ToneCheckRequest,
    brand_scope: UUID = Depends(get_brand_scope_header),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> ToneEvaluationResponse:
    # Serves the tone check endpoint; it checks brand scope, delegates work to services, and returns the
    # response schema.
    brand_scope = require_brand_scope(brand_scope)
    assert_brand_access(principal, brand_scope)
    result = await ContentService(session).tone_check(brand_scope, payload)
    return ToneEvaluationResponse(**result)


@router.get("/history", response_model=list[ContentVersionResponse])
async def content_history(
    brand_scope: UUID = Depends(get_brand_scope_header),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> list[ContentVersionResponse]:
    # Serves the content history endpoint; it checks brand scope, delegates work to services, and returns the
    # response schema.
    brand_scope = require_brand_scope(brand_scope)
    assert_brand_access(principal, brand_scope)

    service = ContentService(session)
    history = await service.history(principal.tenant_id, brand_scope)

    asset_repo = AssetRepository(session)
    items = []

    for content in history:
        assets = await asset_repo.list_by_content(content.id)
        items.append(attach_assets(content, assets))

    return items


@router.get("/{content_id}", response_model=ContentVersionResponse)
async def content_detail(
    content_id: UUID,
    brand_scope: UUID = Depends(get_brand_scope_header),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> ContentVersionResponse:
    # Serves the content detail endpoint; it checks brand scope, delegates work to services, and returns the
    # response schema.
    brand_scope = require_brand_scope(brand_scope)
    assert_brand_access(principal, brand_scope)

    service = ContentService(session)
    content = await service.detail(principal.tenant_id, brand_scope, content_id)
    assets = await AssetRepository(session).list_by_content(content.id)

    return attach_assets(content, assets)


@router.post("/export", response_model=RenderResponse)
async def export_content(
    payload: ContentExportRequest,
    brand_scope: UUID = Depends(get_brand_scope_header),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> RenderResponse:
    # Serves the content export endpoint; it checks brand scope, delegates work to services, and returns the
    # response schema.
    brand_scope = require_brand_scope(brand_scope)
    assert_brand_access(principal, brand_scope)

    response = await ContentService(session).export(
        principal.tenant_id,
        brand_scope,
        payload.content_version_id,
        (payload.studio_panel or {}) | {"file_type": payload.export_format},
        blueprint_payload=payload.blueprint_payload,
        template_id=payload.template_id,
    )

    return RenderResponse(content_version_id=payload.content_version_id, **response)


@router.post("/copy", response_model=dict)
async def copy_content(
    payload: ContentCopyRequest,
    brand_scope: UUID = Depends(get_brand_scope_header),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    # Serves the content copy endpoint; it checks brand scope, delegates work to services, and returns the
    # response schema.
    brand_scope = require_brand_scope(brand_scope)
    assert_brand_access(principal, brand_scope)

    return await ContentService(session).copy(principal.tenant_id, brand_scope, payload.content_version_id)


@router.post("/{content_id}/archive", response_model=ContentVersionResponse)
async def archive_content(
    content_id: UUID,
    brand_scope: UUID = Depends(get_brand_scope_header),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> ContentVersionResponse:
    # Serves the content archive endpoint; it checks brand scope, delegates work to services, and returns the
    # response schema.
    brand_scope = require_brand_scope(brand_scope)
    assert_brand_access(principal, brand_scope)

    content = await ContentService(session).archive(principal.tenant_id, brand_scope, content_id)
    assets = await AssetRepository(session).list_by_content(content.id)
    return attach_assets(content, assets)


@router.delete("/{content_id}", response_model=dict)
async def delete_content(
    content_id: UUID,
    brand_scope: UUID = Depends(get_brand_scope_header),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    # Serves the content deletion endpoint; it checks brand scope, delegates work to services, and returns the
    # response schema.
    brand_scope = require_brand_scope(brand_scope)
    assert_brand_access(principal, brand_scope)

    return await ContentService(session).delete(principal.tenant_id, brand_scope, content_id)
