from langgraph.graph import StateGraph, END

from app.graph.state import ViolytState
from app.graph.nodes import (
    layer1_retrieval,
    layer2_brand_intelligence,
    layer3_brief_interpreter,
    layer4_strategic_reasoning,
    layer5_concept_engine,
    layer6_format_engine,
    layer7_copy_engine,
    layer8_visual_reasoning,
    layer9_scene_graph,
    layer10_evaluation,
    repair_layer,
    renderer_node,
)
from app.graph.routing import route_evaluation, route_repair


def build_violyt_graph() -> StateGraph:
    """Build the Violyt LangGraph with 12 nodes, sequential, parallel, and conditional loops."""
    g = StateGraph(ViolytState)

    # Register all 12 nodes (use lN_ prefixes to avoid state-key collisions)
    g.add_node("l1_brand_retrieval", layer1_retrieval)
    g.add_node("l2_brand_intelligence", layer2_brand_intelligence)
    g.add_node("l3_brief_interpreter", layer3_brief_interpreter)
    g.add_node("l4_strategic_reasoning", layer4_strategic_reasoning)
    g.add_node("l5_concept_engine", layer5_concept_engine)
    g.add_node("l6_format_engine", layer6_format_engine)
    g.add_node("l7_copy_engine", layer7_copy_engine)
    g.add_node("l8_visual_reasoning", layer8_visual_reasoning)
    g.add_node("l9_scene_graph", layer9_scene_graph)
    g.add_node("l10_evaluation", layer10_evaluation)
    g.add_node("repair", repair_layer)
    g.add_node("renderer", renderer_node)

    # Sequential: L1 -> L2 -> L3 -> L4
    g.set_entry_point("l1_brand_retrieval")
    g.add_edge("l1_brand_retrieval", "l2_brand_intelligence")
    g.add_edge("l2_brand_intelligence", "l3_brief_interpreter")
    g.add_edge("l3_brief_interpreter", "l4_strategic_reasoning")

    # L5 and L6 are parallel children of L4; L7 and L8 are children of L5.
    # To make L9 a clean join node in LangGraph, L6 is wired after L5 so that
    # L6, L7, and L8 complete in the same superstep before L9 runs.
    g.add_edge("l4_strategic_reasoning", "l5_concept_engine")
    g.add_edge("l5_concept_engine", "l6_format_engine")
    g.add_edge("l5_concept_engine", "l7_copy_engine")
    g.add_edge("l5_concept_engine", "l8_visual_reasoning")

    # L6 + L7 + L8 join at L9
    g.add_edge("l7_copy_engine", "l9_scene_graph")
    g.add_edge("l8_visual_reasoning", "l9_scene_graph")
    g.add_edge("l6_format_engine", "l9_scene_graph")

    # L9 -> L10 -> conditional routing
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
