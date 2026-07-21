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

logger = get_logger(__name__)

_router = LLMRouter()
_prompt_builder = VisualReasoningPromptBuilder()


async def layer8_visual_reasoning(state: ViolytState) -> dict:
    brand_intelligence = state.get("brand_intelligence")
    format_plan = state.get("format_plan")
    copy = state.get("copy")
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
        copy_headline=copy.headline,
        copy_body=copy.body,
        supporting_line=copy.supporting_line or "",
        cta=copy.cta or "",
        infographic_sections=[s.model_dump() for s in copy.infographic_sections],
        proof_points=copy.proof_points,
        stat_highlights=copy.stat_highlights,
        problem_statement=getattr(copy, "problem_statement", "") or "",
        solution_statement=getattr(copy, "solution_statement", "") or "",
        customer_quote=getattr(copy, "customer_quote", "") or "",
        customer_name=getattr(copy, "customer_name", "") or "",
        process_steps=getattr(copy, "process_steps", []) or [],
        format_strategy=format_plan.format_strategy,
        layout_archetype=format_plan.layout_archetype,
        platform=platform,
        initial_prompt=output.image_prompt_direction,
        user_prompt=user_prompt,
        dominant_visual_system=output.dominant_visual_system,
        fmt=fmt,
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
        # Carousel slide decks are best as 1:1 square for slide presentation on LinkedIn and Instagram
        size = "1080x1080"
    elif fmt == "infographic":
        # Infographics require a vertical portrait layout to fit detailed charts and tables
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
        try:
            dalle = DalleService()
            url = await dalle.generate_and_save(
                tenant_id=tenant_id,
                brand_space_id=brand_id,
                prompt=prompt,
                size=image_size,
                logo_storage_path=logo_storage_path,
                logo_zone_instruction=logo_zone_instruction,
            )
            logger.info("visual_reasoning.dalle_success", url=url, suffix=fallback_suffix)
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
                    prompt=prompt,
                    size=image_size,
                )
                logger.info("visual_reasoning.sdxl_success", url=url, suffix=fallback_suffix)
                return url
            except Exception as e_sdxl:
                logger.error(f"visual_reasoning.sdxl_failed{fallback_suffix}: {e_sdxl}")
                return f"/storage/generated-fallback-{brand_id}{fallback_suffix}.png"

    generated_urls: list[str] = []
    if fmt == "carousel" and format_plan.slide_plan:
        # Build a lookup for slide copy by slide_number
        slide_copy_by_number = {
            s.slide_number: s for s in (copy.slide_copy or [])
        }
        for slide in format_plan.slide_plan:
            slide_copy = slide_copy_by_number.get(slide.slide_number)
            slide_headline = slide_copy.headline if slide_copy else ""
            slide_body = slide_copy.body if slide_copy else ""
            slide_cta = slide_copy.cta if slide_copy else ""
            slide_prompt = (
                f"{image_gen_prompt}\n\n"
                f"--- SLIDE {slide.slide_number} SPECIFIC DIRECTION ---\n"
                f"Focus: {slide.focus}\n"
                f"Visual intent: {slide.visual_intent}\n"
                f"Headline for this slide: {slide_headline}\n"
                f"Body for this slide: {slide_body}\n"
                f"CTA for this slide: {slide_cta}\n"
                f"Render this as a single carousel slide image."
            )[:6000]
            slide_url = await _generate_one_image(slide_prompt, size, f"-slide-{slide.slide_number}")
            generated_urls.append(slide_url)
    else:
        # Static / infographic / story / single-image formats
        single_url = await _generate_one_image(image_gen_prompt[:6000], size)
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
