from __future__ import annotations

from app.core.logging import get_logger
from app.graph.models.layer2_models import BrandIntelligenceOutput
from app.graph.state import ViolytState
from app.prompts.layer2_brand_intelligence import BrandIntelligencePromptBuilder
from app.services.cache.brand_cache import BrandCacheService
from app.services.llm.claude_service import ClaudeService

logger = get_logger(__name__)

_claude_service = ClaudeService()
_brand_cache = BrandCacheService()
_prompt_builder = BrandIntelligencePromptBuilder()


async def layer2_brand_intelligence(state: ViolytState) -> dict:
    brand_id = state.get("brand_id", "unknown")
    brand_context = state.get("brand_context")
    data_version: int = state.get("data_version") or 1  # set by L1 from brand.data_version in DB

    # Try cache first — key includes data_version so re-indexing the brand auto-invalidates.
    cached = await _brand_cache.get(brand_id, data_version=data_version)
    if cached:
        logger.info("brand_intelligence.cache_hit", brand_id=brand_id, data_version=data_version)
        return {"brand_intelligence": cached}

    if not brand_context:
        logger.error("brand_intelligence.no_context", brand_id=brand_id)
        raise ValueError("Layer 1 brand_context is required for Layer 2")

    system = _prompt_builder.build_system()
    user = _prompt_builder.build_user(
        brand_id=brand_id,
        high_context=brand_context.high_relevance_context,
        medium_context=brand_context.medium_relevance_context,
        weak_signals=brand_context.missing_context,
    )

    output, metadata = await _claude_service.complete_structured(
        system=system,
        user=user,
        output_model=BrandIntelligenceOutput,
        layer="l2_brand_intelligence",
        max_tokens=8192,
    )

    await _brand_cache.set(brand_id, output, data_version=data_version)

    return {
        "brand_intelligence": output,
        "layer_latencies": {"l2_brand_intelligence": metadata["latency_ms"]},
        "token_usage": {
            "l2_brand_intelligence": {
                "input_tokens": metadata["input_tokens"],
                "output_tokens": metadata["output_tokens"],
            }
        },
    }
