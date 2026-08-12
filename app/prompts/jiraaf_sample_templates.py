from __future__ import annotations

"""Single source of truth: prompt + format → locked Jiraaf sample template.

Every creative path (L7 copy, L7c blueprint, L8 image) MUST resolve through
``resolve_creative_template()`` so layout DNA cannot drift between layers.
"""

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from app.prompts.brand_copy_tone import (
    BANK_PENALTY_SAMPLE_RULES,
    ICON_STYLE_LOCK,
    INFOGRAPHIC_AUDIENCE_TONE_LOCK,
    INFOGRAPHIC_EXPLAIN_LAYOUT_LOCK,
    INFOGRAPHIC_EXPLAIN_ORANGE_STUB,
    INFOGRAPHIC_EXPLAIN_QUALITY_LOCK,
    INFOGRAPHIC_RANKING_FORMAT_LOCK,
    INFOGRAPHIC_TRADE_BOARD_LOCK,
    JIRAAF_STORYTELLING_LOCK,
    NO_SEBI_STATIC_RULE,
    ORANGE_COVERAGE_LOCK,
    RANKING_IMAGE_STUB,
    RANKING_SAMPLE_DNA_LOCK,
    STATIC_EXPLAIN_LAYOUT_LOCK,
    STATIC_EXPLAIN_QUALITY_LOCK,
    STATIC_HORIZONTAL_BAR_DNA_LOCK,
    STATIC_HORIZONTAL_BAR_IMAGE_STUB,
    STATIC_HUB_FACTS_DNA_LOCK,
    STATIC_HUB_FACTS_IMAGE_STUB,
    STATIC_ORANGE_STUB,
    STATIC_RANKING_INSIGHT_LOCK,
    UNIVERSAL_FIT_LOCK,
    UNIVERSAL_JIRAAF_PALETTE_LOCK,
)
from app.prompts.carousel_sample_dna import CAROUSEL_SAMPLE_DNA, CAROUSEL_SAMPLE_DNA_COMPACT
from app.prompts.jiraaf_layout import (
    LayoutType,
    classify_layout,
    is_trade_data_board,
    static_ranking_style,
)

SAMPLES_DIR = Path(__file__).resolve().parent / "references" / "jiraaf_samples"

TemplateId = Literal[
    "carousel_story",
    "static_explain_poster",
    "infographic_explain_editorial",
    "static_hub_facts",
    "vertical_country_ranking",
    "horizontal_bar_ranking",
    "trade_deficit_board",
]


