from __future__ import annotations

from app.core.logging import get_logger
from app.graph.models.layer7c_models import CreativeBlueprint
from app.graph.state import ViolytState
from app.prompts.jiraaf_layout import classify_layout
from app.prompts.layer7c_content_prep import ContentPrepPromptBuilder
from app.services.blueprint_quality import (
    blueprint_passes_editorial_qa,
    editorial_qa_repair_instructions,
    finalize_blueprint_for_card,
    score_blueprint_editorial_qa,
)
from app.services.copy_proofread import proofread_blueprint
from app.services.llm.llm_router import LLMRouter

logger = get_logger(__name__)

_router = LLMRouter()
_prompt_builder = ContentPrepPromptBuilder()

MAX_BLUEPRINT_REGENERATIONS = 2


def _normalize_blueprint_fields(
    output: CreativeBlueprint,
    *,
    copy,
    fmt: str,
    platform: str,
    layout_type: str,
) -> CreativeBlueprint:
    output.format = fmt  # type: ignore[assignment]
    output.platform = platform
    output.layout_type = layout_type
    output.layout_archetype = layout_type

    # Carousel story: ensure 4–7 slides
    if fmt == "carousel":
        from app.graph.models.layer7c_models import BlueprintSlide

        if not output.slides and copy.slide_copy:
            output.slides = [
                BlueprintSlide(
                    slide_number=s.slide_number,
                    role="hook"
                    if s.slide_number == 1
                    else ("cta" if s.slide_number == len(copy.slide_copy) else "insight"),
                    headline=s.headline,
                    body=s.body,
                    supporting_line=s.supporting_line,
                    cta=s.cta,
                )
                for s in copy.slide_copy
            ]
        if layout_type == "carousel_story" and len(output.slides) < 4:
            beats = list(output.story_flow or [])
            if not beats:
                beats = [
                    output.hook or output.headline or "Start here",
                    output.supporting_line or "Here's the key idea",
                    (output.body or "What this means for you")[:80],
                    output.cta or "Save this for later",
                ]
            while len(output.slides) < 4 and beats:
                text = beats.pop(0)
                output.slides.append(
                    BlueprintSlide(
                        slide_number=len(output.slides) + 1,
                        role="insight",
                        headline=" ".join(str(text).split()[:8]),
                        body=str(text),
                    )
                )

    if fmt in ("infographic", "static") and not output.sections and copy.infographic_sections:
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
    if output.body is None:
        output.body = copy.body
    if layout_type in ("static_hub_facts", "static_ranking"):
        if len(output.body or "") > 80:
            output.body = ""
    if not output.cta:
        output.cta = copy.cta or output.cta
    if not output.supporting_line:
        output.supporting_line = copy.supporting_line
    if not output.hashtags:
        output.hashtags = list(copy.hashtags or [])
    if not output.claim_safety_notes:
        output.claim_safety_notes = list(copy.claim_safety_notes or [])
    if not output.stat_highlights:
        output.stat_highlights = list(copy.stat_highlights or [])
    if not output.proof_points:
        output.proof_points = list(copy.proof_points or [])
    if not str(output.post_caption or "").strip():
        from app.services.post_caption import build_post_caption_from_blueprint

        output.post_caption = build_post_caption_from_blueprint(output, platform=platform)
    return output


