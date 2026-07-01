from pydantic import BaseModel
from typing import List


class RejectedApproach(BaseModel):
    approach_name: str
    rejection_reason: str


class StrategicReasoningOutput(BaseModel):
    strategic_problem: str
    brand_truth: str
    recommended_approach: str
    rejected_approaches: List[RejectedApproach]
    attention_strategy: str
    emotional_strategy: str
    visual_strategy: str
    content_pacing_strategy: str
