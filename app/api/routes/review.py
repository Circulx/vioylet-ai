# FastAPI route handlers live here; they validate request inputs, call services, and return response schemas.
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentPrincipal, assert_brand_access, assert_tenant_access, get_current_principal, get_brand_scope_header, require_brand_scope, require_roles
from app.core.enums import RoleCode
from app.db.session import get_db_session
from app.models.brand import BrandSpace
from app.models.tenant import User
from app.repositories.content import AssetRepository, ChatMessageRepository, ContentRepository
from app.schemas.common import AssetReference
from app.schemas.review import (
    ReviewCommentCreateRequest,
    ReviewCommentResponse,
    ReviewDetailContent,
    ReviewDetailResponse,
    ReviewLinkResponse,
    ReviewStatusUpdateRequest,
    ShareLinkCreateRequest,
)
from app.services.asset_delivery import AssetDeliveryService
from app.services.review import ReviewService


router = APIRouter()


def _asset_reference_from_payload(asset: object, delivery: AssetDeliveryService) -> AssetReference | None:
    if not isinstance(asset, dict):
        return None
    storage_path = str(asset.get("storage_path") or "").strip()
    mime_type = str(asset.get("mime_type") or "").strip()
    asset_role = str(asset.get("asset_role") or "").strip()
    asset_id = asset.get("asset_id")
    if not storage_path or not mime_type or not asset_role or not asset_id:
        return None
    try:
        parsed_asset_id = UUID(str(asset_id))
    except (TypeError, ValueError):
        return None
    return AssetReference(
        asset_id=parsed_asset_id,
        mime_type=mime_type,
        storage_path=storage_path,
        asset_url=delivery.build_signed_url(
            storage_path=storage_path,
            filename=storage_path.rsplit("/", 1)[-1],
        ),
        width=asset.get("width") if isinstance(asset.get("width"), int) else None,
        height=asset.get("height") if isinstance(asset.get("height"), int) else None,
        asset_role=asset_role,
    )


def _payload_asset_list(payload: dict, key: str, delivery: AssetDeliveryService) -> list[AssetReference]:
    value = payload.get(key)
    if not isinstance(value, list):
        return []
    assets: list[AssetReference] = []
    seen: set[str] = set()
    for item in value:
        asset = _asset_reference_from_payload(item, delivery)
        if not asset or not asset.mime_type.startswith("image/") or not asset.asset_url:
            continue
        dedupe_key = asset.storage_path or str(asset.asset_id)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        assets.append(asset)
    return assets


def _display_assets_from_payload(payload: object, delivery: AssetDeliveryService) -> list[AssetReference]:
    if not isinstance(payload, dict):
        return []
    export_assets = _payload_asset_list(payload, "export_assets", delivery)
    if export_assets:
        return export_assets
    preview_asset = _asset_reference_from_payload(payload.get("preview_asset"), delivery)
    if preview_asset and preview_asset.mime_type.startswith("image/") and preview_asset.asset_url:
        return [preview_asset]
    payload_assets = [
        asset
        for asset in _payload_asset_list(payload, "assets", delivery)
        if asset.asset_role in {"render_export", "render_preview", "ai_image"}
    ]
    return payload_assets


