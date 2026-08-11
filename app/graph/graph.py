from langgraph.graph import StateGraph, END

from app.graph.state import ViolytState
from app.graph.nodes import (
    layer1_retrieval,
    layer2_brand_intelligence,
    layer3_brief_interpreter,
    layer4_strategic_reasoning,
    layer5_concept_engine,
    layer6_format_engine,
    layer6b_content_intelligence,
    layer7_copy_engine,
    layer7b_content_validator,
    layer7c_content_prep,
    layer8_visual_reasoning,
    layer9_scene_graph,
    layer10_evaluation,
    repair_layer,
    renderer_node,
)
from app.graph.routing import route_evaluation, route_repair


def _add_shared_upstream(g: StateGraph) -> None:
    """L1 → L7c shared chain used by Phase 1 and the full graph."""
    g.add_node("l1_brand_retrieval", layer1_retrieval)
    g.add_node("l2_brand_intelligence", layer2_brand_intelligence)
    g.add_node("l3_brief_interpreter", layer3_brief_interpreter)
    g.add_node("l4_strategic_reasoning", layer4_strategic_reasoning)
    g.add_node("l5_concept_engine", layer5_concept_engine)
    g.add_node("l6_format_engine", layer6_format_engine)
    g.add_node("l6b_content_intelligence", layer6b_content_intelligence)
    g.add_node("l7_copy_engine", layer7_copy_engine)
    g.add_node("l7b_content_validator", layer7b_content_validator)
    g.add_node("l7c_content_prep", layer7c_content_prep)

    g.set_entry_point("l1_brand_retrieval")
    g.add_edge("l1_brand_retrieval", "l2_brand_intelligence")
    g.add_edge("l2_brand_intelligence", "l3_brief_interpreter")
    g.add_edge("l3_brief_interpreter", "l4_strategic_reasoning")
    g.add_edge("l4_strategic_reasoning", "l5_concept_engine")
    g.add_edge("l4_strategic_reasoning", "l6_format_engine")
    # Content intelligence waits for both concept + format, then drives copy
    g.add_edge("l5_concept_engine", "l6b_content_intelligence")
    g.add_edge("l6_format_engine", "l6b_content_intelligence")
    g.add_edge("l6b_content_intelligence", "l7_copy_engine")
    g.add_edge("l7_copy_engine", "l7b_content_validator")
    g.add_edge("l7b_content_validator", "l7c_content_prep")


def build_phase1_graph() -> StateGraph:
    """Phase 1: L1 → L7c Creative Blueprint, then pause for approval."""
    g = StateGraph(ViolytState)
    _add_shared_upstream(g)
    g.add_edge("l7c_content_prep", END)
    return g


def build_phase2_graph() -> StateGraph:
    """Phase 2: L8 image gen → pass-through renderer (skip L9/L10 for chat latency)."""
    g = StateGraph(ViolytState)

    g.add_node("l8_visual_reasoning", layer8_visual_reasoning)
    g.add_node("renderer", renderer_node)

    g.set_entry_point("l8_visual_reasoning")
    g.add_edge("l8_visual_reasoning", "renderer")
    g.add_edge("renderer", END)
    return g


def build_violyt_graph() -> StateGraph:
    """Full graph L1→renderer (legacy / tests). Prefer phase1 + phase2 in the API."""
    g = StateGraph(ViolytState)
    _add_shared_upstream(g)

    g.add_node("l8_visual_reasoning", layer8_visual_reasoning)
    g.add_node("l9_scene_graph", layer9_scene_graph)
    g.add_node("l10_evaluation", layer10_evaluation)
    g.add_node("repair", repair_layer)
    g.add_node("renderer", renderer_node)

    g.add_edge("l7c_content_prep", "l8_visual_reasoning")
    g.add_edge("l8_visual_reasoning", "l9_scene_graph")
    g.add_edge("l9_scene_graph", "l10_evaluation")
    g.add_conditional_edges(
        "l10_evaluation",
        route_evaluation,
        {"pass": "renderer", "repair": "repair"},
    )
    g.add_conditional_edges(
        "repair",
        route_repair,
        {"retry": "l5_concept_engine", "fail": END},
    )
    g.add_edge("renderer", END)
    return g
