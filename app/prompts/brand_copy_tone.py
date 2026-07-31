from __future__ import annotations

"""Shared creative-copy + visual locks from Jiraaf Brand Space + sample PDFs/PNGs."""

JIRAAF_NAVY = "#003975"
JIRAAF_ORANGE = "#FFA400"
JIRAAF_BG = "#E8F0F8"
JIRAAF_CARD = "#D8E8F0"
JIRAAF_GOLD = "#AE8235"

# Orange must be visibly present — at least ~2% of the overall image area
ORANGE_COVERAGE_LOCK = f"""
ORANGE COVERAGE LOCK (NON-NEGOTIABLE):
- Brand orange {JIRAAF_ORANGE} must cover AT LEAST ~2% of the overall image area.
- Orange is for ACCENTS ONLY — NEVER for headlines or subheadings.
- HEADLINES and SUBHEADINGS: ALWAYS dark navy {JIRAAF_NAVY} — never orange, never white.
- Required orange uses (pick 2+): divider lines, CTA button fill, bar charts, stat numbers/%, bullet dots, chip border accents, icon highlights.
- Orange must be clearly visible at thumbnail size — tiny hairlines alone do NOT count toward 2%.
- Never replace orange with gold-only or gray accents.
- COLOUR RULE SUMMARY: Navy = all headings/subheadings. Gray = body text. Orange = accents/stats/dividers only.
"""

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
    "CAROUSEL ONLY: Reserve bottom ~14% EMPTY ice-blue on EVERY carousel slide for the legal footer. "
    "Do NOT invent SEBI/registration text in the image — exact footer is Pillow-composited after "
    f"(same reliability as Brand Space logo) at readable size:\n{JIRAAF_SEBI_DISCLAIMER}"
)

NO_SEBI_STATIC_RULE = (
    "STATIC / INFOGRAPHIC: Do NOT reserve space for SEBI disclaimer. "
    "Do NOT bake any SEBI / registration / legal disclaimer text. "
    "No footer legal strip — use the full canvas for content."
)

# Locked icon DNA — ULTRA-PREMIUM HD 3D, TOPIC-SPECIFIC (not always bonds / FD)
PREMIUM_HD_ICON_LOCK = f"""
PREMIUM HD ICON LOCK (NON-NEGOTIABLE — Jiraaf sample quality bar):
- Render icons like a top-tier product studio: 4K/HD clarity, razor-sharp edges, zero blur, zero pixel mush.
- Style: premium soft-touch clay + satin plastic + brushed gold metal accents (Octane/Cinema4D product-render look).
- Lighting: professional 3-point studio (key top-left, soft fill, subtle rim light); rich contact shadows on ice-blue BG.
- Materials: visible micro-detail — beveled edges, subtle grain, clean specular highlights, depth-of-field on BG only (icon stays sharp).
- Palette: navy {JIRAAF_NAVY}, gold {JIRAAF_GOLD}, orange {JIRAAF_ORANGE} accents on icons only.
- FORBIDDEN: flat clipart, emoji-style icons, low-poly blocks, fuzzy blobs, plastic toy look, generic AI mush, neon chrome.
- Icons must look EXPENSIVE and CRISP even when small — like Apple/Figma premium 3D illustration packs.
"""

