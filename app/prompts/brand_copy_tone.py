from __future__ import annotations

"""Shared creative-copy + visual locks from Jiraaf Brand Space + sample PDFs/PNGs."""

JIRAAF_NAVY = "#003975"
JIRAAF_ORANGE = "#FFA400"
JIRAAF_BG = "#E8F0F8"
JIRAAF_CARD = "#D8E8F0"
JIRAAF_GOLD = "#AE8235"

# Exact legal footer — Pillow-composited on CAROUSEL slides only (not static / infographic)
JIRAAF_SEBI_DISCLAIMER = (
    "Jiraaf Platform Private Limited; SEBI Registration Number (Stock Broker): INZ000315538. "
    "Disclaimer: Fixed returns do not constitute guaranteed or assured returns. "
    "Investments in corporate debt securities, municipal debt securities/securitized debt "
    "instruments are subject to credit risks, market risks and default risks including delay "
    "and/or default in payment. Read all the offer related documents carefully."
)

# Carousel-only — never inject into static/infographic prompts
SEBI_FOOTER_HINT = (
    "CAROUSEL ONLY: Reserve bottom ~22% EMPTY ice-blue on EVERY carousel slide for the legal footer. "
    "Do NOT invent SEBI/registration text in the image — exact footer is Pillow-composited after "
    f"(same reliability as Brand Space logo) at readable size:\n{JIRAAF_SEBI_DISCLAIMER}"
)

NO_SEBI_STATIC_RULE = (
    "STATIC / INFOGRAPHIC: Do NOT reserve space for SEBI disclaimer. "
    "Do NOT bake any SEBI / registration / legal disclaimer text. "
    "No footer legal strip — use the full canvas for content."
)

# Locked icon DNA — ULTRA-PREMIUM clay-3D (Jiraaf sample quality: briefcase / flag / handshake)
ICON_STYLE_LOCK = f"""
ICON STYLE LOCK (NON-NEGOTIABLE — ULTRA-PREMIUM 3D, same family as Jiraaf samples):
- ULTRA-PREMIUM studio 3D icons: high-resolution, crisp edges, rich subsurface detail,
  soft-touch clay / satin materials with subtle specular highlights (premium product render).
- NOT low-poly. NOT flat clipart. NOT cheap toy blobs. NOT washed-out matte. NOT neon/chrome AI junk.
- Soft keyed studio lighting (top-left key + gentle fill); deep soft contact shadows; clear depth.
- Reference DNA: navy briefcase with gold hardware/"FD", red desk flag on gold stand, soft handshake
  (navy sleeve + white cuff) — same materials, same lighting family on EVERY icon.
- Palette: navy {JIRAAF_NAVY}, gold/amber {JIRAAF_GOLD}, orange {JIRAAF_ORANGE}, warm tan hands, red for alerts.
- Heroes LARGE and dominant (~28–34% canvas height). Chip icons crisp and readable.
- Clean metaphors (briefcase, handshake, flag, bank, coin, shield, chart) — no clutter.
- NEVER pure black / charcoal backgrounds behind icons — always ice-blue {JIRAAF_BG}.
"""

CAROUSEL_FIT_LOCK = f"""
CAROUSEL FIT LOCK — LOCKED STANDARD (same every slide, every topic):
- FULL-BLEED background: solid ice-blue {JIRAAF_BG} EDGE TO EDGE. NO white side panels.
  NO second background color. NO framed white card for the whole slide.
- MUST include: headline + supporting line + 3D hero cluster + orange divider + 3 bottom chips.
  Never headline-only. Never empty white space where body/supporting should be.
- Headline: MEDIUM, max 2 lines, ≤10 words — never cut mid-word. UNIQUE per slide.
- Supporting: REQUIRED one complete short sentence under the headline (deeper insight, not a slogan).
- Typography must look like clean printed sans-serif text, NOT embossed chrome, NOT neon glow,
  NOT outlined sticker text, NOT handwritten. Use normal readable sentence case.
- Hero icons: LARGE (~26–30% height), equal-size ULTRA-PREMIUM clay-3D objects, UNIQUE per slide.
{ICON_STYLE_LOCK}
- Bottom chips: three equal white rounded chips — premium 3D icon + ONE complete WORD each
  (e.g. Coupons | Principal | Maturity). NEVER multi-word phrases that truncate to Steady/Plan/Less.
  Chip band sits at ~60–74% height — FULL labels visible ABOVE the legal footer.
  Bottom ~22% EMPTY for SEBI composite. Never let chips touch or enter the footer zone.
  NEVER reuse capital-control / FDI sample chips unless those words are in approved copy.
- Side margins ≥5%. No clipped letters. No oversized heroes eating the supporting line.
- NEVER pure black / charcoal backgrounds — always solid ice-blue {JIRAAF_BG}.
"""

