from app.graph.state import ViolytState
from app.graph.models.layer3_models import CampaignBriefOutput


async def layer3_brief_interpreter(state: ViolytState) -> dict:
    return {
        "campaign_brief": CampaignBriefOutput(
            campaign_objective="Educate professionals on the value of predictable income through bonds.",
            funnel_stage="education",
            audience_intent="exploring fixed income as a stable portfolio component",
            content_role="educate",
            platform_behavior_constraints="professional, evidence-friendly, no clickbait",
            information_density="medium",
            creative_risk_level="low",
            persuasion_model="evidence-based trust building",
            missing_critical_inputs=[],
        )
    }
