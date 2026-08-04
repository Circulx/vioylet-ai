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
- NO orange underline directly under the main headline title.
- Orange {JIRAAF_ORANGE} is REQUIRED for infographic explain accents:
  left vertical section bars, section dividers, CTA button fill, bullet dots, callout box border.
- Orange {JIRAAF_ORANGE} is also for: thin dividers between cards, bar/arrow accents in charts.
- Gold {JIRAAF_GOLD} is ONLY for: subtle 3D icon metallic highlights — NEVER replace orange accents.
- NEVER use tan/brown/amber as a substitute for brand orange {JIRAAF_ORANGE}.
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

# Carousel education — same retail tone as static/infographic ranking (NOT policy-analyst speak)
CAROUSEL_AUDIENCE_TONE_LOCK = """
CAROUSEL TONE LOCK — same voice as static/infographic samples (NON-NEGOTIABLE):
Target = everyday Indian investor on LinkedIn/Instagram — NOT a policy analyst or textbook.

WRITE LIKE THIS (plain, short, human):
  "What if your savings earned FD-like returns?"
  "Let's say you keep ₹2 lakh in your account"
  "Only ₹50,000 is needed for daily expenses"
  "The rest sits idle at low savings interest"
  "Would you try a sweep-in FD?"

NEVER WRITE LIKE THIS (too technical — client rejected):
  Vostro/Nostro, liquidity risk, sector exposure, currency hedge, macro implications,
  regulatory framework, capital account convertibility, LRS without plain English,
  "implications for portfolio allocation", advisor-briefing essays, empty Pros/Cons chips

COPY RULES (every slide):
- Headline: simple question or claim — max 8–10 words, complete (no mid-word cuts)
- supporting_line: ONE short plain sentence with a ₹/% fact or "what it means"
- body + proof_points: teach with a mini ₹ scenario — words a retail investor gets in 3 seconds
- Each story card: bold label + ONE explanation ≤12 plain English words
- CTA: short invite ("Comment below!" / "What would you do?") — never a paragraph button
- India: ₹ and % default; USD only when source is USD (label "USD" — never $ / US $)
- Perfect spelling. No jargon dumps. Depth = real numbers in simple language.
"""

CAROUSEL_CONTENT_DEPTH_LOCK = """
CAROUSEL CONTENT DEPTH (plain language — still teach, never textbook):
- Every slide needs a REAL insight with ₹ / % / a simple rule — not a vague slogan.
- FORBIDDEN shallow: "Invest wisely" / "Unlock potential" / "Connect the dots"
- FORBIDDEN technical: one-word chips (Selling / Hedging / Pros) with NO explanation
- REQUIRED: mini scenario OR comparison OR honest trade-off — in words anyone understands
- body: 18–32 words per slide — shorter sentences, same teaching depth as Sweep-In samples
- Each card = label + one clear line (6–12 words) with ₹/% — NOT a jargon paragraph
- Include ONE honest caveat somewhere (penalty, condition, illustrative note) in plain English
"""