@dataclass(frozen=True)
class CreativeTemplate:
    """Locked design template derived from a reference sample file."""

    template_id: TemplateId
    sample_file: str
    layout_type: LayoutType
    format: Literal["static", "carousel", "infographic"]
    visual_style: str
    copy_lock: str
    visual_lock: str
    image_stub: str

    @property
    def sample_path(self) -> Path:
        return SAMPLES_DIR / self.sample_file

    def l7c_layout_block(self, *, rank_n: int | None = None) -> str:
        count_line = ""
        extra = ""
        if rank_n and self.layout_type == "static_ranking":
            count_line = (
                f"- sections[] MUST have EXACTLY {rank_n} ranked rows "
                f"(user asked for top {rank_n}) — never stop at 5\n"
            )
        elif self.layout_type == "static_ranking":
            count_line = (
                "- sections[] MUST include ALL entities the user asked to rank — "
                "never silently truncate to 5\n"
            )
        if self.visual_style == "horizontal_bar":
            extra = (
                f"- headline with orange highlight; sections[] = exactly {rank_n or 7} countries "
                "with stat + % + phrase\n"
                "- customer_quote or annotation = insight why focal country ranks (if user asked)\n"
                "- Bake ALL row text + flags + clay-3D icons — India/focal row in ORANGE bar\n"
            )
        elif self.visual_style == "infographic_explain":
            extra = (
                "- sections[] = 2–4 UNIQUE headings; includes[] = 2–3 unique mini-titles with ₹/% explanations\n"
                "- Dense sample layout (3-col fact grids + callout) — NOT sparse poster; topic-safe CTA only\n"
            )
        elif self.visual_style == "trade_board":
            extra = (
                "- sections[] YEAR rows: label=FY, includes Export/Import USD lines, stat=balance\n"
                "- Extra sections: top import categories with USD amounts\n"
                "- source_footer = Ministry of Commerce / research domain\n"
            )
        elif self.visual_style == "hub_spoke":
            extra = (
                "- sections[] EXACTLY 5 banks: Axis Bank | SBI | HDFC Bank | ICICI Bank | PNB\n"
                "- body=\"\"; customer_quote=\"\"; NO fake testimonials\n"
            )
        return f"""
TEMPLATE LOCK — {self.template_id} (sample: {self.sample_file})
{self.copy_lock}
{extra}{count_line}"""

    def l8_image_hint(self, *, canvas_desc: str = "1080x1350") -> str:
        base = (
            f"\nTEMPLATE LOCK — {self.template_id}\n"
            f"MATCH SAMPLE EXACTLY: {self.sample_file}\n"
            f"{self.visual_lock}\n"
            f"- Canvas {canvas_desc}. Ice-blue #E8F0F8 / soft white BG.\n"
            f"- {NO_SEBI_STATIC_RULE}\n"
            f"- {ICON_STYLE_LOCK}\n"
            f"- {UNIVERSAL_FIT_LOCK}\n"
            "Bake ALL quoted text. Perfect spelling. No mid-word breaks. No $ / US $.\n"
        )
        if self.template_id == "carousel_story":
            return base
        if self.template_id in ("infographic_explain_editorial", "static_explain_poster"):
            return base + f"{ORANGE_COVERAGE_LOCK}\n"
        return base


def _tpl(
    template_id: TemplateId,
    sample_file: str,
    layout_type: LayoutType,
    fmt: Literal["static", "carousel", "infographic"],
    visual_style: str,
    copy_lock: str,
    visual_lock: str,
    image_stub: str,
) -> CreativeTemplate:
    return CreativeTemplate(
        template_id=template_id,
        sample_file=sample_file,
        layout_type=layout_type,
        format=fmt,
        visual_style=visual_style,
        copy_lock=copy_lock,
        visual_lock=visual_lock,
        image_stub=image_stub,
    )


