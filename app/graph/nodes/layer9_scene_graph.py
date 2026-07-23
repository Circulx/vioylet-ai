from __future__ import annotations

from app.core.logging import get_logger
from app.graph.models.layer9_models import SceneElement, SceneGraphOutput
from app.graph.state import ViolytState
from app.prompts.layer9_scene_graph import SceneGraphPromptBuilder
from app.services.llm.llm_router import LLMRouter

logger = get_logger(__name__)

_router = LLMRouter()
_prompt_builder = SceneGraphPromptBuilder()


def _role_to_element_type(role: str) -> str:
    r = (role or "").lower()
    if r == "cta":
        return "cta"
    if r == "logo":
        return "logo"
    if r in ("visual", "image", "background", "decorative"):
        return r if r != "image" else "visual"
    return "copy"


def _inject_blueprint_zones(
    output: SceneGraphOutput,
    blueprint,
    width: int,
    height: int,
) -> None:
    """Merge approved Creative Blueprint overlay zones into the scene graph."""
    if not blueprint:
        return

    zones = list(blueprint.overlay_zones or [])
    if not zones:
        # Synthesize minimal zones from blueprint text fields
        synthesized = []
        if blueprint.headline:
            synthesized.append(
                {
                    "zone_id": "headline",
                    "role": "headline",
                    "text": blueprint.headline,
                    "priority": 1,
                    "x_rel": 0.06,
                    "y_rel": 0.08,
                    "w_rel": 0.72,
                    "h_rel": 0.12,
                }
            )
        if blueprint.supporting_line:
            synthesized.append(
                {
                    "zone_id": "supporting_line",
                    "role": "supporting_line",
                    "text": blueprint.supporting_line,
                    "priority": 2,
                    "x_rel": 0.06,
                    "y_rel": 0.20,
                    "w_rel": 0.72,
                    "h_rel": 0.08,
                }
            )
        if blueprint.body and blueprint.format == "static":
            synthesized.append(
                {
                    "zone_id": "body",
                    "role": "body",
                    "text": blueprint.body,
                    "priority": 3,
                    "x_rel": 0.06,
                    "y_rel": 0.55,
                    "w_rel": 0.55,
                    "h_rel": 0.22,
                }
            )
        if blueprint.cta:
            synthesized.append(
                {
                    "zone_id": "cta",
                    "role": "cta",
                    "text": blueprint.cta,
                    "priority": 4,
                    "x_rel": 0.06,
                    "y_rel": 0.82,
                    "w_rel": 0.40,
                    "h_rel": 0.08,
                }
            )
        for i, slide in enumerate(blueprint.slides or []):
            synthesized.append(
                {
                    "zone_id": f"slide_{slide.slide_number}_headline",
                    "role": "headline",
                    "text": slide.headline,
                    "priority": 1,
                    "slide_number": slide.slide_number,
                    "x_rel": 0.08,
                    "y_rel": 0.12,
                    "w_rel": 0.84,
                    "h_rel": 0.14,
                }
            )
            if slide.body:
                synthesized.append(
                    {
                        "zone_id": f"slide_{slide.slide_number}_body",
                        "role": "body",
                        "text": slide.body,
                        "priority": 2,
                        "slide_number": slide.slide_number,
                        "x_rel": 0.08,
                        "y_rel": 0.70,
                        "w_rel": 0.84,
                        "h_rel": 0.16,
                    }
                )
        zones = synthesized

    existing_ids = {el.element_id for el in output.elements}

    for z in zones:
        if hasattr(z, "model_dump"):
            zd = z.model_dump()
        elif isinstance(z, dict):
            zd = z
        else:
            continue

        zone_id = str(zd.get("zone_id") or zd.get("role") or "zone")
        role = str(zd.get("role") or "body")
        text = str(zd.get("text") or "")
        if not text:
            continue

        x_rel = float(zd.get("x_rel") if zd.get("x_rel") is not None else 0.06)
        y_rel = float(zd.get("y_rel") if zd.get("y_rel") is not None else 0.10)
        w_rel = float(zd.get("w_rel") if zd.get("w_rel") is not None else 0.70)
        h_rel = float(zd.get("h_rel") if zd.get("h_rel") is not None else 0.10)

        x = int(max(0, min(width - 1, x_rel * width)))
        y = int(max(0, min(height - 1, y_rel * height)))
        w = int(max(40, min(width - x, w_rel * width)))
        h = int(max(24, min(height - y, h_rel * height)))

        element_id = zone_id
        slide_number = zd.get("slide_number")
        if slide_number is not None and f"slide_{slide_number}" not in element_id:
            element_id = f"slide_{slide_number}_{zone_id}"

        # Prefer updating matching LLM element content; otherwise append
        matched = next((el for el in output.elements if el.element_id == element_id), None)
        if matched is None and role in ("headline", "supporting_line", "body", "cta"):
            matched = next(
                (
                    el
                    for el in output.elements
                    if el.element_type in ("copy", "cta") and role in el.element_id.lower()
                ),
                None,
            )

        if matched:
            matched.content = text
            matched.position = {"x": x, "y": y, "width": w, "height": h}
            matched.style = {
                **(matched.style or {}),
                "role": role,
                "from_blueprint": True,
                "slide_number": slide_number,
            }
        elif element_id not in existing_ids:
            output.elements.append(
                SceneElement(
                    element_id=element_id,
                    element_type=_role_to_element_type(role),  # type: ignore[arg-type]
                    content=text,
                    position={"x": x, "y": y, "width": w, "height": h},
                    style={
                        "role": role,
                        "from_blueprint": True,
                        "slide_number": slide_number,
                        "font_size": 32 if role == "headline" else 18,
                        "color": "#111111",
                        "font_weight": "bold" if role in ("headline", "cta") else "normal",
                    },
                )
            )
            existing_ids.add(element_id)


