# FastAPI route handlers live here; they validate request inputs, call services, and return response schemas.
from uuid import UUID
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import CurrentPrincipal, assert_brand_access, forbid_super_admin_brand_access, get_current_principal
from app.db.session import get_db_session
from app.integrations.object_storage import LocalObjectStorage
from app.schemas.brand import (
    BrandCreateRequest,
    BrandFinalizeRequest,
    BrandOverviewResponse,
    BrandResponse,
    BrandSectionUpsertRequest,
    BrandSectionsUpsertRequest,
    BrandUpdateRequest,
    BrandUsageResponse,
)
from app.schemas.brand_assets import (
    AssetValidationResultResponse,
    DataConflictResponse,
    ResolvedBrandContextResponse,
    ValidationSummaryResponse,
)
from app.schemas.common import MessageResponse
from app.services.brand import BrandSpaceService
from app.services.data_validation import DataValidatorService
from app.services.vectorstore.ingestion_service import IngestionService
from app.workers.ingestion_worker import process_document_sync


router = APIRouter()


def trust_level_for_validation_state(validation_state: str | None) -> str:
    # Serves the trust level for validation state endpoint; it uses FastAPI dependencies, delegates work to
    # services, and returns the response schema.
    normalized = str(validation_state or "pending").lower()
    if normalized == "clean":
        return "trusted"
    if normalized == "warning":
        return "usable_with_warning"
    if normalized == "excluded":
        return "excluded"
    return "reference_only"


