from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class BrandCore(BaseModel):
    brand_name: str
    value_proposition: str
    market_tension: str
    stands_for: List[str]
    stands_against: List[str]
    competitive_position: str


class CommunicationBehavior(BaseModel):
    tone_spectrum: str
    emotional_territory: str
    boldness_level: Literal["low", "medium", "high"]
    authority_level: Literal["low", "medium", "high"]
    simplicity_level: Literal["low", "medium", "high"]
    preferred_language_behavior: str
    prohibited_phrases: List[str]


class VisualBehavior(BaseModel):
    visual_mood: str
    design_sophistication: Literal["minimal", "moderate", "elaborate"]
    color_behavior: str
    image_behavior: str
    logo_zone_instruction: str
    typography_behavior: str


class AudienceModel(BaseModel):
    primary_persona: str
    secondary_persona: Optional[str] = None
    core_motivations: List[str]
    core_objections: List[str]
    emotional_needs: List[str]


class BrandIntelligenceOutput(BaseModel):
    brand_core: BrandCore
    communication_behavior: CommunicationBehavior
    visual_behavior: VisualBehavior
    creative_territory: dict
    audience_model: AudienceModel
    guardrails: List[str]
    weak_signals: List[str]
    confidence: float = Field(ge=0.0, le=1.0)
