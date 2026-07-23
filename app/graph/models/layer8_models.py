from __future__ import annotations

from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ContentSection(BaseModel):
    section_id: str = "section"
    title: str = ""
    body: Optional[str] = None
    metric: Optional[str] = None
    visual_metaphor: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def coerce_aliases(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out = dict(data)
        if not out.get("title"):
            out["title"] = (
                out.get("section_label")
                or out.get("label")
                or out.get("name")
                or out.get("heading")
                or ""
            )
        if not out.get("section_id"):
            title = str(out.get("title") or "section").strip().lower()
            slug = "".join(ch if ch.isalnum() else "_" for ch in title).strip("_") or "section"
            out["section_id"] = slug[:48]
        if not out.get("body"):
            includes = out.get("includes")
            if isinstance(includes, list) and includes:
                out["body"] = "; ".join(str(x) for x in includes)
            elif isinstance(includes, str) and includes.strip():
                out["body"] = includes
        if not out.get("metric"):
            out["metric"] = out.get("stat") or out.get("percentage")
        if not out.get("visual_metaphor"):
            out["visual_metaphor"] = out.get("icon_hint") or out.get("icon") or out.get("metaphor")
        return out


class TextOverlayElement(BaseModel):
    element_type: Literal[
        "headline",
        "subheadline",
        "supporting_line",
        "body",
        "cta",
        "label",
        "footer",
        "section_label",
        "stat",
        "badge",
    ] = "body"
    text: str = ""
    font_size: int = 24
    color_hex: str = "#0B2C5F"
    position_box: str = "top-center"

    @model_validator(mode="before")
    @classmethod
    def coerce_defaults(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out = dict(data)
        if not out.get("text"):
            out["text"] = out.get("content") or out.get("label") or out.get("copy") or ""
        raw_type = str(out.get("element_type") or "body").strip().lower()
        aliases = {
            "title": "headline",
            "heading": "headline",
            "subhead": "subheadline",
            "subtitle": "supporting_line",
            "sub_heading": "supporting_line",
            "section": "section_label",
            "button": "cta",
            "metric": "stat",
        }
        out["element_type"] = aliases.get(raw_type, raw_type)
        allowed = {
            "headline",
            "subheadline",
            "supporting_line",
            "body",
            "cta",
            "label",
            "footer",
            "section_label",
            "stat",
            "badge",
        }
        if out["element_type"] not in allowed:
            out["element_type"] = "body"
        if out.get("font_size") is None:
            defaults = {
                "headline": 42,
                "subheadline": 28,
                "supporting_line": 22,
                "body": 18,
                "cta": 20,
                "section_label": 16,
                "stat": 32,
                "badge": 14,
                "label": 14,
                "footer": 11,
            }
            out["font_size"] = defaults.get(out["element_type"], 24)
        if not out.get("color_hex"):
            out["color_hex"] = out.get("color") or "#0B2C5F"
        if not out.get("position_box"):
            positions = {
                "headline": "top-center",
                "subheadline": "top-center",
                "supporting_line": "upper-center",
                "body": "center",
                "cta": "footer-strip",
                "section_label": "mid-left",
                "stat": "mid-center",
                "footer": "bottom-center",
            }
            out["position_box"] = positions.get(out["element_type"], "center")
        return out

    @field_validator("font_size", mode="before")
    @classmethod
    def coerce_font_size(cls, value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 24


class VisualReasoningOutput(BaseModel):
    dominant_visual_system: Literal[
        "generated_image",
        "type_led",
        "illustration",
        "infographic",
        "data_visual",
        "product_visual",
    ] = "generated_image"
    visual_format_type: Literal[
        "comparison",
        "timeline",
        "chart",
        "matrix",
        "process_flow",
        "hero_scene",
        "data_grid",
    ] = "hero_scene"
    visual_style: str = "Premium corporate educational creative with ultra-glossy 3D icons"
    composition_logic: str = "Top-down educational hierarchy with hero visual and structured content blocks"
    focal_point: str = "Central ultra-premium 3D icon cluster"
    negative_space_plan: str = "Generous margins; keep logo-safe top-right corner clear"
    color_behavior: str = "Navy typography on light cool background with orange/gold accents"
    logo_zone_instruction: str = "Top-right corner with ~32px padding, keep clear for logo compositing"
    typography_behavior: Optional[str] = "Bold navy sans headlines, readable gray body, baked into image"
    image_prompt_direction: str = ""
    content_sections: List[ContentSection] = Field(default_factory=list)
    text_overlay_plan: List[TextOverlayElement] = Field(default_factory=list)
    generated_image_url: str = ""
    generated_image_urls: List[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def fill_missing_core_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out = dict(data)
        # Common LLM renames
        if not out.get("image_prompt_direction"):
            out["image_prompt_direction"] = (
                out.get("image_prompt")
                or out.get("prompt")
                or out.get("expanded_prompt")
                or out.get("visual_prompt")
                or ""
            )
        if not out.get("visual_style"):
            out["visual_style"] = out.get("style") or out.get("art_style") or (
                "Premium corporate educational creative with ultra-glossy 3D icons"
            )
        if not out.get("composition_logic"):
            out["composition_logic"] = out.get("composition") or out.get("layout") or (
                "Top-down educational hierarchy with hero visual and structured content blocks"
            )
        if not out.get("focal_point"):
            out["focal_point"] = out.get("focus") or "Central ultra-premium 3D icon cluster"
        if not out.get("negative_space_plan"):
            out["negative_space_plan"] = out.get("negative_space") or (
                "Generous margins; keep logo-safe top-right corner clear"
            )
        if not out.get("color_behavior"):
            out["color_behavior"] = out.get("colors") or out.get("palette") or (
                "Navy typography on light cool background with orange/gold accents"
            )
        if not out.get("logo_zone_instruction"):
            out["logo_zone_instruction"] = out.get("logo_zone") or (
                "Top-right corner with ~32px padding, keep clear for logo compositing"
            )
        dvs = str(out.get("dominant_visual_system") or "generated_image").strip().lower()
        allowed_dvs = {
            "generated_image",
            "type_led",
            "illustration",
            "infographic",
            "data_visual",
            "product_visual",
        }
        out["dominant_visual_system"] = dvs if dvs in allowed_dvs else "generated_image"
        vft = str(out.get("visual_format_type") or "hero_scene").strip().lower()
        allowed_vft = {
            "comparison",
            "timeline",
            "chart",
            "matrix",
            "process_flow",
            "hero_scene",
            "data_grid",
        }
        out["visual_format_type"] = vft if vft in allowed_vft else "hero_scene"
        if out.get("generated_image_url") is None:
            out["generated_image_url"] = ""
        return out
