from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal


class PipelineRunRequest(BaseModel):
    brand_id: str = Field(..., description="Brand space ID to run the pipeline for")
    user_prompt: str = Field(..., description="User's campaign request")
    platform: Literal["linkedin", "instagram", "twitter"] = Field(default="linkedin")
    format: Literal["static", "carousel", "infographic"] = Field(default="static")


class PipelineRunResponse(BaseModel):
    run_id: str | None = Field(default=None)
    status: str = Field(default="complete")
    brand_id: str
    user_prompt: str
    platform: str
    format: str
    brand_context: dict | None = Field(default=None)
    brand_intelligence: dict | None = Field(default=None)
    campaign_brief: dict | None = Field(default=None)
    strategic_reasoning: dict | None = Field(default=None)
    creative_concepts: dict | None = Field(default=None)
    format_plan: dict | None = Field(default=None)
    copy: dict | None = Field(default=None)
    visual_reasoning: dict | None = Field(default=None)
    scene_graph: dict | None = Field(default=None)
    final_output: dict | None = Field(default=None)
    layer_latencies: dict | None = Field(default=None)
    token_usage: dict | None = Field(default=None)
    error: str | None = Field(default=None)
