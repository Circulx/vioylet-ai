from __future__ import annotations

from typing import Any

from app.graph.models.layer2_models import BrandIntelligenceOutput
from app.graph.models.layer6_models import FormatPlanOutput
from app.graph.models.layer7_models import CopyOutput
from app.prompts.base import BasePromptBuilder


class VisualReasoningPromptBuilder(BasePromptBuilder):
    """Layer 8 Visual Reasoning — prompts rebuilt from Jiraaf-grade sample creatives."""

    PROMPT_VERSION = "4.0-jiraaf-samples"

    # Locked design tokens from sample carousel + infographic
    CAROUSEL_BG = "#E8F2FA"  # solid light cool blue — MUST stay identical across slides
    INFO_BG = "#F7F8FA"  # soft off-white / light gray
    NAVY = "#0B2C5F"
    BODY_GRAY = "#4A5568"
    ORANGE = "#F59A23"
    GOLD = "#E8B84A"
    CARD_BLUE = "#D6E8F7"
    BANNER_NAVY = "#123A6B"

    def build_system(self, fmt: str = "", **kwargs: Any) -> str:
        if fmt == "carousel":
            format_instructions = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAROUSEL — SAMPLE DESIGN SYSTEM (LOCKED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Canvas: 1080x1350 portrait (4:5) educational LinkedIn carousel slide.
Background: SOLID {self.CAROUSEL_BG} across EVERY slide — same hex, no gradients, no photo BGs, no white swaps.
Style: Clean corporate fintech education. Ultra-premium glossy 3D icons (soft studio lighting, reflections, soft drop shadows).
Typography: Bold navy ({self.NAVY}) sans-serif headlines; medium gray ({self.BODY_GRAY}) supporting copy; ALL copy baked into pixels.

SLIDE ANATOMY (top → bottom):
1. TOP-RIGHT: tiny empty pocket only (~12%×7%) — NEVER draw logo/wordmark OR brand-name text (e.g. JIRAAF). Keep headline fully visible left/center.
2. Large centered question / headline in bold navy.
3. One supporting answer sentence under it.
4. Soft rounded callout pill/box ({self.CARD_BLUE}) with a deeper insight sentence.
5. LARGE central 3D hero cluster (2–4 ultra-premium 3D objects that illustrate the topic — e.g. bank + shield + gold coins).
6. Thin orange-accent divider with a short connector phrase in the middle.
7. THREE equal rounded cards in a row — each with a unique ultra-3D icon + short bold label (deeper consequence / insight).
8. Tiny disclaimer line at very bottom if provided.

RULES:
- Multiple 3D objects required (never a single lonely icon).
- Deeper educational content — not sparse marketing fluff.
- Bake exact approved blueprint text; do not invent alternate headlines.
- Keep generous margins; no clipping; fully legible type.
- NEVER draw logo/wordmark/brand-name text (no JIRAAF letters) — tiny top-right pocket only; headline must not clip.
- Every baked word must be spelled correctly (character-accurate).
"""
        elif fmt == "infographic":
            format_instructions = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INFOGRAPHIC — SAMPLE DESIGN SYSTEM (LOCKED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Canvas: 1080x1350 portrait LinkedIn educational poster.
Background: Soft off-white {self.INFO_BG} (not pure stark white clutter).
Style: Dense, structured, premium fintech education. Ultra-premium glossy 3D icons throughout.
Typography: Bold navy headings, orange italic section accents, readable dark body — ALL baked into pixels.

POSTER ANATOMY (top → bottom storyline):
1. TOP-RIGHT: tiny empty pocket only (~12%×7%) — NEVER draw logo/wordmark OR brand-name text (e.g. JIRAAF). Keep headline fully visible left/center.
2. HOOK HEADLINE — bold navy question or bold claim + curiosity line.
3. INTRO paragraph (left) + hero ultra-3D cluster (right): 3–5 related 3D objects (safe, piggy, coins, plant, charts).
4. SECTION TITLE + orange italic sub-label (e.g. "Invested Across Multiple Asset Classes").
5. STRUCTURED ROWS / GRID (3–5 rows). Each row:
   - Left: ultra-3D category icon
   - Title (+ optional % / stat) in bold navy
   - Middle: "What it includes" style bullets
   - Right: short "why it matters" body
   Separated by thin light dividers.
6. DARK NAVY rounded CTA / objective BANNER with white text (exact CTA or objective line).
7. 3–4 objective icons in a horizontal strip with short labels under each.
8. Soft amber NOTE box with lightbulb icon + note text when provided.
9. Tiny legal/disclaimer footer if provided.

RULES:
- Storyline must read: Hook → Explanation → Structured breakdown → Objective/CTA → Note.
- Ultra 3D premium icons on every row — content-specific, glossy, consistent lighting family.
- Bake exact approved blueprint strings; deep content density like a real LinkedIn education post.
- No empty shells. No flat 2D clipart. No purple AI aesthetic.
- NEVER draw logos/wordmarks or brand-name text (no JIRAAF) — tiny top-right pocket only.
- Spelling of every baked word must be perfect.
"""
        else:
            format_instructions = f"""
STATIC SOCIAL FORMAT:
- Canvas 1200x627 (LinkedIn) or 1080x1080 (Instagram).
- Background light cool blue {self.CAROUSEL_BG} or soft off-white.
- Ultra-premium 3D hero cluster + baked headline / supporting line / CTA in navy typography.
- Tiny TOP-RIGHT pocket only for Brand Space logo compositing — never AI-draw logo or brand-name text.
- Perfect spelling on all baked text. Clean corporate fintech education aesthetic.
"""

        return f"""You are Violyt's Visual Reasoning Engine. Plan composition for a finished AI image with baked-in typography.
Return ONE JSON object matching VisualReasoningOutput EXACTLY — every required key below must be present.

CRITICAL:
- dominant_visual_system: generated_image | type_led | illustration | infographic | data_visual | product_visual
- visual_format_type: comparison | timeline | chart | matrix | process_flow | hero_scene | data_grid
- Bake approved Creative Blueprint copy into the image as sharp typography (exact strings).
- Prefer ultra-premium glossy 3D iconography matching high-end fintech LinkedIn education posts.
- NEVER draw logos/wordmarks or brand-name text (no JIRAAF letters); Brand Space logo is composited later into a tiny top-right pocket.
- Spelling of every planned text string must be perfect.
- generated_image_url must be "".
- image_prompt_direction: 600–900 words describing layout, 3D icons, colors, AND exact text to render.

REQUIRED JSON SHAPE (fill every field; do not rename keys):
{{
  "dominant_visual_system": "infographic",
  "visual_format_type": "data_grid",
  "visual_style": "Premium corporate educational creative with ultra-glossy 3D icons",
  "composition_logic": "Top-down educational hierarchy with hero visual and structured rows",
  "focal_point": "Central ultra-premium 3D icon cluster",
  "negative_space_plan": "Generous margins; tiny logo-safe top-right pocket only — headline fully clear",
  "color_behavior": "Navy typography on light cool background with orange/gold accents",
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
        colors = f"Primary: {brand_intelligence.visual_behavior.color_behavior}"
        mood = brand_intelligence.visual_behavior.visual_mood
        logo_zone = brand_intelligence.visual_behavior.logo_zone_instruction
        user_prompt_section = (
            f"\nUSER ORIGINAL PROMPT (primary topic direction):\n{user_prompt}\n" if user_prompt else ""
        )

        if fmt == "carousel":
            text_directive = (
                f"Follow the LOCKED carousel sample system: solid background {self.CAROUSEL_BG}, "
                "ultra-premium multi-object 3D hero, callout box, 3 bottom insight cards, baked text."
            )
        elif fmt == "infographic":
            text_directive = (
                f"Follow the LOCKED infographic sample system: soft bg {self.INFO_BG}, hook headline, "
                "hero 3D cluster, structured multi-row breakdown, navy CTA banner, objective icons, note box."
            )
        else:
            text_directive = (
                "Bake approved headline/supporting/CTA as sharp typography; use ultra-premium 3D icons."
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
Think like a world-class fintech art director. Plan a content-rich educational layout with ultra-premium 3D icons.
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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LOCKED VISUAL SYSTEM (FROM SAMPLE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Canvas: 1080x1350 portrait (4:5).
BACKGROUND (NON-NEGOTIABLE): Solid flat {self.CAROUSEL_BG} across the entire canvas.
- Same background color on every slide in the set. No gradients. No textured paper. No photo backgrounds. No pure white.
Color accents: Navy text {self.NAVY}, body gray {self.BODY_GRAY}, orange divider accents {self.ORANGE}, gold metallic 3D accents {self.GOLD}, soft card tint {self.CARD_BLUE}.
Icon style: ULTRA-PREMIUM GLOSSY 3D — studio lighting, soft contact shadows, reflective materials, high detail. Multiple 3D objects in the hero (never one lonely icon). Content-specific metaphors only.
Typography: Bold navy sans-serif headline; readable supporting lines; all text baked sharply into the image.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LOCKED LAYOUT STRUCTURE (TOP → BOTTOM)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1) TOP-RIGHT: tiny empty pocket only (~12%×7%) — do NOT draw any logo/wordmark AND do NOT write "{brand_name}" / JIRAAF as text. Real logo icon is composited later. Keep the full headline clear left/center — never clip it for the logo.
2) HEADLINE: large, bold, centered navy question or claim.
3) SUPPORTING LINE: one clear answer / subhead under the headline.
4) CALLOUT BOX: soft rounded rectangle ({self.CARD_BLUE}) with a deeper insight sentence (from body / hook).
5) HERO 3D CLUSTER: large centered group of 2–4 ultra-premium 3D objects that visualize the topic (examples from sample language: classical bank building + golden shield with lock + stacks of gold coins with currency mark; or charts + warning triangle + percent badge — choose metaphors that match THIS topic).
6) DIVIDER: thin horizontal line with orange end-caps and a short centered connector phrase (from storyline / body).
7) THREE EQUAL BOTTOM CARDS: rounded soft-blue cards in a row. Each card = unique ultra-3D icon + short bold navy label (deeper consequences / insights / proof points).
8) FOOTER: optional tiny gray disclaimer if claim-safety text exists.

Content must feel DEEP and educational — like a real finance literacy carousel — not sparse marketing fluff.

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
1. Background MUST be solid {self.CAROUSEL_BG} — identical slide-to-slide.
2. Use multiple ultra-premium 3D icons/objects — glossy, consistent family.
3. Bake all listed text as legible typography; no empty shells.
4. Deep content hierarchy: question → answer → insight callout → hero → 3 insight cards.
5. No flat 2D clipart. No purple neon AI look. No watermark text inventing brand slogans.
6. NEVER draw logos or brand-name text (no JIRAAF letters) — tiny top-right pocket only. Perfect spelling on every baked word.

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
    ) -> str:
        title = headline or "Untitled"
        subtitle = supporting_line or ""
        story = "\n".join(f"{i}. {b}" for i, b in enumerate((story_flow or [])[:6], start=1)) or (
            "1. Hook question\n2. Explain mechanism\n3. Break down components\n4. State objective/CTA\n5. Add caution note"
        )

        rows = []
        for i, sec in enumerate((infographic_sections or [])[:5], start=1):
            label = sec.get("section_label") or f"Section {i}"
            stat = sec.get("stat") or ""
            includes = sec.get("includes") or []
            if isinstance(includes, list):
                includes_txt = "; ".join(str(x) for x in includes[:5])
            else:
                includes_txt = str(includes)
            body_sec = sec.get("body") or ""
            icon = sec.get("icon_hint") or "content-specific ultra-3D icon"
            rows.append(
                f"ROW {i}:\n"
                f"  Title: {label}{f' ({stat})' if stat else ''}\n"
                f"  Includes / bullets: {includes_txt or body_sec}\n"
                f"  Why it matters: {body_sec or '(use proof point)'}\n"
                f"  Icon hint: {icon}"
            )
        rows_text = "\n".join(rows) or (
            "Build 3–4 rows from body/proof_points with title + includes + why + unique 3D icon each."
        )

        stats = "\n".join(f"- {s}" for s in (stat_highlights or [])[:5]) or "- (optional)"
        proofs = "\n".join(f"- {p}" for p in (proof_points or [])[:5]) or "- (optional)"
        objectives = "\n".join(f"- {s}" for s in (process_steps or proof_points or [])[:4]) or (
            "- Capital Preservation\n- Regular Income\n- Long-term Wealth Creation\n- Liquidity Management"
        )
        note = customer_quote or ""
        user_block = f'\nUSER TOPIC REQUEST:\n"{user_prompt}"\n' if user_prompt else ""

        return f"""Create ONE finished LinkedIn educational INFOGRAPHIC matching this locked sample design system.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LOCKED VISUAL SYSTEM (FROM SAMPLE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Canvas: 1080x1350 portrait.
BACKGROUND: Soft off-white / light gray {self.INFO_BG}. Clean, airy, premium — not busy, not pure stark white glare.
Colors: Navy headings {self.NAVY}, body {self.BODY_GRAY}, orange/gold accents {self.ORANGE}/{self.GOLD}, dark navy banner {self.BANNER_NAVY}, soft amber note box.
Icon style: ULTRA-PREMIUM GLOSSY 3D icons — safe/vault, piggy bank, coins, classical building, sealed document, pie chart, money bag, shield, plant, charts — choose metaphors that match THIS topic. Same lighting family. Soft shadows. High detail.
Typography: Bold navy sans for headlines; medium gray for intros; orange italic for section sub-labels; white text on navy CTA banner. ALL text baked into pixels.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LOCKED STORYLINE + STRUCTURE (TOP → BOTTOM)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1) TOP-RIGHT must stay a tiny empty pocket — never draw logo/wordmark AND never write "{brand_name}" as text (composited later from Brand Space — logo icon only). Headline must stay fully readable.
2) HOOK HEADLINE (exact): bold navy, multi-line OK, curiosity-driven question or claim.
3) INTRO + HERO CLUSTER:
   - Left: short intro paragraph (supporting line / body).
   - Right: clustered ultra-3D premium objects (3–5) that visualize the topic.
