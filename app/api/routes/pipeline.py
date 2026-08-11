from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.graph.checkpoint import (
    delete_checkpoint,
    get_checkpoint,
    save_checkpoint,
    serialize_state_for_checkpoint,
    update_checkpoint_status,
)
from app.graph.graph import build_phase1_graph, build_phase2_graph
from app.graph.models.layer1_models import BrandContextOutput
from app.graph.models.layer2_models import BrandIntelligenceOutput
from app.graph.models.layer3_models import CampaignBriefOutput
from app.graph.models.layer4_models import StrategicReasoningOutput
from app.graph.models.layer5_models import CreativeConceptsOutput
from app.graph.models.layer6_models import FormatPlanOutput
from app.graph.models.content_intelligence_models import ContentIntelligenceOutput
from app.graph.models.layer7_models import CopyOutput
from app.graph.models.layer7b_models import ContentValidationOutput
from app.graph.models.layer7c_models import CreativeBlueprint
from app.graph.models.layer8_models import VisualReasoningOutput
from app.graph.models.layer9_models import SceneGraphOutput
from app.graph.state import ViolytState
from app.schemas.pipeline import (
    PipelineApproveRequest,
    PipelineEditImageTextRequest,
    PipelineEditImageTextResponse,
    PipelineRejectRequest,
    PipelineRunRequest,
    PipelineRunResponse,
)
from app.services.copy_proofread import proofread_blueprint
from app.services.image_text_edit import apply_text_edits
from app.services.blueprint_quality import finalize_blueprint_for_card
from app.prompts.jiraaf_layout import classify_layout
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["pipeline"])


def _dump(obj):
    return obj.model_dump() if hasattr(obj, "model_dump") else obj


def _hydrate_state(raw: dict) -> ViolytState:
    """Rebuild Pydantic layer outputs from a serialized checkpoint dict."""
    state: ViolytState = {
        "user_prompt": raw.get("user_prompt", ""),
        "brand_id": raw.get("brand_id", ""),
        "platform": raw.get("platform", "linkedin"),
        "format": raw.get("format", "static"),
        "run_id": raw.get("run_id"),
        "org_id": raw.get("org_id"),
        "data_version": raw.get("data_version"),
        "repair_count": raw.get("repair_count", 0),
        "force_repair": raw.get("force_repair", False),
        "layer_latencies": raw.get("layer_latencies") or {},
        "token_usage": raw.get("token_usage") or {},
        "error": raw.get("error"),
        "retrieval_log": raw.get("retrieval_log"),
        "repair_instructions": raw.get("repair_instructions"),
        "final_output": raw.get("final_output"),
        "live_research": raw.get("live_research") or {},
    }

    mapping = [
        ("brand_context", BrandContextOutput),
        ("brand_intelligence", BrandIntelligenceOutput),
        ("campaign_brief", CampaignBriefOutput),
        ("strategic_reasoning", StrategicReasoningOutput),
        ("creative_concepts", CreativeConceptsOutput),
        ("format_plan", FormatPlanOutput),
        ("content_intelligence", ContentIntelligenceOutput),
        ("copy", CopyOutput),
        ("content_validation", ContentValidationOutput),
        ("creative_blueprint", CreativeBlueprint),
        ("visual_reasoning", VisualReasoningOutput),
        ("scene_graph", SceneGraphOutput),
    ]
    for key, model in mapping:
        val = raw.get(key)
        if val is None:
            continue
        if isinstance(val, model):
            state[key] = val  # type: ignore[literal-required]
        elif isinstance(val, dict):
            try:
                state[key] = model.model_validate(val)  # type: ignore[literal-required]
            except Exception:
                # Skip non-critical corrupt checkpoint fields; Phase 2 needs blueprint/copy/etc.
                continue

    return state


