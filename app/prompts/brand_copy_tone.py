from __future__ import annotations

"""Shared creative-copy + visual locks from Jiraaf Brand Space + sample PDFs/PNGs."""

JIRAAF_NAVY = "#003975"
JIRAAF_ORANGE = "#FFA400"
JIRAAF_BG = "#E8F0F8"
JIRAAF_CARD = "#D8E8F0"
JIRAAF_GOLD = "#AE8235"
JIRAAF_BODY_GRAY = "#5A6A7A"
JIRAAF_INSIGHT_CREAM = "#FFF5E8"

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

# Shared text + icon quality — oil bar ranking AND infographic explain use SAME family
JIRAAF_SAMPLE_VISUAL_DNA = f"""
JIRAAF SAMPLE VISUAL DNA (oil bar + infographic explain — SAME quality bar):
Reference: sample_static_oil_consumption_bars.png + sample_infographic_explain_rbi_polymer.png

COLOURS:
- BG soft ice-blue {JIRAAF_BG}
- Headline: bold navy {JIRAAF_NAVY} with 1–2 KEY WORDS in orange {JIRAAF_ORANGE} inside the title
- Supporting line: medium gray {JIRAAF_BODY_GRAY} — clearly smaller than headline
- Section headings / card titles: navy bold {JIRAAF_NAVY}
- Body / paragraph lines: gray {JIRAAF_BODY_GRAY} — crisp, readable, NOT oversized
- Insight / callout box: soft cream {JIRAAF_INSIGHT_CREAM} fill + orange {JIRAAF_ORANGE} text
- Bars / focal row / left bars / CTA: orange {JIRAAF_ORANGE}

TYPOGRAPHY:
- Clean geometric sans-serif (Inter / Helvetica) — vector-sharp, perfect kerning
- No warped, melted, hand-drawn, or blurry baked text
- Hierarchy: headline > section heading > card title > body (each ~30% smaller)

ICONS (premium HD — match oil-bar barrel quality):
- Clay-3D studio render: satin materials, gold/navy accents, soft shadows on ice-blue BG
- Section icons LARGE and sharp at 100% zoom — NOT clipart, NOT emoji, NOT blurry blobs
- Bottom-right hero cluster: 1–2 topic-matched 3D props (barrels, coins, notes) with depth + shadow
{ICON_STYLE_LOCK}
"""

EXPLAIN_COLOR_VIBRANCY_LOCK = f"""
COLOUR VIBRANCY LOCK (NON-NEGOTIABLE — same punch as sample_static_oil_consumption_bars.png):
Ranking-board bars/flags render FLAT, FULLY SATURATED colour. This explain infographic MUST match
that same punch — colours currently come out muted/washed-out are a FAIL.
- Navy {JIRAAF_NAVY} must be a DEEP, SATURATED, FLAT navy blue — like the "INDIA" bar fill in the oil
  chart, NOT a pale grayish-blue, NOT a soft muted slate, NOT desaturated.
- Orange {JIRAAF_ORANGE} must be the FULL vivid saturated orange — like the highlighted bar/CTA in the
  oil chart, NOT tan, NOT mustard, NOT a dusty/muted amber.
- Section-1 circular icon badges: FLAT solid navy fill (like a solid bar chart fill) with crisp white
  line-art on top — NOT a soft gradient, NOT a dark charcoal/gray badge, NOT low-contrast.
- Clay-3D icons (Section 2 + hero): keep the 3D form but colour the surfaces in FULLY SATURATED navy/
  orange/gold — avoid heavy shadow or desaturating ambient occlusion that makes them look gray/dull.
- Background stays light ice-blue {JIRAAF_BG} so navy/orange pop with maximum contrast — never let a
  dark or muddy background reduce colour punch.
- If any element would render as gray, beige, muted, pastel, or washed-out — replace it with the exact
  saturated hex values above. Vivid > subtle, every time, on this creative.
"""

JIRAAF_PARAGRAPH_INSIGHT_LOCK = f"""
PARAGRAPH / INSIGHT BLOCK (SAME as sample_infographic_explain_rbi_polymer.png callout):
- Callout box: white/very-pale fill, THIN orange {JIRAAF_ORANGE} border (1–2px) — NOT a solid cream slab
- Orange circle + white lightbulb icon on the left of the box
- Callout text: dark navy/charcoal (NOT orange) — bold ONLY 2–3 key phrases in the same dark colour
- Short paragraph max 2–3 lines, generous line spacing; never a wall of tiny text
- Oil-bar annotation paragraphs (outside callout box) may use 1–3 orange highlight words instead
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

# Infographic EXPLAIN — LOCK to sample_infographic_explain_rbi_polymer.png
# Real dense editorial infographic (NOT a sparse 3-card poster with giant headline)
INFOGRAPHIC_EXPLAIN_LAYOUT_LOCK = f"""
════════════════════════════════════════════════════════
INFOGRAPHIC EXPLAIN — SAMPLE LOCK (NON-NEGOTIABLE)
File: app/prompts/references/jiraaf_samples/sample_infographic_explain_rbi_polymer.png
Same text colour + icon quality family as sample_static_oil_consumption_bars.png
{JIRAAF_SAMPLE_VISUAL_DNA}
{JIRAAF_PARAGRAPH_INSIGHT_LOCK}
This is a REAL multi-section educational infographic. NEVER output a sparse poster.
════════════════════════════════════════════════════════

