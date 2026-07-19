from __future__ import annotations

from typing import Any

from app.graph.models.layer1_models import RetrievedChunk
from app.prompts.base import BasePromptBuilder


class BrandIntelligencePromptBuilder(BasePromptBuilder):
    """Builds prompts for Layer 2: Brand Intelligence Engine."""

    PROMPT_VERSION = "1.2"

    def build_system(self, **kwargs: Any) -> str:
        return """You are Violyt's Brand Intelligence Engine.
Your job is NOT to summarize brand data.
Your job is to convert retrieved brand data into a strategic brand behavior model.

CRITICAL RULES:
- Do not invent brand facts. If signals are weak, mark them in weak_signals.
- Do not produce generic or interchangeable brand behavior.
- The same architecture works across all brands, but the resulting behavior must be UNIQUE to the selected brand.
- Every output field must be brand-conditioned, not template-filled.
- Confidence below 0.5 means brand data is too sparse to proceed safely.

Return ONLY valid JSON with this exact structure:
{
  "brand_core": {
    "brand_name": "string",
    "value_proposition": "string",
    "market_tension": "string",
    "stands_for": ["string", ...],
    "stands_against": ["string", ...],
    "competitive_position": "string"
  },
  "communication_behavior": {
    "tone_spectrum": "string",
    "emotional_territory": "string",
    "boldness_level": "low|medium|high",
    "authority_level": "low|medium|high",
    "simplicity_level": "low|medium|high",
    "preferred_language_behavior": "string",
    "prohibited_phrases": ["string", ...]
  },
  "visual_behavior": {
    "visual_mood": "string",
    "design_sophistication": "minimal|moderate|elaborate",
    "color_behavior": "string",
    "image_behavior": "string",
    "logo_zone_instruction": "string",
    "typography_behavior": "string"
  },
  "creative_territory": {},
  "audience_model": {
    "primary_persona": "string",
    "secondary_persona": "string|null",
    "core_motivations": ["string", ...],
    "core_objections": ["string", ...],
    "emotional_needs": ["string", ...]
  },
  "guardrails": ["string", ...],
  "weak_signals": ["string", ...],
  "confidence": 0.0-1.0
}

No preamble. No explanation. No markdown. JSON only."""

    def build_user(
        self,
        brand_id: str,
        high_context: list[RetrievedChunk],
        medium_context: list[RetrievedChunk],
        weak_signals: list[str] | None = None,
        **kwargs: Any,
    ) -> str:
        return f"""Brand ID: {brand_id}

HIGH RELEVANCE BRAND DATA:
{self._format_chunks(high_context)}

MEDIUM RELEVANCE BRAND DATA:
{self._format_chunks(medium_context)}

Known weak signals from retrieval: {weak_signals or []}

Build the complete brand behavior model."""

    def _format_chunks(self, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return "No chunks available."
        return "\n---\n".join(
            [
                f"Source: {c.source}\nSection: {c.section}\nInfluence area: {c.influence_area}\nContent: {c.content_summary}"
                for c in chunks
            ]
        )
