from pathlib import Path
import json
from uuid import uuid4

from app.services.brand_scoring import BrandScoringService


def test_brand_scoring_service_builds_deterministic_scorecard() -> None:
    service = BrandScoringService(session=None)
    service._visual_review_for_assets = lambda **kwargs: {  # type: ignore[method-assign]
        "asset_count": 1,
        "page_count": 1,
        "prompt_alignment_score": 78,
        "layout_readability_score": 84,
        "density_score": 80,
        "brand_alignment_score": 86,
        "hierarchy_score": 82,
        "crowding_score": 79,
        "page_balance_score": 81,
        "ocr_confidence_score": 88,
        "visual_diagnostic_score": 82,
        "page_reviews": [{"ocr_text_excerpt": "Fresh seafood sourced with trust for urban buyers."}],
    }
    scorecard = service.build_scorecard(
        prompt="Create a static post about trusted seafood sourcing for urban buyers.",
        studio_panel={"format": "static", "file_type": "png"},
        generated_payload={
            "headline": "Fresh seafood, sourced with trust.",
            "body": "Built for urban buyers who care about quality and freshness.",
            "cta": "Learn more",
        },
        brand_context={
            "brand_name": "The Good Fish Company",
            "identity": {"brand_name": "The Good Fish Company"},
            "audience_insights": {"desired_outcomes": ["trusted seafood freshness"]},
        },
        persona_context={"name": "Urban seafood buyer", "audience_goals": ["trusted seafood freshness"]},
        objective_context={"name": "Trust building", "description": "Build trust with urban buyers."},
        explainability={
            "input_access_summary": {
                "brand_context": {"used_paths": ["identity.brand_name"], "unused_paths": ["identity.brand_description"]},
                "persona_context": {"used_paths": ["audience_goals[0]"], "unused_paths": []},
                "objective_context": {"used_paths": ["name"], "unused_paths": ["description"]},
            }
        },
        output_assets=[{"storage_path": "tenant/brand/generated/output.png", "mime_type": "image/png", "asset_kind": "image"}],
    )

    assert set(scorecard.keys()) == {
        "overall_score",
        "score_breakdown",
        "weighting",
        "scoring_mode",
        "summary",
        "llm_prompt_relevance_analysis",
        "developer_explanation",
    }
    assert scorecard["weighting"] == {
        "on_brand": 0.4,
        "prompt_adherence": 0.35,
        "relevance": 0.25,
    }
    assert set(scorecard["score_breakdown"].keys()) == {"on_brand", "prompt_adherence", "relevance"}
    assert scorecard["scoring_mode"] == {
        "on_brand": "rules",
        "prompt_adherence": "rules",
        "relevance": "rules",
    }
    assert scorecard["llm_prompt_relevance_analysis"] is None
    assert 0 <= scorecard["overall_score"] <= 100
    assert len(scorecard["summary"]) == 3
    assert set(scorecard["developer_explanation"].keys()) == {"overall", "on_brand", "prompt_adherence", "relevance"}
    assert "formula" in scorecard["developer_explanation"]["on_brand"]
    assert "components" in scorecard["developer_explanation"]["prompt_adherence"]
    assert "base_score" in scorecard["developer_explanation"]["overall"]
    assert "boosts" in scorecard["developer_explanation"]["on_brand"]
    assert "penalties" in scorecard["developer_explanation"]["prompt_adherence"]
    assert "semantic_groups" in scorecard["developer_explanation"]["prompt_adherence"]["prompt_details"]
    assert "visual_checks_failed" in scorecard["developer_explanation"]["relevance"]
    assert "payload_semantic_groups" in scorecard["developer_explanation"]["prompt_adherence"]["prompt_details"]
    assert "alignment_evidence" in scorecard["developer_explanation"]["prompt_adherence"]["prompt_details"]


