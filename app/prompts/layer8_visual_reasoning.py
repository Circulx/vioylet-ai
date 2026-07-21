from __future__ import annotations

from typing import Any

from app.graph.models.layer2_models import BrandIntelligenceOutput
from app.graph.models.layer6_models import FormatPlanOutput
from app.graph.models.layer7_models import CopyOutput
from app.prompts.base import BasePromptBuilder


class VisualReasoningPromptBuilder(BasePromptBuilder):
    """Builds prompts for Layer 8: Visual Reasoning Engine."""

    PROMPT_VERSION = "3.0"

    def build_system(self, fmt: str = "", **kwargs: Any) -> str:
        """Return the core system instructions for planning the visual reasoning layout."""
        format_instructions = ""
        if fmt == "carousel":
            format_instructions = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAROUSEL FORMAT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Canvas size: 1080x1350 (4:5 Aspect Ratio).
- Background: Solid, complete light blue background (#EBF5FB) spanning the entire canvas.
- Logo Zone: Always reserve the top-right corner area (160x50 pixels, 56px padding) completely clean, empty, and free of any visual elements, details, or overlays so the logo can be composited safely.
- No text inside image: DALL-E must generate clean, photorealistic/3D layouts without text. Text will be overlaid programmatically later by the compositor.
- All elements must fit safely inside the 4:5 frame with absolutely no clipping or truncation.
"""
        elif fmt == "infographic":
            format_instructions = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MASTER INFOGRAPHIC DESIGN SYSTEM — STRICT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Canvas: 1080x1350 portrait, high resolution, vector illustration style.
No pixelation, no watercolor, no painterly effect, no 3D rendering, no comic style.
Use flat premium vector graphics only.

Brand Personality: Professional, Trustworthy, Educational, Premium, Minimal, Modern, Financial, Clean, Data-driven, Human-centered.
Target Audience: Retail Investors, HNIs, Young Professionals, Finance Enthusiasts.

DESIGN LANGUAGE (FIXED — never change):
- 12-column grid layout with large white margins and generous breathing space.
- Everything must have perfect alignment and spacing.
- Resembles premium LinkedIn carousel infographics from Stripe, HubSpot, McKinsey, Morning Brew, Visual Capitalist, Apple, Google.

BRAND COLORS (use exactly):
- Primary Purple: #33206F
- Secondary Orange: #F59A23
- Accent Yellow: #FFC857
- Dark Text: #222222
- Secondary Text: #5B5B5B
- Background: Pure White #FFFFFF
- Cards: #FAFAFC
- Borders: #ECECEC
- Success: #2EAF62
- Blue: #4F8EF7
- Gray: #9EA3AE

TYPOGRAPHY:
- Modern sans-serif (Inter, Manrope, SF Pro, Plus Jakarta Sans style).
- Bold very large headings, semi-bold subheadings, medium body, regular captions.
- Extremely clear text hierarchy. Perfect readability.

VISUAL STYLE:
- Premium flat illustrations. No gradients unless extremely subtle.
- Rounded corners (16-24px radius). Soft shadows. Large cards. Minimal outlines.
- Soft color palette. Friendly illustrations. Consistent stroke width.
- Rounded icons. Financial dashboard aesthetic. Clean and premium.

ICON STYLE:
- Outlined modern vector icons. Simple, minimal, uniform stroke.
- Finance-related: brain, chart, shield, coin, wallet, graph, calendar, document, target, checkmark, arrow, growth, investment, portfolio, risk, clock, goal.
- All icons from one visual family — same thickness, same corner radius, same style.

LAYOUT (top to bottom):
1. Top Section: Logo zone (top-right, 160x50px, 56px padding — keep completely clean, no drawn logo), Headline, Subheadline, Divider line, Main flat illustration.
2. Problem vs Solution Section: Two equal cards side-by-side. Left = Problem (illustration + pain points as real short text). Right = Solution (illustration + benefits + icons as real short text).
3. Feature Section: Five horizontal cards, each with icon + real title text + real short description text.
4. Metrics Section: 4-5 statistic cards with a large real number/stat + real supporting text + simple icon.
5. Customer Quote Section (only if a quote is supplied below): Rounded testimonial card with avatar circle + real quote text + real name text.
6. Process Section: 4-step timeline with minimal icons, arrows, and real step-label text.
7. CTA Section: brand-logo-safe area (leave empty for compositing) + real CTA text.

CARD STYLE: 16-24px radius, very light shadow, soft border, large padding, consistent spacing, equal width, perfect alignment.

ILLUSTRATIONS: Premium flat vector, friendly, corporate. No realism, no anime, no cartoon. Characters with simple faces, minimal expressions, clean shapes, soft colors.

SPACING: Extremely generous whitespace. Consistent margins and paddings. Nothing cramped.

TEXT RENDERING: This is a text-in-image infographic. Render all text content directly in the image as crisp, perfectly spelled typography. Only the top-right logo badge zone stays empty.
"""
        elif fmt == "banner":
            format_instructions = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BANNER FORMAT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Canvas size: 1200x628 landscape (web banner) or 728x90 (leaderboard) or 300x250 (medium rectangle).
- Logo Zone: Always reserve the top-right corner area (160x50 pixels, 56px padding) completely clean, empty, and free of any visual elements, details, or overlays so the logo can be composited safely.
- No text inside image: DALL-E must generate clean marketing creatives with no text, leaving clean negative space for programmatic text overlay.
- Strong visual focal point, minimal text density, clear CTA placement.
"""
        elif fmt == "newsletter":
            format_instructions = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NEWSLETTER FORMAT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Canvas size: 600x800 portrait (email-optimized width).
- Logo Zone: Reserve top-right corner (120x40 pixels, 24px padding) for logo compositing.
- No text inside image: Generate clean visual layout with negative space for programmatic text overlay.
- Multi-section visual hierarchy: header image → content blocks → CTA area.
- Clean, professional, email-safe design. Minimal complexity for small-screen rendering.
"""
        elif fmt == "blog":
            format_instructions = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BLOG FORMAT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Canvas size: 1200x630 landscape (blog header/hero image).
- Logo Zone: Reserve top-right corner (120x40 pixels, 24px padding) for logo compositing.
- No text inside image: Generate clean editorial hero visual with negative space for title overlay.
- Editorial, magazine-quality visual. Strong narrative imagery. Clean, sophisticated, readable.
"""
        elif fmt == "email":
            format_instructions = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMAIL FORMAT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Canvas size: 600x800 portrait (email-optimized width).
- Logo Zone: Reserve top-right corner (120x40 pixels, 24px padding) for logo compositing.
- No text inside image: Generate clean visual with negative space for programmatic text overlay.
- Direct response aesthetic. Clear visual hierarchy. Action-oriented. Email-safe design.
"""
        elif fmt == "presentation":
            format_instructions = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRESENTATION FORMAT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Canvas size: 1920x1080 landscape (16:9 presentation slide).
- Logo Zone: Reserve top-right corner (160x50 pixels, 48px padding) for logo compositing.
- No text inside image: Generate clean slide backgrounds with negative space for programmatic text overlay.
- Professional, corporate presentation aesthetic. Clean layouts, generous whitespace, strong visual hierarchy.
- Each slide should have ONE dominant visual element with ample negative space for text.
"""
        elif fmt == "ad_creative":
            format_instructions = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AD CREATIVE FORMAT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Canvas size: 1080x1080 square (social ad) or 1200x628 landscape (display ad).
- Logo Zone: Always reserve the top-right corner area (160x50 pixels, 56px padding) completely clean, empty, and free of any visual elements, details, or overlays so the logo can be composited safely.
- No text inside image: DALL-E must generate clean, high-impact marketing creatives with no text, leaving clean negative space for programmatic text overlay.
- Performance-optimized: strong focal point, emotional appeal, clear visual hierarchy, CTA-friendly composition.
"""
        else:
            format_instructions = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STATIC SOCIAL MEDIA FORMAT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Canvas size: 1200x627 landscape (LinkedIn/Twitter) or 1080x1080 square (Instagram).
- Logo Zone: Always reserve the top-right corner area (160x50 pixels, 56px padding) completely clean, empty, and free of any visual elements, details, or overlays so the logo can be composited safely.
- No text inside image: DALL-E must generate clean marketing creatives with no text, leaving clean negative space for programmatic text overlay.
"""

        base_prompt = """You are Violyt's Visual Reasoning Engine. Your job is to reason about composition, style, and imagery before any design is rendered.
You must return a single JSON object matching the VisualReasoningOutput schema.

CRITICAL RULES:
- Determine the correct dominant_visual_system based on the concept and brand behavior. It must be exactly one of: "generated_image", "type_led", "illustration", "infographic", "data_visual", "product_visual".
- Determine the correct visual_format_type based on the layout and context:
  * "comparison": when side-by-side or multi-item comparison is the focus.
  * "timeline": for sequential, historical, or chronological flows.
  * "chart": for quantitative, graph, or bar chart visuals.
  * "matrix": for 2x2 grids, quadrant maps, or tables.
  * "process_flow": for step-by-step sequences, loops, or paths.
  * "hero_scene": for a single cinematic, photorealistic 3D hero scene.
  * "data_grid": for structured dashboard-like grids.
- Refine the visual_style, composition_logic, focal_point, and negative_space_plan to achieve a professional design.
- Define a color_behavior that uses the brand's palette appropriately with hex codes.
- Logo Zone: Define where the logo must sit safely (e.g. 'top-right corner, 32px padding').
- DO NOT invent/fetch real image URLs in the LLM. Return an empty string "" for generated_image_url in the JSON.
- For the "infographic" format: the generated_image_prompt MUST describe a fully finished poster with text baked in. Only the top-right logo badge stays empty for later compositing.
- For all other formats, follow a strictly 'No text, no logos, no watermarks' rule in the generated_image_prompt. Typography and copy will be laid out cleanly on top of the blank space by the compositor.

CONTENT SECTIONS:
- Break down the core content elements into `content_sections` for structured compositing (e.g., column keys, titles, descriptions, metrics).

TEXT OVERLAY PLAN:
- Define exactly what text elements should be rendered, their font_size, color_hex, and position_box ("top-center", "bottom-left", "center-right", "footer-strip", "table-header", "table-row-1", etc.).
- Allowed element_type values: headline, subheadline, supporting_line, body, cta, label, footer, section_label, stat, badge.

IMAGE PROMPT DIRECTION:
- The image_prompt_direction you write will be sent to the Prompt Expander. Write a structured prompt of 600-900 words describing the visual layout, background, 3D shapes/icons, or illustrations. For "infographic" format, include the text content for each section. For all other formats, describe visuals only — no text.

JSON OUTPUT STRUCTURE:
{
  "dominant_visual_system": "generated_image",
  "visual_format_type": "comparison",
  "visual_style": "Minimalistic editorial layout with high contrast",
  "composition_logic": "Asymmetric layout with visual element on left and clean negative space on right",
  "focal_point": "The center visual element",
  "negative_space_plan": "Keep at least 40% margin on the right side for text overlay",
  "color_behavior": "Neutral background with brand primary and secondary accents",
  "logo_zone_instruction": "Top-right corner with 32px padding",
  "typography_behavior": "Bold editorial serif for titles, clean geometric sans-serif for body",
  "image_prompt_direction": "Visual Layout:\\n...\\nBackground:\\n...\\nVisual Metaphor & Icons:\\n...\\nStyle:\\n...\\nColor Palette:\\n...\\nNote: Do NOT draw text/labels.",
  "content_sections": [
    {
      "section_id": "item_1",
      "title": "Equities",
      "body": "High growth potential",
      "metric": "12%",
      "visual_metaphor": "3D rising green graph"
    }
  ],
  "text_overlay_plan": [
    {
      "element_type": "headline",
      "text": "The Power of compounding",
      "font_size": 42,
      "color_hex": "#0D1B3E",
      "position_box": "top-center"
    }
  ],
  "generated_image_url": ""
}

No preamble. No markdown code fences. Return ONLY raw JSON."""
        return base_prompt + format_instructions

    def build_user(
        self,
        brand_intelligence: BrandIntelligenceOutput,
        format_plan: FormatPlanOutput,
        copy: CopyOutput,
        concept: dict,
        user_prompt: str = "",
        **kwargs: Any,
    ) -> str:
        """Return the user prompt for the initial visual reasoning planning."""
        colors = f"Primary: {brand_intelligence.visual_behavior.color_behavior}"
        sophistication = brand_intelligence.visual_behavior.design_sophistication
        mood = brand_intelligence.visual_behavior.visual_mood
        logo_zone = brand_intelligence.visual_behavior.logo_zone_instruction

        user_prompt_section = ""
        if user_prompt:
            user_prompt_section = f"\nUSER ORIGINAL PROMPT/VISUAL REQUEST (USE THIS AS PRIMARY DIRECTION FOR METAPHOR AND DETAIL):\n{user_prompt}\n"

        fmt = kwargs.get("fmt", "static")
        text_directive = (
            "No text inside the image."
            if fmt != "infographic"
            else "Text-baked infographic: render all provided content as legible text in the image."
        )

        return f"""BRAND VISUAL SYSTEM CONTEXT:
Brand Name: {brand_intelligence.brand_core.brand_name}
Value Proposition: {brand_intelligence.brand_core.value_proposition}
Brand Stands For: {', '.join(brand_intelligence.brand_core.stands_for)}
Brand Stands Against: {', '.join(brand_intelligence.brand_core.stands_against)}
Visual Mood: {mood}
Design Sophistication: {sophistication}
Color Behavior: {colors}
Image Behavior: {brand_intelligence.visual_behavior.image_behavior}
Logo Zone Instruction: {logo_zone}
Typography Behavior Preference: {brand_intelligence.visual_behavior.typography_behavior}
Audience: {brand_intelligence.audience_model.primary_persona}
Audience Emotional Needs: {', '.join(brand_intelligence.audience_model.emotional_needs)}
{user_prompt_section}
CREATIVE CONCEPT & FORMAT:
Concept: {concept.get('concept_name', 'Default')}
Core Idea: {concept.get('core_idea', '')}
Hook: {concept.get('hook', '')}
Visual Angle Plan: {concept.get('visual_angle', '')}
Narrative Angle: {concept.get('narrative_angle', '')}
Layout Archetype: {format_plan.layout_archetype}
Format Strategy: {format_plan.format_strategy}
Copy Headline: {copy.headline}
Supporting Line: {copy.supporting_line or 'N/A'}
Copy Body: {copy.body}
CTA: {copy.cta}

SLIDE ROLES AND VISUAL INTENTIONS:
{chr(10).join([f"- Slide {s.slide_number}: role={s.role}, focus={s.focus}, visual_intent={s.visual_intent}" for s in format_plan.slide_plan])}

INSTRUCTION:
Think like a world-class art director and VFX supervisor. Plan a detailed, content-rich poster layout. Decide the placement of elements, section labels, color behaviors, and text overlay boxes. Make sure to reserve space for the brand logo in the top right corner. Specify the exact typography and spacing. {text_directive}

Return ONLY raw JSON."""

    def build_expander_system(
        self, dominant_visual_system: str = "generated_image", fmt: str = "static"
    ) -> str:
        """Return the system prompt for prompt expansion."""
        return """You are a professional AI Art Director. Your job is to transform a visual concept brief into an ULTRA-DETAILED, purely visual image-generation prompt for gpt-image-1.
Follow the designated template structure exactly, filling in every placeholder with specific, vivid detail derived from the brief.
No preamble, no explanation, no markdown headers in the final output — just the expanded prompt text ready to send to the image model."""

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
    ) -> str:
        """Select and fill one of the ten production-ready prompt templates."""
        topic = copy_headline or concept_name or "the brand message"
        goal = core_idea or supporting_line or copy_body[:120]
        primary_color = "Primary Purple (#33206F)"
        secondary_color = "Secondary Orange (#F59A23)"
        accent_color = "Accent Yellow (#FFC857)"

        layout_lower = (layout_archetype or "").lower()
        user_lower = (user_prompt or "").lower()
        platform_lower = (platform or "").lower()

        if fmt == "infographic":
            return self._build_infographic_prompt(
                brand_name=brand_name,
                headline=copy_headline,
                supporting_line=supporting_line,
                body=copy_body,
                cta=cta,
                infographic_sections=infographic_sections or [],
                stat_highlights=stat_highlights or [],
                problem_statement=problem_statement,
                solution_statement=solution_statement,
                customer_quote=customer_quote,
                customer_name=customer_name,
                process_steps=process_steps or [],
                user_prompt=user_prompt,
            )

        # ── Select template based on format + layout/content cues ──
        if fmt == "carousel":
            template_name = "carousel"
        else:
            if any(k in user_lower for k in ("ai", "technology", "artificial intelligence")):
                template_name = "ai_tech"
            elif platform_lower == "linkedin":
                template_name = "linkedin"
            elif "educat" in user_lower:
                template_name = "educational"
            elif "compar" in layout_lower or "versus" in user_lower:
                template_name = "comparison"
            else:
                template_name = "static"

        templates: dict[str, str] = {
            "static": (
                "Create a premium, photorealistic social media marketing image.\n\n"
                "Topic:\n{topic}\n\n"
                "Goal:\n{goal}\n\n"
                "Scene:\nA high-end modern professional workspace with subtle, clean surfaces. "
                "In the center, a beautiful physical visual metaphor representing \"{topic}\" "
                "(for example: crystal-clear geometric blocks stacking into an ascending staircase, "
                "with a golden physical arrow gliding smoothly over them). The environment is realistic, "
                "premium, and sophisticated.\n\n"
                "Main Subject:\nThe central visual metaphor (geometric curves, clean 3D graphs, or objects).\n\n"
                "Supporting Elements:\n"
                "- Subtle 3D shapes representing predictable growth\n"
                "- Very light depth-of-field background showing a minimal, clean luxury office\n"
                "- Clean, open negative space on the left and right margins for text overlay\n"
                "- Leave the top-right corner completely empty and clean for the logo\n\n"
                "Composition:\nProfessional advertising composition. Rule of thirds. Strong focal point. Clean negative space.\n\n"
                "Lighting:\nSoft cinematic lighting. Natural shadows. Premium commercial photography.\n\n"
                "Color Palette:\nPrimary: {primary_color}\nSecondary: {secondary_color}\nAccent: {accent_color}\n\n"
                "Style:\nModern, Luxury, Corporate, Minimal, Editorial quality\n\n"
                "Typography:\nNo text. No logos. No watermark.\n\n"
                "Aspect Ratio:\n1200x627 landscape\n\n"
                "Ultra realistic. 8K. High detail. Premium commercial advertisement."
            ),
            "carousel": (
                "Create a premium carousel slide.\n\n"
                "Slide Purpose:\nEducational hook / explainer for \"{topic}\"\n\n"
                "Main Message:\n{goal}\n\n"
                "Visual Story:\nA gorgeous financial card layout. On a clean solid light blue background, "
                "a beautifully lit, premium 3D icon rises from the center (for example: a 3D bond document "
                "bound with a golden ribbon, or a 3D growth arrow wrapped around a solid block). Thin, elegant "
                "geometric guidelines extend outward from the icon.\n\n"
                "Foreground:\nHighly detailed, polished 3D finance model or icon directly tied to \"{topic}\".\n\n"
                "Background:\nSolid light blue (#EBF5FB) background spanning the entire canvas, no gradients.\n\n"
                "Icons:\nMinimal, premium, content-specific 3D icons — never generic piggy banks or stock coins.\n\n"
                "Charts:\nSimple modern charts or geometric growth paths where relevant.\n\n"
                "Composition:\nModern LinkedIn/Instagram carousel slide. Large empty space reserved for the "
                "headline at the top. Leave the top-right corner completely empty and clean for the logo. "
                "Luxury corporate style.\n\n"
                "Color Palette:\nPrimary: {primary_color}\nSecondary: {secondary_color}\nAccent: {accent_color}\n\n"
                "Typography:\nNo text. Leave blank space where the title and body copy will be added later "
                "by the compositor.\n\n"
                "Ultra realistic. Editorial quality.\nAspect ratio 4:5 (1080x1350)."
            ),
            "comparison": (
                "Create a premium flat vector comparison infographic for LinkedIn.\n\n"
                "Topic:\n{topic}\n\n"
                "Style: Premium flat vector graphics. No 3D, no photorealism. Rounded corners, soft shadows, minimal outlines.\n"
                "Layout: Two equal cards side-by-side on pure white background. Left card = Problem (muted, gray tones). "
                "Right card = Solution (vibrant, brand colors). Thin elegant divider between them.\n"
                "Leave the top-right corner completely empty for the logo.\n\n"
                "Color Palette:\nPrimary: {primary_color}\nSecondary: {secondary_color}\nAccent: {accent_color}\n"
                "Background: Pure white (#FFFFFF). Cards: #FAFAFC. Borders: #ECECEC.\n\n"
                "No text. No labels. Canvas 1080x1350 portrait. 8K."
            ),
            "process": (
                "Create a premium flat vector process infographic for LinkedIn.\n\n"
                "Topic:\n{topic}\n\n"
                "Style: Premium flat vector graphics. No 3D, no photorealism. Rounded corners, soft shadows.\n"
                "Layout: 4-step vertical timeline with minimal outlined icons connected by clean directional arrows. "
                "Each step has a circular icon badge and a blank label area below.\n"
                "Leave the top-right corner completely empty for the logo.\n\n"
                "Color Palette:\nPrimary: {primary_color}\nSecondary: {secondary_color}\nAccent: {accent_color}\n"
                "Background: Pure white (#FFFFFF). Cards: #FAFAFC. Borders: #ECECEC.\n\n"
                "No text. No labels. Canvas 1080x1350 portrait. 8K."
            ),
            "educational": (
                "Create an educational social media illustration.\n\n"
                "Topic:\n{topic}\n\n"
                "Audience:\nWorking professionals and retail investors.\n\n"
                "Main Character:\nA modern, professionally dressed business leader looking thoughtfully toward a "
                "premium 3D glowing dashboard floating in front of them.\n\n"
                "Supporting Objects:\nSimple floating 3D charts, a miniature ledger/document, and clean "
                "geometric lines relevant to \"{topic}\".\n\n"
                "Background:\nMinimal clean office in soft focus. Leave the top-right corner completely empty "
                "and clean for the logo.\n\n"
                "Visual Style:\nModern editorial illustration.\n\n"
                "Color Palette:\nPrimary: {primary_color}\nSecondary: {secondary_color}\nAccent: {accent_color}\n\n"
                "Composition:\nInstagram-style square. No text. Premium quality. 8K."
            ),
            "data_visual": (
                "Create a premium flat vector data visualization infographic for LinkedIn.\n\n"
                "Topic:\n{topic}\n\n"
                "Style: Premium flat vector graphics. No 3D, no photorealism. Rounded corners, soft shadows.\n"
                "Visuals: Clean bar charts, elegant pie charts, ascending growth arrows, and dashboard-style cards — "
                "all flat vector, directly tied to \"{topic}\".\n"
                "Leave the top-right corner completely empty for the logo.\n\n"
                "Color Palette:\nPrimary: {primary_color}\nSecondary: {secondary_color}\nAccent: {accent_color}\n"
                "Background: Pure white (#FFFFFF). Cards: #FAFAFC. Borders: #ECECEC.\n\n"
                "No text. No labels. Canvas 1080x1350 portrait. 8K."
            ),
            "linkedin": (
                "Create a premium LinkedIn marketing image.\n\n"
                "Topic:\n{topic}\n\n"
                "Scene:\nA modern glass corporate office. Two business professionals discussing \"{topic}\", "
                "pointing to a sleek laptop showing clean analytics charts. Natural professional expressions, "
                "confident postures.\n\n"
                "Composition:\nEditorial photography. Leave the top-right corner completely empty and clean "
                "for the logo.\n\n"
                "Lighting:\nSoft daylight streaming through large windows.\n\n"
                "Background:\nMinimalist corporate office setting. Professional.\n\n"
                "Color Palette:\nPrimary: {primary_color}\nSecondary: {secondary_color}\nAccent: {accent_color}\n\n"
                "No text.\nUltra realistic.\nCommercial photography.\nCanvas 1200x627 landscape. 8K."
            ),
            "ai_tech": (
                "Create a futuristic AI illustration.\n\n"
                "Topic:\n{topic}\n\n"
                "Scene:\nA sleek, modern minimalist workspace. Transparent holographic interfaces display "
                "neural networks, deep data analytics, and digital particles flowing in an upward growth trend "
                "related to \"{topic}\".\n\n"
                "Blue neon accents highlight the edges of the holographic cards.\n\n"
                "Minimal composition. Leave the top-right corner completely empty and clean for the logo.\n"
                "Corporate.\nNo text.\nPremium.\nCanvas 1200x627 landscape. 8K."
            ),
        }

        selected_template = templates[template_name]
        expanded_prompt = selected_template.format(
            topic=topic,
            goal=goal,
            primary_color=primary_color,
            secondary_color=secondary_color,
            accent_color=accent_color,
        )

        # ── Attach structured content + explicit constraints so the model has everything it needs ──
        sections_text = ""
        if infographic_sections:
            sections_text = "\n".join(
                f"- {s.get('section_label', '')}: {s.get('stat', '')} — {s.get('body', '')}"
                for s in infographic_sections
            )
        proof_text = "\n".join(f"- {p}" for p in (proof_points or []))
        stat_text = "\n".join(f"- {s}" for s in (stat_highlights or []))

        user_prompt_section = ""
        if user_prompt:
            user_prompt_section = (
                "\n\nUSER'S SPECIFIC DESIGN REQUEST (HIGHEST PRIORITY — incorporate faithfully):\n"
                f"\"{user_prompt}\""
            )

        content_context = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BRAND & CONTENT CONTEXT (use to make the scene specific, not generic)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Brand: {brand_name}
Visual Mood: {visual_mood}
Color Behavior: {color_behavior}
Headline: "{copy_headline}"
Supporting Line: "{supporting_line}"
Body: {copy_body}
CTA: "{cta}"
Structured Sections:
{sections_text or 'None provided — derive 4-6 specific sections from the headline/body above.'}
Proof Points:
{proof_text or 'None provided.'}
Key Stats:
{stat_text or 'None provided.'}
Platform: {platform}
{user_prompt_section}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NON-NEGOTIABLE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Logo Zone: ALWAYS reserve the top-right corner (roughly 160x50px with 56px padding) completely clean, empty, and free of any visual elements so the logo can be composited safely afterward.
2. Strict Dimensions: Respect the exact canvas/aspect ratio specified in the template above for this format.
3. No Text In Image: Do NOT render any text, numbers, letters, logos, or watermarks in the image itself — the compositor will add all copy, labels, and stats afterward with zero clipping or truncation.
4. Background: Pure white (#FFFFFF) for infographic, solid light blue (#EBF5FB) for carousel, or the stated palette for static formats. Cards: #FAFAFC. Borders: #ECECEC.
5. Content-Specific Icons Only: Every icon or illustrated object must directly and specifically represent the brief above — never use generic, repeated, or irrelevant stock imagery. Use flat premium vector icons from one visual family with uniform stroke width.
6. All visual elements must fit safely and completely inside the frame with generous margins — nothing may be cropped or crowd the edges.

Now write the final expanded image-generation prompt following the template structure above, incorporating this context. Return ONLY the expanded prompt text — no preamble, no headers, no explanation."""

        return expanded_prompt + content_context

    def _build_infographic_prompt(
        self,
        *,
        brand_name: str,
        headline: str,
        supporting_line: str,
        body: str,
        cta: str,
        infographic_sections: list[dict],
        stat_highlights: list[str],
        problem_statement: str,
        solution_statement: str,
        customer_quote: str,
        customer_name: str,
        process_steps: list[str],
        user_prompt: str,
    ) -> str:
        """Build the infographic prompt with 3D-style icons (pig, invest, etc.) matching reference images."""

        title = headline or "Untitled"
        subtitle = supporting_line or ""

        features = infographic_sections[:5]
        features_text = "\n".join(
            f"{i}. {sec.get('section_label', '') or 'Feature'} — "
            f"{sec.get('stat', '')}{' — ' if sec.get('stat') else ''}{sec.get('body', '')}".strip(" —")
            for i, sec in enumerate(features, start=1)
        ) or "None supplied — do not invent a features section; omit it."

        stats = stat_highlights[:5]
        stats_text = "\n".join(f"{i}. {s}" for i, s in enumerate(stats, start=1)) or (
            "None supplied — do not invent a statistics section; omit it."
        )

        timeline = process_steps[:4]
        timeline_text = "\n".join(f"Step {i}: {s}" for i, s in enumerate(timeline, start=1)) or (
            "None supplied — do not invent a process/timeline section; omit it."
        )

        quote_block = (
            f'Quote: "{customer_quote}"\nAttribution: {customer_name or "Verified customer"}'
            if customer_quote
            else "None supplied — do not invent a testimonial section; omit it."
        )

        user_prompt_section = ""
        if user_prompt:
            user_prompt_section = (
                "\n\nUSER'S SPECIFIC DESIGN REQUEST (HIGHEST PRIORITY — incorporate faithfully):\n"
                f'"{user_prompt}"'
            )

        return f"""Create a premium, corporate LinkedIn infographic with 3D-style icons. It must look like it was designed by a senior UI/UX designer from Stripe, Apple, Notion, or McKinsey — every word spelled correctly, every card fully finished, not a generic AI poster.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIXED MASTER DESIGN SYSTEM (never change this styling)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Brand Personality: Professional, Trustworthy, Educational, Premium, Minimal, Modern, Financial, Clean, Data-driven, Human-centered.
Target Audience: Retail Investors, HNIs, Young Professionals, Finance Enthusiasts.
Canvas: Portrait 1080x1350, high resolution, 3D rendered icons with clean typography. Use premium 3D icons like piggy bank, investment charts, coins, shields, growth arrows, etc.
Grid: 12-column grid layout, large white margins, generous breathing space, perfect alignment and spacing throughout.

Brand Colors (use exactly):
- Primary Purple: #33206F
- Secondary Orange: #F59A23
- Accent Yellow: #FFC857
- Dark Text: #222222
- Secondary Text: #5B5B5B
- Background: Pure White #FFFFFF
- Cards: #FAFAFC
- Borders: #ECECEC
- Success: #2EAF62
- Blue: #4F8EF7
- Gray: #9EA3AE

Typography: Modern sans-serif (Inter, Manrope, SF Pro, Plus Jakarta Sans style). Bold very large headings, semi-bold subheadings, medium-weight body, regular captions. Extremely clear text hierarchy. Perfect readability. Avoid decorative fonts.

Visual Style: Premium 3D rendered icons (piggy bank, investment growth, coins, shield, target, graph, etc.) with clean flat backgrounds. Rounded corners (16-24px radius), soft shadows, large cards, minimal outlines, soft color palette, friendly illustrations, consistent stroke width, financial dashboard aesthetic.

Icon Style: Premium 3D rendered icons — piggy bank for savings, investment charts for growth, coins for wealth, shield for security, target for goals, graph for performance, calendar for time, document for reports. All icons should be 3D-style with subtle lighting and shadows, matching modern fintech apps.

Card Style: 16-24px radius, very light shadow, soft border, large padding, consistent spacing, equal width, perfectly aligned.

Illustrations: Premium 3D rendered icons, friendly, corporate, no realism, no anime, no cartoon. Icons have subtle lighting, clean shapes, soft colors.

Spacing: Extremely generous whitespace, consistent margins/paddings, nothing cramped, professional presentation.

Logo Zone: Reserve the top-right corner (about 160x50px, 56px padding) completely clean and empty — do NOT draw any logo, wordmark, or brand mark there; the real brand logo is composited afterward by the backend.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LAYOUT (top to bottom) — populate every card with the DYNAMIC CONTENT below
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Top Section: empty logo-safe corner, then the Title as a large bold headline, the Subtitle beneath it, a thin divider line, then one relevant 3D icon for the topic (piggy bank, investment chart, etc.).
2. Problem vs Solution: two equal side-by-side cards. Left card labeled "The Problem" with a small 3D icon and the Problem text. Right card labeled "The Solution" with a small 3D icon and the Solution text. Only include this section if Problem and Solution text are provided below.
3. Features: up to five horizontal cards in a row/grid, each with one 3D icon (piggy bank, investment, coin, shield, target, etc.), the feature title, and its short description, using the Features list below. Only include as many cards as items are supplied.
4. Statistics: statistic cards each showing one large number/stat plus a short supporting label and a small 3D icon, using the Statistics list below. Only include as many cards as items are supplied.
5. Testimonial: one rounded card with a circular avatar placeholder, the quote text, and the attribution name, using the Quote block below. Skip this section entirely if no quote is supplied.
6. Process Timeline: a horizontal 4-step timeline with small numbered 3D icon badges connected by thin arrows, one short label per step, using the Timeline list below. Skip if no steps are supplied.
7. CTA: a closing band with the CTA text as a short bold line, plus a rounded button-style shape containing the CTA text (or a short imperative derived from it). Keep the logo-safe zone here empty too.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DYNAMIC CONTENT — render this exact text, perfectly spelled, nothing invented or altered
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Brand: {brand_name}
Title: {title}
Subtitle: {subtitle or 'None supplied — omit the subtitle line.'}
Problem: {problem_statement or 'None supplied — omit the Problem vs Solution section.'}
Solution: {solution_statement or 'None supplied — omit the Problem vs Solution section.'}
Features:
{features_text}
Statistics:
{stats_text}
Timeline:
{timeline_text}
Testimonial:
{quote_block}
CTA: {cta or 'None supplied — omit the CTA band.'}
{user_prompt_section}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NON-NEGOTIABLE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Every word above must appear in the image exactly as written, with perfect spelling and grammar — proofread before rendering. Never invent extra copy, filler Lorem Ipsum, or duplicate text.
2. Never leave a card, section, or label visually empty or blank; if content for a section is marked "None supplied", omit that whole section rather than drawing an empty placeholder card.
3. All cards, text, and 3D icons must fit completely inside the 1080x1350 canvas with generous margins — nothing cropped, clipped, or crowding an edge.
4. Use 3D-style icons (piggy bank, investment charts, coins, shields, targets, graphs) with subtle lighting and shadows — not flat vector icons.

Return ONLY the finished image. Follow the layout and dynamic content exactly."""