# Infographic EXPLAIN — PERMANENT DNA from sample_infographic_explain_rbi_polymer.png
# User provided this sample once — DO NOT drift; DO NOT ask for the sample again.
INFOGRAPHIC_EXPLAIN_LAYOUT_LOCK = f"""
════════════════════════════════════════════════════════
INFOGRAPHIC EXPLAIN — PERMANENT SAMPLE LOCK (NON-NEGOTIABLE)
File: app/prompts/references/jiraaf_samples/sample_infographic_explain_rbi_polymer.png
Topic example in sample: "Why is the RBI testing plastic currency notes?"
EVERY explain/why/how infographic MUST match this anatomy. Never invent a sparse poster.
════════════════════════════════════════════════════════

CANVAS: 1080x1350 portrait. Soft off-white / pale gray BG (NOT flat ice poster with huge empty space).

1) HEADER
   - EMPTY top-right pocket for Brand Space logo composite — NEVER draw JIRAAF wordmark/giraffe
   - LARGE bold navy headline (question OK) — full width under logo pocket
   - 1–2 line gray intro paragraph with a concrete fact (e.g. trial size / ₹ denominations)

2) SECTION A — orange vertical bar + UNIQUE navy heading (sample: "Why polymer notes?")
   - Thin light divider under section
   - 3-COLUMN row: navy circular icon (white line-art) + UNIQUE bold mini-title + 1–2 line gray body
   - Bold key numbers in body (₹4,000–5,000 crore / 2.5–4x / 60+ countries style)
   - Mini-titles MUST be unique (Lower replacement costs | Longer lifespan | Globally tested)

3) SECTION B — orange vertical bar + UNIQUE navy heading (sample: "Why the RBI is starting with a trial")
   - Short intro line; highlight 1–2 words in ORANGE {JIRAAF_ORANGE} (sample: "cautious before")
   - 3-COLUMN row: premium clay-3D icons + UNIQUE mini-title + explanation
   - Sample icon types: shipping container | ATM | wallet — topic-matched for new topics

4) SECTION C — orange vertical bar + UNIQUE navy heading (sample: "Only ₹10 and ₹20… Why?")
   - 1–2 short paragraphs (text block — no mini-grid here)
   - Bold key phrases (fastest-wearing / wider adoption)

5) CALLOUT BOX — rounded rect, thin ORANGE border
   - Orange circle + white lightbulb on left
   - 2–3 sentence navy insight (customer_quote) with bold key phrases

6) FOOTER
   - "Source: …" small italic gray (when research available)
   - NO AI-drawn SEBI legal strip on static/infographic (carousel only)

ORANGE {JIRAAF_ORANGE} REQUIRED:
- Left bars on EVERY section heading
- Highlight words like "cautious before" in body
- Callout border + lightbulb circle
{ORANGE_COVERAGE_LOCK}

COPY (L7/L7c):
- 2–4 UNIQUE section_labels; includes[] = "Mini-title | explanation with ₹/%"
- All mini-titles unique; customer_quote = callout; source_footer when available
- CTA topic-safe only ("Learn more") — never bond CTA on currency/RBI topics

FORBIDDEN:
- Sparse 3-block poster with giant icons and empty space
- Duplicate headings or duplicate mini-titles
- Typos; bond cards on unrelated topics; ranking/trade boards unless asked
"""

INFOGRAPHIC_EXPLAIN_SPELLING_LOCK = """
INFOGRAPHIC EXPLAIN SPELLING LOCK (FAIL on any typo):
- Perfect English: Financial not Financrial; Less not Leśs; international not internationa!l; flexible not fiexible
- RBI not OBI; India's not Indid's; counterfeit not counterfiet; polymer not polmer
- No stray accents, punctuation inside words, or mid-word breaks
- Bake ONLY quoted blueprint strings letter-perfect
- UNIQUE section headings AND unique mini-titles — rewrite if anything would duplicate
"""

# Static EXPLAIN — simple hero + heading cards (NOT infographic editorial)
STATIC_EXPLAIN_LAYOUT_LOCK = f"""
STATIC EXPLAIN LOCK (simple poster — NOT infographic editorial):
- Bold navy headline + one supporting line
- ONE premium clay-3D hero icon (topic-matched) — NOT country flags
- 3–5 white rounded cards: short HEADING + 1–2 line EXPLANATION
- REQUIRED orange {JIRAAF_ORANGE}: section dividers, CTA button fill, bullet dots (≥2% image area)
- Topic-specific copy ONLY — never paste bond examples on unrelated topics
{ORANGE_COVERAGE_LOCK}
"""

# Visual quality — dense sample-matched infographic explain
INFOGRAPHIC_EXPLAIN_QUALITY_LOCK = f"""
INFOGRAPHIC EXPLAIN QUALITY LOCK (FAIL if sparse poster / duplicates / typos):
{INFOGRAPHIC_EXPLAIN_SPELLING_LOCK}
- MUST look like sample_infographic_explain_rbi_polymer.png: dense editorial, LARGE headline, filled sections.
- FAIL if huge empty background with only 3 short lines — that is a poster, not this infographic.
- EACH fact-grid section: orange left bar + navy heading + 3 columns with:
  1) Icon (navy circular OR premium clay-3D — topic-matched, sharp HD)
  2) UNIQUE bold mini-title (navy, 2–5 words) — never repeat titles
  3) Explanation with ₹/%/number (gray, 8–18 words) — never empty under title
- Callout box: lightbulb + full multi-sentence quote baked in.
- Source footer when provided.
- Orange highlight words in at least one body/intro line + orange bars + orange callout border.
- BG soft {JIRAAF_BG}; navy {JIRAAF_NAVY} headlines; gray body — sharp printed sans-serif.
{ICON_STYLE_LOCK}
{UNIVERSAL_FIT_LOCK}
"""

