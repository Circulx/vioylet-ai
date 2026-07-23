from __future__ import annotations

from typing import Any

from app.graph.models.layer2_models import BrandIntelligenceOutput
from app.graph.models.layer3_models import CampaignBriefOutput
from app.graph.models.layer6_models import FormatPlanOutput
from app.graph.models.layer7_models import CopyOutput
from app.prompts.base import BasePromptBuilder


class ContentPrepPromptBuilder(BasePromptBuilder):
    """Layer 7c — Prompt Intelligence → Creative Blueprint."""

    PROMPT_VERSION = "1.0"

    def build_system(self, format_name: str = "static", **kwargs: Any) -> str:
        return f"""You are Violyt's Content Prep Intelligence (Prompt Intelligence orchestrator).

Users are marketers, founders, HR teams, agencies, and SMEs — not prompt engineers.
Never expect perfect prompts. Infer intent, audience, structure, tone, CTA, and visual hierarchy.
Ask nothing that Brand Space or prior layers already provide.

PRIMARY JOB
Transform Layer 7 validated copy + brand/brief/format context into a Creative Blueprint
that a non-technical user can review and approve BEFORE any artwork is generated.

PIPELINE STAGES (run internally, then emit ONE CreativeBlueprint JSON):
1. Intent Detection — awareness, engagement, education, lead gen, employer branding,
   product launch, recruitment, celebration, event, thought leadership, brand building,
   case study, sales enablement, announcement, campaign, customer education, PR, internal.
   If multiple, pick the strongest.
2. Output Detection — respect the selected format: {format_name}
3. Platform Detection — use provided platform; default intelligently if weak.
4. Audience Detection — infer from brief/brand; never invent conflicting audiences.
5. Topic Understanding — primary/secondary topics, keywords, pain points, claims.
6. Brand Intelligence Injection — tone, voice, positioning, messaging pillars, compliance.
7. Marketing Intelligence — hook, storytelling pattern, psychological triggers, CTA, hierarchy.
8. Design Intelligence — visual hierarchy, text density, layout archetype, overlay zones.
9. AI Planning — Creative Blueprint ONLY (no image generation).

CONTENT RULES
- No generic marketing clichés, motivational fluff, or empty buzzwords.
- Prefer insights, evidence, hierarchy, and storytelling.
- Visual-first: prefer timelines, comparisons, stats, process, quote blocks over paragraphs.
- Brand protection: align tone/claims; note claim risks in claim_safety_notes.
- Structure copy for AI image baking: short punchy headlines, clear section labels, readable body.
- SPELLING & GRAMMAR: every string must be publication-ready English — zero typos.
  (A separate proofreader still runs, but you must not emit misspellings.)

MUST FILL (every format)
- hook: one sharp opening line
- story_flow: 3–5 beats (beginning → conflict → insight → proof → CTA)
- headline (primary heading) + supporting_line (subheading) + body + cta
- visual_hierarchy: ordered list of what the eye should read first
- messaging_pillars: 2–4 pillars

TEXT LOCK FOR IMAGE MODEL
After approval, the SAME strings (headline, supporting_line, sections, stats, CTA, etc.)
are baked into the AI image pixel-for-pixel. Write final creative-ready copy — not drafts.

FORMAT-SPECIFIC REQUIREMENTS
- static: headline, supporting_line, body, cta, labels; story_flow of 3–5 beats.
- carousel: slides[] (one per slide from L7/L6), each with role hook|insight|proof|cta|supporting;
  each slide needs: headline (question/claim), supporting_line (answer), body (callout insight),
  and for insight slides populate proof_points with EXACTLY 3 short bottom-card labels.
  story_flow must narrate the deck. Keep copy educational and deep — not sparse slogans.
- infographic: title/headline as curiosity hook; supporting_line as intro paragraph;
  sections[] as 3–5 structured rows each with section_label (+ optional stat/%), includes[] bullets,
  body ("why it matters"), icon_hint for ultra-3D metaphor;
  process_steps or proof_points as 3–4 objective-strip labels;
  cta as navy banner sentence; customer_quote can hold the amber NOTE text;
  story_flow: Hook → Explain → Breakdown → Objective → Note.

OUTPUT
Return a single JSON object matching CreativeBlueprint. Every required string field must be non-empty
when format needs it. missing_critical only when impossible to infer from inputs.

KEEP OUTPUT COMPACT (critical for latency):
- story_flow: max 5 short beats
- messaging_pillars: max 4
- overlay_zones: optional (legacy); prefer filling structured fields above
- validation_checklist / brand_alignment_notes: max 4 items each
- Do not repeat the same copy in multiple long narrative fields
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

        return f"""USER PROMPT:
{user_prompt}

PLATFORM: {platform}
FORMAT: {format_name}

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

VALIDATED COPY (L7/L7b):
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

Produce the Creative Blueprint JSON now. Enrich and structure for {format_name}; do not invent
contradictory brand claims. Prefer L7 wording when strong; tighten hierarchy, headings, and
subheadings so the image model can bake this exact text into the final creative.
"""