from app.services.research_editorial_planning import ResearchEditorialPlanningService


def test_research_editorial_planning_activates_for_research_heavy_carousel() -> None:
    service = ResearchEditorialPlanningService()

    brief = service.build(
        prompt=(
            "Write a LinkedIn carousel on the India-New Zealand Free Trade Agreement signed on 27 April 2026. "
            "Go beyond the headline numbers and explain why it matters strategically."
        ),
        studio_panel={"platform_preset": "linkedin", "format": "carousel", "file_type": "pdf"},
        brand_context={"brand_name": "Jiraaf"},
        persona_context={},
        objective_context={"name": "Thought Leadership"},
        knowledge_brief=[{"channel": "strategy", "content": "Explain what India negotiated, not just what it gained."}],
        live_research={
            "status": "completed",
            "summary": "The agreement included tariff reductions and phased access commitments.",
            "verified_facts": [
                {
                    "label": "Signing date",
                    "value": "27 April 2026",
                    "source_title": "Official release",
                    "source_url": "https://example.com/release",
                }
            ],
            "sources": [{"title": "Official release", "url": "https://example.com/release"}],
        },
        content_format_guide={"format_expectations": {"carousel": {"preferred_slide_count": 5}}},
    )

    assert brief["active"] is True
    assert brief["mode"] == "research_editorial"
    assert brief["format_family"] == "carousel"
    assert brief["preferred_slide_count"] == 5
    assert any(item["role"] == "hook" for item in brief["outline"])
    assert any("Signing date: 27 April 2026" in item for item in brief["insight_hierarchy"])
    assert brief["fact_model"]["verified_facts"][0]["label"] == "Signing date"
    assert brief["ranked_sources"][0]["label"] == "Official release"
    assert brief["citation_rules"]["style"] == "light_on_canvas_citations"
    assert any("Treat verified_facts as the only claims" in item for item in brief["source_backing_rules"])


def test_research_editorial_planning_uses_style_reference_sample_count_over_generic_preference() -> None:
    service = ResearchEditorialPlanningService()

    brief = service.build(
        prompt="Create a LinkedIn carousel on the India-New Zealand FTA signed on 27 April 2026.",
        studio_panel={"platform_preset": "linkedin", "format": "carousel", "file_type": "png"},
        brand_context={"brand_name": "Jiraaf"},
        persona_context={},
        objective_context={},
        knowledge_brief=[],
        live_research={"status": "completed", "verified_facts": []},
        content_format_guide={"format_expectations": {"carousel": {"preferred_slide_count": 5}}},
        template_context={
            "sequence_pack": {
                "surface_policy": "style_reference_only",
                "slide_count": 4,
                "slides": [
                    {"slide_index": 1, "story_role": "hook", "headline_hint": "Hook"},
                    {"slide_index": 2, "story_role": "structure", "headline_hint": "Mechanics"},
                    {"slide_index": 3, "story_role": "undercovered_angle", "headline_hint": "Missed angle"},
                    {"slide_index": 4, "story_role": "takeaway", "headline_hint": "Takeaway"},
                ],
            }
        },
    )

    assert brief["preferred_slide_count"] == 4
    assert len(brief["outline"]) == 4
    assert brief["narrative_contract"] == "follow_sample_editorial_rhythm"


def test_research_editorial_planning_static_sample_mode_uses_reference_metadata() -> None:
    service = ResearchEditorialPlanningService()

    brief = service.build(
        prompt="Create a static social creative about making complex choices easier.",
        studio_panel={"platform_preset": "linkedin", "format": "static", "file_type": "png"},
        brand_context={"brand_name": "Example Brand"},
        persona_context={},
        objective_context={},
        knowledge_brief=[],
        live_research={},
        reference_assets=[
            {
                "asset_role": "reference_creative",
                "trust_level": "trusted",
                "format_family": "static",
                "metadata": {
                    "format_family": "static",
                    "summary": "Single-surface creative with one dominant hero line, proof cue, and quiet footer.",
                    "editorial_dna": {
                        "story_arc_roles": ["single_frame_story", "proof", "takeaway"],
                        "headline_patterns": ["Lead with one concrete tension."],
                        "supporting_patterns": ["Use one concise supporting proof cue."],
                        "copy_density": "low",
                    },
                },
            }
        ],
    )

    assert brief["mode"] == "sample_guided_explainer"
    assert brief["narrative_contract"] == "follow_sample_static_hierarchy"
    assert brief["sample_editorial_brief"]["source"] == "reference_asset"


