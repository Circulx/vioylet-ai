from __future__ import annotations

import re
from uuid import UUID, uuid4

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.graph.models.layer8_models import VisualReasoningOutput
from app.graph.state import ViolytState
from app.models.brand import BrandSpace
from app.prompts.layer8_visual_reasoning import VisualReasoningPromptBuilder
from app.services.image_generation.dalle_service import DalleService
from app.services.image_generation.logo_fetcher import get_brand_logo_storage_path
from app.services.image_generation.sdxl_service import SdxlService
from app.services.llm.llm_router import LLMRouter
from app.prompts.brand_copy_tone import (
    SOURCE_FOOTER_RULE,
    NO_SEBI_STATIC_RULE,
    ICON_STYLE_LOCK,
    UNIVERSAL_FIT_LOCK,
    CAROUSEL_IMAGE_STYLE_STUB,
    CAROUSEL_IMAGE_EXTRA_LOCKS,
    CAROUSEL_AUDIENCE_TONE_LOCK,
    CAROUSEL_TONE_IMAGE_STUB,
    STATIC_IMAGE_EXTRA_LOCKS,
    INFOGRAPHIC_AUDIENCE_TONE_LOCK,
    INFOGRAPHIC_TRADE_BOARD_LOCK,
    INFOGRAPHIC_EXPLAIN_LAYOUT_LOCK,
    INFOGRAPHIC_EXPLAIN_ORANGE_STUB,
    INFOGRAPHIC_EXPLAIN_QUALITY_LOCK,
    STATIC_EXPLAIN_LAYOUT_LOCK,
    STATIC_EXPLAIN_QUALITY_LOCK,
    STATIC_ORANGE_STUB,
    ORANGE_COVERAGE_LOCK,
    STATIC_RANKING_INSIGHT_LOCK,
    STATIC_HORIZONTAL_BAR_DNA_LOCK,
    STATIC_HORIZONTAL_BAR_IMAGE_STUB,
    EDUCATION_POSTER_LAYOUT_LOCK,
    RANKING_IMAGE_STUB,
)
from app.prompts.jiraaf_layout import classify_layout
from app.prompts.jiraaf_sample_templates import resolve_creative_template
from app.prompts.creative_sizes import canvas_label, size_string
from app.services.blueprint_quality import repair_explain_infographic_copy, repair_generic_headline

# gpt-image-1 practical prompt budget (API also truncates ~6000)
_IMAGE_PROMPT_BUDGET = 5800


def _budget_prompt(content: str, locks: str = "", budget: int = _IMAGE_PROMPT_BUDGET) -> str:
    """Keep slide CONTENT intact; only trim trailing locks if over budget."""
    content = (content or "").strip()
    locks = (locks or "").strip()
    if len(content) >= budget:
        return content[:budget]
    remaining = budget - len(content) - 2
    if remaining <= 0 or not locks:
        return content
    return f"{content}\n\n{locks[:remaining]}"

logger = get_logger(__name__)

_router = LLMRouter()
_prompt_builder = VisualReasoningPromptBuilder()


def _q(value: object, max_chars: int = 280) -> str:
    """Quote exact copy for image prompts; trim on word boundary (never bake '…')."""
    if isinstance(value, (list, tuple)):
        parts: list[str] = []
        for v in value:
            if isinstance(v, dict):
                label = v.get("section_label") or v.get("label") or ""
                body = v.get("body") or v.get("stat") or ""
                chunk = f"{label}: {body}".strip(": ").strip()
                if chunk:
                    parts.append(chunk)
            else:
                s = str(v).strip()
                if s:
                    parts.append(s)
        text = " | ".join(parts)
    else:
        text = str(value or "")
    text = " ".join(text.split()).strip()
    text = text.rstrip("….").strip()
    if not text:
        return '""'
    if len(text) > max_chars:
        cut = text[:max_chars].rsplit(" ", 1)[0].rstrip(" ,.;:")
        text = cut if cut else text[:max_chars].rstrip(" ,.;:")
    safe = text.replace('"', "'")
    return f'"{safe}"'


def _chip_label(value: object, max_words: int = 1, max_chars: int = 14) -> str:
    """One complete chip word — never multi-word phrases that SEBI truncates mid-label."""
    words = " ".join(str(value or "").split()).strip().split()
    label = (words[0] if words else "").strip(".,;:!")
    if len(label) > max_chars:
        label = label[:max_chars]
    return _q(label, max_chars)


# Capital-controls / FDI sample labels — NEVER inject these unless the user asked that topic
_FORBIDDEN_SAMPLE_CHIPS = {
    "inflows",
    "outflows",
    "limits",
    "fdi impact",
    "fx impact",
    "growth signal",
    "rbi role",
    "policy tools",
    "risk control",
    "banks",
    "markets",
    "investors",
}

# Empty teaser/nav chips — these make slides look cheap (user complaint)
_FORBIDDEN_NAV_CHIPS = {
    "pros",
    "cons",
    "examples",
    "example",
    "advantages",
    "disadvantages",
    "comparison",
    "compare",
    "benefits",
    "drawbacks",
    "overview",
    "summary",
    "details",
    "learn",
    "explore",
    "start",
    "more",
    "next",
    "swipe",
}


def _is_nav_chip(word: str) -> bool:
    return (word or "").strip().lower() in _FORBIDDEN_NAV_CHIPS


def _headline_is_repeat(current: str, prior: list[str]) -> bool:
    """True if headline is nearly the same as a previous slide (e.g. 'Capital Controls' x5)."""
    cur = " ".join((current or "").lower().split())
    if not cur:
        return True
    # Strip common prefixes / punctuation
    for prefix in ("what are ", "what is ", "why ", "how ", "understanding ", "about "):
        if cur.startswith(prefix):
            cur_core = cur[len(prefix) :]
            break
    else:
        cur_core = cur
    cur_core = cur_core.strip(" ?!.:-")
    for p in prior:
        prev = " ".join((p or "").lower().split())
        for prefix in ("what are ", "what is ", "why ", "how ", "understanding ", "about "):
            if prev.startswith(prefix):
                prev_core = prev[len(prefix) :]
                break
        else:
            prev_core = prev
        prev_core = prev_core.strip(" ?!.:-")
        if not prev_core:
            continue
        if cur == prev or cur_core == prev_core:
            return True
        # High overlap on short titles
        if len(cur_core) <= 28 and (cur_core in prev_core or prev_core in cur_core):
            return True
        # Token overlap for near-duplicates ("trade deficit" vs "trade deficit and imports-exports")
        cur_toks = set(cur_core.replace("-", " ").split())
        prev_toks = set(prev_core.replace("-", " ").split())
        if cur_toks and prev_toks:
            overlap = len(cur_toks & prev_toks) / max(len(cur_toks | prev_toks), 1)
            if overlap >= 0.7 and len(cur_toks & prev_toks) >= 2:
                return True
    return False


def _is_bare_topic_headline(headline: str, user_prompt: str) -> bool:
    """True for lazy titles that are just the topic name (Trade Deficit / Capital Controls)."""
    h = " ".join((headline or "").lower().split()).strip(" ?!.:-")
    for prefix in ("what are ", "what is ", "understanding ", "about "):
        if h.startswith(prefix):
            h = h[len(prefix) :].strip()
    if not h or len(h.split()) > 5:
        return False
    topic = " ".join((user_prompt or "").lower().split())
    # Known bare topic titles
    bare = {
        "trade deficit",
        "capital controls",
        "capital control",
        "unrealized gains",
        "unrealised gains",
        "sweep-in fd",
        "sweep in fd",
        "fixed deposits",
        "imports exports",
        "imports-exports",
    }
    if h in bare:
        return True
    # Headline is basically a subset of the user topic words only
    h_toks = set(h.replace("-", " ").split()) - {"and", "the", "a", "an", "of", "vs", "versus"}
    if not h_toks:
        return False
    topic_toks = set(topic.replace("-", " ").split())
    return h_toks.issubset(topic_toks) and len(h_toks) <= 4


