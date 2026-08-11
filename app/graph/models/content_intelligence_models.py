from __future__ import annotations

"""Content Intelligence models — Intent → Research → Insight → Narrative → Format."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class SubQuestion(BaseModel):
    question: str
    evidence_needed: str = "quantifiable statistics with sources"
    priority: int = 1


class IntentDecomposition(BaseModel):
    core_question: str
    topic: str = ""
    objective: str = "explain_with_evidence"
    informational_need: Literal[
        "data_points",
        "explanation",
        "comparison",
        "ranking",
        "howto",
        "opinion",
    ] = "data_points"
    sub_questions: List[SubQuestion] = Field(default_factory=list)
    must_answer_why: bool = False


class EvidenceItem(BaseModel):
    claim: str
    value: str = ""
    source_url: str = ""
    source_title: str = ""
    date: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_type: Literal["statistic", "fact", "insight", "explanation", "opinion"] = "statistic"
    approved_for_creative: bool = False


class NarrativeBeat(BaseModel):
    role: Literal["hook", "scale", "why", "effect", "idea", "takeaway", "cta"]
    message: str
    supporting_stat: str = ""


class FormatArchitecture(BaseModel):
    format_name: str = "infographic"
    hero_statistic: str = ""
    supporting_data_points: List[str] = Field(default_factory=list)
    core_insight: str = ""
    copy_density: Literal["short", "medium"] = "short"
    hierarchy_notes: str = ""
    visual_plan: str = ""


class ContentIntelligenceOutput(BaseModel):
    """Authoritative intelligence package consumed by L7 / L7c / L8."""

    intent: IntentDecomposition
    research_queries: List[str] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    insight_thesis: str = ""
    narrative_beats: List[NarrativeBeat] = Field(default_factory=list)
    format_architecture: FormatArchitecture = Field(default_factory=FormatArchitecture)
    brand_thinking_notes: List[str] = Field(default_factory=list)
    qa_self_score: dict = Field(default_factory=dict)
    live_research: dict = Field(default_factory=dict)