def test_research_editorial_planning_infographic_sample_mode_uses_reference_metadata() -> None:
    service = ResearchEditorialPlanningService()

    brief = service.build(
        prompt="Create an infographic about how teams compare options.",
        studio_panel={"platform_preset": "linkedin", "format": "infographic", "file_type": "png"},
        brand_context={"brand_name": "Example Brand"},
        persona_context={},
        objective_context={},
        knowledge_brief=[],
        live_research={},
        reference_assets=[
            {
                "asset_role": "reference_creative",
                "trust_level": "approved",
                "format_family": "infographic",
                "metadata": {
                    "format_family": "infographic",
                    "summary": "Infographic reference with a context band, comparison modules, and takeaway strip.",
                    "structural_cues": ["context band", "comparison modules", "takeaway strip"],
                    "editorial_dna": {
                        "story_arc_roles": ["context", "comparison", "takeaway"],
                        "headline_patterns": ["Frame the comparison clearly."],
                    },
                },
            }
        ],
    )

    assert brief["mode"] == "sample_guided_explainer"
    assert brief["narrative_contract"] == "follow_sample_infographic_flow"
    assert brief["ordered_story_beats"]


def test_research_editorial_planning_honors_explicit_prompt_count_over_sample_count() -> None:
    service = ResearchEditorialPlanningService()

    brief = service.build(
        prompt="Create a 6 slide LinkedIn carousel on a new trade agreement.",
        studio_panel={"platform_preset": "linkedin", "format": "carousel", "file_type": "png"},
        brand_context={"brand_name": "Jiraaf"},
        persona_context={},
        objective_context={},
        knowledge_brief=[],
        live_research={},
        content_format_guide={"format_expectations": {"carousel": {"preferred_slide_count": 5}}},
        template_context={
            "sequence_pack": {
                "surface_policy": "style_reference_only",
                "slide_count": 4,
                "slides": [
                    {"slide_index": 1, "story_role": "hook"},
                    {"slide_index": 2, "story_role": "structure"},
                    {"slide_index": 3, "story_role": "undercovered_angle"},
                    {"slide_index": 4, "story_role": "takeaway"},
                ],
            }
        },
    )

    assert brief["preferred_slide_count"] == 6


def test_research_editorial_planning_separates_inference_and_uncertainty() -> None:
    service = ResearchEditorialPlanningService()

    brief = service.build(
        prompt="Write a blog analyzing what the rate cut could mean for fixed-income investors.",
        studio_panel={"platform_preset": "linkedin", "format": "static", "file_type": "png"},
        brand_context={"brand_name": "Jiraaf"},
        persona_context={},
        objective_context={},
        knowledge_brief=[{"channel": "macro", "content": "The market may be underpricing duration sensitivity."}],
        live_research={
            "status": "completed",
            "summary": "The move may signal a softer policy stance, but the transmission path is still unclear and likely phased.",
            "verified_facts": [
                {
                    "label": "Policy move",
                    "value": "25 bps cut announced",
                    "source_title": "Central bank statement",
                    "source_url": "https://example.com/cb",
                }
            ],
            "sources": [{"title": "Central bank statement", "url": "https://example.com/cb"}],
            "ranked_sources": [{"rank": 1, "title": "Central bank statement", "url": "https://example.com/cb", "support_count": 1}],
            "inferences": ["The move may signal a softer policy stance."],
            "uncertainties": ["The transmission path is still unclear and likely phased."],
        },
    )

    assert brief["fact_model"]["verified_facts"][0]["value"] == "25 bps cut announced"
    assert "softer policy stance" in brief["fact_model"]["inferences"][0]
    assert "still unclear" in brief["fact_model"]["uncertainties"][0]
    assert brief["citation_rules"]["style"] in {"light_source_cues", "light_on_canvas_citations"}


