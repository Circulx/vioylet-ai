from __future__ import annotations

from app.core.logging import get_logger
from app.graph.models.layer6_models import FormatPlanOutput
from app.graph.state import ViolytState
from app.prompts.layer6_format_engine import FormatEnginePromptBuilder
from app.services.llm.llm_router import LLMRouter

logger = get_logger(__name__)

_router = LLMRouter()
_prompt_builder = FormatEnginePromptBuilder()


async def layer6_format_engine(state: ViolytState) -> dict:
    strategic_reasoning = state.get("strategic_reasoning")
    brand_intelligence = state.get("brand_intelligence")
    fmt = state.get("format", "static")
    platform = state.get("platform", "linkedin")

    if not strategic_reasoning or not brand_intelligence:
        logger.error("format_engine.missing_inputs")
        raise ValueError("Layer 4 strategic_reasoning and Layer 2 brand_intelligence are required for Layer 6")

    system = _prompt_builder.build_system(platform=platform, fmt=fmt)
    user = _prompt_builder.build_user(
        strategic_reasoning=strategic_reasoning,
        brand_intelligence=brand_intelligence,
        platform=platform,
        format=fmt,
    )

    service = _router.get_service("l6_format_engine")
    output, metadata = await service.complete_structured(
        system=system,
        user=user,
        output_model=FormatPlanOutput,
        layer="l6_format_engine",
        max_tokens=4096,
    )

    logger.info(
        "format_engine.complete",
        format=fmt,
        platform=platform,
        slides=len(output.slide_plan),
        layout_archetype=output.layout_archetype,
    )

    return {
        "format_plan": output,
        "layer_latencies": {"l6_format_engine": metadata["latency_ms"]},
        "token_usage": {
            "l6_format_engine": {
                "input_tokens": metadata["input_tokens"],
                "output_tokens": metadata["output_tokens"],
            }
        },
    }
