from __future__ import annotations

from typing import Any

from app.graph.models.layer2_models import BrandIntelligenceOutput
from app.graph.models.layer4_models import StrategicReasoningOutput
from app.prompts.base import BasePromptBuilder


class ConceptEnginePromptBuilder(BasePromptBuilder):
    """Builds prompts for Layer 5: Creative Concept Engine."""

    PROMPT_VERSION = "1.1"

    def build_system(self, **kwargs: Any) -> str:
        return """\
You are Violyt's Creative Concept Engine. Your output is a single JSON object — nothing else.

TASK: Generate exactly 3 distinct creative concepts for this brand campaign.

STRICT FIELD LENGTH LIMITS (HARD CAPS — DO NOT EXCEED):
- concept_name: 6 words max
- core_idea: 20 words max
- hook: 15 words max
- narrative_angle: 20 words max
- visual_angle: 20 words max
- brand_fit_reason: 20 words max
- selection_reason: 30 words max

RULES:
1. Each concept must have a DIFFERENT strategic angle, narrative, and visual treatment.
2. Every concept must be brand-ownable — could not belong to a different brand.
3. recommended_concept must be a FULL copy of the chosen concept object from all_concepts.
4. rejected_concepts can be an empty array [].
5. diversity_score must reflect genuine concept variety (0.7–0.9 is typical for 3 good concepts).
6. risk_level must be exactly "low", "medium", or "high".
7. copy_density and visual_density must be exactly "low", "medium", or "high".

OUTPUT FORMAT — return ONLY this JSON, no preamble, no markdown:
{
  "all_concepts": [
    {
      "concept_id": "c1",
      "concept_name": "Short Name Here",
      "core_idea": "One clear sentence about the idea.",
      "hook": "Attention-grabbing opening line.",
      "narrative_angle": "How the story unfolds.",
      "visual_angle": "What the viewer sees.",
      "brand_fit_reason": "Why this fits the brand.",
      "risk_level": "low"
    },
    {
      "concept_id": "c2",
      "concept_name": "Different Name",
      "core_idea": "Completely different idea sentence.",
      "hook": "Different hook line.",
      "narrative_angle": "Different story approach.",
      "visual_angle": "Different visual treatment.",
      "brand_fit_reason": "Why this fits the brand.",
      "risk_level": "medium"
    },
    {
      "concept_id": "c3",
      "concept_name": "Third Name",
      "core_idea": "Third distinct idea sentence.",
      "hook": "Third hook line.",
      "narrative_angle": "Third narrative approach.",
      "visual_angle": "Third visual treatment.",
      "brand_fit_reason": "Why this fits the brand.",
      "risk_level": "low"
    }
  ],
  "recommended_concept": {
    "concept_id": "c1",
    "concept_name": "Short Name Here",
    "core_idea": "One clear sentence about the idea.",
    "hook": "Attention-grabbing opening line.",
    "narrative_angle": "How the story unfolds.",
    "visual_angle": "What the viewer sees.",
    "brand_fit_reason": "Why this fits the brand.",
    "risk_level": "low"
  },
  "selection_reason": "Brief reason for recommending c1 over c2 and c3.",
  "rejected_concepts": [],
  "diversity_score": 0.8
}"""

    def build_user(
        self,
        strategic_reasoning: StrategicReasoningOutput,
        brand_intelligence: BrandIntelligenceOutput,
        **kwargs: Any,
    ) -> str:
        # Serialize lists as compact comma-separated strings
        stands_for = ", ".join(brand_intelligence.brand_core.stands_for[:3])
        stands_against = ", ".join(brand_intelligence.brand_core.stands_against[:3])
        fits = ", ".join(brand_intelligence.creative_territory.get("fits", [])[:4])
        avoids = ", ".join(brand_intelligence.creative_territory.get("avoids", [])[:4])
        guardrails = "; ".join(brand_intelligence.guardrails[:4])

        return f"""\
STRATEGIC DIRECTION:
Problem: {strategic_reasoning.strategic_problem}
Brand truth: {strategic_reasoning.brand_truth}
Approach: {strategic_reasoning.recommended_approach}
Attention: {strategic_reasoning.attention_strategy}
Emotion: {strategic_reasoning.emotional_strategy}
Visual: {strategic_reasoning.visual_strategy}

BRAND SNAPSHOT:
Brand: {brand_intelligence.brand_core.brand_name}
Value prop: {brand_intelligence.brand_core.value_proposition}
Market tension: {brand_intelligence.brand_core.market_tension}
Stands for: {stands_for}
Stands against: {stands_against}
Tone: {brand_intelligence.communication_behavior.tone_spectrum}
Emotional territory: {brand_intelligence.communication_behavior.emotional_territory}
Visual mood: {brand_intelligence.visual_behavior.visual_mood}
Creative fits: {fits}
Creative avoids: {avoids}
Guardrails: {guardrails}

Generate exactly 3 distinct concepts. Keep ALL text fields under the word limits. Return ONLY the JSON object."""