# Visual quality + orange — static explain posters
STATIC_EXPLAIN_QUALITY_LOCK = f"""
STATIC EXPLAIN QUALITY LOCK:
- Bake headline + supporting + EVERY card heading + explanation line — zero missing text.
- EACH white card MUST have its own distinct LARGE clay-3D icon (not text-only cards).
- Hero clay-3D icon top/center — topic-matched, premium studio render.
- Orange {JIRAAF_ORANGE} dividers between cards + orange CTA button fill (≥2% image area).
- Clean premium layout: ice-blue BG, navy headlines, gray body, sharp sans-serif — no gibberish.
{ORANGE_COVERAGE_LOCK}
{ICON_STYLE_LOCK}
"""

# Mandatory orange on ALL static creatives (explain + ranking + hub)
STATIC_ORANGE_STUB = f"""
STATIC ORANGE LOCK (ALL static formats — FAIL if missing):
Brand orange {JIRAAF_ORANGE} REQUIRED ≥2% of image on EVERY static creative:
- Explain: orange dividers, CTA button, bullet dots, icon accents
- Horizontal bar ranking: orange highlight row, orange headline phrase, orange arrow annotation
- Vertical country ranking (Top Countries): orange rank badges, accent line, CTA, coin icons
- Hub facts: orange hub ring accents, divider lines
Never tan/gold-only static with zero #FFA400.
"""

INFOGRAPHIC_EXPLAIN_ORANGE_STUB = f"""
ORANGE BRAND LOCK (infographic explain — match sample):
Brand orange {JIRAAF_ORANGE} REQUIRED:
1) Thick orange vertical bars left of EVERY section heading
2) 1–3 orange highlight words in intro/section line OR callout (sample: "cautious before")
3) Orange callout box border; optional compact orange CTA
4) Orange accents on clay-3D icons where natural
Headline stays mostly navy (sample style) but MUST include orange text accents somewhere in body.
Orange ≥2% of image. Never tan/gold bars instead of #FFA400.
"""

# Legacy alias — route by format in callers
EDUCATION_POSTER_LAYOUT_LOCK = INFOGRAPHIC_EXPLAIN_LAYOUT_LOCK

# Static HORIZONTAL BAR ranking — sample_static_oil_consumption_bars.png
STATIC_HORIZONTAL_BAR_DNA_LOCK = f"""
════════════════════════════════════════════════════════
STATIC HORIZONTAL BAR DNA — sample_static_oil_consumption_bars.png
Reference: app/prompts/references/jiraaf_samples/sample_static_oil_consumption_bars.png
Use for format=static + static_ranking when topic is oil/consumption/data bars (ADDITIVE — does not replace Top Countries).
════════════════════════════════════════════════════════

COLOURS:
- BG ice-blue {JIRAAF_BG}
- Navy headline {JIRAAF_NAVY} with orange highlight phrase in title
- Bars: medium-blue {JIRAAF_CARD} for rows; HIGHLIGHT row (India/subject) in orange {JIRAAF_ORANGE}
- Orange annotation arrow + insight text on the right
{ORANGE_COVERAGE_LOCK}
{STATIC_ORANGE_STUB}

TEXT + ICONS (every row must be complete):
- Bake country NAME + value inside bar + % outside — no missing labels
- Circular flag icon per row — correct country, never empty
- Clay-3D topic icons bottom-right (oil barrels / coins) — premium HD, not blurry
- Source footer with exact domain text

LAYOUT:
1) Centered headline — highlight key phrase in orange (e.g. "Oil-consuming country")
2) Horizontal BAR CHART rows (top to bottom, longest first):
   EACH row LEFT→RIGHT:
   - Country NAME (navy, all-caps or bold)
   - Circular flag icon at bar start
   - Horizontal rounded BAR (length ∝ value)
   - Value INSIDE bar right end (e.g. "5.621 mb/d" or "₹50B")
   - % share OUTSIDE bar on the right (bold)
3) Highlight the focal country row in ORANGE bar (others blue)
4) Orange arrow annotation → 1–2 line insight text block on the right
5) Premium clay-3D topic icons bottom-right (oil barrels / coins — topic-matched)
6) Source footer bottom-left (e.g. "Source: Indian Express, Energy Institute")
7) Tiny empty top-right pocket for logo — never draw JIRAAF text

CURRENCY: mb/d · ₹ · % · USD letters — NEVER $ / US $ / ESD
FLAGS: correct per country (USA not ASA; UAE not HAE)
CTA: omit or compact ≤4 words — data posts often have no CTA button
"""

