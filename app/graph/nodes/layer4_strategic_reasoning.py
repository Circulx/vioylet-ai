from __future__ import annotations

from app.core.logging import get_logger
from app.graph.models.layer4_models import StrategicReasoningOutput
from app.graph.state import ViolytState
from app.prompts.layer4_strategic_reasoning import StrategicReasoningPromptBuilder
from app.services.llm.llm_router import LLMRouter

logger = get_logger(__name__)

_router = LLMRouter()
_prompt_builder = StrategicReasoningPromptBuilder()


async def layer4_strategic_reasoning(state: ViolytState) -> dict:
    brand_intelligence = state.get("brand_intelligence")
    campaign_brief = state.get("campaign_brief")

    if not brand_intelligence or not campaign_brief:
        logger.error("strategic_reasoning.missing_inputs")
        raise ValueError("Layer 2 brand_intelligence and Layer 3 campaign_brief are required for Layer 4")

    system = _prompt_builder.build_system()
    user = _prompt_builder.build_user(
        campaign_brief=campaign_brief,
        brand_intelligence=brand_intelligence,
    )

    service = _router.get_service("l4_strategic_reasoning")
    output, metadata = await service.complete_structured(
        system=system,
        user=user,
        output_model=StrategicReasoningOutput,
        layer="l4_strategic_reasoning",
        max_tokens=8192,
    )

    return {
        "strategic_reasoning": output,
        "layer_latencies": {"l4_strategic_reasoning": metadata["latency_ms"]},
        "token_usage": {
            "l4_strategic_reasoning": {
                "input_tokens": metadata["input_tokens"],
                "output_tokens": metadata["output_tokens"],
            }
        },
    }
