from __future__ import annotations

import re
from uuid import UUID

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.graph.models.layer8_models import VisualReasoningOutput
from app.graph.state import ViolytState
from app.models.brand import BrandSpace
from app.prompts.layer8_visual_reasoning import VisualReasoningPromptBuilder
from app.services.image_generation.dalle_service import DalleService
from app.services.image_generation.logo_fetcher import get_brand_logo_storage_path
from app.services.image_generation.sdxl_service import SdxlService
from app.services.llm.llm_router import LLMRouter
from app.services.copy_proofread import NO_AI_LOGO_RULE, SPELLING_ACCURACY_RULE, HUB_CARD_ICON_RULE
from app.prompts.brand_copy_tone import (
    BRAND_COLOR_LOCK_RULE,
    CAROUSEL_SEBI_LOCK_RULE,
    INDIA_MARKET_LOCK_RULE,
    SOURCE_FOOTER_RULE,
    SEBI_FOOTER_HINT,
    NO_SEBI_STATIC_RULE,
    CAROUSEL_FIT_LOCK,
    ICON_STYLE_LOCK,
)
from app.prompts.jiraaf_layout import classify_layout
from app.prompts.creative_sizes import canvas_label, size_string

logger = get_logger(__name__)

_router = LLMRouter()
_prompt_builder = VisualReasoningPromptBuilder()


def _q(value: object, max_chars: int = 280) -> str:
    """Quote exact copy for image prompts; trim on word boundary (never bake '…')."""
    if isinstance(value, (list, tuple)):
        parts: list[str] = []
        for v in value:
            if isinstance(v, dict):
                label = v.get("section_label") or v.get("label") or ""
                body = v.get("body") or v.get("stat") or ""
                chunk = f"{label}: {body}".strip(": ").strip()
                if chunk:
                    parts.append(chunk)
            else:
                s = str(v).strip()
                if s:
                    parts.append(s)
        text = " | ".join(parts)
    else:
        text = str(value or "")
    text = " ".join(text.split()).strip()
    text = text.rstrip("….").strip()
    if not text:
        return '""'
    if len(text) > max_chars:
        cut = text[:max_chars].rsplit(" ", 1)[0].rstrip(" ,.;:")
        text = cut if cut else text[:max_chars].rstrip(" ,.;:")
    safe = text.replace('"', "'")
    return f'"{safe}"'


def _chip_label(value: object, max_words: int = 1, max_chars: int = 14) -> str:
    """One complete chip word — never multi-word phrases that SEBI truncates mid-label."""
    words = " ".join(str(value or "").split()).strip().split()
    label = (words[0] if words else "").strip(".,;:!")
    if len(label) > max_chars:
        label = label[:max_chars]
    return _q(label, max_chars)


# Capital-controls / FDI sample labels — NEVER inject these unless the user asked that topic
_FORBIDDEN_SAMPLE_CHIPS = {
    "inflows",
    "outflows",
    "limits",
    "fdi impact",
    "fx impact",
    "growth signal",
    "rbi role",
    "policy tools",
    "risk control",
    "banks",
    "markets",
    "investors",
}

_ROLE_HEROES = {
    "hook": "3D question-mark + bond certificate + rupee coin (curiosity hook)",
    "define": "3D bond paper + calendar coupon strip + handshake (plain definition)",
    "impact": "3D rising income chart + wallet + rupee stack (why it helps)",
    "implication": "3D shield + lock/padlock + clock (predictable / protected)",
    "proof": "3D investor briefcase + growth bars + handshake (real-world proof)",
    "myth": "3D myth-bust stamp + lightbulb + checklist (myth vs truth)",
    "cta": "3D CTA arrow + phone/app tile + rupee coin (closing action)",
    "insight": "3D bond certificate + shield + rupee coins (topic insight)",
}

# ONE-WORD chips only — multi-word phrases get truncated by SEBI ("Steady"/"Plan"/"Less")
_ROLE_CHIPS = {
    "hook": ("Hook", "Income", "Bonds"),
    "define": ("Coupons", "Principal", "Maturity"),
    "impact": ("Income", "Cashflow", "Stability"),
    "implication": ("Safety", "Horizon", "Predictable"),
    "proof": ("Example", "Lesson", "Action"),
    "myth": ("Myth", "Reality", "Takeaway"),
    "cta": ("Explore", "Learn", "Start"),
    "insight": ("Income", "Safety", "Liquidity"),
}

# Distinct heroes by slide index so slides 3 vs 4 never clone the same cluster
_BOND_HEROES_BY_N = {
    1: "3D question-mark + bond certificate + rupee coin",
    2: "3D bond paper + coupon calendar + handshake",
    3: "3D coupon stream + wallet + rising income bars (HOW IT WORKS — unique)",
    4: "3D shield + padlock + clock (INVESTOR IMPLICATION — different from slide 3)",
    5: "3D briefcase + warning triangle + checklist (nuance / watch-out)",
    6: "3D myth stamp + lightbulb + checklist",
    7: "3D CTA arrow + phone tile + rupee coin",
}