@router.post("", response_model=BrandResponse)
async def create_brand(
    payload: BrandCreateRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> BrandResponse:
    # Serves the brand creation endpoint; it uses FastAPI dependencies, delegates work to services, and returns
    # the response schema.
    forbid_super_admin_brand_access(principal)
    brand = await BrandSpaceService(session).create_brand(principal.tenant_id, principal.user_id, payload)
    return BrandResponse.model_validate(brand)


@router.get("", response_model=list[BrandResponse])
async def list_brands(
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> list[BrandResponse]:
    # Serves the brands listing endpoint; it uses FastAPI dependencies, delegates work to services, and returns
    # the response schema.
    forbid_super_admin_brand_access(principal)
    brands = await BrandSpaceService(session).list_brands(principal.tenant_id, principal.user_id, principal.role_codes)
    return [BrandResponse.model_validate(item) for item in brands]


@router.get("/{brand_id}", response_model=BrandResponse)
async def get_brand(
    brand_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> BrandResponse:
    # Serves the brand detail lookup endpoint; it checks brand scope, delegates work to services, and returns
    # the response schema.
    forbid_super_admin_brand_access(principal)
    assert_brand_access(principal, brand_id)
    brand = await BrandSpaceService(session).brands.get_scoped(principal.tenant_id, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand Space not found")
    return BrandResponse.model_validate(brand)


@router.get("/{brand_id}/usage", response_model=BrandUsageResponse)
async def get_brand_usage(
    brand_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> BrandUsageResponse:
    # Serves the brand usage detail lookup endpoint; it checks brand scope, delegates work to services, and
    # returns the response schema.
    forbid_super_admin_brand_access(principal)
    assert_brand_access(principal, brand_id)
    if not principal.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    payload = await BrandSpaceService(session).get_usage_summary(principal.tenant_id, brand_id)
    return BrandUsageResponse.model_validate(payload)


@router.put("/{brand_id}", response_model=BrandResponse)
async def update_brand(
    brand_id: UUID,
    payload: BrandUpdateRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> BrandResponse:
    # Serves the brand update endpoint; it checks brand scope, delegates work to services, and returns the
    # response schema.
    forbid_super_admin_brand_access(principal)
    assert_brand_access(principal, brand_id)
    brand = await BrandSpaceService(session).update_brand(principal.tenant_id, brand_id, payload)
    return BrandResponse.model_validate(brand)


@router.put("/{brand_id}/sections/{section_code}", response_model=BrandResponse)
async def upsert_section(
    brand_id: UUID,
    section_code: str,
    payload: BrandSectionUpsertRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> BrandResponse:
    # Serves the upsert section endpoint; it checks brand scope, delegates work to services, and returns the
    # response schema.
    forbid_super_admin_brand_access(principal)
    assert_brand_access(principal, brand_id)
    try:
        request = BrandSectionUpsertRequest(
            section_code=section_code,
            payload=payload.payload,
            completion_percent=payload.completion_percent,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    brand = await BrandSpaceService(session).upsert_section(principal.tenant_id, brand_id, request)
    return BrandResponse.model_validate(brand)


@router.put("/{brand_id}/sections", response_model=BrandResponse)
async def upsert_sections(
    brand_id: UUID,
    payload: BrandSectionsUpsertRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> BrandResponse:
    # Serves the upsert sections endpoint; it checks brand scope, delegates work to services, and returns the
    # response schema.
    forbid_super_admin_brand_access(principal)
    assert_brand_access(principal, brand_id)
    brand = await BrandSpaceService(session).upsert_sections(principal.tenant_id, brand_id, payload)
    return BrandResponse.model_validate(brand)


@router.post("/{brand_id}/finalize", response_model=BrandResponse)
async def finalize_brand(
    brand_id: UUID,
    payload: BrandFinalizeRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> BrandResponse:
    # Serves the brand finalization endpoint; it checks brand scope, delegates work to services, and returns the
    # response schema.
    forbid_super_admin_brand_access(principal)
    assert_brand_access(principal, brand_id)
    brand = await BrandSpaceService(session).finalize_brand(principal.tenant_id, brand_id)
    return BrandResponse.model_validate(brand)


@router.post("/{brand_id}/publish", response_model=BrandResponse)
async def publish_brand(
    brand_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> BrandResponse:
    # Serves the brand publish endpoint; it checks brand scope, delegates work to services, and returns the
    # response schema.
    forbid_super_admin_brand_access(principal)
    assert_brand_access(principal, brand_id)
    brand = await BrandSpaceService(session).publish_brand(principal.tenant_id, brand_id)
    return BrandResponse.model_validate(brand)


@router.post("/{brand_id}/unpublish", response_model=BrandResponse)
async def unpublish_brand(
    brand_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> BrandResponse:
    # Serves the brand unpublish endpoint; it checks brand scope, delegates work to services, and returns the
    # response schema.
    forbid_super_admin_brand_access(principal)
    assert_brand_access(principal, brand_id)
    brand = await BrandSpaceService(session).unpublish_brand(principal.tenant_id, brand_id)
    return BrandResponse.model_validate(brand)


@router.post("/{brand_id}/archive", response_model=BrandResponse)
async def archive_brand(
    brand_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> BrandResponse:
    # Serves the brand archive endpoint; it checks brand scope, delegates work to services, and returns the
    # response schema.
    forbid_super_admin_brand_access(principal)
    assert_brand_access(principal, brand_id)
    brand = await BrandSpaceService(session).archive_brand(principal.tenant_id, brand_id)
    return BrandResponse.model_validate(brand)


@router.post("/{brand_id}/restore", response_model=BrandResponse)
async def restore_brand(
    brand_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> BrandResponse:
    # Serves the brand restore endpoint; it checks brand scope, delegates work to services, and returns the
    # response schema.
    forbid_super_admin_brand_access(principal)
    assert_brand_access(principal, brand_id)
    brand = await BrandSpaceService(session).restore_brand(principal.tenant_id, brand_id)
    return BrandResponse.model_validate(brand)


@router.delete("/{brand_id}", response_model=MessageResponse)
async def delete_brand(
    brand_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    # Serves the brand deletion endpoint; it checks brand scope, delegates work to services, and returns the
    # response schema.
    forbid_super_admin_brand_access(principal)
    assert_brand_access(principal, brand_id)
    await BrandSpaceService(session).delete_brand(principal.tenant_id, brand_id)
    return MessageResponse(message="Brand deleted")


@router.get("/{brand_id}/overview", response_model=BrandOverviewResponse)
async def brand_overview(
    brand_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> BrandOverviewResponse:
    # Serves the brand overview endpoint; it checks brand scope, delegates work to services, and returns the
    # response schema.
    forbid_super_admin_brand_access(principal)
    assert_brand_access(principal, brand_id)
    service = BrandSpaceService(session)
    brand = await service.brands.get_scoped(principal.tenant_id, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand Space not found")
    sections = await service.sections.list_current_sections(brand_id, principal.tenant_id)
    personas = await service.personas.list_by_brand(brand_id, principal.tenant_id)
    guardrails = await service.guardrails.list_by_brand(brand_id, principal.tenant_id)
    objectives = await service.objectives.list_by_brand(brand_id, principal.tenant_id)
    return BrandOverviewResponse(
        brand=BrandResponse.model_validate(brand),
        sections=[{"section_code": item.section_code, "payload": item.payload, "version": item.version} for item in sections],
        personas=[service.intelligence.persona_to_dict(item) for item in personas],
        guardrails=[service.intelligence.guardrail_to_dict(item) for item in guardrails],
        objectives=[service.intelligence.objective_to_dict(item) for item in objectives],
    )


@router.get("/{brand_id}/validation", response_model=ValidationSummaryResponse)
async def brand_validation_summary(
    brand_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> ValidationSummaryResponse:
    # Serves the brand validation summary endpoint; it checks brand scope, delegates work to services, and
    # returns the response schema.
    forbid_super_admin_brand_access(principal)
    assert_brand_access(principal, brand_id)
    validator = DataValidatorService(session)
    payload = await validator.get_validation_summary(principal.tenant_id, brand_id)
    snapshot = payload["snapshot"]
    return ValidationSummaryResponse(
        brand_space_id=brand_id,
        warnings=payload["warnings"],
        conflicts=[DataConflictResponse.model_validate(item) for item in payload["conflicts"]],
        excluded_assets=payload["excluded_assets"],
        validation_results=[
            AssetValidationResultResponse.model_validate(item).model_copy(
                update={"trust_level": trust_level_for_validation_state(item.validation_state)}
            )
            for item in payload["validation_results"]
        ],
        latest_snapshot=ResolvedBrandContextResponse(
            brand_space_id=brand_id,
            snapshot_id=snapshot.id if snapshot else None,
            snapshot_kind=snapshot.snapshot_kind if snapshot else "validated",
            status=snapshot.status if snapshot else "active",
            warnings=snapshot.warnings if snapshot else [],
            excluded_asset_ids=snapshot.excluded_asset_ids if snapshot else [],
            context_json=snapshot.context_json if snapshot else {},
        )
        if snapshot
        else None,
    )


@router.get("/{brand_id}/resolved-context", response_model=ResolvedBrandContextResponse)
async def brand_resolved_context(
    brand_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> ResolvedBrandContextResponse:
    # Serves the brand resolved context endpoint; it checks brand scope, delegates work to services, and returns
    # the response schema.
    forbid_super_admin_brand_access(principal)
    assert_brand_access(principal, brand_id)
    validator = DataValidatorService(session)
    snapshot = await validator.get_latest_snapshot(principal.tenant_id, brand_id)
    if snapshot:
        return ResolvedBrandContextResponse(
            brand_space_id=brand_id,
            snapshot_id=snapshot.id,
            snapshot_kind=snapshot.snapshot_kind,
            status=snapshot.status,
            warnings=snapshot.warnings,
            excluded_asset_ids=snapshot.excluded_asset_ids,
            context_json=snapshot.context_json,
        )
    brand = await BrandSpaceService(session).brands.get_scoped(principal.tenant_id, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand Space not found")
    return ResolvedBrandContextResponse(
        brand_space_id=brand_id,
        context_json=brand.resolved_brand_context,
    )


@router.post("/{brand_id}/documents", response_model=MessageResponse)
async def upload_brand_document(
    brand_id: UUID,
    file: UploadFile,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Upload and ingest a brand guideline document (DOCX, PDF, TXT)."""
    forbid_super_admin_brand_access(principal)
    assert_brand_access(principal, brand_id)

    settings = get_settings()
    allowed_extensions = {".docx", ".pdf", ".txt"}
    file_extension = Path(file.filename).suffix.lower()

    # Validate file extension
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )

    # Validate file size
    file_content = await file.read()
    if len(file_content) > settings.upload_max_file_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.upload_max_file_bytes / (1024 * 1024)}MB"
        )

    # Store file using LocalObjectStorage
    storage = LocalObjectStorage()
    stored = storage.save_bytes(
        tenant_id=principal.tenant_id,
        brand_space_id=brand_id,
        category="brand_documents",
        filename=file.filename,
        content=file_content
    )

    # Process document (synchronous fallback for now)
    try:
        result = process_document_sync(str(brand_id), stored.absolute_path)
        return MessageResponse(
            message=f"Document queued for ingestion. Processed {result['total_chunks']} chunks."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document ingestion failed: {str(e)}")


@router.get("/{brand_id}/documents/search")
async def search_brand_documents(
    brand_id: UUID,
    q: str,
    top_k: int = 10,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
):
    """Search ingested brand guideline documents."""
    forbid_super_admin_brand_access(principal)
    assert_brand_access(principal, brand_id)

    ingestion_service = IngestionService()

    try:
        results = ingestion_service.search_pinecone(str(brand_id), q, top_k)
        return {
            "query": q,
            "brand_id": str(brand_id),
            "results": results,
            "total": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
