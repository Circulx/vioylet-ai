from pydantic import BaseModel
from typing import Literal, Optional


class VisualReasoningOutput(BaseModel):
    dominant_visual_system: Literal[
        "generated_image", "type_led", "illustration", "infographic", "data_visual", "product_visual"
    ]
    visual_style: str
    composition_logic: str
    focal_point: str
    negative_space_plan: str
    color_behavior: str
    logo_zone_instruction: str
    typography_behavior: Optional[str] = None
    image_prompt_direction: str
    generated_image_url: str
