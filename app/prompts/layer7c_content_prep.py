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
    CAROUSEL_AUDIENCE_TONE_LOCK,
)
from app.prompts.jiraaf_sample_templates import resolve_creative_template



class ContentPrepPromptBuilder(BasePromptBuilder):
    """Layer 7c — Prompt Intelligence → Creative Blueprint."""

    PROMPT_VERSION = "1.4-carousel-retail-tone"

    def build_system(self, format_name: str = "static", **kwargs: Any) -> str:
        layout_type = str(kwargs.get("layout_type") or "carousel_story")
        user_p = str(kwargs.get("user_prompt") or "")
        brand_name = str(kwargs.get("brand_name") or "")
        is_jiraaf = "jiraaf" in brand_name.casefold()
        template = resolve_creative_template(user_p, format_name, brand_name=brand_name or None)
        hub = layout_type == "static_hub_facts"

        from app.prompts.jiraaf_layout import requested_rank_count

        rank_n = requested_rank_count(user_p) if layout_type == "static_ranking" else None
        layout_block = template.l7c_layout_block(rank_n=rank_n)
        if template.template_id == "carousel_story" and is_jiraaf:
            layout_block += f"""
{CAROUSEL_AUDIENCE_TONE_LOCK}
- 5–6 slides STORY: hook → ₹ scenario (3 blocks) → how it works → choice → pros/cons WITH short reasons → CTA
- TONE: plain retail language — same voice as static/infographic (NOT policy analyst / NOT jargon)
- UNIQUE COMPLETE headline every slide (max 8–10 words) — NEVER truncate, NEVER bare topic titles
- body: 18–32 words in short sentences + proof_points[2–3] plain lines with ₹/%
- proof_points must be simple explanations (6–12 words) — not one-word chips or technical dumps
- chip_labels NEVER Pros/Cons/Examples/Advantages — empty nav chips make slides look cheap
- Icons/avatars are premium clay-3D accents — COPY carries the teaching story in plain English
- If pros/cons beat: put real short reasons in body/proof_points
- Prefer ₹ scenarios, simple comparisons, hold-vs-exit choices — depth WITHOUT jargon
- Perfect spelling. Never sparse 1–2 line slides. Never Vostro/hedge/sector-exposure language.
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
- India aviation: always spell UDAN (not ADAN). Prefer verified scheme names, airport counts, passenger figures.
- If live research sources exist, fill sources:[{{title,url}}] and source_footer like "Source: domain.com".

INSIGHT LOCK (MANDATORY — this is the "insight intelligence" pass)
Every section must answer: FACT → SO-WHAT → WHY IT MATTERS.
- section_label: short insight title (not a vague category)
- stat: the concrete number/metric when available (₹ / % / crore / count)
- includes[]: 1–2 hard facts with numbers
- body: 1 complete insight sentence — implication for the reader (investor / traveller / policymaker). NEVER a flat restatement of the label.
BAD body: "More airports make travel easier for millions."
GOOD body: "Regional airports cut multi-leg journeys, unlocking tourism and job growth in tier-2/3 cities."
Reject empty STAT when a number exists in research. Prefer depth over slogans.

MUST FILL
- hook + story_flow + headline + supporting_line + body + cta (body often empty for data posts)
- post_caption: 4–6 short paragraphs for {format_name} on the selected platform — this is the SOCIAL MEDIA caption users paste below the image (NOT text baked into the creative). Write like a human brand manager: educational, conversational, line breaks between paragraphs, end with one engagement question. Do NOT repeat slide/box copy verbatim.
- layout_type + sources + source_footer when stats present

FORMAT-SPECIFIC
- static hub: headline + sections[4–5] fact cards; body=""; no fake testimonial
- static ranking: ranked sections — row count = user's top-N (e.g. top 10 → 10 rows, not 5)
- education poster (static/infographic story): 3–5 benefit/reason cards — each with FACT + INSIGHT body — no country ranks
- carousel story: 4–7 short slides — each slide teaches one insight, not a slogan

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
        is_jiraaf = "jiraaf" in (brand.brand_name or "").casefold()
        is_cognixia = "cognixia" in (brand.brand_name or "").casefold() or "cognia" in (brand.brand_name or "").casefold()
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
Prefer L7 facts/numbers and REWRITE to sample quality:
short headlines, ranked/hub numbers OR carousel story beats — almost no paragraphs.
{"Currency: India retail → ₹; rates → %; Japan commits → ¥; DPIIT FDI → USD labeled clearly. Countries/flags/banks must be real and matched. Totals must add up." if is_jiraaf else f"Use {brand.brand_name}'s brand voice and real facts — no Jiraaf finance jargon, no ₹/SEBI/bond references unless the brand is in finance."}
Brand accents: {"orange #FFA400 with navy #003975 for Jiraaf only" if is_jiraaf else ("Cognixia official: primary #0952A9, deep navy #00387A, card #F3F9FF, accent teal #74ADBA, body #707070, font Outfit — NEVER Jiraaf orange/ice-blue" if is_cognixia else f"use {brand.brand_name} Brand Space palette — NEVER Jiraaf orange/ice-blue/navy")}.
{"If L7 looks like 'What Are Your FD Penalty Rates?' teaser, replace with 'Bank Penalty Rates and Key Rules' + 5 bank sections." if is_jiraaf else f"Use {brand.brand_name} Brand Space voice."}
COMPLETE SENTENCES ONLY: every section_label and body must be a finished thought — never end mid-word or on dangling words (with/and/the/hit/about). Example BAD: "demand will hit 450". Example GOOD: "By 2030, demand will hit 450 million passengers." Put real numbers in STAT when available; put supporting facts in includes[].
INSIGHT PASS: each section body must explain WHY the fact matters (so-what), not repeat the label. Spell India schemes correctly — UDAN not ADAN.
For rankings: if the user asked for top-N, keep EXACTLY that many section rows (top 10 → 10, not 5).
AUDIENCE: Use the EXACT audience from the brand persona — age group, demographics, pain points. NEVER substitute with a different audience (e.g. if TG is children/teens, never show toddlers/babies/adults).
TYPOGRAPHY: Use brand font from Brand Space visual identity if specified.
Lock final short strings for image baking — short but COMPLETE. Fill sources + source_footer when research URLs exist.
"""
