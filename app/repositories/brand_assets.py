# Repository classes isolate SQLAlchemy queries so service code works with intent-level operations.
from __future__ import annotations

from typing import TypeVar
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brand_assets import (
    AssetCategoryRouting,
    AssetProcessingStatus,
    AssetValidationResult,
    AudienceInsightAsset,
    AudienceInsightStructuredData,
    BrandCTATemplate,
    BrandLegalAsset,
    BrandLogoAsset,
    BrandLogoMetadata,
    ColorPaletteEntry,
    DataConflict,
    MoodBoardAsset,
    NegativeWord,
    PositiveWord,
    ReplaceableWord,
    ReusableBrandAsset,
    ResolvedBrandContextSnapshot,
    TypographyGuide,
    VisualReferenceAsset,
    WordBankUpload,
)
from app.repositories.base import Repository


ModelT = TypeVar("ModelT")


class ScopedRepository(Repository[ModelT]):
    # Data-access helper for scoped; services call this class instead of repeating SQLAlchemy filters inline.
    async def get_for_brand(self, entity_id: UUID, tenant_id: UUID, brand_space_id: UUID) -> ModelT | None:
        # Fetches the requested for brand record or None, leaving not-found handling to the calling service.
        result = await self.session.execute(
            select(self.model).where(
                self.model.id == entity_id,
                self.model.tenant_id == tenant_id,
                self.model.brand_space_id == brand_space_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_brand(self, tenant_id: UUID, brand_space_id: UUID) -> list[ModelT]:
        # Returns matching for brand records with repository scope applied; services assemble responses from
        # these rows.
        result = await self.session.execute(
            select(self.model).where(
                self.model.tenant_id == tenant_id,
                self.model.brand_space_id == brand_space_id,
            )
        )
        return list(result.scalars().all())


class BrandLogoAssetRepository(ScopedRepository[BrandLogoAsset]):
    # Data-access helper for brand logo asset; services call this class instead of repeating SQLAlchemy filters
    # inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds BrandLogoAssetRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, BrandLogoAsset)

    async def get_by_knowledge_asset(self, knowledge_asset_id: UUID) -> BrandLogoAsset | None:
        # Fetches the requested by knowledge asset record or None, leaving not-found handling to the calling
        # service.
        result = await self.session.execute(
            select(BrandLogoAsset).where(BrandLogoAsset.knowledge_asset_id == knowledge_asset_id)
        )
        return result.scalar_one_or_none()


class BrandLogoMetadataRepository(ScopedRepository[BrandLogoMetadata]):
    # Data-access helper for brand logo metadata; services call this class instead of repeating SQLAlchemy
    # filters inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds BrandLogoMetadataRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, BrandLogoMetadata)

    async def get_by_logo_asset(self, brand_logo_asset_id: UUID) -> BrandLogoMetadata | None:
        # Fetches the requested by logo asset record or None, leaving not-found handling to the calling service.
        result = await self.session.execute(
            select(BrandLogoMetadata).where(BrandLogoMetadata.brand_logo_asset_id == brand_logo_asset_id)
        )
        return result.scalar_one_or_none()


class AudienceInsightAssetRepository(ScopedRepository[AudienceInsightAsset]):
    # Data-access helper for audience insight asset; services call this class instead of repeating SQLAlchemy
    # filters inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds AudienceInsightAssetRepository to the current async session, giving every query method the same
        # DB transaction context.
        super().__init__(session, AudienceInsightAsset)

    async def get_by_knowledge_asset(self, knowledge_asset_id: UUID) -> AudienceInsightAsset | None:
        # Fetches the requested by knowledge asset record or None, leaving not-found handling to the calling
        # service.
        result = await self.session.execute(
            select(AudienceInsightAsset).where(AudienceInsightAsset.knowledge_asset_id == knowledge_asset_id)
        )
        return result.scalar_one_or_none()


class AudienceInsightStructuredDataRepository(ScopedRepository[AudienceInsightStructuredData]):
    # Data-access helper for audience insight structured data; services call this class instead of repeating
    # SQLAlchemy filters inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds AudienceInsightStructuredDataRepository to the current async session, giving every query method
        # the same DB transaction context.
        super().__init__(session, AudienceInsightStructuredData)

    async def get_by_audience_asset(self, audience_asset_id: UUID) -> AudienceInsightStructuredData | None:
        # Fetches the requested by audience asset record or None, leaving not-found handling to the calling
        # service.
        result = await self.session.execute(
            select(AudienceInsightStructuredData).where(
                AudienceInsightStructuredData.audience_insight_asset_id == audience_asset_id
            )
        )
        return result.scalar_one_or_none()


class VisualReferenceAssetRepository(ScopedRepository[VisualReferenceAsset]):
    # Data-access helper for visual reference asset; services call this class instead of repeating SQLAlchemy
    # filters inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds VisualReferenceAssetRepository to the current async session, giving every query method the same
        # DB transaction context.
        super().__init__(session, VisualReferenceAsset)

    async def get_by_knowledge_asset(self, knowledge_asset_id: UUID) -> VisualReferenceAsset | None:
        # Fetches the requested by knowledge asset record or None, leaving not-found handling to the calling
        # service.
        result = await self.session.execute(
            select(VisualReferenceAsset).where(VisualReferenceAsset.knowledge_asset_id == knowledge_asset_id)
        )
        return result.scalar_one_or_none()


class MoodBoardAssetRepository(ScopedRepository[MoodBoardAsset]):
    # Data-access helper for mood board asset; services call this class instead of repeating SQLAlchemy filters
    # inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds MoodBoardAssetRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, MoodBoardAsset)

    async def get_by_knowledge_asset(self, knowledge_asset_id: UUID) -> MoodBoardAsset | None:
        # Fetches the requested by knowledge asset record or None, leaving not-found handling to the calling
        # service.
        result = await self.session.execute(
            select(MoodBoardAsset).where(MoodBoardAsset.knowledge_asset_id == knowledge_asset_id)
        )
        return result.scalar_one_or_none()


class ReusableBrandAssetRepository(ScopedRepository[ReusableBrandAsset]):
    # Data-access helper for reusable brand asset; services call this class instead of repeating SQLAlchemy
    # filters inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds ReusableBrandAssetRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, ReusableBrandAsset)

    async def list_by_brand(
        self,
        brand_space_id: UUID,
        *,
        tenant_id: UUID | None = None,
        active_only: bool = True,
    ) -> list[ReusableBrandAsset]:
        # Returns matching by brand records with repository scope applied; services assemble responses from
        # these rows.
        query = select(ReusableBrandAsset).where(ReusableBrandAsset.brand_space_id == brand_space_id)
        if tenant_id is not None:
            query = query.where(ReusableBrandAsset.tenant_id == tenant_id)
        if active_only:
            query = query.where(ReusableBrandAsset.is_active.is_(True))
        result = await self.session.execute(query.order_by(ReusableBrandAsset.created_at.desc()))
        return list(result.scalars().all())

    async def list_by_knowledge_asset(self, knowledge_asset_id: UUID) -> list[ReusableBrandAsset]:
        # Returns matching by knowledge asset records with repository scope applied; services assemble responses
        # from these rows.
        result = await self.session.execute(
            select(ReusableBrandAsset).where(ReusableBrandAsset.knowledge_asset_id == knowledge_asset_id)
        )
        return list(result.scalars().all())

    async def delete_by_knowledge_asset(self, knowledge_asset_id: UUID) -> None:
        # Removes persisted by knowledge asset rows at the DB boundary so services do not issue raw delete
        # statements.
        await self.session.execute(
            delete(ReusableBrandAsset).where(ReusableBrandAsset.knowledge_asset_id == knowledge_asset_id)
        )
        await self.session.flush()


class ColorPaletteEntryRepository(ScopedRepository[ColorPaletteEntry]):
    # Data-access helper for color palette entry; services call this class instead of repeating SQLAlchemy
    # filters inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds ColorPaletteEntryRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, ColorPaletteEntry)

    async def delete_by_asset(self, knowledge_asset_id: UUID) -> None:
        # Removes persisted by asset rows at the DB boundary so services do not issue raw delete statements.
        await self.session.execute(delete(ColorPaletteEntry).where(ColorPaletteEntry.knowledge_asset_id == knowledge_asset_id))
        await self.session.flush()


class TypographyGuideRepository(ScopedRepository[TypographyGuide]):
    # Data-access helper for typography guide; services call this class instead of repeating SQLAlchemy filters
    # inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds TypographyGuideRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, TypographyGuide)

    async def get_by_knowledge_asset(self, knowledge_asset_id: UUID) -> TypographyGuide | None:
        # Fetches the requested by knowledge asset record or None, leaving not-found handling to the calling
        # service.
        result = await self.session.execute(
            select(TypographyGuide).where(TypographyGuide.knowledge_asset_id == knowledge_asset_id)
        )
        return result.scalar_one_or_none()


class WordBankUploadRepository(ScopedRepository[WordBankUpload]):
    # Data-access helper for word bank upload; services call this class instead of repeating SQLAlchemy filters
    # inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds WordBankUploadRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, WordBankUpload)

    async def get_by_knowledge_asset(self, knowledge_asset_id: UUID) -> WordBankUpload | None:
        # Fetches the requested by knowledge asset record or None, leaving not-found handling to the calling
        # service.
        result = await self.session.execute(
            select(WordBankUpload).where(WordBankUpload.knowledge_asset_id == knowledge_asset_id)
        )
        return result.scalar_one_or_none()


class PositiveWordRepository(ScopedRepository[PositiveWord]):
    # Data-access helper for positive word; services call this class instead of repeating SQLAlchemy filters
    # inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds PositiveWordRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, PositiveWord)

    async def delete_by_upload(self, upload_id: UUID) -> None:
        # Removes persisted by upload rows at the DB boundary so services do not issue raw delete statements.
        await self.session.execute(delete(PositiveWord).where(PositiveWord.upload_id == upload_id))
        await self.session.flush()


class NegativeWordRepository(ScopedRepository[NegativeWord]):
    # Data-access helper for negative word; services call this class instead of repeating SQLAlchemy filters
    # inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds NegativeWordRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, NegativeWord)

    async def delete_by_upload(self, upload_id: UUID) -> None:
        # Removes persisted by upload rows at the DB boundary so services do not issue raw delete statements.
        await self.session.execute(delete(NegativeWord).where(NegativeWord.upload_id == upload_id))
        await self.session.flush()


class ReplaceableWordRepository(ScopedRepository[ReplaceableWord]):
    # Data-access helper for replaceable word; services call this class instead of repeating SQLAlchemy filters
    # inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds ReplaceableWordRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, ReplaceableWord)

    async def delete_by_upload(self, upload_id: UUID) -> None:
        # Removes persisted by upload rows at the DB boundary so services do not issue raw delete statements.
        await self.session.execute(delete(ReplaceableWord).where(ReplaceableWord.upload_id == upload_id))
        await self.session.flush()


class AssetProcessingStatusRepository(ScopedRepository[AssetProcessingStatus]):
    # Data-access helper for asset processing status; services call this class instead of repeating SQLAlchemy
    # filters inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds AssetProcessingStatusRepository to the current async session, giving every query method the same
        # DB transaction context.
        super().__init__(session, AssetProcessingStatus)

    async def get_by_asset(self, knowledge_asset_id: UUID) -> AssetProcessingStatus | None:
        # Fetches the requested by asset record or None, leaving not-found handling to the calling service.
        result = await self.session.execute(
            select(AssetProcessingStatus).where(AssetProcessingStatus.knowledge_asset_id == knowledge_asset_id)
        )
        return result.scalar_one_or_none()


class AssetValidationResultRepository(ScopedRepository[AssetValidationResult]):
    # Data-access helper for asset validation result; services call this class instead of repeating SQLAlchemy
    # filters inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds AssetValidationResultRepository to the current async session, giving every query method the same
        # DB transaction context.
        super().__init__(session, AssetValidationResult)

    async def list_by_asset_ids(self, asset_ids: list[UUID]) -> list[AssetValidationResult]:
        # Returns matching by asset IDs records with repository scope applied; services assemble responses from
        # these rows.
        if not asset_ids:
            return []
        result = await self.session.execute(
            select(AssetValidationResult).where(AssetValidationResult.knowledge_asset_id.in_(asset_ids))
        )
        return list(result.scalars().all())


class AssetCategoryRoutingRepository(ScopedRepository[AssetCategoryRouting]):
    # Data-access helper for asset category routing; services call this class instead of repeating SQLAlchemy
    # filters inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds AssetCategoryRoutingRepository to the current async session, giving every query method the same
        # DB transaction context.
        super().__init__(session, AssetCategoryRouting)

    async def get_by_asset(self, knowledge_asset_id: UUID) -> AssetCategoryRouting | None:
        # Fetches the requested by asset record or None, leaving not-found handling to the calling service.
        result = await self.session.execute(
            select(AssetCategoryRouting).where(AssetCategoryRouting.knowledge_asset_id == knowledge_asset_id)
        )
        return result.scalar_one_or_none()


class DataConflictRepository(ScopedRepository[DataConflict]):
    # Data-access helper for data conflict; services call this class instead of repeating SQLAlchemy filters
    # inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds DataConflictRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, DataConflict)

    async def delete_open_for_brand(self, tenant_id: UUID, brand_space_id: UUID) -> None:
        # Removes persisted open for brand rows at the DB boundary so services do not issue raw delete
        # statements.
        await self.session.execute(
            delete(DataConflict).where(
                DataConflict.tenant_id == tenant_id,
                DataConflict.brand_space_id == brand_space_id,
                DataConflict.resolution_status == "open",
            )
        )
        await self.session.flush()


class ResolvedBrandContextSnapshotRepository(ScopedRepository[ResolvedBrandContextSnapshot]):
    # Data-access helper for resolved brand context snapshot; services call this class instead of repeating
    # SQLAlchemy filters inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds ResolvedBrandContextSnapshotRepository to the current async session, giving every query method
        # the same DB transaction context.
        super().__init__(session, ResolvedBrandContextSnapshot)

    async def latest_for_brand(
        self,
        tenant_id: UUID,
        brand_space_id: UUID,
        snapshot_kind: str = "validated",
    ) -> ResolvedBrandContextSnapshot | None:
        # Fetches the requested latest for brand record or None, leaving not-found handling to the calling
        # service.
        result = await self.session.execute(
            select(ResolvedBrandContextSnapshot)
            .where(
                ResolvedBrandContextSnapshot.tenant_id == tenant_id,
                ResolvedBrandContextSnapshot.brand_space_id == brand_space_id,
                ResolvedBrandContextSnapshot.snapshot_kind == snapshot_kind,
            )
            .order_by(ResolvedBrandContextSnapshot.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def trim_for_brand(
        self,
        tenant_id: UUID,
        brand_space_id: UUID,
        *,
        snapshot_kind: str = "validated",
        keep_latest: int = 25,
    ) -> None:
        # Removes persisted for brand rows at the DB boundary so services do not issue raw delete statements.
        if keep_latest <= 0:
            await self.session.execute(
                delete(ResolvedBrandContextSnapshot).where(
                    ResolvedBrandContextSnapshot.tenant_id == tenant_id,
                    ResolvedBrandContextSnapshot.brand_space_id == brand_space_id,
                    ResolvedBrandContextSnapshot.snapshot_kind == snapshot_kind,
                )
            )
            await self.session.flush()
            return
        result = await self.session.execute(
            select(ResolvedBrandContextSnapshot.id)
            .where(
                ResolvedBrandContextSnapshot.tenant_id == tenant_id,
                ResolvedBrandContextSnapshot.brand_space_id == brand_space_id,
                ResolvedBrandContextSnapshot.snapshot_kind == snapshot_kind,
            )
            .order_by(ResolvedBrandContextSnapshot.created_at.desc())
            .offset(keep_latest)
        )
        stale_ids = [row[0] for row in result.all()]
        if not stale_ids:
            return
        await self.session.execute(
            delete(ResolvedBrandContextSnapshot).where(ResolvedBrandContextSnapshot.id.in_(stale_ids))
        )
        await self.session.flush()


class BrandLegalAssetRepository(ScopedRepository[BrandLegalAsset]):
    # Data-access helper for brand legal asset; services call this class instead of repeating SQLAlchemy filters
    # inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds BrandLegalAssetRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, BrandLegalAsset)

    async def get_by_brand_space(self, brand_space_id: UUID) -> list[BrandLegalAsset]:
        # Fetches the requested by brand space record or None, leaving not-found handling to the calling
        # service.
        result = await self.session.execute(
            select(BrandLegalAsset).where(BrandLegalAsset.brand_space_id == brand_space_id)
        )
        return list(result.scalars().all())

    async def get_by_source_asset(self, source_asset_id: UUID) -> BrandLegalAsset | None:
        # Fetches the requested by source asset record or None, leaving not-found handling to the calling
        # service.
        result = await self.session.execute(
            select(BrandLegalAsset).where(BrandLegalAsset.source_asset_id == source_asset_id)
        )
        return result.scalar_one_or_none()


class BrandCTATemplateRepository(ScopedRepository[BrandCTATemplate]):
    # Data-access helper for brand CTAtemplate; services call this class instead of repeating SQLAlchemy filters
    # inline.
    def __init__(self, session: AsyncSession) -> None:
        # Binds BrandCTATemplateRepository to the current async session, giving every query method the same DB
        # transaction context.
        super().__init__(session, BrandCTATemplate)

    async def get_by_brand_space(self, brand_space_id: UUID) -> list[BrandCTATemplate]:
        # Fetches the requested by brand space record or None, leaving not-found handling to the calling
        # service.
        result = await self.session.execute(
            select(BrandCTATemplate).where(BrandCTATemplate.brand_space_id == brand_space_id)
        )
        return list(result.scalars().all())

    async def get_default(self, brand_space_id: UUID) -> BrandCTATemplate | None:
        # Fetches the requested default record or None, leaving not-found handling to the calling service.
        result = await self.session.execute(
            select(BrandCTATemplate).where(
                BrandCTATemplate.brand_space_id == brand_space_id,
                BrandCTATemplate.is_default == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()
