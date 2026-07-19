from __future__ import annotations

from app.core.logging import get_logger
from app.graph.models.layer5_models import CreativeConceptsOutput
from app.graph.state import ViolytState
from app.prompts.layer5_concept_engine import ConceptEnginePromptBuilder
from app.services.llm.llm_router import LLMRouter

logger = get_logger(__name__)

_router = LLMRouter()
_prompt_builder = ConceptEnginePromptBuilder()

MAX_DIVERSITY_RETRIES = 2
DIVERSITY_THRESHOLD = 0.5


async def layer5_concept_engine(state: ViolytState) -> dict:
    strategic_reasoning = state.get("strategic_reasoning")
    brand_intelligence = state.get("brand_intelligence")

    if not strategic_reasoning or not brand_intelligence:
        logger.error("concept_engine.missing_inputs")
        raise ValueError("Layer 4 strategic_reasoning and Layer 2 brand_intelligence are required for Layer 5")

    system = _prompt_builder.build_system()
    user = _prompt_builder.build_user(
        strategic_reasoning=strategic_reasoning,
        brand_intelligence=brand_intelligence,
    )

    service = _router.get_service("l5_concept_engine")

    output: CreativeConceptsOutput | None = None
    metadata: dict | None = None

    for attempt in range(MAX_DIVERSITY_RETRIES + 1):
        current_user = user
        if attempt > 0:
            current_user = (
                user
                + "\n\nIMPORTANT: The previous concepts were too similar (diversity_score < 0.5). "
                "Generate genuinely DIFFERENT concepts with distinct strategic angles, "
                "narrative behaviors, and visual treatments. Do not repeat or slightly vary "
                "previous concepts."
            )
            logger.warning("concept_engine.diversity_retry", attempt=attempt)

        output, metadata = await service.complete_structured(
            system=system,
            user=current_user,
            output_model=CreativeConceptsOutput,
            layer="l5_concept_engine",
            max_tokens=16000,
        )

        if output.diversity_score >= DIVERSITY_THRESHOLD:
            break

        logger.warning(
            "concept_engine.low_diversity",
            diversity_score=output.diversity_score,
            attempt=attempt,
        )

    assert output is not None and metadata is not None

    logger.info(
        "concept_engine.complete",
        concepts_count=len(output.all_concepts),
        recommended=output.recommended_concept.concept_name,
        diversity_score=output.diversity_score,
    )

    return {
        "creative_concepts": output,
        "layer_latencies": {"l5_concept_engine": metadata["latency_ms"]},
        "token_usage": {
            "l5_concept_engine": {
                "input_tokens": metadata["input_tokens"],
                "output_tokens": metadata["output_tokens"],
            }
        },
    }
