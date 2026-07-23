from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class OverlayZone(BaseModel):
    """Optional text placement hint (legacy). Final creatives bake text via AI image model."""

    zone_id: str
    role: str  # headline | supporting_line | body | cta | label | section_label | stat | quote
    text: str
    priority: int = 1
    # Relative 0–1 boxes (optional guidance for L9 / renderer)
    x_rel: Optional[float] = None
    y_rel: Optional[float] = None
    w_rel: Optional[float] = None
    h_rel: Optional[float] = None
    slide_number: Optional[int] = None  # for carousel frames


class BlueprintSlide(BaseModel):
    slide_number: int
    role: str = "insight"  # hook | insight | proof | cta | supporting
    headline: str
    body: str = ""
    label: Optional[str] = None
    supporting_line: Optional[str] = None
    cta: Optional[str] = None


class BlueprintInfographicSection(BaseModel):
    section_label: str
    stat: Optional[str] = None
    includes: List[str] = Field(default_factory=list)
    body: str = ""
    icon_hint: Optional[str] = None


class CreativeBlueprint(BaseModel):
    """Format-aware creative content package shown for user approval before artwork."""

    # Meta
    purpose: str = ""
    intent: str = "awareness"
    audience: str = ""
    platform: str = "linkedin"
    format: Literal["static", "carousel", "infographic"] = "static"
    tone: str = ""

    # Story
    hook: str = ""
    story_flow: List[str] = Field(default_factory=list)
    messaging_pillars: List[str] = Field(default_factory=list)
    cta: str = ""

    # Static / shared text
    headline: str = ""
    supporting_line: Optional[str] = None
    body: str = ""
    labels: List[str] = Field(default_factory=list)
    hashtags: List[str] = Field(default_factory=list)

    # Carousel
    slides: List[BlueprintSlide] = Field(default_factory=list)

    # Infographic
    title: Optional[str] = None
    sections: List[BlueprintInfographicSection] = Field(default_factory=list)
    problem_statement: Optional[str] = None
    solution_statement: Optional[str] = None
    proof_points: List[str] = Field(default_factory=list)
    stat_highlights: List[str] = Field(default_factory=list)
    process_steps: List[str] = Field(default_factory=list)
    customer_quote: Optional[str] = None
    customer_name: Optional[str] = None

    # Design plan
    visual_hierarchy: List[str] = Field(default_factory=list)
    text_density: str = "moderate"  # sparse | moderate | dense
    layout_archetype: str = ""
    overlay_zones: List[OverlayZone] = Field(default_factory=list)

    # Quality
    brand_alignment_notes: List[str] = Field(default_factory=list)
    validation_checklist: List[str] = Field(default_factory=list)
    missing_critical: List[str] = Field(default_factory=list)
    claim_safety_notes: List[str] = Field(default_factory=list)
