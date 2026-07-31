# Service classes hold business workflows between the HTTP layer, repositories, and integrations.
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.brand_intelligence import BrandIntelligenceService
from app.core.enums import BrandSpaceLifecycle, RoleCode, UsageMetricCode
from app.core.exceptions import LifecycleError, NotFoundError
from app.models.brand import BrandConfigurationSection, BrandSpace, BrandSpaceMember, Guardrail, Objective, Persona
from app.models.collaboration import BrandSpaceHistory, UsageLimit
from app.models.content import ContentVersion, GeneratedAsset
from app.models.knowledge import KnowledgeAsset
from app.models.tenant import Role, Tenant, User, UserRole
from app.repositories.collaboration import BrandSpaceHistoryRepository
from app.repositories.brand import (
    BrandMemberRepository,
    BrandSectionRepository,
    BrandSpaceRepository,
    GuardrailRepository,
    ObjectiveRepository,
    PersonaRepository,
)
from app.schemas.brand import BrandCreateRequest, BrandSectionUpsertRequest, BrandSectionsUpsertRequest, BrandUpdateRequest, GuardrailPayload
from app.services.brand_capacity import BrandCapacityAllocationService
from app.services.brand_summary_memory import BrandSummaryMemoryService
from app.services.vectorstore.brand_profile_embedder import BrandProfileEmbedder
from app.services.data_validation import DataValidatorService
from app.services.email import EmailService
from app.services.notification import InAppNotificationService
from app.services.notification_preferences import email_notifications_enabled
from app.services.usage import UsageLimitService
from app.utils.text import slugify


