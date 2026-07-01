from pydantic import BaseModel
from typing import List, Literal, Optional


class SlidePlan(BaseModel):
    slide_number: int
    role: str
    focus: str
    copy_intent: str
    visual_intent: str


class FormatPlanOutput(BaseModel):
    format_strategy: str
    content_structure: str
    copy_density: Literal["low", "medium", "high"]
    visual_density: Literal["low", "medium", "high"]
    layout_archetype: str
    slide_plan: List[SlidePlan]
    notes: Optional[str] = None
