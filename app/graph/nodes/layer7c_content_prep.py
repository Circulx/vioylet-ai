from __future__ import annotations

from app.core.logging import get_logger
from app.graph.models.layer7c_models import CreativeBlueprint
from app.graph.state import ViolytState
from app.prompts.layer7c_content_prep import ContentPrepPromptBuilder
from app.services.copy_proofread import proofread_blueprint
from app.services.llm.llm_router import LLMRouter

logger = get_logger(__name__)

_router = LLMRouter()
_prompt_builder = ContentPrepPromptBuilder()


async def layer7c_content_prep(state: ViolytState) -> dict:
    """Layer 7c — Prompt Intelligence → Creative Blueprint for user approval."""
    copy = state.get("copy")
    brand_intelligence = state.get("brand_intelligence")
    format_plan = state.get("format_plan")
    campaign_brief = state.get("campaign_brief")
    user_prompt = state.get("user_prompt", "")
    platform = state.get("platform", "linkedin")
    fmt = str(state.get("format", "static") or "static").strip().lower()
    if fmt not in ("static", "carousel", "infographic"):
        fmt = "static"

    if not copy or not brand_intelligence or not format_plan:
        logger.error("content_prep.missing_inputs")
        raise ValueError(
            "Layer 7 copy, Layer 2 brand_intelligence, and Layer 6 format_plan "
            "are required for Layer 7c"
        )

    system = _prompt_builder.build_system(format_name=fmt)
    user = _prompt_builder.build_user(
        user_prompt=user_prompt,
        platform=platform,
        format_name=fmt,
        brand_intelligence=brand_intelligence,
        campaign_brief=campaign_brief,
        format_plan=format_plan,
        copy=copy,
    )

    service = _router.get_service("l7c_content_prep")
    output, metadata = await service.complete_structured(
        system=system,
        user=user,
        output_model=CreativeBlueprint,
        layer="l7c_content_prep",
        max_tokens=16000,
    )

    # Ensure format/platform match the run (user cannot drift via LLM)
    output.format = fmt  # type: ignore[assignment]
    output.platform = platform

    # Fallback: if LLM omitted slides for carousel, lift from L7
    if fmt == "carousel" and not output.slides and copy.slide_copy:
        from app.graph.models.layer7c_models import BlueprintSlide

        output.slides = [
            BlueprintSlide(
                slide_number=s.slide_number,
                role="hook" if s.slide_number == 1 else "insight",
                headline=s.headline,
                body=s.body,
                supporting_line=s.supporting_line,
                cta=s.cta,
            )
            for s in copy.slide_copy
        ]

    if fmt == "infographic" and not output.sections and copy.infographic_sections:
        from app.graph.models.layer7c_models import BlueprintInfographicSection

        output.sections = [
            BlueprintInfographicSection(
                section_label=s.section_label,
                stat=s.stat,
                includes=list(s.includes or []),
                body=s.body,
                icon_hint=s.icon_hint,
            )
            for s in copy.infographic_sections
        ]
        if not output.headline:
            output.headline = copy.headline
        if not output.title:
            output.title = copy.headline

    # Ensure core static fields always present
    if not output.headline:
        output.headline = copy.headline
    if not output.body:
        output.body = copy.body
    if not output.cta:
        output.cta = copy.cta or output.cta
    if not output.supporting_line:
        output.supporting_line = copy.supporting_line
    if not output.hashtags:
        output.hashtags = list(copy.hashtags or [])
    if not output.claim_safety_notes:
        output.claim_safety_notes = list(copy.claim_safety_notes or [])

    # Fast local spelling polish before blueprint is shown (LLM polish runs on approve)
    try:
        output = await proofread_blueprint(output, use_llm=False)
        output.format = fmt  # type: ignore[assignment]
        output.platform = platform
    except Exception as exc:
        logger.warning("content_prep.proofread_failed", error=str(exc))

    logger.info(
        "content_prep.complete",
        format=fmt,
        slides=len(output.slides),
        sections=len(output.sections),
        zones=len(output.overlay_zones),
    )

    return {
        "creative_blueprint": output,
        "layer_latencies": {"l7c_content_prep": metadata["latency_ms"]},
        "token_usage": {
            "l7c_content_prep": {
                "input_tokens": metadata["input_tokens"],
                "output_tokens": metadata["output_tokens"],
            }
        },
    }