def test_brand_scoring_service_marks_render_loss_when_payload_outpaces_visible_output() -> None:
    service = BrandScoringService(session=None)
    service._visual_review_for_assets = lambda **kwargs: {  # type: ignore[method-assign]
        "asset_count": 1,
        "page_count": 1,
        "prompt_alignment_score": 22,
        "layout_readability_score": 85,
        "density_score": 72,
        "brand_alignment_score": 70,
        "hierarchy_score": 78,
        "crowding_score": 80,
        "page_balance_score": 79,
        "ocr_confidence_score": 88,
        "visual_diagnostic_score": 82,
        "page_reviews": [
            {
                "ocr_text_excerpt": "FD Bonds offer fixed, predictable returns similar to traditional fixed deposits.",
                "missing_prompt_terms": [
                    "bond comparison",
                    "beginner suitability guidance",
                    "fixed rate bonds",
                    "floating rate bonds",
                ],
            }
        ],
    }
    scorecard = service.build_scorecard(
        prompt=(
            "Create a LinkedIn static post about FD Bonds and explain the actual differences between "
            "FD Bonds, Floating Rate Bonds, and Fixed Rate Bonds. Also include guidance on which type "
            "of bond is more suitable for beginner investors"
        ),
        studio_panel={"format": "static", "file_type": "png"},
        generated_payload={
            "headline": "FD Bonds vs Fixed and Floating Rate Bonds",
            "body": (
                "FD Bonds offer fixed, predictable returns. Fixed Rate Bonds pay a set interest rate "
                "throughout their tenure. Floating Rate Bonds adjust periodically based on market benchmarks. "
                "For beginners, FD Bonds are usually the easiest starting point."
            ),
            "cta": "Explore now",
        },
        brand_context={"brand_name": "Jiraaf", "audience_insights": {"desired_outcomes": ["stable wealth building"]}},
        persona_context={"name": "Beginner investor", "audience_goals": ["stable wealth building"]},
        objective_context={"name": "Education", "description": "Explain bond choices for beginners."},
        explainability={"input_access_summary": {}},
        output_assets=[{"storage_path": "tenant/brand/generated/output.png", "mime_type": "image/png", "asset_kind": "image"}],
    )

    prompt_details = scorecard["developer_explanation"]["prompt_adherence"]["prompt_details"]

    assert prompt_details["semantic_groups"]["failed"]
    assert "fixed rate bonds" in prompt_details["payload_semantic_groups"]["matched"]
    assert prompt_details["render_loss_detected"] is True
    assert "fixed rate bonds" in prompt_details["render_loss_terms"]
    assert (
        prompt_details["alignment_evidence"]["rendered_text_prompt"]
        < prompt_details["alignment_evidence"]["payload_text_prompt"]
    )
    assert (
        prompt_details["alignment_evidence"]["effective_text_prompt"]
        < prompt_details["alignment_evidence"]["payload_text_prompt"]
    )