def _response_from_state(
    *,
    run_id: str,
    status: str,
    request_brand_id: str,
    request_prompt: str,
    request_platform: str,
    request_format: str,
    state: dict,
    error: str | None = None,
) -> PipelineRunResponse:
    return PipelineRunResponse(
        run_id=run_id,
        status=status,
        brand_id=request_brand_id or state.get("brand_id", ""),
        user_prompt=request_prompt or state.get("user_prompt", ""),
        platform=request_platform or state.get("platform", "linkedin"),
        format=request_format or state.get("format", "static"),
        brand_context=_dump(state.get("brand_context")),
        brand_intelligence=_dump(state.get("brand_intelligence")),
        campaign_brief=_dump(state.get("campaign_brief")),
        strategic_reasoning=_dump(state.get("strategic_reasoning")),
        creative_concepts=_dump(state.get("creative_concepts")),
        format_plan=_dump(state.get("format_plan")),
        content_intelligence=_dump(state.get("content_intelligence")),
        copy=_dump(state.get("copy")),
        content_validation=_dump(state.get("content_validation")),
        creative_blueprint=_dump(state.get("creative_blueprint")),
        visual_reasoning=_dump(state.get("visual_reasoning")),
        scene_graph=_dump(state.get("scene_graph")),
        final_output=state.get("final_output"),
        layer_latencies=state.get("layer_latencies"),
        token_usage=state.get("token_usage"),
        error=error or state.get("error"),
    )


@router.post("/run", response_model=PipelineRunResponse, status_code=202)
async def run_pipeline(request: PipelineRunRequest) -> PipelineRunResponse:
    """Phase 1: run L1→L7c and pause for Creative Blueprint approval."""
    run_id = str(uuid4())
    logger.info(
        "pipeline.run.start",
        run_id=run_id,
        brand_id=request.brand_id,
        platform=request.platform,
        format=request.format,
        prompt_preview=(request.user_prompt or "")[:120],
    )

    initial_state: ViolytState = {
        "user_prompt": request.user_prompt,
        "brand_id": request.brand_id,
        "platform": request.platform,
        "format": request.format,
        "run_id": run_id,
        "repair_count": 0,
    }

    # Intent router: pick layout + format from the prompt.
    # Strong data intents (trade / rank / hub) OVERRIDE a wrong format click
    # so the user does NOT need to rewrite the prompt.
    fmt_in = str(request.format or "").strip().lower()
    layout = classify_layout(request.user_prompt, fmt_in or None)
    if (
        not fmt_in
        or fmt_in == "auto"
        or layout.reason.startswith("intent_")
    ):
        initial_state["format"] = layout.suggested_format
        logger.info(
            "pipeline.run.layout_routed",
            layout=layout.layout_type,
            format=layout.suggested_format,
            reason=layout.reason,
            user_format=fmt_in or "auto",
        )

    try:
        graph = build_phase1_graph().compile()
        final_state = await graph.ainvoke(initial_state)
    except Exception as exc:
        logger.error("pipeline.run.failed", run_id=run_id, error=str(exc), exc_info=True)
        return _response_from_state(
            run_id=run_id,
            status="failed",
            request_brand_id=request.brand_id,
            request_prompt=request.user_prompt,
            request_platform=request.platform,
            request_format=request.format,
            state=dict(initial_state),
            error=str(exc),
        )

    serialized = serialize_state_for_checkpoint(dict(final_state))
    save_checkpoint(run_id, serialized, status="awaiting_blueprint_approval")
    logger.info("pipeline.run.phase1_complete", run_id=run_id, status="awaiting_blueprint_approval")

    return _response_from_state(
        run_id=run_id,
        status="awaiting_blueprint_approval",
        request_brand_id=request.brand_id,
        request_prompt=request.user_prompt,
        request_platform=request.platform,
        request_format=request.format,
        state=final_state,
    )


