# FastAPI route handlers live here; they validate request inputs, call services, and return response schemas.
import re
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentPrincipal, assert_brand_access, assert_tenant_access, get_current_principal, get_brand_scope_header, require_brand_scope, require_roles
from app.core.enums import RoleCode
from app.core.security import decode_token
from app.db.session import AsyncSessionLocal, get_db_session
from app.models.brand import BrandSpace, BrandSpaceMember
from app.models.content import ContentVersion, GeneratedAsset
from app.models.tenant import Role, User, UserRole
from app.repositories.content import AssetRepository, ChatMessageRepository, ContentRepository
from app.schemas.common import AssetReference
from app.schemas.review import (
    ReviewCommentCreateRequest,
    ReviewCommentResponse,
    ReviewDetailContent,
    ReviewDetailResponse,
    ReviewLinkResponse,
    ReviewParticipantResponse,
    ReviewShareAccessResponse,
    ReviewShareAccessUpdateRequest,
    ReviewUserSummary,
    ReviewStatusUpdateRequest,
    ShareLinkCreateRequest,
)
from app.services.asset_delivery import AssetDeliveryService
from app.services.review import ReviewService


router = APIRouter()


async def _send_comment_notifications_background(review_link_id: UUID, comment_id: UUID) -> None:
    async with AsyncSessionLocal() as session:
        await ReviewService(session).send_comment_notifications_for_comment(
            review_link_id,
            comment_id,
        )


async def _optional_principal_from_authorization(
    authorization: str | None,
    session: AsyncSession,
) -> CurrentPrincipal | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None
    try:
        payload = decode_token(token)
        user_id = UUID(payload["sub"])
    except Exception:  # noqa: BLE001
        return None
    user = await session.get(User, user_id)
    if not user or not user.is_active:
        return None
    role_result = await session.execute(
        select(Role.code)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    role_rows_result = await session.execute(
        select(UserRole.brand_space_id).where(
            UserRole.user_id == user.id,
            UserRole.brand_space_id.is_not(None),
        )
    )
    member_rows_result = await session.execute(
        select(BrandSpaceMember.brand_space_id).where(BrandSpaceMember.user_id == user.id)
    )
    brand_space_ids = set(role_rows_result.scalars().all())
    brand_space_ids.update(member_rows_result.scalars().all())
    return CurrentPrincipal(
        user_id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        role_codes=set(role_result.scalars().all()),
        brand_space_ids=brand_space_ids,
    )


def _review_access_denied() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You need to be mentioned on this review to access it.",
    )


def _review_user_summary(user: User, role_codes: set[str] | None = None) -> ReviewUserSummary:
    return ReviewUserSummary(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role_codes=sorted(role_codes or set()),
    )


def _review_participant_summary(
    user: User,
    role_codes: set[str] | None = None,
    *,
    access_role: str = "viewer",
    is_owner: bool = False,
) -> ReviewParticipantResponse:
    return ReviewParticipantResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role_codes=sorted(role_codes or set()),
        access_role=access_role,
        is_owner=is_owner,
    )


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


def _expected_carousel_slide_count(
    content: ContentVersion | None,
    assets: list[GeneratedAsset],
) -> int:
    payload = (
        content.generated_payload
        if content and isinstance(content.generated_payload, dict)
        else {}
    )
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    carousel_specs = (
        metadata.get("carousel_slide_specs")
        if isinstance(metadata.get("carousel_slide_specs"), list)
        else []
    )
    expected_count = len(carousel_specs)
    for asset in assets:
        asset_metadata = asset.metadata_json if isinstance(asset.metadata_json, dict) else {}
        try:
            expected_count = max(expected_count, int(asset_metadata.get("slide_count") or 0))
        except (TypeError, ValueError):
            continue
    return expected_count


