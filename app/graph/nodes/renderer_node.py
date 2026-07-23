from __future__ import annotations

from copy import deepcopy

from app.core.logging import get_logger
from app.graph.state import ViolytState

logger = get_logger(__name__)


async def renderer_node(state: ViolytState) -> dict:
    """Pass through AI-generated images (text already baked by gpt-image). No Pillow overlay."""
    visual_reasoning = state.get("visual_reasoning")
    scene_graph = state.get("scene_graph")
    blueprint = state.get("creative_blueprint")
    platform = state.get("platform", "linkedin")
    fmt = state.get("format", "static")

    if not visual_reasoning:
        logger.warning("renderer_node.missing_visual_reasoning")
        return {
            "final_output": {
                "platform": platform,
                "format": fmt,
                "canvas_ratio": scene_graph.platform_ratio if scene_graph else "1200x627",
                "asset_url": "",
                "asset_urls": [],
                "slide_count": 0,
                "render_status": "failed",
                "message": "No AI artwork available.",
                "blueprint_approved": bool(blueprint),
            }
        }

    image_urls = [u for u in (visual_reasoning.generated_image_urls or []) if u]
    if visual_reasoning.generated_image_url and visual_reasoning.generated_image_url not in image_urls:
        image_urls.insert(0, visual_reasoning.generated_image_url)

    final_image_url = image_urls[0] if image_urls else ""
    logger.info(
        "renderer_node.ai_passthrough format=%s urls=%s blueprint=%s",
        fmt,
        len(image_urls),
        bool(blueprint),
    )

    updated_visual_reasoning = deepcopy(visual_reasoning)
    updated_visual_reasoning.generated_image_url = final_image_url
    updated_visual_reasoning.generated_image_urls = image_urls

    return {
        "visual_reasoning": updated_visual_reasoning,
        "final_output": {
            "platform": platform,
            "format": fmt,
            "canvas_ratio": scene_graph.platform_ratio if scene_graph else "1200x627",
            "asset_url": final_image_url,
            "asset_urls": image_urls,
            "slide_count": len(image_urls),
            "render_status": "success" if final_image_url else "failed",
            "message": (
                "AI creative ready (text baked in image)."
                if final_image_url
                else "Image generation returned no asset."
            ),
            "blueprint_approved": bool(blueprint),
        },
    }