def _content_fact_lines(bp_slide: object | None, slide_body: str, slide_supporting: str) -> list[str]:
    """Pull explanation lines to bake as content cards (full sentences, not empty Pros/Cons)."""
    lines: list[str] = []

    def _add(s: str, max_len: int = 75) -> None:
        t = " ".join(str(s).split()).strip()
        if not t:
            return
        # Skip bare nav words
        if _is_nav_chip(t) or (len(t.split()) == 1 and t.lower() in {"selling", "hedging", "leverage", "hold", "sell"}):
            return
        if t not in lines:
            lines.append(t[:max_len])

    if bp_slide:
        for p in list(getattr(bp_slide, "proof_points", None) or [])[:4]:
            _add(str(p), 90)
        for p in list(getattr(bp_slide, "stat_highlights", None) or [])[:3]:
            _add(str(p), 90)
        # Longer chip phrases that already explain something
        for c in list(getattr(bp_slide, "chip_labels", None) or [])[:3]:
            s = " ".join(str(c).split()).strip()
            if s and (any(ch.isdigit() for ch in s) or "₹" in s or "%" in s or len(s.split()) >= 3):
                _add(s, 90)

    body = " ".join((slide_body or "").split()).strip()
    if body:
        # Prefer sentence chunks as separate cards
        parts = [p.strip() for p in body.replace(";", ".").split(".") if p.strip()]
        if len(parts) >= 2:
            for part in parts[:3]:
                if len(part.split()) >= 4:
                    _add(part, 90)
        else:
            # Split long body into ~2 chunks by words
            words = body.split()
            if len(words) >= 16:
                mid = len(words) // 2
                _add(" ".join(words[:mid]), 90)
                _add(" ".join(words[mid:]), 90)
            else:
                _add(body, 110)

    if len(lines) < 2 and slide_supporting:
        _add(slide_supporting, 90)

    # Ensure at least something teachable
    while len(lines) < 2 and body:
        _add(body, 110)
        break
    return lines[:3]

_ROLE_HEROES = {
    "hook": "HD premium clay-3D avatar: soft wallet + rupee coin stack + question spark (curiosity)",
    "define": "HD premium clay-3D avatar: savings document + coin pile + labeled threshold marker",
    "impact": "HD premium clay-3D avatar: comparison chart bars + FD certificate + wallet",
    "implication": "HD premium clay-3D avatar: sweep arrows + savings phone + soft padlock",
    "proof": "HD premium clay-3D avatar: checklist board + shield + coin stack",
    "myth": "HD premium clay-3D avatar: balance scale + lightbulb + checklist",
    "cta": "HD premium clay-3D avatar: comment bubble + phone tile + soft CTA arrow",
    "insight": "HD premium clay-3D avatar: document + shield + chart",
}

_BOND_HEROES_BY_N = {
    1: "HD premium clay-3D avatar: bond certificate + gold rupee coin + soft spark",
    2: "HD premium clay-3D avatar: bond paper + coupon calendar + wallet",
    3: "HD premium clay-3D avatar: coupon stream + wallet + rising income bars",
    4: "HD premium clay-3D avatar: shield + padlock + clock",
    5: "HD premium clay-3D avatar: balance scale + checklist + lightbulb",
    6: "HD premium clay-3D avatar: myth stamp + lightbulb + checklist",
    7: "HD premium clay-3D avatar: CTA arrow + phone tile + rupee coin",
}

_CAPITAL_CONTROL_HEROES_BY_N = {
    1: "HD premium clay-3D avatar: border gate + currency arrows + soft spark",
    2: "HD premium clay-3D avatar: rule document + gold lock + currency token",
    3: "HD premium clay-3D avatar: currency chart + shield + lock",
    4: "HD premium clay-3D avatar: LRS document + sector icons + RBI stamp",
    5: "HD premium clay-3D avatar: open gate + inflow arrows + bond certificate",
    6: "HD premium clay-3D avatar: balance scale + arrows + checklist",
    7: "HD premium clay-3D avatar: CTA arrow + document + chart",
}

_CAPITAL_CONTROL_CHIPS_BY_N = {
    1: ("Duty", "Gold", "Story"),
    2: ("Who", "Amount", "Where"),
    3: ("Currency", "Markets", "Costs"),
    4: ("LRS", "FDI", "RBI"),
    5: ("Ease", "Attract", "Inflow"),
    6: ("Myth", "Reality", "Takeaway"),
    7: ("Comment", "Share", "Ask"),
}

_BOND_CHIPS_BY_N = {
    1: ("Price", "Coupon", "Rates"),
    2: ("Bond", "Premium", "Yield"),
    3: ("Hold", "Coupon", "Maturity"),
    4: ("Exit", "Gain", "Redeploy"),
    5: ("Cycle", "Opportunity", "Timing"),
    6: ("Hold", "Sell", "Goals"),
    7: ("Comment", "Share", "Ask"),
}

_ROLE_CHIPS = {
    "hook": ("Fact", "Tension", "Why"),
    "define": ("Meaning", "Rule", "Flow"),
    "impact": ("Mechanism", "Number", "Effect"),
    "implication": ("Choice", "Condition", "Impact"),
    "proof": ("Caveat", "Tradeoff", "Watch"),
    "myth": ("Myth", "Reality", "Takeaway"),
    "cta": ("Comment", "Share", "Ask"),
    "insight": ("Fact", "Number", "Impact"),
}


def _is_bond_topic(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in ("bond", "bonds", "debenture", "debentures", "fixed income", "coupon", "yield", "maturity"))


def _is_capital_controls_topic(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in ("capital control", "capital controls", "capital flow", "inflow", "outflow", "currency control", "cross-border"))


def _normalize_role(role: object) -> str:
    r = str(role or "insight").strip().lower()
    aliases = {
        "hook": "hook",
        "intro": "hook",
        "define": "define",
        "definition": "define",
        "impact": "impact",
        "how": "impact",
        "mechanism": "impact",
        "why": "impact",
        "implication": "implication",
        "affect": "implication",
        "investor": "implication",
        "proof": "proof",
        "example": "proof",
        "nuance": "proof",
        "watch": "proof",
        "myth": "myth",
        "myth-bust": "myth",
        "cta": "cta",
        "close": "cta",
        "closing": "cta",
    }
    for key, val in aliases.items():
        if key in r:
            return val
    return "insight"


def _chips_look_like_wrong_sample(chips: tuple[str, str, str]) -> bool:
    return any(
        c.strip().lower() in _FORBIDDEN_SAMPLE_CHIPS or _is_nav_chip(c)
        for c in chips
    )


def _one_word_chips(values: list[str] | tuple[str, ...]) -> tuple[str, str, str] | None:
    words: list[str] = []
    for v in values:
        w = " ".join(str(v or "").split()).strip()
        if not w:
            continue
        # Prefer first token; keep short compounds like Cashflow
        token = w.split()[0].strip(".,;:!")
        if token and token.lower() not in _FORBIDDEN_SAMPLE_CHIPS and not _is_nav_chip(token):
            words.append(token[:14])
        if len(words) == 3:
            return (words[0], words[1], words[2])
    return None


