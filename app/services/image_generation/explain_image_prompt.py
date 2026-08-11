from __future__ import annotations

"""Build AI image prompts for INFOGRAPHIC EXPLAIN / paragraph-information layouts ONLY.

LOCKED premium LinkedIn editorial DNA (Apple + Stripe + Notion + McKinsey + Bloomberg).
Do NOT use for ranking / top-N list boards — those stay on ranking_board.py.
"""

import re
from typing import Any

from app.services.image_generation.ranking_board import sanitize_ranking_text

# Explain-only palette (does not change ranking board colours)
EXPLAIN_BG = "#87CEFA"
EXPLAIN_HEADING = "#033B5E"
EXPLAIN_ORANGE = "#F7931A"
EXPLAIN_SECONDARY_BLUE = "#2D8CFF"
EXPLAIN_CARD = "#F8FBFF"
EXPLAIN_BORDER = "#DCEAF5"
EXPLAIN_BODY = "#4E6272"

_SAFE_CHARS = re.compile(r"[^\w\s₹%&.,'\"?!():;\-–/×+]")


def _scrub(text: str, *, max_words: int = 16) -> str:
    t = sanitize_ranking_text(str(text or ""))
    t = _SAFE_CHARS.sub("", t)
    t = re.sub(r"\s+", " ", t).strip()
    return " ".join(t.split()[:max_words]).strip()


def _split_fact(raw: str) -> tuple[str, str]:
    fact = sanitize_ranking_text(raw)
    if "|" in fact:
        title, rest = [p.strip() for p in fact.split("|", 1)]
    elif ". " in fact and len(fact.split(". ")[0].split()) <= 5:
        title, rest = fact.split(". ", 1)
    else:
        parts = fact.split()
        title = " ".join(parts[:3])
        rest = " ".join(parts[3:])
    return _scrub(title, max_words=4).upper(), _scrub(rest, max_words=14)


