from __future__ import annotations

from typing import Any

from app.graph.models.layer2_models import BrandIntelligenceOutput
from app.graph.models.layer6_models import FormatPlanOutput
from app.graph.models.layer7_models import CopyOutput
from app.graph.models.layer8_models import VisualReasoningOutput
from app.prompts.base import BasePromptBuilder


class SceneGraphPromptBuilder(BasePromptBuilder):
    """Builds prompts for Layer 9: Scene Graph Engine."""

    PROMPT_VERSION = "1.0"

    def build_system(self, width: int, height: int, **kwargs: Any) -> str:
        return f"""You are Violyt's Scene Graph Engine. Your job is to convert all copy, visual plans, and assets into a deterministic, render-ready scene graph layout.
You must return a single JSON object matching the SceneGraphOutput schema.

CRITICAL LOGIC & PLACEMENT RULES:
- Canvas dimensions: The target canvas width is {width} and height is {height}. All coordinates and sizes must fit inside this bounding box.
- Background layer: Always include a background element with id "bg" starting at (0, 0) with width {width} and height {height}.
- Element Layering: Define elements from background up: background -> visual -> copy -> logo -> cta -> decorative.
- Position constraints: Avoid element overlapping. Headlines should be placed with ample line heights and margins. 
- Logo zone: Honor the logo zone instruction. Compute and place the logo element within the safe zone margins.
- CTA: Provide a CTA box element with x, y, width, height, background color, border radius, and text properties.
- Assets: Include any generated image asset URLs in the assets list, and link them to their respective visual element's asset_url.

JSON OUTPUT STRUCTURE:
{{
  "platform": "linkedin",
  "platform_ratio": "{width}x{height}",
  "canvas_width": {width},
  "canvas_height": {height},
  "layers": ["background", "visual", "copy", "logo", "cta", "decorative"],
  "elements": [
    {{
      "element_id": "bg",
      "element_type": "background",
      "content": "Description of background fill",
      "position": {{"x": 0, "y": 0, "width": {width}, "height": {height}}},
      "style": {{"color": "#FFFFFF"}}
    }},
    {{
      "element_id": "main_visual",
      "element_type": "visual",
      "content": "Image focus description",
      "position": {{"x": 50, "y": 100, "width": 500, "height": 400}},
      "style": {{"border_radius": 12}},
      "asset_url": "URL_FROM_VISUAL_REASONING"
    }},
    {{
      "element_id": "main_headline",
      "element_type": "copy",
      "content": "Headline copy string",
      "position": {{"x": 600, "y": 120, "width": 550, "height": 100}},
      "style": {{"font_size": 36, "color": "#000000", "font_weight": "bold"}}
    }},
    {{
      "element_id": "cta_button",
      "element_type": "cta",
      "content": "CTA text",
      "position": {{"x": 600, "y": 450, "width": 200, "height": 50}},
      "style": {{"background": "#FF0000", "color": "#FFFFFF", "border_radius": 8}}
    }},
    {{
      "element_id": "logo_mark",
      "element_type": "logo",
      "content": "logo placement",
      "position": {{"x": {width - 150}, "y": {height - 80}, "width": 100, "height": 40}},
      "style": {{"opacity": 1.0}}
    }}
  ],
  "styles": {{
    "font_family": "Arial",
    "theme": "modern"
  }},
  "assets": ["URL_FROM_VISUAL_REASONING"]
}}

Coordinate alignment check: Ensure all element boundaries x + width <= {width} and y + height <= {height}. No element coordinates should be negative.
No preamble. Return ONLY raw JSON."""

    def build_user(
        self,
        brand_intelligence: BrandIntelligenceOutput,
        format_plan: FormatPlanOutput,
        copy: CopyOutput,
        visual_reasoning: VisualReasoningOutput,
        **kwargs: Any,
    ) -> str:
        logo_zone = brand_intelligence.visual_behavior.logo_zone_instruction
        bg_behavior = brand_intelligence.visual_behavior.color_behavior

        return f"""VISUAL DESIGN DIRECTIVES:
Brand Logo Zone: {logo_zone}
Background / Color Strategy: {bg_behavior}
Sophistication: {brand_intelligence.visual_behavior.design_sophistication}
Visual Style: {visual_reasoning.visual_style}
Composition Logic: {visual_reasoning.composition_logic}
Focal Point: {visual_reasoning.focal_point}
Negative Space Plan: {visual_reasoning.negative_space_plan}
Dominant Visual System: {visual_reasoning.dominant_visual_system}

COPY AND ASSET RESOURCES:
Headline: {copy.headline}
Supporting Line: {copy.supporting_line}
Body Copy: {copy.body}
CTA Text: {copy.cta}
Hashtags: {", ".join(copy.hashtags)}
Generated Image URL (Use for visual element's asset_url): {visual_reasoning.generated_image_url}

LAYOUT REQUIREMENTS:
Format: {format_plan.format_strategy} (Archetype: {format_plan.layout_archetype})
Content Structure: {format_plan.content_structure}
Copy Density: {format_plan.copy_density}
Visual Density: {format_plan.visual_density}

Construct the scene graph. Position elements safely relative to the logo zone and focal points. Return ONLY valid JSON matching SceneGraphOutput."""