_BOND_CHIPS_BY_N = {
    1: ("Surprise", "Income", "Bonds"),
    2: ("Coupons", "Principal", "Maturity"),
    3: ("Mechanism", "Cashflow", "Timing"),
    4: ("Investor", "Safety", "Horizon"),
    5: ("Risk", "Condition", "Watch"),
    6: ("Myth", "Reality", "Takeaway"),
    7: ("Explore", "Learn", "Start"),
}


def _normalize_role(role: object) -> str:
    r = str(role or "insight").strip().lower()
    aliases = {
        "hook": "hook",
        "intro": "hook",
        "define": "define",
        "definition": "define",
        "impact": "impact",
        "how": "impact",
        "mechanism": "impact",
        "why": "impact",
        "implication": "implication",
        "affect": "implication",
        "investor": "implication",
        "proof": "proof",
        "example": "proof",
        "nuance": "proof",
        "watch": "proof",
        "myth": "myth",
        "myth-bust": "myth",
        "cta": "cta",
        "close": "cta",
        "closing": "cta",
    }
    for key, val in aliases.items():
        if key in r:
            return val
    return "insight"


def _chips_look_like_wrong_sample(chips: tuple[str, str, str]) -> bool:
    return any(c.strip().lower() in _FORBIDDEN_SAMPLE_CHIPS for c in chips)


def _one_word_chips(values: list[str] | tuple[str, ...]) -> tuple[str, str, str] | None:
    words: list[str] = []
    for v in values:
        w = " ".join(str(v or "").split()).strip()
        if not w:
            continue
        # Prefer first token; keep short compounds like Cashflow
        token = w.split()[0].strip(".,;:!")
        if token and token.lower() not in _FORBIDDEN_SAMPLE_CHIPS:
            words.append(token[:14])
        if len(words) == 3:
            return (words[0], words[1], words[2])
    return None


def _derive_carousel_chips(
    *,
    role: str,
    n: int,
    bp_slide: object | None,
    slide_headline: str,
    slide_body: str,
    user_prompt: str,
) -> tuple[str, str, str]:
    """Bottom chips: 3 complete ONE-WORD labels for THIS slide — never truncated phrases."""
    # 1) Blueprint chip_labels (preferred — content-authored)
    if bp_slide and getattr(bp_slide, "chip_labels", None):
        got = _one_word_chips(list(bp_slide.chip_labels or []))
        if got and not _chips_look_like_wrong_sample(got):
            return got

    # 2) proof_points if already chip-sized
    if bp_slide and getattr(bp_slide, "proof_points", None):
        got = _one_word_chips([str(p) for p in (bp_slide.proof_points or [])])
        if got and not _chips_look_like_wrong_sample(got):
            return got

    blob = f"{user_prompt} {slide_headline} {slide_body}".lower()
    if any(k in blob for k in ("bond", "coupon", "predictable", "income", "yield", "maturity")):
        return _BOND_CHIPS_BY_N.get(n) or _BOND_CHIPS_BY_N[((n - 1) % 7) + 1]

    return _ROLE_CHIPS.get(role, _ROLE_CHIPS["insight"])


def _derive_carousel_hero(
    *,
    role: str,
    n: int,
    slide_headline: str,
    user_prompt: str,
    used_heroes: set[str],
) -> str:
    """Hero cluster unique per slide index — slides 3 and 4 must not share the same set."""
    blob = f"{user_prompt} {slide_headline}".lower()
    if any(k in blob for k in ("bond", "coupon", "predictable", "income", "yield")):
        hero = _BOND_HEROES_BY_N.get(n) or _BOND_HEROES_BY_N[((n - 1) % 7) + 1]
    else:
        hero = _ROLE_HEROES.get(role) or _ROLE_HEROES["insight"]
    # If somehow duplicated, append slide index cue for the image model
    if hero in used_heroes:
        hero = f"{hero} — SLIDE {n} VARIANT (different objects, different pose)"
    used_heroes.add(hero)
    return hero