ICON_STYLE_LOCK = f"""
{PREMIUM_HD_ICON_LOCK}
ICON STYLE LOCK (NON-NEGOTIABLE — ULTRA-PREMIUM HD 3D, same quality family as Jiraaf samples):
- ULTRA-PREMIUM HD studio 3D icons: high-resolution, pixel-sharp, rich subsurface detail,
  soft-touch clay / satin materials with controlled specular highlights (premium product render).
- NOT low-poly. NOT flat clipart. NOT cheap toy blobs. NOT washed-out soft mush. NOT neon/chrome AI junk.
- NOT blurry, NOT out-of-focus, NOT low-res — icons must read crisp at 100% zoom.
- Soft keyed studio lighting (top-left key + gentle fill); deep soft contact shadows; clear depth.
- TOPIC LOCK: choose objects from the user's topic ONLY.
  Examples:
  * capital controls / policy -> gate, lock, shield, arrows, document, currency flow
  * trade deficit / imports-exports -> bars, containers, arrows, balance, table markers
  * bonds / fixed income -> bond certificate, coupon slip, wallet, chart, rupee coin
- Do NOT default to FD briefcase, handshake, bond certificate, or bank icons for unrelated topics.
- Palette: navy {JIRAAF_NAVY}, gold/amber {JIRAAF_GOLD}, orange {JIRAAF_ORANGE}, warm neutral accents.
- SIZE: static/infographic icons can be medium; CAROUSEL icons/avatars ~12–16% height —
  HD premium clay-3D illustrated objects (wallet, coins, doc, lock, shield) — not giant mushy heroes.
- Clean metaphors only — no clutter, no random mixed-topic objects.
- NEVER pure black / charcoal backgrounds behind icons — always ice-blue {JIRAAF_BG}.
"""

CAROUSEL_ICON_LOCK = f"""
{PREMIUM_HD_ICON_LOCK}
CAROUSEL ICON LOCK (NON-NEGOTIABLE — sample PDF avatar/icons):
- ONE premium HD clay-3D illustrated avatar-object per slide (~12–16% canvas height).
- Match sample style: soft-touch wallet, coin stack, bond document, lock+gate, shield, chart, phone.
- Maximum render quality: sharp edges, satin + gold accents, studio-lit, no blur.
- Place bottom-right or mid-right — text story cards own the left/center.
- Never soft blurry low-res clay mush. Never clipart. Never emoji. Never cheap calculator blobs.
- Never omit the icon. Never make it a giant full-width hero.
- If the icon looks cheap, blurry, or toy-like — the slide FAILS.
"""

HEADLINE_COLOR_LOCK = f"""
HEADLINE & TEXT COLOUR LOCK (NON-NEGOTIABLE):
- ALL headlines: dark navy {JIRAAF_NAVY} ONLY. Never orange. Never white on light BG.
- ALL subheadings / section titles: dark navy {JIRAAF_NAVY} ONLY.
- Body / supporting text: medium gray (#4A5568) or dark navy — never orange.
- NO orange underline / orange bar under the headline.
- Orange {JIRAAF_ORANGE} is ONLY for: thin dividers between cards, small bullet dots, bar/arrow accents in icons.
- Gold {JIRAAF_GOLD} is ONLY for: 3D icon metallic accents — never for any text.
- NEVER colour a headline, subheading, body paragraph, or ₹ amount orange (keep numbers navy).
"""

CAROUSEL_TEXT_FIT_LOCK = """
CAROUSEL TEXT FIT LOCK (NON-NEGOTIABLE — fixes broken/out-of-frame text):
1) Outer safe margin ≥8% on ALL sides. Text never touches crop edges.
2) Keep ALL content ABOVE the bottom SEBI zone (~14% empty). Nothing clipped by footer.
3) HEADLINE MUST BE COMPLETE — never truncate mid-word ("o.." / "…"). Wrap to 2 FULL lines instead.
4) Headline stays in LEFT ~75% of width — leave top-right logo pocket empty (do not cut words for logo).
5) No mid-word breaks. No awkward 1–2 word orphan lines. Prefer 2 balanced lines max per card.
6) Each explanation card: max ~14 words — wrap cleanly inside the card with padding ≥12px.
7) Never place text under/through icons. Never let icons overlap text.
8) Prefer 2–3 fully-visible story cards (sample DNA) — drop optional lines before clipping.
"""

