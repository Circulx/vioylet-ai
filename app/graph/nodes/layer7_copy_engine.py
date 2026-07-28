from __future__ import annotations

import re
from app.core.logging import get_logger
from app.graph.models.layer7_models import CopyOutput
from app.graph.state import ViolytState
from app.prompts.layer7_copy_engine import CopyEnginePromptBuilder
from app.prompts.jiraaf_layout import classify_layout, needs_live_research
from app.services.live_research import LiveResearchService
from app.services.llm.llm_router import LLMRouter

logger = get_logger(__name__)

_router = LLMRouter()
_prompt_builder = CopyEnginePromptBuilder()
_live_research = LiveResearchService()

# Common generic AI tropes to check for in Brand Uniqueness validation
AI_TROPES = [
    r"\bunlock\b",
    r"\belevate\b",
    r"\brevolutionize\b",
    r"\btransform\b",
    r"\bdelve\b",
    r"\btestament\b",
    r"\bbeacon\b",
    r"in today's",
    r"look no further",
    r"\bgame changer\b",
    r"\bgame-changer\b",
]

MAX_VALIDATION_RETRIES = 2


def contains_ai_tropes(text: str) -> list[str]:
    """Check text for generic AI words and return matches."""
    matches = []
    for trope in AI_TROPES:
        if re.search(trope, text, re.IGNORECASE):
            matches.append(trope.replace(r"\b", ""))
    return matches


async def layer7_copy_engine(state: ViolytState) -> dict:
    brand_intelligence = state.get("brand_intelligence")
    format_plan = state.get("format_plan")
    creative_concepts = state.get("creative_concepts")
    brand_context = state.get("brand_context")
    user_prompt = state.get("user_prompt", "")
    platform = state.get("platform", "linkedin")
    fmt = str(state.get("format", "static") or "static").strip().lower()

    if not brand_intelligence or not format_plan or not creative_concepts:
        logger.error("copy_engine.missing_inputs")
        raise ValueError("Layer 2 brand_intelligence, Layer 5 creative_concepts, and Layer 6 format_plan are required for Layer 7")

    recommended = creative_concepts.recommended_concept

    # Convert Concept Pydantic model to dict
    concept_dict = {
        "concept_name": recommended.concept_name,
        "core_idea": recommended.core_idea,
        "hook": recommended.hook,
        "narrative_angle": recommended.narrative_angle,
        "visual_angle": recommended.visual_angle,
    }

    # Live web research for news/data/top-N/rates (Jiraaf sourced creatives)
    layout = classify_layout(user_prompt, fmt)
    live_research: dict = {}
    if needs_live_research(user_prompt, layout.layout_type):
        try:
            knowledge_brief = [
                {"content": chunk.content_summary, "source": chunk.source}
                for chunk in (brand_context.high_relevance_context if brand_context else [])
            ]
            research_query = f"{user_prompt} {recommended.core_idea} {brand_intelligence.brand_core.brand_name}".strip()
            live_research = _live_research.gather_sync(
                prompt=research_query,
                studio_panel={"format": fmt or layout.suggested_format, "platform_preset": platform},
                compiled_context={"knowledge_brief": knowledge_brief},
            ) or {}
            logger.info(
                "copy_engine.live_research",
                status=live_research.get("status"),
                fact_count=len(live_research.get("verified_facts", [])),
                source_count=len(live_research.get("sources", [])),
                search_hits=live_research.get("search_hits"),
                layout=layout.layout_type,
                summary_preview=(live_research.get("summary") or "")[:160],
            )
        except Exception as e:
            logger.warning(f"copy_engine.live_research_failed: {e}")
            live_research = {}

    system = _prompt_builder.build_system(
        format_name=fmt,
        user_prompt=user_prompt,
        layout_type=layout.layout_type,
    )
    user = _prompt_builder.build_user(
        brand_intelligence=brand_intelligence,
        format_plan=format_plan,
        concept=concept_dict,
        format_name=fmt,
        live_research=live_research,
        user_prompt=user_prompt,
        layout_type=layout.layout_type,
    )

    service = _router.get_service("l7_copy_engine")

    output: CopyOutput | None = None
    metadata: dict | None = None

    for attempt in range(MAX_VALIDATION_RETRIES + 1):
        current_user = user
        if attempt > 0:
            current_user = (
                user
                + f"\n\nIMPORTANT: The previous output contained generic AI phrasing or lacked brand specificity. "
                "Do NOT use typical AI tropes or corporate fluff (e.g., 'unlock', 'elevate', 'transform'). "
                "Keep the language authentic, direct, and completely aligned with this brand's positioning."
            )
            logger.warning("copy_engine.uniqueness_retry", attempt=attempt)

        output, metadata = await service.complete_structured(
            system=system,
            user=current_user,
            output_model=CopyOutput,
            layer="l7_copy_engine",
            max_tokens=8192,
        )

        # Brand Uniqueness validation check
        full_text_to_validate = " ".join([
            output.headline,
            output.supporting_line or "",
            output.body,
            output.cta,
            " ".join([slide.headline + " " + slide.body for slide in output.slide_copy])
        ])

        found_tropes = contains_ai_tropes(full_text_to_validate)
        if not found_tropes:
            logger.info("copy_engine.brand_uniqueness_passed", attempt=attempt)
            break
        
        logger.warning(
            "copy_engine.brand_uniqueness_failed",
            found_tropes=found_tropes,
            attempt=attempt,
        )

    assert output is not None and metadata is not None

    return {
        "copy": output,
        "live_research": live_research or {},
        "layer_latencies": {"l7_copy_engine": metadata["latency_ms"]},
        "token_usage": {
            "l7_copy_engine": {
                "input_tokens": metadata["input_tokens"],
                "output_tokens": metadata["output_tokens"],
            }
        },
    }