4) SECTION HEADER: bold title + orange italic sub-label describing the breakdown.
5) STRUCTURED CONTENT GRID (3–5 horizontal rows with thin dividers). Each row has:
   - Ultra-3D category icon (left)
   - Bold title (+ percentage/stat when provided)
   - Bullets: what it includes
   - Short paragraph: why it matters
6) NAVY ROUNDED CTA / OBJECTIVE BANNER: exact CTA or objective sentence in white.
7) OBJECTIVE STRIP: 3–4 small premium icons in a row with short labels under each.
8) NOTE BOX: soft amber/cream rounded box with lightbulb icon + caution/note text when available.
9) Tiny gray disclaimer footer if claim-safety notes exist.

This must feel like a deep educational LinkedIn infographic — dense, structured, premium — not sparse marketing poster.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXACT COPY TO BAKE (verbatim)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Brand: {brand_name}
Hook: {hook or title}
Headline: {title}
Supporting / intro: {subtitle or body}
Body: {body}
Problem (optional callout): {problem_statement or '(omit)'}
Solution (optional callout): {solution_statement or '(omit)'}
Storyline:
{story}
Structured rows:
{rows_text}
Stats:
{stats}
Proof points:
{proofs}
Objective strip labels:
{objectives}
CTA / banner text: {cta or 'The objective is simple, but crucial'}
Note box: {note or '(omit note box if empty)'}
Quote attribution: {customer_name or ''}
Visual mood: {visual_mood}
Brand color behavior: {color_behavior}
{user_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NON-NEGOTIABLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Follow the sample structure: Hook → Intro+3D hero → Section title → Multi-row breakdown → Navy CTA banner → Objective icons → Note.
2. Ultra-premium glossy 3D icons on the hero AND every row — content-specific.
3. Bake exact strings as sharp typography; no empty shells; no paraphrased alternate headlines.
4. Deep content density with clear hierarchy and generous but organized whitespace.
5. No flat clipart. No purple neon AI aesthetic. No inventing legal claims.
6. NEVER draw logos/wordmarks or brand-name text (no JIRAAF) — tiny top-right pocket only. Spelling of every baked word must be perfect.

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
    ) -> str:
        ratio = "1080x1080" if (platform or "").lower() == "instagram" else "1200x627"
        user_block = f'\nUSER TOPIC REQUEST:\n"{user_prompt}"\n' if user_prompt else ""
        return f"""Create a finished premium LinkedIn/social STATIC creative.

Background: solid light cool blue {self.CAROUSEL_BG} or soft {self.INFO_BG}.
Style: Ultra-premium glossy 3D hero cluster + clean navy typography baked into the image.
Logo: tiny top-right icon pocket only for {brand_name} — never draw brand-name text.
Layout: Bold headline, supporting line, optional short body, clear CTA band, 1–3 supporting 3D icons.
Canvas: {ratio}.

Exact text:
Headline: {headline}
Supporting: {supporting_line}
Body: {body}
CTA: {cta}
Mood: {visual_mood}
Colors: {color_behavior}
{user_block}

Return ONLY the finished image-generation prompt."""
