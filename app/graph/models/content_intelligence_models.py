from __future__ import annotations

"""Content Intelligence models — Understand → Evidence → Insight spine."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class SubQuestion(BaseModel):
    question: str
    evidence_needed: str = "quantifiable statistics with sources"
    priority: int = 1


class IntentDecomposition(BaseModel):
    """Structured Intent Brief (Understand layer)."""

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
    # Intent Brief extensions
    geography: str = ""
    freshness: Literal["current", "recent", "any"] = "recent"
    depth: Literal["simplified", "standard", "deep"] = "simplified"
    audience_hint: str = ""
    evidence_requirement: str = "real quantitative data with sources"
    content_type: str = ""
    compliance_sensitive: bool = False
    intent_brief: str = ""


class EvidenceItem(BaseModel):
    claim: str
    value: str = ""
    source_url: str = ""
    source_title: str = ""
    date: str = ""
    data_period: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_type: Literal["statistic", "fact", "insight", "explanation", "opinion"] = "statistic"
    approved_for_creative: bool = False
    # Verify / Prioritize / Interpret
    source_type: Literal[
        "government",
        "regulator",
        "industry",
        "media",
        "secondary",
        "unknown",
    ] = "unknown"
    corroborated: bool = False
    publishable: bool = False
    priority_tier: Literal["must_know", "useful", "optional", "irrelevant"] = "optional"
    priority_score: float = Field(default=0.0, ge=0.0, le=1.0)
    interpretation: str = ""
    certainty: Literal["fact", "inference", "speculation"] = "fact"


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


class InsightCandidate(BaseModel):
    territory: str = ""
    insight: str
    score: float = Field(default=0.5, ge=0.0, le=1.0)
    true_test: bool = True
    interesting_test: bool = True
    relevant_test: bool = True
    useful_test: bool = True


class ContentIntelligenceOutput(BaseModel):
    """Authoritative intelligence package consumed by L5 / L7 / L7c / L8."""

    intent: IntentDecomposition
    research_queries: List[str] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    insight_thesis: str = ""
    primary_insight: str = ""
    supporting_insights: List[str] = Field(default_factory=list)
    insight_candidates: List[InsightCandidate] = Field(default_factory=list)
    reasoning_map: str = ""
    narrative_beats: List[NarrativeBeat] = Field(default_factory=list)
    format_architecture: FormatArchitecture = Field(default_factory=FormatArchitecture)
    brand_thinking_notes: List[str] = Field(default_factory=list)
    qa_self_score: dict = Field(default_factory=dict)
    live_research: dict = Field(default_factory=dict)