def test_research_editorial_planning_preserves_requested_top_ten_verified_rows() -> None:
    service = ResearchEditorialPlanningService()
    facts = [
        {
            "label": f"Rank {index}",
            "value": f"Verified value {index}",
            "source_title": "Ranking source",
            "source_url": "https://example.com/ranking",
        }
        for index in range(1, 11)
    ]
    prompt = "Create a static post comparing a metric and create a top 10 ranking."

    brief = service.build(
        prompt=prompt,
        studio_panel={"platform_preset": "linkedin", "format": "static", "file_type": "png"},
        brand_context={"brand_name": "Jiraaf"},
        persona_context={},
        objective_context={},
        knowledge_brief=[],
        live_research={
            "status": "completed",
            "summary": "The source contains ten verified ranking rows.",
            "verified_facts": facts,
            "sources": [{"title": "Ranking source", "url": "https://example.com/ranking"}],
        },
    )

    sanitized = ResearchEditorialPlanningService.enforce_source_backing(
        {"headline": "Top 10 ranking", "body": "", "cta": "", "metadata": {"proof_points": [], "claim_evidence_pairs": []}},
        prompt_text=prompt,
        brief=brief,
    )

    assert brief["fact_limit"] == 10
    assert len(brief["fact_model"]["verified_facts"]) == 10
    assert len(sanitized["metadata"]["claim_evidence_pairs"]) == 10


def test_research_editorial_planning_stays_standard_for_simple_social_prompt() -> None:
    service = ResearchEditorialPlanningService()

    brief = service.build(
        prompt="Create an Instagram post about investing confidence with Jiraaf.",
        studio_panel={"platform_preset": "instagram", "format": "static", "file_type": "png"},
        brand_context={"brand_name": "Jiraaf"},
        persona_context={},
        objective_context={},
        knowledge_brief=[],
        live_research={},
    )

    assert brief["active"] is False
    assert brief["mode"] == "standard"
    assert brief["format_family"] == "static"


def test_research_editorial_planning_filters_visual_template_knowledge_from_insights() -> None:
    service = ResearchEditorialPlanningService()

    brief = service.build(
        prompt="Write a LinkedIn carousel explaining why the latest trade agreement matters strategically.",
        studio_panel={"platform_preset": "linkedin", "format": "carousel", "file_type": "pdf"},
        brand_context={"brand_name": "Jiraaf"},
        persona_context={},
        objective_context={},
        knowledge_brief=[
            {"channel": "strategy", "content": "Look at what India negotiated, not just the tariff headline."},
            {"channel": "logo", "content": "Logo palette uses blue and yellow with curved shapes."},
            {"channel": "reference_creative", "content": "Reference creative uses an editorial composition and premium spacing."},
        ],
        live_research={"status": "unavailable", "summary": "", "verified_facts": []},
    )

    assert any("India negotiated" in item for item in brief["insight_hierarchy"])
    assert not any("palette" in item.casefold() for item in brief["insight_hierarchy"])
    assert not any("reference creative" in item.casefold() for item in brief["insight_hierarchy"])


