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
from app.models.brand import BrandSpace
from app.models.brand_assets import BrandLogoAsset
from app.models.knowledge import KnowledgeAsset

logger = get_logger(__name__)


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

        # ── 2. Check KnowledgeAsset table directly ────────────────────────────
        if not storage_path:
            stmt = (
                select(KnowledgeAsset.storage_path)
                .where(KnowledgeAsset.brand_space_id == brand_uuid)
                .where(
                    (KnowledgeAsset.asset_category == "logo") | 
                    (KnowledgeAsset.field_key == "logo") |
                    (KnowledgeAsset.name.ilike("%logo%"))
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

        # ── 4. Verify Filesystem Existence and Find Local Fallback ────────────
        if storage_path:
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

        # If we got here, either no path was found, or the database path is missing on disk.
        # Let's scan the brand space storage folder recursively for any logo/brand files.
        # Find tenant folder from brand space or default to 00000000-0000-0000-0000-000000000001
        tenant_id_str = str(getattr(brand, "tenant_id", "00000000-0000-0000-0000-000000000001"))
        brand_folder = base_storage_path / tenant_id_str / str(brand_uuid)
        
        if brand_folder.exists():
            image_extensions = {".png", ".jpg", ".jpeg", ".webp"}
            logo_candidates: list[Path] = []
            fallback_candidates: list[Path] = []

            for p in brand_folder.rglob("*"):
                if p.is_file() and p.suffix.lower() in image_extensions:
                    # Exclude generated folder
                    if "generated" in p.parts:
                        continue
                    lowered_name = p.name.lower()
                    # Check for keywords - added 'images' and 'jiraaf' per user request
                    if any(k in lowered_name for k in ["logo", "brand", "icon", "images", "jiraaf"]):
                        logo_candidates.append(p)
                    else:
                        fallback_candidates.append(p)

            # Prioritize candidates: files matching keywords, then most recently modified others
            logo_candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            fallback_candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            ordered_files = logo_candidates + fallback_candidates
            if ordered_files:
                selected_file = ordered_files[0]
                resolved_rel_path = str(selected_file.relative_to(base_storage_path)).replace("\\", "/")
                logger.info(
                    "logo_fetcher.scanned_fallback_found",
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