def _error_free_text_block(lines: list[tuple[str, str]], *, is_carousel: bool = False) -> str:
    """Build quoted-text bake instructions (font + contrast + exact strings)."""
    parts = [
        "\n\nCRITICAL — ERROR-FREE BAKED TEXT (quoted strings are EXACT):\n",
        "Typography: clean printed sans-serif only. No chrome, bevel, glow, outline, handwriting, or decorative text effects.\n",
        "Contrast: dark navy text (#003975) on ice-blue background (#E8F0F8) with orange accents (#FFA400).\n",
        "Render ONLY the quoted strings below — letter-perfect, never truncate headline with '...'.\n",
        "Do not invent words. Do not misspell. Do not leave empty cards. Logo is composited after.\n",
        "India market: prefer ₹/%; NEVER use £; USD only if source is USD; correct country names/flags.\n",
        "Brand: navy #003975 + REQUIRED orange #FFA400 accents; ice-blue BG #E8F0F8.\n",
    ]
    if is_carousel:
        parts.append(f"{SEBI_FOOTER_HINT}\n")
    else:
        parts.append(f"{NO_SEBI_STATIC_RULE}\n")
    for label, quoted in lines:
        if quoted and quoted != '""':
            parts.append(f"{label}: {quoted}\n")
    return "".join(parts)


