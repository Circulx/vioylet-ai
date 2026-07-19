from __future__ import annotations
from uuid import UUID, uuid4
from pathlib import Path
from copy import deepcopy

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.graph.state import ViolytState
from app.models.brand import BrandSpace
from app.services.image_generation.logo_fetcher import get_brand_logo_storage_path
from app.services.renderer import RendererService
from app.ai.contracts import (
    RendererInput,
    GenerationSceneGraph,
    SceneGraphCanvas,
    SceneGraphElement,
    SceneGraphGeometry,
    SceneGraphAssetBinding,
    StructuredTextPayload,
    GeneratedImageAsset,
    BlueprintPayload,
)

logger = get_logger(__name__)


async def renderer_node(state: ViolytState) -> dict:
    scene_graph = state.get("scene_graph")
    visual_reasoning = state.get("visual_reasoning")
    copy = state.get("copy")
    brand_id = state.get("brand_id", "unknown")
    platform = state.get("platform", "linkedin")
    fmt = state.get("format", "static")

    if not scene_graph or not visual_reasoning or not copy:
        logger.warning("renderer_node.missing_data_for_rendering")
        return {
            "final_output": {
                "platform": platform,
                "format": fmt,
                "canvas_ratio": scene_graph.platform_ratio if scene_graph else "1200x627",
                "asset_url": "https://example.com/mock/final_render.png",
                "render_status": "success",
                "message": "Creative layout generated (visual rendering skipped due to missing data).",
            }
        }

    # 1. Resolve tenant_id and brand logo storage path
    tenant_id = None
    logo_storage_path = None
    try:
        brand_uuid = UUID(str(brand_id)) if not isinstance(brand_id, UUID) else brand_id
        async with AsyncSessionLocal() as session:
            brand = await session.get(BrandSpace, brand_uuid)
            if brand:
                tenant_id = brand.tenant_id
            
            logo_storage_path = await get_brand_logo_storage_path(
                brand_space_id=brand_uuid,
                session=session,
            )
    except Exception as e:
        logger.warning(f"renderer_node.db_failed: {e}")

    if not tenant_id:
        tenant_id = UUID("00000000-0000-0000-0000-000000000000")

    # 2. Map SceneGraphOutput to GenerationSceneGraph
    canvas = SceneGraphCanvas(
        width=scene_graph.canvas_width,
        height=scene_graph.canvas_height,
        platform=scene_graph.platform,
    )

    elements = []
    assets_bindings = []

    for el in scene_graph.elements:
        role = el.element_id
        if el.element_type == "copy":
            if "headline" in el.element_id.lower():
                role = "headline"
            elif "supporting" in el.element_id.lower():
                role = "supporting_line"
            elif "body" in el.element_id.lower():
                role = "body"
            else:
                role = "body"
        elif el.element_type == "cta":
            role = "cta"
        elif el.element_type == "logo":
            role = "logo"
        elif el.element_type == "visual":
            role = "image"
        elif el.element_type == "background":
            role = "background"
        elif el.element_type == "decorative":
            role = "decorative_shape"

        geometry = SceneGraphGeometry(
            x=el.position.get("x", 0),
            y=el.position.get("y", 0),
            width=el.position.get("width", 100),
            height=el.position.get("height", 100),
            units="pixels"
        )

        asset = None
        if el.asset_url:
            # Storage expects path without leading '/storage/' prefix
            storage_path = el.asset_url.replace("/storage/", "")
            asset = SceneGraphAssetBinding(
                storage_path=storage_path,
                asset_role="hero_visual" if role == "image" else None
            )
            assets_bindings.append(asset)

        scene_el = SceneGraphElement(
            element_id=el.element_id,
            element_type=el.element_type,
            role=role,
            geometry=geometry,
            text=el.content,
            style=el.style or {},
            asset=asset,
            visible=True,
        )
        elements.append(scene_el)

    gen_scene_graph = GenerationSceneGraph(
        canvas=canvas,
        elements=elements,
        styles=scene_graph.styles or {},
        assets=assets_bindings,
        layout_mode="synthesized_layout",
    )

    is_infographic = fmt == "infographic"
    image_assets = []
    image_urls = visual_reasoning.generated_image_urls or []
    if visual_reasoning.generated_image_url and visual_reasoning.generated_image_url not in image_urls:
        image_urls.append(visual_reasoning.generated_image_url)
    for idx, img_url in enumerate(image_urls):
        if img_url:
            storage_path = img_url.replace("/storage/", "")
            image_assets.append(
                GeneratedImageAsset(
                    asset_id=uuid4(),
                    mime_type="image/png",
                    storage_path=storage_path,
                    width=scene_graph.canvas_width,
                    height=scene_graph.canvas_height,
                    asset_role="hero_visual" if idx == 0 else f"slide_visual_{idx + 1}"
                )
            )

    # 4. Resolve font asset paths
    repo_root = Path(__file__).resolve().parents[3]
    font_asset_paths = [
        str(repo_root / "frontend" / "public" / "fonts" / "DM_Sans" / "static" / "DMSans-Regular.ttf"),
        str(repo_root / "frontend" / "public" / "fonts" / "DM_Sans" / "static" / "DMSans-Bold.ttf"),
        str(repo_root / "frontend" / "public" / "fonts" / "Manrope" / "static" / "Manrope-Regular.ttf"),
        str(repo_root / "frontend" / "public" / "fonts" / "Manrope" / "static" / "Manrope-Bold.ttf"),
    ]

    brand_visual_rules = {
        "typography": {
            "uploaded_font_assets": [
                {"family_name": "DM_Sans", "storage_path": str(repo_root / "frontend" / "public" / "fonts" / "DM_Sans" / "static" / "DMSans-Regular.ttf")},
                {"family_name": "Manrope", "storage_path": str(repo_root / "frontend" / "public" / "fonts" / "Manrope" / "static" / "Manrope-Regular.ttf")}
            ]
        }
    }

    # 5. Build structured metadata — for infographics this is the primary content source.
    # The renderer reads render_sections, proof_points, stat_highlights, and
    # infographic_section_specs from text.metadata to draw the actual visible information.
    infographic_section_specs: list[dict] = []
    if is_infographic and hasattr(copy, "infographic_sections"):
        for sec in (copy.infographic_sections or []):
            infographic_section_specs.append(
                sec.model_dump() if hasattr(sec, "model_dump") else dict(sec)
            )

    # Build render_sections so the renderer knows exactly what text to place
    render_sections: dict = {
        "headline_display": copy.headline,
        "supporting_line": getattr(copy, "supporting_line", None) or "",
        "body_display": copy.body,
        "cta_display": copy.cta,
        "proof_points": getattr(copy, "proof_points", []) or [],
        "stat_highlights": getattr(copy, "stat_highlights", []) or [],
    }

    text_metadata: dict = {
        "render_sections": render_sections,
        "proof_points": getattr(copy, "proof_points", []) or [],
        "stat_highlights": getattr(copy, "stat_highlights", []) or [],
        "infographic_section_specs": infographic_section_specs,
        "problem_statement": getattr(copy, "problem_statement", None) or "",
        "solution_statement": getattr(copy, "solution_statement", None) or "",
        "customer_quote": getattr(copy, "customer_quote", None) or "",
        "customer_name": getattr(copy, "customer_name", None) or "",
        "process_steps": getattr(copy, "process_steps", []) or [],
        # Include ALL slide content for comprehensive display
        "slide_copy": [slide.model_dump() if hasattr(slide, "model_dump") else dict(slide) for slide in (getattr(copy, "slide_copy", []) or [])],
        "hashtags": getattr(copy, "hashtags", []) or [],
        "claim_safety_notes": getattr(copy, "claim_safety_notes", []) or [],
        # tell renderer to show the primary visual in the illustration section
        "text_content_plan": {"show_primary_visual": True},
    }

    # 6. Build RendererInput
    payload = RendererInput(
        tenant_id=tenant_id,
        brand_space_id=UUID(str(brand_id)) if not isinstance(brand_id, UUID) else brand_id,
        content_version_id=uuid4(),
        studio_panel={
            "size": {"width": scene_graph.canvas_width, "height": scene_graph.canvas_height},
            "format": fmt,
            "platform_preset": platform,
        },
        scene_graph=gen_scene_graph,
        text=StructuredTextPayload(
            headline=copy.headline,
            body=copy.body,
            cta=copy.cta,
            hashtags=copy.hashtags or [],
            metadata=text_metadata,
        ),
        logo_asset_path=logo_storage_path,
        image_assets=image_assets,
        font_asset_paths=font_asset_paths,
        brand_visual_rules=brand_visual_rules,
        blueprint=BlueprintPayload(
            layout_type=fmt,
            zones=[],
            hierarchy=[],
            text_blocks=[],
            image_zones=[],
            logo_rules={},
            cta_placement={},
            platform_preset=platform,
            export_format="png",
            overflow_strategy={"mode": "shrink_then_wrap", "deterministic": True},
            composition_plan={
                # For infographics: show the DALL-E image in the main illustration section.
                "text_content_plan": {"show_primary_visual": True},
            },
        )
    )

    # 6. Render
    final_image_urls: list[str] = []
    final_image_url = ""

    # Carousels need multiple slide images, so bypass the single-image renderer and use
    # the already-generated per-slide images directly.
    # Infographics are now generated as a single fully text-baked AI image (headline,
    # cards, stats, icons, CTA all rendered by the image model) plus a pixel-composited
    # brand logo — skip the PIL card/text renderer entirely for this format.
    if fmt in ("carousel", "infographic") and visual_reasoning.generated_image_urls:
        final_image_urls = [u for u in visual_reasoning.generated_image_urls if u]
        final_image_url = final_image_urls[0] if final_image_urls else visual_reasoning.generated_image_url
        logger.info(f"renderer_node.{fmt}_direct", slide_count=len(final_image_urls))
    else:
        try:
            async with AsyncSessionLocal() as session:
                renderer = RendererService(session)
                response = await renderer.render(payload)
                if response.preview_asset and response.preview_asset.get("storage_path"):
                    final_image_url = f"/storage/{response.preview_asset['storage_path']}"
                    final_image_urls.append(final_image_url)
                    logger.info("renderer_node.success composited_url=%s", final_image_url)
                else:
                    logger.warning("renderer_node.no_preview_asset response_keys=%s", list(response.model_dump().keys()) if hasattr(response, "model_dump") else "n/a")
        except Exception as e:
            logger.error("renderer_node.render_failed: %s", e, exc_info=True)

        # Fallback to visual_reasoning generated_image_url if compositing failed
        if not final_image_url:
            final_image_url = visual_reasoning.generated_image_url
            if final_image_url:
                final_image_urls.append(final_image_url)
                logger.warning("renderer_node.fallback_to_raw_image raw_url=%s", final_image_url)

    # Overwrite visual_reasoning.generated_image_url so frontend displays the composited/selected result.
    updated_visual_reasoning = deepcopy(visual_reasoning)
    updated_visual_reasoning.generated_image_url = final_image_url

    return {
        "visual_reasoning": updated_visual_reasoning,
        "final_output": {
            "platform": platform,
            "format": fmt,
            "canvas_ratio": scene_graph.platform_ratio if scene_graph else "1200x627",
            "asset_url": final_image_url,
            "asset_urls": final_image_urls,
            "slide_count": len(final_image_urls),
            "render_status": "success",
            "message": "Creative rendered successfully." if final_image_url else "Rendering failed.",
        }
    }
