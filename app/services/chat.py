from __future__ import annotations

from datetime import timedelta
import logging
import re
from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AssetRole, BrandSpaceLifecycle, ExportFileType
from app.core.studio import resolve_studio_panel_defaults
from app.core.exceptions import GenerationFailureError, GuardrailViolationError, LifecycleError, NotFoundError
from app.integrations.object_storage import get_object_storage
from app.services.asset_delivery import AssetDeliveryService
from app.services.conversation_memory import ConversationMemoryService
from app.models.content import ChatMessage, ContentSession, GeneratedAsset
from app.repositories.brand import BrandSectionRepository, BrandSpaceRepository
from app.repositories.content import AssetRepository, ChatMessageRepository, ContentRepository, SessionRepository
from app.schemas.common import StudioPanelSelection
from app.schemas.chat import ChatMessageCreateRequest, ChatSessionCreateRequest
from app.schemas.content import ContentGenerateRequest, ContentRewriteRequest, RequestInheritancePolicy
from app.services.artifact_state import ArtifactStateService
from app.services.brand_summary_memory import BrandSummaryMemoryService
from app.services.conversation import ConversationService
from app.services.content import ContentService
from app.services.evaluation import EvaluationService
from app.services.intent_router import ChatIntentDecision, IntentRouterService
from app.services.mixed_workflow import MixedWorkflowService
from app.services.text_content import TextContentService

logger = logging.getLogger(__name__)

CHAT_HISTORY_MESSAGE_LIMIT = 30


