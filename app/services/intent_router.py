from __future__ import annotations

from dataclasses import dataclass
import json
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
    direct_reply: str | None = None


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
    _SESSION_SUMMARY_KEYS = (
        "last_response_mode",
        "last_non_evaluation_response_mode",
        "last_content_version_id",
        "last_non_evaluation_content_version_id",
        "last_text_deliverable_type",
        "last_evaluation_review_type",
        "last_evaluation_scope",
        "last_displayed_asset_ids",
        "last_displayed_asset_paths",
        "last_generated_visual_type",
        "last_generated_visual",
        "last_generated_visuals_by_format",
        "generated_asset_memory",
        "last_generated_static_image",
        "last_generated_infographic",
        "last_generated_carousel",
        "last_workflow_state",
    )

    def __init__(self) -> None:
        self.providers = ProviderRouter()

    def route(self, message: str, session_context: dict[str, Any] | None = None) -> ChatIntentDecision:
        text = " ".join(str(message or "").split()).strip()
        session_context = session_context or {}
        if not text:
            return ChatIntentDecision(mode="small_talk", reason="empty_message")

        llm_decision = self._classify_with_llm(
            text=text,
            session_context=self._router_session_summary(session_context),
        )
        if llm_decision is None:
            return ChatIntentDecision(
                mode="strategy_chat",
                reason="llm_classification_unavailable",
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
            "mode": "strategy_chat",
            "confidence": 0.0,
            "reason": "provider_unavailable",
            "deliverable_type": None,
            "uses_previous_output": False,
            "workflow_type": None,
            "revision_scope": None,
            "display_retrieved_asset": False,
            "direct_reply": None,
        }
        try:
            response = provider.generate_structured_json(
                PromptEnvelope(
                    system=(
                        "You classify the user's top-level intent for a content studio. "
                        "Return JSON only. "
                        "Classify the current User message only. Session context is reference-only for resolving phrases like previous, last, this, or that; never infer a generation request from session context alone. "
                        "Pick exactly one mode from: small_talk, strategy_chat, content_only, visual_generation, evaluation, retrieval. "
                        "small_talk = greeting or lightweight casual chat. "
                        "strategy_chat = asking questions, brainstorming, advice, or discussion without requesting deliverable generation. "
                        "content_only = explicitly asking to write, draft, generate, create, prepare, rewrite, revise, edit, or improve written copy/text content such as a blog, article, caption, post, email, script, thread, newsletter, or description. "
                        "visual_generation = explicitly asking to generate, create, design, make, render, or revise an image, creative, carousel, poster, infographic, banner, slide deck, slides, or other visual deliverable. "
                        "evaluation = asking to review, check, assess, score, audit, or analyze existing content, tone, brand alignment, compliance, or consistency. "
                        "retrieval = asking to show, find, fetch, retrieve, display, or bring back something already created earlier in the conversation, especially an image or visual asset. "
                        "Do not classify a greeting, thanks, or casual one-line chat as content_only just because brand context exists. "
                        "Do not classify brand/audience questions as content_only unless the user asks for a written deliverable. "
                        "If the user explicitly asks for written content generation, classify as content_only with high confidence. "
                        "If the user explicitly asks for visual/image/carousel generation, classify as visual_generation with high confidence. "
                        "If uncertain between strategy_chat and content_only, choose strategy_chat unless the message contains an explicit writing/generation deliverable request. "
                        "If uncertain between small_talk and content_only, choose small_talk unless the message contains an explicit writing/generation deliverable request. "
                        "If the user is asking about a previously generated image or visual, including prompts like tell me about the last image, describe the previous visual, what is the earlier carousel about, or explain the generated image, classify it as retrieval, not evaluation. "
                        "If the user asks for the latest, last, previous, earlier, or same generated image/visual/carousel/static image/infographic/slide/asset, classify it as retrieval. "
                        "If the user asks to show the last generated static image, last generated infographic, or last generated carousel, classify it as retrieval with display_retrieved_asset true. "
                        "If the user asks to generate a new image/visual/carousel/slide/asset, classify it as visual_generation. "
                        "Set display_retrieved_asset to true only when the user explicitly wants the old image shown again, such as show, display, open, fetch, retrieve, or bring back the image. "
                        "Set display_retrieved_asset to false when the user only wants to discuss, explain, describe, analyze, or answer questions about the previous image without re-showing it. "
                        "Infer deliverable_type when mode is content_only. "
                        "Infer uses_previous_output when the user is modifying, continuing, reusing, or referring to earlier output. "
                        "Infer workflow_type only when the prompt is clearly one of: review_then_generate, repurpose_text_to_visual, apply_last_review. Otherwise use null. "
                        "Infer revision_scope only when the prompt is editing previous content or visuals. Otherwise use null. "
                        "For pure small_talk only, also return direct_reply with a concise natural assistant reply. "
                        "Pure small_talk means greetings, thanks, sign-offs, and lightweight casual chat with no brand factual question, no strategy question, no content request, no retrieval request, and no evaluation request. "
                        "For every non-small_talk mode, direct_reply must be null. "
                        "If a message asks about brand facts such as audience, colors, tone, motivations, positioning, or strategy, classify it as strategy_chat and set direct_reply to null. "
                        "Allowed deliverable_type values: null, blog, linkedin_post, instagram_caption, social_caption, x_post, x_thread, youtube_description, newsletter, email, script, long_description, general_copy. "
                        "revision_scope must be either null or an object with keys: targeted_fields, slide_indexes, slide_targets, preserve_visuals, preserve_copy, change_layout, change_tone, only_targeted. "
                        "targeted_fields must be an array using only: headline, body, cta, hashtags, layout, visuals. "
                        "slide_targets must be an array using only: cover, last."
                    ),
                    user=(
                        f"Session summary for reference only: {self._compact_json(session_context)}\n"
                        f"User message: {text}\n"
                        "Return a JSON object with keys: mode, confidence, reason, deliverable_type, uses_previous_output, workflow_type, revision_scope, display_retrieved_asset, direct_reply."
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
            "direct_reply": self._normalize_direct_reply(mode=mode, value=response.get("direct_reply")),
        }

    @classmethod
    def _router_session_summary(cls, session_context: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(session_context, dict):
            return {}
        summary: dict[str, Any] = {}
        for key in cls._SESSION_SUMMARY_KEYS:
            if key not in session_context:
                continue
            value = session_context.get(key)
            if value in (None, "", [], {}):
                continue
            summary[key] = cls._prompt_safe_value(value)
        return summary

    @classmethod
    def _prompt_safe_value(cls, value: Any, *, max_depth: int = 2) -> Any:
        if max_depth < 0:
            return cls._normalize_scalar(value, limit=160)
        if isinstance(value, dict):
            return {
                str(key): cls._prompt_safe_value(item, max_depth=max_depth - 1)
                for key, item in list(value.items())[:8]
            }
        if isinstance(value, list):
            return [cls._prompt_safe_value(item, max_depth=max_depth - 1) for item in value[:6]]
        return cls._normalize_scalar(value, limit=220)

    @staticmethod
    def _normalize_scalar(value: Any, *, limit: int) -> Any:
        if isinstance(value, (bool, int, float)):
            return value
        text = " ".join(str(value or "").split()).strip()
        return text[:limit].rstrip()

    @staticmethod
    def _compact_json(value: Any) -> str:
        try:
            return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
        except TypeError:
            return str(value)

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
            direct_reply=llm_decision.get("direct_reply"),
        )

    @staticmethod
    def _normalize_direct_reply(*, mode: str, value: Any) -> str | None:
        if mode != "small_talk":
            return None
        text = " ".join(str(value or "").split()).strip()
        if not text:
            return None
        return text[:600].rstrip()

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