@router.post("/share-link", response_model=ReviewLinkResponse)
async def create_share_link(
    payload: ShareLinkCreateRequest,
    brand_scope: UUID = Depends(get_brand_scope_header),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> ReviewLinkResponse:
    # Serves the share link creation endpoint; it checks brand scope, delegates work to services, and returns
    # the response schema.
    brand_scope = require_brand_scope(brand_scope)
    assert_brand_access(principal, brand_scope)
    link = await ReviewService(session).create_link(principal.tenant_id, brand_scope, payload.content_version_id, principal.user_id, payload.title, payload.allow_external_comments)
    creator = await session.get(User, principal.user_id)
    return ReviewLinkResponse.model_validate(link).model_copy(
        update={"created_by_name": creator.full_name if creator else None}
    )


@router.get("/{token}", response_model=ReviewDetailResponse)
async def get_review(token: str, session: AsyncSession = Depends(get_db_session)) -> dict:
    # Serves the review detail lookup endpoint; it uses FastAPI dependencies, delegates work to services, and
    # returns the response schema.
    link, comments = await ReviewService(session).get_by_token(token)
    creator = await session.get(User, link.created_by)
    brand_space = await session.get(BrandSpace, link.brand_space_id)
    content = await ContentRepository(session).get_scoped(link.content_version_id, link.tenant_id, link.brand_space_id)
    assets = await AssetRepository(session).list_by_content(link.content_version_id)
    delivery = AssetDeliveryService()
    assistant_message = await ChatMessageRepository(session).get_latest_assistant_by_content(
        link.content_version_id,
        link.tenant_id,
        link.brand_space_id,
    )
    display_assets = _display_assets_from_payload(
        assistant_message.structured_payload if assistant_message else {},
        delivery,
    )
    return ReviewDetailResponse(
        link=ReviewLinkResponse.model_validate(link).model_copy(
            update={"created_by_name": creator.full_name if creator else None}
        ).model_dump(),
        content=ReviewDetailContent(
            id=content.id,
            title=content.title,
            brand_name=brand_space.name if brand_space else None,
            generated_payload=content.generated_payload,
            blueprint_payload=content.blueprint_payload,
            generation_decision=content.explainability_metadata.get("layout_decision", {}),
            display_assets=display_assets,
            assets=[
                AssetReference(
                    asset_id=item.id,
                    mime_type=item.mime_type,
                    storage_path=item.storage_path,
                    asset_url=delivery.build_signed_url(
                        storage_path=item.storage_path,
                        filename=item.storage_path.rsplit("/", 1)[-1],
                    ),
                    width=item.width,
                    height=item.height,
                    asset_role=item.asset_role,
                )
                for item in assets
            ],
        ) if content else None,
        comments=[
            ReviewCommentResponse(
                id=item.id,
                body=item.body,
                parent_comment_id=item.parent_comment_id,
                external_author_name=item.external_author_name,
                author_user_id=item.author_user_id,
            )
            for item in comments
        ],
    )


@router.post("/{token}/comment", response_model=ReviewCommentResponse)
async def add_comment(token: str, payload: ReviewCommentCreateRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    # Serves the add comment endpoint; it uses FastAPI dependencies, delegates work to services, and returns the
    # response schema.
    service = ReviewService(session)
    link, _ = await service.get_by_token(token)
    comment = await service.add_comment(
        link.id,
        link.tenant_id,
        link.brand_space_id,
        payload.body,
        None,
        payload.external_author_name,
        payload.parent_comment_id,
    )
    return ReviewCommentResponse(
        id=comment.id,
        body=comment.body,
        parent_comment_id=comment.parent_comment_id,
        external_author_name=comment.external_author_name,
        author_user_id=comment.author_user_id,
    )


@router.post("/{token}/status", response_model=ReviewLinkResponse)
async def update_review_status(
    token: str,
    payload: ReviewStatusUpdateRequest,
    principal: CurrentPrincipal = Depends(require_roles(RoleCode.TENANT_ADMIN)),
    session: AsyncSession = Depends(get_db_session),
) -> ReviewLinkResponse:
    # Serves the review status update endpoint; it uses FastAPI dependencies, delegates work to services, and
    # returns the response schema.
    service = ReviewService(session)
    link, _ = await service.get_by_token(token)
    assert_tenant_access(principal, link.tenant_id)
    assert_brand_access(principal, link.brand_space_id)
    updated = await service.update_status(link.id, payload.status)
    creator = await session.get(User, updated.created_by)
    return ReviewLinkResponse.model_validate(updated).model_copy(
        update={"created_by_name": creator.full_name if creator else None}
    )
