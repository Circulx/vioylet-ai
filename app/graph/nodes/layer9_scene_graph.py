from __future__ import annotations

from app.core.logging import get_logger
from app.graph.models.layer9_models import SceneGraphOutput
from app.graph.state import ViolytState
from app.prompts.layer9_scene_graph import SceneGraphPromptBuilder
from app.services.llm.llm_router import LLMRouter

logger = get_logger(__name__)

_router = LLMRouter()
_prompt_builder = SceneGraphPromptBuilder()


async def layer9_scene_graph(state: ViolytState) -> dict:
    brand_intelligence = state.get("brand_intelligence")
    format_plan = state.get("format_plan")
    copy = state.get("copy")
    visual_reasoning = state.get("visual_reasoning")

    platform = state.get("platform", "linkedin").lower()
    fmt = state.get("format", "static")

    if not brand_intelligence or not format_plan or not copy or not visual_reasoning:
        logger.error("scene_graph.missing_inputs")
        raise ValueError("Layer 2 brand_intelligence, Layer 6 format_plan, Layer 7 copy, and Layer 8 visual_reasoning are required for Layer 9")

    # Platform ratio enforcement
    ratios = {
        "linkedin": (1200, 627),
        "instagram": (1080, 1080),
        "twitter": (1200, 675),
        "x": (1200, 675),
        "story": (1080, 1920),
    }
    
    # Enforce exact canvas dimensions for layouts that override default platform ratios
    fmt_lower = str(fmt or "static").strip().lower()
    if fmt_lower == "infographic":
        width, height = (1080, 1350)
    elif fmt_lower == "carousel":
        width, height = (1080, 1080)
    else:
        width, height = ratios.get(platform, (1200, 627))

    system = _prompt_builder.build_system(width=width, height=height)
    user = _prompt_builder.build_user(
        brand_intelligence=brand_intelligence,
        format_plan=format_plan,
        copy=copy,
        visual_reasoning=visual_reasoning,
    )

    # Complete scene graph structured layout (GPT-4o)
    service = _router.get_service("l9_scene_graph")
    output, metadata = await service.complete_structured(
        system=system,
        user=user,
        output_model=SceneGraphOutput,
        layer="l9_scene_graph",
        max_tokens=4096,
    )

    # Coordinates & Boundary Safety Validation and Clamping
    for el in output.elements:
        pos = el.position
        x = pos.get("x", 0)
        y = pos.get("y", 0)
        w = pos.get("width", 100)
        h = pos.get("height", 100)

        # Ensure no negative positions
        if x < 0:
            x = 0
        if y < 0:
            y = 0

        # Ensure dimensions do not exceed canvas size
        if w > width:
            w = width
        if h > height:
            h = height

        # Clamp right/bottom coordinates
        if x + w > width:
            x = width - w
        if y + h > height:
            y = height - h

        pos["x"] = int(x)
        pos["y"] = int(y)
        pos["width"] = int(w)
        pos["height"] = int(h)

        # Asset URL binding from Visual Reasoning if it's a visual element
        # For carousels with multiple generated images, match by element_id/slide number if possible.
        if el.element_type == "visual":
            image_urls = visual_reasoning.generated_image_urls or []
            if not image_urls and visual_reasoning.generated_image_url:
                image_urls = [visual_reasoning.generated_image_url]
            if image_urls:
                # Try to extract a slide/card number from element_id, e.g. "slide_1_visual", "visual_2", "card-3"
                import re
                match = re.search(r"(?:slide|card|visual)[_\-]?(\d+)", el.element_id, re.IGNORECASE)
                if match:
                    idx = int(match.group(1)) - 1
                    idx = max(0, min(idx, len(image_urls) - 1))
                    el.asset_url = image_urls[idx]
                else:
                    el.asset_url = image_urls[0]

    # Ensure generated image URLs are present in the scene graph's assets list
    for img_url in (visual_reasoning.generated_image_urls or [visual_reasoning.generated_image_url]):
        if img_url and img_url not in output.assets:
            output.assets.append(img_url)

    logger.info(
        "scene_graph.complete",
        platform=platform,
        dimensions=f"{width}x{height}",
        elements_count=len(output.elements),
    )

    return {
        "scene_graph": output,
        "layer_latencies": {"l9_scene_graph": metadata["latency_ms"]},
        "token_usage": {
            "l9_scene_graph": {
                "input_tokens": metadata["input_tokens"],
                "output_tokens": metadata["output_tokens"],
            }
        },
    }