CONTENT_DEPTH_LOCK = """
CONTENT DEPTH LOCK (NON-NEGOTIABLE — client quality bar):
Every slide / card / row must contain a REAL concrete insight — not a vague slogan.
FORBIDDEN shallow copy:
  - "Connect the dots" / "Invest wisely" / "Grow your wealth" / "Unlock potential"
  - Any line that could apply to any investment topic without a specific mechanism
  - One-word chips (Selling / Hedging / Pros / Cons) with NO explanation sentence
REQUIRED depth (pick ALL that fit):
  - A specific mechanism explained in plain English (how it works, step by step)
  - A real ₹ / % / USD number from research in a full sentence
  - A concrete "who benefits and when" statement
  - A myth-bust or caveat (penalty, condition, illustrative note)
CAROUSEL BODY: 22–36 words per slide — teach like Sweep-In samples (₹ scenario + mechanism).
Each content card = short label + one clear explanation (8–14 words), not a lone keyword.
NEVER ship a slide with only 1–2 vague lines and empty space — that is NOT sample DNA.
"""

UNIVERSAL_FIT_LOCK = f"""
UNIVERSAL FIT LOCK (NON-NEGOTIABLE — ALL formats + ALL platforms):
Applies to static / carousel / infographic on LinkedIn / Instagram / X (Twitter).
Whatever the content length, EVERYTHING must fit INSIDE the canvas with ZERO clipping.

CANVAS BOUNDARY — ABSOLUTE RULE:
Every single pixel of every element (text, icon, chip, bar, card, CTA, source line, divider)
MUST be 100% inside the canvas rectangle. Nothing may bleed, overflow, or be cropped at any edge.
If content does not fit at normal size, reduce font size or drop optional elements — NEVER clip.

HARD RULES:
1) Outer margins >=6% on ALL sides (top/right/bottom/left). Nothing touches or crosses the crop edge.
2) NO overlapping: text never overlaps icons, icons never overlap text, rows never collide, chips never collide.
3) NO cut-off: headlines, supporting lines, row facts, chip labels, CTA buttons, source lines — fully visible.
4) Prefer LESS content that fits over MORE content that breaks. Drop optional body/CTA before clipping.
5) Keep baked strings SHORT: headline <=10 words, supporting <=14, fact lines <=8 words, chip labels = 1 word.
6) CTA button (if any): COMPACT only — max ~22–28% canvas width, ~3.5–4.5% canvas height,
   short label (2–3 words), modest padding. Never a wide bar or oversized pill.
   Fully inside frame with >=8% empty space below (or omit CTA if crowded).
7) Tables/rankings: equal row heights, full-width dividers, consistent columns; no broken half-lines.
8) Icons: sized to leave clear breathing room around nearby text; never crush labels.
9) Spelling perfect — never invent broken words (technology not tecnlogy; real estate not restate).
10) Background is one continuous field edge-to-edge — no second BG color, no white side panels.
11) Scale down all elements proportionally before allowing any element to touch an edge.
"""

CAROUSEL_FIT_LOCK = f"""
{UNIVERSAL_FIT_LOCK}
{CAROUSEL_TEXT_FIT_LOCK}
{CAROUSEL_ICON_LOCK}
CAROUSEL FIT LOCK — MATCH SAMPLE PDFs (Sweep-In / Capital / Gains):
- FULL-BLEED ice-blue {JIRAAF_BG}. NO white side panels. NO second BG.
- STYLE: premium white rounded cards with soft shadow + generous padding (Sweep-In / Gains DNA) —
  NOT sparse empty slides, NOT quadrant grids, NOT thin orange divider stacks.
- STORY FIRST: every slide teaches one beat of the arc with ₹/%/rules — not a slogan + icon.
- ICONS/AVATARS: ONE premium HD clay-3D object (~12–16% height) bottom-right — crisp, not mushy.
- FORBIDDEN: truncated headlines ("o.."), missing headlines, topic title alone, empty Pros/Cons,
  sparse 1–2 line slides with huge empty space.
- MANDATORY: UNIQUE COMPLETE navy headline at top-left on EVERY slide (wrap 2 lines if needed).
- NEVER reuse topic name alone ("Capital Controls", "Sweep-in FD") as headline.
- Headlines/subheads: navy {JIRAAF_NAVY} ONLY. No orange underlines under titles.
{HEADLINE_COLOR_LOCK}
{ORANGE_COVERAGE_LOCK}
- REQUIRED: 2–3 white story cards/blocks with full short explanations (sample page density).
- Bottom ~14% EMPTY for SEBI. Nothing clipped. Margins ≥8%.
- Top-right corner: plain empty ice-blue only — NO AI logo, NO "Brand Logo" text, NO dashed box.
- Spelling perfect. Plain printed sans-serif.
"""

