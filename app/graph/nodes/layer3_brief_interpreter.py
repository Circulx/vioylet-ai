from __future__ import annotations

from app.core.logging import get_logger
from app.graph.models.layer3_models import CampaignBriefOutput
from app.graph.state import ViolytState
from app.prompts.layer3_brief_interpreter import BriefInterpreterPromptBuilder
from app.services.llm.llm_router import LLMRouter

logger = get_logger(__name__)

_router = LLMRouter()
_prompt_builder = BriefInterpreterPromptBuilder()


async def layer3_brief_interpreter(state: ViolytState) -> dict:
    brand_intelligence = state.get("brand_intelligence")
    if not brand_intelligence:
        logger.error("brief_interpreter.no_brand_intelligence")
        raise ValueError("Layer 2 brand_intelligence is required for Layer 3")

    system = _prompt_builder.build_system()
    user = _prompt_builder.build_user(
        user_prompt=state.get("user_prompt", ""),
        platform=state.get("platform", ""),
        format=state.get("format", ""),
        brand_intelligence=brand_intelligence,
    )

    service = _router.get_service("l3_brief_interpreter")
    output, metadata = await service.complete_structured(
        system=system,
        user=user,
        output_model=CampaignBriefOutput,
        layer="l3_brief_interpreter",
        temperature=0.1,
        max_tokens=2048,
    )

    layer_latencies = state.get("layer_latencies") or {}
    token_usage = state.get("token_usage") or {}
    layer_latencies["l3_brief_interpreter"] = metadata["latency_ms"]
    token_usage["l3_brief_interpreter"] = {
        "input_tokens": metadata["input_tokens"],
        "output_tokens": metadata["output_tokens"],
    }

    return {
        "campaign_brief": output,
        "layer_latencies": {"l3_brief_interpreter": metadata["latency_ms"]},
        "token_usage": {
            "l3_brief_interpreter": {
                "input_tokens": metadata["input_tokens"],
                "output_tokens": metadata["output_tokens"],
            }
        },
    }