@router.post("/approve", response_model=PipelineRunResponse)
async def approve_blueprint(request: PipelineApproveRequest) -> PipelineRunResponse:
    """Phase 2: apply approved blueprint and run L8→renderer."""
    logger.info("pipeline.approve.start", run_id=request.run_id)
    raw = get_checkpoint(request.run_id)
    if not raw:
        logger.warning("pipeline.approve.missing_checkpoint", run_id=request.run_id)
        raise HTTPException(
            status_code=404,
            detail="Pipeline run not found or expired. Start a new run (server restarts clear old in-memory runs; checkpoints are now saved to disk).",
        )

    if request.creative_blueprint is not None:
        try:
            bp = CreativeBlueprint.model_validate(request.creative_blueprint)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Invalid creative_blueprint: {exc}") from exc
        try:
            bp = await proofread_blueprint(bp, use_llm=False)
            logger.info("pipeline.approve.proofread_ok")
        except Exception as exc:
            logger.warning("pipeline.approve.proofread_failed", error=str(exc))
        user_prompt = str(raw.get("user_prompt", ""))
        fmt = str(raw.get("format", bp.format or "static"))
        layout = classify_layout(user_prompt, fmt)
        bp = finalize_blueprint_for_card(
            bp,
            layout_type=layout.layout_type,
            user_prompt=user_prompt,
            live_research=raw.get("live_research") or {},
        )
        if bp.missing_critical:
            logger.warning(
                "pipeline.approve.blueprint_quality_flags",
                missing=bp.missing_critical,
                layout=layout.layout_type,
            )
        raw["creative_blueprint"] = bp.model_dump()

    if not raw.get("creative_blueprint"):
        raise HTTPException(status_code=400, detail="No creative_blueprint available to approve")

    # Always proofread checkpoint blueprint even if client didn't resend edits
    if request.creative_blueprint is None and raw.get("creative_blueprint"):
        try:
            bp = CreativeBlueprint.model_validate(raw["creative_blueprint"])
            bp = await proofread_blueprint(bp, use_llm=False)
            user_prompt = str(raw.get("user_prompt", ""))
            fmt = str(raw.get("format", bp.format or "static"))
            layout = classify_layout(user_prompt, fmt)
            bp = finalize_blueprint_for_card(
                bp,
                layout_type=layout.layout_type,
                user_prompt=user_prompt,
                live_research=raw.get("live_research") or {},
            )
            raw["creative_blueprint"] = bp.model_dump()
        except Exception as exc:
            logger.warning("pipeline.approve.checkpoint_proofread_failed", error=str(exc))
    update_checkpoint_status(request.run_id, "generating")
    state = _hydrate_state(raw)

    try:
        graph = build_phase2_graph().compile()
        final_state = await graph.ainvoke(state)
    except Exception as exc:
        update_checkpoint_status(request.run_id, "failed")
        return _response_from_state(
            run_id=request.run_id,
            status="failed",
            request_brand_id=str(raw.get("brand_id", "")),
            request_prompt=str(raw.get("user_prompt", "")),
            request_platform=str(raw.get("platform", "linkedin")),
            request_format=str(raw.get("format", "static")),
            state=raw,
            error=str(exc),
        )

    delete_checkpoint(request.run_id)

    return _response_from_state(
        run_id=request.run_id,
        status="complete",
        request_brand_id=str(raw.get("brand_id", "")),
        request_prompt=str(raw.get("user_prompt", "")),
        request_platform=str(raw.get("platform", "linkedin")),
        request_format=str(raw.get("format", "static")),
        state=final_state,
    )


@router.post("/reject", response_model=PipelineRunResponse)
async def reject_blueprint(request: PipelineRejectRequest) -> PipelineRunResponse:
    """Cancel a paused Phase-1 run."""
    raw = get_checkpoint(request.run_id)
    if not raw:
        raise HTTPException(status_code=404, detail="Pipeline run not found or expired")

    delete_checkpoint(request.run_id)
    return _response_from_state(
        run_id=request.run_id,
        status="cancelled",
        request_brand_id=str(raw.get("brand_id", "")),
        request_prompt=str(raw.get("user_prompt", "")),
        request_platform=str(raw.get("platform", "linkedin")),
        request_format=str(raw.get("format", "static")),
        state=raw,
    )


@router.post("/edit-image-text", response_model=PipelineEditImageTextResponse)
async def edit_image_text(request: PipelineEditImageTextRequest) -> PipelineEditImageTextResponse:
    """Fix spelling / copy on a generated image inside chat (real fonts, logo untouched)."""
    if not (request.headline or request.supporting_line or request.body or request.cta):
        raise HTTPException(status_code=400, detail="Provide at least one text field to apply")
    try:
        new_url = apply_text_edits(
            image_url=request.image_url,
            headline=request.headline,
            supporting_line=request.supporting_line,
            body=request.body,
            cta=request.cta,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found in storage")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("pipeline.edit_image_text_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Could not edit image text: {exc}") from exc

    return PipelineEditImageTextResponse(
        image_url=new_url,
        headline=request.headline,
        supporting_line=request.supporting_line,
        body=request.body,
        cta=request.cta,
    )