_TEMPLATES: dict[TemplateId, CreativeTemplate] = {
    "carousel_story": _tpl(
        "carousel_story",
        "sample_sweep_in_fd.pdf (+ capital_control_v2, unrealized_gains)",
        "carousel_story",
        "carousel",
        "carousel_education",
        copy_lock=CAROUSEL_SAMPLE_DNA,
        visual_lock=CAROUSEL_SAMPLE_DNA_COMPACT,
        image_stub="Carousel: 5–6 slides — hook → ₹ scenario → mechanism → choice → CTA.",
    ),
    "static_explain_poster": _tpl(
        "static_explain_poster",
        "sample_infographic_explain_rbi_polymer.png (static variant)",
        "carousel_story",
        "static",
        "static_explain",
        copy_lock=f"{STATIC_EXPLAIN_LAYOUT_LOCK}\n{STATIC_EXPLAIN_QUALITY_LOCK}\n{STATIC_ORANGE_STUB}",
        visual_lock=f"{STATIC_EXPLAIN_LAYOUT_LOCK}\n{STATIC_EXPLAIN_QUALITY_LOCK}\n{STATIC_ORANGE_STUB}",
        image_stub="Static explain: hero icon + heading/explanation cards — NOT ranking rows.",
    ),
    "infographic_explain_editorial": _tpl(
        "infographic_explain_editorial",
        "sample_infographic_explain_why_airports.png",
        "carousel_story",
        "infographic",
        "infographic_explain",
        copy_lock=(
            f"{UNIVERSAL_JIRAAF_PALETTE_LOCK}\n"
            f"{JIRAAF_STORYTELLING_LOCK}\n"
            f"{INFOGRAPHIC_EXPLAIN_LAYOUT_LOCK}\n"
            f"{INFOGRAPHIC_EXPLAIN_ORANGE_STUB}\n"
            f"{INFOGRAPHIC_EXPLAIN_QUALITY_LOCK}"
        ),
        visual_lock=(
            f"{UNIVERSAL_JIRAAF_PALETTE_LOCK}\n"
            f"{INFOGRAPHIC_EXPLAIN_LAYOUT_LOCK}\n"
            f"{INFOGRAPHIC_EXPLAIN_ORANGE_STUB}\n"
            f"{INFOGRAPHIC_EXPLAIN_QUALITY_LOCK}\n"
            f"{ORANGE_COVERAGE_LOCK}"
        ),
        image_stub=(
            "AI-only storytelling editorial like sample_infographic_explain_why_airports.png: "
            "ice-blue BG #E8F0F8, navy #003975 headlines, orange #FFA400 accents, "
            "hook→stats→reason cards→chart→navy footer. Empty top-right logo pocket. "
            "Insight-led — NEVER textbook, NEVER 'Web Search:' labels, NEVER hub-spoke collage."
        ),
    ),
    "static_hub_facts": _tpl(
        "static_hub_facts",
        "sample_bank_penalties.png",
        "static_hub_facts",
        "static",
        "hub_spoke",
        copy_lock=f"{STATIC_HUB_FACTS_DNA_LOCK}\n{BANK_PENALTY_SAMPLE_RULES}",
        visual_lock=STATIC_HUB_FACTS_DNA_LOCK,
        image_stub=STATIC_HUB_FACTS_IMAGE_STUB,
    ),
    "vertical_country_ranking": _tpl(
        "vertical_country_ranking",
        "sample_top_countries_investing.png",
        "static_ranking",
        "infographic",  # default; caller may override format
        "vertical_countries",
        copy_lock=(
            f"{UNIVERSAL_JIRAAF_PALETTE_LOCK}\n"
            f"{INFOGRAPHIC_AUDIENCE_TONE_LOCK}\n"
            f"{INFOGRAPHIC_RANKING_FORMAT_LOCK}\n"
            f"{RANKING_SAMPLE_DNA_LOCK}"
        ),
        visual_lock=(
            f"{UNIVERSAL_JIRAAF_PALETTE_LOCK}\n"
            f"{RANKING_IMAGE_STUB}\n"
            f"{RANKING_SAMPLE_DNA_LOCK}\n"
            f"{STATIC_ORANGE_STUB}"
        ),
        image_stub=(
            "Vertical ranking: orange # badge | flag | NAME + phrase | ₹50B | coin icon."
        ),
    ),
    "horizontal_bar_ranking": _tpl(
        "horizontal_bar_ranking",
        "sample_static_oil_consumption_bars.png",
        "static_ranking",
        "static",
        "horizontal_bar",
        copy_lock=(
            f"{STATIC_HORIZONTAL_BAR_DNA_LOCK}\n"
            f"{STATIC_RANKING_INSIGHT_LOCK}\n"
            f"{STATIC_ORANGE_STUB}"
        ),
        visual_lock=(
            f"{STATIC_HORIZONTAL_BAR_DNA_LOCK}\n"
            f"{STATIC_HORIZONTAL_BAR_IMAGE_STUB}\n"
            f"{STATIC_RANKING_INSIGHT_LOCK}\n"
            f"{STATIC_ORANGE_STUB}"
        ),
        image_stub=(
            "Horizontal bar: COUNTRY | flag | bar | value inside | % outside. "
            "Focal row orange. Orange arrow insight."
        ),
    ),
    "trade_deficit_board": _tpl(
        "trade_deficit_board",
        "sample_india_russia_trade_deficit.png",
        "static_ranking",
        "infographic",
        "trade_board",
        copy_lock=f"{INFOGRAPHIC_AUDIENCE_TONE_LOCK}\n{INFOGRAPHIC_TRADE_BOARD_LOCK}",
        visual_lock=f"{INFOGRAPHIC_AUDIENCE_TONE_LOCK}\n{INFOGRAPHIC_TRADE_BOARD_LOCK}",
        image_stub=(
            "Trade board: EXPORT orange | BALANCE | IMPORT navy. "
            "Bottom box: What India buys most."
        ),
    ),
}


