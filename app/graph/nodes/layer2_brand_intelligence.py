from app.graph.state import ViolytState
from app.graph.models.layer2_models import (
    BrandIntelligenceOutput,
    BrandCore,
    CommunicationBehavior,
    VisualBehavior,
    AudienceModel,
)


async def layer2_brand_intelligence(state: ViolytState) -> dict:
    brand_id = state.get("brand_id", "unknown")

    return {
        "brand_intelligence": BrandIntelligenceOutput(
            brand_core=BrandCore(
                brand_name=brand_id,
                value_proposition="Calm, credible financial partner for predictable income.",
                market_tension="Investors feel fixed income is boring and inaccessible.",
                stands_for=["predictability", "trust", "accessibility"],
                stands_against=["hype", "complexity", "risk-taking"],
                competitive_position="Disciplined, data-forward alternative to fintech noise.",
            ),
            communication_behavior=CommunicationBehavior(
                tone_spectrum="authoritative but accessible",
                emotional_territory="quiet confidence",
                boldness_level="medium",
                authority_level="high",
                simplicity_level="high",
                preferred_language_behavior="plain evidence, no jargon",
                prohibited_phrases=["get rich quick", "guaranteed returns"],
            ),
            visual_behavior=VisualBehavior(
                visual_mood="editorial, minimal, data-forward",
                design_sophistication="moderate",
                color_behavior="neutral base with calm accent",
                image_behavior="clean typography, subtle data visuals",
                logo_zone_instruction="bottom-right corner, clear margin",
                typography_behavior="modern sans-serif, high readability",
            ),
            creative_territory={"fits": ["calm charts", "trust narratives"], "avoids": ["aggressive sales"]},
            audience_model=AudienceModel(
                primary_persona="professional exploring fixed income",
                secondary_persona=None,
                core_motivations=["stability", "predictability", "peace of mind"],
                core_objections=["bonds are boring", "yields are low"],
                emotional_needs=["confidence", "clarity"],
            ),
            guardrails=["no guaranteed return claims", "always disclose risk"],
            weak_signals=[],
            confidence=0.88,
        )
    }