logger = logging.getLogger(__name__)


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
        self.history = BrandSpaceHistoryRepository(session)
        self.usage = UsageLimitService(session)
        self.intelligence = BrandIntelligenceService()
        self.validator = DataValidatorService(session)
        self.brand_summary_memory = BrandSummaryMemoryService()
        self.profile_embedder = BrandProfileEmbedder()
        self.email = EmailService()

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
        current_brand_spaces = int(
            await self.session.scalar(
                select(func.count(BrandSpace.id)).where(
                    BrandSpace.tenant_id == tenant_id,
                    BrandSpace.lifecycle_state != BrandSpaceLifecycle.DELETED,
                )
            )
            or 0
        )
        await self.usage.enforce(
            tenant_id,
            UsageMetricCode.BRAND_SPACES,
            current_usage=current_brand_spaces,
        )
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
        await self.usage.increment(
            tenant_id,
            UsageMetricCode.BRAND_SPACES,
            current_usage=current_brand_spaces,
        )
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

        # Embed structured brand-space fields into Pinecone so Layer 1 retrieval
        # can surface both document chunks and structured profile data.
        # Run in a thread because IngestionService (OpenAI + Pinecone) is synchronous.
        try:
            persona_rows = await self.personas.list_by_brand(brand_space_id, brand.tenant_id)
            guardrail_rows = await self.guardrails.list_by_brand(brand_space_id, brand.tenant_id)
            objective_rows = await self.objectives.list_by_brand(brand_space_id, brand.tenant_id)
            import asyncio
            await asyncio.to_thread(
                self.profile_embedder.embed_brand_profile,
                brand_space_id,
                brand_name=brand.name,
                description=brand.description,
                industry_category=brand.industry_category,
                overview_snapshot=brand.overview_snapshot,
                sections=[{"section_code": s.section_code, "payload": s.payload} for s in sections],
                personas=[{k: v for k, v in p.__dict__.items() if not k.startswith("_") and k not in ("tenant_id", "brand_space_id")} for p in persona_rows],
                guardrails=[{k: v for k, v in g.__dict__.items() if not k.startswith("_") and k not in ("tenant_id", "brand_space_id")} for g in guardrail_rows],
                objectives=[{k: v for k, v in o.__dict__.items() if not k.startswith("_") and k not in ("tenant_id", "brand_space_id")} for o in objective_rows],
            )
        except Exception as exc:
            # Profile embedding is best-effort — don't block brand save on Pinecone issues
            import logging
            logging.getLogger(__name__).warning(f"brand_profile_embedder.failed brand_id={brand_space_id} error={exc}")

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

    async def upsert_sections(
        self,
        tenant_id: UUID,
        brand_space_id: UUID,
        payload: BrandSectionsUpsertRequest,
        actor_user_id: UUID | None = None,
        actor_role_codes: set[str] | None = None,
    ) -> BrandSpace:
        # Runs the sections service flow and persists the resulting state before returning it to the route or
        # worker.
        brand = await self.brands.get_scoped(tenant_id, brand_space_id)
        if not brand:
            raise NotFoundError("Brand Space not found")
        was_published = brand.lifecycle_state == BrandSpaceLifecycle.ACTIVE
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
        updated_brand = await self.refresh_context(brand_space_id)
        normalized_actor_roles = {str(role_code) for role_code in (actor_role_codes or set())}
        if was_published and actor_user_id and RoleCode.TENANT_ADMIN.value in normalized_actor_roles:
            emails_scheduled = await self._dispatch_published_brand_space_updated_emails(updated_brand, actor_user_id)
            if emails_scheduled:
                await self.create_history_entry(
                    tenant_id=tenant_id,
                    brand_space_id=brand_space_id,
                    activity_type="brand_space_updated",
                    message="Brand Space updated.",
                    performed_by=actor_user_id,
                    metadata={"brand_space_name": updated_brand.name},
                )
        return updated_brand

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
        now = datetime.now(timezone.utc)
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        month_end = (
            datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
            if now.month == 12
            else datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
        )

        content_used = int(
            await self.session.scalar(
                select(func.count(ContentVersion.id)).where(
                    ContentVersion.tenant_id == tenant_id,
                    ContentVersion.brand_space_id == brand_space_id,
                    ContentVersion.created_at >= month_start,
                    ContentVersion.created_at < month_end,
                )
            )
            or 0
        )
        image_used = int(
            await self.session.scalar(
                select(func.count(GeneratedAsset.id)).where(
                    GeneratedAsset.tenant_id == tenant_id,
                    GeneratedAsset.brand_space_id == brand_space_id,
                    GeneratedAsset.created_at >= month_start,
                    GeneratedAsset.created_at < month_end,
                )
            )
            or 0
        )
        ocr_used = int(
            await self.session.scalar(
                select(func.coalesce(func.sum(KnowledgeAsset.page_count), 0)).where(
                    KnowledgeAsset.tenant_id == tenant_id,
                    KnowledgeAsset.brand_space_id == brand_space_id,
                    KnowledgeAsset.created_at >= month_start,
                    KnowledgeAsset.created_at < month_end,
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
        usage_percent = round(
            BrandCapacityAllocationService.equal_average_usage_percent(
                {str(metric_code): value for metric_code, value in usage_values.items()},
                {str(metric_code): value for metric_code, value in limits.items()},
            )
        )

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

    async def list_history(self, tenant_id: UUID, brand_space_id: UUID) -> list[BrandSpaceHistory]:
        brand = await self.brands.get_scoped(tenant_id, brand_space_id)
        if not brand:
            raise NotFoundError("Brand Space not found")
        return await self.history.list_for_brand(tenant_id, brand_space_id)

    async def create_history_entry(
        self,
        *,
        tenant_id: UUID,
        brand_space_id: UUID,
        activity_type: str,
        message: str,
        performed_by: UUID | None = None,
        metadata: dict | None = None,
    ) -> BrandSpaceHistory:
        history_entry = BrandSpaceHistory(
            tenant_id=tenant_id,
            brand_space_id=brand_space_id,
            activity_type=activity_type,
            message=message,
            performed_by=performed_by,
            metadata_json=metadata or {},
        )
        await self.history.add(history_entry)
        await self.session.commit()
        return history_entry

    async def _brand_space_update_email_recipients(
        self,
        tenant_id: UUID,
        brand_space_id: UUID,
        actor_user_id: UUID,
    ) -> list[User]:
        actor_result = await self.session.execute(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                User.id == actor_user_id,
                User.tenant_id == tenant_id,
                User.is_active.is_(True),
                Role.code == RoleCode.TENANT_ADMIN.value,
            )
            .distinct()
        )
        super_user_result = await self.session.execute(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                User.tenant_id == tenant_id,
                User.is_active.is_(True),
                Role.code == RoleCode.TENANT_USER.value,
            )
            .distinct()
        )
        brand_user_result = await self.session.execute(
            select(User)
            .join(BrandSpaceMember, BrandSpaceMember.user_id == User.id)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                BrandSpaceMember.tenant_id == tenant_id,
                BrandSpaceMember.brand_space_id == brand_space_id,
                User.tenant_id == tenant_id,
                User.is_active.is_(True),
                Role.code == RoleCode.BRAND_USER.value,
            )
            .distinct()
        )
        recipients: list[User] = []
        seen_emails: set[str] = set()
        for user in [
            *actor_result.scalars().all(),
            *super_user_result.scalars().all(),
            *brand_user_result.scalars().all(),
        ]:
            email = (user.email or "").strip()
            email_key = email.lower()
            if not email_key or email_key in seen_emails:
                continue
            if not email_notifications_enabled(getattr(user, "metadata_json", None)):
                continue
            seen_emails.add(email_key)
            recipients.append(user)
        return recipients

    async def _dispatch_published_brand_space_updated_emails(self, brand: BrandSpace, actor_user_id: UUID) -> bool:
        email_tasks = [
            (recipient.email, recipient.full_name, brand.name)
            for recipient in await self._brand_space_update_email_recipients(brand.tenant_id, brand.id, actor_user_id)
        ]
        if not email_tasks:
            return False
        asyncio.create_task(asyncio.to_thread(self._run_brand_space_updated_email_tasks, email_tasks))
        return True

    def _run_brand_space_updated_email_tasks(self, email_tasks: list[tuple[str, str | None, str]]) -> None:
        for recipient_email, recipient_name, brand_space_name in email_tasks:
            try:
                self.email.send_brand_space_updated_email(recipient_email, recipient_name, brand_space_name)
            except Exception:
                logger.exception("Failed to send Brand Space updated email to %s.", recipient_email)

    async def require_active(self, tenant_id: UUID, brand_space_id: UUID) -> BrandSpace:
        # Runs the require active service flow by coordinating repositories, validators, and integrations, then
        # returns domain data.
        brand = await self.brands.get_scoped(tenant_id, brand_space_id)
        if not brand:
            raise NotFoundError("Brand Space not found")
        if brand.lifecycle_state != BrandSpaceLifecycle.ACTIVE:
            raise LifecycleError("Brand Space must be Active")
        return brand
