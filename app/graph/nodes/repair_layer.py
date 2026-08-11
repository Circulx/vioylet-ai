from __future__ import annotations

from app.core.logging import get_logger
from app.graph.state import ViolytState

logger = get_logger(__name__)


async def repair_layer(state: ViolytState) -> dict:
    """Diagnose failed evaluation and set targeted repair instructions."""
    repair_count = state.get("repair_count", 0)
    evaluation = state.get("evaluation")
    repair_target = (state.get("repair_target") or "").strip().lower()

    instructions: list[str] = []
    if evaluation and evaluation.required_repairs:
        for r in evaluation.required_repairs:
            instructions.append(f"{r.target_layer}: {r.repair_action} ({r.failure_reason})")
            # Infer target from first critical/major repair if unset
            if not repair_target:
                layer = (r.target_layer or "").lower()
                if "l6b" in layer or "content_intelligence" in layer or "insight" in layer:
                    repair_target = "l6b"
                elif "l5" in layer or "concept" in layer:
                    repair_target = "l5"
                elif "l7c" in layer or "blueprint" in layer or "content_prep" in layer:
                    repair_target = "l7c"
                elif "l7" in layer or "copy" in layer:
                    repair_target = "l7"

    if not repair_target:
        repair_target = "l5"

    if not instructions:
        defaults = {
            "l6b": "content_intelligence: strengthen verify/prioritize/insight — answer WHY with must_know evidence",
            "l5": "concept_engine: regenerate concepts that express PRIMARY INSIGHT with brand-specific tension",
            "l7": "copy_engine: rewrite copy from ranked evidence + primary insight; complete sentences; UDAN not ADAN",
            "l7c": "content_prep: rebuild blueprint hierarchy — hero stat + insight sections; no truncation",
        }
        instructions.append(defaults.get(repair_target, defaults["l5"]))

    logger.warning(
        "repair.targeted",
        repair_count=repair_count + 1,
        repair_target=repair_target,
        instructions=instructions[:3],
    )

    return {
        "repair_count": repair_count + 1,
        "repair_instructions": instructions,
        "repair_target": repair_target,
    }
