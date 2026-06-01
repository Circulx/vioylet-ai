from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from app.ai.providers.base import PromptEnvelope
from app.ai.providers.router import ProviderRouter


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ChatIntentDecision:
    mode: str
    deliverable_type: str | None = None
    reason: str = ""
    uses_previous_output: bool = False
    revision_scope: dict[str, Any] | None = None
    workflow_plan: dict[str, Any] | None = None
    display_retrieved_asset: bool = False


class IntentRouterService:
    _LLM_ALLOWED_MODES = {
        "small_talk",
        "strategy_chat",
        "content_only",
        "visual_generation",
        "evaluation",
        "retrieval",
    }
    _LLM_ALLOWED_DELIVERABLE_TYPES = {
        "blog",
        "linkedin_post",
        "instagram_caption",
        "social_caption",
        "x_post",
        "x_thread",
        "youtube_description",
        "newsletter",
        "email",
        "script",
        "long_description",
        "general_copy",
    }
    _LLM_ALLOWED_WORKFLOW_TYPES = {
        "review_then_generate",
        "repurpose_text_to_visual",
        "apply_last_review",
    }
    _LLM_ALLOWED_TARGET_FIELDS = {
        "headline",
        "body",
        "cta",
        "hashtags",
        "layout",
        "visuals",
    }
    _LLM_ALLOWED_SLIDE_TARGETS = {"cover", "last"}
    _LLM_CONFIDENCE_THRESHOLD = 0.7

    def __init__(self) -> None:
        self.providers = ProviderRouter()

    def route(self, message: str, session_context: dict[str, Any] | None = None) -> ChatIntentDecision:
        text = " ".join(str(message or "").split()).strip()
        session_context = session_context or {}
        if not text:
            return ChatIntentDecision(mode="small_talk", reason="empty_message")

        llm_decision = self._classify_with_llm(
            text=text,
            session_context=session_context,
        )
        if llm_decision is None:
            return ChatIntentDecision(
                mode="content_only",
                deliverable_type="general_copy",
                reason="emergency_default_content",
            )
        return self._build_decision_from_llm(llm_decision=llm_decision)

    def _classify_with_llm(
        self,
        *,
        text: str,
        session_context: dict[str, Any],
    ) -> dict[str, Any] | None:
        provider = self.providers.get_text_provider("generation")
        fallback = {
            "mode": "content_only",
            "confidence": 0.0,
            "reason": "provider_unavailable",
            "deliverable_type": None,
            "uses_previous_output": False,
            "workflow_type": None,
            "revision_scope": None,
            "display_retrieved_asset": False,
        }
        try:
            response = provider.generate_structured_json(
                PromptEnvelope(
                    system=(
                        "You classify the user's top-level intent for a content studio. "
                        "Return JSON only. "
                        "Pick exactly one mode from: small_talk, strategy_chat, content_only, visual_generation, evaluation, retrieval. "
                        "small_talk = greeting or lightweight casual chat. "
                        "strategy_chat = asking questions, brainstorming, advice, or discussion without requesting deliverable generation. "
                        "content_only = asking for written copy or text content generation. "
                        "visual_generation = asking for an image, creative, carousel, poster, infographic, banner, slides, or a visual deliverable. "
                        "evaluation = asking to review, check, assess, score, audit, or analyze existing content, tone, brand alignment, compliance, or consistency. "
                        "retrieval = asking to show, find, fetch, retrieve, display, or bring back something already created earlier in the conversation, especially an image or visual asset. "
                        "If the user is asking about a previously generated image or visual, including prompts like tell me about the last image, describe the previous visual, what is the earlier carousel about, or explain the generated image, classify it as retrieval, not evaluation. "
                        "Set display_retrieved_asset to true only when the user explicitly wants the old image shown again, such as show, display, open, fetch, retrieve, or bring back the image. "
                        "Set display_retrieved_asset to false when the user only wants to discuss, explain, describe, analyze, or answer questions about the previous image without re-showing it. "
                        "Infer deliverable_type when mode is content_only. "
                        "Infer uses_previous_output when the user is modifying, continuing, reusing, or referring to earlier output. "
                        "Infer workflow_type only when the prompt is clearly one of: review_then_generate, repurpose_text_to_visual, apply_last_review. Otherwise use null. "
                        "Infer revision_scope only when the prompt is editing previous content or visuals. Otherwise use null. "
                        "Allowed deliverable_type values: null, blog, linkedin_post, instagram_caption, social_caption, x_post, x_thread, youtube_description, newsletter, email, script, long_description, general_copy. "
                        "revision_scope must be either null or an object with keys: targeted_fields, slide_indexes, slide_targets, preserve_visuals, preserve_copy, change_layout, change_tone, only_targeted. "
                        "targeted_fields must be an array using only: headline, body, cta, hashtags, layout, visuals. "
                        "slide_targets must be an array using only: cover, last."
                    ),
                    user=(
                        f"Session context: {session_context}\n"
                        f"User message: {text}\n"
                        "Return a JSON object with keys: mode, confidence, reason, deliverable_type, uses_previous_output, workflow_type, revision_scope, display_retrieved_asset."
                    ),
                ),
                fallback=fallback,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("intent_router.llm_classification_failed: %s", exc)
            return None

        mode = str(response.get("mode") or "").strip().casefold()
        if mode not in self._LLM_ALLOWED_MODES:
            return None
        try:
            confidence = float(response.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        if confidence < self._LLM_CONFIDENCE_THRESHOLD:
            return None

        deliverable_type = str(response.get("deliverable_type") or "").strip() or None
        if deliverable_type and deliverable_type not in self._LLM_ALLOWED_DELIVERABLE_TYPES:
            deliverable_type = None
        workflow_type = str(response.get("workflow_type") or "").strip() or None
        if workflow_type and workflow_type not in self._LLM_ALLOWED_WORKFLOW_TYPES:
            workflow_type = None

        return {
            "mode": mode,
            "confidence": confidence,
            "reason": str(response.get("reason") or "").strip() or "llm_classification",
            "deliverable_type": deliverable_type,
            "uses_previous_output": bool(response.get("uses_previous_output")),
            "workflow_type": workflow_type,
            "revision_scope": self._normalize_revision_scope(response.get("revision_scope")),
            "display_retrieved_asset": bool(response.get("display_retrieved_asset")),
        }

    def _build_decision_from_llm(self, *, llm_decision: dict[str, Any]) -> ChatIntentDecision:
        mode = str(llm_decision.get("mode") or "").strip().casefold()
        workflow_type = str(llm_decision.get("workflow_type") or "").strip() or None
        uses_previous_output = bool(llm_decision.get("uses_previous_output"))
        return ChatIntentDecision(
            mode=mode,
            deliverable_type=str(llm_decision.get("deliverable_type") or "").strip() or None,
            reason=f"llm_selected:{str(llm_decision.get('reason') or 'llm_classification').strip()}",
            uses_previous_output=uses_previous_output,
            revision_scope=llm_decision.get("revision_scope"),
            workflow_plan=self._workflow_plan_from_llm(
                workflow_type=workflow_type,
                mode=mode,
                uses_previous_output=uses_previous_output,
            ),
            display_retrieved_asset=bool(llm_decision.get("display_retrieved_asset")),
        )

    def _normalize_revision_scope(self, value: Any) -> dict[str, Any] | None:
        if not isinstance(value, dict):
            return None

        targeted_fields = [
            str(item).strip()
            for item in value.get("targeted_fields", [])
            if str(item).strip() in self._LLM_ALLOWED_TARGET_FIELDS
        ]
        slide_indexes: list[int] = []
        for item in value.get("slide_indexes", []):
            try:
                normalized = int(item)
            except (TypeError, ValueError):
                continue
            if normalized > 0:
                slide_indexes.append(normalized)
        slide_targets = [
            str(item).strip()
            for item in value.get("slide_targets", [])
            if str(item).strip() in self._LLM_ALLOWED_SLIDE_TARGETS
        ]

        normalized_scope = {
            "targeted_fields": targeted_fields,
            "slide_indexes": sorted(set(slide_indexes)),
            "slide_targets": list(dict.fromkeys(slide_targets)),
            "preserve_visuals": bool(value.get("preserve_visuals")),
            "preserve_copy": bool(value.get("preserve_copy")),
            "change_layout": bool(value.get("change_layout")),
            "change_tone": bool(value.get("change_tone")),
            "only_targeted": bool(value.get("only_targeted")),
        }
        if any(
            [
                normalized_scope["targeted_fields"],
                normalized_scope["slide_indexes"],
                normalized_scope["slide_targets"],
                normalized_scope["preserve_visuals"],
                normalized_scope["preserve_copy"],
                normalized_scope["change_layout"],
                normalized_scope["change_tone"],
                normalized_scope["only_targeted"],
            ]
        ):
            return normalized_scope
        return None

    @staticmethod
    def _workflow_plan_from_llm(
        *,
        workflow_type: str | None,
        mode: str,
        uses_previous_output: bool,
    ) -> dict[str, Any] | None:
        normalized = str(workflow_type or "").strip()
        if not normalized:
            return None
        if normalized == "review_then_generate":
            return {
                "type": "review_then_generate",
                "target_mode": mode,
                "uses_previous_output": uses_previous_output,
                "reason": "llm_review_then_generate",
                "review_source": "reference_assets_or_previous",
                "apply_review_to_rewrite": uses_previous_output,
            }
        if normalized == "repurpose_text_to_visual":
            return {
                "type": "repurpose_text_to_visual",
                "target_mode": "visual_generation",
                "uses_previous_output": False,
                "reason": "llm_repurpose_text_to_visual",
            }
        if normalized == "apply_last_review":
            return {
                "type": "apply_last_review",
                "target_mode": mode,
                "uses_previous_output": True if not uses_previous_output else uses_previous_output,
                "reason": "llm_apply_last_review",
                "review_source": "last_evaluation",
            }
        return None
