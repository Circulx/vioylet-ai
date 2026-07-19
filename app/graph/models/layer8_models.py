from pydantic import BaseModel
from typing import List, Literal, Optional


class ContentSection(BaseModel):
    section_id: str
    title: str
    body: Optional[str] = None
    metric: Optional[str] = None  # e.g., "8.25%"
    visual_metaphor: Optional[str] = None  # e.g., "3D piggy bank"


class TextOverlayElement(BaseModel):
    element_type: Literal[
        "headline", "subheadline", "supporting_line", "body", "cta", "label", "footer", "section_label", "stat", "badge"
    ]
    text: str
    font_size: int
    color_hex: str
    position_box: str  # e.g. "top-center", "bottom-left", "center-right", "footer-strip"


class VisualReasoningOutput(BaseModel):
    dominant_visual_system: Literal[
        "generated_image", "type_led", "illustration", "infographic", "data_visual", "product_visual"
    ]
    visual_format_type: Literal[
        "comparison", "timeline", "chart", "matrix", 
        "process_flow", "hero_scene", "data_grid"
    ]
    visual_style: str
    composition_logic: str
    focal_point: str
    negative_space_plan: str
    color_behavior: str
    logo_zone_instruction: str
    typography_behavior: Optional[str] = None
    image_prompt_direction: str
    content_sections: List[ContentSection] = []
    text_overlay_plan: List[TextOverlayElement] = []
    generated_image_url: str = ""
    generated_image_urls: List[str] = []