STATIC_HORIZONTAL_BAR_IMAGE_STUB = f"""
STATIC HORIZONTAL BAR = sample_static_oil_consumption_bars.png:
BG {JIRAAF_BG}. Navy headline {JIRAAF_NAVY} + orange highlight phrase.
Rows: COUNTRY | flag circle | horizontal bar | value inside | % outside.
Focal row (India/topic) = ORANGE bar; others = blue bars.
Orange arrow → insight text. Clay-3D icons bottom-right. Source footer.
Never vertical rank badges. Never bond benefit cards.
"""

# Hybrid ranking + insight (e.g. "top 7 oil countries — why India is top 3")
STATIC_RANKING_INSIGHT_LOCK = f"""
STATIC RANKING + INSIGHT (when user asks top-N AND why/describe about focal country):
- Main visual = ranking board (horizontal bars OR vertical country rows — do NOT switch to education cards).
- Bake the ranked list/data as the PRIMARY layout (all 7 rows with values).
- Add 1–2 line INSIGHT annotation (orange arrow or callout box) answering the why/describe part.
  Example: "India's rising energy demand reflects expanding mobility, industrial growth, and a fast-growing economy."
- Highlight focal country (India) in ORANGE bar/row when user mentions India.
{STATIC_ORANGE_STUB}
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

# Shared DNA for INFOGRAPHIC ranking — vertical rows (Top Countries sample)
RANKING_SAMPLE_DNA_LOCK = f"""
════════════════════════════════════════════════════════
RANKING SAMPLE DNA — Top Countries vertical rows (UNCHANGED — primary country/FDI ranking)
Reference: app/prompts/references/jiraaf_samples/sample_top_countries_investing.png
Use for: infographic static_ranking OR static static_ranking when topic is country/FDI top-N.
(Does NOT apply to oil/consumption horizontal bar topics — those use STATIC_HORIZONTAL_BAR_DNA_LOCK.)
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
TRADE DEFICIT BOARD LOCK — match sample_india_russia_trade_deficit.png EXACTLY:
Reference: app/prompts/references/jiraaf_samples/sample_india_russia_trade_deficit.png
- Punchy plain headline + one short subtitle on cream rounded strip (no jargon)
- Clean dual-bar year table ONLY: EXPORT (orange) | TRADE BALANCE | IMPORT (navy), Billion USD
- Year labels correct (2020-21, 2021-22, 2022-23, 2023-24…) — never "2021-2023"
- Bake exact strings: "Export: USD X.XB" / "Import: USD Y.YB" — NEVER ESD / Emp / Impp / $
- Orange export bars LEFT; navy import bars RIGHT; balance numbers CENTER (deficit in red if large)
- Bottom light-blue box: "What India buys most from Russia" — orange arrow bullets + category + USD lines
- Source: Ministry of Commerce (or research domain)
- Thick orange brand line at bottom edge optional
- FORBIDDEN technical sidebars: Key Drivers, Sector Exposure, Currency Risk, Vostro/Bistro,
  Investment Considerations, Questions for Advisors, FD briefcase, handshake as main story
- Optional CTA: COMPACT 2–4 words only — never a paragraph-length button
"""

# Static HUB facts — sample_bank_penalties.png
STATIC_HUB_FACTS_DNA_LOCK = f"""
════════════════════════════════════════════════════════
STATIC HUB FACTS DNA — sample_bank_penalties.png
Reference: app/prompts/references/jiraaf_samples/sample_bank_penalties.png
Use for: bank penalties / key rules / top-N bank facts (layout_type=static_hub_facts).
════════════════════════════════════════════════════════

LAYOUT (hub + spoke — NOT ranking rows):
1) Centered navy headline: "Bank's Penalty Rates and Key Rules" (or topic-matched variant)
2) CENTER HUB: white circle with premium clay-3D bank building icon
   - Coloured ring segments behind hub (orange {JIRAAF_ORANGE} segment required)
   - Five bank pods on the ring (Axis Bank | SBI | HDFC Bank | ICICI Bank | PNB)
