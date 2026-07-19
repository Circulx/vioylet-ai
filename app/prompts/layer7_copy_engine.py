from __future__ import annotations

from typing import Any

from app.graph.models.layer2_models import BrandIntelligenceOutput
from app.graph.models.layer6_models import FormatPlanOutput
from app.prompts.base import BasePromptBuilder


class CopyEnginePromptBuilder(BasePromptBuilder):
    """Builds prompts for Layer 7: Copy Engine."""

    PROMPT_VERSION = "1.1"

    _INFOGRAPHIC_SYSTEM_SUFFIX = """
INFOGRAPHIC FORMAT — CRITICAL ADDITIONAL RULES:
The renderer draws a premium LinkedIn-style infographic poster with the following sections:
1. Headline + Subheadline (top)
2. Problem vs Solution (two cards side-by-side)
3. Feature cards (5 horizontal cards with icon + title + description)
4. Metrics cards (4-5 statistic cards with large numbers)
5. Customer quote (testimonial card)
6. Process timeline (4 steps)
7. CTA section

You MUST populate these extra fields with rich, deep, structured content pulled from the brand
context and live research — NOT generic filler:

- "infographic_sections": Array of EXACTLY 5 sections (one per feature card), each with:
    - "section_label": Short feature title (2-4 words), e.g. "Predictable Income", "Capital Preservation", "Diversification", "Lower Volatility", "Liquidity".
    - "stat": Key metric or number for this feature (e.g. "5-8%", "40% lower", "AAA-rated", "Monthly", "T+1"). Never null — always provide a concrete figure.
    - "includes": Array of EXACTLY 3 short bullet phrases (4-8 words each) describing key benefits/aspects of this feature.
    - "body": 2-3 full sentences explaining WHY this feature matters. Specific, factual, benefit-driven.
    - "icon_hint": One word visual metaphor for renderer (e.g. "growth", "shield", "chart", "calendar", "rupee", "lock", "bond", "cash", "target", "checkmark")

- "problem_statement": 1-2 sentences describing the core problem/pain point the audience faces.

- "solution_statement": 1-2 sentences describing how the brand/product solves this problem.

- "proof_points": Array of exactly 4 short bullet labels (2-3 words each) used as the bottom objective badges, e.g. ["Capital Preservation", "Regular Income", "Long-Term Wealth", "Liquidity Management"].

- "stat_highlights": Array of 4-5 short stat chips, format "<number> <context>", e.g. ["5-8% annual yield", "40% lower volatility", "AAA-rated options", "Monthly payouts"].

- "customer_quote": A realistic 1-2 sentence testimonial quote from a hypothetical satisfied customer.

- "customer_name": Short name for the testimonial, e.g. "Rajesh K., Investor".

- "process_steps": Array of exactly 4 short step labels (2-4 words each), e.g. ["Assess Goals", "Allocate Assets", "Monitor Regularly", "Rebalance Quarterly"].

ALL fields MUST be fully populated. This content IS the visible text on the poster; richer and more
specific content directly improves the final creative. The top-level headline/supporting_line/body
copy should stay concise since the real depth lives in infographic_sections.
"""

    def build_system(self, format_name: str = "static", **kwargs: Any) -> str:
        base = """You are Violyt's Copy Engine. Your task is to generate platform-native, brand-aligned, and strategically focused copy.
You must return a single JSON object representing the generated copy matching the CopyOutput structure.

CRITICAL RULES:
- Brand voice alignment: Use tone spectrum, emotional territory, simplicity, and preferred vocabulary from the brand behavior model.
- Formatting: Provide headline, supporting line, main body, primary call to action, slide copy (if format involves multiple slides/steps), and hashtags.
- Platform context: Tailor copy density and structure to format and platform.
- Uniqueness: Avoid generic AI filler words (e.g., 'unlock', 'elevate', 'revolutionize', 'transform', 'in today\\'s digital landscape'). Be precise, human, and authentic.
- Claim safety: Document any copy lines that contain yield, performance, or financial claims in claim_safety_notes.

JSON OUTPUT STRUCTURE:
{
  "headline": "Main headline or hook",
  "supporting_line": "Sub-headline or secondary line",
  "body": "Primary copy block",
  "cta": "Clickable action line",
  "hashtags": ["#Tag1", "#Tag2"],
  "slide_copy": [
    {
      "slide_number": 1,
      "headline": "Slide headline",
      "supporting_line": "Slide subhead",
      "body": "Slide body copy",
      "cta": "Slide action (optional)"
    }
  ],
  "claim_safety_notes": ["Note about verify claims"],
  "infographic_sections": [
    {
      "section_label": "Feature name",
      "stat": "e.g. 5-8%",
      "includes": ["Bullet 1", "Bullet 2", "Bullet 3"],
      "body": "2-3 sentence why-explanation.",
      "icon_hint": "growth"
    }
  ],
  "problem_statement": "1-2 sentence problem description.",
  "solution_statement": "1-2 sentence solution description.",
  "proof_points": [],
  "stat_highlights": [],
  "customer_quote": "1-2 sentence testimonial.",
  "customer_name": "Customer name, title",
  "process_steps": ["Step 1", "Step 2", "Step 3", "Step 4"]
}

No preamble. No explanations. Return ONLY raw JSON."""

        if format_name == "infographic":
            base += self._INFOGRAPHIC_SYSTEM_SUFFIX
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
        # Prepare list strings
        stands_for = ", ".join(brand_intelligence.brand_core.stands_for)
        prohibited = ", ".join(brand_intelligence.communication_behavior.prohibited_phrases)
        guardrails = "; ".join(brand_intelligence.guardrails)

        slides_str = "\n".join([
            f"- Slide {s.slide_number} (Role: {s.role}, Focus: {s.focus}, Visual Intent: {s.visual_intent})"
            for s in format_plan.slide_plan
        ])

        infographic_note = ""
        if format_name == "infographic":
            infographic_note = """
FORMAT: INFOGRAPHIC
This is a premium LinkedIn-style infographic with multiple content sections. You MUST produce detailed, factual content in:
- infographic_sections: EXACTLY 5 feature cards, each with section_label, stat, includes (exactly 3 bullets), body (2-3 sentence why-explanation), icon_hint
- problem_statement: 1-2 sentence problem description
- solution_statement: 1-2 sentence solution description
- proof_points: exactly 4 short objective badge labels (2-3 words each)
- stat_highlights: 4-5 stat badges as short strings like "5-8% annual yield"
- customer_quote: 1-2 sentence testimonial quote
- customer_name: short customer name/title
- process_steps: exactly 4 short step labels (2-4 words each)

The infographic image will DISPLAY this text on screen. Make it information-dense and specific — pull actual numbers, features, and facts from the brand context. NO decorative fluff, NO empty bullets.
"""

        live_research_note = ""
        verified_facts = (live_research or {}).get("verified_facts") or []
        research_summary = (live_research or {}).get("summary") or ""
        if verified_facts or research_summary:
            facts_str = "\n".join(
                f"- {fact.get('label', '')}: {fact.get('value', '')}"
                + (f" (source: {fact.get('source_title')})" if fact.get("source_title") else "")
                for fact in verified_facts
            )
            live_research_note = f"""
LIVE RESEARCH — LATEST VERIFIED DATA (USE THESE REAL NUMBERS/FACTS WHEREVER RELEVANT):
Summary: {research_summary or 'N/A'}
Verified Facts:
{facts_str or 'No individually verified facts returned.'}

Prioritize these verified, up-to-date facts over generic or outdated claims when populating stats, proof_points, and infographic_sections. Do not fabricate numbers beyond what is provided here or already present in the brand context.
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

SLIDE STRUCTURE TO FOLLOW:
{slides_str}
{infographic_note}{live_research_note}
Generate the copy output. Ensure slide_copy list matches the slide numbers and roles listed above. Keep text concise, impactful, and authentic to the brand."""