def _derive_carousel_chips(
    *,
    role: str,
    n: int,
    bp_slide: object | None,
    slide_headline: str,
    slide_body: str,
    user_prompt: str,
) -> tuple[str, str, str]:
    """Bottom chips: 3 complete ONE-WORD labels for THIS slide — never truncated phrases."""
    # 1) Blueprint chip_labels (preferred — content-authored)
    if bp_slide and getattr(bp_slide, "chip_labels", None):
        got = _one_word_chips(list(bp_slide.chip_labels or []))
        if got and not _chips_look_like_wrong_sample(got):
            return got

    # 2) proof_points if already chip-sized
    if bp_slide and getattr(bp_slide, "proof_points", None):
        got = _one_word_chips([str(p) for p in (bp_slide.proof_points or [])])
        if got and not _chips_look_like_wrong_sample(got):
            return got

    blob = f"{user_prompt} {slide_headline} {slide_body}".lower()
    if _is_capital_controls_topic(blob):
        return _CAPITAL_CONTROL_CHIPS_BY_N.get(n) or _CAPITAL_CONTROL_CHIPS_BY_N[((n - 1) % 7) + 1]
    if _is_bond_topic(user_prompt):
        return _BOND_CHIPS_BY_N.get(n) or _BOND_CHIPS_BY_N[((n - 1) % 7) + 1]

    return _ROLE_CHIPS.get(role, _ROLE_CHIPS["insight"])


def _derive_carousel_hero(
    *,
    role: str,
    n: int,
    slide_headline: str,
    user_prompt: str,
    used_heroes: set[str],
) -> str:
    """Hero cluster unique per slide index — slides 3 and 4 must not share the same set."""
    blob = f"{user_prompt} {slide_headline}".lower()
    if _is_capital_controls_topic(blob):
        hero = _CAPITAL_CONTROL_HEROES_BY_N.get(n) or _CAPITAL_CONTROL_HEROES_BY_N[((n - 1) % 7) + 1]
    elif _is_bond_topic(user_prompt):
        hero = _BOND_HEROES_BY_N.get(n) or _BOND_HEROES_BY_N[((n - 1) % 7) + 1]
    else:
        hero = _ROLE_HEROES.get(role) or _ROLE_HEROES["insight"]
    # If somehow duplicated, append slide index cue for the image model
    if hero in used_heroes:
        hero = f"{hero} — SLIDE {n} VARIANT (different objects, different pose)"
    used_heroes.add(hero)
    return hero


def _error_free_text_block(lines: list[tuple[str, str]], *, is_carousel: bool = False) -> str:
    """Build quoted-text bake instructions (font + contrast + exact strings). Keep SHORT for image budget."""
    parts = [
        "\nEXACT BAKED TEXT (letter-perfect — never truncate mid-word):\n",
        "Font: clean navy sans-serif on ice-blue/white. India: ₹/% only — never £.\n",
    ]
    if is_carousel:
        parts.append("Leave bottom ~14% empty for SEBI composite. No AI logo.\n")
    else:
        parts.append("No SEBI footer. No AI logo.\n")
    for label, quoted in lines:
        if quoted and quoted != '""':
            parts.append(f"{label}: {quoted}\n")
    return "".join(parts)


