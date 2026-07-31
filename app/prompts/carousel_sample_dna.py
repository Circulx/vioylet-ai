from __future__ import annotations

"""Locked carousel DNA from Jiraaf sample PDFs:
- (Jiraaf) Sweep-In FD.pdf
- capital control (2).pdf
- (Jiraaf) Unrealized Gains.pdf

Use for L7 / L7c / L8 carousel story generation.
"""

from app.prompts.brand_copy_tone import (
    CONTENT_DEPTH_LOCK,
    HEADLINE_COLOR_LOCK,
    JIRAAF_BG,
    JIRAAF_NAVY,
    JIRAAF_ORANGE,
)

CAROUSEL_SAMPLE_DNA = f"""
════════════════════════════════════════════════════════
JIRAAF CAROUSEL SAMPLE DNA (NON-NEGOTIABLE — MATCH THESE PDFs)
Samples: Sweep-In FD | Capital Controls | Unrealized Gains
════════════════════════════════════════════════════════

VISUAL SYSTEM (every slide — copy the sample look exactly):
- Canvas 1080x1350 portrait (4:5)
- Background: solid ice-blue {JIRAAF_BG} full-bleed
- Headlines / subheads: dark navy {JIRAAF_NAVY} ONLY — never orange
- Orange {JIRAAF_ORANGE}: dividers, bullets, bars, accent numbers, CTA fill ONLY
- ICONS / AVATARS: premium soft clay-3D illustrated objects (wallet, coins, document,
  lock, shield, chart, phone) — HD sharp, satin + gold accents — like sample PDFs.
  ONE medium-small accent per slide (~12–16% height), bottom-right or mid-right.
  NOT blurry toy blobs. NOT empty slides. NOT giant full-width heroes.
- Bottom ~14% reserved EMPTY for SEBI legal footer (composited later)
- EVERY slide MUST have a full navy headline at top-left — NEVER omit, NEVER truncate mid-word
- Everything fully inside frame — never clip chips/text/icons

STORY ARC (5–6 slides) — SAME SHAPE AS THE SAMPLES (this is the "story"):
1 HOOK — surprising concrete tension with a real fact/number
   Sweep-In: "What if your savings could quietly earn FD-like returns?"
   Capital: "Most people saw a tax change. Economists saw a bigger story."
   Gains: "Your bonds could be sitting on unrealised gains."
2 SCENARIO / DEFINE — plain mechanism + concrete ₹ example in 3 text blocks
   Sweep-In: "Let's say you keep ₹2 lakh…" / "only need ₹50,000…" / "₹1.5 lakh earns low interest"
   Capital: What capital controls are + Who / How much / Where money can move
   Gains: Bought bond ₹1,00,000 @ 9% for 5 years; rates fall to 7% → price rises
3 HOW IT WORKS — engine with comparison OR numbered rules OR concrete mechanism
   Sweep-In: Regular savings vs Sweep-in FD (₹6,000 vs ₹10,500 illustrative)
   Capital: Why controls exist (weaker currency / unstable markets / higher borrowing costs)
   Gains: Hold till maturity — coupon ₹9,000/year + principal
4 IMPLICATION / CHOICE — investor decision with specific conditions
   Sweep-In: "But what happens when you need the money?" + sweep-back + penalty note
   Capital: Real India forms (LRS $250,000, FDI limits, overseas borrowing)
   Gains: Exit earlier — price rise; hold coupons OR book gain
5 NUANCE / PROS-CONS — honest trade-offs WITH full reason sentences (never empty Pros/Cons)
   Sweep-In: Pros vs Cons cards + "it may make sense if…" conditions
   Capital: "Not all capital controls are restrictions" + easing examples
   Gains: When selling earlier may make sense
6 CTA — short question inviting comment
   "Would you opt for Sweep-in FD?" / "What would you do? Comment below!"

PER-SLIDE VISUAL RECIPE (match sample pages — NOT sparse 2-line cards):
HOOK: big question headline (full words) + 1 support line + 1–2 insight cards + premium icon avatar
SCENARIO: short headline + THREE stacked story blocks with ₹ amounts (like Sweep-In page 2)
HOW IT WORKS: headline + mechanism line + comparison/table OR 2–3 fact cards with numbers
CHOICE: question headline + 2–3 explained cards + caveat note
PROS/CONS: headline + TWO columns/cards each with FULL reason sentences (not empty labels)
CTA: big question + "Let us know in the comments" + premium icon
   Optional orange CTA button: COMPACT only (≤28% width, ≤4.5% height) — never a wide bar

DEPTH RULES (client "deep content"):
{CONTENT_DEPTH_LOCK}
- Put REAL ₹ / % / USD / policy numbers from research on 2+ slides.
- Prefer a mini scenario over a slogan (who has how much / what rate / what happens).
- Prefer a comparison or choice (A vs B, hold vs exit, pros vs cons WITH reasons).
- Include ONE honest caveat/note somewhere (penalty, illustrative, risk, condition).
- supporting_line on every slide must add a mechanism or number — not restate the headline.

FORBIDDEN (instant fail — these match the bad outputs the client rejected):
- Truncated headlines ("Interest earned o.." / mid-word cuts / "…")
- Missing headline on any slide
- Sparse slides with only 1–2 short lines and huge empty space
- Empty Pros/Cons/Examples chips with no explanation
- Topic title alone as headline ("Sweep-in FD", "Capital Controls")
- Cloning the same body across slides
- Cheap blurry calculator / toy icons

PER-SLIDE COPY SHAPE:
- headline: max 8–10 words, COMPLETE (no truncation), navy, unique, concrete
- supporting_line: 1 short mechanism/number sentence (REQUIRED)
- body: 22–36 words — full scenario / mechanism / comparison / caveat
- proof_points: 2–3 FULL explanation lines with ₹/%/rules
- chip_labels: exactly 3 ONE-WORD content labels matching THIS slide's beat
  Sweep-In: Idle | Threshold | Sweep  OR  Liquidity | Penalty | Access
  Capital: Who | Amount | Where  OR  Currency | Markets | Costs
  Gains: Price | Coupon | Tenure  OR  Hold | Exit | Redeploy

COLOUR LOCK:
{HEADLINE_COLOR_LOCK}
"""

# Compact version kept for L7/L7c reference — NEVER paste into image API prompts
# (use CAROUSEL_IMAGE_STYLE_STUB from brand_copy_tone instead — 6000 char budget).
CAROUSEL_SAMPLE_DNA_COMPACT = f"""
CAROUSEL ONLY — MATCH SAMPLE PDFs (Sweep-In / Capital / Gains):
STORY: hook → ₹ scenario (3 blocks) → how it works → choice → pros/cons WITH reasons → CTA.
EVERY slide: FULL navy headline top-left (never omit, never truncate mid-word).
CONTENT DENSE: 2–3 white story cards with ₹/%/rules — NOT sparse empty slides.
ICONS/AVATARS: ONE premium HD clay-3D object (~12–16% height) bottom-right.
Bottom ~14% EMPTY for SEBI. COLOUR: navy {JIRAAF_NAVY}; orange {JIRAAF_ORANGE}; BG {JIRAAF_BG}.
"""
