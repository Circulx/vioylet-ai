# FastAPI route handlers live here; they validate request inputs, call services, and return response schemas.
from uuid import UUID
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel, ValidationError
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import (
    CurrentPrincipal,
    assert_brand_access,
    assert_brand_manage_access,
    forbid_super_admin_brand_access,
    get_current_principal,
)
from app.db.session import get_db_session
from app.integrations.object_storage import LocalObjectStorage
from app.models.brand import BrandSpace
from app.models.retrieval_log import RetrievalLog
from app.schemas.brand import (
    BrandAutofillResponse,
    BrandCreateRequest,
    BrandFinalizeRequest,
    BrandOverviewResponse,
    BrandResponse,
    BrandSpaceHistoryResponse,
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
from app.services.asset_delivery import AssetDeliveryService
from app.services.brand import BrandSpaceService
from app.services.brand_autofill import BrandAutofillService
from app.services.data_validation import DataValidatorService
from app.services.vectorstore.ingestion_service import IngestionService
from app.services.vectorstore.retrieval_service import BrandRetrievalService
from app.workers.ingestion_worker import process_document_sync


router = APIRouter()


def _brand_response(brand) -> BrandResponse:
    response = BrandResponse.model_validate(brand)
    context = dict(response.resolved_brand_context or {})
    identity = dict(context.get("identity") or {})
    delivery = AssetDeliveryService()

    def signed_url(storage_path: object) -> str | None:
        if not isinstance(storage_path, str) or not storage_path.strip():
            return None
        return delivery.build_signed_url(
            storage_path=storage_path,
            filename=storage_path.rsplit("/", 1)[-1],
        )

    logo_assets = identity.get("logo_assets")
    if isinstance(logo_assets, list):
        enriched_assets = []
        for asset in logo_assets:
            if not isinstance(asset, dict):
                enriched_assets.append(asset)
                continue
            enriched_asset = dict(asset)
            asset_url = enriched_asset.get("asset_url") or enriched_asset.get("url")
            if not asset_url:
                asset_url = signed_url(enriched_asset.get("storage_path"))
            if asset_url:
                enriched_asset["asset_url"] = asset_url
                enriched_asset["url"] = asset_url
            enriched_assets.append(enriched_asset)
        identity["logo_assets"] = enriched_assets

    logo_asset_url = identity.get("logo_asset_url")
    if not logo_asset_url:
        logo_asset_url = signed_url(identity.get("logo_asset_path"))
    if not logo_asset_url and isinstance(identity.get("logo_assets"), list):
        logo_asset_url = next(
            (
                asset.get("asset_url") or asset.get("url")
                for asset in identity["logo_assets"]
                if isinstance(asset, dict) and (asset.get("asset_url") or asset.get("url"))
            ),
            None,
        )
    if logo_asset_url:
        identity["logo_asset_url"] = logo_asset_url

    context["identity"] = identity
    return response.model_copy(update={"resolved_brand_context": context})


def _brand_responses(brands) -> list[BrandResponse]:
    return [_brand_response(item) for item in brands]


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
    assert_brand_manage_access(principal)
    brand = await BrandSpaceService(session).create_brand(
        principal.tenant_id,
        principal.user_id,
        payload,
        principal.role_codes,
    )
    return _brand_response(brand)


@router.get("", response_model=list[BrandResponse])
async def list_brands(
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> list[BrandResponse]:
    # Serves the brands listing endpoint; it uses FastAPI dependencies, delegates work to services, and returns
    # the response schema.
    forbid_super_admin_brand_access(principal)
    brands = await BrandSpaceService(session).list_brands(principal.tenant_id, principal.user_id, principal.role_codes)
    return _brand_responses(brands)


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
    return _brand_response(brand)


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


@router.get("/{brand_id}/history", response_model=list[BrandSpaceHistoryResponse])
async def brand_history(
    brand_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> list[BrandSpaceHistoryResponse]:
    # Serves Brand Space activity history for users who can access the current Brand Space.
    forbid_super_admin_brand_access(principal)
    assert_brand_access(principal, brand_id)
    if not principal.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    history_entries = await BrandSpaceService(session).list_history(principal.tenant_id, brand_id)
    return [BrandSpaceHistoryResponse.model_validate(item) for item in history_entries]


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
    assert_brand_manage_access(principal)
    brand = await BrandSpaceService(session).update_brand(principal.tenant_id, brand_id, payload)
    return _brand_response(brand)


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
    assert_brand_manage_access(principal)
    try:
        request = BrandSectionUpsertRequest(
            section_code=section_code,
            payload=payload.payload,
            completion_percent=payload.completion_percent,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    brand = await BrandSpaceService(session).upsert_section(principal.tenant_id, brand_id, request)
    return _brand_response(brand)


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
    assert_brand_manage_access(principal)
    brand = await BrandSpaceService(session).upsert_sections(
        principal.tenant_id,
        brand_id,
        payload,
        principal.user_id,
        principal.role_codes,
    )
    return _brand_response(brand)


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
    assert_brand_manage_access(principal)
    brand = await BrandSpaceService(session).finalize_brand(
        principal.tenant_id,
        brand_id,
        principal.user_id,
        principal.role_codes,
    )
    return _brand_response(brand)


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
    assert_brand_manage_access(principal)
    brand = await BrandSpaceService(session).publish_brand(
        principal.tenant_id,
        brand_id,
        principal.user_id,
        principal.role_codes,
    )
    return _brand_response(brand)


@router.post("/{brand_id}/autofill-from-knowledge", response_model=BrandAutofillResponse)
async def autofill_brand_from_knowledge(
    brand_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> BrandAutofillResponse:
    """Suggest Brand Space tab values by reading indexed vector-DB knowledge."""
    forbid_super_admin_brand_access(principal)
    assert_brand_access(principal, brand_id)
    brand = await BrandSpaceService(session).brands.get_scoped(principal.tenant_id, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand Space not found")
    try:
        suggestion = await BrandAutofillService().suggest(
            brand_id=brand_id,
            brand_name=brand.name or "",
            brand_description=brand.description or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Autofill failed: {exc}") from exc
    return BrandAutofillResponse.model_validate(suggestion.model_dump())


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
    assert_brand_manage_access(principal)
    brand = await BrandSpaceService(session).unpublish_brand(principal.tenant_id, brand_id)
    return _brand_response(brand)


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
    assert_brand_manage_access(principal)
    brand = await BrandSpaceService(session).archive_brand(
        principal.tenant_id,
        brand_id,
        principal.user_id,
        principal.role_codes,
    )
    return _brand_response(brand)


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
    assert_brand_manage_access(principal)
    brand = await BrandSpaceService(session).restore_brand(
        principal.tenant_id,
        brand_id,
        principal.user_id,
        principal.role_codes,
    )
    return _brand_response(brand)


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
    assert_brand_manage_access(principal)
    await BrandSpaceService(session).delete_brand(
        principal.tenant_id,
        brand_id,
        principal.user_id,
        principal.role_codes,
    )
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
        brand=_brand_response(brand),
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


class RetrievalPreviewRequest(BaseModel):
    user_prompt: str
    platform: str = ""
    format: str = ""
    categories: list[str] | None = None


@router.post("/{brand_id}/retrieval-preview")
async def brand_retrieval_preview(
    brand_id: UUID,
    payload: RetrievalPreviewRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
):
    """Layer 1 preview: run namespace-isolated retrieval + multi-signal reranking.

    Returns the validated BrandContextOutput plus the full retrieval log and the
    per-chunk signal breakdown so the pipeline's first layer can be verified.
    """
    forbid_super_admin_brand_access(principal)
    assert_brand_access(principal, brand_id)

    service = BrandRetrievalService()
    try:
        result = service.retrieve(
            brand_id=str(brand_id),
            user_prompt=payload.user_prompt,
            platform=payload.platform,
            format=payload.format,
            categories=payload.categories,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")

    brand = await session.get(BrandSpace, brand_id)
    log = RetrievalLog(
        tenant_id=brand.tenant_id if brand else principal.tenant_id,
        brand_space_id=brand_id,
        query=result["retrieval_log"]["query"],
        namespace=result["retrieval_log"]["namespace"],
        isolation_status=result["output"].brand_isolation_status,
        confidence=result["output"].retrieval_confidence,
        total_chunks=result["retrieval_log"]["total_chunks"],
        chunks=result["retrieval_log"]["chunks"],
        metadata_json={
            "user_prompt": payload.user_prompt,
            "platform": payload.platform,
            "format": payload.format,
        },
    )
    session.add(log)
    await session.commit()

    return {
        "brand_context": result["output"].model_dump(),
        "retrieval_log": result["retrieval_log"],
        "ranked_chunks": result["ranked_chunks"],
    }


@router.get("/{brand_id}/retrieval-logs")
async def get_brand_retrieval_logs(
    brand_id: UUID,
    limit: int = 50,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
):
    """Query persisted retrieval logs for a brand (Layer 1 audit trail)."""
    forbid_super_admin_brand_access(principal)
    assert_brand_access(principal, brand_id)

    stmt = (
        select(RetrievalLog)
        .where(RetrievalLog.brand_space_id == brand_id)
        .order_by(desc(RetrievalLog.created_at))
        .limit(limit)
    )
    result = await session.execute(stmt)
    logs = result.scalars().all()
    return {
        "brand_id": str(brand_id),
        "total": len(logs),
        "logs": [
            {
                "id": str(log.id),
                "query": log.query,
                "namespace": log.namespace,
                "isolation_status": log.isolation_status,
                "confidence": log.confidence,
                "total_chunks": log.total_chunks,
                "chunks": log.chunks,
                "metadata_json": log.metadata_json,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }
