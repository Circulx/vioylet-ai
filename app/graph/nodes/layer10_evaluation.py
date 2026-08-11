from __future__ import annotations

"""Layer 10 — real Evaluate gate for Phase 1 blueprints (and full graph)."""

from app.core.logging import get_logger
from app.graph.models.layer10_models import EvaluationOutput, RepairInstruction
from app.graph.state import ViolytState
from app.services.blueprint_quality import (
    blueprint_passes_editorial_qa,
    evaluate_blueprint_gate,
    score_blueprint_editorial_qa,
)

logger = get_logger(__name__)


async def layer10_evaluation(state: ViolytState) -> dict:
    if state.get("force_repair"):
        return {
            "evaluation": EvaluationOutput(
                brand_alignment_score=0.65,
                prompt_match_score=0.80,
                audience_relevance_score=0.78,
                originality_score=0.61,
                visual_quality_score=0.76,
                format_fit_score=0.79,
                brand_uniqueness_score=0.70,
                strategic_quality_score=0.74,
                contamination_risk="low",
                overall_pass=False,
                required_repairs=[
                    RepairInstruction(
                        target_layer="l5_concept_engine",
                        failure_reason="Forced repair for loop testing",
                        repair_action="Regenerate with stronger brand-specific insight tension",
                        priority="major",
                    )
                ],
                evaluator_reasoning="Forced failure stub for repair-loop testing.",
            ),
            "repair_target": "l5",
            "layer_latencies": {"l10_evaluation": 0},
        }

    blueprint = state.get("creative_blueprint")
    content_intelligence = state.get("content_intelligence")
    user_prompt = state.get("user_prompt", "")
    brand_intelligence = state.get("brand_intelligence")

    if blueprint is None:
        return {
            "evaluation": EvaluationOutput(
                brand_alignment_score=0.4,
                prompt_match_score=0.4,
                audience_relevance_score=0.4,
                originality_score=0.4,
                visual_quality_score=0.4,
                format_fit_score=0.4,
                brand_uniqueness_score=0.4,
                strategic_quality_score=0.4,
                contamination_risk="medium",
                overall_pass=False,
                required_repairs=[
                    RepairInstruction(
                        target_layer="l7c_content_prep",
                        failure_reason="Missing creative blueprint",
                        repair_action="Regenerate blueprint from Content Intelligence package",
                        priority="critical",
                    )
                ],
                evaluator_reasoning="No creative blueprint present.",
            ),
            "repair_target": "l7c",
            "layer_latencies": {"l10_evaluation": 0},
        }

    evaluation, repair_target = evaluate_blueprint_gate(
        blueprint,
        user_prompt=user_prompt,
        content_intelligence=content_intelligence,
        brand_intelligence=brand_intelligence,
    )

    scores = score_blueprint_editorial_qa(
        blueprint,
        user_prompt=user_prompt,
        content_intelligence=content_intelligence,
    )
    logger.info(
        "evaluation.complete",
        overall_pass=evaluation.overall_pass,
        repair_target=repair_target,
        editorial=scores,
        passes_editorial=blueprint_passes_editorial_qa(scores),
    )

    return {
        "evaluation": evaluation,
        "repair_target": repair_target if not evaluation.overall_pass else None,
        "layer_latencies": {"l10_evaluation": 0},
    }