COLORS (locked):
- BG soft ice-blue/off-white {JIRAAF_BG}
- Headlines/titles navy {JIRAAF_NAVY}
- Body gray; accents orange {JIRAAF_ORANGE} only

TYPE SCALE (CRITICAL — fail if wrong):
- Headline: medium-large navy — ~4–6% of canvas height, wraps 1–2 lines MAX
- Intro: clearly SMALLER than headline (~40% of headline size), 1 line only
- Section headings: medium bold navy (~55% of headline size)
- Card mini-titles: short bold (~40% of headline) — 2–4 words max
- Card body: ONE short line (~30% of headline) — 6–10 words max, gray
- Icons: LARGE — each icon ~25–30% of column width, hero of the column
- FAIL if headline eats the top third OR if body text runs 3+ lines per card

LAYOUT ANATOMY (match sample exactly):
Canvas 1080x1350 portrait. Clean grid — icons prominent, text minimal.

1) HEADER
   - EMPTY top-right logo pocket (never draw JIRAAF wordmark)
   - Navy headline with 1–2 ORANGE highlight words inside title (oil-bar style) + gray intro line

2) SECTION A — THIN orange LEFT vertical bar (NOT full-width orange header) + navy heading
   - 3-COLUMN grid: LARGE navy circular icon + short mini-title + ONE line body
   - Mini-titles unique (Lower costs | Longer life | Global proof)

3) SECTION B — THIN orange LEFT bar + navy heading + 1-line intro (1–2 orange highlight words)
   - 3-COLUMN: LARGE clay-3D icons (container | ATM | wallet) + mini-title + ONE line

4) SECTION C (optional) — THIN orange LEFT bar + ONE short paragraph (max 2 lines, gray body)

5) CALLOUT — cream {JIRAAF_INSIGHT_CREAM} rounded box, thin orange border + lightbulb + orange insight text

6) FOOTER — tiny gray Source line; premium clay-3D hero icons bottom-right (topic-matched, oil-barrel quality)

ORANGE {JIRAAF_ORANGE} REQUIRED: LEFT vertical bars only, highlight words, callout border (~2%+)
{ORANGE_COVERAGE_LOCK}

COPY (SHORT — image model cannot render long paragraphs):
- Card body: 6–10 words max per card — punchy, with ₹/% where possible
- includes[] = "Mini-title | short explanation" (explanation ≤10 words)
- customer_quote = ONE sentence callout (≤16 words)
- Topic-safe CTA only

FORBIDDEN:
- Full-width solid ORANGE section header bars (sample uses LEFT bars beside headings)
- Extra invented text beyond blueprint copy — no paraphrasing, no Hindi, no gibberish
- Sparse poster OR overcrowded wall-of-text — balance icons + short copy
- Oversized headline dominating the canvas
- Solid full-width orange slogan bar instead of bordered callout
- Typos / OBI / ranking boards / off-topic bond cards
- Blurry, clipart, or emoji icons
"""

INFOGRAPHIC_EXPLAIN_SPELLING_LOCK = """
INFOGRAPHIC EXPLAIN SPELLING LOCK (FAIL on any typo):
- Perfect English: Financial not Financrial; Exploring not Explering; could not couid
- durable not duiable; Globally not Gldbally; cautious not caurious; adoption not adeption
- crore not ctore; times not rimes; notes not hotes; hardware not herdware
- currency not currancy; designed not designad; before not berore; switch not sivitch
- RBI not OBI (NEVER OBI); polymer not polmer or palymer
- replacement not replacament; year not yaar; worn not wornn; small not smail; why not wny
- Bake ONLY quoted blueprint strings letter-perfect — zero invented misspellings
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
INFOGRAPHIC EXPLAIN QUALITY LOCK:
{INFOGRAPHIC_EXPLAIN_SPELLING_LOCK}
{JIRAAF_SAMPLE_VISUAL_DNA}
{JIRAAF_PARAGRAPH_INSIGHT_LOCK}
- ZERO spelling mistakes — character-perfect quoted strings only
- SAME icon quality as oil-bar sample: sharp clay-3D, gold/navy accents, bottom-right hero cluster
- Headline: navy + 1–2 orange accent words (like "Oil-" in oil bar sample)
- Paragraph/callout: cream insight box + orange text — NOT a solid orange slab
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
{JIRAAF_SAMPLE_VISUAL_DNA}
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
