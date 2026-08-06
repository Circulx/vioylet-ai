from __future__ import annotations



"""Build AI image prompts for infographic EXPLAIN (polymer sample DNA).



AI-only - no Pillow text overlay. Copy is hard-locked, spelling-sanitized, and

kept SHORT. Visual quality matches oil-bar ranking sample (text colours + HD icons).

"""



import re

from typing import Any



from app.prompts.brand_copy_tone import (

    EXPLAIN_COLOR_VIBRANCY_LOCK,

    ICON_STYLE_LOCK,

    INFOGRAPHIC_EXPLAIN_SPELLING_LOCK,

    JIRAAF_BG,

    JIRAAF_BODY_GRAY,

    JIRAAF_INSIGHT_CREAM,

    JIRAAF_NAVY,

    JIRAAF_ORANGE,

    JIRAAF_PARAGRAPH_INSIGHT_LOCK,

    JIRAAF_SAMPLE_VISUAL_DNA,

)

from app.services.image_generation.ranking_board import sanitize_ranking_text



_SAFE_CHARS = re.compile(r"[^\w\s₹%&.,'\"?!():;\-–/×+]")





def _scrub_bake_text(text: str, *, max_words: int = 24) -> str:

    """Sanitize and trim for image bake - ASCII-safe, no garbled tokens."""

    t = sanitize_ranking_text(str(text or ""))

    t = _SAFE_CHARS.sub("", t)

    t = re.sub(r"\s+", " ", t).strip()

    words = t.split()

    return " ".join(words[:max_words]).strip()





def _orange_words_line(words: list[str]) -> str:

    if not words:

        return ""

    quoted = ", ".join(f'"{w}"' for w in words if w)

    return f"  ORANGE TEXT ({JIRAAF_ORANGE}): paint these words orange → {quoted}\n"





def _headline_orange_hint(headline: str) -> str:

    """Pick 1–2 words in headline to paint orange (oil-bar style)."""

    words = (headline or "").split()

    if not words:

        return ""

    if len(words) <= 3:

        return _orange_words_line([words[0]])

    # Prefer topic words: plastic, polymer, RBI, currency, notes, etc.

    for w in words:

        low = w.lower().strip("?.,!")

        if low in ("plastic", "polymer", "currency", "notes", "rbi", "oil", "investing"):

            return _orange_words_line([w.strip("?.,!")])

    return _orange_words_line([words[2] if len(words) > 2 else words[1]])





