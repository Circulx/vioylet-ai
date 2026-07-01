from pydantic import BaseModel
from typing import List, Literal


class CampaignBriefOutput(BaseModel):
    campaign_objective: str
    funnel_stage: Literal["awareness", "consideration", "conversion", "retention", "education"]
    audience_intent: str
    content_role: Literal["educate", "persuade", "announce", "compare", "inspire", "convert"]
    platform_behavior_constraints: str
    information_density: Literal["low", "medium", "high"]
    creative_risk_level: Literal["low", "medium", "high"]
    persuasion_model: str
    missing_critical_inputs: List[str]