async def layer9_scene_graph(state: ViolytState) -> dict:
    brand_intelligence = state.get("brand_intelligence")
    format_plan = state.get("format_plan")
    copy = state.get("copy")
    blueprint = state.get("creative_blueprint")
    visual_reasoning = state.get("visual_reasoning")

    platform = state.get("platform", "linkedin").lower()
    fmt = state.get("format", "static")

    if not brand_intelligence or not format_plan or not copy or not visual_reasoning:
        logger.error("scene_graph.missing_inputs")
        raise ValueError(
            "Layer 2 brand_intelligence, Layer 6 format_plan, Layer 7 copy, "
            "and Layer 8 visual_reasoning are required for Layer 9"
        )

    # Platform ratio enforcement
    ratios = {
        "linkedin": (1200, 627),
        "instagram": (1080, 1080),
        "twitter": (1200, 675),
        "x": (1200, 675),
        "story": (1080, 1920),
    }

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
    if blueprint:
        user = (
            user
            + "\n\nAPPROVED CREATIVE BLUEPRINT — use these exact strings for copy/cta elements:\n"
            + f"headline: {blueprint.headline}\n"
            + f"supporting_line: {blueprint.supporting_line}\n"
            + f"body: {blueprint.body}\n"
            + f"cta: {blueprint.cta}\n"
            + f"overlay_zones: {[z.model_dump() if hasattr(z, 'model_dump') else z for z in (blueprint.overlay_zones or [])]}\n"
            + "Place copy elements using overlay_zones relative boxes when provided."
        )

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

        if x < 0:
            x = 0
        if y < 0:
            y = 0
        if w > width:
            w = width
        if h > height:
            h = height
        if x + w > width:
            x = width - w
        if y + h > height:
            y = height - h

        pos["x"] = int(x)
        pos["y"] = int(y)
        pos["width"] = int(w)
        pos["height"] = int(h)

        if el.element_type == "visual":
            image_urls = visual_reasoning.generated_image_urls or []
            if not image_urls and visual_reasoning.generated_image_url:
                image_urls = [visual_reasoning.generated_image_url]
            if image_urls:
                import re

                match = re.search(r"(?:slide|card|visual)[_\-]?(\d+)", el.element_id, re.IGNORECASE)
                if match:
                    idx = int(match.group(1)) - 1
                    idx = max(0, min(idx, len(image_urls) - 1))
                    el.asset_url = image_urls[idx]
                else:
                    el.asset_url = image_urls[0]

    _inject_blueprint_zones(output, blueprint, width, height)

    for img_url in visual_reasoning.generated_image_urls or [visual_reasoning.generated_image_url]:
        if img_url and img_url not in output.assets:
            output.assets.append(img_url)

    logger.info(
        "scene_graph.complete",
        platform=platform,
        dimensions=f"{width}x{height}",
        elements_count=len(output.elements),
        blueprint_bound=bool(blueprint),
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
