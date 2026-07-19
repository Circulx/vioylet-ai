from __future__ import annotations

from typing import Any

from app.graph.models.layer2_models import BrandIntelligenceOutput
from app.graph.models.layer3_models import CampaignBriefOutput
from app.prompts.base import BasePromptBuilder


class StrategicReasoningPromptBuilder(BasePromptBuilder):
    """Builds prompts for Layer 4: Strategic Reasoning Engine."""

    PROMPT_VERSION = "1.3"

    def build_system(self, **kwargs: Any) -> str:
        return """You are Violyt's Strategic Reasoning Engine.
Before any creative output is generated, reason through the campaign like a senior advertising strategist at a top agency.

You MUST evaluate:
- Why this campaign should exist
- What audience tension it solves
- What brand truth it should express
- What communication approach is strongest
- What emotional reaction is required
- What visual behavior is most suitable
- What platform behavior matters
- What should be avoided for this brand

Consider multiple possible strategic approaches internally.
Document the ones you REJECTED and explain why.
Select the single strongest direction.

DO NOT generate final copy.
DO NOT generate design directions.
STRATEGIC REASONING ONLY.

Return ONLY valid JSON with this exact structure:
{
  "strategic_problem": "string",
  "brand_truth": "string",
  "recommended_approach": "string",
  "rejected_approaches": [
    {
      "approach_name": "string",
      "rejection_reason": "string"
    }
  ],
  "attention_strategy": "string",
  "emotional_strategy": "string",
  "visual_strategy": "string",
  "content_pacing_strategy": "string"
}

No preamble. No explanation. No markdown. JSON only."""

    def build_user(
        self,
        campaign_brief: CampaignBriefOutput,
        brand_intelligence: BrandIntelligenceOutput,
        **kwargs: Any,
    ) -> str:
        return f"""CAMPAIGN BRIEF:
- Objective: {campaign_brief.campaign_objective}
- Funnel stage: {campaign_brief.funnel_stage}
- Audience intent: {campaign_brief.audience_intent}
- Content role: {campaign_brief.content_role}
- Platform constraints: {campaign_brief.platform_behavior_constraints}
- Persuasion model: {campaign_brief.persuasion_model}

BRAND BEHAVIOR MODEL:
- Brand name: {brand_intelligence.brand_core.brand_name}
- Value proposition: {brand_intelligence.brand_core.value_proposition}
- Market tension: {brand_intelligence.brand_core.market_tension}
- Stands for: {brand_intelligence.brand_core.stands_for}
- Stands against: {brand_intelligence.brand_core.stands_against}
- Tone spectrum: {brand_intelligence.communication_behavior.tone_spectrum}
- Emotional territory: {brand_intelligence.communication_behavior.emotional_territory}
- Visual mood: {brand_intelligence.visual_behavior.visual_mood}
- Creative territory fits: {brand_intelligence.creative_territory.get('fits', [])}
- Creative territory avoids: {brand_intelligence.creative_territory.get('avoids', [])}
- Guardrails: {brand_intelligence.guardrails}

Reason through the campaign and select the strongest strategic direction."""
