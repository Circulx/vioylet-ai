from pydantic import BaseModel, Field
from typing import List, Literal


class Concept(BaseModel):
    concept_id: str
    concept_name: str
    core_idea: str
    hook: str
    narrative_angle: str
    visual_angle: str
    brand_fit_reason: str
    risk_level: Literal["low", "medium", "high"]


class CreativeConceptsOutput(BaseModel):
    all_concepts: List[Concept]
    recommended_concept: Concept
    selection_reason: str
    rejected_concepts: List[dict]
    diversity_score: float = Field(ge=0.0, le=1.0)