def build_explain_infographic_prompt(

    blueprint: Any,

    *,

    canvas_desc: str,

    supporting: str = "",

    customer_quote: str = "",

) -> str:

    """Single prompt for gpt-image: sample layout + oil-bar quality + short typo-free copy."""

    sec_blocks: list[str] = []

    orange_notes: list[str] = []

    sections = getattr(blueprint, "sections", None) or []



    for i, sec in enumerate(sections[:3], start=1):

        label = _scrub_bake_text(getattr(sec, "section_label", None) or f"Section {i}", max_words=8)

        sec_blocks.append(f'SECTION {i} HEADING: "{label}"')

        includes = getattr(sec, "includes", None) or []

        facts = [str(x).strip() for x in includes if str(x).strip()][:3]

        body_raw = _scrub_bake_text(getattr(sec, "body", None) or "", max_words=14)



        if facts:

            if body_raw:

                sec_blocks.append(f'SECTION {i} INTRO: "{body_raw}"')

                if i == 2:

                    orange_notes.append(_orange_words_line(["cautious", "before"]))

            for j, raw in enumerate(facts, start=1):

                fact = sanitize_ranking_text(raw)

                if "|" in fact:

                    title, rest = [p.strip() for p in fact.split("|", 1)]

                elif ". " in fact and len(fact.split(". ")[0].split()) <= 5:

                    title, rest = fact.split(". ", 1)

                else:

                    parts = fact.split()

                    title = " ".join(parts[:3])

                    rest = " ".join(parts[3:])

                title = _scrub_bake_text(title, max_words=4)

                rest = _scrub_bake_text(rest, max_words=8)

                sec_blocks.append(f'SECTION {i} CARD {j} TITLE: "{title}" BODY: "{rest}"')

        elif body_raw:

            sec_blocks.append(f'SECTION {i} BODY: "{body_raw}"')

            if i == 3:

                orange_notes.append(_orange_words_line(["₹10", "₹20", "adoption"]))



    hl = _scrub_bake_text(

        getattr(blueprint, "headline", None) or getattr(blueprint, "title", None) or "",

        max_words=10,

    )

    intro = _scrub_bake_text(

        getattr(blueprint, "supporting_line", None) or supporting or "",

        max_words=14,

    )

    quote = _scrub_bake_text(

        getattr(blueprint, "customer_quote", None) or customer_quote or "",

        max_words=16,

    )

    src = _scrub_bake_text(

        getattr(blueprint, "source_footer", None) or "Source: rbi.org.in",

        max_words=8,

    )

    if not src.lower().startswith("source"):

        src = f"Source: {src}"



    orange_notes.insert(0, _headline_orange_hint(hl))



    copy_block = (

        f'HEADLINE: "{hl}"\n'

        + (f'INTRO: "{intro}"\n' if intro else "")

        + "\n".join(sec_blocks)

        + "\n"

        + (f'CALLOUT: "{quote}"\n' if quote else "")

        + (f'SOURCE: "{src}"\n' if src else "")

    )



    text_colour_lock = f"""

TEXT COLOURS (headline/body = oil-bar sample; callout = polymer sample EXACTLY):
FLAT, FULLY SATURATED colour only — no muted/washed-out/pastel navy or orange (see vibrancy lock above).

- BG ice-blue {JIRAAF_BG}

- Headline: navy {JIRAAF_NAVY} bold — paint 1–2 accent words ORANGE {JIRAAF_ORANGE} inside headline only

- Intro / supporting: gray {JIRAAF_BODY_GRAY} — smaller than headline

- Section headings + card titles: navy {JIRAAF_NAVY} bold

- Card body + paragraph text: gray {JIRAAF_BODY_GRAY} — one line each, sharp sans-serif

- Callout box: white/very-pale fill, THIN orange {JIRAAF_ORANGE} border — NOT solid cream/orange

- Callout text: dark navy/charcoal, bold ONLY 2–3 key phrases (NOT the whole sentence orange)

- Source footer: light gray, small

{"".join(orange_notes)}

"""



    icon_lock = f"""

ICON QUALITY (SAME render fidelity as oil-bar 3D barrels — premium HD studio render):

- Section 1: 3 LARGE navy circular badges, crisp white line-art (rupee-arrow, shield/clock, globe)

- Section 2: 3 LARGE clay-3D props with gold/navy accents — container, ATM, wallet with notes

- NO bottom-right hero icon cluster on this layout — sample_infographic_explain_rbi_polymer.png

  ends with the callout box + source line only. Keep that empty space clean, do not add extra icons.

- Callout: orange circle + white lightbulb left of the thin-border callout box

- Icons sharp at 100% zoom — satin clay, studio lighting, NOT clipart, NOT blurry

{ICON_STYLE_LOCK}

"""



    return (

        "=== RENDER THIS EXACT HEADLINE (verbatim, character-perfect) ===\n"

        f'"{hl}"\n'

        "=== END HEADLINE — this is the ONLY headline text. Everything below this line is a\n"

        "DESIGN BRIEF for an infographic image — none of these instruction words (INFOGRAPHIC,\n"

        "LinkedIn, educational, sample, layout, canvas, etc.) are content to render. ===\n\n"

        "Design a premium finance-education INFOGRAPHIC image. English only. Zero spelling mistakes.\n"

        "Visual quality reference = sample_static_oil_consumption_bars.png (text colours + HD icons).\n"

        "Layout reference = sample_infographic_explain_rbi_polymer.png (multi-section editorial).\n"

        f"Canvas {canvas_desc}.\n"

        "Empty top-right logo pocket — NEVER draw JIRAAF wordmark.\n\n"

        f"{JIRAAF_SAMPLE_VISUAL_DNA}\n"

        f"{EXPLAIN_COLOR_VIBRANCY_LOCK}\n"

        f"{JIRAAF_PARAGRAPH_INSIGHT_LOCK}\n"

        "LAYOUT (all blocks required):\n"

        "1) Header: navy headline with orange accent word(s) + gray intro line\n"

        "2) Section A: orange LEFT bar + 3 columns (navy circular icon + navy title + gray body)\n"

        "3) Section B: orange LEFT bar + intro with orange highlights + 3 clay-3D columns\n"

        "4) Section C: orange LEFT bar + short gray paragraph (max 2 lines)\n"

        "5) CALLOUT: white/pale box + thin orange border + lightbulb + dark navy insight text (bold key phrases only)\n"

        "6) Source line bottom-left — leave remaining space clean, NO extra hero icons\n\n"

        f"{text_colour_lock}\n"

        f"{icon_lock}\n"

        f"{INFOGRAPHIC_EXPLAIN_SPELLING_LOCK}\n"

        "RENDER ONLY the quoted copy below — character-perfect, no invented headline, no extra text.\n"

        "The HEADLINE line below MUST match the exact headline stated at the very top of this brief.\n\n"

        "=== EXACT COPY TO BAKE (this is the ONLY text allowed in the image) ===\n"

        f"{copy_block}"

        "=== END COPY — do not add, invent, or substitute any other headline/body text ===\n"

    )