class ChatService:
    VISUAL_REGENERATION_MARKER = "Revise the existing creative with this instruction:"
    VISUAL_REGENERATION_POLICY = (
        "Treat this as a fresh full visual regeneration that keeps the same topic and format while applying the revision."
    )
    VISUAL_TOPIC_STOPWORDS = {
        "a",
        "an",
        "and",
        "alternative",
        "analytical",
        "brand",
        "carousel",
        "conversational",
        "create",
        "creative",
        "draft",
        "for",
        "friend",
        "generate",
        "indian",
        "informed",
        "intelligent",
        "investments",
        "length",
        "like",
        "linkedin",
        "not",
        "platform",
        "post",
        "scannable",
        "short",
        "signed",
        "slide",
        "slides",
        "swipe",
        "that",
        "the",
        "this",
        "tone",
        "visual",
        "well",
        "write",
    }
    VISUAL_FOLLOW_UP_REFERENCE_PATTERN = re.compile(
        r"\b(?:make|turn|convert|repurpose|use|reuse|revise|rewrite|edit|change|rework|improve)\s+(?:it|this|that)\b"
        r"|\b(?:this|that|same|previous|earlier|last)\s+(?:one|creative|design|post|layout|format|version|carousel|slide)\b",
        re.IGNORECASE,
    )
    FRESH_VISUAL_PROMPT_PATTERN = re.compile(
        r"^(?:write|create|generate|design|draft|prepare|make)\b",
        re.IGNORECASE,
    )
    VISUAL_WORKSPACE_FORMATS = {"static", "carousel", "infographic"}
    VISUAL_TEXT_DELIVERABLE_OVERRIDES = {"linkedin_post", "instagram_caption", "social_caption", "x_post"}

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sessions = SessionRepository(session)
        self.messages = ChatMessageRepository(session)
        self.contents = ContentRepository(session)
        self.assets = AssetRepository(session)
        self.brands = BrandSpaceRepository(session)
        self.brand_sections = BrandSectionRepository(session)
        self.content = ContentService(session)
        self.conversation = ConversationService()
        self.evaluation = EvaluationService(session)
        self.intent_router = IntentRouterService()
        self.mixed_workflow = MixedWorkflowService()
        self.artifacts = ArtifactStateService()
        self.text_content = TextContentService(session)
        self.delivery = AssetDeliveryService()
        self.memory = ConversationMemoryService(session)
        self.brand_summary_memory = BrandSummaryMemoryService()

    @staticmethod
    def _generation_inheritance_policy(
        *,
        request_mode: str,
        inherit_persona: bool | None = None,
        inherit_objective: bool | None = None,
        inherit_template: bool | None = None,
        inherit_reference_assets: bool | None = None,
        inherit_copy_context: bool | None = None,
        inherit_layout_context: bool | None = None,
    ) -> RequestInheritancePolicy:
        normalized_mode = str(request_mode or "").strip().casefold()
        inherit_previous_defaults = normalized_mode in {"modify_previous", "variant_of_previous"}
        return RequestInheritancePolicy(
            inherit_persona=inherit_persona if inherit_persona is not None else inherit_previous_defaults,
            inherit_objective=inherit_objective if inherit_objective is not None else inherit_previous_defaults,
            inherit_template=inherit_template if inherit_template is not None else inherit_previous_defaults,
            inherit_reference_assets=inherit_reference_assets if inherit_reference_assets is not None else inherit_previous_defaults,
            inherit_copy_context=inherit_copy_context if inherit_copy_context is not None else inherit_previous_defaults,
            inherit_layout_context=inherit_layout_context if inherit_layout_context is not None else inherit_previous_defaults,
        )

    async def create_session(
        self,
        tenant_id: UUID,
        brand_space_id: UUID,
        user_id: UUID,
        payload: ChatSessionCreateRequest,
    ) -> ContentSession:
        brand = await self.brands.get_scoped(tenant_id, brand_space_id)
        if not brand:
            raise NotFoundError("Brand Space not found")
        if brand.lifecycle_state != BrandSpaceLifecycle.ACTIVE:
            raise LifecycleError("Brand Space must be Active for chat")

        # Truncate title to fit database column (VARCHAR(255))
        title = payload.title or "Chat Session"
        if len(title) > 255:
            title = title[:252] + "..."

        session = ContentSession(
            tenant_id=tenant_id,
            brand_space_id=brand_space_id,
            user_id=user_id,
            title=title,
            session_kind="chat",
            studio_panel=payload.studio_panel.model_dump(),
            conversational_context={"message_count": 0},
        )
        await self.sessions.add(session)
        await self.session.commit()
        return session

    async def list_sessions(self, tenant_id: UUID, brand_space_id: UUID) -> list[ContentSession]:
        return await self.sessions.list_by_brand(brand_space_id, session_kind="chat", tenant_id=tenant_id)

    async def get_session(self, session_id: UUID, tenant_id: UUID | None = None, brand_space_id: UUID | None = None) -> ContentSession:
        session = await self.sessions.get(session_id)
        if not session:
            raise NotFoundError("Chat session not found")
        if tenant_id and session.tenant_id != tenant_id:
            raise NotFoundError("Chat session not found")
        if brand_space_id and session.brand_space_id != brand_space_id:
            raise NotFoundError("Chat session not found")
        return session

    async def list_messages(self, session_id: UUID) -> list[ChatMessage]:
        session = await self.get_session(session_id)
        items = await self.messages.list_recent_by_session(session_id, limit=CHAT_HISTORY_MESSAGE_LIMIT)
        if await self.backfill_content_history_messages(session, items):
            await self.session.commit()
            items = await self.messages.list_recent_by_session(session_id, limit=CHAT_HISTORY_MESSAGE_LIMIT)
        for item in items:
            item.structured_payload = self.decorate_structured_payload_assets(item.structured_payload or {})
        return items

    async def backfill_content_history_messages(
        self,
        session: ContentSession,
        existing_messages: list[ChatMessage],
    ) -> bool:
        existing_content_ids = {
            item.content_version_id
            for item in existing_messages
            if item.role == "assistant" and item.content_version_id
        }
        content_versions = await self.contents.list_by_session(session.id, tenant_id=session.tenant_id)
        missing_versions = [
            content
            for content in reversed(content_versions)
            if content.id not in existing_content_ids
        ]
        if not missing_versions:
            return False

        for content_version in missing_versions:
            content_assets = await self.assets.list_by_content(content_version.id)
            serialized_assets = [self.serialize_asset(asset) for asset in content_assets]
            user_created_at = content_version.created_at
            assistant_created_at = content_version.created_at + timedelta(milliseconds=1)
            await self.messages.add(
                ChatMessage(
                    tenant_id=session.tenant_id,
                    brand_space_id=session.brand_space_id,
                    session_id=session.id,
                    user_id=content_version.created_by,
                    role="user",
                    message_text=content_version.prompt,
                    structured_payload={"studio_panel": content_version.studio_panel or {}},
                    citations=[],
                    created_at=user_created_at,
                    updated_at=user_created_at,
                )
            )
            await self.messages.add(
                ChatMessage(
                    tenant_id=session.tenant_id,
                    brand_space_id=session.brand_space_id,
                    session_id=session.id,
                    user_id=None,
                    content_version_id=content_version.id,
                    role="assistant",
                    message_text=self.build_assistant_message_text(content_version.generated_payload or {}),
                    structured_payload=self.build_content_history_payload(content_version, serialized_assets),
                    citations=self.make_json_safe(self.build_citations(content_version.explainability_metadata or {})),
                    created_at=assistant_created_at,
                    updated_at=assistant_created_at,
                )
            )
        return True

    async def send_message(
        self,
        tenant_id: UUID,
        brand_space_id: UUID,
        user_id: UUID,
        session_id: UUID,
        payload: ChatMessageCreateRequest,
    ) -> tuple[ChatMessage, ChatMessage]:
        session = await self.get_session(session_id, tenant_id=tenant_id, brand_space_id=brand_space_id)
        studio_panel = self._resolve_studio_panel(payload, session)
        brand = await self.brands.get_scoped(tenant_id, brand_space_id)
        brand_name = getattr(brand, "name", None)
        intent = self.intent_router.route(payload.message, session.conversational_context)
        if self._should_override_text_intent_to_visual(intent=intent, payload=payload, studio_panel=studio_panel):
            intent = ChatIntentDecision(
                mode="visual_generation",
                deliverable_type=intent.deliverable_type,
                reason="explicit_visual_panel_override",
                uses_previous_output=False,
            )
        logger.info(
            "chat.send_message.intent session_id=%s mode=%s reason=%s uses_previous_output=%s last_response_mode=%s last_content_version_id=%s revision_scope=%s workflow_type=%s",
            session.id,
            intent.mode,
            intent.reason,
            intent.uses_previous_output,
            (session.conversational_context or {}).get("last_response_mode"),
            (session.conversational_context or {}).get("last_content_version_id"),
            intent.revision_scope or {},
            (intent.workflow_plan or {}).get("type"),
        )
        mixed_workflow = getattr(self, "mixed_workflow", MixedWorkflowService())
        artifact_service = getattr(self, "artifacts", ArtifactStateService())
        evaluation_service = getattr(self, "evaluation", getattr(self, "text_content", None))
        user_message = ChatMessage(
            tenant_id=tenant_id,
            brand_space_id=brand_space_id,
            session_id=session.id,
            user_id=user_id,
            role="user",
            message_text=payload.message,
            structured_payload={
                "studio_panel": studio_panel.model_dump(),
                "intent_mode": intent.mode,
                "intent_reason": intent.reason,
                "display_retrieved_asset": intent.display_retrieved_asset,
                "revision_scope": intent.revision_scope,
                "workflow_plan": intent.workflow_plan,
                "workflow_state": None,
            },
            citations=[],
        )
        await self.messages.add(user_message)
        memory_service = getattr(self, "memory", None)
        content_version = None
        memory_assets: list[GeneratedAsset | dict[str, Any]] = []
        review_result = None
        workflow_context = None

        try:
            if intent.mode in {"small_talk", "strategy_chat"}:
                if intent.mode == "small_talk" and intent.direct_reply:
                    conversation = {
                        "message_text": intent.direct_reply,
                        "structured_payload": {
                            "mode": "conversation",
                            "conversation_mode": "small_talk",
                            "brand_name": brand_name,
                            "reply_source": "intent_router",
                        },
                    }
                else:
                    recent_messages = await self.messages.list_recent_by_session(session.id, limit=3)
                    brand_summary_service = getattr(self, "brand_summary_memory", None)
                    if brand_summary_service is None:
                        brand_summary_service = BrandSummaryMemoryService()
                    brand_sections_repository = getattr(self, "brand_sections", None)
                    brand_sections = (
                        await brand_sections_repository.list_current_sections(brand_space_id, tenant_id)
                        if brand is not None and brand_sections_repository is not None
                        else []
                    )
                    brand_summary = (
                        brand_summary_service.retrieve_brand_summary(
                            brand=brand,
                            query=payload.message,
                            sections=brand_sections,
                        )
                        if brand is not None
                        else ""
                    )
                    conversation = self.conversation.reply(
                        message=payload.message,
                        brand_name=brand_name,
                        brand_summary=brand_summary,
                        recent_messages=self._recent_conversation_messages(recent_messages),
                        mode=intent.mode,
                    )
                assistant_message = ChatMessage(
                    tenant_id=tenant_id,
                    brand_space_id=brand_space_id,
                    session_id=session.id,
                    user_id=None,
                    role="assistant",
                    message_text=conversation["message_text"],
                    structured_payload=self.make_json_safe(conversation["structured_payload"]),
                    citations=[],
                )
            elif intent.mode == "evaluation":
                evaluation = await evaluation_service.evaluate(
                    tenant_id=tenant_id,
                    brand_space_id=brand_space_id,
                    session=session,
                    prompt=payload.message,
                    persona_id=payload.persona_id,
                    objective_id=payload.objective_id,
                    reference_asset_ids=payload.reference_asset_ids,
                )
                assistant_message = ChatMessage(
                    tenant_id=tenant_id,
                    brand_space_id=brand_space_id,
                    session_id=session.id,
                    user_id=None,
                    role="assistant",
                    message_text=str(evaluation.get("summary") or "").strip() or "Evaluation complete.",
                    structured_payload=self.make_json_safe(evaluation),
                    citations=[],
                )
            elif intent.mode == "retrieval":
                backfilled_visual_state = None
                if memory_service is not None:
                    backfilled_visual_state = await self._backfill_displayed_asset_memory_from_history(
                        tenant_id=tenant_id,
                        brand_space_id=brand_space_id,
                        session=session,
                        memory_service=memory_service,
                    )
                if backfilled_visual_state:
                    generated_asset_memory = self._updated_generated_asset_memory(
                        session.conversational_context.get("generated_asset_memory"),
                        visual_memory_state=backfilled_visual_state,
                    )
                    session.conversational_context = {
                        **session.conversational_context,
                        "last_generated_visual": backfilled_visual_state,
                        "last_generated_visual_type": backfilled_visual_state.get("format"),
                        "last_generated_visuals_by_format": self._updated_visuals_by_format(
                            session.conversational_context.get("last_generated_visuals_by_format"),
                            visual_memory_state=backfilled_visual_state,
                        ),
                        "generated_asset_memory": generated_asset_memory,
                        "last_generated_static_image": generated_asset_memory.get("static"),
                        "last_generated_infographic": generated_asset_memory.get("infographic"),
                        "last_generated_carousel": generated_asset_memory.get("carousel"),
                    }
                retrieval_result = (
                    await memory_service.retrieve_image_assets(
                        tenant_id=tenant_id,
                        brand_space_id=brand_space_id,
                        session_id=session.id,
                        query=payload.message,
                        session_context=session.conversational_context,
                    )
                    if memory_service is not None
                    else {
                        "status": "not_found",
                        "message": "Conversation memory is not available yet for image retrieval.",
                        "assets": [],
                        "matched_entries": [],
                    }
                )
                assistant_message = ChatMessage(
                    tenant_id=tenant_id,
                    brand_space_id=brand_space_id,
                    session_id=session.id,
                    user_id=None,
                    role="assistant",
                    message_text=str(retrieval_result.get("message") or "").strip() or "I couldn't find a matching image yet.",
                    structured_payload=self.make_json_safe(
                        {
                            "mode": "retrieval",
                            "retrieval_type": "generated_image",
                            "retrieval_status": retrieval_result.get("status", "not_found"),
                            "assets": retrieval_result.get("assets", []) if intent.display_retrieved_asset else [],
                            "matched_entries": retrieval_result.get("matched_entries", []),
                            "selected_asset": retrieval_result.get("selected_asset") if intent.display_retrieved_asset else None,
                            "selection_required": retrieval_result.get("selection_required", False) if intent.display_retrieved_asset else False,
                            "selection_prompt": retrieval_result.get("selection_prompt") if intent.display_retrieved_asset else None,
                            "selection_options": retrieval_result.get("selection_options", []) if intent.display_retrieved_asset else [],
                            "display_retrieved_asset": intent.display_retrieved_asset,
                        }
                    ),
                    citations=[],
                )
            elif intent.mode == "content_only":
                workflow_plan = intent.workflow_plan or {}
                if workflow_plan.get("type") == "review_then_generate":
                    review_result = await evaluation_service.evaluate(
                        tenant_id=tenant_id,
                        brand_space_id=brand_space_id,
                        session=session,
                        prompt=payload.message,
                        persona_id=payload.persona_id,
                        objective_id=payload.objective_id,
                        reference_asset_ids=payload.reference_asset_ids,
                    )
                workflow_context = mixed_workflow.prepare_generation_context(
                    message=payload.message,
                    workflow_plan=workflow_plan,
                    session_context=session.conversational_context,
                    review_result=review_result,
                    reference_asset_ids=payload.reference_asset_ids,
                )
                user_message.structured_payload["workflow_state"] = workflow_context.workflow_state
                previous_content_version_id = self._last_content_version_id(session)
                if intent.uses_previous_output and previous_content_version_id:
                    logger.info(
                        "chat.send_message.text_rewrite session_id=%s previous_content_version_id=%s deliverable_type=%s",
                        session.id,
                        previous_content_version_id,
                        intent.deliverable_type,
                    )
                    text_result = await self.text_content.rewrite(
                        tenant_id=tenant_id,
                        brand_space_id=brand_space_id,
                        user_id=user_id,
                        session=session,
                        content_version_id=previous_content_version_id,
                        rewrite_instruction=workflow_context.prompt if workflow_context else payload.message,
                        studio_panel=studio_panel,
                        revision_scope=intent.revision_scope,
                    )
                else:
                    logger.info(
                        "chat.send_message.text_generate session_id=%s deliverable_type=%s prompt_length=%s",
                        session.id,
                        intent.deliverable_type,
                        len((workflow_context.prompt if workflow_context else payload.message) or ""),
                    )
                    text_result = await self.text_content.generate(
                        tenant_id=tenant_id,
                        brand_space_id=brand_space_id,
                        user_id=user_id,
                        session=session,
                        prompt=workflow_context.prompt if workflow_context else payload.message,
                        studio_panel=studio_panel,
                        persona_id=payload.persona_id,
                        objective_id=payload.objective_id,
                        deliverable_type=intent.deliverable_type,
                        uses_previous_output=intent.uses_previous_output,
                    )
                content_version = text_result.content_version
                assistant_message = ChatMessage(
                    tenant_id=tenant_id,
                    brand_space_id=brand_space_id,
                    session_id=session.id,
                    user_id=None,
                    content_version_id=content_version.id,
                    role="assistant",
                    message_text=text_result.assistant_text,
                    structured_payload=self.make_json_safe(text_result.assistant_payload),
                    citations=self.make_json_safe(self.build_citations(content_version.explainability_metadata)),
                )
                if workflow_context and workflow_context.workflow_state:
                    assistant_message.structured_payload["workflow_state"] = workflow_context.workflow_state
            else:
                workflow_plan = intent.workflow_plan or {}
                if workflow_plan.get("type") == "review_then_generate":
                    review_result = await evaluation_service.evaluate(
                        tenant_id=tenant_id,
                        brand_space_id=brand_space_id,
                        session=session,
                        prompt=payload.message,
                        persona_id=payload.persona_id,
                        objective_id=payload.objective_id,
                        reference_asset_ids=payload.reference_asset_ids,
                    )
                workflow_context = mixed_workflow.prepare_generation_context(
                    message=payload.message,
                    workflow_plan=workflow_plan,
                    session_context=session.conversational_context,
                    review_result=review_result,
                    reference_asset_ids=payload.reference_asset_ids,
                )
                user_message.structured_payload["workflow_state"] = workflow_context.workflow_state
                previous_content_version_id = self._last_content_version_id(session)
                if intent.uses_previous_output and previous_content_version_id:
                    contents_repo = getattr(self, "contents", None)
                    previous_content = (
                        await contents_repo.get_scoped(
                            previous_content_version_id,
                            tenant_id,
                            brand_space_id,
                        )
                        if contents_repo is not None
                        else None
                    )
                    instruction_prompt = workflow_context.prompt if workflow_context else payload.message
                    should_treat_as_fresh_generation = self._looks_like_distinct_new_visual_topic(
                        previous_content,
                        instruction_prompt,
                        revision_scope=intent.revision_scope,
                    )
                    if should_treat_as_fresh_generation:
                        logger.info(
                            "chat.send_message.visual_follow_up_reset_to_new_topic session_id=%s previous_content_version_id=%s studio_format=%s file_type=%s",
                            session.id,
                            previous_content_version_id,
                            studio_panel.format,
                            studio_panel.file_type,
                        )
                        content_version = await self.content.generate(
                            tenant_id=tenant_id,
                            brand_space_id=brand_space_id,
                            user_id=user_id,
                            payload=ContentGenerateRequest(
                                prompt=instruction_prompt,
                                raw_user_prompt=payload.message,
                                session_id=session.id,
                                persona_id=payload.persona_id,
                                objective_id=payload.objective_id,
                                template_id=payload.template_id,
                                request_mode="new_content",
                                inheritance_policy=self._generation_inheritance_policy(request_mode="new_content"),
                                studio_panel=studio_panel,
                                generate_image=payload.generate_image,
                                reference_asset_ids=workflow_context.reference_asset_ids if workflow_context else payload.reference_asset_ids,
                            ),
                        )
                    elif self._should_regenerate_visual_follow_up(intent.revision_scope):
                        regenerated_prompt = self._compose_visual_regeneration_prompt(
                            previous_content,
                            instruction_prompt,
                        )
                        logger.info(
                            "chat.send_message.visual_regenerate_from_follow_up session_id=%s previous_content_version_id=%s studio_format=%s file_type=%s",
                            session.id,
                            previous_content_version_id,
                            studio_panel.format,
                            studio_panel.file_type,
                        )
                        content_version = await self.content.generate(
                            tenant_id=tenant_id,
                            brand_space_id=brand_space_id,
                            user_id=user_id,
                            payload=ContentGenerateRequest(
                                prompt=regenerated_prompt,
                                raw_user_prompt=payload.message,
                                rewrite_instruction=instruction_prompt,
                                source_prompt_snapshot=self._base_visual_prompt(previous_content.prompt) if previous_content else None,
                                session_id=session.id,
                                persona_id=payload.persona_id,
                                objective_id=payload.objective_id,
                                template_id=previous_content.selected_template_id if previous_content else payload.template_id,
                                request_mode="variant_of_previous",
                                source_content_version_id=previous_content_version_id,
                                inheritance_policy=self._generation_inheritance_policy(
                                    request_mode="variant_of_previous",
                                    inherit_template=True,
                                ),
                                studio_panel=studio_panel,
                                generate_image=payload.generate_image,
                            ),
                        )
                    else:
                        logger.info(
                            "chat.send_message.visual_rewrite session_id=%s previous_content_version_id=%s studio_format=%s file_type=%s",
                            session.id,
                            previous_content_version_id,
                            studio_panel.format,
                            studio_panel.file_type,
                        )
                        content_version = await self.content.rewrite(
                            tenant_id=tenant_id,
                            brand_space_id=brand_space_id,
                            user_id=user_id,
                            payload=ContentRewriteRequest(
                                content_version_id=previous_content_version_id,
                                rewrite_instruction=workflow_context.prompt if workflow_context else payload.message,
                                studio_panel=studio_panel,
                                revision_scope=intent.revision_scope,
                            ),
                        )
                else:
                    logger.info(
                        "chat.send_message.visual_generate session_id=%s studio_format=%s file_type=%s generate_image=%s prompt_length=%s",
                        session.id,
                        studio_panel.format,
                        studio_panel.file_type,
                        payload.generate_image,
                        len((workflow_context.prompt if workflow_context else payload.message) or ""),
                    )
                    content_version = await self.content.generate(
                        tenant_id=tenant_id,
                        brand_space_id=brand_space_id,
                        user_id=user_id,
                        payload=ContentGenerateRequest(
                            prompt=workflow_context.prompt if workflow_context else payload.message,
                            raw_user_prompt=payload.message,
                            session_id=session.id,
                            persona_id=payload.persona_id,
                            objective_id=payload.objective_id,
                            template_id=payload.template_id,
                            request_mode="new_content",
                            inheritance_policy=self._generation_inheritance_policy(request_mode="new_content"),
                            studio_panel=studio_panel,
                            generate_image=payload.generate_image,
                            reference_asset_ids=workflow_context.reference_asset_ids if workflow_context else payload.reference_asset_ids,
                        ),
                    )
                render_payload = None
                should_export_visual = studio_panel.file_type != ExportFileType.DOC or (
                    str(studio_panel.format or "").strip().casefold() in self.VISUAL_WORKSPACE_FORMATS
                )
                if should_export_visual:
                    logger.info(
                        "chat.send_message.visual_export session_id=%s content_version_id=%s studio_format=%s file_type=%s",
                        session.id,
                        content_version.id,
                        studio_panel.format,
                        studio_panel.file_type,
                    )
                    render_payload = await self.content.export(
                        tenant_id=tenant_id,
                        brand_space_id=brand_space_id,
                        content_version_id=content_version.id,
                        studio_panel=studio_panel.model_dump(),
                    )
                content_assets = await self.assets.list_by_content(content_version.id)
                memory_assets = self._resolve_displayed_memory_assets(
                    content_assets=list(content_assets),
                    render_payload=render_payload,
                )
                serialized_assets = [self.serialize_asset(asset) for asset in content_assets]
                image_asset_count = len(
                    [
                        asset
                        for asset in content_assets
                        if str(asset.asset_role) == AssetRole.AI_IMAGE
                        or (asset.metadata_json or {}).get("render_source") == "ai"
                    ]
                )
                logger.info(
                    "chat.send_message.visual_result session_id=%s content_version_id=%s image_asset_count=%s render_preview=%s export_asset_count=%s",
                    session.id,
                    content_version.id,
                    image_asset_count,
                    bool(render_payload and render_payload.get("preview_asset")),
                    len((render_payload or {}).get("export_assets", [])),
                )
                assistant_text = self.build_assistant_message_text(content_version.generated_payload)
                raw_generation_decision = content_version.explainability_metadata.get("creative_decision", {}) or content_version.explainability_metadata.get("layout_decision", {})
                generation_decision = self.decorate_generation_decision(raw_generation_decision)
                assistant_payload = self.make_json_safe(
                    {
                        "mode": "visual_generation",
                        "content_version_id": str(content_version.id),
                        "generated_payload": content_version.generated_payload,
                        "generation_decision": generation_decision,
                        "repair_attempts": content_version.explainability_metadata.get("repair_attempts", 0),
                        "tone_feedback": content_version.tone_feedback,
                        "assets": serialized_assets,
                        "preview_asset": render_payload.get("preview_asset") if render_payload else None,
                        "export_assets": render_payload.get("export_assets", []) if render_payload else [],
                        "image_generation_requested": payload.generate_image,
                        "image_generation_status": "generated" if image_asset_count else "not_generated",
                        "image_asset_count": image_asset_count,
                        "workflow_type": workflow_context.workflow_type if workflow_context else None,
                        "workflow_state": workflow_context.workflow_state if workflow_context else None,
                        "workflow_review_summary": review_result.get("summary") if isinstance(review_result, dict) else None,
                        "artifact_state": (content_version.explainability_metadata or {}).get("artifact_state", {}),
                        "brand_scoring": (content_version.explainability_metadata or {}).get("brand_scoring", {}),
                    }
                )
                assistant_message = ChatMessage(
                    tenant_id=tenant_id,
                    brand_space_id=brand_space_id,
                    session_id=session.id,
                    user_id=None,
                    content_version_id=content_version.id,
                    role="assistant",
                    message_text=assistant_text,
                    structured_payload=assistant_payload,
                    citations=self.make_json_safe(self.build_citations(content_version.explainability_metadata)),
                )
        except (GenerationFailureError, GuardrailViolationError) as exc:
            assistant_text = self.build_generation_failure_message_text(exc)
            assistant_payload = self.make_json_safe(
                self.build_generation_failure_payload(
                    exc,
                    generate_image=payload.generate_image,
                    content_version_id=str(content_version.id) if content_version else None,
                )
            )
            assistant_message = ChatMessage(
                tenant_id=tenant_id,
                brand_space_id=brand_space_id,
                session_id=session.id,
                user_id=None,
                content_version_id=content_version.id if content_version else None,
                role="assistant",
                message_text=assistant_text,
                structured_payload=assistant_payload,
                citations=[],
            )
        await self.messages.add(assistant_message)
        if memory_service is not None:
            if content_version is not None:
                await memory_service.index_content_version_summary(
                    session=session,
                    content_version=content_version,
                )
                if memory_assets:
                    await memory_service.index_generated_assets(
                        session=session,
                        content_version=content_version,
                        assets=memory_assets,
                    )
        session.title = session.title or payload.message[:50]
        last_response_mode = str((assistant_message.structured_payload or {}).get("mode") or intent.mode).strip() or intent.mode
        preserve_previous_state = last_response_mode in {"evaluation", "retrieval"}
        last_text_output = None
        if last_response_mode == "content_only":
            last_text_output = assistant_message.message_text
        last_reviewed_asset_ids = None
        last_evaluation_summary = None
        last_evaluation_review_type = None
        last_evaluation_scope = None
        last_evaluation_score = None
        if last_response_mode == "evaluation":
            payload_data = assistant_message.structured_payload or {}
            last_reviewed_asset_ids = payload_data.get("reviewed_asset_ids")
            last_evaluation_summary = assistant_message.message_text
            last_evaluation_review_type = payload_data.get("review_type")
            last_evaluation_scope = payload_data.get("evaluation_scope")
            scorecard = payload_data.get("scorecard") if isinstance(payload_data.get("scorecard"), dict) else {}
            last_evaluation_score = scorecard.get("overall_score")
        session_artifact_state = artifact_service.build_session_state(
            session.conversational_context,
            content_artifact_state=(
                (assistant_message.structured_payload or {}).get("artifact_state")
                if isinstance((assistant_message.structured_payload or {}).get("artifact_state"), dict)
                else None
            ),
            evaluation_entry=artifact_service.build_evaluation_entry(assistant_message.structured_payload)
            if last_response_mode == "evaluation"
            else None,
        )
        visual_memory_state = (
            self._build_last_generated_visual_state(
                content_version=content_version,
                assets=memory_assets,
            )
            if content_version is not None and memory_assets and last_response_mode == "visual_generation"
            else None
        )
        last_generated_visuals_by_format = self._updated_visuals_by_format(
            session.conversational_context.get("last_generated_visuals_by_format"),
            visual_memory_state=visual_memory_state,
        )
        generated_asset_memory = self._updated_generated_asset_memory(
            session.conversational_context.get("generated_asset_memory"),
            visual_memory_state=visual_memory_state,
        )
        session.conversational_context = {
            **session.conversational_context,
            "message_count": int(session.conversational_context.get("message_count", 0)) + 2,
            "last_user_prompt": payload.message,
            "last_response_mode": last_response_mode,
            "last_non_evaluation_response_mode": (
                session.conversational_context.get("last_non_evaluation_response_mode")
                if preserve_previous_state
                else last_response_mode
            ),
            "last_text_output": last_text_output or session.conversational_context.get("last_text_output"),
            "last_non_evaluation_text_output": (
                session.conversational_context.get("last_non_evaluation_text_output")
                if preserve_previous_state
                else (last_text_output or session.conversational_context.get("last_non_evaluation_text_output"))
            ),
            "last_text_deliverable_type": (assistant_message.structured_payload or {}).get("deliverable_type") or session.conversational_context.get("last_text_deliverable_type"),
            "last_content_version_id": str(content_version.id) if content_version else session.conversational_context.get("last_content_version_id"),
            "last_non_evaluation_content_version_id": (
                session.conversational_context.get("last_non_evaluation_content_version_id")
                if preserve_previous_state
                else (str(content_version.id) if content_version else session.conversational_context.get("last_non_evaluation_content_version_id"))
            ),
            "last_evaluation_summary": last_evaluation_summary or session.conversational_context.get("last_evaluation_summary"),
            "last_evaluation_review_type": last_evaluation_review_type or session.conversational_context.get("last_evaluation_review_type"),
            "last_evaluation_scope": last_evaluation_scope or session.conversational_context.get("last_evaluation_scope"),
            "last_evaluation_score": last_evaluation_score if last_evaluation_score is not None else session.conversational_context.get("last_evaluation_score"),
            "last_reviewed_asset_ids": last_reviewed_asset_ids or session.conversational_context.get("last_reviewed_asset_ids"),
            "last_revision_scope": intent.revision_scope or session.conversational_context.get("last_revision_scope"),
            "last_workflow_state": (
                workflow_context.workflow_state
                if workflow_context and workflow_context.workflow_state
                else session.conversational_context.get("last_workflow_state")
            ),
            "artifact_state": session_artifact_state,
            "last_generated_visual": visual_memory_state
            or session.conversational_context.get("last_generated_visual"),
            "last_generated_visual_type": (
                visual_memory_state.get("format")
                if visual_memory_state
                else session.conversational_context.get("last_generated_visual_type")
            ),
            "last_generated_visuals_by_format": last_generated_visuals_by_format,
            "generated_asset_memory": generated_asset_memory,
            "last_generated_static_image": generated_asset_memory.get("static"),
            "last_generated_infographic": generated_asset_memory.get("infographic"),
            "last_generated_carousel": generated_asset_memory.get("carousel"),
            "last_displayed_asset_ids": (
                [
                    asset_id
                    for asset in memory_assets
                    if (asset_id := self._memory_asset_ref_id(asset))
                ]
                if memory_assets and last_response_mode == "visual_generation"
                else session.conversational_context.get("last_displayed_asset_ids")
            ),
            "last_displayed_asset_paths": (
                [
                    storage_path
                    for asset in memory_assets
                    if (storage_path := self._memory_asset_ref_storage_path(asset))
                ]
                if memory_assets and last_response_mode == "visual_generation"
                else session.conversational_context.get("last_displayed_asset_paths")
            ),
        }
        await self.session.commit()
        return user_message, assistant_message

    @staticmethod
    def _resolve_studio_panel(payload: ChatMessageCreateRequest, session: ContentSession) -> StudioPanelSelection:
        base = payload.studio_panel.model_dump() if payload.studio_panel else dict(session.studio_panel or {})
        resolved = resolve_studio_panel_defaults(base)
        return StudioPanelSelection.model_validate(resolved)

    @staticmethod
    def _recent_conversation_messages(messages: list[ChatMessage], *, limit: int = 3) -> list[dict[str, str]]:
        return [
            {
                "role": str(item.role),
                "message": " ".join(str(item.message_text or "").split()).strip(),
            }
            for item in messages[-limit:]
            if str(item.message_text or "").strip()
        ]

    @classmethod
    def _should_override_text_intent_to_visual(
        cls,
        *,
        intent: ChatIntentDecision,
        payload: ChatMessageCreateRequest,
        studio_panel: StudioPanelSelection,
    ) -> bool:
        if intent.mode != "content_only":
            return False
        if intent.uses_previous_output or intent.workflow_plan:
            return False
        if payload.studio_panel is None or not payload.generate_image:
            return False
        if str(studio_panel.format or "").strip().casefold() not in cls.VISUAL_WORKSPACE_FORMATS:
            return False
        return str(intent.deliverable_type or "").strip().casefold() in cls.VISUAL_TEXT_DELIVERABLE_OVERRIDES

    @staticmethod
    def build_assistant_message_text(generated_payload: dict) -> str:
        return "\n".join(
            [
                generated_payload.get("headline", ""),
                generated_payload.get("body", ""),
                generated_payload.get("cta", ""),
            ]
        ).strip()

    @staticmethod
    def _normalize_storage_path(value: str | None) -> str:
        return str(value or "").strip()

    @staticmethod
    def _memory_asset_ref_id(asset: GeneratedAsset | dict[str, Any]) -> str | None:
        if isinstance(asset, dict):
            asset_id = str(asset.get("asset_id") or "").strip()
            return asset_id or None
        return str(asset.id) if asset.id else None

    @classmethod
    def _memory_asset_ref_storage_path(cls, asset: GeneratedAsset | dict[str, Any]) -> str | None:
        if isinstance(asset, dict):
            storage_path = cls._normalize_storage_path(asset.get("storage_path"))
        else:
            storage_path = cls._normalize_storage_path(asset.storage_path)
        return storage_path or None

    @staticmethod
    def _compact_context_text(value: Any, *, limit: int = 500) -> str:
        text = " ".join(str(value or "").split()).strip()
        return text[:limit].rstrip(" ,.;:")

    @classmethod
    def _memory_asset_context_ref(cls, asset: GeneratedAsset | dict[str, Any]) -> dict[str, Any] | None:
        storage_path = cls._memory_asset_ref_storage_path(asset)
        if not storage_path:
            return None
        if isinstance(asset, dict):
            metadata = asset.get("metadata") if isinstance(asset.get("metadata"), dict) else {}
            metadata_json = asset.get("metadata_json") if isinstance(asset.get("metadata_json"), dict) else {}
            metadata = {**metadata_json, **metadata}
            return {
                "asset_id": str(asset.get("asset_id") or "").strip() or None,
                "storage_path": storage_path,
                "asset_role": cls._compact_context_text(asset.get("asset_role"), limit=80)
                or AssetRole.RENDER_EXPORT.value,
                "mime_type": cls._compact_context_text(asset.get("mime_type") or metadata.get("mime_type"), limit=80)
                or "image/png",
                "width": asset.get("width") or metadata.get("width"),
                "height": asset.get("height") or metadata.get("height"),
                "slide_index": asset.get("slide_index")
                or metadata.get("slide_index")
                or metadata.get("page_index")
                or metadata.get("page_number"),
                "slide_count": metadata.get("slide_count"),
            }
        metadata = asset.metadata_json or {}
        return {
            "asset_id": str(asset.id) if asset.id else None,
            "storage_path": storage_path,
            "asset_role": cls._compact_context_text(asset.asset_role, limit=80) or AssetRole.RENDER_EXPORT.value,
            "mime_type": cls._compact_context_text(asset.mime_type, limit=80) or "image/png",
            "width": asset.width,
            "height": asset.height,
            "slide_index": metadata.get("slide_index") or metadata.get("page_index") or metadata.get("page_number"),
            "slide_count": metadata.get("slide_count"),
        }

    @classmethod
    def _build_last_generated_visual_state(
        cls,
        *,
        content_version: Any,
        assets: list[GeneratedAsset | dict[str, Any]],
    ) -> dict[str, Any] | None:
        asset_refs = [
            asset_ref
            for asset in assets
            if (asset_ref := cls._memory_asset_context_ref(asset)) is not None
        ]
        if not asset_refs:
            return None
        payload = content_version.generated_payload or {}
        studio_panel = content_version.studio_panel or {}
        format_name = cls._compact_context_text(studio_panel.get("format"), limit=40)
        return {
            "content_version_id": str(content_version.id),
            "format": format_name,
            "platform": cls._compact_context_text(studio_panel.get("platform_preset"), limit=40),
            "file_type": cls._compact_context_text(studio_panel.get("file_type"), limit=40),
            "prompt": cls._compact_context_text(content_version.prompt, limit=500),
            "headline": cls._compact_context_text(payload.get("headline"), limit=220),
            "body": cls._compact_context_text(payload.get("body"), limit=420),
            "cta": cls._compact_context_text(payload.get("cta"), limit=160),
            "asset_count": len(asset_refs),
            "assets": asset_refs,
            "created_at": (
                content_version.created_at.isoformat()
                if getattr(content_version, "created_at", None) is not None
                else None
            ),
        }

    @staticmethod
    def _updated_visuals_by_format(
        existing: Any,
        *,
        visual_memory_state: dict[str, Any] | None,
    ) -> dict[str, Any]:
        visuals_by_format = dict(existing) if isinstance(existing, dict) else {}
        if not visual_memory_state:
            return visuals_by_format
        format_name = str(visual_memory_state.get("format") or "").strip().casefold()
        if format_name:
            visuals_by_format[format_name] = visual_memory_state
        return visuals_by_format

    @staticmethod
    def _visual_memory_format(value: dict[str, Any] | None) -> str:
        return str((value or {}).get("format") or "").strip().casefold()

    @classmethod
    def _updated_generated_asset_memory(
        cls,
        existing: Any,
        *,
        visual_memory_state: dict[str, Any] | None,
    ) -> dict[str, Any]:
        memory = dict(existing) if isinstance(existing, dict) else {}
        for key in ("static", "infographic", "carousel"):
            if key in memory and not isinstance(memory.get(key), dict):
                memory.pop(key, None)
        if not visual_memory_state:
            memory.setdefault("latest_type", cls._visual_memory_format(memory.get("latest")) or None)
            return memory

        format_name = cls._visual_memory_format(visual_memory_state)
        memory["latest"] = visual_memory_state
        memory["latest_type"] = format_name or None
        if format_name in {"static", "infographic", "carousel"}:
            memory[format_name] = visual_memory_state
        return memory

    async def _backfill_displayed_asset_memory_from_history(
        self,
        *,
        tenant_id: UUID,
        brand_space_id: UUID,
        session: ContentSession,
        memory_service: ConversationMemoryService,
    ) -> dict[str, Any] | None:
        messages = await self.messages.list_recent_by_session(session.id, limit=CHAT_HISTORY_MESSAGE_LIMIT)
        latest_visual_state: dict[str, Any] | None = None
        for message in messages:
            payload = message.structured_payload if isinstance(message.structured_payload, dict) else {}
            if payload.get("mode") != "visual_generation" or not message.content_version_id:
                continue
            render_payload = {
                "preview_asset": payload.get("preview_asset") if isinstance(payload.get("preview_asset"), dict) else None,
                "export_assets": payload.get("export_assets") if isinstance(payload.get("export_assets"), list) else [],
            }
            displayed_assets = self._resolve_displayed_memory_assets(
                content_assets=[],
                render_payload=render_payload,
            )
            if not displayed_assets:
                continue
            content_version = await self.contents.get_scoped(message.content_version_id, tenant_id, brand_space_id)
            if content_version is None:
                continue
            await memory_service.index_generated_assets(
                session=session,
                content_version=content_version,
                assets=displayed_assets,
            )
            latest_visual_state = self._build_last_generated_visual_state(
                content_version=content_version,
                assets=displayed_assets,
            )
        return latest_visual_state

    @classmethod
    def _resolve_displayed_memory_assets(
        cls,
        *,
        content_assets: list[GeneratedAsset],
        render_payload: dict | None,
    ) -> list[GeneratedAsset | dict[str, Any]]:
        asset_by_key: dict[tuple[str, str], GeneratedAsset] = {}
        asset_by_path: dict[str, GeneratedAsset] = {}
        for asset in content_assets:
            storage_path = cls._normalize_storage_path(asset.storage_path)
            if not storage_path:
                continue
            asset_by_key[(storage_path, str(asset.asset_role))] = asset
            asset_by_path.setdefault(storage_path, asset)

        def resolve_refs(refs: list[dict] | None) -> list[GeneratedAsset | dict[str, Any]]:
            resolved: list[GeneratedAsset | dict[str, Any]] = []
            seen_keys: set[tuple[str, str]] = set()
            for ref in refs or []:
                if not isinstance(ref, dict):
                    continue
                storage_path = cls._normalize_storage_path(ref.get("storage_path"))
                asset_role = str(ref.get("asset_role") or "")
                if not storage_path:
                    continue
                matched = asset_by_key.get((storage_path, asset_role)) or asset_by_path.get(storage_path)
                if matched is not None:
                    seen_key = ("asset", str(matched.id))
                    if seen_key in seen_keys:
                        continue
                    seen_keys.add(seen_key)
                    resolved.append(matched)
                    continue

                seen_key = ("path", f"{storage_path}:{asset_role}")
                if seen_key in seen_keys:
                    continue
                seen_keys.add(seen_key)
                resolved.append(
                    {
                        **ref,
                        "storage_path": storage_path,
                        "asset_role": asset_role,
                    }
                )
            return resolved

        def is_image_ref(asset: GeneratedAsset | dict[str, Any]) -> bool:
            if isinstance(asset, dict):
                return str(asset.get("mime_type") or "").startswith("image/")
            return str(asset.mime_type or "").startswith("image/")

        export_assets = resolve_refs(
            render_payload.get("export_assets")
            if isinstance(render_payload, dict) and isinstance(render_payload.get("export_assets"), list)
            else []
        )
        image_export_assets = [asset for asset in export_assets if is_image_ref(asset)]
        if image_export_assets:
            return image_export_assets

        preview_asset = resolve_refs(
            [render_payload.get("preview_asset")]
            if isinstance(render_payload, dict) and isinstance(render_payload.get("preview_asset"), dict)
            else []
        )
        if preview_asset:
            return preview_asset
        if export_assets:
            return export_assets

        render_exports = [
            asset
            for asset in content_assets
            if str(asset.mime_type or "").startswith("image/")
            and str(asset.asset_role) == AssetRole.RENDER_EXPORT.value
        ]
        if render_exports:
            return sorted(render_exports, key=lambda item: (item.created_at, str(item.id)))

        render_previews = [
            asset
            for asset in content_assets
            if str(asset.mime_type or "").startswith("image/")
            and str(asset.asset_role) == AssetRole.RENDER_PREVIEW.value
        ]
        if render_previews:
            return sorted(render_previews, key=lambda item: (item.created_at, str(item.id)))[:1]

        ai_images = [
            asset
            for asset in content_assets
            if str(asset.mime_type or "").startswith("image/")
            and str(asset.asset_role) == AssetRole.AI_IMAGE.value
        ]
        if ai_images:
            return sorted(ai_images, key=lambda item: (item.created_at, str(item.id)))

        return []

    @staticmethod
    def build_generation_failure_message_text(exc: Exception) -> str:
        if isinstance(exc, GenerationFailureError):
            return exc.user_safe_message
        if isinstance(exc, GuardrailViolationError):
            return f"I couldn't generate this because it conflicts with your brand rules: {str(exc)}"
        return "I couldn't generate the visual this time. Please regenerate."

    @staticmethod
    def build_generation_failure_payload(
        exc: Exception,
        *,
        generate_image: bool,
        content_version_id: str | None,
    ) -> dict:
        if isinstance(exc, GenerationFailureError):
            failure = exc.to_payload()
        elif isinstance(exc, GuardrailViolationError):
            failure = {
                "failure_type": "guardrail_conflict",
                "reason_code": "guardrail_violation",
                "reason_summary": str(exc),
                "user_safe_message": f"I couldn't generate this because it conflicts with your brand rules: {str(exc)}",
                "retryable": False,
                "rule_source": "brand",
                "suggested_next_action": "Adjust the request so it complies with the current brand and policy rules.",
                "details": {},
            }
        else:
            failure = {
                "failure_type": "provider_failure",
                "reason_code": "generation_failed",
                "reason_summary": str(exc),
                "user_safe_message": "I couldn't generate the visual this time. Please regenerate.",
                "retryable": True,
                "rule_source": "system",
                "suggested_next_action": "Regenerate the creative.",
                "details": {},
            }
        return {
            "content_version_id": content_version_id,
            "generation_status": "failed",
            "failure": failure,
            "image_generation_requested": generate_image,
            "image_generation_status": "failed" if generate_image else "not_requested",
            "can_regenerate": bool(failure.get("retryable")),
        }

    @classmethod
    def build_content_history_payload(cls, content_version, serialized_assets: list[dict]) -> dict:
        explainability = content_version.explainability_metadata or {}
        raw_generation_decision = explainability.get("creative_decision", {}) or explainability.get("layout_decision", {})
        image_asset_count = len(
            [
                asset
                for asset in serialized_assets
                if asset.get("asset_role") == AssetRole.AI_IMAGE
                or asset.get("asset_role") == AssetRole.RENDER_PREVIEW
                or asset.get("asset_role") == AssetRole.RENDER_EXPORT
            ]
        )
        return cls.make_json_safe(
            {
                "content_version_id": str(content_version.id),
                "generated_payload": content_version.generated_payload or {},
                "generation_decision": cls.decorate_generation_decision(raw_generation_decision),
                "repair_attempts": explainability.get("repair_attempts", 0),
                "tone_feedback": content_version.tone_feedback or {},
                "assets": serialized_assets,
                "preview_asset": None,
                "export_assets": [],
                "image_generation_requested": bool(image_asset_count),
                "image_generation_status": "generated" if image_asset_count else "not_generated",
                "image_asset_count": image_asset_count,
                "brand_scoring": explainability.get("brand_scoring", {}),
            }
        )

    @staticmethod
    def decorate_generation_decision(decision: dict | None) -> dict:
        if not isinstance(decision, dict):
            return {}
        payload = dict(decision)
        recommendations = [
            item
            for item in payload.get("template_recommendations", []) or []
            if isinstance(item, dict)
        ]
        template_id = str(payload.get("template_id") or "").strip()
        template_name = str(payload.get("template_name") or "").strip()
        matched = next(
            (
                item
                for item in recommendations
                if str(item.get("template_id") or "").strip() == template_id
            ),
            None,
        )
        if matched is None and template_name:
            matched = next(
                (
                    item
                    for item in recommendations
                    if str(item.get("name") or "").strip() == template_name
                ),
                None,
            )
        if matched is None and recommendations:
            matched = recommendations[0]
        if matched:
            if matched.get("asset_url") and not payload.get("template_preview_asset_url"):
                payload["template_preview_asset_url"] = matched.get("asset_url")
            if matched.get("decision_confidence") is not None and payload.get("template_decision_confidence") is None:
                payload["template_decision_confidence"] = matched.get("decision_confidence")
        return payload

    @staticmethod
    def serialize_asset(asset: GeneratedAsset) -> dict:
        delivery = AssetDeliveryService()
        return {
            "asset_id": str(asset.id),
            "mime_type": asset.mime_type,
            "storage_path": asset.storage_path,
            "asset_url": delivery.build_signed_url(
                storage_path=asset.storage_path,
                filename=asset.storage_path.rsplit("/", 1)[-1],
            ),
            "width": asset.width,
            "height": asset.height,
            "asset_role": str(asset.asset_role),
        }

    @staticmethod
    def _decorate_asset_ref(asset: dict) -> dict:
        if not isinstance(asset, dict):
            return asset
        storage_path = str(asset.get("storage_path", "")).strip()
        if not storage_path:
            return asset
        storage = get_object_storage()
        if not storage.exists(storage_path):
            return {
                **asset,
                "asset_url": None,
            }
        delivery = AssetDeliveryService()
        return {
            **asset,
            "asset_url": delivery.build_signed_url(
                storage_path=storage_path,
                filename=storage_path.rsplit("/", 1)[-1],
            ),
        }

    @classmethod
    def decorate_structured_payload_assets(cls, payload: dict) -> dict:
        if not isinstance(payload, dict):
            return payload
        decorated = dict(payload)
        for heavy_key in (
            "blueprint_payload",
            "creative_decision",
            "scene_graph",
            "validation_report",
            "renderer_metadata",
        ):
            decorated.pop(heavy_key, None)
        if isinstance(decorated.get("preview_asset"), dict):
            preview_asset = cls._decorate_asset_ref(decorated["preview_asset"])
            decorated["preview_asset"] = preview_asset if preview_asset.get("asset_url") else None
        if isinstance(decorated.get("assets"), list):
            decorated["assets"] = [
                refreshed
                for asset in decorated["assets"]
                if isinstance(asset, dict)
                for refreshed in [cls._decorate_asset_ref(asset)]
                if refreshed.get("asset_url")
            ]
        if isinstance(decorated.get("export_assets"), list):
            decorated["export_assets"] = [
                refreshed
                for asset in decorated["export_assets"]
                if isinstance(asset, dict)
                for refreshed in [cls._decorate_asset_ref(asset)]
                if refreshed.get("asset_url")
            ]
        return decorated

    @staticmethod
    def make_json_safe(value):
        return jsonable_encoder(value)

    @staticmethod
    def build_citations(explainability_metadata: dict) -> list[dict]:
        return [
            {"channel": channel}
            for channel in explainability_metadata.get("retrieval_channels", [])
        ]

    @staticmethod
    def _last_content_version_id(session: ContentSession) -> UUID | None:
        raw_value = (session.conversational_context or {}).get("last_content_version_id")
        try:
            return UUID(str(raw_value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _should_regenerate_visual_follow_up(revision_scope: dict[str, object] | None) -> bool:
        if not isinstance(revision_scope, dict):
            return False
        targeted_fields = {
            str(value).strip().casefold()
            for value in (revision_scope.get("targeted_fields") or [])
            if str(value).strip()
        }
        has_slide_targets = bool(revision_scope.get("slide_indexes") or revision_scope.get("slide_targets"))
        if has_slide_targets:
            return False
        if bool(revision_scope.get("preserve_visuals")) or bool(revision_scope.get("preserve_copy")):
            return False
        if targeted_fields and targeted_fields.issubset({"cta", "hashtags"}):
            return False
        if targeted_fields and {"headline", "body"} & targeted_fields:
            return True
        return bool(
            revision_scope.get("change_tone")
            or revision_scope.get("change_layout")
            or not revision_scope.get("only_targeted")
        )

    @classmethod
    def _base_visual_prompt(cls, prompt: str | None) -> str:
        text = str(prompt or "").strip()
        if not text:
            return ""
        if cls.VISUAL_REGENERATION_MARKER not in text:
            return text
        return text.split(cls.VISUAL_REGENERATION_MARKER, 1)[0].strip()

    @classmethod
    def _topic_tokens(cls, text: str | None) -> set[str]:
        tokens = {
            token
            for token in re.findall(r"[a-z0-9']+", str(text or "").casefold())
            if len(token) > 2 and token not in cls.VISUAL_TOPIC_STOPWORDS
        }
        return tokens

    @classmethod
    def _looks_like_distinct_new_visual_topic(
        cls,
        previous_content: ContentVersion | None,
        follow_up_instruction: str,
        *,
        revision_scope: dict[str, object] | None = None,
    ) -> bool:
        instruction = str(follow_up_instruction or "").strip()
        if previous_content is None or not instruction:
            return False
        if not cls.FRESH_VISUAL_PROMPT_PATTERN.match(instruction):
            return False
        instruction_token_count = len(re.findall(r"[a-z0-9']+", instruction.casefold()))
        if instruction_token_count >= 18:
            return True
        if cls.VISUAL_FOLLOW_UP_REFERENCE_PATTERN.search(instruction):
            return False
        if isinstance(revision_scope, dict):
            if revision_scope.get("slide_indexes") or revision_scope.get("slide_targets"):
                return False
            if revision_scope.get("preserve_visuals") or revision_scope.get("preserve_copy"):
                return False
            if revision_scope.get("targeted_fields"):
                return False
        previous_prompt = cls._base_visual_prompt(previous_content.prompt)
        previous_payload = previous_content.generated_payload if isinstance(previous_content.generated_payload, dict) else {}
        prior_context = " ".join(
            part
            for part in [
                previous_prompt,
                str(previous_payload.get("headline") or "").strip(),
                str(previous_payload.get("body") or "").strip(),
            ]
            if part
        )
        current_tokens = cls._topic_tokens(instruction)
        previous_tokens = cls._topic_tokens(prior_context)
        if len(current_tokens) < 4 or not previous_tokens:
            return False
        overlap = current_tokens & previous_tokens
        if not overlap:
            return True
        overlap_ratio = len(overlap) / max(len(current_tokens), 1)
        return overlap_ratio <= 0.2 and len(current_tokens - overlap) >= 4

    @classmethod
    def _compose_visual_regeneration_prompt(
        cls,
        previous_content: ContentVersion | None,
        follow_up_instruction: str,
    ) -> str:
        instruction = str(follow_up_instruction or "").strip()
        if previous_content is None:
            return instruction
        previous_prompt = cls._base_visual_prompt(previous_content.prompt)
        if not previous_prompt:
            return instruction
        return (
            f"{previous_prompt}\n\n"
            f"{cls.VISUAL_REGENERATION_MARKER} {instruction}\n"
            f"{cls.VISUAL_REGENERATION_POLICY}"
        ).strip()