def test_brand_scoring_service_uses_single_llm_result_for_prompt_and_relevance() -> None:
    service = BrandScoringService(session=None)
    service._visual_review_for_assets = lambda **kwargs: {  # type: ignore[method-assign]
        "asset_count": 1,
        "page_count": 1,
        "prompt_alignment_score": 91,
        "layout_readability_score": 88,
        "density_score": 82,
        "brand_alignment_score": 80,
        "hierarchy_score": 84,
        "crowding_score": 86,
        "page_balance_score": 83,
        "ocr_confidence_score": 90,
        "visual_diagnostic_score": 86,
        "page_reviews": [{"ocr_text_excerpt": "A simple wealth education visual."}],
    }
    service._llm_prompt_relevance_analysis = lambda **kwargs: {  # type: ignore[method-assign]
        "source": "llm_vision",
        "model": "test-vision-model",
        "scores": {"prompt_adherence": 61, "relevance": 58},
        "explanations": {
            "prompt_adherence": "The visual misses the requested comparison.",
            "relevance": "The concept is too generic for beginner investors.",
        },
        "missing_content_or_visuals": ["comparison between bond types"],
        "improvement_suggestions": ["Add clear visual contrast between FD, fixed, and floating bonds."],
        "visual_quality_issues": ["Requested comparison modules are not visually distinct."],
        "asset_type_assessment": {
            "asset_type": "static",
            "primary_purpose": "communicate one key message quickly and clearly",
            "purpose_fit": "partial",
        },
        "visible_inventory": {
            "expected_item_count": 3,
            "observed_visible_item_count": 1,
            "visible_items_or_labels": ["FD Bonds"],
            "missing_or_unclear_items": ["Fixed Rate Bonds", "Floating Rate Bonds"],
            "inventory_confidence": "medium",
        },
        "prompt_content_contract": {
            "core_user_ask": "a comparison of FD Bonds, Fixed Rate Bonds, and Floating Rate Bonds",
            "expected_content_areas": ["FD Bonds", "Fixed Rate Bonds", "Floating Rate Bonds"],
            "observed_content_areas": ["FD Bonds"],
            "missing_or_undercovered_content_areas": ["Fixed Rate Bonds", "Floating Rate Bonds"],
            "content_gap_reason": "The visible creative does not compare all requested bond types.",
        },
        "requirement_coverage": {
            "visible_requested_items": ["FD Bonds"],
            "missing_or_unclear_requested_items": ["Fixed Rate Bonds", "Floating Rate Bonds"],
            "completeness_reason": "Only one requested bond type is clearly visible.",
        },
        "critical_requirement_failures": ["comparison between all requested bond types"],
        "brand_intelligence_suggestions": [
            "Show all requested bond types as separate labeled comparison modules."
        ],
        "score_consistency_reason": "The score is reduced because the core comparison is incomplete.",
        "evaluated_format": "static",
        "slide_observations": ["Single image is readable but generic."],
        "carousel_story_assessment": {},
        "asset_count": 1,
        "overlay_policy": {
            "do_not_penalize_missing_logo": True,
            "do_not_penalize_missing_cta": True,
        },
    }

    scorecard = service.build_scorecard(
        prompt="Create a static post comparing FD Bonds, Fixed Rate Bonds, and Floating Rate Bonds.",
        studio_panel={"format": "static", "file_type": "png"},
        generated_payload={"headline": "Bond basics", "body": "A short education post."},
        brand_context={"brand_name": "Jiraaf"},
        persona_context={"name": "Beginner investor"},
        objective_context={"name": "Education"},
        explainability={"input_access_summary": {}},
        output_assets=[{"storage_path": "tenant/brand/generated/output.png", "mime_type": "image/png", "asset_kind": "image"}],
    )

    assert scorecard["score_breakdown"]["prompt_adherence"] == 61
    assert scorecard["score_breakdown"]["relevance"] == 58
    assert scorecard["scoring_mode"]["prompt_adherence"] == "llm_vision"
    assert scorecard["scoring_mode"]["relevance"] == "llm_vision"
    assert scorecard["llm_prompt_relevance_analysis"]["missing_content_or_visuals"] == ["comparison between bond types"]
    assert scorecard["developer_explanation"]["prompt_adherence"]["scoring_source"] == "llm_vision"
    assert scorecard["developer_explanation"]["prompt_adherence"]["llm_analysis"]["visual_quality_issues"]
    assert scorecard["developer_explanation"]["prompt_adherence"]["llm_analysis"]["critical_requirement_failures"]
    assert scorecard["developer_explanation"]["prompt_adherence"]["llm_analysis"]["visible_inventory"]["observed_visible_item_count"] == 1
    assert scorecard["developer_explanation"]["prompt_adherence"]["llm_analysis"]["prompt_content_contract"]["missing_or_undercovered_content_areas"]
    assert scorecard["developer_explanation"]["relevance"]["llm_analysis"]["overlay_policy"]["do_not_penalize_missing_logo"] is True
    assert "missing or undercovered" in scorecard["summary"][1]