# Infographic / static data posts — retail audience tone (client feedback Jul 2026)
INFOGRAPHIC_AUDIENCE_TONE_LOCK = f"""
RANKING TONE LOCK — match sample_top_countries_investing.png EXACTLY:
Target = everyday Indian investor. Language must be THIS simple:

GOOD phrases (copy this style):
  "Top investor in India"
  "Strong economic ties"
  "Growing interest"
  "Diverse sectors"
  "Strategic partnerships"

BAD (never):
  textbook essays, Vostro/hedge/sector-exposure jargon, ESD/HAE/ASA typos,
  mid-word cuts, paragraph CTAs like "Explore Investment Opportunities"

COPY SHAPE:
- Headline: plain claim ("Top 6 Countries Investing in India")
- Supporting: one soft line ("A strong signal from global investors.")
- Each row: ONE phrase ≤5 words under the country name
- Amount: ₹50B style (or % / USD letters when source requires)
- CTA: "Explore more" (2–3 words) — NEVER a long button sentence
"""

# Shared DNA for STATIC + INFOGRAPHIC ranking — locked to saved sample PNG
RANKING_SAMPLE_DNA_LOCK = f"""
════════════════════════════════════════════════════════
RANKING SAMPLE DNA — STATIC + INFOGRAPHIC (SAME EVERY TIME)
Reference: app/prompts/references/jiraaf_samples/sample_top_countries_investing.png
════════════════════════════════════════════════════════

COLOURS:
- BG ice-blue {JIRAAF_BG}
- Navy text {JIRAAF_NAVY}
- Orange {JIRAAF_ORANGE}: rank squares, accent line under subtitle, coin/chart icons, CTA
{ORANGE_COVERAGE_LOCK}
{HEADLINE_COLOR_LOCK}

LAYOUT (exact columns left→right on EVERY row):
1) Orange rounded square with white rank number
2) Rounded real country flag (matched — UAE not HAE, USA not ASA, never India flag for UAE)
3) Country NAME bold + ONE short grey phrase under it
4) Amount bold (₹50B / ₹45B …) 
5) Tiny gold coin + rising orange bars icon

Header: centered navy headline + soft supporting + short centered orange accent line
Footer: compact orange CTA ("Explore more")
Thin light dividers between rows. No dark BG. No $ / US $ signs.

CURRENCY: ₹ for India FDI ranks · % for inflation · ¥ Japan · USD letters only if source USD
{INFOGRAPHIC_AUDIENCE_TONE_LOCK}
"""

# Compact stub for any remaining AI image path
RANKING_IMAGE_STUB = f"""
RANKING = sample_top_countries_investing.png DNA:
BG {JIRAAF_BG}. Navy {JIRAAF_NAVY}. Orange badges+accent+CTA+coin icons {JIRAAF_ORANGE}.
Row: orange # square | real flag | NAME + ≤5-word phrase | ₹50B | coin/chart icon.
Tone: "Top investor in India" / "Strong economic ties" — never textbook. CTA "Explore more".
Never HAE/ASA/$/US $/wrong flags. Same for static AND infographic.
"""

INFOGRAPHIC_RANKING_FORMAT_LOCK = RANKING_SAMPLE_DNA_LOCK

