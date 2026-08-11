from app.graph.state import ViolytState


def route_evaluation(state: ViolytState) -> str:
    """Route from L10 evaluation to pass (END/renderer) or repair."""
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
    """Route repair to the failed layer (max 2), else fail/deliver."""
    repair_count = state.get("repair_count", 0)
    if repair_count >= 2:
        return "fail"

    target = (state.get("repair_target") or "l5").strip().lower()
    mapping = {
        "l6b": "retry_l6b",
        "content_intelligence": "retry_l6b",
        "insight": "retry_l6b",
        "l5": "retry_l5",
        "concept": "retry_l5",
        "l7": "retry_l7",
        "copy": "retry_l7",
        "l7c": "retry_l7c",
        "blueprint": "retry_l7c",
    }
    return mapping.get(target, "retry_l5")
