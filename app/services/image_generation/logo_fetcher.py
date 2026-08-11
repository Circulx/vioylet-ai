from __future__ import annotations

"""Logo fetcher utility for the AI image generation pipeline.

Looks up the brand logo storage path from the database (via BrandSpace context,
KnowledgeAsset records, or BrandLogoAsset mappings) so it can be composited
onto DALL-E generated images after generation.
"""

from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.brand import BrandConfigurationSection, BrandSpace
from app.models.brand_assets import BrandLogoAsset
from app.models.knowledge import KnowledgeAsset

logger = get_logger(__name__)


def _path_from_asset_record(asset: object) -> str | None:
    if not isinstance(asset, dict):
        return None
    for key in ("storage_path", "storagePath", "path"):
        value = asset.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


async def _path_from_current_section(
    session: AsyncSession,
    brand_uuid: UUID,
    section_code: str,
) -> str | None:
    stmt = (
        select(BrandConfigurationSection.payload)
        .where(
            BrandConfigurationSection.brand_space_id == brand_uuid,
            BrandConfigurationSection.section_code == section_code,
            BrandConfigurationSection.is_current.is_(True),
        )
        .order_by(BrandConfigurationSection.version.desc())
        .limit(1)
    )
    payload = (await session.execute(stmt)).scalar_one_or_none()
    if not isinstance(payload, dict):
        return None

    if section_code == "identity":
        direct = _path_from_asset_record({"storage_path": payload.get("logo_asset_path")})
        if direct:
            return direct
        logo_id = payload.get("logo_asset_id")
        if logo_id:
            try:
                asset_uuid = UUID(str(logo_id))
                stmt_asset = select(KnowledgeAsset.storage_path).where(KnowledgeAsset.id == asset_uuid)
                resolved = (await session.execute(stmt_asset)).scalar_one_or_none()
                if resolved:
                    return str(resolved).strip()
            except Exception:
                pass
        for asset in payload.get("logo_assets") or []:
            path = _path_from_asset_record(asset)
            if path:
                return path

    if section_code == "visual_identity":
        for asset in payload.get("logo_assets") or []:
            path = _path_from_asset_record(asset)
            if path:
                return path

    return None


