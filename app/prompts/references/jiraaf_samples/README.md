# Jiraaf sample library (layout DNA) — LOCKED ONCE

Samples live in this folder. Used as permanent creative DNA for Violyt L7/L7c/L8.
**Do not ask the user to re-provide these samples** — they are locked in code + this folder.

**Resolver:** `app/prompts/jiraaf_sample_templates.py` → `resolve_creative_template(prompt, format)`

## Locked PNG templates (permanent)

| Sample file | Template ID | When |
|-------------|-------------|------|
| **`sample_infographic_explain_rbi_polymer.png`** | `infographic_explain_editorial` | Explain colors DNA (BG ice-blue · navy · orange) |
| **`sample_infographic_illustrated_spectrum.png`** | `infographic_explain_editorial` | Explain **layout** DNA (visual-first spectrum style) |
| **`sample_infographic_illustrated_salary.png`** | `infographic_explain_editorial` | Explain **layout** DNA (illustrated salary style) |
| `sample_static_oil_consumption_bars.png` | `horizontal_bar_ranking` | Oil/consumption top-N + static |
| `sample_top_countries_investing.png` | `vertical_country_ranking` | Country/FDI top-N |
| `sample_bank_penalties.png` | `static_hub_facts` | Bank penalties / key rules |
| `sample_india_russia_trade_deficit.png` | `trade_deficit_board` | Trade deficit data |

### Infographic explain (locked — sample_infographic_explain_why_airports.png)
1. Navy headline + gray insight thesis  
2. At-a-glance stats + reason cards (story beats)  
3. Proof chart + navy footer tagline  
4. Empty top-right logo pocket (Brand Space composite)

**Universal colours (ALL Jiraaf assets):** BG `#E8F0F8` · navy `#003975` · orange `#FFA400` · body gray `#5A6A7A`  
Same palette for explain, ranking, lists, paragraphs — no format invents a new palette.
AI-only. Ranking boards use the same hexes.

Code: `INFOGRAPHIC_EXPLAIN_LAYOUT_LOCK` in `brand_copy_tone.py`

## Carousel (LOCKED — RBI plastic sample grid)
| Sample | Path |
|--------|------|
| Full grid | `sample_carousel_rbi_plastic_grid.png` |
| Cropped slides 01–10 | `carousel_rbi_plastic_slides/sample_slide_XX.png` |

**Exact template DNA** (code: `carousel_image_prompt.py`):
1. Soft sky BG `#D9ECF8` · navy `#033B5E` · orange `#FF8C24`
2. **NO page numbers** in generated images (no 01 badge, no 1 of N)
3. Top-right Brand Space logo composite · bottom navy bar + SEBI composite
4. 10-slide story arc with locked layout + 3D hero per slide position (see `SAMPLE_SLIDE_SPECS`)
5. Left-aligned unique UPPERCASE headline + orange underline + short body

## Carousel PDFs (story arc — Sweep-In / Capital / Gains)
Still used for educational story shape via `carousel_sample_dna.py`

## Shared DNA
- Navy `#003975` · Orange `#FFA400` · soft BG  
- Logo: Brand Space composite only  
- SEBI: carousel only  

## QA
```bash
python scripts/verify_layout_router.py
```