def _is_jiraaf_brand(brand_name: str | None) -> bool:
    return "jiraaf" in (brand_name or "").casefold()


def _neutralize_for_brand(template: CreativeTemplate, brand_name: str) -> CreativeTemplate:
    """Strip Jiraaf-only sample DNA so other brands use their own visual identity."""
    from app.prompts.brand_visual_palette import resolve_brand_palette_lock
    from app.prompts.cognixia_brand_dna import COGNIXIA_VOICE_LOCK, is_cognixia_brand

    brand_label = brand_name.strip() or "this brand"
    palette = resolve_brand_palette_lock(brand_name=brand_label)
    style_note = (
        "Cognixia official layout: white/card-tint background, blue-teal tech icons, Outfit typography, hub + connected nodes."
        if is_cognixia_brand(brand_label)
        else f"Premium connected-infographic creative for {brand_label}."
    )
    copy_lock = (
        f"Brand: {brand_label}. {COGNIXIA_VOICE_LOCK} Use Cognixia B2B digital transformation voice."
        if is_cognixia_brand(brand_label)
        else (
            f"Brand: {brand_label}. Use this brand's voice, topic, and category. "
            "Do NOT copy Jiraaf finance templates, RBI plastic carousel DNA, or SEBI disclaimers."
        )
    )
    return replace(
        template,
        copy_lock=copy_lock,
        visual_lock=palette,
        image_stub=(
            f"{style_note} Official brand palette only — never Jiraaf ice-blue/orange/navy."
        ),
    )


def resolve_creative_template(
    user_prompt: str,
    selected_format: str | None = None,
    brand_name: str | None = None,
) -> CreativeTemplate:
    """Authoritative template picker — same logic at L7, L7c, and L8."""
    decision = classify_layout(user_prompt, selected_format)
    layout = decision.layout_type
    fmt = (selected_format or decision.suggested_format or "static").strip().lower()
    if fmt not in ("static", "carousel", "infographic"):
        fmt = decision.suggested_format or "static"

    if layout == "static_hub_facts":
        template = _TEMPLATES["static_hub_facts"]
    elif layout == "static_ranking":
        if is_trade_data_board(user_prompt):
            template = replace(_TEMPLATES["trade_deficit_board"], format=fmt)  # type: ignore[arg-type]
        else:
            style = static_ranking_style(user_prompt)
            if style == "horizontal_bar" and fmt == "static":
                template = _TEMPLATES["horizontal_bar_ranking"]
            else:
                template = replace(_TEMPLATES["vertical_country_ranking"], format=fmt)  # type: ignore[arg-type]
    elif layout == "carousel_story":
        if fmt == "infographic":
            template = _TEMPLATES["infographic_explain_editorial"]
        elif fmt == "static":
            template = _TEMPLATES["static_explain_poster"]
        else:
            template = _TEMPLATES["carousel_story"]
    else:
        template = _TEMPLATES["carousel_story"]

    if brand_name and not _is_jiraaf_brand(brand_name):
        return _neutralize_for_brand(template, brand_name)
    return template


def list_locked_samples() -> list[dict[str, str]]:
    """Human-readable registry for docs / QA scripts."""
    rows: list[dict[str, str]] = []
    for tid, tpl in _TEMPLATES.items():
        rows.append(
            {
                "template_id": tid,
                "sample": tpl.sample_file,
                "layout_type": tpl.layout_type,
                "format": tpl.format,
                "style": tpl.visual_style,
                "exists": str(tpl.sample_path.exists() if "/" not in tpl.sample_file else True),
            }
        )
    return rows