async def get_brand_logo_storage_path(
    brand_space_id: str | UUID,
    session: AsyncSession,
) -> str | None:
    """Return the storage_path of the primary brand logo for a given brand space.

    Highly robust lookup strategy:
    1. Loads BrandSpace and checks resolved_brand_context['identity']['logo_asset_path']
    2. Checks BrandSpace resolved_brand_context['identity']['logo_selection']['storage_path']
    3. Checks BrandSpace overview_snapshot['logo']['storage_path']
    4. Queries KnowledgeAsset directly for logo category/field (ignoring deleted/active constraints)
    5. Fallback to BrandLogoAsset join query
    6. Verifies filesystem existence of the target path. If missing, scans the brand
       folder recursively for fallback logo assets (e.g., matching 'logo' or 'brand').
    """
    settings = get_settings()
    base_storage_path = Path(settings.object_storage_base_path).resolve()
    brand_uuid = UUID(str(brand_space_id))

    storage_path: str | None = None

    try:
        # ── 1. Check BrandSpace Context & Snapshot ────────────────────────────
        brand = await session.get(BrandSpace, brand_uuid)
        if brand:
            context = brand.resolved_brand_context or {}
            snapshot = brand.overview_snapshot or {}
            
            # 1a. Try resolved_brand_context identity section for explicit asset IDs
            identity = context.get("identity") or {}
            if isinstance(identity, dict):
                # Check for explicit logo_asset_id or logo_asset_ids
                logo_id = identity.get("logo_asset_id")
                if not logo_id and identity.get("logo_asset_ids"):
                    logo_id = identity["logo_asset_ids"][0]
                
                if logo_id:
                    try:
                        asset_uuid = UUID(str(logo_id))
                        stmt = select(KnowledgeAsset.storage_path).where(KnowledgeAsset.id == asset_uuid)
                        res = await session.execute(stmt)
                        storage_path = res.scalar_one_or_none()
                        if storage_path:
                            logger.info("logo_fetcher.found_by_explicit_id", brand_id=str(brand_uuid), asset_id=str(asset_uuid))
                    except Exception as e:
                        logger.warning(f"logo_fetcher.explicit_id_lookup_failed: {e}")

                # Fallback to previously existing path-based identity lookups
                if not storage_path:
                    storage_path = identity.get("logo_asset_path") or (identity.get("logo_selection") or {}).get("storage_path")
            
            # 1b. Try overview_snapshot path
            if not storage_path and isinstance(snapshot, dict):
                storage_path = (snapshot.get("logo") or {}).get("storage_path")
                if not storage_path:
                    identity_snapshot = snapshot.get("identity") or {}
                    if isinstance(identity_snapshot, dict):
                        storage_path = _path_from_asset_record(
                            {"storage_path": identity_snapshot.get("logo_asset_path")}
                        )
                        if not storage_path:
                            for asset in identity_snapshot.get("logo_assets") or []:
                                storage_path = _path_from_asset_record(asset)
                                if storage_path:
                                    break
                if not storage_path:
                    visual_snapshot = snapshot.get("visual_identity") or {}
                    if isinstance(visual_snapshot, dict):
                        for asset in visual_snapshot.get("logo_assets") or []:
                            storage_path = _path_from_asset_record(asset)
                            if storage_path:
                                break

        # ── 1c. Current identity / visual_identity section payloads ───────────
        if not storage_path:
            for section_code in ("identity", "visual_identity"):
                storage_path = await _path_from_current_section(session, brand_uuid, section_code)
                if storage_path:
                    logger.info(
                        "logo_fetcher.found_in_section_payload",
                        brand_id=str(brand_uuid),
                        section_code=section_code,
                        storage_path=storage_path,
                    )
                    break

        # ── 2. Check KnowledgeAsset table directly ────────────────────────────
        if not storage_path:
            stmt = (
                select(KnowledgeAsset.storage_path)
                .where(KnowledgeAsset.brand_space_id == brand_uuid)
                .where(
                    (KnowledgeAsset.asset_category == "logo")
                    | (KnowledgeAsset.field_key == "logo")
                    | (KnowledgeAsset.field_key.ilike("%logo%"))
                    | (KnowledgeAsset.name.ilike("%logo%"))
                )
                .order_by(KnowledgeAsset.created_at.desc())
                .limit(1)
            )
            res = await session.execute(stmt)
            storage_path = res.scalar_one_or_none()

        # ── 3. Fallback to BrandLogoAsset standard query ───────────────────────
        if not storage_path:
            stmt_standard = (
                select(KnowledgeAsset.storage_path)
                .join(BrandLogoAsset, BrandLogoAsset.knowledge_asset_id == KnowledgeAsset.id)
                .where(BrandLogoAsset.brand_space_id == brand_uuid)
                .where(KnowledgeAsset.is_active.is_(True))
                .order_by(KnowledgeAsset.created_at.desc())
                .limit(1)
            )
            res_std = await session.execute(stmt_standard)
            storage_path = res_std.scalar_one_or_none()

        if storage_path:
            storage_path = str(storage_path).strip()

        # ── 4. Verify Existence — prefer S3 check, fall back to local disk ────
        if storage_path:
            # First try: verify via object storage (S3 / MinIO / local-S3)
            s3_verified = False
            try:
                from app.integrations.object_storage import get_object_storage
                _storage = get_object_storage()
                if hasattr(_storage, "read_bytes"):
                    _bytes = _storage.read_bytes(storage_path)
                    if _bytes:
                        s3_verified = True
                        logger.info(
                            "logo_fetcher.verified_in_object_storage",
                            brand_space_id=str(brand_uuid),
                            storage_path=storage_path,
                            size=len(_bytes),
                        )
            except Exception as _s3_err:
                logger.debug("logo_fetcher.s3_verify_failed", error=str(_s3_err)[:120])

            if s3_verified:
                return storage_path

            # Second try: local disk
            full_path = (base_storage_path / storage_path).resolve()
            if full_path.exists():
                logger.info(
                    "logo_fetcher.verified_on_disk",
                    brand_space_id=str(brand_uuid),
                    storage_path=storage_path,
                )
                return storage_path
            else:
                logger.warning(
                    "logo_fetcher.path_missing_on_disk",
                    brand_space_id=str(brand_uuid),
                    attempted_path=storage_path,
                )

        # ── 5. Local filesystem fallback scan (skip if S3 storage) ────────────
        # Only scan local folder if we're on local filesystem storage (S3 will not have local files)
        _is_local_storage = True
        try:
            from app.integrations.object_storage import get_object_storage as _gos
            _s = _gos()
            _is_local_storage = type(_s).__name__ in ("LocalObjectStorage", "LocalFileStorage")
        except Exception:
            pass

        if _is_local_storage:
            tenant_id_str = str(getattr(brand, "tenant_id", "00000000-0000-0000-0000-000000000001"))
            brand_folder = base_storage_path / tenant_id_str / str(brand_uuid)
            
            if brand_folder.exists():
                image_extensions = {".png", ".jpg", ".jpeg", ".webp"}
                logo_candidates: list[Path] = []

                for p in brand_folder.rglob("*"):
                    if p.is_file() and p.suffix.lower() in image_extensions:
                        if "generated" in p.parts or "_ocr" in str(p):
                            continue
                        lowered_name = p.name.lower()
                        if any(k in lowered_name for k in ["logo", "brand", "icon"]):
                            logo_candidates.append(p)

                logo_candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                if logo_candidates:
                    selected_file = logo_candidates[0]
                    resolved_rel_path = str(selected_file.relative_to(base_storage_path)).replace("\\", "/")
                    logger.info(
                        "logo_fetcher.scanned_local_fallback_found",
                        brand_space_id=str(brand_uuid),
                        storage_path=resolved_rel_path,
                        filename=selected_file.name,
                    )
                    return resolved_rel_path

        logger.info(
            "logo_fetcher.failed_all_lookups",
            brand_space_id=str(brand_uuid),
        )
        return None

    except Exception as exc:
        logger.warning(
            "logo_fetcher.error",
            brand_space_id=str(brand_space_id),
            error=str(exc)[:300],
        )
        return None
