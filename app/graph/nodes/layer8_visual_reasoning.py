from app.graph.state import ViolytState
from app.graph.models.layer8_models import VisualReasoningOutput


async def layer8_visual_reasoning(state: ViolytState) -> dict:
    brand_id = state.get("brand_id", "unknown")
    platform = state.get("platform", "linkedin")

    return {
        "visual_reasoning": VisualReasoningOutput(
            dominant_visual_system="type_led",
            visual_style="editorial minimal with calm accent",
            composition_logic="single focal point, generous negative space, logo-safe zone",
            focal_point="headline and supporting line centered",
            negative_space_plan="40% negative space around the message",
            color_behavior="neutral base with one calm accent",
            logo_zone_instruction="bottom-right corner, clear margin",
            typography_behavior="modern sans-serif, high contrast",
            image_prompt_direction=f"Minimal editorial {platform} creative for {brand_id}, clean typography, calm palette, no human figures",
            generated_image_url="https://example.com/mock/generated_image.png",
        )
    }
