from __future__ import annotations

"""Exact carousel layout grid locked to Jiraaf sample canvas (1080×1350).

Derived from Sweep-In FD / Capital Controls / Unrealized Gains sample DNA:
- 4:5 portrait LinkedIn/IG carousel
- Top-left headline, mid white cards, bottom-right icon, bottom SEBI strip
- Outer margins ~8%, logo pocket top-right, SEBI ~24% bottom

All values are ratios of canvas so they scale if export size differs.
"""

from dataclasses import dataclass


# Canonical sample canvas
CAROUSEL_W = 1080
CAROUSEL_H = 1350

# Brand colours (RGB)
NAVY = (0, 57, 117)  # #003975
BODY_GRAY = (74, 85, 104)  # #4A5568
ORANGE = (255, 164, 0)  # #FFA400
ICE_BLUE = (232, 240, 248)  # #E8F0F8
CARD_WHITE = (255, 255, 255)
CARD_SHADOW = (200, 214, 228)


@dataclass(frozen=True)
class CarouselLayout:
    """Pixel boxes for one canvas size."""

    width: int
    height: int
    margin_x: int
    margin_top: int
    logo_left: int
    logo_bottom: int
    headline_box: tuple[int, int, int, int]  # x0,y0,x1,y1
    supporting_box: tuple[int, int, int, int]
    cards_box: tuple[int, int, int, int]
    icon_box: tuple[int, int, int, int]
    sebi_top: int
    content_wipe: tuple[int, int, int, int]  # wipe AI text, keep icon


def resolve_carousel_layout(width: int = CAROUSEL_W, height: int = CAROUSEL_H) -> CarouselLayout:
    """Compute locked zones for a carousel canvas.

    Sample geometry (1080×1350 reference):
    - Outer margin X: 8% (~86px)
    - Top content start: 7% (~95px) — below logo band
    - Logo pocket: right 14% × top 9%
    - Headline: left content to 78% width, max 2 lines
    - Supporting: under headline
    - Cards column: left 8% → 58% width (leaves icon column)
    - Icon: right 55%→94% × mid 48%→74% (above SEBI)
    - SEBI: bottom 24% empty then Pillow text
    """
    w = max(int(width), 1)
    h = max(int(height), 1)

    mx = int(w * 0.08)
    mt = int(h * 0.07)
    logo_left = int(w * 0.86)
    logo_bottom = int(h * 0.09)
    sebi_top = int(h * 0.76)  # bottom 24%

    # Headline sits under top margin, left of logo pocket
    hl_x0 = mx
    hl_y0 = mt
    hl_x1 = min(int(w * 0.78), logo_left - int(w * 0.02))
    hl_y1 = int(h * 0.20)

    # Supporting under headline
    sup_x0 = mx
    sup_y0 = hl_y1 + int(h * 0.008)
    sup_x1 = hl_x1
    sup_y1 = int(h * 0.28)

    # Cards: left column only — never enter icon or SEBI
    cards_x0 = mx
    cards_y0 = max(sup_y1 + int(h * 0.012), int(h * 0.28))
    cards_x1 = int(w * 0.58)
    cards_y1 = int(h * 0.72)

    # Icon pocket bottom-right above SEBI
    icon_x0 = int(w * 0.55)
    icon_y0 = int(h * 0.48)
    icon_x1 = int(w * 0.94)
    icon_y1 = sebi_top - int(h * 0.02)

    # Wipe AI-baked text in headline+cards; keep icon column
    wipe_x0 = int(w * 0.04)
    wipe_y0 = int(h * 0.05)
    wipe_x1 = int(w * 0.60)
    wipe_y1 = sebi_top - int(h * 0.01)

    return CarouselLayout(
        width=w,
        height=h,
        margin_x=mx,
        margin_top=mt,
        logo_left=logo_left,
        logo_bottom=logo_bottom,
        headline_box=(hl_x0, hl_y0, hl_x1, hl_y1),
        supporting_box=(sup_x0, sup_y0, sup_x1, sup_y1),
        cards_box=(cards_x0, cards_y0, cards_x1, cards_y1),
        icon_box=(icon_x0, icon_y0, icon_x1, icon_y1),
        sebi_top=sebi_top,
        content_wipe=(wipe_x0, wipe_y0, wipe_x1, wipe_y1),
    )


def layout_prompt_lock(width: int = CAROUSEL_W, height: int = CAROUSEL_H) -> str:
    """Short lock for image prompts — exact % zones matching resolve_carousel_layout."""
    return (
        f"CANVAS LOCK {width}x{height}. "
        f"Margins 8% all sides. "
        f"TOP-RIGHT 14%x9%: empty (logo later). "
        f"HEADLINE zone: top-left, y 7–20%, width to 78% — COMPLETE navy text. "
        f"SUPPORTING: y 20–28%. "
        f"CARDS: left column x 8–58%, y 28–72% — 2 white cards, COMPLETE sentences. "
        f"ICON ONLY: right pocket x 55–94%, y 48–74% — ONE premium clay-3D object. "
        f"BOTTOM 24% (y 76–100%): EMPTY ice-blue for SEBI — no buttons, no text, no icons. "
        f"If CTA button appears ABOVE SEBI: COMPACT only — width ≤28% canvas, height ≤4.5% canvas, "
        f"2–3 word label, small padding — NEVER a wide orange bar. "
        f"Never clip. Never mid-word cut."
    )
