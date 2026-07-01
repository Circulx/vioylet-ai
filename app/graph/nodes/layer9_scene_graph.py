from app.graph.state import ViolytState
from app.graph.models.layer9_models import SceneGraphOutput, SceneElement


async def layer9_scene_graph(state: ViolytState) -> dict:
    platform = state.get("platform", "linkedin")
    fmt = state.get("format", "static")

    ratios = {
        "linkedin": (1200, 627),
        "instagram": (1080, 1080),
        "twitter": (1200, 675),
        "story": (1080, 1920),
    }
    width, height = ratios.get(platform, (1200, 627))

    elements = [
        SceneElement(
            element_id="bg",
            element_type="background",
            content="neutral base",
            position={"x": 0, "y": 0, "width": width, "height": height},
            style={"color": "#F5F5F5"},
        ),
        SceneElement(
            element_id="headline",
            element_type="copy",
            content="Predictability is a power, not a limitation.",
            position={"x": 80, "y": 200, "width": width - 160, "height": 80},
            style={"font_size": 42, "color": "#111111"},
        ),
        SceneElement(
            element_id="cta",
            element_type="cta",
            content="Learn more",
            position={"x": 80, "y": height - 120, "width": 200, "height": 48},
            style={"background": "#333333", "color": "#FFFFFF"},
        ),
        SceneElement(
            element_id="logo",
            element_type="logo",
            content="brand logo",
            position={"x": width - 160, "y": height - 100, "width": 80, "height": 40},
            style={"safe_zone": "clear"},
        ),
    ]

    return {
        "scene_graph": SceneGraphOutput(
            platform=platform,
            platform_ratio=f"{width}x{height}",
            canvas_width=width,
            canvas_height=height,
            layers=["background", "visual", "copy", "cta", "logo"],
            elements=elements,
            styles={"palette": ["#F5F5F5", "#111111", "#333333"], "typography": "sans-serif"},
            assets=["https://example.com/mock/generated_image.png"],
        )
    }
