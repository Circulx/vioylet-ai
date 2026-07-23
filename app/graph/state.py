from typing import Annotated, TypedDict, Optional, List, NotRequired

from app.graph.models.layer1_models import BrandContextOutput
from app.graph.models.layer2_models import BrandIntelligenceOutput
from app.graph.models.layer3_models import CampaignBriefOutput
from app.graph.models.layer4_models import StrategicReasoningOutput
from app.graph.models.layer5_models import CreativeConceptsOutput
from app.graph.models.layer6_models import FormatPlanOutput
from app.graph.models.layer7_models import CopyOutput
from app.graph.models.layer7b_models import ContentValidationOutput
from app.graph.models.layer7c_models import CreativeBlueprint
from app.graph.models.layer8_models import VisualReasoningOutput
from app.graph.models.layer9_models import SceneGraphOutput
from app.graph.models.layer10_models import EvaluationOutput


def _merge_dicts(left: dict | None, right: dict | None) -> dict:
    """Reducer for parallel node updates — merges both dicts."""
    result = dict(left or {})
    result.update(right or {})
    return result


class ViolytState(TypedDict):
    # ── Input fields (set at pipeline start) ──────────────────
    user_prompt: str
    brand_id: str
    platform: NotRequired[str]
    format: NotRequired[str]
    run_id: NotRequired[str]
    org_id: NotRequired[str]
    data_version: NotRequired[int]  # brand.data_version — used as cache key in L2

    # ── Layer outputs (set progressively) ─────────────────────
    brand_context: NotRequired[Optional[BrandContextOutput]]
    brand_intelligence: NotRequired[Optional[BrandIntelligenceOutput]]
    campaign_brief: NotRequired[Optional[CampaignBriefOutput]]
    strategic_reasoning: NotRequired[Optional[StrategicReasoningOutput]]
    creative_concepts: NotRequired[Optional[CreativeConceptsOutput]]
    format_plan: NotRequired[Optional[FormatPlanOutput]]
    copy: NotRequired[Optional[CopyOutput]]
    content_validation: NotRequired[Optional[ContentValidationOutput]]
    creative_blueprint: NotRequired[Optional[CreativeBlueprint]]
    visual_reasoning: NotRequired[Optional[VisualReasoningOutput]]
    scene_graph: NotRequired[Optional[SceneGraphOutput]]
    evaluation: NotRequired[Optional[EvaluationOutput]]

    # ── Control fields ─────────────────────────────────────────
    repair_count: NotRequired[int]
    repair_instructions: NotRequired[Optional[List[str]]]
    force_repair: NotRequired[bool]
    final_output: NotRequired[Optional[dict]]
    retrieval_log: NotRequired[Optional[dict]]
    layer_latencies: Annotated[dict, _merge_dicts]
    token_usage: Annotated[dict, _merge_dicts]
    error: NotRequired[Optional[str]]
