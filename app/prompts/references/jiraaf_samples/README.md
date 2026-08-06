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

### Infographic explain (locked — sample_infographic_explain_rbi_polymer.png)
1. Navy headline (**not oversized**) + gray intro  
2. Orange-bar section + **3 circular-icon fact columns** with real explanations  
3. Orange-bar section + orange highlight words + **3 clay-3D fact columns**  
4. Orange-bar text section (short paragraphs)  
5. Thin orange-border callout + lightbulb (**not** solid orange slab)  
6. Source footer · empty top-right logo pocket  

Colors: BG `#E8F0F8` · navy `#003975` · orange `#FFA400`  
AI-only. Ranking boards unchanged.

Code: `INFOGRAPHIC_EXPLAIN_LAYOUT_LOCK` in `brand_copy_tone.py`

## Carousel PDFs
Sweep-In FD / Capital Controls / Unrealized Gains → `carousel_sample_dna.py`

## Shared DNA
- Navy `#003975` · Orange `#FFA400` · soft BG  
- Logo: Brand Space composite only  
- SEBI: carousel only  

## QA
```bash
python scripts/verify_layout_router.py
```
