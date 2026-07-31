# Jiraaf sample library (layout DNA)

Samples live in this folder. Used as locked creative DNA for Violyt L7/L7c/L8.

## Carousel story (4–7 slides) — SAMPLE DNA LOCKED
Primary references (content depth + storyline):
| File | Pattern |
|------|---------|
| sample_sweep_in_fd.pdf | Hook → ₹ scenario → comparison table → liquidity/penalty → pros/cons → CTA |
| sample_capital_control_v2.pdf | Hook with real policy fact → define (who/how/where) → why exists → India forms → easing nuance |
| sample_unrealized_gains.pdf | Hook → bond ₹/rate example → hold scenario → exit scenario → when to sell → CTA |

Also:
| File | Pattern |
|------|---------|
| sample_cds_vs_ncds.pdf | Comparison story (Rahul vs Neha), short lines |
| sample_india_japan_investment.pdf | News explainer, ¥ amounts, 3D diorama |
| sample_capital_control.pdf | Myth → definition → implication |
| sample_fire.pdf | Personal-finance education blocks |
| sample_logical_fallacies.pdf | One fallacy per slide |
| sample_jiraaf_1_0.pdf | Character story (Arjun) |
| sample_inflation_lie.pdf | % + ₹ myth-bust, 3D characters |

Code lock: `app/prompts/carousel_sample_dna.py` (`CAROUSEL_SAMPLE_DNA`)

## Static hubs / rankings / data boards
| File | Pattern |
|------|---------|
| sample_top_countries_investing.png | **LOCKED ranking DNA**: orange # badge \| flag \| Name + short phrase \| ₹50B \| coin icon |
| sample_bank_penalties*.png | Hub + 5 bank fact cards, ₹/% |
| India–Russia trade deficit (reference) | Dual-bar year table Export\|Balance\|Import |

**Ranking tone (exact):** "Top investor in India" / "Strong economic ties" / "Growing interest" — never textbook.
Country ranks use **AI image only** (Pillow board disabled). Logo still Brand Space composite.
Code locks: `RANKING_SAMPLE_DNA_LOCK`, `INFOGRAPHIC_AUDIENCE_TONE_LOCK`, `RANKING_IMAGE_STUB`, `INFOGRAPHIC_TRADE_BOARD_LOCK`

## Shared DNA
- BG ice-blue `#E8F0F8`, navy `#003975` headlines only, orange `#FFA400` accents only
- Soft matte clay-3D icons sized to FIT (rounded soft-touch, satin finish — not glossy chrome)
- SEBI disclaimer on CAROUSEL slides only (Pillow-composited). Static / infographic: no SEBI strip.
- India currency rules: ₹/% default; ¥ Japan; USD only when source is USD
- Logo: Brand Space composite only (no AI wordmark)
- Carousel depth: real ₹ scenarios, mechanisms, A-vs-B choices, pros/cons — never shallow slogans
