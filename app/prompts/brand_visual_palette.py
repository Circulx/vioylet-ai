from __future__ import annotations

from app.prompts.brand_copy_tone import JIRAAF_BG, JIRAAF_NAVY, JIRAAF_ORANGE
from app.prompts.cognixia_brand_dna import (
    cognixia_color_behavior,
    cognixia_default_palette,
    is_cognixia_brand,
)

JIRAAF_FORBIDDEN = (
    "FORBIDDEN for this brand: Jiraaf navy #003975, orange #FFA400, ice-blue #E8F0F8/#87CEFA/#D9ECF8."
)


def is_jiraaf_brand(brand_name: str | None) -> bool:
    return "jiraaf" in (brand_name or "").casefold()


def resolve_brand_palette_lock(
    *,
    brand_name: str = "",
    color_behavior: str = "",
    visual_mood: str = "",
    primary_color: str = "",
    secondary_color: str = "",
    additional_colors: list[dict] | None = None,
) -> str:
    """Authoritative palette lock for non-Jiraaf image prompts."""
    label = (brand_name or "this brand").strip() or "this brand"

    if is_jiraaf_brand(label):
        return (
            f"JIRAAF LOCK: Navy {JIRAAF_NAVY} headlines on ice-blue {JIRAAF_BG} "
            f"with REQUIRED orange {JIRAAF_ORANGE} accents."
        )

    if is_cognixia_brand(label):
        return cognixia_color_behavior(
            primary_color=primary_color,
            secondary_color=secondary_color,
        )

    parts = [
        f"BRAND LOCK ({label}): Use ONLY this brand's official colour palette.",
        JIRAAF_FORBIDDEN,
    ]
    if primary_color:
        parts.append(f"PRIMARY colour: {primary_color} — use for headlines, key accents, CTA buttons.")
    if secondary_color:
        parts.append(f"SECONDARY colour: {secondary_color} — use for supporting accents, icons, highlights.")
    if additional_colors:
        extras = [
            f"{c.get('name', '')} {c.get('hex', '')}"
            for c in additional_colors
            if c.get("hex") and c.get("hex") not in (primary_color, secondary_color)
        ]
        if extras:
            parts.append(f"Additional palette: {', '.join(extras[:4])}.")
    if color_behavior or visual_mood:
        parts.append(color_behavior or visual_mood)
    if not primary_color and not secondary_color:
        parts.append("Use Brand Space visual identity colors only.")
    return " ".join(parts)


def static_background_instruction(*, brand_name: str) -> str:
    if is_jiraaf_brand(brand_name):
        return f"solid ice-blue {JIRAAF_BG}"
    if is_cognixia_brand(brand_name):
        palette = cognixia_default_palette()
        return f"clean WHITE {palette['white']} or soft card tint {palette['card_bg']}"
    return "clean WHITE #FFFFFF — soft subtle gradient allowed, never ice-blue"


def jiraaf_accent_requirement(*, brand_name: str) -> str:
    if is_jiraaf_brand(brand_name):
        return f"Brand colours REQUIRED: navy {JIRAAF_NAVY} + visible orange {JIRAAF_ORANGE} accents."
    return resolve_brand_palette_lock(brand_name=brand_name)