def _headline_three_lines(headline: str) -> str:
    """Split headline into 3-line layout with middle word largest."""
    words = (headline or "").upper().split()
    if not words:
        return 'Line1: ""\nLine2: "" (LARGEST)\nLine3: ""'
    if len(words) <= 2:
        return f'Line1: "{words[0]}"\nLine2: "{" ".join(words[1:])}" (LARGEST)'
    third = max(1, len(words) // 3)
    return (
        f'Line1: "{" ".join(words[:third])}"\n'
        f'Line2: "{" ".join(words[third : third * 2])}" (LARGEST)\n'
        f'Line3: "{" ".join(words[third * 2 :])}"'
    )


def build_explain_infographic_prompt(
    blueprint: Any,
    *,
    canvas_desc: str,
    supporting: str = "",
    customer_quote: str = "",
) -> str:
    """LOCKED premium paragraph/info LinkedIn infographic prompt (not ranking).

    Uses the actual blueprint content — headline, sections, CTA — NOT hardcoded defaults.
    The layout and aesthetic are locked (Jiraaf premium), but ALL copy comes from the blueprint.
    """
    sections = getattr(blueprint, "sections", None) or []

    # ── Extract headline, supporting, CTA from blueprint ──────────────────────
    hl = _scrub(
        getattr(blueprint, "headline", None) or getattr(blueprint, "title", None) or "",
        max_words=12,
    ).upper()
    sub_headline = _scrub(
        getattr(blueprint, "supporting_line", None) or supporting or "",
        max_words=18,
    )
    cta_text = _scrub(
        getattr(blueprint, "cta", None) or "",
        max_words=8,
    ).upper()
    source_footer = _scrub(
        getattr(blueprint, "source_footer", None) or customer_quote or "",
        max_words=14,
    )

    # ── Extract section cards from blueprint sections ──────────────────────────
    cards: list[tuple[str, str, str]] = []  # (TITLE, body, icon_hint)
    for sec in sections[:8]:
        raw_label = _scrub(getattr(sec, "section_label", None) or "", max_words=5).upper()
        raw_body = _scrub(getattr(sec, "body", None) or "", max_words=18)
        includes = [str(x).strip() for x in (getattr(sec, "includes", None) or []) if str(x).strip()]
        stat = _scrub(getattr(sec, "stat", None) or "", max_words=6)

        # Use includes as body if body is empty
        if not raw_body and includes:
            raw_body = _scrub(includes[0], max_words=18)

        # Use stat as suffix if available
        if stat and stat not in raw_body:
            raw_body = f"{raw_body} ({stat})" if raw_body else stat

        if raw_label or raw_body:
            # Pick a generic icon hint based on label content
            icon_hint = _pick_icon_hint(raw_label + " " + raw_body)
            cards.append((raw_label or "POINT", raw_body, icon_hint))

    # ── Build card lines for the prompt ───────────────────────────────────────
    card_lines = "\n".join(
        f'{i}. TITLE "{title}" | BODY "{body}" | ICON {icon}'
        for i, (title, body, icon) in enumerate(cards, start=1)
    ) if cards else "(Use the topic facts to generate relevant card content.)"

    headline_lines = _headline_three_lines(hl)
    num_cards = len(cards) or 4
    grid_desc = f"2 rows x {(num_cards + 1) // 2} columns" if num_cards > 2 else f"{num_cards} cards"

    return (
        "=== LOCKED FORMAT: PREMIUM LINKEDIN INFOGRAPHIC EXPLAIN (PARAGRAPH / INFORMATION ONLY) ===\n"
        "NOT a ranking board. NOT a top-N list chart. This is an educational/explanatory poster.\n"
        f"Canvas: {canvas_desc or '1080x1350'} portrait 4:5. Ultra HD / 4K LinkedIn-ready.\n"
        "Aesthetic: Apple + Stripe + Notion + McKinsey + Bloomberg — expensive, elegant, minimal.\n"
        "Spacious layout, lots of breathing room, invisible grid, equal spacing, ≥6% margins.\n\n"
        f"BACKGROUND: full-bleed {EXPLAIN_BG} with very subtle radial gradient + soft lighting. "
        "No textures, patterns, noise, or dark BG.\n\n"
        "BRANDING: empty TOP-RIGHT corner (~7% canvas width) — COMPLETELY BLANK, background colour only. "
        "NEVER draw any logo, leaf, compass, badge, icon, or wordmark in the top-right. "
        "Brand logo is composited in post-processing.\n"
        "NO SEBI / legal disclaimer on this infographic.\n\n"
        "COLOUR PALETTE:\n"
        f"- Heading text: {EXPLAIN_HEADING}\n"
        f"- Accent orange (highlights ONLY, 2-3 elements max): {EXPLAIN_ORANGE}\n"
        f"- Secondary blue: {EXPLAIN_SECONDARY_BLUE}\n"
        f"- Soft white cards: {EXPLAIN_CARD}\n"
        f"- Card border: {EXPLAIN_BORDER}\n"
        f"- Body/caption text: {EXPLAIN_BODY}\n"
        "Orange ONLY for accents / CTA fill / key title highlights — never overuse.\n\n"
        "TYPOGRAPHY: bold geometric sans (SF Pro / Inter / Helvetica Now / Gilroy / Poppins SemiBold). "
        "Hierarchy = huge title > medium section titles > body > captions. Corporate, readable.\n"
        "COMPLETE SENTENCES — never truncate mid-word or mid-sentence. Shrink font if needed.\n\n"
        "TITLE (3-line layout, key middle word LARGEST):\n"
        f"{headline_lines}\n\n"
        "HERO (top-right area, under logo pocket — NO text on hero):\n"
        "Premium photoreal 3D floating object relevant to the topic — clean studio lighting, "
        "soft shadow, reflections. Physically rendered, NOT cartoon, NOT clipart.\n\n"
        "CARDS: rounded ~24px, soft shadow, light borders, large padding, float above BG.\n\n"
        "ICON STYLE (NON-NEGOTIABLE): Pixar-quality 3D ONLY — matte/ceramic/metal/glass. "
        "Studio lighting, soft reflections, GI, AO, ultra detailed. "
        "NOT flat, NOT emoji, NOT outline, NOT clipart.\n\n"
        "LAYOUT:\n"
        "1) TOP-LEFT: 3-line title + optional compact orange CTA pill under title\n"
        f'   Supporting line: "{sub_headline}"\n'
        "2) TOP-RIGHT: premium 3D hero object relevant to topic (no text on hero)\n"
        f"3) MIDDLE GRID: {grid_desc} of explanation cards (REQUIRED — do not leave empty)\n"
        f"4) BOTTOM: source footer / CTA strip\n"
        "5) NEVER empty cards. NEVER invented placeholder text.\n\n"
        "RENDER QUALITY: Octane/Redshift/Cinema4D look — ray tracing, GI, crisp edges, HDR.\n"
        "NEGATIVE: no clipart, cartoons, flat icons, pixelation, busy BG, watermark, "
        "random gradients, inconsistent spacing, handwritten fonts, neon, cheap clutter.\n\n"
        "=== BAKE ONLY THIS COPY (letter-perfect, zero typos, COMPLETE sentences) ===\n"
        f'HEADLINE: "{hl}"\n'
        + (f'CTA (orange fill, white text, compact pill): "{cta_text}"\n' if cta_text else "")
        + f'SUPPORTING LINE: "{sub_headline}"\n'
        f"SECTION CARDS ({num_cards} cards total):\n"
        f"{card_lines}\n"
        + (f'SOURCE FOOTER: "{source_footer}"\n' if source_footer else "")
        + "=== END LOCKED EXPLAIN INFOGRAPHIC PROMPT ===\n"
    )


def _pick_icon_hint(text: str) -> str:
    """Pick a relevant 3D icon hint based on keywords in the label/body."""
    t = text.lower()
    if any(k in t for k in ("airport", "flight", "air", "runway", "terminal", "plane", "udan")):
        return "3D glossy airplane or airport tower with soft shadow"
    if any(k in t for k in ("money", "invest", "fund", "crore", "lakh", "₹", "revenue", "cost")):
        return "3D gold coins or rising bar chart"
    if any(k in t for k in ("job", "employ", "work", "labour", "skill")):
        return "3D briefcase or handshake"
    if any(k in t for k in ("connect", "route", "region", "city", "map", "network")):
        return "3D location pin or network nodes"
    if any(k in t for k in ("growth", "expand", "develop", "build", "construct", "infra")):
        return "3D building or construction crane"
    if any(k in t for k in ("trade", "export", "import", "global", "international")):
        return "3D cargo ship or globe"
    if any(k in t for k in ("tech", "digital", "data", "software", "cloud")):
        return "3D chip or circuit board"
    if any(k in t for k in ("health", "medical", "hospital", "care")):
        return "3D medical cross or stethoscope"
    if any(k in t for k in ("learn", "education", "school", "skill", "train")):
        return "3D book or graduation cap"
    if any(k in t for k in ("secure", "safe", "protect", "lock")):
        return "3D shield with checkmark"
    if any(k in t for k in ("environment", "green", "eco", "sustain", "solar", "energy")):
        return "3D green leaf or solar panel"
    if any(k in t for k in ("time", "fast", "speed", "quick")):
        return "3D clock or lightning bolt"
    if any(k in t for k in ("passenger", "tourist", "travel", "trip")):
        return "3D suitcase or passport"
    return "Premium 3D icon relevant to the topic with soft studio lighting"
