from __future__ import annotations

from typing import Any

from app.graph.models.layer2_models import BrandIntelligenceOutput
from app.graph.models.layer6_models import FormatPlanOutput
from app.graph.models.layer7_models import CopyOutput
from app.prompts.base import BasePromptBuilder
from app.prompts.brand_copy_tone import (
    JIRAAF_BG,
    JIRAAF_CARD,
    JIRAAF_GOLD,
    JIRAAF_NAVY,
    JIRAAF_ORANGE,
    SOURCE_FOOTER_RULE,
    SEBI_FOOTER_HINT,
    NO_SEBI_STATIC_RULE,
    CAROUSEL_FIT_LOCK,
    UNIVERSAL_FIT_LOCK,
    ICON_STYLE_LOCK,
    ORANGE_COVERAGE_LOCK,
    HEADLINE_COLOR_LOCK,
    CONTENT_DEPTH_LOCK,
    CAROUSEL_ICON_LOCK,
    CAROUSEL_TEXT_FIT_LOCK,
    CAROUSEL_AUDIENCE_TONE_LOCK,
    PREMIUM_HD_ICON_LOCK,
    EDUCATION_POSTER_LAYOUT_LOCK,
    INFOGRAPHIC_EXPLAIN_LAYOUT_LOCK,
    INFOGRAPHIC_EXPLAIN_ORANGE_STUB,
    INFOGRAPHIC_EXPLAIN_QUALITY_LOCK,
    STATIC_EXPLAIN_LAYOUT_LOCK,
    STATIC_EXPLAIN_QUALITY_LOCK,
    STATIC_ORANGE_STUB,
    STATIC_RANKING_INSIGHT_LOCK,
    STATIC_HORIZONTAL_BAR_DNA_LOCK,
    STATIC_HORIZONTAL_BAR_IMAGE_STUB,
    INFOGRAPHIC_AUDIENCE_TONE_LOCK,
    INFOGRAPHIC_RANKING_FORMAT_LOCK,
    INFOGRAPHIC_TRADE_BOARD_LOCK,
    RANKING_IMAGE_STUB,
    STATIC_IMAGE_EXTRA_LOCKS,
)
from app.prompts.creative_sizes import size_string, canvas_label
from app.prompts.carousel_sample_dna import CAROUSEL_SAMPLE_DNA_COMPACT


