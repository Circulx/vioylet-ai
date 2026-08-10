from __future__ import annotations

"""CAROUSEL slide bake — sample colours + connected infographic layouts.

NO numbers in headlines (no 1. 2. 6. or 01 badges).
Connected infographic style: small icons + labels linked by lines/arrows (Magnific-style).
Logo + disclaimer composited after — never baked.
"""

import re

from app.services.image_generation.ranking_board import sanitize_ranking_text

CAROUSEL_BG = "#D9ECF8"
CAROUSEL_BG_ALT = "#E8F4FC"
CAROUSEL_NAVY = "#033B5E"
CAROUSEL_ORANGE = "#FF8C24"
CAROUSEL_BODY = "#2F4A5E"
CAROUSEL_WHITE = "#FFFFFF"
CAROUSEL_GREEN = "#36B37E"
CAROUSEL_GOLD = "#F4B400"
CAROUSEL_BLUE = "#3B82F6"

_SAFE = re.compile(r"[^\w\s₹%&.,'\"?!():;\-–/×+&]")
# Strip list prefixes: "1.", "6.", "01", "02 —", etc.
_HEADING_NUMBER_PREFIX = re.compile(
    r"^(?:\d{1,2}\s*[\.\)\-–:]\s*|\d{1,2}\s+)",
    re.IGNORECASE,
)

INFOGRAPHIC_LAYOUT_LOCK = """
CONNECTED INFOGRAPHIC LAYOUT (MAGNIFIC / PREMIUM EDITORIAL STYLE):
• Show content through CONNECTED visual modules — not one giant blob.
• Use 2–4 small premium round-icon nodes OR mini white cards linked by thin navy/orange
  connector lines, curved arrows, or dotted paths (left→right or top→down flow).
• Each node = SMALL 3D icon (~8–12% size) + short text label beside/under it (from copy).
• Mix scales: one medium hero object (20–30%) + 2–3 smaller connected nodes telling the story.
• White rounded cards with soft shadow; thin orange accent dots on connectors.
• Process / benefit / cause→effect chains — icons visually CONNECT the ideas.
• Asymmetric: headline+body TOP-LEFT; connected infographic cluster fills right/center.
• BAN: numbered headings, page counters, single centered poster, disconnected random icons.
"""

CREATIVE_DEPTH_LOCK = """
3D CRAFT (premium, not flat):
• Small icons still Pixar-quality — glass, ceramic, matte plastic, soft gold.
• Soft studio light, contact shadows, depth layers (foreground nodes, midground hero).
• Optional soft blue podium under hero only — keep infographic nodes floating cleanly.
"""

SAMPLE_SLIDE_SPECS: dict[int, dict[str, str]] = {
    1: {
        "role": "cover",
        "composition": (
            "COVER: LEFT headline stack (PLASTIC emphasised) + orange underline + tagline + body. "
            "RIGHT: medium 3D cluster on podium (note in glass + coins + sprout + shield)."
        ),
        "infographic": "optional 3 connected mini nodes under body: durability | security | sustainability",
    },
    2: {
        "role": "why",
        "composition": "WHY: headline + body top-left. Connected flow: bank icon → arrow → RBI seal.",
        "infographic": "horizontal 2-node connected path with curved arrow between",
    },
    3: {
        "role": "overview",
        "composition": "OVERVIEW: headline top. Hub-and-spoke — central shield, 4–5 small icons on connector lines.",
        "infographic": "radial connected infographic (shield hub + orbiting nodes on lines)",
    },
    4: {
        "role": "detail",
        "composition": "LONGER LIFE: headline (NO number) + body. Hourglass hero + stat card '2-3x LONGER'.",
        "infographic": "hourglass node → arrow → clock node → arrow → calendar card",
    },
    5: {
        "role": "detail",
        "composition": "COST EFFECTIVE: coins + down arrow. Connected row: print cost → logistics → savings.",
        "infographic": "3 small nodes linked left-to-right with down-trend arrow",
    },
    6: {
        "role": "detail",
        "composition": "STRONGER SECURITY: lock + fingerprint + shield in connected triangle layout.",
        "infographic": "3-node triangle connected by lines",
    },
    7: {
        "role": "detail",
        "composition": "WATER RESISTANT: note in water splash. Flow: note → water drop → clean note.",
        "infographic": "3-step horizontal flow with droplet icons",
    },
    8: {
        "role": "detail",
        "composition": "ENVIRONMENT FRIENDLY: large recycle symbol + 2 small connected leaf/waste nodes.",
        "infographic": "recycle hub with 2 spoke lines to eco nodes",
    },
    9: {
        "role": "detail",
        "composition": "BETTER FOR ECONOMY: bar chart + ₹ coin + up arrow. NO '6.' in headline.",
        "infographic": "connected row: lower cost → less waste → stronger circulation (small icons + labels)",
    },
    10: {
        "role": "close",
        "composition": "ROAD AHEAD: India map + city blocks. Timeline flow: test → pilot → rollout.",
        "infographic": "3 connected milestone nodes on a path line",
    },
}