def _asset_sequence_index(asset: GeneratedAsset, fallback_index: int) -> int:
    metadata = asset.metadata_json if isinstance(asset.metadata_json, dict) else {}
    for key in ("slide_index", "page_index", "order", "reference_slide_index"):
        try:
            value = int(metadata.get(key) or 0)
        except (TypeError, ValueError):
            value = 0
        if value > 0:
            return value
    match = re.search(
        r"(?:slide|page|p)[-_]?(\d+)",
        str(asset.storage_path or ""),
        re.IGNORECASE,
    )
    return int(match.group(1)) if match else fallback_index + 1


def _asset_reference_from_model(
    asset: GeneratedAsset,
    delivery: AssetDeliveryService,
) -> AssetReference:
    return AssetReference(
        asset_id=asset.id,
        mime_type=asset.mime_type,
        storage_path=asset.storage_path,
        asset_url=delivery.build_signed_url(
            storage_path=asset.storage_path,
            filename=asset.storage_path.rsplit("/", 1)[-1],
        ),
        width=asset.width,
        height=asset.height,
        asset_role=asset.asset_role,
    )


def _complete_carousel_display_assets(
    content: ContentVersion | None,
    assets: list[GeneratedAsset],
    delivery: AssetDeliveryService,
) -> list[AssetReference]:
    expected_count = _expected_carousel_slide_count(content, assets)
    if expected_count <= 1:
        return []

    image_assets = [
        asset
        for asset in assets
        if str(asset.mime_type or "").startswith("image/")
        and str(asset.asset_role or "") in {"render_preview", "render_export", "ai_image"}
    ]
    if len(image_assets) <= 1:
        return []

    ai_final_assets = [
        asset
        for asset in image_assets
        if (asset.metadata_json or {}).get("render_source") == "ai"
        and (asset.metadata_json or {}).get("generation_stage") == "final_render"
    ]
    candidates = ai_final_assets if len(ai_final_assets) >= expected_count else image_assets
    ordered = sorted(
        candidates,
        key=lambda item: (
            _asset_sequence_index(item, image_assets.index(item)),
            str(item.asset_role or ""),
            str(item.storage_path or ""),
        ),
    )
    deduped_by_slide: dict[int, GeneratedAsset] = {}
    for index, asset in enumerate(ordered):
        slide_index = _asset_sequence_index(asset, index)
        current = deduped_by_slide.get(slide_index)
        if current is None or current.asset_role != "render_preview":
            deduped_by_slide[slide_index] = asset
    selected = [deduped_by_slide[key] for key in sorted(deduped_by_slide)]
    if len(selected) <= 1:
        return []
    return [_asset_reference_from_model(asset, delivery) for asset in selected]


def _review_display_assets(
    content: ContentVersion | None,
    assets: list[GeneratedAsset],
    payload_display_assets: list[AssetReference],
    delivery: AssetDeliveryService,
) -> list[AssetReference]:
    carousel_assets = _complete_carousel_display_assets(content, assets, delivery)
    if carousel_assets and len(carousel_assets) > len(payload_display_assets):
        return carousel_assets
    return payload_display_assets


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
async def get_review(
    token: str,
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    # Serves the review detail lookup endpoint; it uses FastAPI dependencies, delegates work to services, and
    # returns the response schema.
    service = ReviewService(session)
    link, comments = await service.get_by_token(token)
    principal = await _optional_principal_from_authorization(authorization, session)
    if not await service.can_access_link(
        link,
        principal.user_id if principal else None,
        principal.role_codes if principal else None,
        principal.brand_space_ids if principal else None,
    ):
        raise _review_access_denied()
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
    payload_display_assets = _display_assets_from_payload(
        assistant_message.structured_payload if assistant_message else {},
        delivery,
    )
    display_assets = _review_display_assets(content, assets, payload_display_assets, delivery)
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
                created_at=item.created_at,
            )
            for item in comments
        ],
    )


