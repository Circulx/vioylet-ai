from app.services.content_planning import ContentPlanningService


def test_content_planning_derives_editorial_reveal_archetype_from_outline() -> None:
    plan = ContentPlanningService.derive_content_plan(
        deliverable_type="linkedin_carousel",
        format_family_plan={
            "family": "carousel",
            "primary_unit": "slide",
            "body_shape": "multi_slide_sequence",
        },
        research_editorial_brief={
            "outline": [
                {"title": "The overlooked headline", "role": "hook"},
                {"title": "What actually changed", "role": "structure"},
                {"title": "What most coverage missed", "role": "undercovered_angle"},
                {"title": "Why it matters strategically", "role": "strategic_meaning"},
            ]
        },
    )

    assert plan["carousel_archetype"] == "editorial_reveal"
    assert plan["carousel_slide_grammar"][0]["role"] == "hook"


def test_content_planning_derives_list_teaching_archetype_from_bias_topic() -> None:
    plan = ContentPlanningService.derive_content_plan(
        deliverable_type="behavioural_biases_carousel",
        format_family_plan={
            "family": "carousel",
            "content_structure": ["setup_slide", "one_bias_per_slide", "closing_cta"],
            "notes": ["Teach one bias per slide with a repeated learning pattern."],
        },
        research_editorial_brief={"outline": []},
    )

    assert plan["carousel_archetype"] == "list_teaching"
    assert any(step["role"] == "list_item" for step in plan["carousel_slide_grammar"])


def test_content_planning_derives_problem_solution_feature_archetype_from_analyzer_topic() -> None:
    plan = ContentPlanningService.derive_content_plan(
        deliverable_type="bond_analyzer_carousel",
        format_family_plan={
            "family": "carousel",
            "notes": ["Frame the product problem first, then show the solution and capability flow."],
        },
        research_editorial_brief={"outline": []},
    )

    assert plan["carousel_archetype"] == "problem_solution_feature"
    assert plan["carousel_slide_grammar"][0]["role"] == "problem_frame"


def test_content_planning_adds_semantic_carousel_contracts_only_when_enabled() -> None:
    research_brief = {
        "preferred_slide_count": 4,
        "semantic_carousel_plan": {
            "family": "macro_analysis",
            "recommended_slide_count": 5,
            "story_map": [
                {
                    "role": "hook",
                    "purpose": "Open with the undercovered market implication.",
                    "notes": "Keep it sharp.",
                    "section_focus": "implication",
                    "representation_hint": "hero_stat",
                },
                {
                    "role": "structure",
                    "purpose": "Explain the mechanism behind the shift.",
                    "section_focus": "mechanics",
                    "representation_hint": "process_path",
                },
            ],
        },
    }

    baseline = ContentPlanningService.derive_content_plan(
        deliverable_type="linkedin_carousel",
        format_family_plan={"family": "carousel"},
        research_editorial_brief=research_brief,
    )
    enabled = ContentPlanningService.derive_content_plan(
        deliverable_type="linkedin_carousel",
        format_family_plan={"family": "carousel"},
        research_editorial_brief=research_brief,
        enable_semantic_carousel_plan=True,
    )

    assert baseline["sequence_contract"] == "native_carousel_metadata"
    assert baseline["carousel_slide_contracts"] == []
    assert baseline["semantic_carousel_plan"] == {}
    assert enabled["sequence_contract"] == "semantic_prompt_story_plan"
    assert enabled["preferred_slide_count"] == 5
    assert enabled["carousel_slide_grammar"][0]["role"] == "hook"
    assert enabled["carousel_slide_contracts"][1]["representation_hint"] == "process_path"
    assert enabled["semantic_carousel_plan"]["family"] == "macro_analysis"