def _scrub(text: str, *, max_words: int = 24) -> str:
    t = sanitize_ranking_text(str(text or ""))
    t = _SAFE.sub("", t)
    t = re.sub(r"\s+", " ", t).strip()
    return " ".join(t.split()[:max_words]).strip()


def strip_carousel_heading_numbers(text: str) -> str:
    """Remove list/slide number prefixes from headlines — user forbids numbers in headings."""
    t = _scrub(text, max_words=16)
    t = _HEADING_NUMBER_PREFIX.sub("", t).strip()
    # Also strip leading "SLIDE N" patterns
    t = re.sub(r"^slide\s+\d+\s*[-:]\s*", "", t, flags=re.IGNORECASE).strip()
    return t.upper() if t else "KEY INSIGHT"


def _slide_spec(slide_number: int, role: str) -> dict[str, str]:
    n = max(1, min(int(slide_number or 1), 10))
    if n in SAMPLE_SLIDE_SPECS:
        return SAMPLE_SLIDE_SPECS[n]
    return {
        "role": (role or "insight").lower(),
        "composition": "Left text + connected infographic nodes (2–4 small icons on connector lines).",
        "infographic": "horizontal connected flow with small icons + short labels",
    }


def build_carousel_slide_image_prompt(
    *,
    slide_number: int,
    total_slides: int,
    role: str,
    headline: str,
    supporting: str = "",
    body: str = "",
    story_blocks: list[str] | None = None,
    cta: str = "",
    canvas_desc: str = "1080x1350",
    topic: str = "",
    is_last: bool = False,
    prior_headlines: list[str] | None = None,
) -> str:
    """Connected infographic carousel slide. NO numbers in headings."""
    spec = _slide_spec(slide_number, role)
    hl = strip_carousel_heading_numbers(headline)
    sup = _scrub(supporting, max_words=14).upper() if supporting else ""
    body_txt = _scrub(body, max_words=28)
    blocks = [_scrub(b, max_words=14) for b in (story_blocks or []) if str(b).strip()][:4]
    cta_label = _scrub(cta, max_words=4) if (is_last and cta) else ""
    topic_clean = _scrub(topic, max_words=12)
    priors = [strip_carousel_heading_numbers(p) for p in (prior_headlines or []) if str(p).strip()][:9]
    prior_line = "; ".join(f'"{p}"' for p in priors) if priors else "(first slide)"

    nodes = ""
    if blocks:
        nodes = (
            "CONNECTED CONTENT NODES (bake each label beside its small icon):\n"
            + "\n".join(
                f'  NODE {i}: small 3D icon + label "{b}" — link to next with thin orange/navy line/arrow'
                for i, b in enumerate(blocks, start=1)
            )
            + "\n"
        )
    else:
        nodes = f"INFOGRAPHIC PATTERN: {spec['infographic']}\n"

    return (
        "=== PREMIUM CAROUSEL — CONNECTED INFOGRAPHIC TEMPLATE ===\n"
        "Editorial LinkedIn carousel like premium infographic designs: "
        "small connected icons + labels showing the story flow. Sample colours/layout craft.\n"
        f"Canvas {canvas_desc} 1080×1350.\n\n"
        f"{INFOGRAPHIC_LAYOUT_LOCK}\n"
        f"{CREATIVE_DEPTH_LOCK}\n"
        "════════════════════════════════════\n"
        "ABSOLUTE BANS\n"
        "════════════════════════════════════\n"
        "• NO numbers in headline — never '1.', '2.', '6.', '01', '02', step counters, or list prefixes.\n"
        "• NO page numbers / '1 of N' / slide badges anywhere on the image.\n"
        "• NO logo / JIRAAF / giraffe — top-right EMPTY (Brand Space composite).\n"
        "• NO disclaimer / SEBI / tagline — bottom EMPTY (Pillow composite).\n"
        "• Headline must be words ONLY (e.g. BETTER FOR THE ECONOMY — not 6. BETTER...).\n\n"
        "COLOURS: "
        f"BG {CAROUSEL_BG} | navy {CAROUSEL_NAVY} | orange {CAROUSEL_ORANGE} | "
        f"body {CAROUSEL_BODY} | white cards {CAROUSEL_WHITE}\n"
        "CHROME: empty top-right logo pocket · empty bottom footer zone.\n\n"
        f"COMPOSITION: {spec['composition']}\n"
        f"{nodes}\n"
        "TYPOGRAPHY: left-aligned UPPERCASE headline (NO digits) + thin orange underline. "
        "Body 1–2 lines. Zero typos.\n"
        f'HEADLINE (no numbers): "{hl}"\n'
        f"FORBIDDEN prior headlines: {prior_line}\n\n"
        "COPY TO BAKE:\n"
        + (f'TOPIC: "{topic_clean}"\n' if topic_clean else "")
        + f'HEADLINE: "{hl}"\n'
        + (f'TAGLINE: "{sup}"\n' if sup else "")
        + (f'BODY: "{body_txt}"\n' if body_txt else "")
        + (f'CTA: "{cta_label}"\n' if cta_label else "")
        + "=== END ===\n"
    )