def test_research_editorial_planning_enforces_source_backing_without_verified_facts() -> None:
    payload = {
        "headline": "65% of women now prefer fixed income",
        "body": "Women participation has risen 20% since 2023 according to market data.",
        "cta": "Explore Jiraaf",
        "hashtags": ["#Jiraaf"],
        "metadata": {
            "supporting_line": "65% of women choose bonds first.",
            "proof_points": ["20% growth since 2023", "Stable long-term wealth"],
            "stat_highlights": ["65% prefer fixed income"],
            "claim_evidence_pairs": [{"claim": "Women participation up 20%", "evidence": "Market data"}],
        },
    }
    brief = {
        "active": True,
        "needs_live_research": True,
        "research_status": "unavailable",
        "topic_focus": "Women borrowers are reshaping credit markets",
        "angle": "Explain the structural shift without overstating unsupported current numbers.",
        "reader_payoff": "Reader should understand the shift without relying on unsupported stats.",
        "insight_hierarchy": ["The change is real, but exact current figures still need verification."],
        "fact_model": {
            "verified_facts": [],
            "inferences": ["The shift appears meaningful, but exact current figures still need verification."],
            "uncertainties": ["External verification was unavailable, so current percentages should stay qualitative."],
        },
        "ranked_sources": [],
    }

    sanitized = ResearchEditorialPlanningService.enforce_source_backing(
        payload,
        prompt_text="Create a LinkedIn post about how women borrowers are reshaping credit markets.",
        brief=brief,
    )

    assert sanitized["headline"] == "Women borrowers are reshaping credit markets"
    assert "20%" not in sanitized["body"]
    assert sanitized["metadata"]["stat_highlights"] == []
    assert sanitized["metadata"]["claim_evidence_pairs"] == []
    assert sanitized["metadata"]["proof_points"]


def test_research_editorial_planning_marks_hard_fail_when_fresh_research_is_required_but_unavailable() -> None:
    brief = ResearchEditorialPlanningService().build(
        prompt="Write a LinkedIn carousel analyzing the latest India-New Zealand FTA signed on 27 April 2026.",
        studio_panel={"platform_preset": "linkedin", "format": "carousel", "file_type": "pdf"},
        brand_context={"brand_name": "Jiraaf"},
        persona_context={},
        objective_context={},
        knowledge_brief=[],
        live_research={"status": "unavailable", "summary": "", "verified_facts": [], "ranked_sources": []},
    )

    assert brief["research_guard"]["strict_mode"] is True
    assert brief["research_guard"]["hard_fail"] is True


def test_research_editorial_planning_hard_fails_top_n_ranking_when_research_not_configured() -> None:
    brief = ResearchEditorialPlanningService().build(
        prompt="Create a static post comparing a metric and create a top 10 ranking.",
        studio_panel={"platform_preset": "linkedin", "format": "static", "file_type": "png"},
        brand_context={"brand_name": "Jiraaf"},
        persona_context={},
        objective_context={},
        knowledge_brief=[],
        live_research={"status": "not_configured", "summary": "No live search backend configured.", "verified_facts": [], "ranked_sources": []},
    )

    assert brief["active"] is True
    assert brief["research_guard"]["requires_verified_rows"] is True
    assert brief["research_guard"]["hard_fail"] is True


def test_research_editorial_planning_hard_fails_top_n_ranking_when_research_missing() -> None:
    brief = ResearchEditorialPlanningService().build(
        prompt="Create a static post comparing a metric and create a top 10 ranking.",
        studio_panel={"platform_preset": "linkedin", "format": "static", "file_type": "png"},
        brand_context={"brand_name": "Jiraaf"},
        persona_context={},
        objective_context={},
        knowledge_brief=[],
        live_research={},
    )

    assert brief["active"] is True
    assert brief["research_guard"]["requires_verified_rows"] is True
    assert brief["research_guard"]["hard_fail"] is True


def test_research_editorial_planning_allows_qualitative_inflation_prompt_when_research_unavailable() -> None:
    brief = ResearchEditorialPlanningService().build(
        prompt='Create a LinkedIn carousel on how inflation quietly erodes savings and real returns. Angle: a sharp reminder for people who think parking money in savings is "safe."',
        studio_panel={"platform_preset": "linkedin", "format": "carousel", "file_type": "png"},
        brand_context={"brand_name": "Jiraaf"},
        persona_context={},
        objective_context={},
        knowledge_brief=[],
        live_research={"status": "unavailable", "summary": "", "verified_facts": [], "ranked_sources": []},
    )

    assert brief["research_guard"]["strict_mode"] is True
    assert brief["research_guard"]["requires_fresh_research"] is True
    assert brief["research_guard"]["requires_blocking_research"] is False
    assert brief["research_guard"]["hard_fail"] is False
