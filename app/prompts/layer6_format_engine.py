from __future__ import annotations

from typing import Any

from app.graph.models.layer2_models import BrandIntelligenceOutput
from app.graph.models.layer4_models import StrategicReasoningOutput
from app.prompts.base import BasePromptBuilder


class FormatEnginePromptBuilder(BasePromptBuilder):
    """Builds prompts for Layer 6: Format Intelligence Engine."""

    PROMPT_VERSION = "1.1"

    def build_system(self, platform: str = "", fmt: str = "", **kwargs: Any) -> str:
        format_instructions = self._format_specific_instructions(fmt)

        return f"""\
You are Violyt's Format Intelligence Engine. Output a single JSON object — nothing else.

PLATFORM: {platform}
FORMAT: {fmt}

{format_instructions}

RULES:
1. The format plan must be architecturally specific to the format type.
2. Each slide must have a distinct role, focus, copy_intent, and visual_intent.
3. Keep ALL text fields under 25 words.
4. copy_density and visual_density must be exactly "low", "medium", or "high".
5. layout_archetype is a short label (3–5 words max).

OUTPUT FORMAT — return ONLY this JSON, no preamble, no markdown:
{{
  "format_strategy": "One sentence describing the format approach.",
  "content_structure": "One sentence describing how content is organized.",
  "copy_density": "low",
  "visual_density": "medium",
  "layout_archetype": "Bold visual + minimal text",
  "slide_plan": [
    {{
      "slide_number": 1,
      "role": "hook",
      "focus": "What this slide focuses on.",
      "copy_intent": "What the copy achieves.",
      "visual_intent": "What the visual communicates."
    }}
  ],
  "notes": null
}}"""

    def build_user(
        self,
        strategic_reasoning: StrategicReasoningOutput,
        brand_intelligence: BrandIntelligenceOutput,
        platform: str,
        format: str,
        **kwargs: Any,
    ) -> str:
        return f"""\
STRATEGIC DIRECTION:
Problem: {strategic_reasoning.strategic_problem}
Brand truth: {strategic_reasoning.brand_truth}
Approach: {strategic_reasoning.recommended_approach}
Attention strategy: {strategic_reasoning.attention_strategy}
Content pacing: {strategic_reasoning.content_pacing_strategy}

BRAND:
Name: {brand_intelligence.brand_core.brand_name}
Tone: {brand_intelligence.communication_behavior.tone_spectrum}
Visual mood: {brand_intelligence.visual_behavior.visual_mood}
Design sophistication: {brand_intelligence.visual_behavior.design_sophistication}

PLATFORM: {platform}
FORMAT: {format}

Build the format-native content structure with a complete slide_plan. Keep all text fields under 25 words. Return ONLY the JSON object."""

    @staticmethod
    def _format_specific_instructions(fmt: str) -> str:
        if fmt == "carousel":
            return """\
CAROUSEL FORMAT:
- Narrative flow: hook slide → insight slides → CTA slide
- Typically 5-7 slides
- Each slide has ONE clear role: hook | insight | proof | brand_truth | cta
- Opening slide grabs attention; closing slide drives action
- slide_plan must have 5-7 entries"""

        if fmt == "infographic":
            return """\
INFOGRAPHIC FORMAT:
- Information hierarchy: title → data/insights → context → CTA
- Typically 4-6 sections
- Each section presents one data point or insight visually
- slide_plan entries represent sections, not slides
- Typical roles: header | data_point | comparison | context | cta"""

        return """\
STATIC FORMAT:
- Single frame with one dominant message
- Hierarchy: headline → supporting line → CTA
- One visual focal point, minimal text
- slide_plan has exactly 1 entry with role: "single_frame\""""