def build_carousel_style_stub() -> str:
    return (
        f"CAROUSEL: BG {CAROUSEL_BG}; connected infographic (small icons + lines/arrows + labels); "
        "NO numbers in headline; NO page badges; empty logo/footer pockets."
    )


def build_brand_carousel_slide_image_prompt(
    *,
    slide_number: int,
    total_slides: int,
    role: str,
    headline: str,
    supporting: str = "",
    body: str = "",
    story_blocks: list[str] | None = None,
    cta: str = "",
    canvas_desc: str = "1080x1350",
    topic: str = "",
    is_last: bool = False,
    prior_headlines: list[str] | None = None,
    brand_name: str = "",
    color_behavior: str = "",
    primary_color: str = "",
    secondary_color: str = "",
    accent_color: str = "",
) -> str:
    """Brand-specific carousel — uses Brand Space colours, NOT Jiraaf RBI template."""
    hl = strip_carousel_heading_numbers(headline)
    sup = _scrub(supporting, max_words=14)
    body_txt = _scrub(body, max_words=28)
    blocks = [_scrub(b, max_words=14) for b in (story_blocks or []) if str(b).strip()][:4]
    cta_label = _scrub(cta, max_words=4) if (is_last and cta) else ""
    topic_clean = _scrub(topic, max_words=12)
    priors = [strip_carousel_heading_numbers(p) for p in (prior_headlines or []) if str(p).strip()][:9]
    prior_line = "; ".join(f'"{p}"' for p in priors) if priors else "(first slide)"
    palette = color_behavior or (
        f"primary {primary_color or CAROUSEL_NAVY}, secondary {secondary_color or CAROUSEL_BODY}, "
        f"accent {accent_color or CAROUSEL_ORANGE}"
    )
    nodes = ""
    if blocks:
        nodes = "\n".join(
            f'  NODE {i}: small icon + "{b}" linked by connector line'
            for i, b in enumerate(blocks, start=1)
        )

    return (
        "=== BRAND CAROUSEL SLIDE — CONNECTED INFOGRAPHIC (NOT JIRAAF TEMPLATE) ===\n"
        f"Brand: {brand_name or 'this brand'}. Use ONLY this brand's visual identity colours.\n"
        f"DO NOT use Jiraaf ice-blue #E8F0F8, Jiraaf navy #003975, or Jiraaf orange #FFA400 unless this IS Jiraaf.\n"
        f"Canvas {canvas_desc} 1080×1350. Beat {slide_number}/{total_slides}. Role: {role}.\n\n"
        f"BRAND COLOURS: {palette}\n"
        "Light clean background using brand primary/secondary tints — not Jiraaf sample colours.\n\n"
        f"{INFOGRAPHIC_LAYOUT_LOCK}\n"
        "BANS: NO numbers in headline (no 1. 2. 6.), NO page badges, NO logo baked, NO disclaimer baked.\n"
        "Use connected small-icon infographic layout to show depth content.\n\n"
        f'HEADLINE (no digits): "{hl}"\n'
        f"FORBIDDEN priors: {prior_line}\n"
        + (f'SUPPORTING: "{sup}"\n' if sup else "")
        + (f'BODY: "{body_txt}"\n' if body_txt else "")
        + (f"{nodes}\n" if nodes else "")
        + (f'CTA: "{cta_label}"\n' if cta_label else "")
        + (f'TOPIC: "{topic_clean}"\n' if topic_clean else "")
        + "=== END ===\n"
    )
