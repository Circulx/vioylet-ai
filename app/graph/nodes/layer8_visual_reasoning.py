from __future__ import annotations

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
from app.services.copy_proofread import NO_AI_LOGO_RULE, SPELLING_ACCURACY_RULE

logger = get_logger(__name__)

_router = LLMRouter()
_prompt_builder = VisualReasoningPromptBuilder()


def _q(value: object, max_chars: int = 280) -> str:
    """Quote exact copy for image prompts; trim long strings to reduce garbling."""
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
    if not text:
        return '""'
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip(" ,.;:") + "…"
    safe = text.replace('"', "'")
    return f'"{safe}"'


def _error_free_text_block(lines: list[tuple[str, str]]) -> str:
    """Build quoted-text bake instructions (font + contrast + exact strings)."""
    parts = [
        "\n\nCRITICAL — ERROR-FREE BAKED TEXT (quoted strings are EXACT):\n",
        "Typography: bold clean sans-serif / block letters only.\n",
        "Contrast: dark navy text (#1B2A4A) on light background (#E8F2FA / #F7F8FA).\n",
        "Render ONLY the quoted strings below — letter-perfect, never truncate headline with '...'.\n",
        "Do not invent words. Do not leave empty cards. No Pillow overlay will be applied.\n",
    ]
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

    # Convert Concept Pydantic model to dict
    concept_dict = {
        "concept_name": recommended.concept_name,
        "core_idea": recommended.core_idea,
        "hook": recommended.hook,
        "narrative_angle": recommended.narrative_angle,
        "visual_angle": recommended.visual_angle,
    }

    system = _prompt_builder.build_system(fmt=fmt)
    user = _prompt_builder.build_user(
        brand_intelligence=brand_intelligence,
        format_plan=format_plan,
        copy=copy,
        concept=concept_dict,
        user_prompt=user_prompt,
        fmt=fmt,
    )
    if blueprint:
        story = "; ".join(blueprint.story_flow or [])
        user = (
            user
            + "\n\nAPPROVED CREATIVE BLUEPRINT (bake this EXACT text into the image — no Pillow overlay):\n"
            + f"purpose={blueprint.purpose}\nlayout={blueprint.layout_archetype}\n"
            + f"text_density={blueprint.text_density}\nhierarchy={blueprint.visual_hierarchy}\n"
            + f"hook={blueprint.hook}\nstory_flow={story}\n"
            + f"headline={headline}\nsupporting_line={supporting}\nbody={body}\ncta={cta}\n"
            + f"problem={problem_statement}\nsolution={solution_statement}\n"
            + f"sections={sections}\nstats={stat_highlights}\nproof={proof_points}\n"
            + f"process_steps={process_steps}\nquote={customer_quote}\nquote_by={customer_name}\n"
            + "CRITICAL: Generate a FINISHED creative. Render the approved strings as sharp typography in the image. "
            "Do not leave empty shells. Do not invent alternate copy."
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
            temperature=0.85,
            max_tokens=2048,
        )
        logger.info(
            "visual_reasoning.prompt_expansion_complete",
            expanded_prompt_len=len(expanded_prompt),
            expander_tokens=expander_meta.get("output_tokens", 0),
        )
        image_gen_prompt = expanded_prompt
        output.image_prompt_direction = expanded_prompt
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

    # 3. Size computation based on platform and format
    if fmt == "carousel":
        # Sample carousel slides are vertical educational 4:5
        size = "1080x1350"
    elif fmt == "infographic":
        size = "1080x1350"
    elif fmt == "banner":
        size = "1200x628"
    elif fmt == "newsletter":
        size = "600x800"
    elif fmt == "blog":
        size = "1200x630"
    elif fmt == "email":
        size = "600x800"
    elif fmt == "presentation":
        size = "1920x1080"
    elif fmt == "ad_creative":
        size = "1080x1080"
    else:
        ratios = {
            "linkedin": "1200x627",
            "instagram": "1080x1080",
            "twitter": "1200x675",
            "x": "1200x675",
            "facebook": "1200x628",
            "website": "1200x628",
            "email": "600x800",
            "internal": "1200x627",
            "story": "1080x1920",
        }
        size = ratios.get(platform, "1024x1024")

    # 4. Image generation with gpt-image-1 + brand logo composite, falling back to SDXL/Mock
    async def _generate_one_image(prompt: str, image_size: str, fallback_suffix: str = "") -> str:
        # Brand logo comes from Brand Space compositing — never from the image model.
        safe_prompt = (prompt + NO_AI_LOGO_RULE + SPELLING_ACCURACY_RULE)[:6000]
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
                return f"/storage/generated-fallback-{brand_id}{fallback_suffix}.png"

    generated_urls: list[str] = []
    if fmt == "carousel" and format_plan.slide_plan:
        # Prefer approved blueprint slides; fall back to L7 slide_copy
        slide_copy_by_number = {
            s.slide_number: s for s in (copy.slide_copy or [])
        }
        blueprint_slides = {
            s.slide_number: s for s in ((blueprint.slides if blueprint else None) or [])
        }
        for slide in format_plan.slide_plan:
            bp_slide = blueprint_slides.get(slide.slide_number)
            slide_copy = slide_copy_by_number.get(slide.slide_number)
            slide_headline = (
                bp_slide.headline if bp_slide else (slide_copy.headline if slide_copy else "")
            )
            slide_body = bp_slide.body if bp_slide else (slide_copy.body if slide_copy else "")
            slide_cta = (
                (bp_slide.cta if bp_slide else None)
                or (slide_copy.cta if slide_copy else "")
                or ""
            )
            slide_supporting = (
                (bp_slide.supporting_line if bp_slide else None)
                or (getattr(slide_copy, "supporting_line", None) if slide_copy else None)
                or ""
            )
            slide_prompt = (
                f"{image_gen_prompt}\n\n"
                f"--- CAROUSEL SLIDE {slide.slide_number} (SAMPLE SYSTEM) ---\n"
                f"Background MUST remain solid #E8F2FA (identical across all slides).\n"
                f"Focus: {slide.focus}\n"
                f"Visual intent: {slide.visual_intent}\n"
                "Typography: bold clean sans-serif, dark navy on light blue, high contrast.\n"
                f"HEADLINE (exact): {_q(slide_headline, 120)}\n"
                f"SUPPORTING LINE (exact): {_q(slide_supporting, 160)}\n"
                f"BODY / CALLOUT (exact): {_q(slide_body, 220)}\n"
                f"CTA (exact, closing slides only): {_q(slide_cta, 60)}\n"
                "Layout: headline → supporting → soft blue callout → multi-object ultra-premium 3D hero cluster "
                "→ orange divider → THREE bottom insight cards with unique 3D icons + bold short labels.\n"
                "Keep labels to 1–2 correctly spelled words. Bake all quoted text into the image."
            )[:6000]
            slide_url = await _generate_one_image(slide_prompt, size, f"-slide-{slide.slide_number}")
            generated_urls.append(slide_url)
    else:
        # Static / infographic / other — single finished image only
        # (Carousel is the only multi-image format.)
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
            ]
        )
        single_url = await _generate_one_image((image_gen_prompt + text_bake_suffix)[:6000], size)
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
