from pydantic import BaseModel, Field
from typing import List, Literal


class RepairInstruction(BaseModel):
    target_layer: str
    failure_reason: str
    repair_action: str
    priority: Literal["critical", "major", "minor"]


class EvaluationOutput(BaseModel):
    brand_alignment_score: float = Field(ge=0.0, le=1.0)
    prompt_match_score: float = Field(ge=0.0, le=1.0)
    audience_relevance_score: float = Field(ge=0.0, le=1.0)
    originality_score: float = Field(ge=0.0, le=1.0)
    visual_quality_score: float = Field(ge=0.0, le=1.0)
    format_fit_score: float = Field(ge=0.0, le=1.0)
    brand_uniqueness_score: float = Field(ge=0.0, le=1.0)
    strategic_quality_score: float = Field(ge=0.0, le=1.0)
    contamination_risk: Literal["low", "medium", "high"]
    overall_pass: bool
    required_repairs: List[RepairInstruction]
    evaluator_reasoning: str
