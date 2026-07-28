from __future__ import annotations

from typing import Any

from app.graph.models.layer2_models import BrandIntelligenceOutput
from app.graph.models.layer6_models import FormatPlanOutput
from app.prompts.base import BasePromptBuilder
from app.prompts.brand_copy_tone import (
    BANK_PENALTY_SAMPLE_RULES,
    SIMPLIFIED_CREATIVE_TONE_RULES,
    SOURCE_FOOTER_RULE,
)


def _is_data_hub_topic(text: str) -> bool:
    t = (text or "").lower()
    keys = (
        "penalty",
        "penalties",
        "top 5 bank",
        "top five bank",
        "top 5 banks",
        "key rules",
        "fd ",
        "fixed deposit",
        "premature withdrawal",
    )
    return any(k in t for k in keys)


class CopyEnginePromptBuilder(BasePromptBuilder):
    """Builds prompts for Layer 7: Copy Engine."""

    PROMPT_VERSION = "1.4-jiraaf-layout"

    _CAROUSEL_STORY_SUFFIX = """
CAROUSEL STORY — LOCKED STANDARD (do not invent a new structure each time):
Emit 5–6 slides in slide_copy. Each slide teaches ONE deeper beat from research — not a vague slogan.

ARC (fixed):
1 hook — surprising concrete angle from research (a real mechanism/number/tension)
2 define — what it actually is in plain words (mechanism, not metaphor)
3 how it works — the engine (e.g. coupons / price / duration) with one concrete detail
4 investor implication — who benefits / when it helps, with a specific reason
5 nuance or watch-out from research (risk, condition, myth-bust)
6 CTA — short action (optional if 5 slides)

DEPTH RULES (client bar):
- Source article is good — EXTRACT a deeper insight per slide; do NOT stay at "bonds are useful" / "connect the dots".
- FORBIDDEN vague lines: "Connect the Dots", "bonds like stocks" with no mechanism, "grow in value" alone.
- Every body ≤22 words BUT must include a concrete idea (how coupons work, why income is predictable, what changes price).
- If live research has facts/numbers, put at least one concrete fact across the deck (not all on slide 1).

UNIQUENESS:
- Every headline UNIQUE. Slide 3 and 4 must NOT restate slide 1–2.
- Never clone the same metaphor/body across slides.

CHIP LABELS (for visual layer):
- Also emit chip_labels when writing blueprint slides (3 ONE-WORD labels per slide).
- Examples: Coupons | Principal | Maturity — never half-phrases like Steady / Plan / Less.

TOPIC LOCK: stay on the user's topic. No FDI/FX/capital-control drift.
Spelling perfect.
"""

    _RANKING_SUFFIX = """
STATIC RANKING / DATA BOARD (layout_type=static_ranking):
Pick the board type from the user topic:

A) COUNTRY / TOP-N RANK (FDI, inflation ranks):
- Fill infographic_sections with ranked rows: Name | % | amount.
- Row COUNT must match the user's request (top 10 → 10 rows).

B) TRADE DEFICIT / EXPORT–IMPORT BOARD (India–Russia sample DNA):
- Punchy data headline (e.g. "India Buys 13x More From Russia than it Sells!" when research supports).
- supporting_line: one factual subtitle about deficit growth.
- sections[] = fiscal YEAR rows (typically 2020-21 … 2024-25):
  section_label = year (e.g. "2023-2024")
  includes = ["Export: USD X.XXB", "Import: USD Y.YYB"]
  stat = trade balance as signed number (e.g. "-56.9")
- Add 2–4 more sections for "What India buys most" categories with USD amounts
  (Mineral fuels, Edible oils, Fertilisers, …) from research — not invented.
- source_footer from research (e.g. Ministry of Commerce and Industry).
- body=""; customer_quote="".
FORBIDDEN for trade boards: Capital Preservation, Regular Income, FD briefcase,
Liquidity Management, bond benefit cards, investment product CTAs, wrong flags.
"""

    _EDUCATION_POSTER_SUFFIX = """
EDUCATION / WHY / BENEFITS POSTER (layout_type=carousel_story on static or infographic):
User asked WHY / HOW / useful / benefits / explain — NOT a ranking or country comparison.
- headline: topic claim (e.g. "Bonds: Your Path to Predictable Income")
- supporting_line: one short why-it-matters line
- infographic_sections: 3–5 BENEFIT / REASON cards — labels like "Regular Income",
  "Capital Preservation", "Predictable Coupons" — NOT countries, NOT banks, NOT % ranking rows
- includes = 1 short plain-English reason each (no invented foreign yields)
FORBIDDEN unless the user explicitly asked to compare/rank:
- Country tables (India/USA/Germany/Japan…)
- Flag rows, FDI ranks, cross-market % boards, "vs" comparison matrices
"""

    _INFOGRAPHIC_SYSTEM_SUFFIX = """
INFOGRAPHIC FORMAT — CRITICAL ADDITIONAL RULES:
Match Jiraaf sample tone — scannable, short labels — NOT textbook essays / teaser ads.

Pick structure from USER INTENT (do NOT default to comparison):
- WHY / useful / benefits / explain / how → BENEFIT cards (reasons), never country ranks
- Ranking / top-N / country-wise / FDI → ranked Name|%|amount rows
- Bank penalties / key rules → bank fact cards

When education (why/benefits):
- sections = reasons/benefits with short includes; NO invented country yield tables

When ranking / comparison / top-N (user asked for it):
- section_label = name (country/bank), stat = number when useful, includes = 1–2 short facts

Top-level body usually EMPTY — facts live in sections.
"""

    _STATIC_DATA_HUB_SUFFIX = """
STATIC DATA / HUB TOPICS (bank penalties, top-N rules, comparisons):
Even for format=static you MUST fill infographic_sections with the actual data cards.
Example for FD penalty rates of top 5 Indian banks:
- headline: "Bank's Penalty Rates and Key Rules"
- supporting_line: "" 
- body: ""
- customer_quote: ""
- cta: "" or very short
- infographic_sections: EXACTLY 5 — Axis Bank, SBI, HDFC Bank, ICICI Bank, PNB
  each with includes = 1–2 short ₹/% rule lines, body = ""
FORBIDDEN: teaser creatives that only ask "What Are Your FD Penalty Rates?" without listing the rates.
"""

    def build_system(self, format_name: str = "static", **kwargs: Any) -> str:
        user_prompt = str(kwargs.get("user_prompt") or "")
        layout_type = str(kwargs.get("layout_type") or "")
        data_hub = _is_data_hub_topic(user_prompt) or layout_type == "static_hub_facts"
        base = f"""You are Violyt's Copy Engine. Generate platform-native, brand-aligned creative copy.
Return a single JSON object matching CopyOutput.
LAYOUT_TYPE (LOCKED): {layout_type or "infer from topic"}

{SIMPLIFIED_CREATIVE_TONE_RULES}
{BANK_PENALTY_SAMPLE_RULES if data_hub else ""}
{SOURCE_FOOTER_RULE}

CRITICAL RULES:
- Brand voice: follow tone spectrum, emotional territory, simplicity, and preferred vocabulary from the brand model.
- Prefer short scannable lines over long explanation blocks.
- Uniqueness: avoid generic AI filler (unlock, elevate, revolutionize, transform, in todays digital landscape).
- Claim safety: note yield/performance claims in claim_safety_notes.
- For data/hub topics (bank penalties, top-N rules): fill infographic_sections with the actual facts even if format is static. body/customer_quote usually empty. NO teaser ads.

JSON OUTPUT STRUCTURE:
{{
  "headline": "Main headline or hook (max 12 words)",
  "supporting_line": "One short subhead (max 18 words) or empty",
  "body": "Usually empty for data posts",
  "cta": "Short action or empty",
  "hashtags": ["#Tag1", "#Tag2"],
  "slide_copy": [],
  "claim_safety_notes": ["Note about verify claims"],
  "infographic_sections": [
    {{
      "section_label": "Axis Bank",
      "stat": "",
      "includes": ["Short ₹/% rule line 1", "Short rule line 2"],
      "body": "",
      "icon_hint": "bank"
    }}
  ],
  "problem_statement": "",
  "solution_statement": "",
  "proof_points": [],
  "stat_highlights": [],
  "customer_quote": "",
  "customer_name": "",
  "process_steps": []
}}

No preamble. No explanations. Return ONLY raw JSON."""

        if format_name == "infographic":
            base += self._INFOGRAPHIC_SYSTEM_SUFFIX
        if data_hub or layout_type == "static_hub_facts":
            base += self._STATIC_DATA_HUB_SUFFIX
        # Ranking suffix ONLY for real rankings — never for every infographic
        if layout_type == "static_ranking":
            base += self._RANKING_SUFFIX
        if layout_type == "carousel_story" and format_name in ("static", "infographic"):
            base += self._EDUCATION_POSTER_SUFFIX
        if layout_type == "carousel_story" or format_name == "carousel":
            base += self._CAROUSEL_STORY_SUFFIX
        return base

    def build_user(
        self,
        brand_intelligence: BrandIntelligenceOutput,
        format_plan: FormatPlanOutput,
        concept: dict,
        format_name: str = "static",
        live_research: dict | None = None,
        **kwargs: Any,
    ) -> str:
        user_prompt = str(kwargs.get("user_prompt") or "")
        layout_type = str(kwargs.get("layout_type") or "")
        stands_for = ", ".join(brand_intelligence.brand_core.stands_for)
        prohibited = ", ".join(brand_intelligence.communication_behavior.prohibited_phrases)
        guardrails = "; ".join(brand_intelligence.guardrails)
        data_hub = _is_data_hub_topic(user_prompt) or layout_type == "static_hub_facts"

        from app.prompts.jiraaf_layout import requested_rank_count

        rank_n = requested_rank_count(user_prompt)
        rank_note = ""
        if layout_type == "static_ranking":
            if rank_n:
                rank_note = (
                    f"\nRANK COUNT LOCK: User asked for TOP {rank_n}. "
                    f"infographic_sections MUST contain EXACTLY {rank_n} ranked rows "
                    f"(do not stop at 5).\n"
                )
            else:
                rank_note = (
                    "\nRANK COUNT: Include every entity the user asked to compare/rank "
                    "(do not silently truncate to 5).\n"
                )
        elif layout_type == "carousel_story" and format_name in ("static", "infographic"):
            rank_note = (
                "\nEDUCATION LOCK: User asked why/benefits/explain — sections must be "
                "REASON/BENEFIT cards only. Do NOT invent country comparisons, FDI ranks, "
                "or flag tables unless the user explicitly asked to compare countries.\n"
            )

        slides_str = "\n".join([
            f"- Slide {s.slide_number} (Role: {s.role}, Focus: {s.focus}, Visual Intent: {s.visual_intent})"
            for s in format_plan.slide_plan
        ])

        data_note = ""
        if data_hub:
            data_note = f"""
USER PROMPT (DATA HUB — MUST ANSWER WITH FACTS, NOT A TEASER):
{user_prompt}

Required: headline like "Bank's Penalty Rates and Key Rules";
infographic_sections with EXACTLY 5 Indian banks (Axis, SBI, HDFC, ICICI, PNB)
each with 1–2 short ₹/% premature-withdrawal rule lines.
body="", customer_quote="", no curiosity-only bullets.
"""
        elif user_prompt:
            data_note = f'\nUSER ORIGINAL PROMPT:\n"{user_prompt}"\n{rank_note}'
        else:
            data_note = rank_note
        live_research_note = ""
        verified_facts = (live_research or {}).get("verified_facts") or []
        research_summary = (live_research or {}).get("summary") or ""
        if verified_facts or research_summary:
            facts_str = "\n".join(
                f"- {fact.get('label', '')}: {fact.get('value', '')}"
                + (f" (source: {fact.get('source_title')})" if fact.get("source_title") else "")
                + (f" [{fact.get('source_url')}]" if fact.get("source_url") else "")
                for fact in verified_facts
            )
            live_research_note = f"""
LIVE RESEARCH — GO DEEPER (client bar — not basic slogans):
Summary: {research_summary or 'N/A'}
Verified Facts:
{facts_str or 'No individually verified facts returned.'}

Source article is useful — EXTRACT concrete mechanisms, numbers, and conditions into the deck.
Each carousel slide should teach ONE deeper insight from this research (how it works / why it matters /
what to watch). Do NOT stay at vague lines like "Connect the Dots" or "bonds are like stocks".
Translate into plain language — do not paste research prose. Put at least one concrete fact in the deck.
"""

        return f"""BRAND SIGNAL CONTEXT:
Brand Name: {brand_intelligence.brand_core.brand_name}
Value Proposition: {brand_intelligence.brand_core.value_proposition}
Market Tension: {brand_intelligence.brand_core.market_tension}
Stands For: {stands_for}
Tone: {brand_intelligence.communication_behavior.tone_spectrum}
Emotional Territory: {brand_intelligence.communication_behavior.emotional_territory}
Prohibited terms (DO NOT USE): {prohibited}
Guardrails: {guardrails}

CREATIVE CONCEPT & FOCUS:
Concept: {concept.get('concept_name', 'Default')}
Core Idea: {concept.get('core_idea', '')}
Narrative angle: {concept.get('narrative_angle', '')}
Format layout archetype: {format_plan.layout_archetype}
Format: {format_name}
Layout type (LOCKED): {layout_type or 'auto'}

SLIDE STRUCTURE TO FOLLOW:
{slides_str}
{data_note}{live_research_note}
Generate the copy. Keep every field short, clear, and approachable — never textbook-heavy or teaser-only.
If layout is carousel_story: fill 4–7 slide_copy beats. If hub/ranking: fill complete infographic_sections.
"""