INFOGRAPHIC_TRADE_BOARD_LOCK = f"""
TRADE DEFICIT BOARD LOCK (simple for retail audience — match India–Russia sample):
- Punchy plain headline + one short subtitle (no "implications / exposure / hedge" jargon)
- Clean dual-bar year table ONLY: EXPORT (orange) | TRADE BALANCE | IMPORT (navy), Billion USD
- Year labels correct (2020-21, 2021-22, 2022-23, 2023-24…) — never "2021-2023"
- Bake exact strings: "Export: USD X.XB" / "Import: USD Y.YB" — NEVER ESD / Emp / Impp / $
- Orange accents required on export bars + dividers
- Bottom box: "What India buys most from Russia" — 3–4 simple category + USD lines
- Source: Ministry of Commerce (or research domain)
- FORBIDDEN technical sidebars: Key Drivers, Sector Exposure, Currency Risk, Vostro/Bistro,
  Investment Considerations, Questions for Advisors, FD briefcase, handshake as main story
- Optional CTA: COMPACT 2–4 words only — never a paragraph-length button
"""

SIMPLIFIED_CREATIVE_TONE_RULES = f"""
JIRAAF SAMPLE SYSTEM LOCK (NON-NEGOTIABLE)

Match PDF/PNG samples in app/prompts/references/jiraaf_samples/.
Educate-first, short human lines — NEVER textbook paragraphs, NEVER empty teaser ads.
{INFOGRAPHIC_AUDIENCE_TONE_LOCK}

════════════════════════════════════════
LAYOUT ROUTER (follow layout_type)
════════════════════════════════════════
- carousel_story: education story OR single education poster
  Examples: why bonds / predictable income / liquidity / FIRE / myths / checklists
  → BENEFIT/REASON cards — NEVER invent country comparison tables unless user asked
- static_hub_facts: hub + 4–5 short fact cards (bank penalties / key rules) — REAL ₹/% facts
- static_ranking: ranked rows OR trade-deficit data boards
  → FDI/country ranks: Name | short plain phrase | amount
  → Trade deficit (India–Russia sample): year rows Export|Balance|Import dual bars
    + "What India buys most" categories — NEVER bond/FD benefit cards / technical sidebars

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
GOOD: "Top 6 Countries Investing in India" + ranked flag rows + plain phrases + amounts

════════════════════════════════════════
CONTENT DEPTH
════════════════════════════════════════
{CONTENT_DEPTH_LOCK}

════════════════════════════════════════
BRAND COLOURS + ICONS + FIT
════════════════════════════════════════
- Navy {JIRAAF_NAVY} + REQUIRED orange accents {JIRAAF_ORANGE} every creative
{HEADLINE_COLOR_LOCK}
{ORANGE_COVERAGE_LOCK}
- BG ice-blue {JIRAAF_BG}; cream/soft cards OK
- Icons: ULTRA-PREMIUM clay-3D / soft-touch studio renders (high detail, subtle gloss, strong shadows)
  — never flat clipart, never cheap low-poly, never washed-out blobs
{ICON_STYLE_LOCK}
- Content must FIT: no cut-off headlines, no overcrowding, no empty shells, no "..." truncation
{UNIVERSAL_FIT_LOCK}
- SEBI disclaimer: CAROUSEL slides only (Pillow composite). Static/infographic: NO SEBI footer.
{CAROUSEL_FIT_LOCK}

════════════════════════════════════════
CURRENCY + ACCURACY
════════════════════════════════════════
- India default: ₹ for retail/FD/banks; % for rates
- ¥ only for Japan investment commits
- USD only when source data is USD (label "USD")
- Real banks/countries only; matched flags; totals must add up
- Never invent ASA (use USA); never wrong UK↔Germany flags; never HAE (use UAE)
- Perfect English spelling on every baked word (investment not investmet; growth not grewth)

HARD CAPS:
- headline ≤10 words | supporting ≤14 | body often empty for data posts
- section_label = name | includes = 1–2 short facts | body empty
- carousel slide body 22–36 words (teach like Sweep-In samples; still scannable)
- CTA ≤4 words; compact button only
"""

