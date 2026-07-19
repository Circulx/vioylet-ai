from __future__ import annotations

from typing import Any

from app.graph.models.layer2_models import BrandIntelligenceOutput
from app.prompts.base import BasePromptBuilder


class BriefInterpreterPromptBuilder(BasePromptBuilder):
    """Builds prompts for Layer 3: Campaign Brief Interpreter."""

    PROMPT_VERSION = "1.1"

    def build_system(self, **kwargs: Any) -> str:
        return """You are Violyt's Campaign Brief Interpreter.
Convert a plain-English user request into an agency-grade campaign brief.
Infer all strategic parameters without requiring the user to specify them.

CRITICAL RULES:
- Only flag missing_critical_inputs for genuinely unresolvable information.
- Never ask the user to provide inferrable information.
- Match the brief to the brand's behavior model.
- Every field must have a concrete value — never use field names as values.
- missing_critical_inputs is an ARRAY of strings (e.g. []), not a value for any other field.

Return ONLY valid JSON with this exact structure:
{
  "campaign_objective": "a clear objective statement",
  "funnel_stage": "one of: awareness, consideration, conversion, retention, education",
  "audience_intent": "what the audience wants to achieve",
  "content_role": "one of: educate, persuade, announce, compare, inspire, convert",
  "platform_behavior_constraints": "platform-specific constraints",
  "information_density": "one of: low, medium, high",
  "creative_risk_level": "one of: low, medium, high",
  "persuasion_model": "the persuasion approach",
  "missing_critical_inputs": []
}

No preamble. No explanation. No markdown. JSON only."""

    def build_user(
        self,
        user_prompt: str,
        platform: str,
        format: str,
        brand_intelligence: BrandIntelligenceOutput,
        **kwargs: Any,
    ) -> str:
        return f"""USER REQUEST:
{user_prompt}

PLATFORM: {platform}
FORMAT: {format}

BRAND BEHAVIOR MODEL:
- Brand name: {brand_intelligence.brand_core.brand_name}
- Value proposition: {brand_intelligence.brand_core.value_proposition}
- Tone spectrum: {brand_intelligence.communication_behavior.tone_spectrum}
- Emotional territory: {brand_intelligence.communication_behavior.emotional_territory}
- Visual mood: {brand_intelligence.visual_behavior.visual_mood}
- Guardrails: {brand_intelligence.guardrails}

Convert this into a complete campaign brief."""