SIMPLIFIED_CREATIVE_TONE_RULES = f"""
JIRAAF SAMPLE SYSTEM LOCK (NON-NEGOTIABLE)

Match PDF/PNG samples in app/prompts/references/jiraaf_samples/.
Educate-first, short human lines — NEVER textbook paragraphs, NEVER empty teaser ads.

════════════════════════════════════════
LAYOUT ROUTER (follow layout_type)
════════════════════════════════════════
- carousel_story: education story OR single education poster
  Examples: why bonds / predictable income / liquidity / FIRE / myths / checklists
  → BENEFIT/REASON cards — NEVER invent country comparison tables unless user asked
- static_hub_facts: hub + 4–5 short fact cards (bank penalties / key rules) — REAL ₹/% facts
- static_ranking: ranked rows OR trade-deficit data boards
  → FDI/country ranks: Name | % | amount
  → Trade deficit (India–Russia sample): year rows Export|Balance|Import dual bars
    + "What India buys most" categories — NEVER bond/FD benefit cards

════════════════════════════════════════
DATA POST vs TEASER vs EDUCATION
════════════════════════════════════════
If user asks WHY / useful / benefits / explain / predictable income:
→ Education poster with reason cards. FORBIDDEN: invent India vs USA vs Germany yield boards.

If user asks rates / rules / top-N / comparison / FDI / inflation / bank penalties:
→ Put ACTUAL facts in sections/slides. NO curiosity-only teasers. NO fake testimonials replacing data.

BAD: "What Are Your FD Penalty Rates?" + "Learn more" + fake quote
BAD: "Why bonds for income?" + India/USA/Germany/Japan comparison nobody asked for
GOOD: "Bonds: Path to Predictable Income" + 4 benefit cards (income, capital, wealth, liquidity)
GOOD: "Bank's Penalty Rates and Key Rules" + 5 bank cards with ₹/% rules

════════════════════════════════════════
BRAND COLOURS + ICONS + FIT
════════════════════════════════════════
- Navy {JIRAAF_NAVY} + REQUIRED orange accents {JIRAAF_ORANGE} every creative
- BG ice-blue {JIRAAF_BG}; cream/soft cards OK
- Icons: ULTRA-PREMIUM clay-3D / soft-touch studio renders (high detail, subtle gloss, strong shadows)
  — never flat clipart, never cheap low-poly, never washed-out blobs
{ICON_STYLE_LOCK}
- Content must FIT: no cut-off headlines, no overcrowding, no empty shells, no "..." truncation
- SEBI disclaimer: CAROUSEL slides only (Pillow composite). Static/infographic: NO SEBI footer.
{CAROUSEL_FIT_LOCK}

════════════════════════════════════════
CURRENCY + ACCURACY
════════════════════════════════════════
- India default: ₹ for retail/FD/banks; % for rates
- ¥ only for Japan investment commits
- USD only when source data is USD (label "USD")
- Real banks/countries only; matched flags; totals must add up
- Never invent ASA (use USA); never wrong UK↔Germany flags
- Perfect English spelling on every baked word (investment not investmet; growth not grewth)

HARD CAPS:
- headline ≤10 words | supporting ≤14 | body often empty for data posts
- section_label = name | includes = 1–2 short facts | body empty
- carousel slide body ≤22 words
"""

BRAND_COLOR_LOCK_RULE = f"""
\n\nBRAND COLOUR + ICON QUALITY LOCK:
- Navy {JIRAAF_NAVY}; REQUIRED orange accents {JIRAAF_ORANGE} (dashes, dividers, CTA arrows, bullets).
- BG {JIRAAF_BG}. No purple/neon AI look. NEVER pure black / charcoal backgrounds.
- ULTRA-PREMIUM clay-3D icons (high detail, studio light, subtle gloss) — never flat/cheap/low-poly.
{ICON_STYLE_LOCK}
- All requested content must fit fully — never truncate with "...".
- {NO_SEBI_STATIC_RULE}
"""

CAROUSEL_SEBI_LOCK_RULE = f"""
\n\n{SEBI_FOOTER_HINT}
"""

INDIA_MARKET_LOCK_RULE = """
\n\nINDIA MARKET + DATA ACCURACY LOCK:
- Prefer ₹/%; ¥ for Japan commits; USD only when source is USD (label USD).
- Real bank/country names; correct flags; totals must match rows.
- For top-5 banks / penalty rates: show ALL 5 banks with concrete ₹/% rules — never a teaser.
- When stats/rates are shown, include Source: domain.com footer from verified research URLs.
"""

BANK_PENALTY_SAMPLE_RULES = """
\n\nBANK PENALTY / HUB LOCK:
Layout = static_hub_facts. Headline like "Bank's Penalty Rates and Key Rules".
sections: EXACTLY 5 — use these EXACT labels only:
  Axis Bank | SBI | HDFC Bank | ICICI Bank | PNB
NEVER invent or misspell banks (forbidden: OBI, HAFT, ACINI, PUB, ASA, fake banks).
Say "FDs" not "Ads". Each section: 1–2 short ₹/% premature-withdrawal lines.
body="", customer_quote="". NO teaser questions without rates.
"""

SOURCE_FOOTER_RULE = """
\n\nSOURCE FOOTER LOCK:
If verified research sources exist, bake a compact footer line:
Source: domain1.com · domain2.com
Do not invent sources. Prefer official/public domains.
"""
