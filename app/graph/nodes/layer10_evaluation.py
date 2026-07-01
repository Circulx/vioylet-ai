from app.graph.state import ViolytState
from app.graph.models.layer10_models import EvaluationOutput


async def layer10_evaluation(state: ViolytState) -> dict:
    # Default stub passes cleanly. Set state["force_repair"] = True to exercise the repair loop.
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
                required_repairs=[],
                evaluator_reasoning="Forced failure stub for repair-loop testing.",
            )
        }

    return {
        "evaluation": EvaluationOutput(
            brand_alignment_score=0.89,
            prompt_match_score=0.94,
            audience_relevance_score=0.85,
            originality_score=0.82,
            visual_quality_score=0.80,
            format_fit_score=0.88,
            brand_uniqueness_score=0.87,
            strategic_quality_score=0.90,
            contamination_risk="low",
            overall_pass=True,
            required_repairs=[],
            evaluator_reasoning="All 8 dimensions meet the 0.75 threshold; contamination risk is low.",
        )
    }