async def layer7c_content_prep(state: ViolytState) -> dict:
    """Layer 7c — Creative Blueprint with Phase-1 reject/regenerate QA loop."""
    copy = state.get("copy")
    brand_intelligence = state.get("brand_intelligence")
    format_plan = state.get("format_plan")
    campaign_brief = state.get("campaign_brief")
    user_prompt = state.get("user_prompt", "")
    platform = state.get("platform", "linkedin")
    live_research = state.get("live_research") or {}
    content_intelligence = state.get("content_intelligence")
    fmt = str(state.get("format", "static") or "static").strip().lower()
    if fmt not in ("static", "carousel", "infographic"):
        fmt = "static"

    layout = classify_layout(user_prompt, fmt)

    if not copy or not brand_intelligence or not format_plan:
        logger.error("content_prep.missing_inputs")
        raise ValueError(
            "Layer 7 copy, Layer 2 brand_intelligence, and Layer 6 format_plan "
            "are required for Layer 7c"
        )

    brand_name = (brand_intelligence.brand_core.brand_name or "").strip()
    system = _prompt_builder.build_system(
        format_name=fmt,
        user_prompt=user_prompt,
        layout_type=layout.layout_type,
        brand_name=brand_name,
    )
    base_user = _prompt_builder.build_user(
        user_prompt=user_prompt,
        platform=platform,
        format_name=fmt,
        brand_intelligence=brand_intelligence,
        campaign_brief=campaign_brief,
        format_plan=format_plan,
        copy=copy,
        layout_type=layout.layout_type,
        live_research=live_research,
    )
    try:
        from app.services.content_intelligence import content_intelligence_prompt_block

        intel_block = content_intelligence_prompt_block(content_intelligence)
        if intel_block:
            base_user = (
                base_user
                + "\n\n"
                + intel_block
                + "\nBlueprint MUST follow narrative architecture + approved evidence. "
                "Hero statistic + supporting data points from format architecture. "
                "Section bodies = so-what insights, not slogans. UDAN never ADAN.\n"
            )
    except Exception as exc:
        logger.warning("content_prep.intel_block_failed", error=str(exc)[:120])

    service = _router.get_service("l7c_content_prep")

    total_latency = 0
    total_in = 0
    total_out = 0
    output: CreativeBlueprint | None = None
    last_scores: dict = {}

    for attempt in range(MAX_BLUEPRINT_REGENERATIONS + 1):
        user = base_user
        if attempt > 0 and last_scores:
            user = (
                base_user
                + "\n\n"
                + editorial_qa_repair_instructions(last_scores, user_prompt=user_prompt)
            )
            logger.warning("content_prep.regenerate", attempt=attempt, scores=last_scores)

        draft, metadata = await service.complete_structured(
            system=system,
            user=user,
            output_model=CreativeBlueprint,
            layer="l7c_content_prep",
            max_tokens=4096,
        )
        total_latency += int(metadata.get("latency_ms") or 0)
        total_in += int(metadata.get("input_tokens") or 0)
        total_out += int(metadata.get("output_tokens") or 0)

        draft = _normalize_blueprint_fields(
            draft,
            copy=copy,
            fmt=fmt,
            platform=platform,
            layout_type=layout.layout_type,
        )
        draft = finalize_blueprint_for_card(
            draft,
            layout_type=layout.layout_type,
            user_prompt=user_prompt,
            live_research=live_research,
            content_intelligence=content_intelligence,
        )
        try:
            draft = await proofread_blueprint(draft, use_llm=False)
            draft.format = fmt  # type: ignore[assignment]
            draft.platform = platform
            draft.layout_type = layout.layout_type
            draft = finalize_blueprint_for_card(
                draft,
                layout_type=layout.layout_type,
                user_prompt=user_prompt,
                live_research=live_research,
                content_intelligence=content_intelligence,
            )
        except Exception as exc:
            logger.warning("content_prep.proofread_failed", error=str(exc))

        last_scores = score_blueprint_editorial_qa(
            draft,
            user_prompt=user_prompt,
            content_intelligence=content_intelligence,
        )
        notes = list(draft.brand_alignment_notes or [])
        notes.append(f"phase1_editorial_qa_attempt_{attempt}={last_scores}")
        draft.brand_alignment_notes = notes[:10]
        output = draft

        if blueprint_passes_editorial_qa(last_scores):
            logger.info("content_prep.qa_passed", attempt=attempt, scores=last_scores)
            break
        logger.warning("content_prep.qa_rejected", attempt=attempt, scores=last_scores)
    else:
        logger.warning(
            "content_prep.qa_exhausted",
            attempts=MAX_BLUEPRINT_REGENERATIONS + 1,
            scores=last_scores,
        )

    assert output is not None

    logger.info(
        "content_prep.complete",
        format=fmt,
        layout=layout.layout_type,
        slides=len(output.slides),
        sections=len(output.sections),
        sources=len(output.sources),
        missing=output.missing_critical,
        qa=last_scores,
    )

    return {
        "creative_blueprint": output,
        "layer_latencies": {"l7c_content_prep": total_latency},
        "token_usage": {
            "l7c_content_prep": {
                "input_tokens": total_in,
                "output_tokens": total_out,
            }
        },
    }