BRAND_COLOR_LOCK_RULE = f"""
\n\nBRAND COLOUR + ICON QUALITY LOCK:
- Navy {JIRAAF_NAVY}; REQUIRED orange accents {JIRAAF_ORANGE} (dashes, dividers, CTA arrows, bullets).
{HEADLINE_COLOR_LOCK}
{ORANGE_COVERAGE_LOCK}
- BG {JIRAAF_BG}. No purple/neon AI look. NEVER pure black / charcoal backgrounds.
- ULTRA-PREMIUM clay-3D icons (high detail, studio light, subtle gloss) — never flat/cheap/low-poly.
{ICON_STYLE_LOCK}
- All requested content must fit fully — never truncate with "...".
{UNIVERSAL_FIT_LOCK}
- {NO_SEBI_STATIC_RULE}
"""

# SHORT locks for IMAGE API only (gpt-image-1 hard ~6000 char budget).
# NEVER paste mega-locks (CAROUSEL_FIT_LOCK / BRAND_COLOR_LOCK_RULE) into image prompts —
# they alone exceed 6000 chars and wipe the slide headline/body.
CAROUSEL_IMAGE_STYLE_STUB = f"""
CAROUSEL STYLE (match Sweep-In / Capital / Gains samples):
- Canvas portrait ice-blue BG {JIRAAF_BG} full-bleed.
- Headlines navy {JIRAAF_NAVY} ONLY, COMPLETE words (never mid-word cut like "o..").
- Orange {JIRAAF_ORANGE} accents only (dividers/stats). Body gray.
- Layout: FULL headline top-left + 2–3 white story cards with ₹/% facts + ONE premium HD clay-3D
  avatar icon (~12–16% height) bottom-right (wallet/coins/doc/lock/shield).
- CTA button (if any): COMPACT — ≤28% canvas width, ≤4.5% height, 2–3 words — NEVER a wide orange bar.
- Bottom ~14% EMPTY for SEBI footer (composited later). Margins ≥8%. Nothing clipped.
- Top-right: plain empty ice-blue — NO logo, NO JIRAAF text, NO "Brand Logo" box.
- Story density like samples — NOT sparse empty slides. Perfect spelling. Plain sans-serif.
"""

CAROUSEL_IMAGE_EXTRA_LOCKS = f"""
BRAND/LOGO BAN: never draw JIRAAF wordmark, giraffe, "Brand Logo", dashed logo box, watermark.
SEBI: leave bottom ~14% empty ice-blue — do NOT bake legal footer text.
INDIA: prefer ₹/%; never £. Real numbers only. Never invent extra sentences.
SPELLING: bake ONLY quoted strings letter-perfect. Never truncate headline with "…" or "o..".
ICON: one HD clay-3D object only — sharp, studio-lit — not blurry toy.
CTA: compact orange pill only (≤28% width, ≤4.5% height) — never oversized wide bar.
"""

STATIC_IMAGE_EXTRA_LOCKS = f"""
BRAND/LOGO BAN: never draw brand wordmark / watermark / "Brand Logo" placeholder.
{NO_SEBI_STATIC_RULE}
INDIA: ₹/% retail · ¥ Japan · USD letters if source USD — NEVER $ / US $ / ESD / £.
Navy {JIRAAF_NAVY} headlines; orange {JIRAAF_ORANGE} MUST show (~2%+); BG {JIRAAF_BG}.
Flags match countries (no ASA/HAE invents). Totals add up.
TONE: short retail hooks — no Vostro/hedge/sector-exposure jargon side panels.
CTA: compact ≤28% width, ≤4 words — never a wide paragraph button.
NO mid-word text breaks. No garbled labels.
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