3) FIVE white rounded cards around hub — one per bank:
   - Exact bank name as heading (typed text — NOT official trademark logos)
   - 1–2 SHORT lines with concrete ₹/% premature-withdrawal rules
   - Thin connector line from card to hub pod
4) BG soft off-white / ice-blue {JIRAAF_BG} — never dark navy/black
5) Tiny empty top-right pocket for logo composite — never draw JIRAAF wordmark
6) NO fake customer quotes. NO teaser question without rates. body="" on blueprint.

COLOURS: navy {JIRAAF_NAVY} headlines · orange {JIRAAF_ORANGE} hub ring segment + dividers (≥2%)
{ORANGE_COVERAGE_LOCK}
{STATIC_ORANGE_STUB}
"""

STATIC_HUB_FACTS_IMAGE_STUB = f"""
STATIC HUB = sample_bank_penalties.png:
Hub + 5 bank fact cards. Center clay-3D bank building. Ring with bank pods.
Cards: Axis | SBI | HDFC | ICICI | PNB — each with ₹/% penalty lines. Orange ring accent.
Never ranking rows. Never bond benefit cards. Never teaser-only headline.
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
- static_hub_facts → hub + 5 bank fact cards (sample_bank_penalties.png)
- static_ranking + oil/consumption/data bars + format=static → horizontal bar (sample_static_oil_consumption_bars.png)
- static_ranking + country/FDI top-N → vertical rank rows (sample_top_countries_investing.png)
- static_ranking + trade deficit → dual-bar board (sample_india_russia_trade_deficit.png)
- carousel_story + format=infographic → DENSE sample editorial (sample_infographic_explain_rbi_polymer.png)
- carousel_story + format=static → simple hero + heading cards (STATIC_EXPLAIN_LAYOUT_LOCK)

════════════════════════════════════════
DATA POST vs TEASER vs EDUCATION
════════════════════════════════════════
If user asks WHY / useful / benefits / explain / how / what is:
→ INFOGRAPHIC: multi-section editorial (section headings + 3-col icon cards + callout box)
→ STATIC: simple hero + 3–5 heading/explanation cards
→ FORBIDDEN: bond benefit cards (Capital Preservation / Regular Income) on unrelated topics
→ FORBIDDEN: invent India vs USA vs Germany yield boards unless user asked compare/rank

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
- TONE: plain retail language on baked text — short sentences, ₹/% facts, NO jargon.
- Layout: FULL headline top-left + 2–3 white story cards with simple ₹/% lines + ONE premium HD clay-3D
  avatar icon (~12–16% height) bottom-right (wallet/coins/doc/lock/shield).
- CTA button (if any): COMPACT — ≤28% canvas width, ≤4.5% height, 2–3 words — NEVER a wide orange bar.
- Bottom ~14% EMPTY for SEBI footer (composited later). Margins ≥8%. Nothing clipped.
- Top-right: plain empty ice-blue — NO logo, NO JIRAAF text, NO "Brand Logo" box.
- Story density like samples — NOT sparse empty slides. Perfect spelling. Plain sans-serif.
"""

CAROUSEL_TONE_IMAGE_STUB = """
TONE on baked text: plain retail — short sentences, ₹/% facts. NO Vostro/hedge/sector-exposure jargon.
"""

CAROUSEL_IMAGE_EXTRA_LOCKS = f"""
BRAND/LOGO BAN: never draw JIRAAF wordmark, giraffe, "Brand Logo", dashed logo box, watermark.
SEBI: leave bottom ~14% empty ice-blue — do NOT bake legal footer text.
INDIA: prefer ₹/%; never £ or $ / US $. Real numbers only. Plain retail tone — no hedge/Vostro jargon.
SPELLING: bake ONLY quoted strings letter-perfect. Never truncate headline with "…" or "o..".
ICON: one HD clay-3D object only — sharp, studio-lit — not blurry toy.
CTA: compact orange pill only (≤28% width, ≤4.5% height) — never oversized wide bar.
"""

STATIC_IMAGE_EXTRA_LOCKS = f"""
BRAND/LOGO BAN: never draw brand wordmark / watermark / "Brand Logo" placeholder.
{NO_SEBI_STATIC_RULE}
{STATIC_ORANGE_STUB}
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
