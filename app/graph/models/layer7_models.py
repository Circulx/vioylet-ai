from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class CopySlide(BaseModel):
    slide_number: int = 1
    headline: str = ""
    supporting_line: Optional[str] = None
    body: str = ""
    cta: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_slide(cls, data: Any) -> Any:
        """LLM often returns body-only slides — fill required fields instead of crashing Phase 1."""
        if not isinstance(data, dict):
            return data
        out = dict(data)
        body = str(out.get("body") or "").strip()
        headline = str(out.get("headline") or out.get("title") or "").strip()
        if not headline and body:
            # Use first sentence / first ~10 words as headline
            first = body.split(".")[0].strip() or body
            words = first.split()
            headline = " ".join(words[:10]) if words else "Key point"
        out["headline"] = headline or "Key point"
        out["body"] = body
        if out.get("slide_number") is None:
            out["slide_number"] = 1
        try:
            out["slide_number"] = int(out.get("slide_number") or 1)
        except (TypeError, ValueError):
            out["slide_number"] = 1
        return out


class InfographicSection(BaseModel):
    """A structured infographic section (table row) with a label, stat/metric, bullet
    breakdown of what it includes, and a supporting explanation of why it matters."""

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


class CopyOutput(BaseModel):
    headline: str = ""
    supporting_line: Optional[str] = None
    body: str = ""
    cta: str = ""
    hashtags: List[str] = Field(default_factory=list)
    slide_copy: List[CopySlide] = Field(default_factory=list)
    claim_safety_notes: List[str] = Field(default_factory=list)

    # Infographic-specific structured content
    infographic_sections: List[InfographicSection] = Field(default_factory=list)
    problem_statement: Optional[str] = None
    solution_statement: Optional[str] = None
    proof_points: List[str] = Field(default_factory=list)
    stat_highlights: List[str] = Field(default_factory=list)
    customer_quote: Optional[str] = None
    customer_name: Optional[str] = None
    process_steps: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _renumber_slides(self) -> CopyOutput:
        for i, slide in enumerate(self.slide_copy or [], start=1):
            slide.slide_number = i
            if not (slide.headline or "").strip() and (slide.body or "").strip():
                words = slide.body.split()
                slide.headline = " ".join(words[:10]) or f"Slide {i}"
        if not (self.headline or "").strip() and self.slide_copy:
            self.headline = self.slide_copy[0].headline or "Creative"
        return self