class VisualReasoningPromptBuilder(BasePromptBuilder):
    """Layer 8 Visual Reasoning — prompts rebuilt from Jiraaf-grade sample creatives."""

    PROMPT_VERSION = "5.1-infographic-explain-static-bar-samples"

    # Locked design tokens from Brand Space + PDF samples
    CAROUSEL_BG = JIRAAF_BG  # ice-blue #E8F0F8
    INFO_BG = JIRAAF_BG
    NAVY = JIRAAF_NAVY  # #003975
    BODY_GRAY = "#4A5568"
    ORANGE = JIRAAF_ORANGE  # #FFA400 — REQUIRED accent
    GOLD = JIRAAF_GOLD
    CARD_BLUE = JIRAAF_CARD
    BANNER_NAVY = JIRAAF_NAVY

    def build_system(self, fmt: str = "", **kwargs: Any) -> str:
        layout_type = str(kwargs.get("layout_type") or "")
        layout_lock = ""
        if layout_type == "carousel_story":
            if fmt in ("static", "infographic"):
                layout_lock = (
                    "LAYOUT_TYPE=carousel_story (education poster on static/infographic): "
                    "headline + 3–5 heading+explanation cards — NOT ranking rows, NOT country flags."
                )
            else:
                layout_lock = (
                    "LAYOUT_TYPE=carousel_story: 4–7 swipe education slides; one idea per slide; short lines."
                )
        elif layout_type == "static_hub_facts":
            layout_lock = "LAYOUT_TYPE=static_hub_facts: hub + 4–5 short fact cards with real ₹/% facts — never teaser-only."
        elif layout_type == "static_ranking":
            layout_lock = "LAYOUT_TYPE=static_ranking: ranked Name|%|amount rows; almost no paragraphs."

        if fmt == "carousel":
            format_instructions = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAROUSEL — SAMPLE DESIGN SYSTEM (LOCKED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Canvas: 1080x1350 portrait (4:5) educational LinkedIn carousel slide.
ABSOLUTE BOUNDARY: every element fully inside the 1080x1350 canvas — nothing bleeds or clips past edges.
Safe margin ≥6% all sides. Reduce/drop content rather than clip.
Background: SOLID {self.CAROUSEL_BG} FULL BLEED edge-to-edge — same hex everywhere.
NO white side panels. NO second background. NO framed white page inside the canvas.
Style: Clean corporate fintech education matching Jiraaf sample carousels.
{CAROUSEL_AUDIENCE_TONE_LOCK}
Soft ULTRA-PREMIUM HD clay-3D icons (4K-sharp studio product renders, satin + gold accents, strong shadows — NOT flat, NOT blurry, NOT low-poly).
Typography: bold navy ({self.NAVY}) headlines; gray supporting; ALL copy baked.
Text must render as clean printed sans-serif, not embossed, not glowing, not outlined, not metallic.
{HEADLINE_COLOR_LOCK}

SLIDE ANATOMY — TEXT DOMINANT (carousel only — match Sweep-In / Capital / Gains):
1. TOP-RIGHT: plain empty ice-blue corner only — never draw logo, wordmark, or "Brand Logo" placeholder.
2. MANDATORY UNIQUE navy headline at top-left on EVERY slide — never omit, never repeat topic title.
3. Supporting line with mechanism or real number (required).
4. DEPTH BLOCK (REQUIRED, ~35–45% of slide height): max TWO white cards with soft shadow.
   EACH card = short bold label + one clear explanation (6–12 plain English words) with ₹/%/rule.
5. ICONS/AVATARS: premium HD clay-3D object (~12–16% height) bottom-right — wallet/coins/doc/lock. NEVER omit. NEVER giant hero.
6. Thin orange divider optional between cards — never a stack of orange lines as the layout.
7. NEVER empty Pros/Cons/Examples/Advantages navigation buttons.
8. Bottom ~24% EMPTY for legal footer composite — do not bake SEBI text.

   Exact SEBI legal footer is composited in post (same as logo). Never invent SEBI text.

{ICON_STYLE_LOCK}
{CAROUSEL_ICON_LOCK}
{CAROUSEL_TEXT_FIT_LOCK}
{CAROUSEL_FIT_LOCK}
{CAROUSEL_SAMPLE_DNA_COMPACT}

RULES:
- Required every slide: mandatory unique headline + supporting + max 2 explained fact cards.
- Icons must stay tiny. If unsure, prefer MORE text and SMALLER icons.
- FULL-BLEED ice-blue only — never white side bars / dual backgrounds.
- Text style must be plain printed sans-serif with perfect English spelling — no stylized chrome/glow outlines.
- EACH SLIDE UNIQUE: different headline, different facts, different look.
- Brand colours: navy {self.NAVY} + orange accents {self.ORANGE}.
{HEADLINE_COLOR_LOCK}
{ORANGE_COVERAGE_LOCK}
- NEVER invent Follow-Jiraaf lines; top-right corner stays plain empty ice-blue.
- Perfect spelling. Do not invent SEBI text.
- India market: prefer ₹ / %; USD only when source is USD.
- Bake copy in plain retail tone — no Vostro/hedge/sector-exposure jargon on slides.
- FAIL if: repeated headlines, empty Pros/Cons chips, giant icons, thin one-line content, clipped text.
"""
        elif fmt == "infographic":
            format_instructions = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INFOGRAPHIC — MATCH JIRAAF SAMPLE POSTERS (LOCKED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Canvas: 1080x1350 portrait LinkedIn educational poster.
ABSOLUTE BOUNDARY: every element fully inside the 1080x1350 canvas — nothing bleeds or clips past edges.
Safe margin ≥6% all sides. Reduce/drop content rather than clip.
Background: Soft off-white {self.INFO_BG}.
Style: Clean, scannable, premium fintech — LIKE the Jiraaf samples (ranking bars / hub facts / % ranks).
Typography: Bold navy headings; short labels; ALL copy baked into pixels.

CHOOSE LAYOUT BY TOPIC (pick ONE — do not invent essay grids):
A) TRADE DEFICIT / EXPORT–IMPORT DATA BOARD (India–Russia sample — when user asks trade deficit):
   - Punchy data headline + one factual subtitle
   - Column headers: EXPORT | TRADE BALANCE | IMPORT (Billion USD)
   - Year rows with orange export bars LEFT, blue import bars RIGHT, balance numbers CENTER
   - Bottom box: "What India buys most from Russia" with category + USD amounts
   - Source footer (Ministry of Commerce…)
   - NO clay FD briefcase, NO Capital Preservation / Regular Income / bond cards, NO investment CTAs
B) EDUCATION / WHY / BENEFITS (ONLY when user asks why / useful / predictable income / explain):
   - Hero clay-3D icon + 3–5 BENEFIT/REASON cards — NOT trade tables
C) RANKING LIST (ONLY if user asked top-N / FDI / country-wise ranks):
   - Vertical ranked rows: flag/icon + NAME + bar + % + metric
D) HUB + SHORT FACTS (ONLY bank penalties / key rules):
   - Center hub + 4–5 bank fact cards

POSTER RULES:
1. TOP-RIGHT: tiny empty pocket only — NEVER draw logo/wordmark OR brand-name text (JIRAAF).
2. Prefer short labels over paragraphs. If blueprint has long body, IGNORE it visually.
3. Brand colours REQUIRED: navy {self.NAVY} + visible orange accents {self.ORANGE}
{ORANGE_COVERAGE_LOCK}
   (section dashes, highlight bars, CTA arrows, dividers). Never navy-only.
4. Trade boards = flat bars + typography. Soft matte clay-3D ONLY for education/hub — never on trade tables.
5. Bake exact approved short strings; spelling must be perfect.
6. NEVER invent bond/FD benefit cards for a trade-deficit topic.
7. Currency: USD labeled for trade boards; ₹ for India retail topics.
8. No textbook essay paragraphs under every card.
9. No empty shells. No purple AI aesthetic.
"""
        else:
            format_instructions = f"""
STATIC SOCIAL FORMAT — MATCH JIRAAF SAMPLE TONE:
- Canvas: exact format×platform size (LinkedIn static 1200x627, Instagram 1080x1080, X 1200x675).
- ABSOLUTE BOUNDARY: every element fully inside the canvas — nothing bleeds or clips past edges.
- Safe margin ≥6% all sides. Reduce/drop content rather than clip.
- Background ice-blue {self.CAROUSEL_BG}.
- Brand colours REQUIRED: navy {self.NAVY} + visible orange accents {self.ORANGE}.
{ORANGE_COVERAGE_LOCK}
- Trade deficit / export-import → dual-bar year table (NOT bond education cards).
- Education / why topics → benefit cards + hero icon (NOT country comparisons).
- Ranking / comparison ONLY when the user asked for top-N / country-wise / vs ranks.
- Tiny TOP-RIGHT pocket only for Brand Space logo — never AI-draw brand-name text.
- Headline + 1 support line + short facts. NO textbook paragraphs.
- Perfect spelling on all baked text.
"""

        return f"""You are Violyt's Visual Reasoning Engine. Plan composition for a finished AI image with baked-in typography.
Return ONE JSON object matching VisualReasoningOutput EXACTLY — every required key below must be present.

CRITICAL:
- dominant_visual_system: generated_image | type_led | illustration | infographic | data_visual | product_visual
- visual_format_type: comparison | timeline | chart | matrix | process_flow | hero_scene | data_grid
- Bake approved Creative Blueprint copy into the image as sharp typography (exact strings).
- Prefer soft matte clay-3D iconography (rounded soft-touch fintech icons) matching Jiraaf samples.
- NEVER draw logos/wordmarks or brand-name text (no JIRAAF letters); Brand Space logo is composited later into a tiny top-right pocket.
- Spelling of every planned text string must be perfect.
- generated_image_url must be "".
- image_prompt_direction: 600–900 words describing layout, soft matte 3D icons, colors, AND exact text to render.

REQUIRED JSON SHAPE (fill every field; do not rename keys):
{{
  "dominant_visual_system": "infographic",
  "visual_format_type": "data_grid",
  "visual_style": "Premium corporate educational creative with soft matte clay-3D icons",
  "composition_logic": "Top-down educational hierarchy with hero visual and structured rows",
  "focal_point": "Central soft matte clay-3D icon cluster",
  "negative_space_plan": "Generous margins; tiny logo-safe top-right pocket only — headline fully clear",
  "color_behavior": "Navy #003975 headlines on ice-blue #E8F0F8 with REQUIRED orange #FFA400 accents",
  "logo_zone_instruction": "Tiny top-right pocket (~12% width x 7% height), 20px padding; never draw brand-name text",
  "typography_behavior": "Bold navy sans headlines, readable gray body, baked into image",
  "image_prompt_direction": "Detailed image prompt covering layout, icons, colors, and exact text...",
  "content_sections": [
    {{
      "section_id": "row_1",
      "title": "Section title",
      "body": "Why it matters",
      "metric": "45%",
      "visual_metaphor": "3D classical bank building"
    }}
  ],
  "text_overlay_plan": [
    {{
      "element_type": "headline",
      "text": "Exact headline",
      "font_size": 42,
      "color_hex": "#0B2C5F",
      "position_box": "top-center"
    }},
    {{
      "element_type": "supporting_line",
      "text": "Exact supporting line",
      "font_size": 22,
      "color_hex": "#4A5568",
      "position_box": "upper-center"
    }},
    {{
      "element_type": "cta",
      "text": "Exact CTA",
      "font_size": 20,
      "color_hex": "#FFFFFF",
      "position_box": "footer-strip"
    }}
  ],
  "generated_image_url": ""
}}

content_sections items MUST use keys section_id + title (not section_label).
text_overlay_plan items MUST include font_size, color_hex, position_box.
element_type allowed: headline|subheadline|supporting_line|body|cta|label|footer|section_label|stat|badge.

No preamble. No markdown fences. ONLY raw JSON.
{layout_lock}
{SOURCE_FOOTER_RULE}
{(SEBI_FOOTER_HINT if fmt == "carousel" and "jiraaf" in str(kwargs.get("brand_name") or "").casefold() else NO_SEBI_STATIC_RULE)}
{format_instructions}"""

    def build_user(
        self,
        brand_intelligence: BrandIntelligenceOutput,
        format_plan: FormatPlanOutput,
        copy: CopyOutput,
        concept: dict,
        user_prompt: str = "",
        **kwargs: Any,
    ) -> str:
        fmt = str(kwargs.get("fmt") or "").strip().lower()
        layout_type = str(kwargs.get("layout_type") or "").strip()
        colors = f"Primary: {brand_intelligence.visual_behavior.color_behavior}"
        mood = brand_intelligence.visual_behavior.visual_mood
        logo_zone = brand_intelligence.visual_behavior.logo_zone_instruction
        user_prompt_section = (
            f"\nUSER ORIGINAL PROMPT (primary topic direction):\n{user_prompt}\n" if user_prompt else ""
        )

        if fmt == "carousel" or layout_type == "carousel_story":
            text_directive = (
                f"Follow the LOCKED carousel sample system: solid background {self.CAROUSEL_BG}, "
                "soft matte clay-3D multi-object hero, callout box, 3 bottom insight cards, baked text."
            )
        elif layout_type == "static_hub_facts":
            text_directive = (
                f"Follow hub+fact-cards sample: soft bg {self.INFO_BG}, center hub, 4–5 short fact cards, "
                f"navy {self.NAVY} + orange {self.ORANGE} accents, Source footer if provided."
            )
        elif layout_type == "static_ranking":
            from app.prompts.jiraaf_layout import is_trade_data_board

            if is_trade_data_board(user_prompt or ""):
                text_directive = (
                    f"Follow TRADE DEFICIT data board (India–Russia sample): soft bg {self.INFO_BG}, "
                    f"EXPORT(orange)|BALANCE|IMPORT(navy) year rows with dual bars, "
                    f"'What India buys most' category box, Source footer. "
                    f"NO FD/bond benefit cards. Navy {self.NAVY} + orange {self.ORANGE}."
                )
            else:
                text_directive = (
                    f"Follow ranking sample: soft bg {self.INFO_BG}, Name|%|amount rows, "
                    f"navy {self.NAVY} + orange {self.ORANGE}, Source footer if provided."
                )
        elif fmt == "infographic" or (
            layout_type == "carousel_story" and fmt in ("static", "infographic")
        ):
            if layout_type == "carousel_story" and fmt == "infographic":
                text_directive = (
                    f"Follow DENSE INFOGRAPHIC EXPLAIN (sample_infographic_explain_rbi_polymer.png): "
                    f"BG {self.INFO_BG}, navy {self.NAVY}, orange {self.ORANGE}. "
                    f"Multi-section editorial with orange bars + 3-col fact cards + callout. "
                    f"Headline NOT oversized. Fill canvas with real content. Perfect spelling."
                )
            else:
                text_directive = (
                    f"Follow STATIC EXPLAIN poster: soft bg {self.INFO_BG}, hero clay-3D icon, "
                    f"3–5 heading + explanation cards, navy {self.NAVY} + orange {self.ORANGE}."
                )
        else:
            text_directive = (
                "Bake approved headline/supporting/CTA as sharp typography; use soft matte clay-3D icons."
            )

        return f"""BRAND VISUAL SYSTEM CONTEXT:
Brand Name: {brand_intelligence.brand_core.brand_name}
Value Proposition: {brand_intelligence.brand_core.value_proposition}
Brand Stands For: {', '.join(brand_intelligence.brand_core.stands_for)}
Brand Stands Against: {', '.join(brand_intelligence.brand_core.stands_against)}
Visual Mood: {mood}
Design Sophistication: {brand_intelligence.visual_behavior.design_sophistication}
Color Behavior: {colors}
Image Behavior: {brand_intelligence.visual_behavior.image_behavior}
Logo Zone Instruction: {logo_zone}
Layout Type (LOCKED): {layout_type or 'auto'}
{user_prompt_section}
CONCEPT:
Name: {concept.get('concept_name', '')}
Core Idea: {concept.get('core_idea', '')}
Hook: {concept.get('hook', '')}
Narrative Angle: {concept.get('narrative_angle', '')}
Visual Angle: {concept.get('visual_angle', '')}
Layout Archetype: {format_plan.layout_archetype}
Format Strategy: {format_plan.format_strategy}
Copy Headline: {copy.headline}
Supporting Line: {copy.supporting_line or 'N/A'}
Copy Body: {copy.body}
CTA: {copy.cta}

SLIDE ROLES AND VISUAL INTENTIONS:
{chr(10).join([f"- Slide {s.slide_number}: role={s.role}, focus={s.focus}, visual_intent={s.visual_intent}" for s in format_plan.slide_plan])}

INSTRUCTION:
Think like a world-class fintech art director. Plan a scannable educational layout with short copy and soft matte clay-3D icons.
{text_directive}

Return ONLY raw JSON."""

    def build_expander_system(
        self, dominant_visual_system: str = "generated_image", fmt: str = "static"
    ) -> str:
        return (
            "You are a senior fintech Art Director writing the FINAL image-generation prompt for gpt-image-1. "
            "Match the locked sample design system for the requested format. "
            "Output ONLY the expanded prompt text — no preamble, no markdown headers."
        )

    def build_expander_user(
        self,
        brand_name: str,
        visual_mood: str,
        color_behavior: str,
        image_behavior: str,
        design_sophistication: str,
        concept_name: str,
        core_idea: str,
        visual_angle: str,
        copy_headline: str,
        copy_body: str,
        supporting_line: str = "",
        cta: str = "",
        infographic_sections: list[dict] | None = None,
        proof_points: list[str] | None = None,
        stat_highlights: list[str] | None = None,
        problem_statement: str = "",
        solution_statement: str = "",
        customer_quote: str = "",
        customer_name: str = "",
        process_steps: list[str] | None = None,
        format_strategy: str = "",
        layout_archetype: str = "",
        platform: str = "",
        initial_prompt: str = "",
        user_prompt: str = "",
        dominant_visual_system: str = "generated_image",
        fmt: str = "static",
        story_flow: list[str] | None = None,
        hook: str = "",
        slides: list[dict] | None = None,
        **kwargs: Any,
    ) -> str:
        # Resolve exact export size for this format+platform — used in every sub-builder
        canvas = canvas_label(fmt, platform)  # e.g. "1080x1350 4:5 portrait"
        layout_type = str(kwargs.get("layout_type") or layout_archetype or "")

        if fmt == "infographic":
            return self._build_infographic_prompt(
                brand_name=brand_name,
                headline=copy_headline,
                supporting_line=supporting_line,
                body=copy_body,
                cta=cta,
                hook=hook,
                story_flow=story_flow or [],
                infographic_sections=infographic_sections or [],
                stat_highlights=stat_highlights or [],
                proof_points=proof_points or [],
                problem_statement=problem_statement,
                solution_statement=solution_statement,
                customer_quote=customer_quote,
                customer_name=customer_name,
                process_steps=process_steps or [],
                user_prompt=user_prompt,
                visual_mood=visual_mood,
                color_behavior=color_behavior,
                canvas=canvas,
                layout_type=layout_type,
            )

        if fmt == "carousel":
            return self._build_carousel_prompt(
                brand_name=brand_name,
                headline=copy_headline,
                supporting_line=supporting_line,
                body=copy_body,
                cta=cta,
                hook=hook,
                story_flow=story_flow or [],
                proof_points=proof_points or [],
                stat_highlights=stat_highlights or [],
                process_steps=process_steps or [],
                slides=slides or [],
                user_prompt=user_prompt,
                visual_mood=visual_mood,
                color_behavior=color_behavior,
                initial_prompt=initial_prompt,
                canvas=canvas,
            )

        return self._build_static_prompt(
            brand_name=brand_name,
            headline=copy_headline,
            supporting_line=supporting_line,
            body=copy_body,
            cta=cta,
            user_prompt=user_prompt,
            visual_mood=visual_mood,
            color_behavior=color_behavior,
            platform=platform,
            sections=infographic_sections or [],
            customer_quote=customer_quote,
            customer_name=customer_name,
            layout_type=layout_type,
            canvas=canvas,
        )

    def _build_carousel_prompt(
        self,
        *,
        brand_name: str,
        headline: str,
        supporting_line: str,
        body: str,
        cta: str,
        hook: str,
        story_flow: list[str],
        proof_points: list[str],
        stat_highlights: list[str],
        process_steps: list[str],
        slides: list[dict],
        user_prompt: str,
        visual_mood: str,
        color_behavior: str,
        initial_prompt: str,
        canvas: str = "1080x1350 4:5 portrait",
    ) -> str:
        story = "\n".join(f"- {b}" for b in (story_flow or [])[:5]) or "- (derive from headline/body)"
        proofs = "\n".join(f"- {p}" for p in (proof_points or [])[:5]) or "- (omit if empty)"
        stats = "\n".join(f"- {s}" for s in (stat_highlights or [])[:4]) or "- (omit if empty)"
        steps = "\n".join(f"- {s}" for s in (process_steps or [])[:4]) or "- (omit if empty)"
        slides_block = "\n".join(
            f"Slide {s.get('slide_number', i+1)} [{s.get('role', 'insight')}]: "
            f"headline={s.get('headline', '')}; body={s.get('body', '')}; cta={s.get('cta') or ''}"
            for i, s in enumerate((slides or [])[:8])
        ) or "Use headline/body/cta as a single educational slide."

        user_block = f'\nUSER TOPIC REQUEST:\n"{user_prompt}"\n' if user_prompt else ""

        return f"""Create ONE finished LinkedIn educational CAROUSEL SLIDE matching this locked sample design system.

{CAROUSEL_AUDIENCE_TONE_LOCK}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CANVAS BOUNDARY LOCK (NON-NEGOTIABLE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Canvas: {canvas}.
ABSOLUTE BOUNDARY: Every pixel of every element (text, icon, chip, divider, CTA) MUST be
fully inside the canvas rectangle. Nothing may be cropped, clipped, or bleed off any edge.
Outer safe margin ≥6% on ALL four sides. Content that does not fit must be shortened or dropped.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LOCKED VISUAL SYSTEM (FROM SAMPLE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Canvas: {canvas}.
BACKGROUND (NON-NEGOTIABLE): Solid flat {self.CAROUSEL_BG} across the entire canvas.
- Same background color on every slide in the set. No gradients. No textured paper. No photo backgrounds. No pure white.
- NEVER pure black, charcoal, dark navy, or grainy dark backgrounds — instant fail.
Color accents: Navy text {self.NAVY}, body gray {self.BODY_GRAY}, orange divider accents {self.ORANGE}, gold metallic 3D accents {self.GOLD}, soft card tint {self.CARD_BLUE}.
{ICON_STYLE_LOCK}
{PREMIUM_HD_ICON_LOCK}
Icon style: ULTRA-PREMIUM HD clay-3D — 4K-sharp studio product renders, satin + gold accents, rich shadows
(NOT flat, NOT low-poly, NOT blurry, NOT washed-out). ONE tiny HD premium accent in corner (never giant hero cluster).
Typography: Bold navy sans-serif headline; readable supporting lines; all text baked sharply into the image. Perfect English spelling — never invent gibberish on props.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LOCKED LAYOUT STRUCTURE (TOP → BOTTOM)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1) TOP-RIGHT: tiny empty pocket only (~12%×7%) — do NOT draw any logo/wordmark AND do NOT write "{brand_name}" / JIRAAF as text. Real logo icon is composited later. Keep the full headline clear left/center — never clip it for the logo.
2) HEADLINE: MEDIUM bold navy (max 2 lines, ≤10 words) — never cut mid-word.
3) SUPPORTING LINE: one short answer / subhead.
4) CALLOUT BOX (optional): soft rounded ({self.CARD_BLUE}) — one short insight OR omit if crowded.
5) PREMIUM HD clay-3D avatar icons (~12–16% height) bottom-right — sharp studio render — NEVER omit, NEVER giant hero cluster.
6) DEPTH BLOCK: 2–3 white cards / rows with label + full explanation sentence each.
7) DIVIDER: thin horizontal orange line optional.
8) FOOTER SAFE ZONE (MANDATORY): leave bottom ~22% EMPTY ice-blue — do NOT bake SEBI text
   (exact legal footer is Pillow-composited after, same as logo — larger readable type).
   Content cards must never enter the footer zone.

{CAROUSEL_FIT_LOCK}
{CAROUSEL_SAMPLE_DNA_COMPACT}

Content must feel educational AND perfectly fitted — prefer less content that fits over more that breaks.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXACT COPY TO BAKE (verbatim — do not paraphrase)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Brand: {brand_name}
Hook: {hook or '(optional)'}
Headline: {headline}
Supporting line: {supporting_line or '(optional)'}
Body / callout source: {body}
CTA (use on closing slides only if provided): {cta or '(omit)'}
Storyline beats:
{story}
Proof / bottom-card labels source:
{proofs}
Stats:
{stats}
Process cues:
{steps}
Slide pack context (for multi-slide consistency — keep SAME background {self.CAROUSEL_BG}):
{slides_block}
Visual mood: {visual_mood}
Brand color behavior: {color_behavior}
{user_block}
Initial art direction (refine, do not ignore locked system):
{initial_prompt[:1200]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NON-NEGOTIABLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Background MUST be solid {self.CAROUSEL_BG} — identical slide-to-slide. NEVER black/charcoal.
2. Use multiple ULTRA-PREMIUM clay-3D icons — LARGE, sharp, high-detail; still leave SEBI footer room.
3. Bake all listed text as legible typography; no empty shells; no mid-word cuts; perfect spelling.
4. Hierarchy: headline → supporting → DEPTH explanation cards (most of slide) → tiny accents → SEBI footer.
5. No flat 2D clipart. No cheap low-poly blobs. No purple neon AI look. No watermark slogans.
6. NEVER draw logos or brand-name text (no JIRAAF letters) — tiny top-right pocket only.
7. NEVER invent SEBI/registration text in the image — leave bottom safe zone empty for post-composite.

Return ONLY the finished image-generation prompt."""

    def _build_infographic_prompt(
        self,
        *,
        brand_name: str,
        headline: str,
        supporting_line: str,
        body: str,
        cta: str,
        hook: str,
        story_flow: list[str],
        infographic_sections: list[dict],
        stat_highlights: list[str],
        proof_points: list[str],
        problem_statement: str,
        solution_statement: str,
        customer_quote: str,
        customer_name: str,
        process_steps: list[str],
        user_prompt: str,
        visual_mood: str,
        color_behavior: str,
        canvas: str = "1080x1350 4:5 portrait",
        layout_type: str = "",
    ) -> str:
        title = headline or "Untitled"
        subtitle = supporting_line or ""
        layout_type = str(layout_type or "").strip()
        from app.prompts.jiraaf_layout import is_trade_data_board

        is_rank = layout_type == "static_ranking"
        is_hub = layout_type == "static_hub_facts"
        is_education = layout_type == "carousel_story" or (
            not is_rank and not is_hub
        )

        rows = []
        for i, sec in enumerate((infographic_sections or [])[:15], start=1):
            label = sec.get("section_label") or f"Item {i}"
            stat = sec.get("stat") or ""
            includes = sec.get("includes") or []
            if isinstance(includes, list):
                includes_txt = "; ".join(str(x) for x in includes[:2])
            else:
                includes_txt = str(includes)
            body_sec = (sec.get("body") or "").strip()
            if len(body_sec.split()) > 8:
                body_sec = ""
            icon = sec.get("icon_hint") or ("flag/metric icon" if is_rank else "clay-3D topic icon")

            if is_education:
                sub_lines = []
                if isinstance(includes, list):
                    for inc in includes[:3]:
                        sub_lines.append(f"    - {inc}")
                rows.append(
                    f'SECTION {i}: "{label}"'
                    + (("\n" + "\n".join(sub_lines)) if sub_lines else "")
                    + (f'\n    callout: {body_sec}' if body_sec else "")
                )
            else:
                rows.append(
                    f"RANK {i}: {label}"
                    f"{f' | {stat}' if stat else ''}"
                    f"{f' | {includes_txt}' if includes_txt else ''}"
                    f"{f' | note: {body_sec}' if body_sec else ''}"
                    f" | icon: {icon}"
                )

        if is_education:
            rows_text = "\n".join(rows) or (
                "Build DENSE sample-style sections: orange bars + 3-col UNIQUE fact cards + callout — NOT sparse poster."
            )
        else:
            rows_text = "\n".join(rows) or (
                "Build ranked rows from the topic data — NOT benefit cards."
            )

        stats = "\n".join(f"- {s}" for s in (stat_highlights or [])[:5]) or "- (optional)"
        proofs = "\n".join(f"- {p}" for p in (proof_points or [])[:5]) or "- (optional)"
        objectives = "\n".join(f"- {s}" for s in (process_steps or proof_points or [])[:4]) or (
            "- Section 1: Why it matters\n- Section 2: How it works\n- Section 3: What to watch"
        )
        note = customer_quote or ""
        user_block = f'\nUSER TOPIC REQUEST:\n"{user_prompt}"\n' if user_prompt else ""

        if is_rank and is_trade_data_board(user_prompt or ""):
            layout_section = f"""LOCKED LAYOUT — TRADE DEFICIT DATA BOARD (layout_type=static_ranking):
{INFOGRAPHIC_TRADE_BOARD_LOCK}
Match the Jiraaf India–Russia sample EXACTLY:
1) Tiny empty top-right pocket
2) Punchy PLAIN data headline + one soft subtitle
3) Column headers: EXPORT | TRADE BALANCE | IMPORT (Billion USD)
4) Fiscal-year rows: orange export bars LEFT | balance CENTER | navy import bars RIGHT
5) Bottom white box: "What India buys most from …" — category + USD Bn lines
6) Source line if provided
FORBIDDEN: bond benefit cards, handshake/FD briefcase, technical sidebars, wrong flags."""
        elif is_rank:
            layout_section = f"""LOCKED LAYOUT — RANKING LIST (layout_type=static_ranking):
{INFOGRAPHIC_RANKING_FORMAT_LOCK}
Premium AI look identical to static Top Countries sample: glossy 3D flags + coin icons.
Currency: ₹ / ¥ / USD letters / % — NEVER $ / US $
Language like: "Top investor in India" / "Strong economic ties" — NOT textbook essays."""
        elif is_hub:
            layout_section = """LOCKED LAYOUT — HUB + SHORT FACTS (layout_type=static_hub_facts):
Center hub + 4–5 bank/rule fact cards with distinct clay-3D icons."""
        else:
            layout_section = f"""LOCKED LAYOUT — DENSE INFOGRAPHIC EXPLAIN (layout_type=carousel_story):
{INFOGRAPHIC_EXPLAIN_LAYOUT_LOCK}
{INFOGRAPHIC_EXPLAIN_ORANGE_STUB}
{INFOGRAPHIC_EXPLAIN_QUALITY_LOCK}
{ORANGE_COVERAGE_LOCK}
Match sample_infographic_explain_rbi_polymer.png EXACTLY:
1) Navy headline (NOT oversized) + gray intro with ₹/% fact
2) Orange-bar section + 3 circular-icon fact columns with real explanations
3) Orange-bar section + orange highlight words + 3 clay-3D fact columns
4) Orange-bar text section (short paragraphs)
5) Thin orange-border callout + lightbulb (NOT solid orange slab)
6) Source footer · empty top-right logo pocket
FAIL if: sparse giant-headline poster, empty ice-blue void, typos, ranking rows"""

        return f"""Create ONE finished LinkedIn educational INFOGRAPHIC matching Jiraaf sample tone.

{INFOGRAPHIC_AUDIENCE_TONE_LOCK}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CANVAS BOUNDARY LOCK (NON-NEGOTIABLE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Canvas: {canvas}.
ABSOLUTE BOUNDARY: Every pixel of every element (headline, icon, bar, card, source line) MUST be
fully inside the canvas rectangle. Nothing may bleed, clip, or extend past any edge.
Safe margin ≥6% on ALL four sides. If content does not fit, shorten labels or drop optional rows.
No mid-word breaks. Perfect spelling (USD not ESD; Import not Emp; UAE not HAE).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LOCKED VISUAL SYSTEM (FROM JIRAAF SAMPLES)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Canvas: {canvas}.
BACKGROUND: Soft off-white / light ice-blue {self.INFO_BG}. Clean, airy, premium.
NEVER pure black, charcoal, dark navy, grainy, or textured dark backgrounds.
Colors: Navy headings {self.NAVY}, body {self.BODY_GRAY}, REQUIRED orange accents {self.ORANGE}, gold {self.GOLD}. Never navy-only.
{ORANGE_COVERAGE_LOCK}
{ICON_STYLE_LOCK}
Typography: Bold navy sans headlines; short labels. ALL text baked into pixels. Perfect spelling.
CTA (if any): COMPACT ≤28% width, ≤4.5% height, 2–4 words — never a wide paragraph button.
{STATIC_IMAGE_EXTRA_LOCKS}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{layout_section}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXACT COPY TO BAKE (verbatim — keep short + simple)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Brand: {brand_name}
Hook: {hook or title}
Headline: {title}
Supporting / subtitle: {subtitle or body}
Body (use ONLY if short; else omit visually): {body}
Problem: {problem_statement or '(omit)'}
Solution: {solution_statement or '(omit)'}
Storyline:
{chr(10).join(f"{i}. {b}" for i, b in enumerate((story_flow or [])[:6], start=1)) or "1. Hook\n2. Explain\n3. CTA"}
{"Section blocks (heading + sub-points):" if is_education else "Rank / data rows (label first):"}
{rows_text}
Stats:
{stats}
Proof points:
{proofs}
Objective strip labels:
{objectives}
CTA / source / banner: {cta or '(short CTA ≤4 words for education; Source line only if ranking)'}
Note box: {note or '(omit note box if empty)'}
Quote attribution: {customer_name or ''}
Visual mood: {visual_mood}
Brand color behavior: {color_behavior}
{user_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NON-NEGOTIABLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. layout_type={layout_type or 'auto'} — follow the LOCKED LAYOUT above; do NOT switch to ranking for explain topics.
2. Bake exact short strings; never paraphrase into heavier textbook wording.
3. Spelling perfect — never invent gibberish on cards (USD/Import/UAE correct).
4. Brand colours: navy {self.NAVY} + REQUIRED visible orange {self.ORANGE} accents.
{ORANGE_COVERAGE_LOCK}
5. India market: ₹/% only when numbers belong; never invent foreign yield comparison tables.
6. NEVER invent country flags / India-USA-Germany-Japan boards for education prompts.
{UNIVERSAL_FIT_LOCK}
7. NEVER draw logos/wordmarks or brand-name text (no JIRAAF) — tiny top-right pocket only.
8. No purple neon AI aesthetic. No empty shells. No text breaking / mid-word cuts.
9. {NO_SEBI_STATIC_RULE}

Return ONLY the finished image-generation prompt."""

    def _build_static_prompt(
        self,
        *,
        brand_name: str,
        headline: str,
        supporting_line: str,
        body: str,
        cta: str,
        user_prompt: str,
        visual_mood: str,
        color_behavior: str,
        platform: str,
        sections: list[dict] | None = None,
        customer_quote: str = "",
        customer_name: str = "",
        layout_type: str = "",
        canvas: str = "",
    ) -> str:
        # Use canvas from size_string if not passed in
        if not canvas:
            canvas = canvas_label("static", platform)
        ratio = canvas
        user_block = f'\nUSER TOPIC REQUEST:\n"{user_prompt}"\n' if user_prompt else ""
        topic = (user_prompt or "").lower()
        layout_type = str(layout_type or "").strip()
        is_bank_hub = layout_type == "static_hub_facts" or any(
            k in topic
            for k in (
                "penalty",
                "penalties",
                "top 5 bank",
                "top five bank",
                "key rules",
                "fd penalty",
                "premature withdrawal",
            )
        )
        # NEVER treat ranking / country lists as bank hub just because section count >= 4
        if layout_type == "static_ranking":
            is_bank_hub = False

        from app.prompts.jiraaf_layout import requested_rank_count

        # BUG FIX: do NOT hard-slice to 5 — that killed "top 10" rankings.
        # Hub stays at most 5 banks; ranking uses user top-N or all provided rows (cap 15).
        rank_n = requested_rank_count(user_prompt)
        if layout_type == "static_ranking":
            row_limit = rank_n or min(max(len(sections or []), 1), 15)
        elif is_bank_hub:
            row_limit = 5
        else:
            row_limit = min(max(len(sections or []), 1), 15)

        rows = []
        is_education = layout_type == "carousel_story" and not is_bank_hub
        for i, sec in enumerate((sections or [])[:row_limit], start=1):
            label = sec.get("section_label") or f"Item {i}"
            includes = sec.get("includes") or []
            if isinstance(includes, list):
                fact_parts = [str(x).strip() for x in includes[:2] if str(x).strip()]
            else:
                fact_parts = [str(includes).strip()] if str(includes).strip() else []
            quoted_bits = []
            for f in fact_parts:
                short = " ".join(f.replace("£", "₹").split()[:12])
                quoted_bits.append(f'"{short}"')
            quoted = " | ".join(quoted_bits) or '"(no extra line)"'
            if is_bank_hub:
                rows.append(f'{i}. Bank name "{label}" — facts: {quoted}')
            elif is_education:
                rows.append(f'{i}. HEADING "{label}" — explanation: {quoted}')
            else:
                rows.append(f'{i}. Row name "{label}" — facts: {quoted}')
        rows_text = "\n".join(rows)

        if is_bank_hub and rows_text:
            return f"""Create a finished premium LinkedIn/social STATIC creative matching the Jiraaf
BANK PENALTY RATES SAMPLE (hub + short fact cards WITH ICONS) — NOT a teaser ad.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CANVAS BOUNDARY LOCK (NON-NEGOTIABLE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Canvas: {ratio}.
ABSOLUTE BOUNDARY: Every pixel of every element (hub, cards, icons, text) MUST be
fully inside the {ratio} canvas. Nothing may bleed, clip, or extend past any edge.
Safe margin ≥6% on ALL four sides.
Background: clean solid ice-blue {self.INFO_BG} — NO texture stamps, NO ghost watermarks.
Brand colours REQUIRED: navy {self.NAVY} headlines + visible orange {self.ORANGE} accents.
{ORANGE_COVERAGE_LOCK}
{ICON_STYLE_LOCK}

FORBIDDEN (instant fail if present):
- Any watermark / translucent brand shape / giant letter J / giraffe
- Invented lines like "Follow Jiraaf…" / "Follow JIRAAF for more…"
- Drawing a fake brand wordmark (real Brand Space logo is composited later — leave top-right pocket empty)
- Text-only fact cards with no icons
- Official trademark bank logos (Axis/SBI/HDFC/ICICI/PNB logo marks) — AI ruins trademarks
- Cheap low-poly / washed-out / tiny icons

Logo pocket: leave ONLY a tiny empty top-right corner (~10%×6%) blank — real Brand Space
icon is composited later. Do not draw anything there.

LOCKED LAYOUT (HUB + 5 ICON FACT CARDS):
1) Top: bold navy title (exact headline) — fully visible, never clipped
2) Optional ONE short supporting line under title (exact) — perfect spelling
3) Center: circular hub with a LARGE ULTRA-PREMIUM clay-3D classical bank building
4) FIVE white rounded fact cards around the hub, connected by thin lines
5) EACH card MUST include:
   - A LARGE distinct ULTRA-PREMIUM clay-3D icon (different per bank: vault, coin stack, shield,
     modern bank, card stack) — high detail, studio lighting — icons are mandatory
   - Exact bank name as clean typography
   - ONLY the exact 1–2 short fact lines listed below (letter-perfect) — NO invented words
6) {NO_SEBI_STATIC_RULE}
7) NO fake testimonial. NO teaser CTA replacing the data.
Use full canvas — no empty legal strip.

Exact title: "{headline}"
Supporting (optional): "{supporting_line}"
CTA (optional, omit if empty): "{cta}"

Exact fact cards — bake ONLY these strings, letter-perfect; use ₹ and % as written (never £):
{rows_text}

FAIL if any card shows gibberish, invented sentences, or misspellings.

Mood: {visual_mood}
Colors: navy {self.NAVY} + REQUIRED orange {self.ORANGE} accents on {self.INFO_BG}
{ORANGE_COVERAGE_LOCK}
{user_block}

Return ONLY the finished image-generation prompt."""

        # Education / explain poster — headings + explanation cards (NOT ranking)
        education_block = ""
        if layout_type == "carousel_story" and not is_bank_hub:
            education_block = f"""
LAYOUT LOCK — STATIC EXPLAIN POSTER (layout_type=carousel_story on static):
{STATIC_EXPLAIN_LAYOUT_LOCK}
{STATIC_EXPLAIN_QUALITY_LOCK}
{STATIC_ORANGE_STUB}
Canvas: {ratio}. Soft ice-blue {self.INFO_BG}.
- Bold navy headline + supporting line — fully baked
- ONE premium clay-3D hero + 3–5 cards (icon + heading + explanation each)
- Orange dividers + orange CTA button
Exact cards (letter-perfect, no missing text):
{rows_text or '(use sections below)'}
"""

        # Ranking / general static — keep text baked in (integrated), exact strings locked
        ranking_block = ""
        if layout_type == "static_ranking" and rows_text:
            from app.prompts.jiraaf_layout import is_trade_data_board

            if is_trade_data_board(user_prompt or ""):
                ranking_block = f"""
LAYOUT LOCK — TRADE DEFICIT DATA BOARD (match Jiraaf India–Russia sample, NOT bond poster):
Canvas: {ratio}.
ABSOLUTE BOUNDARY: every element fully inside the canvas — nothing clips or bleeds past edges.
Background: soft off-white / ice-blue {self.INFO_BG}.
Top: punchy headline + one factual subtitle ONLY.
Main: aligned dual-bar table —
  headers EXPORT (orange bars, left) | TRADE BALANCE (center numbers) | IMPORT (navy bars, right)
  Unit: Billion USD. One row per fiscal year from the data below.
Bar lengths must visually match the numbers (imports much longer when deficit is large).
Bottom white rounded box: "What India buys most from …" with category + USD amounts from data.
Source footer line from research.
FORBIDDEN: clay handshake, FD briefcase, Capital Preservation, Regular Income, Liquidity Management,
bond benefit cards, fake flags, investment product CTAs.
Exact year / category rows (bake letter-perfect):
{rows_text}
"""
            else:
                from app.prompts.jiraaf_layout import static_ranking_style

                if static_ranking_style(user_prompt or "") == "horizontal_bar":
                    ranking_block = f"""
LAYOUT LOCK — STATIC HORIZONTAL BAR (sample_static_oil_consumption_bars.png):
{STATIC_HORIZONTAL_BAR_DNA_LOCK}
{STATIC_HORIZONTAL_BAR_IMAGE_STUB}
{STATIC_RANKING_INSIGHT_LOCK}
{STATIC_ORANGE_STUB}
Canvas: {ratio}. Horizontal bars: COUNTRY | flag | bar | value inside | % outside.
Highlight India/focal country in ORANGE bar. Orange arrow → insight text if provided below.
Clay-3D oil barrels bottom-right. Source footer. Bake ALL rows — no stacked white cards.
Exact bar rows + insight (letter-perfect):
{rows_text}
{customer_quote or ''}
"""
                else:
                    ranking_block = f"""
LAYOUT LOCK — STATIC VERTICAL COUNTRY RANKING (UNCHANGED — sample_top_countries_investing.png):
{RANKING_IMAGE_STUB}
{STATIC_ORANGE_STUB}
Canvas: {ratio}. Orange rank badges, flags, amounts, coin icons — bake ALL row text.
Exact ranked rows (letter-perfect):
{rows_text}
"""

        return f"""Create a finished premium LinkedIn/social STATIC creative matching Jiraaf sample DNA.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CANVAS BOUNDARY LOCK (NON-NEGOTIABLE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Canvas: {ratio}.
ABSOLUTE BOUNDARY: Every pixel of every element (headline, icon, card, CTA, source line) MUST be
fully inside the {ratio} canvas. Nothing may bleed, clip, or extend past any edge.
Safe margin ≥6% on ALL four sides. Shorten or drop content before clipping occurs.

Background: solid ice-blue {self.CAROUSEL_BG} or soft {self.INFO_BG} — NEVER dark navy / black.
Style: premium fintech creative with glossy 3D accents + sharp baked typography (like Top Countries sample).
Brand colours REQUIRED: navy {self.NAVY} + visible orange accents {self.ORANGE}.
{ORANGE_COVERAGE_LOCK}
{STATIC_ORANGE_STUB}
{STATIC_IMAGE_EXTRA_LOCKS}
Logo: tiny top-right empty pocket only — never draw brand-name text.
Layout: Bold large headline, supporting line, ranked rows OR fact cards, compact CTA.
{education_block}
{ranking_block}
If sections/facts are provided below and this is NOT a ranking, prefer education cards or hub layout.
{NO_SEBI_STATIC_RULE}
Never use $ or US $ — prefer ₹ / ¥ / USD letters / %.

Exact text (bake letter-perfect — never invent gibberish):
Headline: {headline}
Supporting: {supporting_line}
Body: {body}
CTA: {cta}
Quote (omit if empty): {customer_quote} {customer_name}
Fact / rank rows:
{rows_text or '(none)'}
Mood: {visual_mood}
Colors: {color_behavior} — must include orange {self.ORANGE}
{user_block}

Return ONLY the finished image-generation prompt."""
