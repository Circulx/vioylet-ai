# Service classes hold business workflows between the HTTP layer, repositories, and integrations.
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.brand_intelligence import BrandIntelligenceService
from app.core.enums import BrandSpaceLifecycle, RoleCode, UsageMetricCode
from app.core.exceptions import LifecycleError, NotFoundError
from app.models.brand import BrandConfigurationSection, BrandSpace, BrandSpaceMember, Guardrail, Objective, Persona
from app.models.collaboration import UsageLimit
from app.models.content import ContentVersion, GeneratedAsset
from app.models.knowledge import KnowledgeAsset
from app.models.tenant import Tenant
from app.repositories.brand import (
    BrandMemberRepository,
    BrandSectionRepository,
    BrandSpaceRepository,
    GuardrailRepository,
    ObjectiveRepository,
    PersonaRepository,
)
from app.schemas.brand import BrandCreateRequest, BrandSectionUpsertRequest, BrandSectionsUpsertRequest, BrandUpdateRequest, GuardrailPayload
from app.services.brand_summary_memory import BrandSummaryMemoryService
from app.services.data_validation import DataValidatorService
from app.services.notification import InAppNotificationService
from app.services.usage import UsageLimitService
from app.utils.text import slugify


class BrandSpaceService:
    # Business layer for brand space; routes and workers pass validated inputs here and receive domain results
    # back.
    def __init__(self, session: AsyncSession) -> None:
        # Wires the repositories and helper services this workflow reuses across its public methods.
        self.session = session
        self.brands = BrandSpaceRepository(session)
        self.sections = BrandSectionRepository(session)
        self.personas = PersonaRepository(session)
        self.guardrails = GuardrailRepository(session)
        self.objectives = ObjectiveRepository(session)
        self.members = BrandMemberRepository(session)
        self.usage = UsageLimitService(session)
        self.intelligence = BrandIntelligenceService()
        self.validator = DataValidatorService(session)
        self.brand_summary_memory = BrandSummaryMemoryService()

    @staticmethod
    def _clamp_percent(value: object) -> int:
        # Internal helper for clamp percent; it keeps the public service method focused on orchestration instead
        # of low-level shaping.
        try:
            numeric_value = int(value)
        except (TypeError, ValueError):
            return 0
        return max(0, min(numeric_value, 100))

    @staticmethod
    def _metric_percent(used: int, allocated_limit: float) -> int:
        # Internal helper for metric percent; it keeps the public service method focused on orchestration
        # instead of low-level shaping.
        if allocated_limit <= 0:
            return 0
        return max(0, min(round((used / allocated_limit) * 100), 100))

    async def _commit_and_refresh_brand(self, brand: BrandSpace) -> BrandSpace:
        # Internal helper for commit and refresh brand; it keeps the public service method focused on
        # orchestration instead of low-level shaping.
        await self.session.commit()
        await self.session.refresh(brand)
        return brand

    @staticmethod
    def _build_guardrail_record(payload: dict) -> dict:
        # Guardrail sections may include asset references and other section-only
        # metadata. The relational guardrails table stores only the core rule set.
        return GuardrailPayload.model_validate(payload).model_dump(
            exclude={
                "positive_word_bank_asset_ids",
                "negative_word_bank_asset_ids",
                "replaceable_word_bank_asset_ids",
            }
        )

    async def create_brand(
        self,
        tenant_id: UUID,
        created_by: UUID,
        payload: BrandCreateRequest,
        actor_role_codes: set[str] | None = None,
    ) -> BrandSpace:
        # Runs the brand service flow and persists the resulting state before returning it to the route or
        # worker.
        await self.usage.enforce(tenant_id, UsageMetricCode.BRAND_SPACES)
        slug = slugify(payload.identity.brand_name)
        brand = BrandSpace(
            tenant_id=tenant_id,
            name=payload.identity.brand_name,
            slug=slug,
            description=payload.identity.brand_description,
            industry_category=payload.identity.industry_category,
            sub_industry=payload.identity.sub_industry,
            geography_country=payload.identity.target_geography.get("country"),
            geography_city=payload.identity.target_geography.get("city"),
            audience_type=payload.identity.audience_type,
            lifecycle_state=BrandSpaceLifecycle.DRAFT,
            overview_snapshot={},
            resolved_brand_context={},
        )
        await self.brands.add(brand)
        await self.members.add(
            BrandSpaceMember(
                tenant_id=tenant_id,
                brand_space_id=brand.id,
                user_id=created_by,
                can_manage=True,
            )
        )
        await self.sections.add(
            BrandConfigurationSection(
                tenant_id=tenant_id,
                brand_space_id=brand.id,
                section_code="identity",
                payload=payload.identity.model_dump(),
                completion_percent=100,
            )
        )
        # The payload/context shape drives this branch because downstream serializers depend on consistent
        # fields.
        if payload.foundations:
            await self.sections.add(
                BrandConfigurationSection(
                    tenant_id=tenant_id,
                    brand_space_id=brand.id,
                    section_code="foundations",
                    payload=payload.foundations.model_dump(),
                    completion_percent=100,
                )
            )
        else:
            await self.sections.add(
                BrandConfigurationSection(
                    tenant_id=tenant_id,
                    brand_space_id=brand.id,
                    section_code="foundations",
                    payload={},
                    completion_percent=0,
                )
            )
        # The payload/context shape drives this branch because downstream serializers depend on consistent
        # fields.
        if payload.voice_tone:
            await self.sections.add(
                BrandConfigurationSection(
                    tenant_id=tenant_id,
                    brand_space_id=brand.id,
                    section_code="voice_tone",
                    payload=payload.voice_tone.model_dump(),
                    completion_percent=100,
                )
            )
        else:
            await self.sections.add(
                BrandConfigurationSection(
                    tenant_id=tenant_id,
                    brand_space_id=brand.id,
                    section_code="voice_tone",
                    payload={},
                    completion_percent=0,
                )
            )
        # Builds the grouped response or persistence payload one record at a time because later steps expect
        # this exact shape.
        for section_code in ["personas", "guardrails", "knowledge", "objectives", "visual_identity", "prompt_intelligence", "review"]:
            await self.sections.add(
                BrandConfigurationSection(
                    tenant_id=tenant_id,
                    brand_space_id=brand.id,
                    section_code=section_code,
                    payload={},
                    completion_percent=0,
                )
            )
        await self.usage.increment(tenant_id, UsageMetricCode.BRAND_SPACES)
        if actor_role_codes:
            await InAppNotificationService(self.session).create_brand_space_created_notification(
                recipient_user_id=created_by,
                tenant_id=tenant_id,
                brand_space_name=brand.name,
                actor_role_codes=actor_role_codes,
            )
        await self.session.commit()
        return await self.refresh_context(brand.id)

    async def refresh_context(self, brand_space_id: UUID) -> BrandSpace:
        # Runs the refresh context service flow by coordinating repositories, validators, and integrations, then
        # returns domain data.
        brand, _snapshot = await self.validator.refresh_brand_context(brand_space_id)
        try:
            sections = await self.sections.list_current_sections(brand_space_id, brand.tenant_id)
        except AttributeError:
            sections = []
        self.brand_summary_memory.upsert_brand_summary(brand, sections=sections)
        return brand

    async def _apply_section_upsert(
        self,
        tenant_id: UUID,
        brand_space_id: UUID,
        brand: BrandSpace,
        payload: BrandSectionUpsertRequest,
        existing_sections: list[BrandConfigurationSection],
        section_versions: dict[str, int],
    ) -> None:
        # Internal helper for section upsert; it keeps the public service method focused on orchestration
        # instead of low-level shaping.
        for existing in existing_sections:
            if existing.section_code == payload.section_code:
                existing.is_current = False
        next_version = section_versions.get(payload.section_code, 0) + 1
        section_versions[payload.section_code] = next_version
        await self.sections.add(
            BrandConfigurationSection(
                tenant_id=tenant_id,
                brand_space_id=brand_space_id,
                section_code=payload.section_code,
                version=next_version,
                is_current=True,
                completion_percent=payload.completion_percent,
                payload=payload.payload,
            )
        )

        # The payload/context shape drives this branch because downstream serializers depend on consistent
        # fields.
        if payload.section_code == "identity":
            brand.name = payload.payload.get("brand_name", brand.name)
            brand.description = payload.payload.get("brand_description", brand.description)
            brand.industry_category = payload.payload.get("industry_category")
            brand.sub_industry = payload.payload.get("sub_industry")
            target_geography = payload.payload.get("target_geography", {}) or {}
            brand.geography_country = target_geography.get("country")
            brand.geography_city = target_geography.get("city")
            brand.audience_type = payload.payload.get("audience_type")
        if payload.section_code == "foundations":
            brand.overview_snapshot = {
                **brand.overview_snapshot,
                "foundations": payload.payload,
            }
        if payload.section_code == "voice_tone":
            brand.overview_snapshot = {
                **brand.overview_snapshot,
                "voice_tone": payload.payload,
            }
        if payload.section_code == "visual_identity":
            brand.overview_snapshot = {
                **brand.overview_snapshot,
                "visual_identity": payload.payload,
            }

        # The payload/context shape drives this branch because downstream serializers depend on consistent
        # fields.
        if payload.section_code == "personas":
            existing_personas = await self.personas.list_by_brand(brand_space_id, tenant_id)
            for existing in existing_personas:
                await self.personas.delete(existing)
            default_persona_id = None
            for item in payload.payload.get("personas", []):
                created = await self.personas.add(Persona(tenant_id=tenant_id, brand_space_id=brand_space_id, **item))
                if created.is_default:
                    default_persona_id = created.id
            brand.default_persona_id = default_persona_id
        # The payload/context shape drives this branch because downstream serializers depend on consistent
        # fields.
        if payload.section_code == "guardrails":
            existing_guardrails = await self.guardrails.list_by_brand(brand_space_id, tenant_id)
            for existing in existing_guardrails:
                await self.guardrails.delete(existing)
            await self.guardrails.add(
                Guardrail(
                    tenant_id=tenant_id,
                    brand_space_id=brand_space_id,
                    **self._build_guardrail_record(payload.payload),
                )
            )
        if payload.section_code == "objectives":
            existing_objectives = await self.objectives.list_by_brand(brand_space_id, tenant_id)
            for existing in existing_objectives:
                await self.objectives.delete(existing)
            for item in payload.payload.get("objectives", []):
                await self.objectives.add(Objective(tenant_id=tenant_id, brand_space_id=brand_space_id, **item))

    async def upsert_section(self, tenant_id: UUID, brand_space_id: UUID, payload: BrandSectionUpsertRequest) -> BrandSpace:
        # Runs the section service flow and persists the resulting state before returning it to the route or
        # worker.
        brand = await self.brands.get_scoped(tenant_id, brand_space_id)
        if not brand:
            raise NotFoundError("Brand Space not found")
        existing_sections = await self.sections.list_current_sections(brand_space_id, tenant_id)
        section_versions = {
            section.section_code: max(
                section.version,
                max((item.version for item in existing_sections if item.section_code == section.section_code), default=0),
            )
            for section in existing_sections
        }
        await self._apply_section_upsert(tenant_id, brand_space_id, brand, payload, existing_sections, section_versions)
        await self.session.commit()
        return await self.refresh_context(brand_space_id)

    async def upsert_sections(self, tenant_id: UUID, brand_space_id: UUID, payload: BrandSectionsUpsertRequest) -> BrandSpace:
        # Runs the sections service flow and persists the resulting state before returning it to the route or
        # worker.
        brand = await self.brands.get_scoped(tenant_id, brand_space_id)
        if not brand:
            raise NotFoundError("Brand Space not found")
        existing_sections = await self.sections.list_current_sections(brand_space_id, tenant_id)
        section_versions = {
            section.section_code: max(
                section.version,
                max((item.version for item in existing_sections if item.section_code == section.section_code), default=0),
            )
            for section in existing_sections
        }
        for section in payload.sections:
            await self._apply_section_upsert(tenant_id, brand_space_id, brand, section, existing_sections, section_versions)
        await self.session.commit()
        return await self.refresh_context(brand_space_id)

    async def update_brand(self, tenant_id: UUID, brand_space_id: UUID, payload: BrandUpdateRequest) -> BrandSpace:
        # Runs the brand service flow by coordinating repositories, validators, and integrations, then returns
        # domain data.
        brand = await self.brands.get_scoped(tenant_id, brand_space_id)
        if not brand:
            raise NotFoundError("Brand Space not found")
        if payload.description is not None:
            brand.description = payload.description
        if payload.overview_snapshot is not None:
            brand.overview_snapshot = payload.overview_snapshot
        return await self._commit_and_refresh_brand(brand)

    async def get_usage_summary(self, tenant_id: UUID, brand_space_id: UUID) -> dict:
        # Runs the usage summary service flow by coordinating repositories, validators, and integrations, then
        # returns domain data.
        brand = await self.brands.get_scoped(tenant_id, brand_space_id)
        if not brand:
            raise NotFoundError("Brand Space not found")

        tenant = await self.session.get(Tenant, tenant_id)
        usage_limit = await self.session.scalar(
            select(UsageLimit).where(UsageLimit.tenant_id == tenant_id)
        )
        configured_targets = {}
        if tenant and isinstance(tenant.metadata_json, dict):
            raw_targets = tenant.metadata_json.get("brand_usage_targets")
            if isinstance(raw_targets, dict):
                configured_targets = raw_targets
        capacity_percent = self._clamp_percent(configured_targets.get(str(brand_space_id)) or configured_targets.get(brand_space_id))
        capacity_ratio = capacity_percent / 100

        content_used = int(
            await self.session.scalar(
                select(func.count(ContentVersion.id)).where(
                    ContentVersion.tenant_id == tenant_id,
                    ContentVersion.brand_space_id == brand_space_id,
                )
            )
            or 0
        )
        image_used = int(
            await self.session.scalar(
                select(func.count(GeneratedAsset.id)).where(
                    GeneratedAsset.tenant_id == tenant_id,
                    GeneratedAsset.brand_space_id == brand_space_id,
                )
            )
            or 0
        )
        ocr_used = int(
            await self.session.scalar(
                select(func.coalesce(func.sum(KnowledgeAsset.page_count), 0)).where(
                    KnowledgeAsset.tenant_id == tenant_id,
                    KnowledgeAsset.brand_space_id == brand_space_id,
                )
            )
            or 0
        )

        limits = {
            UsageMetricCode.CONTENT_GENERATIONS: float(getattr(usage_limit, "max_content_generations", 0) or 0) * capacity_ratio,
            UsageMetricCode.IMAGE_GENERATIONS: float(getattr(usage_limit, "max_image_generations", 0) or 0) * capacity_ratio,
            UsageMetricCode.OCR_PAGES: float(getattr(usage_limit, "max_ocr_pages", 0) or 0) * capacity_ratio,
        }
        usage_values = {
            UsageMetricCode.CONTENT_GENERATIONS: content_used,
            UsageMetricCode.IMAGE_GENERATIONS: image_used,
            UsageMetricCode.OCR_PAGES: ocr_used,
        }
        metrics = [
            {
                "code": metric_code,
                "used": usage_values[metric_code],
                "allocated_limit": limits[metric_code],
                "percent": self._metric_percent(usage_values[metric_code], limits[metric_code]),
            }
            for metric_code in (
                UsageMetricCode.CONTENT_GENERATIONS,
                UsageMetricCode.IMAGE_GENERATIONS,
                UsageMetricCode.OCR_PAGES,
            )
        ]
        active_metric_percents = [item["percent"] for item in metrics if item["allocated_limit"] > 0]
        usage_percent = round(sum(active_metric_percents) / len(active_metric_percents)) if active_metric_percents else 0

        return {
            "brand_space_id": brand_space_id,
            "tenant_id": tenant_id,
            "capacity_percent": capacity_percent,
            "usage_percent": usage_percent,
            "metrics": metrics,
        }

    async def finalize_brand(
        self,
        tenant_id: UUID,
        brand_space_id: UUID,
        actor_user_id: UUID | None = None,
        actor_role_codes: set[str] | None = None,
    ) -> BrandSpace:
        # Runs the brand service flow by coordinating repositories, validators, and integrations, then returns
        # domain data.
        return await self.publish_brand(tenant_id, brand_space_id, actor_user_id, actor_role_codes)

    async def publish_brand(
        self,
        tenant_id: UUID,
        brand_space_id: UUID,
        actor_user_id: UUID | None = None,
        actor_role_codes: set[str] | None = None,
    ) -> BrandSpace:
        # Runs the brand service flow by coordinating repositories, validators, and integrations, then returns
        # domain data.
        brand = await self.brands.get_scoped(tenant_id, brand_space_id)
        if not brand:
            raise NotFoundError("Brand Space not found")
        should_notify_publish = brand.lifecycle_state != BrandSpaceLifecycle.ACTIVE
        sections = await self.sections.list_current_sections(brand_space_id, tenant_id)
        identity_section = next((section for section in sections if section.section_code == "identity"), None)
        if not identity_section or not identity_section.payload.get("brand_name"):
            raise LifecycleError("Brand Space cannot be published without a brand identity.")
        brand = await self.refresh_context(brand_space_id)
        brand.lifecycle_state = BrandSpaceLifecycle.ACTIVE
        brand.is_finalized = True
        if actor_user_id and actor_role_codes and should_notify_publish:
            await InAppNotificationService(self.session).create_brand_space_published_notification(
                recipient_user_id=actor_user_id,
                tenant_id=tenant_id,
                brand_space_name=brand.name,
                actor_role_codes=actor_role_codes,
            )
        return await self._commit_and_refresh_brand(brand)

    async def unpublish_brand(self, tenant_id: UUID, brand_space_id: UUID) -> BrandSpace:
        # Runs the brand service flow by coordinating repositories, validators, and integrations, then returns
        # domain data.
        brand = await self.brands.get_scoped(tenant_id, brand_space_id)
        if not brand:
            raise NotFoundError("Brand Space not found")
        brand.lifecycle_state = BrandSpaceLifecycle.DRAFT
        return await self._commit_and_refresh_brand(brand)

    async def archive_brand(
        self,
        tenant_id: UUID,
        brand_space_id: UUID,
        actor_user_id: UUID | None = None,
        actor_role_codes: set[str] | None = None,
    ) -> BrandSpace:
        # Runs the brand service flow by coordinating repositories, validators, and integrations, then returns
        # domain data.
        brand = await self.brands.get_scoped(tenant_id, brand_space_id)
        if not brand:
            raise NotFoundError("Brand Space not found")
        brand.lifecycle_state = BrandSpaceLifecycle.ARCHIVED
        if actor_user_id and actor_role_codes:
            await InAppNotificationService(self.session).create_brand_space_archived_notification(
                recipient_user_id=actor_user_id,
                tenant_id=tenant_id,
                brand_space_name=brand.name,
                actor_role_codes=actor_role_codes,
            )
        return await self._commit_and_refresh_brand(brand)

    async def restore_brand(
        self,
        tenant_id: UUID,
        brand_space_id: UUID,
        actor_user_id: UUID | None = None,
        actor_role_codes: set[str] | None = None,
    ) -> BrandSpace:
        # Runs the brand service flow by coordinating repositories, validators, and integrations, then returns
        # domain data.
        brand = await self.brands.get_scoped(tenant_id, brand_space_id)
        if not brand:
            raise NotFoundError("Brand Space not found")
        brand.lifecycle_state = BrandSpaceLifecycle.ACTIVE
        if actor_user_id and actor_role_codes:
            await InAppNotificationService(self.session).create_brand_space_restored_notification(
                recipient_user_id=actor_user_id,
                tenant_id=tenant_id,
                brand_space_name=brand.name,
                actor_role_codes=actor_role_codes,
            )
        return await self._commit_and_refresh_brand(brand)

    async def delete_brand(
        self,
        tenant_id: UUID,
        brand_space_id: UUID,
        actor_user_id: UUID | None = None,
        actor_role_codes: set[str] | None = None,
    ) -> BrandSpace:
        # Runs the brand service flow by coordinating repositories, validators, and integrations, then returns
        # domain data.
        brand = await self.brands.get_scoped(tenant_id, brand_space_id)
        if not brand:
            raise NotFoundError("Brand Space not found")
        brand.lifecycle_state = BrandSpaceLifecycle.DELETED
        if actor_user_id and actor_role_codes:
            await InAppNotificationService(self.session).create_brand_space_deleted_notification(
                recipient_user_id=actor_user_id,
                tenant_id=tenant_id,
                brand_space_name=brand.name,
                actor_role_codes=actor_role_codes,
            )
        return await self._commit_and_refresh_brand(brand)

    async def list_brands(self, tenant_id: UUID, user_id: UUID, role_codes: set[str]) -> list[BrandSpace]:
        # Runs the brands service flow by coordinating repositories, validators, and integrations, then returns
        # domain data.
        if RoleCode.BRAND_USER in role_codes:
            brand_ids = await self.members.list_brand_ids_for_user(user_id)
            all_brands = await self.brands.list_by_tenant(tenant_id)
            return [brand for brand in all_brands if brand.id in set(brand_ids)]
        return await self.brands.list_by_tenant(tenant_id)

    async def require_active(self, tenant_id: UUID, brand_space_id: UUID) -> BrandSpace:
        # Runs the require active service flow by coordinating repositories, validators, and integrations, then
        # returns domain data.
        brand = await self.brands.get_scoped(tenant_id, brand_space_id)
        if not brand:
            raise NotFoundError("Brand Space not found")
        if brand.lifecycle_state != BrandSpaceLifecycle.ACTIVE:
            raise LifecycleError("Brand Space must be Active")
        return brand