async def layer8_visual_reasoning(state: ViolytState) -> dict:
    brand_intelligence = state.get("brand_intelligence")
    format_plan = state.get("format_plan")
    copy = state.get("copy")
    blueprint = state.get("creative_blueprint")
    creative_concepts = state.get("creative_concepts")
    user_prompt = state.get("user_prompt", "")

    brand_id = state.get("brand_id", "unknown")
    platform = state.get("platform", "linkedin")
    fmt = state.get("format", "static")

    if not brand_intelligence or not format_plan or not copy or not creative_concepts:
        logger.error("visual_reasoning.missing_inputs")
        raise ValueError(
            "Layer 2 brand_intelligence, Layer 5 creative_concepts, Layer 6 format_plan, "
            "and Layer 7 copy are required for Layer 8"
        )

    # Prefer approved Creative Blueprint text for art direction cues
    headline = (blueprint.headline if blueprint and blueprint.headline else copy.headline)
    body = (blueprint.body if blueprint and blueprint.body else copy.body)
    supporting = (
        blueprint.supporting_line
        if blueprint and blueprint.supporting_line is not None
        else copy.supporting_line
    ) or ""
    cta = (blueprint.cta if blueprint and blueprint.cta else copy.cta) or ""
    sections = (
        [s.model_dump() for s in blueprint.sections]
        if blueprint and blueprint.sections
        else [s.model_dump() for s in copy.infographic_sections]
    )
    proof_points = (
        list(blueprint.proof_points)
        if blueprint and blueprint.proof_points
        else list(copy.proof_points or [])
    )
    stat_highlights = (
        list(blueprint.stat_highlights)
        if blueprint and blueprint.stat_highlights
        else list(copy.stat_highlights or [])
    )
    problem_statement = (
        (blueprint.problem_statement if blueprint else None) or copy.problem_statement or ""
    )
    solution_statement = (
        (blueprint.solution_statement if blueprint else None) or copy.solution_statement or ""
    )
    customer_quote = (
        (blueprint.customer_quote if blueprint else None) or copy.customer_quote or ""
    )
    customer_name = (
        (blueprint.customer_name if blueprint else None) or copy.customer_name or ""
    )
    process_steps = (
        list(blueprint.process_steps)
        if blueprint and blueprint.process_steps
        else list(copy.process_steps or [])
    )

    recommended = creative_concepts.recommended_concept

    layout_type = (
        (blueprint.layout_type if blueprint else "")
        or classify_layout(user_prompt, fmt).layout_type
    )

    # Convert Concept Pydantic model to dict
    concept_dict = {
        "concept_name": recommended.concept_name,
        "core_idea": recommended.core_idea,
        "hook": recommended.hook,
        "narrative_angle": recommended.narrative_angle,
        "visual_angle": recommended.visual_angle,
    }

    system = _prompt_builder.build_system(
        fmt=fmt,
        layout_type=layout_type,
    )
    user = _prompt_builder.build_user(
        brand_intelligence=brand_intelligence,
        format_plan=format_plan,
        copy=copy,
        concept=concept_dict,
        user_prompt=user_prompt,
        fmt=fmt,
        layout_type=layout_type,
    )
    if blueprint:
        story = "; ".join(blueprint.story_flow or [])
        layout_type = (
            blueprint.layout_type
            or blueprint.layout_archetype
            or classify_layout(user_prompt, fmt).layout_type
        )
        source_footer = (blueprint.source_footer or "").strip()
        sources_note = ""
        if blueprint.sources:
            sources_note = "; ".join(
                f"{s.title or 'source'}: {s.url}" for s in blueprint.sources[:4] if s.url
            )
        user = (
            user
            + "\n\nAPPROVED CREATIVE BLUEPRINT (bake this EXACT text into the image — no Pillow overlay):\n"
            + f"purpose={blueprint.purpose}\nlayout_type={layout_type}\nlayout={blueprint.layout_archetype}\n"
            + f"text_density={blueprint.text_density}\nhierarchy={blueprint.visual_hierarchy}\n"
            + f"hook={blueprint.hook}\nstory_flow={story}\n"
            + f"headline={headline}\nsupporting_line={supporting}\nbody={body}\ncta={cta}\n"
            + f"problem={problem_statement}\nsolution={solution_statement}\n"
            + f"sections={sections}\nstats={stat_highlights}\nproof={proof_points}\n"
            + f"process_steps={process_steps}\nquote={customer_quote}\nquote_by={customer_name}\n"
            + f"source_footer={source_footer}\nsources={sources_note}\n"
            + "CRITICAL: Generate a FINISHED creative. Render the approved strings as sharp typography in the image. "
            "Do not leave empty shells. Do not invent alternate copy. "
            "REQUIRED: navy #003975 + orange #FFA400 accents; ULTRA-PREMIUM clay-3D icons; content must fit fully. "
            + (
                f'Bake compact footer text EXACTLY as: "{source_footer}". '
                if source_footer
                else "If no source_footer, omit Source line (do not invent domains). "
            )
            + SOURCE_FOOTER_RULE
        )

    # 1. Complete visual reasoning structure (GPT-4o)
    service = _router.get_service("l8_visual_reasoning")
    output, metadata = await service.complete_structured(
        system=system,
        user=user,
        output_model=VisualReasoningOutput,
        layer="l8_visual_reasoning",
        max_tokens=8192,
    )

    # 1b. STAGE 2: Expand the image prompt into a professional 2500+ word cinematic art direction brief
    expander_meta: dict = {}
    logger.info(
        "visual_reasoning.prompt_expansion_start",
        initial_prompt_len=len(output.image_prompt_direction),
    )
    expander_system = _prompt_builder.build_expander_system(
        dominant_visual_system=output.dominant_visual_system,
        fmt=fmt,
    )
    expander_user = _prompt_builder.build_expander_user(
        brand_name=brand_intelligence.brand_core.brand_name,
        visual_mood=brand_intelligence.visual_behavior.visual_mood,
        color_behavior=brand_intelligence.visual_behavior.color_behavior,
        image_behavior=brand_intelligence.visual_behavior.image_behavior,
        design_sophistication=brand_intelligence.visual_behavior.design_sophistication,
        concept_name=concept_dict.get("concept_name", ""),
        core_idea=concept_dict.get("core_idea", ""),
        visual_angle=concept_dict.get("visual_angle", ""),
        copy_headline=headline,
        copy_body=body,
        supporting_line=supporting,
        cta=cta,
        infographic_sections=sections,
        proof_points=proof_points,
        stat_highlights=stat_highlights,
        problem_statement=problem_statement,
        solution_statement=solution_statement,
        customer_quote=customer_quote,
        customer_name=customer_name,
        process_steps=process_steps,
        format_strategy=format_plan.format_strategy,
        layout_archetype=(
            blueprint.layout_archetype if blueprint and blueprint.layout_archetype else format_plan.layout_archetype
        ),
        platform=platform,
        initial_prompt=output.image_prompt_direction,
        user_prompt=user_prompt,
        dominant_visual_system=output.dominant_visual_system,
        fmt=fmt,
        layout_type=layout_type,
        hook=(blueprint.hook if blueprint else "") or getattr(copy, "hook", None) or "",
        story_flow=list(blueprint.story_flow) if blueprint and blueprint.story_flow else [],
        slides=(
            [s.model_dump() for s in blueprint.slides]
            if blueprint and blueprint.slides
            else [s.model_dump() for s in (copy.slide_copy or [])]
        ),
    )

    try:
        expanded_prompt, expander_meta = await service.complete_text(
            system=expander_system,
            user=expander_user,
            layer="l8_prompt_expander",
            temperature=0.35,
            max_tokens=2048,
        )
        logger.info(
            "visual_reasoning.prompt_expansion_complete",
            expanded_prompt_len=len(expanded_prompt),
            expander_tokens=expander_meta.get("output_tokens", 0),
        )
        # Lock exact approved copy AFTER expansion so the LLM cannot paraphrase away spelling
        exact_lock = (
            "\n\nLOCKED EXACT COPY (bake letter-perfect — do not rewrite):\n"
            f'Headline: "{headline}"\n'
            f'Supporting: "{supporting}"\n'
            f'CTA: "{cta}"\n'
        )
        if sections:
            exact_lock += "Sections:\n"
            # Include all ranking rows (cap 15) — truncating to 5/6 caused top-10 bugs
            for i, sec in enumerate(sections[:15], start=1):
                if isinstance(sec, dict):
                    lab = sec.get("section_label") or f"Item {i}"
                    st = sec.get("stat") or ""
                    incs = sec.get("includes") or []
                    if isinstance(incs, list):
                        incs_txt = "; ".join(str(x) for x in incs[:2])
                    else:
                        incs_txt = str(incs)
                    exact_lock += f'{i}. "{lab}" | "{st}" | "{incs_txt}"\n'
        image_gen_prompt = (expanded_prompt + exact_lock + f"\n{ICON_STYLE_LOCK}\n")[:6000]
        output.image_prompt_direction = image_gen_prompt
    except Exception as e:
        logger.warning(
            f"visual_reasoning.prompt_expansion_failed, using original prompt: {e}"
        )
        image_gen_prompt = output.image_prompt_direction

    # 2. Get the correct tenant_id and brand logo path from DB
    tenant_id = None
    logo_storage_path: str | None = None
    logo_zone_instruction: str | None = brand_intelligence.visual_behavior.logo_zone_instruction

    try:
        brand_uuid = UUID(str(brand_id)) if not isinstance(brand_id, UUID) else brand_id
        async with AsyncSessionLocal() as session:
            brand = await session.get(BrandSpace, brand_uuid)
            if brand:
                tenant_id = brand.tenant_id

            # Fetch the brand logo path for composite overlay
            logo_storage_path = await get_brand_logo_storage_path(
                brand_space_id=brand_uuid,
                session=session,
            )

        if logo_storage_path:
            logger.info(
                "visual_reasoning.logo_found",
                logo_path=logo_storage_path,
                zone=logo_zone_instruction,
            )
        else:
            logger.info(
                "visual_reasoning.logo_not_found",
                brand_id=str(brand_id),
            )
    except Exception as e:
        logger.warning(f"visual_reasoning.db_tenant_or_logo_failed: {e}")

    # Fallback default UUID if DB call fails
    if not tenant_id:
        tenant_id = UUID("00000000-0000-0000-0000-000000000000")

    # 3. Size computation — format × platform (must match Studio picker)
    size = size_string(fmt, platform)
    canvas_desc = canvas_label(fmt, platform)
    logger.info("visual_reasoning.canvas_size", format=fmt, platform=platform, size=size)

    # 4. Image generation with gpt-image-1 + brand logo composite, falling back to SDXL/Mock
    async def _generate_one_image(
        prompt: str,
        image_size: str,
        fallback_suffix: str = "",
        *,
        composite_sebi_footer: bool = False,
    ) -> str:
        # Brand logo comes from Brand Space compositing — never from the image model.
        # SEBI footer: carousel ONLY (user rule). Static/infographic never get disclaimer.
        extra_locks = BRAND_COLOR_LOCK_RULE + INDIA_MARKET_LOCK_RULE
        if composite_sebi_footer:
            extra_locks = CAROUSEL_SEBI_LOCK_RULE + extra_locks
        else:
            extra_locks = f"\n\n{NO_SEBI_STATIC_RULE}\n" + extra_locks
        safe_prompt = (
            prompt
            + NO_AI_LOGO_RULE
            + SPELLING_ACCURACY_RULE
            + HUB_CARD_ICON_RULE
            + extra_locks
        )[:6000]
        try:
            dalle = DalleService()
            url = await dalle.generate_and_save(
                tenant_id=tenant_id,
                brand_space_id=brand_id,
                prompt=safe_prompt,
                size=image_size,
                logo_storage_path=logo_storage_path,
                logo_zone_instruction=logo_zone_instruction
                or "tiny top-right pocket, ~12% width, 20px padding, no brand-name text",
                composite_sebi_footer=composite_sebi_footer,
            )
            logger.info(
                "visual_reasoning.dalle_success",
                url=url,
                suffix=fallback_suffix,
                logo_composited=bool(logo_storage_path),
            )
            return url
        except Exception as e:
            logger.warning(
                f"visual_reasoning.dalle_failed{fallback_suffix}, falling back to SDXL: {type(e).__name__}: {e}"
            )
            try:
                sdxl = SdxlService()
                url = await sdxl.generate_and_save(
                    tenant_id=tenant_id,
                    brand_space_id=brand_id,
                    prompt=safe_prompt,
                    size=image_size,
                )
                logger.info("visual_reasoning.sdxl_success", url=url, suffix=fallback_suffix)
                return url
            except Exception as e_sdxl:
                logger.error(f"visual_reasoning.sdxl_failed{fallback_suffix}: {e_sdxl}")
                raise RuntimeError(
                    f"Image generation failed for {fallback_suffix or 'creative'} "
                    f"(DALL·E: {type(e).__name__}; SDXL: {type(e_sdxl).__name__}: {e_sdxl})"
                ) from e_sdxl

    generated_urls: list[str] = []
    # Prefer approved blueprint slides as the carousel source of truth
    carousel_slides = list(format_plan.slide_plan or [])
    if fmt == "carousel" and blueprint and blueprint.slides:
        from types import SimpleNamespace

        carousel_slides = [
            SimpleNamespace(
                slide_number=s.slide_number,
                focus=s.role or "insight",
                visual_intent=s.headline or "",
            )
            for s in blueprint.slides
        ]
    elif fmt == "carousel" and not carousel_slides and copy.slide_copy:
        from types import SimpleNamespace

        carousel_slides = [
            SimpleNamespace(
                slide_number=s.slide_number,
                focus="insight",
                visual_intent=s.headline or "",
            )
            for s in copy.slide_copy
        ]

    if fmt == "carousel" and not carousel_slides:
        raise ValueError(
            "Carousel selected but no slides were prepared in the blueprint. "
            "Re-run Phase 1 or add slides on the approval card before generating."
        )

    if fmt == "carousel" and carousel_slides:
        slide_copy_by_number = {s.slide_number: s for s in (copy.slide_copy or [])}
        blueprint_slides = {
            s.slide_number: s for s in ((blueprint.slides if blueprint else None) or [])
        }
        # Short style lock only — NEVER paste the full master expander prompt (that clones one slide N times)
        style_lock = (
            f"Finished {platform} {fmt} creative, canvas {canvas_desc}. "
            f"FULL-BLEED solid ice-blue #E8F0F8 edge-to-edge — NO white side bars, NO second BG color, "
            f"NO giant white frame. Navy #003975 headlines, gray supporting, orange #FFA400 accents. "
            f"ULTRA-PREMIUM clay-3D icons (high-detail studio renders, LARGE heroes ~30% height). "
            f"Match Jiraaf educational carousel samples. "
            f"Leave tiny empty top-right pocket for Brand Space logo — no Follow-Jiraaf lines. "
            f"Spell every word perfectly — never invent nonsense words (e.g. never 'Mealtime' for mid-term). "
            f"TOPIC LOCK: stay on the user request only — never inject FDI / FX / capital-control / "
            f"Inflows-Outflows-Limits chips unless those words are in the approved slide copy. "
            f"{ICON_STYLE_LOCK}"
            f"{CAROUSEL_FIT_LOCK}"
        )
        total = len(carousel_slides)
        # Build ordered storyline from blueprint for swipe continuity
        ordered_bp = sorted(
            ((blueprint.slides if blueprint else None) or []),
            key=lambda s: s.slide_number,
        )
        storyline_lines = []
        for s in ordered_bp:
            storyline_lines.append(
                f"{s.slide_number}. [{s.role}] {s.headline} — {(s.body or '')[:80]}"
            )
        if not storyline_lines and blueprint and blueprint.story_flow:
            storyline_lines = [str(x) for x in blueprint.story_flow]
        storyline_block = "\n".join(storyline_lines) or "(derive from per-slide headlines)"
        topic_lock = _q(user_prompt, 160)
        used_heroes: set[str] = set()
        used_headlines: list[str] = []

        for idx, slide in enumerate(carousel_slides):
            bp_slide = blueprint_slides.get(slide.slide_number)
            slide_copy = slide_copy_by_number.get(slide.slide_number)
            n = int(getattr(slide, "slide_number", 0) or 0) or (idx + 1)
            slide_headline = (
                (bp_slide.headline if bp_slide else None)
                or (slide_copy.headline if slide_copy else None)
                or getattr(slide, "visual_intent", None)
                or f"Slide {n}"
            )
            slide_body = (
                (bp_slide.body if bp_slide else None)
                or (slide_copy.body if slide_copy else None)
                or ""
            )
            slide_cta = (
                (bp_slide.cta if bp_slide else None)
                or (slide_copy.cta if slide_copy else None)
                or ""
            )
            slide_supporting = (
                (bp_slide.supporting_line if bp_slide else None)
                or (getattr(slide_copy, "supporting_line", None) if slide_copy else None)
                or ""
            )
            role_raw = (
                (bp_slide.role if bp_slide else None)
                or getattr(slide, "focus", None)
                or "insight"
            )
            role = _normalize_role(role_raw)
            prev_hl = ""
            next_hl = ""
            if ordered_bp:
                for j, s in enumerate(ordered_bp):
                    if s.slide_number == n:
                        if j > 0:
                            prev_hl = ordered_bp[j - 1].headline or ""
                        if j + 1 < len(ordered_bp):
                            next_hl = ordered_bp[j + 1].headline or ""
                        break
            hero = _derive_carousel_hero(
                role=role,
                n=n,
                slide_headline=str(slide_headline or ""),
                user_prompt=user_prompt or "",
                used_heroes=used_heroes,
            )
            bottoms = _derive_carousel_chips(
                role=role,
                n=n,
                bp_slide=bp_slide,
                slide_headline=str(slide_headline or ""),
                slide_body=str(slide_body or ""),
                user_prompt=user_prompt or "",
            )

            is_last = n == total or role == "cta"
            # Ensure supporting line is never empty (samples always have it)
            if not (slide_supporting or "").strip():
                slide_supporting = (slide_body or "").split(".")[0].strip()[:90]
            hl = _q(slide_headline, 70)
            sup = _q(slide_supporting, 100)
            body_txt = _q(slide_body, 120)
            b0, b1, b2 = _chip_label(bottoms[0]), _chip_label(bottoms[1]), _chip_label(bottoms[2])
            prior = "; ".join(used_headlines[-3:]) if used_headlines else "(none yet)"
            used_headlines.append(str(slide_headline or "")[:60])
            slide_prompt = (
                f"{style_lock}\n\n"
                f"=== USER TOPIC (do not drift) ===\n{topic_lock}\n\n"
                f"=== CAROUSEL STORYLINE (slide {n} of {total}) ===\n"
                f"{storyline_block}\n\n"
                f"=== RENDER SLIDE {n} — BEAT [{role}] ===\n"
                f"Previous headline: {_q(prev_hl, 60)} | Next (don't show): {_q(next_hl, 60)}\n"
                f"Already rendered headlines (do NOT clone look/meaning): {prior}\n"
                f"This slide MUST look visually different from slides 1–{max(n-1,1)} "
                f"(different hero objects, different chip words, different headline).\n"
                f"FULL-BLEED ice-blue #E8F0F8 — never draw white side panels, black background, transparency, or a second background.\n"
                f"HERO ULTRA-PREMIUM clay-3D cluster (~28% height, UNIQUE to slide {n}): {hero}\n"
                f"HEADLINE (exact, required, unique): {hl}\n"
                f"SUPPORTING LINE (exact, REQUIRED — deeper insight, not a vague slogan): {sup}\n"
                f"SOFT CALLOUT (short insight if space — from body): {body_txt}\n"
                f"BOTTOM CHIPS — three equal white rounded chips at 60–74% height "
                f"(FULL one-word labels ABOVE the empty footer zone):\n"
                f"  1) {b0}  2) {b1}  3) {b2}\n"
                f"Each chip: soft-touch rounded 3D icon + the ONE complete word fully visible. "
                f"Never truncate. Never multi-word. Never Steady/Plan/Less fragments.\n"
                "Reserve bottom ~22% EMPTY ice-blue for SEBI composite — chips must NOT enter that zone.\n"
                "Chip labels MUST match this education beat — NEVER use Inflows, Outflows, "
                "Limits, FDI impact, FX impact, RBI role, or Policy tools unless those exact words "
                "are in the approved headline/body above.\n"
                "ALL text must be plain printed English sans-serif with perfect spelling. No embossed/glowing/outlined text effects.\n"
                + (
                    f"CTA (closing): {_q(slide_cta, 40)}\n"
                    if is_last and slide_cta
                    else ""
                )
                + "LAYOUT STANDARD: headline → supporting → hero 3D → orange divider → "
                "3 one-word chips (60–74%) → empty bottom ~22% for legal footer (do not bake SEBI text).\n"
                "FAIL if: cloned look vs prior slides, headline-only, missing supporting, truncated chips, "
                "chips overlapping footer, white side bars, black/charcoal background, or wrong-topic FDI/FX chips."
            )[:6500]
            slide_url = await _generate_one_image(
                slide_prompt, size, f"-slide-{n}", composite_sebi_footer=True
            )
            generated_urls.append(slide_url)
    else:
        # Static / infographic / ranking — always AI image path (no Pillow board)
        text_bake_suffix = _error_free_text_block(
            [
                ("HEADLINE", _q(headline, 140)),
                ("SUPPORTING LINE", _q(supporting, 180)),
                ("BODY", _q(body, 260)),
                ("CTA", _q(cta, 60)),
                ("PROBLEM", _q(problem_statement, 160)),
                ("SOLUTION", _q(solution_statement, 160)),
                ("SECTIONS", _q(sections, 220)),
                ("STATS", _q(stat_highlights, 160)),
                ("PROOF POINTS", _q(proof_points, 180)),
                ("PROCESS STEPS", _q(process_steps, 160)),
                ("QUOTE", _q(customer_quote, 160)),
                ("QUOTE ATTRIBUTION", _q(customer_name, 60)),
                (
                    "SOURCE FOOTER",
                    _q(
                        (blueprint.source_footer if blueprint else "") or "",
                        80,
                    ),
                ),
            ],
            is_carousel=False,
        )
        # Build ultra-exact card bake lines for hub/ranking (cuts AI gibberish)
        card_bake = ""
        if blueprint and (blueprint.sections or []):
            card_lines = [
                "\nEXACT CARD / ROW TEXT — bake ONLY these quoted strings (zero invented words):\n"
            ]
            for i, sec in enumerate((blueprint.sections or [])[:15], start=1):
                label = (sec.section_label or f"Item {i}").strip()
                facts = [str(x).strip() for x in (sec.includes or []) if str(x).strip()][:2]
                if sec.stat and str(sec.stat).strip():
                    facts = [str(sec.stat).strip()] + facts
                facts = facts[:2]
                card_lines.append(f'CARD {i} name: "{label}"\n')
                for j, fact in enumerate(facts, start=1):
                    # Keep each fact short so the image model doesn't garble
                    short = " ".join(fact.split()[:10])
                    card_lines.append(f'CARD {i} line {j}: "{short}"\n')
            card_lines.append(
                "Never invent extra sentences on cards. Never use £ — only ₹ or %.\n"
                "If a fact does not fit, shorten spacing — do NOT invent filler words.\n"
            )
            card_bake = "".join(card_lines)

        layout_hint = (
            f"\n{NO_SEBI_STATIC_RULE}\n"
            "Use full canvas for content — no legal footer strip.\n"
            "BACKGROUND MUST be ice-blue #E8F0F8 — NEVER pure black, charcoal, or dark grain.\n"
            f"{ICON_STYLE_LOCK}\n"
        )
        if blueprint and blueprint.layout_type == "static_hub_facts":
            layout_hint = (
                "\nLAYOUT LOCK — HUB + 5 FACT CARDS WITH ICONS:\n"
                "- Clean ice-blue #E8F0F8 background. NEVER black/charcoal. "
                "NO watermark, NO giant J, NO JIRAAF text, NO giraffe.\n"
                "- Center: strong ULTRA-PREMIUM clay-3D bank building icon in a circle.\n"
                "- FIVE white rounded cards around the hub — EVERY card MUST have its own "
                "distinct LARGE ULTRA-PREMIUM clay-3D icon (vault / coins / shield / bank / cards) "
                "+ exact bank name + 1–2 SHORT exact fact lines only.\n"
                "- Card body text = ONLY the quoted CARD lines below. No gibberish. No invented words.\n"
                "- Do NOT draw official trademark bank logos — premium 3D icons + typed names only.\n"
                "- Tiny empty top-right pocket only for Brand Space logo composite later.\n"
                f"- {NO_SEBI_STATIC_RULE}\n"
                f"{ICON_STYLE_LOCK}\n"
            )
        elif blueprint and blueprint.layout_type == "static_ranking":
            from app.prompts.jiraaf_layout import is_trade_data_board

            if is_trade_data_board(user_prompt or ""):
                layout_hint = (
                    "\nLAYOUT LOCK — TRADE DEFICIT DATA BOARD (Jiraaf India–Russia sample DNA):\n"
                    "- Portrait 1080x1350, ice-blue #E8F0F8 background.\n"
                    "- Punchy data headline + one factual subtitle.\n"
                    "- Dual-bar table: EXPORT (orange bars left) | TRADE BALANCE (center) | "
                    "IMPORT (navy bars right), Billion USD, one row per fiscal year.\n"
                    "- Bar lengths must match the numbers visually.\n"
                    "- Bottom box: What India buys most — category + USD amounts from CARD lines.\n"
                    "- Source footer from research (e.g. Ministry of Commerce).\n"
                    "- FORBIDDEN: FD briefcase, handshake hero as main story, Capital Preservation, "
                    "Regular Income, Liquidity Management, bond cards, wrong flags, investment CTAs.\n"
                    f"- {NO_SEBI_STATIC_RULE}\n"
                )
            else:
                layout_hint = (
                    "\nLAYOUT LOCK — RANKING / DATA ROWS:\n"
                    "- Ice-blue background. Ranked Name | % | amount rows from CARD lines.\n"
                    "- Real flat flags only for country ranks. No bond benefit cards.\n"
                    f"- {NO_SEBI_STATIC_RULE}\n"
                )
        single_url = await _generate_one_image(
            (image_gen_prompt + layout_hint + card_bake + text_bake_suffix)[:6000],
            size,
            composite_sebi_footer=False,
        )
        generated_urls.append(single_url)

    # Set the generated image fields on the output Pydantic model
    output.generated_image_url = generated_urls[0] if generated_urls else ""
    output.generated_image_urls = generated_urls

    total_l8_latency = metadata["latency_ms"]
    total_l8_input = metadata["input_tokens"]
    total_l8_output = metadata["output_tokens"]
    try:
        total_l8_latency += expander_meta["latency_ms"]
        total_l8_input += expander_meta["input_tokens"]
        total_l8_output += expander_meta["output_tokens"]
    except (KeyError, TypeError):
        pass

    return {
        "visual_reasoning": output,
        "layer_latencies": {"l8_visual_reasoning": total_l8_latency},
        "token_usage": {
            "l8_visual_reasoning": {
                "input_tokens": total_l8_input,
                "output_tokens": total_l8_output,
            }
        },
    }
