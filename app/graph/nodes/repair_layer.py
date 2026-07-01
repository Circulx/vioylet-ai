from app.graph.state import ViolytState


async def repair_layer(state: ViolytState) -> dict:
    repair_count = state.get("repair_count", 0)
    evaluation = state.get("evaluation")

    instructions = []
    if evaluation and evaluation.required_repairs:
        for r in evaluation.required_repairs:
            instructions.append(f"{r.target_layer}: {r.repair_action}")
    else:
        instructions.append("concept_engine: regenerate with stronger brand-specific tension")

    return {
        "repair_count": repair_count + 1,
        "repair_instructions": instructions,
    }