def test_brand_scoring_summary_prioritizes_prompt_content_gap_over_brand_mood() -> None:
    service = BrandScoringService(session=None)
    service._visual_review_for_assets = lambda **kwargs: {  # type: ignore[method-assign]
        "asset_count": 4,
        "page_count": 4,
        "prompt_alignment_score": 82,
        "layout_readability_score": 88,
        "density_score": 82,
        "brand_alignment_score": 72,
        "style_alignment_score": 78,
        "mood_alignment_score": 48,
        "typography_alignment_score": 76,
        "motif_alignment_score": 70,
        "hierarchy_score": 84,
        "crowding_score": 86,
        "page_balance_score": 83,
        "ocr_confidence_score": 90,
        "visual_diagnostic_score": 86,
        "page_reviews": [
            {"ocr_text_excerpt": "India closes a landmark trade deal with New Zealand."},
            {"ocr_text_excerpt": "Zero duty, work visas, student mobility."},
            {"ocr_text_excerpt": "Students, investment targets, AYUSH practitioners."},
            {"ocr_text_excerpt": "Focus on New Zealand and future deals."},
        ],
    }
    service._llm_prompt_relevance_analysis = lambda **kwargs: {  # type: ignore[method-assign]
        "source": "llm_vision",
        "model": "test-vision-model",
        "scores": {"prompt_adherence": 63, "relevance": 66},
        "explanations": {
            "prompt_adherence": "The carousel is about the FTA but does not break down sectoral and economic implications in detail.",
            "relevance": "The topic is relevant, but the useful implications are underdeveloped.",
        },
        "missing_content_or_visuals": ["sectoral impact breakdown", "economic implication breakdown"],
        "improvement_suggestions": ["Add slides covering agriculture, dairy, technology, services, trade growth, and investment flows."],
        "visual_quality_issues": [],
        "asset_type_assessment": {
            "asset_type": "carousel",
            "primary_purpose": "tell a story across multiple slides",
            "purpose_fit": "partial",
        },
        "visible_inventory": {},
        "prompt_content_contract": {
            "core_user_ask": "a carousel breaking down sectoral and economic implications worth watching",
            "expected_content_areas": [
                "sectoral impacts",
                "agriculture",
                "dairy",
                "technology",
                "education",
                "healthcare",
                "services",
                "trade growth",
                "exports",
                "GDP impact",
                "investment flows",
                "employment",
            ],
            "observed_content_areas": ["student mobility", "work visas", "trade access"],
            "missing_or_undercovered_content_areas": [
                "sector-by-sector breakdown",
                "agriculture and dairy implications",
                "technology/services implications",
                "GDP, exports, investment flows, and employment impact",
            ],
            "content_gap_reason": "The visible carousel mainly discusses mobility and access instead of the requested implication breakdown.",
        },
        "requirement_coverage": {
            "visible_requested_items": ["FTA topic", "student mobility", "work visas", "trade access"],
            "missing_or_unclear_requested_items": ["sectoral implications", "economic implications"],
            "completeness_reason": "The core breakdown requested by the prompt is incomplete.",
        },
        "critical_requirement_failures": ["sectoral and economic implication breakdown is incomplete"],
        "brand_intelligence_suggestions": [
            "Add dedicated slides for sectoral impacts and economic impacts instead of focusing mainly on mobility."
        ],
        "score_consistency_reason": "Scores are reduced because the carousel misses the requested content angle.",
        "evaluated_format": "carousel",
        "slide_observations": [],
        "carousel_story_assessment": {
            "hook_strength": "solid",
            "continuity": "partial",
            "progression": "narrows too much into mobility",
            "conclusion_or_promotion": "weak",
        },
        "asset_count": 4,
        "overlay_policy": {
            "do_not_penalize_missing_logo": True,
            "do_not_penalize_missing_cta": True,
        },
    }

    scorecard = service.build_scorecard(
        prompt=(
            "Create a LinkedIn carousel on the India-New Zealand FTA signed on 27 April 2026. "
            "Break down the sectoral and economic implications worth watching."
        ),
        studio_panel={"format": "carousel", "file_type": "png"},
        generated_payload={"slides": []},
        brand_context={"brand_name": "Jiraaf"},
        persona_context={"name": "Working professionals"},
        objective_context={"name": "Education"},
        explainability={"input_access_summary": {}},
        output_assets=[{"storage_path": "tenant/brand/generated/output.png", "mime_type": "image/png", "asset_kind": "image"}],
    )

    assert "mood alignment" in scorecard["summary"][0]
    assert "sectoral and economic implications" in scorecard["summary"][1]
    assert "student mobility, work visas, trade access" in scorecard["summary"][1]
    assert "GDP, exports, investment flows, and employment impact" in scorecard["summary"][1]
    assert scorecard["developer_explanation"]["prompt_adherence"]["llm_analysis"]["prompt_content_contract"]["core_user_ask"]


def test_brand_scoring_service_saves_json_to_brand_scoring_folder() -> None:
    service = BrandScoringService(session=None)
    tenant_id = uuid4()
    brand_space_id = uuid4()
    output_id = str(uuid4())
    scorecard = {
        "overall_score": 78,
        "score_breakdown": {"on_brand": 82, "prompt_adherence": 75, "relevance": 76},
        "weighting": {"on_brand": 0.4, "prompt_adherence": 0.35, "relevance": 0.25},
        "summary": ["Strong visual brand fit.", "Prompt topic is mostly followed.", "Output is relevant but slightly generic."],
        "developer_explanation": {
            "overall": {"formula": "overall = ...", "computed_from": {}, "weighted_contributions": {}, "final_score": 78},
            "on_brand": {"formula": "on_brand = ...", "score": 82, "components": {}},
            "prompt_adherence": {"formula": "prompt_adherence = ...", "score": 75, "components": {}},
            "relevance": {"formula": "relevance = ...", "score": 76, "components": {}},
        },
    }
    written = service.save_scorecard(
        tenant_id=tenant_id,
        brand_space_id=brand_space_id,
        output_id=output_id,
        scorecard=scorecard,
    )
    path = Path(written)
    try:
        assert path.exists()
        assert path.parent.name == "brand_scoring"
        assert path.parent.parent.name == str(brand_space_id)
        assert path.parent.parent.parent.name == str(tenant_id)
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload == scorecard
    finally:
        if path.exists():
            path.unlink()
