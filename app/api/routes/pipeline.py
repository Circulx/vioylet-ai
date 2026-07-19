from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.graph.graph import build_violyt_graph
from app.graph.state import ViolytState
from app.schemas.pipeline import PipelineRunRequest, PipelineRunResponse

router = APIRouter(tags=["pipeline"])


@router.post("/run", response_model=PipelineRunResponse, status_code=202)
async def run_pipeline(request: PipelineRunRequest) -> PipelineRunResponse:
    """Run the Violyt pipeline through Layer 4 (Brand Intelligence) synchronously.

    This is a synchronous endpoint for Milestone 4 testing. Future milestones will
    make it async with job_id + WebSocket streaming.
    """
    run_id = str(uuid4())

    initial_state: ViolytState = {
        "user_prompt": request.user_prompt,
        "brand_id": request.brand_id,
        "platform": request.platform,
        "format": request.format,
        "run_id": run_id,
        "repair_count": 0,
    }

    try:
        graph = build_violyt_graph().compile()
        final_state = await graph.ainvoke(initial_state)
    except Exception as exc:
        return PipelineRunResponse(
            run_id=run_id,
            status="failed",
            brand_id=request.brand_id,
            user_prompt=request.user_prompt,
            platform=request.platform,
            format=request.format,
            error=str(exc),
        )

    def _dump(obj):
        return obj.model_dump() if hasattr(obj, "model_dump") else obj

    return PipelineRunResponse(
        run_id=run_id,
        status="complete",
        brand_id=request.brand_id,
        user_prompt=request.user_prompt,
        platform=request.platform,
        format=request.format,
        brand_context=_dump(final_state.get("brand_context")),
        brand_intelligence=_dump(final_state.get("brand_intelligence")),
        campaign_brief=_dump(final_state.get("campaign_brief")),
        strategic_reasoning=_dump(final_state.get("strategic_reasoning")),
        creative_concepts=_dump(final_state.get("creative_concepts")),
        format_plan=_dump(final_state.get("format_plan")),
        copy=_dump(final_state.get("copy")),
        visual_reasoning=_dump(final_state.get("visual_reasoning")),
        scene_graph=_dump(final_state.get("scene_graph")),
        final_output=final_state.get("final_output"),
        layer_latencies=final_state.get("layer_latencies"),
        token_usage=final_state.get("token_usage"),
        error=final_state.get("error"),
    )
