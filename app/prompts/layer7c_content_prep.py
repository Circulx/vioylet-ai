from __future__ import annotations

from typing import Any

from app.graph.models.layer2_models import BrandIntelligenceOutput
from app.graph.models.layer3_models import CampaignBriefOutput
from app.graph.models.layer6_models import FormatPlanOutput
from app.graph.models.layer7_models import CopyOutput
from app.prompts.base import BasePromptBuilder
from app.prompts.brand_copy_tone import (
    BANK_PENALTY_SAMPLE_RULES,
    SIMPLIFIED_CREATIVE_TONE_RULES,
    SOURCE_FOOTER_RULE,
    INFOGRAPHIC_AUDIENCE_TONE_LOCK,
    INFOGRAPHIC_RANKING_FORMAT_LOCK,
    INFOGRAPHIC_TRADE_BOARD_LOCK,
)
from app.prompts.carousel_sample_dna import CAROUSEL_SAMPLE_DNA



class ContentPrepPromptBuilder(BasePromptBuilder):
    """Layer 7c — Prompt Intelligence → Creative Blueprint."""

    PROMPT_VERSION = "1.3-jiraaf-layout"

    def build_system(self, format_name: str = "static", **kwargs: Any) -> str:
        layout_type = str(kwargs.get("layout_type") or "carousel_story")
        hub = layout_type == "static_hub_facts"
        ranking = layout_type == "static_ranking"
        story = layout_type == "carousel_story"

        layout_block = ""
        if story and format_name == "carousel":
            layout_block = f"""
LAYOUT = carousel_story (LOCKED TO JIRAAF SAMPLE PDFs — Sweep-In / Capital / Gains):
{CAROUSEL_SAMPLE_DNA}
- 5–6 slides STORY: hook → ₹ scenario (3 blocks) → how it works → choice → pros/cons WITH reasons → CTA
- UNIQUE COMPLETE headline every slide (max 8–10 words) — NEVER truncate, NEVER bare topic titles
- body: 22–36 words that teach the beat + proof_points[2–3] full reason lines with ₹/% + chip_labels[3]
- proof_points must be readable explanations (not one-word chips)
- chip_labels NEVER Pros/Cons/Examples/Advantages — empty nav chips make slides look cheap
- Icons/avatars are premium clay-3D accents — COPY must carry the teaching story
- If pros/cons beat: put real reasons in body/proof_points
- Prefer ₹ scenarios, comparison cues, hold-vs-exit choices — same depth as sample PDFs
- Perfect spelling. Never sparse 1–2 line slides.
"""
        elif hub:
            layout_block = """
LAYOUT = static_hub_facts (LOCKED):
- headline like "Bank's Penalty Rates and Key Rules" (not a teaser question alone)
- sections[] with 4–5 REAL entity cards (banks) + short ₹/% includes
- body=""; customer_quote=""; NO fake testimonials replacing data
"""
        elif story:
            layout_block = """
LAYOUT = education poster (LOCKED — carousel_story on static/infographic):
- User asked WHY / useful / benefits / explain — NOT a country comparison.
- headline = topic claim; supporting_line = one short why line
- sections[] = 3–5 BENEFIT/REASON cards (Capital Preservation, Regular Income, etc.)
- FORBIDDEN: invent India/USA/Germany/Japan tables, flags, FDI ranks, or % comparison boards
  unless the user explicitly asked to compare/rank countries
- body often short or empty; cta short
"""
        elif ranking:
            from app.prompts.jiraaf_layout import is_trade_data_board, requested_rank_count

            user_p = str(kwargs.get("user_prompt") or "")
            if is_trade_data_board(user_p):
                layout_block = f"""
LAYOUT = trade deficit DATA BOARD (LOCKED — simple retail tone + India–Russia sample):
{INFOGRAPHIC_AUDIENCE_TONE_LOCK}
{INFOGRAPHIC_TRADE_BOARD_LOCK}
- headline = punchy plain data claim from research — not bond slogans / not "implications"
- supporting_line = one soft factual subtitle
- sections[] YEAR rows: label=FY, includes=["Export: USD …B","Import: USD …B"], stat=balance
- Extra sections: top import categories India buys (fuels/oils/fertilisers) with USD amounts
- source_footer = Ministry of Commerce / research domain
- FORBIDDEN: Capital Preservation, Regular Income, FD, Liquidity Management, bond cards,
  Key Drivers / Currency Risk / Vostro side panels, paragraph CTAs
"""
            else:
                rank_n = requested_rank_count(user_p)
                count_line = (
                    f"- sections[] MUST have EXACTLY {rank_n} ranked rows (user asked for top {rank_n}) — never stop at 5"
                    if rank_n
                    else "- sections[] MUST include ALL entities the user asked to rank/compare — never silently truncate to 5"
                )
                layout_block = f"""
LAYOUT = static_ranking (LOCKED — same DNA for static AND infographic ranking):
{INFOGRAPHIC_AUDIENCE_TONE_LOCK}
{INFOGRAPHIC_RANKING_FORMAT_LOCK}
- Ranked sections: Country | plain phrase ≤6 words | amount — almost no paragraphs
{count_line}
- Fill sections[] OR dense stat_highlights with ALL requested entities
- Real country names + correct flags (UAE not HAE; USA not ASA)
- Currency: ₹/% India retail · ¥ Japan · USD letters if source USD — never $ / US $
- Include Source footer domains when research available
- CTA ≤4 words, compact — or omit
"""

        return f"""You are Violyt's Content Prep Intelligence (Prompt Intelligence orchestrator).

Users are marketers, founders, HR teams, agencies, and SMEs — not prompt engineers.
Never expect perfect prompts. Infer intent, audience, structure, tone, CTA, and visual hierarchy.
Ask nothing that Brand Space or prior layers already provide.

{SIMPLIFIED_CREATIVE_TONE_RULES}
{BANK_PENALTY_SAMPLE_RULES if hub else ""}
{SOURCE_FOOTER_RULE}

PRIMARY JOB
Transform Layer 7 validated copy + brand/brief/format context into a Creative Blueprint
that a non-technical user can review and approve BEFORE any artwork is generated.
REWRITE heavy / textbook / teaser L7 wording into sample-style creatives.
Set layout_type="{layout_type}" and layout_archetype="{layout_type}".

{layout_block}

PIPELINE STAGES (run internally, then emit ONE CreativeBlueprint JSON):
1. Intent Detection
2. Output Detection — respect the selected format: {format_name}
3. Platform Detection
4. Audience Detection
5. Topic Understanding
6. Brand Intelligence Injection
7. Marketing Intelligence
8. Design Intelligence — layout_archetype = {layout_type}
9. AI Planning — Creative Blueprint ONLY (no image generation).

CONTENT RULES
- No teaser ads when the user asked for concrete rates/rules/top-N data.
- Education / why / benefits: sections[] = reason cards — NEVER invent country comparison tables.
- Data layouts only: sections[] with real bank/country names + short ₹/% facts when user asked for ranks/rules.
- Visual-first: education benefit cards OR hub+fact cards OR ranking rows OR carousel story — not paragraphs.
- SPELLING & GRAMMAR: publication-ready English — zero typos.
- If live research sources exist, fill sources:[{{title,url}}] and source_footer like "Source: domain.com".

MUST FILL
- hook + story_flow + headline + supporting_line + body + cta (body often empty for data posts)
- layout_type + sources + source_footer when stats present

FORMAT-SPECIFIC
- static hub: headline + sections[4–5] fact cards; body=""; no fake testimonial
- static ranking: ranked sections — row count = user's top-N (e.g. top 10 → 10 rows, not 5)
- education poster (static/infographic story): 3–5 benefit/reason cards — no country ranks
- carousel story: 4–7 short slides

OUTPUT
Return a single JSON object matching CreativeBlueprint.

KEEP OUTPUT COMPACT.
If L7 returned a teaser, REWRITE it into the sample hub/data/story structure before locking text.
"""

    def build_user(
        self,
        *,
        user_prompt: str,
        platform: str,
        format_name: str,
        brand_intelligence: BrandIntelligenceOutput,
        campaign_brief: CampaignBriefOutput | None,
        format_plan: FormatPlanOutput,
        copy: CopyOutput,
        **kwargs: Any,
    ) -> str:
        layout_type = str(kwargs.get("layout_type") or "carousel_story")
        live_research = kwargs.get("live_research") or {}
        brand = brand_intelligence.brand_core
        behavior = brand_intelligence.communication_behavior
        audience = brand_intelligence.audience_model
        brief_block = ""
        if campaign_brief:
            brief_block = f"""
CAMPAIGN BRIEF (L3):
- Objective: {campaign_brief.campaign_objective}
- Funnel stage: {campaign_brief.funnel_stage}
- Audience intent: {campaign_brief.audience_intent}
- Content role: {campaign_brief.content_role}
- Information density: {campaign_brief.information_density}
- Persuasion model: {campaign_brief.persuasion_model}
- Platform constraints: {campaign_brief.platform_behavior_constraints}
"""

        slides_json = [
            {
                "slide_number": s.slide_number,
                "headline": s.headline,
                "supporting_line": s.supporting_line,
                "body": s.body,
                "cta": s.cta,
            }
            for s in (copy.slide_copy or [])
        ]
        sections_json = [
            {
                "section_label": s.section_label,
                "stat": s.stat,
                "includes": s.includes,
                "body": s.body,
                "icon_hint": s.icon_hint,
            }
            for s in (copy.infographic_sections or [])
        ]

        slide_plan = []
        for sp in getattr(format_plan, "slide_plan", None) or []:
            if hasattr(sp, "model_dump"):
                slide_plan.append(sp.model_dump())
            elif isinstance(sp, dict):
                slide_plan.append(sp)
            else:
                slide_plan.append(str(sp))

        research_block = ""
        verified = live_research.get("verified_facts") or []
        if verified or live_research.get("summary"):
            facts_str = "\n".join(
                f"- {f.get('label','')}: {f.get('value','')}"
                + (f" | {f.get('source_url','')}" if f.get("source_url") else "")
                for f in verified
            )
            research_block = f"""
LIVE RESEARCH (use facts; attach source URLs into sources[]):
Summary: {live_research.get('summary') or 'N/A'}
Verified:
{facts_str or 'none'}
Do NOT invent numbers if research is empty — flag missing_critical instead.
"""

        return f"""USER PROMPT:
{user_prompt}

PLATFORM: {platform}
FORMAT: {format_name}
LAYOUT_TYPE (LOCKED): {layout_type}

BRAND (L2):
- Name: {brand.brand_name}
- Value proposition: {brand.value_proposition}
- Market tension: {brand.market_tension}
- Stands for: {brand.stands_for}
- Competitive position: {brand.competitive_position}
- Tone spectrum: {behavior.tone_spectrum}
- Emotional territory: {behavior.emotional_territory}
- Language behavior: {behavior.preferred_language_behavior}
- Prohibited phrases: {behavior.prohibited_phrases}
- Primary persona: {audience.primary_persona}
- Guardrails: {brand_intelligence.guardrails}
{brief_block}
FORMAT PLAN (L6) slide_plan:
{slide_plan}

VALIDATED COPY (L7/L7b) — SIMPLIFY IF HEAVY:
- headline: {copy.headline}
- supporting_line: {copy.supporting_line}
- body: {copy.body}
- cta: {copy.cta}
- hashtags: {copy.hashtags}
- slide_copy: {slides_json}
- claim_safety_notes: {copy.claim_safety_notes}
- infographic_sections: {sections_json}
- problem_statement: {copy.problem_statement}
- solution_statement: {copy.solution_statement}
- proof_points: {copy.proof_points}
- stat_highlights: {copy.stat_highlights}
- customer_quote: {copy.customer_quote}
- customer_name: {copy.customer_name}
- process_steps: {copy.process_steps}
{research_block}
Produce the Creative Blueprint JSON for {format_name} with layout_type={layout_type}.
Prefer L7 facts/numbers, but REWRITE to Jiraaf SAMPLE tone:
short headlines, ranked/hub numbers OR carousel story beats — almost no paragraphs.
Currency: India retail → ₹; rates → %; Japan commits → ¥; DPIIT FDI → USD labeled clearly.
Countries/flags/banks must be real and matched. Totals must add up.
Brand accents must include orange #FFA400 with navy #003975.
If L7 looks like "What Are Your FD Penalty Rates?" teaser, replace with
"Bank's Penalty Rates and Key Rules" + 5 bank sections.
For rankings: if the user asked for top-N, keep EXACTLY that many section rows (top 10 → 10, not 5).
Lock final short strings for image baking. Fill sources + source_footer when research URLs exist.
"""
