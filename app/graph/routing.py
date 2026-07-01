from app.graph.state import ViolytState


def route_evaluation(state: ViolytState) -> str:
    """Route from L10 evaluation to renderer (pass) or repair (fail)."""
    evaluation = state.get("evaluation")

    if state.get("force_repair"):
        return "repair"

    if evaluation is None:
        return "repair"

    if not evaluation.overall_pass:
        return "repair"

    if evaluation.contamination_risk != "low":
        return "repair"

    threshold = 0.75
    scores = [
        evaluation.brand_alignment_score,
        evaluation.prompt_match_score,
        evaluation.audience_relevance_score,
        evaluation.originality_score,
        evaluation.visual_quality_score,
        evaluation.format_fit_score,
        evaluation.brand_uniqueness_score,
        evaluation.strategic_quality_score,
    ]
    if any(score < threshold for score in scores):
        return "repair"

    return "pass"


def route_repair(state: ViolytState) -> str:
    """Route from repair layer back to concept_engine (retry) or END (fail)."""
    repair_count = state.get("repair_count", 0)
    return "retry" if repair_count < 2 else "fail"