async def layer8_visual_reasoning(state: ViolytState) -> dict:
    brand_intelligence = state.get("brand_intelligence")
    format_plan = state.get("format_plan")
    copy = state.get("copy")
    blueprint = state.get("creative_blueprint")
    creative_concepts = state.get("creative_concepts")
    user_prompt = state.get("user_prompt", "")

    brand_id = state.get("brand_id", "unknown")
    platform = state.get("platform", "linkedin")
    fmt = state.get("format", "static")

    if not brand_intelligence or not format_plan or not copy or not creative_concepts:
        logger.error("visual_reasoning.missing_inputs")
        raise ValueError(
            "Layer 2 brand_intelligence, Layer 5 creative_concepts, Layer 6 format_plan, "
            "and Layer 7 copy are required for Layer 8"
        )

    # Prefer approved Creative Blueprint text for art direction cues
    brand_name = (brand_intelligence.brand_core.brand_name or "").strip()
    is_jiraaf_brand = "jiraaf" in brand_name.casefold()
    brand_primary_color = ""
    brand_secondary_color = ""
    brand_additional_colors: list[dict] = []
    brand_typography_font = ""
    try:
        brand_uuid_early = UUID(str(brand_id)) if not isinstance(brand_id, UUID) else brand_id
        async with AsyncSessionLocal() as session:
            brand_row = await session.get(BrandSpace, brand_uuid_early)
            if brand_row and isinstance(brand_row.overview_snapshot, dict):
                visual_identity = brand_row.overview_snapshot.get("visual_identity") or {}
                if isinstance(visual_identity, dict):
                    palette = visual_identity.get("brand_color_palette") or {}
                    if isinstance(palette, dict):
                        brand_primary_color = str(palette.get("primary") or "").strip()
                        brand_secondary_color = str(palette.get("secondary") or "").strip()
                        brand_additional_colors = list(palette.get("additional") or [])
                    typo = visual_identity.get("typography") or {}
                    if isinstance(typo, dict):
                        brand_typography_font = str(typo.get("primary_style") or "").strip()
    except Exception as exc:
        logger.warning("visual_reasoning.brand_palette_load_failed", error=str(exc)[:120])

    if not is_jiraaf_brand:
        from app.prompts.brand_visual_palette import resolve_brand_palette_lock
        from app.prompts.cognixia_brand_dna import cognixia_default_palette, is_cognixia_brand

        if is_cognixia_brand(brand_name) and not brand_primary_color:
            defaults = cognixia_default_palette()
            brand_primary_color = defaults["primary"]
            brand_secondary_color = defaults["secondary"]

        locked_palette = resolve_brand_palette_lock(
            brand_name=brand_name,
            color_behavior=brand_intelligence.visual_behavior.color_behavior,
            visual_mood=brand_intelligence.visual_behavior.visual_mood,
            primary_color=brand_primary_color,
            secondary_color=brand_secondary_color,
            additional_colors=brand_additional_colors or None,
        )
        brand_intelligence = brand_intelligence.model_copy(
            update={
                "visual_behavior": brand_intelligence.visual_behavior.model_copy(
                    update={"color_behavior": locked_palette}
                )
            }
        )
    headline = (blueprint.headline if blueprint and blueprint.headline else copy.headline)
    body = (blueprint.body if blueprint and blueprint.body else copy.body)
    supporting = (
        blueprint.supporting_line
        if blueprint and blueprint.supporting_line is not None
        else copy.supporting_line
    ) or ""
    cta = (blueprint.cta if blueprint and blueprint.cta else copy.cta) or ""
    sections = (
        [s.model_dump() for s in blueprint.sections]
        if blueprint and blueprint.sections
        else [s.model_dump() for s in copy.infographic_sections]
    )
    proof_points = (
        list(blueprint.proof_points)
        if blueprint and blueprint.proof_points
        else list(copy.proof_points or [])
    )
    stat_highlights = (
        list(blueprint.stat_highlights)
        if blueprint and blueprint.stat_highlights
        else list(copy.stat_highlights or [])
    )
    problem_statement = (
        (blueprint.problem_statement if blueprint else None) or copy.problem_statement or ""
    )
    solution_statement = (
        (blueprint.solution_statement if blueprint else None) or copy.solution_statement or ""
    )
    customer_quote = (
        (blueprint.customer_quote if blueprint else None) or copy.customer_quote or ""
    )
    customer_name = (
        (blueprint.customer_name if blueprint else None) or copy.customer_name or ""
    )
    process_steps = (
        list(blueprint.process_steps)
        if blueprint and blueprint.process_steps
        else list(copy.process_steps or [])
    )

    recommended = creative_concepts.recommended_concept

    layout_decision = classify_layout(user_prompt, fmt)
    layout_type = layout_decision.layout_type
    creative_template = resolve_creative_template(user_prompt, fmt, brand_name=brand_name)
    if creative_template.layout_type != layout_type:
        layout_type = creative_template.layout_type
    is_infographic_explain = (
        fmt == "infographic"
        and (
            layout_type == "carousel_story"
            or creative_template.template_id == "infographic_explain_editorial"
            or creative_template.visual_style == "infographic_explain"
        )
    )
    if blueprint and is_infographic_explain:
        blueprint = repair_explain_infographic_copy(
            blueprint,
            layout_type=layout_type,
            user_prompt=user_prompt or "",
        )
        blueprint = repair_generic_headline(blueprint, layout_type=layout_type)
        headline = blueprint.headline or headline
        supporting = blueprint.supporting_line or supporting
        customer_quote = blueprint.customer_quote or customer_quote
        sections = [s.model_dump() for s in blueprint.sections] if blueprint.sections else sections
    logger.info(
        "visual_reasoning.template_locked",
        template_id=creative_template.template_id,
        sample=creative_template.sample_file,
        layout=layout_type,
        format=fmt,
        style=creative_template.visual_style,
    )
    if blueprint:
        stale = (blueprint.layout_type or blueprint.layout_archetype or "").strip()
        if stale and stale != layout_type:
            logger.warning(
                "visual_reasoning.layout_override",
                blueprint_layout=stale,
                resolved_layout=layout_type,
                reason=layout_decision.reason,
            )
            blueprint.layout_type = layout_type
            blueprint.layout_archetype = layout_type

    # Convert Concept Pydantic model to dict
    concept_dict = {
        "concept_name": recommended.concept_name,
        "core_idea": recommended.core_idea,
        "hook": recommended.hook,
        "narrative_angle": recommended.narrative_angle,
        "visual_angle": recommended.visual_angle,
    }

    system = _prompt_builder.build_system(
        fmt=fmt,
        layout_type=layout_type,
        brand_name=brand_name,
        brand_primary_color=brand_primary_color,
        brand_secondary_color=brand_secondary_color,
        brand_typography_font=brand_typography_font,
    )
    user = _prompt_builder.build_user(
        brand_intelligence=brand_intelligence,
        format_plan=format_plan,
        copy=copy,
        concept=concept_dict,
        user_prompt=user_prompt,
        fmt=fmt,
        layout_type=layout_type,
    )

    # Visual-semantic blueprint from Content Intelligence (Phase-1 package)
    content_intelligence = state.get("content_intelligence")
    if content_intelligence and getattr(content_intelligence, "format_architecture", None):
        fa = content_intelligence.format_architecture
        thesis = getattr(content_intelligence, "insight_thesis", "") or ""
        beats = getattr(content_intelligence, "narrative_beats", None) or []
        beat_lines = "; ".join(
            f"[{getattr(b, 'role', '')}] {getattr(b, 'message', '')}"
            for b in beats[:6]
        )
        user = (
            user
            + "\n\n════════════════════════════════════════\n"
            + "VISUAL-SEMANTIC BLUEPRINT (EXECUTE THIS HIERARCHY)\n"
            + "════════════════════════════════════════\n"
            + f"INSIGHT THESIS: {thesis}\n"
            + f"HERO STATISTIC (largest visual number): {fa.hero_statistic}\n"
            + f"SUPPORTING DATA POINTS: {fa.supporting_data_points}\n"
            + f"CORE INSIGHT: {fa.core_insight}\n"
            + f"HIERARCHY: {fa.hierarchy_notes}\n"
            + f"VISUAL PLAN: {fa.visual_plan}\n"
            + (f"NARRATIVE BEATS: {beat_lines}\n" if beat_lines else "")
            + "Hero statistic must dominate. Supporting cards secondary. "
            "Do not give equal visual weight to every box. "
            "Complete sentences only. Spell UDAN correctly (never ADAN).\n"
        )

    if blueprint:
        story = "; ".join(blueprint.story_flow or [])
        source_footer = (blueprint.source_footer or "").strip()
        sources_note = ""
        if blueprint.sources:
            sources_note = "; ".join(
                f"{s.title or 'source'}: {s.url}" for s in blueprint.sources[:4] if s.url
            )
        user = (
            user
            + "\n\n════════════════════════════════════════\n"
            + "USER-APPROVED CREATIVE BLUEPRINT — LOCK THIS EXACTLY\n"
            + "════════════════════════════════════════\n"
            + "The user reviewed and approved these EXACT strings. Render them word-for-word in the image.\n"
            + "DO NOT paraphrase, summarise, or replace ANY approved text with your own wording.\n"
            + "DO NOT change the topic, facts, or messaging from what is listed below.\n"
            + f"HEADLINE (render EXACTLY): \"{headline}\"\n"
            + (f"SUPPORTING LINE (render EXACTLY): \"{supporting}\"\n" if supporting else "")
            + (f"BODY TEXT (render EXACTLY): \"{body}\"\n" if body else "")
            + (f"CTA (render EXACTLY): \"{cta}\"\n" if cta else "")
            + (f"HOOK: \"{blueprint.hook}\"\n" if blueprint.hook else "")
            + (f"STORY FLOW: {story}\n" if story else "")
            + (f"SECTIONS (render these section labels/facts): {sections}\n" if sections else "")
            + (f"PROOF POINTS: {proof_points}\n" if proof_points else "")
            + (f"STAT HIGHLIGHTS: {stat_highlights}\n" if stat_highlights else "")
            + (f"SOURCE FOOTER: \"{source_footer}\"\n" if source_footer else "")
            + f"layout_type={layout_type} layout={blueprint.layout_archetype} purpose={blueprint.purpose}\n"
            + "════════════════════════════════════════\n"
            + "CRITICAL: Generate a FINISHED creative. Render the approved strings as sharp typography in the image. "
            "Do not leave empty shells. Do not invent alternate copy. The approved headline/body/sections are FINAL — do not rewrite them. "
            + (
                "REQUIRED: navy #003975 + orange #FFA400 accents (orange text+accents >=~2% of image); "
                if is_jiraaf_brand
                else (
                    f"REQUIRED: use {brand_name}'s EXACT Brand Space palette — "
                    + (f"PRIMARY {brand_primary_color}" if brand_primary_color else "brand primary colour")
                    + (f", SECONDARY {brand_secondary_color}" if brand_secondary_color else "")
                    + (f", ACCENT {brand_additional_colors[2]['hex'] if len(brand_additional_colors) > 2 else ''}" if brand_additional_colors and len(brand_additional_colors) > 2 else "")
                    + " — NOT Jiraaf navy #003975/orange #FFA400/ice-blue #E8F0F8; "
                    + (f"FONT: {brand_typography_font} — use this font for all headlines; " if brand_typography_font else "")
                    + "AUDIENCE: depict the EXACT target audience (correct age group/demographics) — do NOT show wrong age group; "
                )
            )
            + "ULTRA-PREMIUM clay-3D icons; content must fit fully. "
            + (
                f'Bake compact footer text EXACTLY as: "{source_footer}". '
                if source_footer
                else "If no source_footer, omit Source line (do not invent domains). "
            )
            + SOURCE_FOOTER_RULE
        )

    # Size computation early — needed by expander prompts AND image generation
    size = size_string(fmt, platform)
    canvas_desc = canvas_label(fmt, platform)
    logger.info("visual_reasoning.canvas_size", format=fmt, platform=platform, size=size)

    # 1. Complete visual reasoning structure (GPT-4o)
    service = _router.get_service("l8_visual_reasoning")
    output, metadata = await service.complete_structured(
        system=system,
        user=user,
        output_model=VisualReasoningOutput,
        layer="l8_visual_reasoning",
        max_tokens=8192,
    )

    # 1b. STAGE 2: Expand image prompt — SKIP for carousel (per-slide prompts are built below;
    # expander output was unused and burned tokens every run).
    expander_meta: dict = {}
    image_gen_prompt = output.image_prompt_direction
    if fmt == "carousel" or is_infographic_explain:
        logger.info(
            "visual_reasoning.prompt_expansion_skipped",
            reason="carousel_or_explain_uses_direct_image_prompt",
        )
    else:
        logger.info(
            "visual_reasoning.prompt_expansion_start",
            initial_prompt_len=len(output.image_prompt_direction),
        )
        expander_system = _prompt_builder.build_expander_system(
            dominant_visual_system=output.dominant_visual_system,
            fmt=fmt,
            brand_name=brand_name,
        )
        expander_user = _prompt_builder.build_expander_user(
            brand_name=brand_intelligence.brand_core.brand_name,
            visual_mood=brand_intelligence.visual_behavior.visual_mood,
            color_behavior=brand_intelligence.visual_behavior.color_behavior,
            image_behavior=brand_intelligence.visual_behavior.image_behavior,
            design_sophistication=brand_intelligence.visual_behavior.design_sophistication,
            concept_name=concept_dict.get("concept_name", ""),
            core_idea=concept_dict.get("core_idea", ""),
            visual_angle=concept_dict.get("visual_angle", ""),
            copy_headline=headline,
            copy_body=body,
            supporting_line=supporting,
            cta=cta,
            infographic_sections=sections,
            proof_points=proof_points,
            stat_highlights=stat_highlights,
            problem_statement=problem_statement,
            solution_statement=solution_statement,
            customer_quote=customer_quote,
            customer_name=customer_name,
            process_steps=process_steps,
            format_strategy=format_plan.format_strategy,
            layout_archetype=(
                blueprint.layout_archetype if blueprint and blueprint.layout_archetype else format_plan.layout_archetype
            ),
            platform=platform,
            initial_prompt=output.image_prompt_direction,
            user_prompt=user_prompt,
            dominant_visual_system=output.dominant_visual_system,
            fmt=fmt,
            layout_type=layout_type,
            hook=(blueprint.hook if blueprint else "") or getattr(copy, "hook", None) or "",
            story_flow=list(blueprint.story_flow) if blueprint and blueprint.story_flow else [],
            slides=(
                [s.model_dump() for s in blueprint.slides]
                if blueprint and blueprint.slides
                else [s.model_dump() for s in (copy.slide_copy or [])]
            ),
            canvas=canvas_desc,
        )

        try:
            expanded_prompt, expander_meta = await service.complete_text(
                system=expander_system,
                user=expander_user,
                layer="l8_prompt_expander",
                temperature=0.35,
                max_tokens=2048,
            )
            logger.info(
                "visual_reasoning.prompt_expansion_complete",
                expanded_prompt_len=len(expanded_prompt),
                expander_tokens=expander_meta.get("output_tokens", 0),
            )
            exact_lock = (
                "\n\nLOCKED EXACT COPY (bake letter-perfect — do not rewrite):\n"
                f'Headline: "{headline}"\n'
                f'Supporting: "{supporting}"\n'
                f'CTA: "{cta}"\n'
            )
            if sections:
                exact_lock += "Sections:\n"
                for i, sec in enumerate(sections[:15], start=1):
                    if isinstance(sec, dict):
                        lab = str(sec.get("section_label") or "").strip()
                        if not lab or lab.casefold() in {"item", f"item {i}"}:
                            body = str(sec.get("body") or "").strip()
                            incs_raw = sec.get("includes") or []
                            first = (
                                str(incs_raw[0]).strip()
                                if isinstance(incs_raw, list) and incs_raw
                                else ""
                            )
                            lab = " ".join((body or first).split()[:8]).rstrip(".,;:") or f"Point {i}"
                        st = sec.get("stat") or ""
                        incs = sec.get("includes") or []
                        if isinstance(incs, list):
                            incs_txt = "; ".join(str(x) for x in incs[:2])
                        else:
                            incs_txt = str(incs)
                        exact_lock += f'{i}. "{lab}" | "{st}" | "{incs_txt}"\n'
            image_gen_prompt = (expanded_prompt + exact_lock + f"\n{ICON_STYLE_LOCK}\n")[:6000]
            if not is_jiraaf_brand:
                # Keep premium icon quality, but drop Jiraaf-only finance object examples / palette defaults.
                brand_icon_lock = (
                    "\nBRAND ICON LOCK: Match THIS brand's visual mood and topic objects only. "
                    f"Brand: {brand_name or 'active Brand Space'}. "
                    "Do NOT invent finance/wallet/rupee/SEBI/bond icons unless the topic requires them. "
                    "Prefer icons that match the brand category and the user's prompt.\n"
                )
                image_gen_prompt = (expanded_prompt + exact_lock + brand_icon_lock)[:6000]
            output.image_prompt_direction = image_gen_prompt
        except Exception as e:
            logger.warning(
                f"visual_reasoning.prompt_expansion_failed, using original prompt: {e}"
            )
            image_gen_prompt = output.image_prompt_direction

    # 2. Get the correct tenant_id and brand logo path from DB
    tenant_id = None
    logo_storage_path: str | None = None
    logo_zone_instruction: str | None = brand_intelligence.visual_behavior.logo_zone_instruction

    try:
        brand_uuid = UUID(str(brand_id)) if not isinstance(brand_id, UUID) else brand_id
        async with AsyncSessionLocal() as session:
            brand = await session.get(BrandSpace, brand_uuid)
            if brand:
                tenant_id = brand.tenant_id

            # Fetch the brand logo path for composite overlay
            logo_storage_path = await get_brand_logo_storage_path(
                brand_space_id=brand_uuid,
                session=session,
            )

        if logo_storage_path:
            logger.info(
                "visual_reasoning.logo_found",
                logo_path=logo_storage_path,
                zone=logo_zone_instruction,
            )
        else:
            logger.info(
                "visual_reasoning.logo_not_found",
                brand_id=str(brand_id),
            )
    except Exception as e:
        logger.warning(f"visual_reasoning.db_tenant_or_logo_failed: {e}")

    # Fallback default UUID if DB call fails
    if not tenant_id:
        tenant_id = UUID("00000000-0000-0000-0000-000000000000")

    # 4. Image generation with gpt-image-1 + brand logo composite, falling back to SDXL/Mock
    async def _generate_one_image(
        prompt: str,
        image_size: str,
        fallback_suffix: str = "",
        *,
        composite_sebi_footer: bool = False,
        image_quality: str | None = None,
        skip_extra_locks: bool = False,
    ) -> str:
        extra = ""
        if not skip_extra_locks:
            if composite_sebi_footer:
                extra = CAROUSEL_IMAGE_EXTRA_LOCKS
            elif is_jiraaf_brand:
                extra = STATIC_IMAGE_EXTRA_LOCKS
            else:
                color_hint = ""
                if brand_intelligence and brand_intelligence.visual_behavior:
                    color_hint = str(brand_intelligence.visual_behavior.color_behavior or "").strip()
                _primary_lock = brand_primary_color or ""
                _secondary_lock = brand_secondary_color or ""
                _font_lock = brand_typography_font or ""
                _accent_lock = (brand_additional_colors[2]["hex"] if len(brand_additional_colors) > 2 else "") if brand_additional_colors else ""
                extra = (
                    f"\nBRAND VISUAL LOCK for {brand_name or 'this brand'}: "
                    + (f"PRIMARY colour {_primary_lock} — headlines, key elements. " if _primary_lock else "")
                    + (f"SECONDARY colour {_secondary_lock} — accents, icons. " if _secondary_lock else "")
                    + (f"ACCENT colour {_accent_lock}. " if _accent_lock else "")
                    + (f"FONT: {_font_lock} — use for all text. " if _font_lock else "")
                    + f"Use ONLY this brand's palette. "
                    "NEVER Jiraaf navy #003975, orange #FFA400, or ice-blue #E8F0F8. "
                    "NO SEBI footer. NO finance/wallet/rupee/bond icons unless the topic requires them. "
                    "AUDIENCE: depict the correct demographic — right age group matching brand persona.\n"
                )
        safe_prompt = _budget_prompt(prompt, extra, _IMAGE_PROMPT_BUDGET)
        logger.info(
            "visual_reasoning.image_prompt_budget",
            suffix=fallback_suffix,
            prompt_len=len(safe_prompt),
            has_headline=("HEADLINE" in safe_prompt) or ("Headline:" in safe_prompt),
            carousel=composite_sebi_footer,
        )
        try:
            dalle = DalleService()
            url = await dalle.generate_and_save(
                tenant_id=tenant_id,
                brand_space_id=brand_id,
                prompt=safe_prompt,
                size=image_size,
                logo_storage_path=logo_storage_path,
                logo_zone_instruction=logo_zone_instruction
                or "plain empty top-right corner — no text, no box, no logo drawn",
                composite_sebi_footer=composite_sebi_footer,
                # Always wipe the top-right corner before pasting the logo
                # so AI-drawn decorative icons (leaf, compass, etc.) are removed.
                wipe_reserved_corner=True,
                quality=image_quality,
            )
            logger.info(
                "visual_reasoning.dalle_success",
                url=url,
                suffix=fallback_suffix,
                logo_composited=bool(logo_storage_path),
            )
            return url
        except Exception as e:
            logger.warning(
                f"visual_reasoning.dalle_failed{fallback_suffix}, falling back to SDXL: {type(e).__name__}: {e}"
            )
            try:
                from app.integrations.object_storage import get_object_storage
                from app.services.image_generation.dalle_service import apply_brand_image_overlays

                sdxl = SdxlService()
                sdxl_url = await sdxl.generate_and_save(
                    tenant_id=tenant_id,
                    brand_space_id=brand_id,
                    prompt=safe_prompt,
                    size=image_size,
                )
                if logo_storage_path or composite_sebi_footer or wipe_reserved_corner:
                    storage = get_object_storage()
                    rel_path = sdxl_url.removeprefix("/storage/").lstrip("/")
                    raw_bytes = storage.read_bytes(rel_path)
                    processed = apply_brand_image_overlays(
                        raw_bytes,
                        storage=storage,
                        logo_storage_path=logo_storage_path,
                        logo_zone_instruction=logo_zone_instruction,
                        composite_sebi_footer=composite_sebi_footer,
                        wipe_reserved_corner=wipe_reserved_corner,
                    )
                    filename = f"sdxl-branded-{uuid4().hex[:8]}.png"
                    stored = storage.save_bytes(
                        tenant_id=UUID(str(tenant_id)),
                        brand_space_id=UUID(str(brand_id)),
                        category="generated",
                        filename=filename,
                        content=processed,
                    )
                    url = f"/storage/{stored.storage_path}"
                else:
                    url = sdxl_url
                logger.info(
                    "visual_reasoning.sdxl_success",
                    url=url,
                    suffix=fallback_suffix,
                    logo_composited=bool(logo_storage_path),
                )
                return url
            except Exception as e_sdxl:
                logger.error(f"visual_reasoning.sdxl_failed{fallback_suffix}: {e_sdxl}")
                raise RuntimeError(
                    f"Image generation failed for {fallback_suffix or 'creative'} "
                    f"(DALL·E: {type(e).__name__}; SDXL: {type(e_sdxl).__name__}: {e_sdxl})"
                ) from e_sdxl

    generated_urls: list[str] = []
    # Prefer approved blueprint slides as the carousel source of truth
    carousel_slides = list(format_plan.slide_plan or [])
    if fmt == "carousel" and blueprint and blueprint.slides:
        from types import SimpleNamespace

        carousel_slides = [
            SimpleNamespace(
                slide_number=s.slide_number,
                focus=s.role or "insight",
                visual_intent=s.headline or "",
            )
            for s in blueprint.slides
        ]
    elif fmt == "carousel" and not carousel_slides and copy.slide_copy:
        from types import SimpleNamespace

        carousel_slides = [
            SimpleNamespace(
                slide_number=s.slide_number,
                focus="insight",
                visual_intent=s.headline or "",
            )
            for s in copy.slide_copy
        ]

    if fmt == "carousel" and not carousel_slides:
        raise ValueError(
            "Carousel selected but no slides were prepared in the blueprint. "
            "Re-run Phase 1 or add slides on the approval card before generating."
        )

    if fmt == "carousel" and carousel_slides:
        slide_copy_by_number = {s.slide_number: s for s in (copy.slide_copy or [])}
        blueprint_slides = {
            s.slide_number: s for s in ((blueprint.slides if blueprint else None) or [])
        }
        # SHORT style stub ONLY — mega-locks were ~16k chars and wiped slide content at [:6500]
        if is_jiraaf_brand:
            style_stub = (
                f"Finished {platform} carousel, canvas {canvas_desc}. "
                f"{CAROUSEL_IMAGE_STYLE_STUB}"
            )
        else:
            color_hint = ""
            if brand_intelligence and brand_intelligence.visual_behavior:
                color_hint = str(brand_intelligence.visual_behavior.color_behavior or "").strip()
            _pc = brand_primary_color or ""
            _sc = brand_secondary_color or ""
            _fc = brand_typography_font or ""
            _ac = (brand_additional_colors[2]["hex"] if len(brand_additional_colors) > 2 else "") if brand_additional_colors else ""
            style_stub = (
                f"Finished {platform} carousel for {brand_name}, canvas {canvas_desc}. "
                + (f"PRIMARY brand colour: {_pc}. " if _pc else "")
                + (f"SECONDARY brand colour: {_sc}. " if _sc else "")
                + (f"ACCENT colour: {_ac}. " if _ac else "")
                + (f"FONT: {_fc}. " if _fc else "")
                + "Use ONLY this brand's palette — NOT Jiraaf navy/orange/ice-blue. "
                "Depict EXACT brand audience demographics (correct age group). "
                "No fintech/SEBI/bond visuals unless brand is in finance."
            )
        total = len(carousel_slides)
        # Build ordered storyline from blueprint for swipe continuity
        ordered_bp = sorted(
            ((blueprint.slides if blueprint else None) or []),
            key=lambda s: s.slide_number,
        )
        storyline_lines = []
        for s in ordered_bp:
            storyline_lines.append(
                f"{s.slide_number}. [{s.role}] {s.headline} — {(s.body or '')[:80]}"
            )
        if not storyline_lines and blueprint and blueprint.story_flow:
            storyline_lines = [str(x) for x in blueprint.story_flow]
        storyline_block = "\n".join(storyline_lines) or "(derive from per-slide headlines)"
        topic_lock = _q(user_prompt, 160)
        used_heroes: set[str] = set()
        used_headlines: list[str] = []

        for idx, slide in enumerate(carousel_slides):
            bp_slide = blueprint_slides.get(slide.slide_number)
            slide_copy = slide_copy_by_number.get(slide.slide_number)
            n = int(getattr(slide, "slide_number", 0) or 0) or (idx + 1)
            slide_headline = (
                (bp_slide.headline if bp_slide else None)
                or (slide_copy.headline if slide_copy else None)
                or getattr(slide, "visual_intent", None)
                or f"Slide {n}"
            )
            slide_body = (
                (bp_slide.body if bp_slide else None)
                or (slide_copy.body if slide_copy else None)
                or ""
            )
            slide_cta = (
                (bp_slide.cta if bp_slide else None)
                or (slide_copy.cta if slide_copy else None)
                or ""
            )
            slide_supporting = (
                (bp_slide.supporting_line if bp_slide else None)
                or (getattr(slide_copy, "supporting_line", None) if slide_copy else None)
                or ""
            )
            role_raw = (
                (bp_slide.role if bp_slide else None)
                or getattr(slide, "focus", None)
                or "insight"
            )
            role = _normalize_role(role_raw)
            prev_hl = ""
            next_hl = ""
            if ordered_bp:
                for j, s in enumerate(ordered_bp):
                    if s.slide_number == n:
                        if j > 0:
                            prev_hl = ordered_bp[j - 1].headline or ""
                        if j + 1 < len(ordered_bp):
                            next_hl = ordered_bp[j + 1].headline or ""
                        break
            hero = _derive_carousel_hero(
                role=role,
                n=n,
                slide_headline=str(slide_headline or ""),
                user_prompt=user_prompt or "",
                used_heroes=used_heroes,
            )
            bottoms = _derive_carousel_chips(
                role=role,
                n=n,
                bp_slide=bp_slide,
                slide_headline=str(slide_headline or ""),
                slide_body=str(slide_body or ""),
                user_prompt=user_prompt or "",
            )

            is_last = n == total or role == "cta"
            # Ensure supporting line is never empty (samples always have it)
            if not (slide_supporting or "").strip():
                slide_supporting = (slide_body or "").split(".")[0].strip()[:90]
            # Anti-repeat + ban bare topic titles ("TRADE DEFICIT", "CAPITAL CONTROLS")
            raw_hl = str(slide_headline or "").strip()
            needs_unique = _headline_is_repeat(raw_hl, used_headlines) or _is_bare_topic_headline(
                raw_hl, user_prompt or ""
            )
            if needs_unique:
                role_titles = {
                    "hook": "Most people miss this",
                    "define": "What this means in practice",
                    "impact": "How the numbers work",
                    "implication": "What this means for your money",
                    "proof": "Trade-offs to watch",
                    "myth": "The bit most people skip",
                    "cta": "What would you do?",
                    "insight": "The simple takeaway",
                }
                body_first = (slide_body or "").split(".")[0].strip()
                if (
                    body_first
                    and 4 <= len(body_first.split()) <= 10
                    and not _headline_is_repeat(body_first, used_headlines)
                    and not _is_bare_topic_headline(body_first, user_prompt or "")
                ):
                    raw_hl = body_first
                elif slide_supporting and not _is_bare_topic_headline(str(slide_supporting), user_prompt or ""):
                    # Use supporting as title if it's a real insight sentence (shorten)
                    words = str(slide_supporting).split()
                    raw_hl = " ".join(words[:8]).rstrip(".,;:")
                    if _headline_is_repeat(raw_hl, used_headlines) or _is_bare_topic_headline(raw_hl, user_prompt or ""):
                        raw_hl = role_titles.get(role, f"Key insight {n}")
                else:
                    raw_hl = role_titles.get(role, f"Key insight {n}")
                # If role title also repeats, append slide number
                if _headline_is_repeat(raw_hl, used_headlines):
                    raw_hl = f"{role_titles.get(role, 'Insight')} — slide {n}"
                slide_headline = raw_hl

            # Never ship an empty or bare-topic headline to the image model
            if not str(slide_headline or "").strip() or _is_bare_topic_headline(
                str(slide_headline), user_prompt or ""
            ):
                slide_headline = f"What investors should know next"

            # Keep headlines short enough to bake fully (samples use ~6–10 words)
            hl_words = str(slide_headline).split()
            if len(hl_words) > 10:
                slide_headline = " ".join(hl_words[:10]).rstrip(".,;:")

            fact_lines = _content_fact_lines(bp_slide, str(slide_body or ""), str(slide_supporting or ""))
            # Filter nav chips out of bottoms
            bottoms = tuple(
                ("Fact" if _is_nav_chip(x) else x) for x in bottoms
            )
            if all(_is_nav_chip(x) or x == "Fact" for x in bottoms):
                # Replace empty nav set with content-derived words
                derived = _one_word_chips(fact_lines) or _ROLE_CHIPS.get(role, _ROLE_CHIPS["insight"])
                bottoms = derived

            hl = _q(slide_headline, 80)
            sup = _q(slide_supporting, 110)
            body_txt = _q(slide_body, 260)
            fact_q = [_q(f, 90) for f in fact_lines[:3]]
            while len(fact_q) < 3:
                fact_q.append('""')
            f0, f1, f2 = fact_q[0], fact_q[1], fact_q[2]
            prior = "; ".join(used_headlines[-3:]) if used_headlines else "(none yet)"
            used_headlines.append(str(slide_headline or "")[:60])

            from app.services.image_generation.carousel_image_prompt import (
                build_brand_carousel_slide_image_prompt,
                build_carousel_slide_image_prompt,
                strip_carousel_heading_numbers,
            )

            story_blocks = [
                str(x).strip('"')
                for x in (f0, f1, f2)
                if str(x).strip() and str(x).strip() != '""'
            ]
            story_blocks = [b.strip('"') for b in story_blocks if b.strip('"')]
            slide_headline = strip_carousel_heading_numbers(str(slide_headline or ""))

            color_behavior = ""
            if brand_intelligence and brand_intelligence.visual_behavior:
                color_behavior = str(brand_intelligence.visual_behavior.color_behavior or "")

            if is_jiraaf_brand:
                slide_prompt = build_carousel_slide_image_prompt(
                    slide_number=n,
                    total_slides=total,
                    role=role,
                    headline=str(slide_headline or ""),
                    supporting=str(slide_supporting or ""),
                    body=str(slide_body or ""),
                    story_blocks=story_blocks,
                    cta=str(slide_cta or "") if is_last else "",
                    canvas_desc=canvas_desc,
                    topic=str(topic_lock or ""),
                    is_last=is_last,
                    prior_headlines=list(used_headlines[:-1]) if used_headlines else [],
                )
                carousel_style_extra = style_stub + "\n" + CAROUSEL_TONE_IMAGE_STUB
            else:
                slide_prompt = build_brand_carousel_slide_image_prompt(
                    slide_number=n,
                    total_slides=total,
                    role=role,
                    headline=str(slide_headline or ""),
                    supporting=str(slide_supporting or ""),
                    body=str(slide_body or ""),
                    story_blocks=story_blocks,
                    cta=str(slide_cta or "") if is_last else "",
                    canvas_desc=canvas_desc,
                    topic=str(topic_lock or ""),
                    is_last=is_last,
                    prior_headlines=list(used_headlines[:-1]) if used_headlines else [],
                    brand_name=brand_name,
                    color_behavior=color_behavior,
                    primary_color=brand_primary_color,
                    secondary_color=brand_secondary_color,
                )
                carousel_style_extra = (
                    f"Brand carousel — use {brand_name} colours only. NOT Jiraaf template.\n"
                    + CAROUSEL_TONE_IMAGE_STUB
                )
            # Keep continuity + prior-headline guard under budget without wiping locked DNA
            continuity = (
                f"\nSTORYLINE:\n{storyline_block}\n"
                f"Prior headlines (do not repeat): {prior}\n"
                f"Hero cue: {hero}\n"
            )
            slide_prompt = _budget_prompt(
                slide_prompt,
                continuity + "\n" + carousel_style_extra,
                _IMAGE_PROMPT_BUDGET,
            )
            logger.info(
                "visual_reasoning.carousel_slide_prompt",
                slide=n,
                role=role,
                prompt_len=len(slide_prompt),
                has_headline=hl in slide_prompt or "HEADLINE" in slide_prompt,
                headline=str(slide_headline or "")[:60],
            )
            slide_url = await _generate_one_image(
                slide_prompt,
                size,
                f"-slide-{n}",
                # Jiraaf-only legal footer — never bake onto other brands.
                composite_sebi_footer=is_jiraaf_brand,
            )
            generated_urls.append(slide_url)
    else:
        # Static / hub / ranking / trade / explain — AI image only (NO Pillow renderers).
        from app.services.image_generation.ranking_board import sanitize_ranking_text

        if is_infographic_explain and blueprint:
            color_behavior = ""
            if brand_intelligence and brand_intelligence.visual_behavior:
                color_behavior = str(brand_intelligence.visual_behavior.color_behavior or "")

            if is_jiraaf_brand:
                from app.services.image_generation.explain_image_prompt import (
                    build_explain_infographic_prompt,
                )

                explain_prompt = build_explain_infographic_prompt(
                    blueprint,
                    canvas_desc=canvas_desc,
                    supporting=supporting or "",
                    customer_quote=customer_quote or "",
                )
            else:
                explain_prompt = _prompt_builder.build_expander_user(
                    brand_name=brand_name,
                    visual_mood=brand_intelligence.visual_behavior.visual_mood,
                    color_behavior=color_behavior,
                    image_behavior=brand_intelligence.visual_behavior.image_behavior,
                    design_sophistication=brand_intelligence.visual_behavior.design_sophistication,
                    concept_name=concept_dict.get("concept_name", ""),
                    core_idea=concept_dict.get("core_idea", ""),
                    visual_angle=concept_dict.get("visual_angle", ""),
                    copy_headline=headline,
                    copy_body=body,
                    supporting_line=supporting,
                    cta=cta,
                    infographic_sections=sections,
                    proof_points=proof_points,
                    stat_highlights=stat_highlights,
                    problem_statement=problem_statement,
                    solution_statement=solution_statement,
                    customer_quote=customer_quote,
                    customer_name=customer_name,
                    process_steps=process_steps,
                    format_strategy=format_plan.format_strategy,
                    layout_archetype=(
                        blueprint.layout_archetype if blueprint and blueprint.layout_archetype else format_plan.layout_archetype
                    ),
                    platform=platform,
                    initial_prompt=output.image_prompt_direction,
                    user_prompt=user_prompt,
                    dominant_visual_system=output.dominant_visual_system,
                    fmt="infographic",
                    layout_type=layout_type,
                    hook=(blueprint.hook if blueprint else "") or getattr(copy, "hook", None) or "",
                    story_flow=list(blueprint.story_flow) if blueprint and blueprint.story_flow else [],
                    slides=[],
                    canvas=canvas_desc,
                )
                explain_prompt = (
                    explain_prompt
                    + f"\n\nBRAND DNA LOCK: Use ONLY {brand_name} Brand Space colors ({color_behavior or 'from visual identity'}). "
                    "NEVER Jiraaf navy #003975, orange #FFA400, or ice-blue #E8F0F8. NO SEBI footer.\n"
                )
            logger.info(
                "visual_reasoning.explain_ai_prompt",
                prompt_len=len(explain_prompt),
                headline=(blueprint.headline or "")[:60],
                sections=len(blueprint.sections or []),
            )
            last_err: Exception | None = None
            for attempt in range(2):
                try:
                    suffix = "" if attempt == 0 else "-explain-retry"
                    prompt_try = explain_prompt
                    if attempt == 1:
                        prompt_try = (
                            explain_prompt
                            + "\nRETRY: Previous output had spelling errors. "
                            "Render ONLY the quoted COPY block — zero paraphrase.\n"
                        )
                    single_url = await _generate_one_image(
                        prompt_try[:6000],
                        size,
                        suffix,
                        composite_sebi_footer=False,
                        image_quality="high",
                        skip_extra_locks=True,
                    )
                    generated_urls.append(single_url)
                    break
                except Exception as exc:
                    last_err = exc
                    logger.warning(
                        "visual_reasoning.explain_ai_attempt_failed",
                        attempt=attempt + 1,
                        error=str(exc)[:200],
                    )
            else:
                raise RuntimeError(
                    f"Explain infographic image failed after 2 attempts: {last_err}"
                ) from last_err
        else:
            text_bake_suffix = _error_free_text_block(
                [
                    ("HEADLINE", _q(sanitize_ranking_text(str(headline or "")), 140)),
                    ("SUPPORTING LINE", _q(sanitize_ranking_text(str(supporting or "")), 180)),
                    ("BODY", _q(body, 260)),
                    ("CTA", _q(sanitize_ranking_text(str(cta or "")), 40)),
                    ("PROBLEM", _q(problem_statement, 160)),
                    ("SOLUTION", _q(solution_statement, 160)),
                    ("SECTIONS", _q(sections, 220)),
                    ("STATS", _q(stat_highlights, 160)),
                    ("PROOF POINTS", _q(proof_points, 180)),
                    ("PROCESS STEPS", _q(process_steps, 160)),
                    ("QUOTE", _q(customer_quote, 160)),
                    ("QUOTE ATTRIBUTION", _q(customer_name, 60)),
                    (
                        "SOURCE FOOTER",
                        _q(
                            sanitize_ranking_text(
                                str((blueprint.source_footer if blueprint else "") or "")
                            ),
                            80,
                        ),
                    ),
                ],
                is_carousel=False,
            )
            card_bake = ""
            if blueprint and (blueprint.sections or []):
                is_education_layout = layout_type == "carousel_story"
                is_rank_layout = layout_type == "static_ranking"
                card_lines = [
                    "\nEXACT CARD / ROW TEXT — bake ONLY these quoted strings (zero invented words):\n"
                ]
                for i, sec in enumerate((blueprint.sections or [])[:15], start=1):
                    raw_label = (sec.section_label or "").strip()
                    if not raw_label or raw_label.casefold() in {"item", f"item {i}"}:
                        body = (sec.body or "").strip()
                        first = next(
                            (str(x).strip() for x in (sec.includes or []) if str(x).strip()),
                            "",
                        )
                        raw_label = " ".join((body or first).split()[:8]).rstrip(".,;:") or f"Point {i}"
                    label = sanitize_ranking_text(raw_label)
                    max_facts = 2
                    facts = [
                        sanitize_ranking_text(str(x).strip())
                        for x in (sec.includes or [])
                        if str(x).strip()
                    ][:max_facts]
                    stat = sanitize_ranking_text(str(sec.stat or "").strip())
                    if stat and is_rank_layout:
                        import re as _re

                        stat = _re.sub(r"US\s*\$", "USD ", stat, flags=_re.I)
                        stat = _re.sub(r"\$", "", stat)
                        facts = [stat] + facts
                    facts = facts[:max_facts]
                    if is_education_layout:
                        card_lines.append(f'CARD {i} HEADING: "{label}"\n')
                        for j, fact in enumerate(facts, start=1):
                            # Keep up to 20 words — enough for a complete sentence
                            short = " ".join(fact.split()[:20])
                            card_lines.append(f'CARD {i} EXPLANATION {j}: "{short}"\n')
                    else:
                        card_lines.append(f'CARD {i} name: "{label}"\n')
                        for j, fact in enumerate(facts, start=1):
                            # Keep up to 15 words — complete sentence, not truncated bullets
                            short = " ".join(fact.split()[:15])
                            card_lines.append(f'CARD {i} line {j}: "{short}"\n')
                card_lines.append(f"Layout: {creative_template.image_stub}\n")
                card_bake = "".join(card_lines)

            layout_hint = creative_template.l8_image_hint(canvas_desc=canvas_desc)
            if creative_template.layout_type == "static_ranking":
                layout_hint += f"\n{INFOGRAPHIC_AUDIENCE_TONE_LOCK}\n"
            layout_hint += (
                f"Canvas size LOCKED: {canvas_desc}. Fit every element inside with >=6% margins.\n"
                "Never clip CTA/text/icons. CTA COMPACT <=28% width, <=4 words.\n"
            )
            single_url = await _generate_one_image(
                (image_gen_prompt + layout_hint + card_bake + text_bake_suffix)[:6000],
                size,
                composite_sebi_footer=False,
            )
            generated_urls.append(single_url)

    # Set the generated image fields on the output Pydantic model
    output.generated_image_url = generated_urls[0] if generated_urls else ""
    output.generated_image_urls = generated_urls

    total_l8_latency = metadata["latency_ms"]
    total_l8_input = metadata["input_tokens"]
    total_l8_output = metadata["output_tokens"]
    try:
        total_l8_latency += expander_meta["latency_ms"]
        total_l8_input += expander_meta["input_tokens"]
        total_l8_output += expander_meta["output_tokens"]
    except (KeyError, TypeError):
        pass

    return {
        "visual_reasoning": output,
        "layer_latencies": {"l8_visual_reasoning": total_l8_latency},
        "token_usage": {
            "l8_visual_reasoning": {
                "input_tokens": total_l8_input,
                "output_tokens": total_l8_output,
            }
        },
    }
