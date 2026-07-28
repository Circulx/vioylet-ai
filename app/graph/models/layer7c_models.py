from __future__ import annotations

from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class OverlayZone(BaseModel):
    """Optional text placement hint (legacy). Final creatives bake text via AI image model."""

    zone_id: str = ""
    role: str = "headline"  # headline | supporting_line | body | cta | label | section_label | stat | quote
    text: str = ""
    priority: int = 1
    x_rel: Optional[float] = None
    y_rel: Optional[float] = None
    w_rel: Optional[float] = None
    h_rel: Optional[float] = None
    slide_number: Optional[int] = None


class BlueprintSlide(BaseModel):
    slide_number: int = 1
    role: str = "insight"  # hook | insight | proof | cta | supporting
    headline: str = ""
    body: str = ""
    label: Optional[str] = None
    supporting_line: Optional[str] = None
    cta: Optional[str] = None
    # Three ONE-WORD bottom chip labels for this slide (never truncated phrases)
    chip_labels: List[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_slide(cls, data: Any) -> Any:
        """LLM often omits slide_number — fill instead of crashing Phase 1."""
        if not isinstance(data, dict):
            return data
        out = dict(data)
        body = str(out.get("body") or "").strip()
        headline = str(out.get("headline") or out.get("title") or "").strip()
        if not headline and body:
            words = body.split(".")[0].strip().split()
            headline = " ".join(words[:10]) if words else "Key point"
        out["headline"] = headline or "Key point"
        out["body"] = body
        try:
            out["slide_number"] = int(out["slide_number"]) if out.get("slide_number") is not None else 1
        except (TypeError, ValueError):
            out["slide_number"] = 1
        if not out.get("role"):
            out["role"] = "insight"
        chips = out.get("chip_labels") or out.get("chips") or []
        if isinstance(chips, str):
            chips = [c.strip() for c in chips.replace("|", ",").split(",") if c.strip()]
        if isinstance(chips, list):
            cleaned: list[str] = []
            for c in chips[:3]:
                w = " ".join(str(c).split()).strip()
                if not w:
                    continue
                # Force one clear word (or short compound) so SEBI never eats half a phrase
                cleaned.append(w.split()[0][:14])
            out["chip_labels"] = cleaned
        else:
            out["chip_labels"] = []
        return out


class BlueprintInfographicSection(BaseModel):
    section_label: str = ""
    stat: Optional[str] = None
    includes: List[str] = Field(default_factory=list)
    body: str = ""
    icon_hint: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_section(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out = dict(data)
        if not out.get("section_label"):
            out["section_label"] = (
                str(out.get("label") or out.get("title") or out.get("name") or "Item").strip()
                or "Item"
            )
        if out.get("body") is None:
            out["body"] = ""
        return out


class BlueprintSource(BaseModel):
    title: str = ""
    url: str = ""


class CreativeBlueprint(BaseModel):
    """Format-aware creative content package shown for user approval before artwork."""

    # Meta
    purpose: str = ""
    intent: str = "awareness"
    audience: str = ""
    platform: str = "linkedin"
    format: Literal["static", "carousel", "infographic"] = "static"
    tone: str = ""
    layout_type: str = ""  # carousel_story | static_hub_facts | static_ranking

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

    # Infographic / hub / ranking
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

    # Live research sources (shown on image footer + chat)
    sources: List[BlueprintSource] = Field(default_factory=list)
    source_footer: str = ""  # e.g. "Source: dpiit.gov.in · rbi.org.in"

    # Quality
    brand_alignment_notes: List[str] = Field(default_factory=list)
    validation_checklist: List[str] = Field(default_factory=list)
    missing_critical: List[str] = Field(default_factory=list)
    claim_safety_notes: List[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_format(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out = dict(data)
        fmt = str(out.get("format") or "static").strip().lower()
        if fmt not in ("static", "carousel", "infographic"):
            # layout_type carousel_story often arrives without format=carousel
            layout = str(out.get("layout_type") or "").strip().lower()
            if layout == "carousel_story" or out.get("slides"):
                fmt = "carousel"
            elif layout in ("static_hub_facts", "static_ranking") or out.get("sections"):
                fmt = "static"
            else:
                fmt = "static"
        out["format"] = fmt
        return out

    @model_validator(mode="after")
    def _renumber_slides(self) -> CreativeBlueprint:
        roles = ["hook", "insight", "proof", "cta", "insight", "insight", "cta"]
        for i, slide in enumerate(self.slides or [], start=1):
            slide.slide_number = i
            if not (slide.headline or "").strip() and (slide.body or "").strip():
                words = slide.body.split()
                slide.headline = " ".join(words[:10]) or f"Slide {i}"
            if (slide.role or "insight") == "insight" and i <= len(roles):
                # Only set default role when still generic and first/last need structure
                if i == 1:
                    slide.role = "hook"
                elif i == len(self.slides):
                    slide.role = "cta"
        if not (self.headline or "").strip() and self.slides:
            self.headline = self.slides[0].headline or "Creative"
        if self.format == "carousel" and not self.layout_type:
            self.layout_type = "carousel_story"
        return self
