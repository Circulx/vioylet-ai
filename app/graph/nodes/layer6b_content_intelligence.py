from __future__ import annotations

"""Layer 6b — Content Intelligence spine.

Understand → Retrieve → Verify → Prioritize → Interpret → Reason → Insight.
Runs after L4 and BEFORE L5/L6 so Conceptualize/Plan are insight-led.
"""

from app.core.logging import get_logger
from app.graph.state import ViolytState
from app.prompts.jiraaf_layout import classify_layout

logger = get_logger(__name__)


async def layer6b_content_intelligence(state: ViolytState) -> dict:
    from app.services.content_intelligence import run_content_intelligence

    brand_intelligence = state.get("brand_intelligence")
    brand_context = state.get("brand_context")
    user_prompt = state.get("user_prompt", "")
    platform = state.get("platform", "linkedin")
    fmt = str(state.get("format", "static") or "static").strip().lower()
    if fmt not in ("static", "carousel", "infographic"):
        fmt = "static"

    brand_name = ""
    if brand_intelligence and brand_intelligence.brand_core:
        brand_name = (brand_intelligence.brand_core.brand_name or "").strip()

    layout = classify_layout(user_prompt, fmt)

    package, meta = await run_content_intelligence(
        user_prompt=user_prompt,
        fmt=fmt,
        platform=platform,
        brand_name=brand_name,
        brand_intelligence=brand_intelligence,
        brand_context=brand_context,
        layout_type=layout.layout_type,
    )

    logger.info(
        "content_intelligence.complete",
        thesis=(package.insight_thesis or "")[:120],
        approved_evidence=meta.get("approved_evidence"),
        total_evidence=meta.get("total_evidence"),
        hero=package.format_architecture.hero_statistic[:80] if package.format_architecture else "",
        scores=package.qa_self_score,
    )

    return {
        "content_intelligence": package,
        # Keep live_research in state for L7c source attachment / enrichment
        "live_research": package.live_research or state.get("live_research") or {},
        "layer_latencies": {"l6b_content_intelligence": meta.get("latency_ms", 0)},
        "token_usage": {
            "l6b_content_intelligence": {
                "input_tokens": meta.get("input_tokens", 0),
                "output_tokens": meta.get("output_tokens", 0),
            }
        },
    }