@router.get("/{token}/share-access", response_model=ReviewShareAccessResponse)
async def get_review_share_access(
    token: str,
    principal: CurrentPrincipal = Depends(require_roles(RoleCode.TENANT_ADMIN)),
    session: AsyncSession = Depends(get_db_session),
) -> ReviewShareAccessResponse:
    service = ReviewService(session)
    link, _ = await service.get_by_token(token)
    assert_tenant_access(principal, link.tenant_id)
    assert_brand_access(principal, link.brand_space_id)
    owner, participants, mentionable_users, role_codes_by_user = await service.list_share_access(link)
    return ReviewShareAccessResponse(
        owner=_review_participant_summary(
            owner,
            role_codes_by_user.get(owner.id, set()),
            access_role="owner",
            is_owner=True,
        ) if owner else None,
        participants=[
            _review_participant_summary(
                user,
                role_codes_by_user.get(user.id, set()),
                access_role=participant.access_role,
            )
            for participant, user in participants
        ],
        mentionable_users=[
            _review_user_summary(user, role_codes_by_user.get(user.id, set()))
            for user in mentionable_users
        ],
    )


@router.post("/{token}/share-access", response_model=ReviewShareAccessResponse)
async def update_review_share_access(
    token: str,
    payload: ReviewShareAccessUpdateRequest,
    principal: CurrentPrincipal = Depends(require_roles(RoleCode.TENANT_ADMIN)),
    session: AsyncSession = Depends(get_db_session),
) -> ReviewShareAccessResponse:
    service = ReviewService(session)
    link, _ = await service.get_by_token(token)
    assert_tenant_access(principal, link.tenant_id)
    assert_brand_access(principal, link.brand_space_id)
    await service.grant_share_access(link.id, payload.user_ids, principal.user_id, payload.user_emails)
    await service.revoke_share_access(link.id, payload.remove_user_ids, principal.user_id)
    owner, participants, mentionable_users, role_codes_by_user = await service.list_share_access(link)
    return ReviewShareAccessResponse(
        owner=_review_participant_summary(
            owner,
            role_codes_by_user.get(owner.id, set()),
            access_role="owner",
            is_owner=True,
        ) if owner else None,
        participants=[
            _review_participant_summary(
                user,
                role_codes_by_user.get(user.id, set()),
                access_role=participant.access_role,
            )
            for participant, user in participants
        ],
        mentionable_users=[
            _review_user_summary(user, role_codes_by_user.get(user.id, set()))
            for user in mentionable_users
        ],
    )


@router.post("/{token}/comment", response_model=ReviewCommentResponse)
async def add_comment(
    token: str,
    payload: ReviewCommentCreateRequest,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    # Serves the add comment endpoint; it uses FastAPI dependencies, delegates work to services, and returns the
    # response schema.
    service = ReviewService(session)
    link, _ = await service.get_by_token(token)
    principal = await _optional_principal_from_authorization(authorization, session)
    if not await service.can_access_link(
        link,
        principal.user_id if principal else None,
        principal.role_codes if principal else None,
        principal.brand_space_ids if principal else None,
    ):
        raise _review_access_denied()
    comment = await service.add_comment(
        link.id,
        link.tenant_id,
        link.brand_space_id,
        payload.body,
        principal.user_id if principal else None,
        payload.external_author_name,
        payload.parent_comment_id,
        send_notifications=False,
    )
    background_tasks.add_task(_send_comment_notifications_background, link.id, comment.id)
    return ReviewCommentResponse(
        id=comment.id,
        body=comment.body,
        parent_comment_id=comment.parent_comment_id,
        external_author_name=comment.external_author_name,
        author_user_id=comment.author_user_id,
        created_at=comment.created_at,
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
    updated = await service.update_status(link.id, payload.status, principal.user_id)
    creator = await session.get(User, updated.created_by)
    return ReviewLinkResponse.model_validate(updated).model_copy(
        update={"created_by_name": creator.full_name if creator else None}
    )
