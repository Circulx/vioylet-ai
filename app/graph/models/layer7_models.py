from pydantic import BaseModel, Field
from typing import List, Optional


class CopySlide(BaseModel):
    slide_number: int
    headline: str
    supporting_line: Optional[str] = None
    body: str
    cta: Optional[str] = None


class InfographicSection(BaseModel):
    """A structured infographic section (table row) with a label, stat/metric, bullet
    breakdown of what it includes, and a supporting explanation of why it matters."""
    section_label: str           # e.g. "Government Securities", "Corporate Debt"
    stat: Optional[str] = None   # e.g. "45%-65%" — key metric/range for this section
    includes: List[str] = Field(default_factory=list)  # 3 short bullets: "what it includes"
    body: str                    # 2-3 sentence "why" explanation for the renderer's third column
    icon_hint: Optional[str] = None  # e.g. "growth", "shield", "chart" — visual cue for renderer


class CopyOutput(BaseModel):
    headline: str
    supporting_line: Optional[str] = None
    body: str
    cta: str
    hashtags: List[str]
    slide_copy: List[CopySlide]
    claim_safety_notes: List[str]

    # Infographic-specific structured content
    # These fields are populated when format == "infographic"
    infographic_sections: List[InfographicSection] = Field(default_factory=list)
    problem_statement: Optional[str] = None
    solution_statement: Optional[str] = None
    proof_points: List[str] = Field(default_factory=list)
    stat_highlights: List[str] = Field(default_factory=list)
    customer_quote: Optional[str] = None
    customer_name: Optional[str] = None
    process_steps: List[str] = Field(default_factory=list)
