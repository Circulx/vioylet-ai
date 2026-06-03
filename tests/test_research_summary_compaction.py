from app.ai.orchestrator import AIOrchestratorService


def test_research_summary_context_payload_compacts_without_losing_research_signals() -> None:
    service = AIOrchestratorService()
    compiled_context = {
        "brand_copy_brief": {
            "positioning": "Premium fixed-income access for cautious wealth builders.",
            "differentiators": [
                "curated opportunities",
                "transparent risk notes",
                "investor education",
            ],
            "voice": "clear, calm, expert",
        },
        "audience_brief": {
            "audience_research_pain_points": [
                "fear of losing capital",
                "confusion comparing yield and risk",
            ],
            "audience_research_motivations": ["stable income", "better alternatives to idle cash"],
            "audience_research_objections": ["needs proof before trusting a new platform"],
        },
        "objective_brief": {
            "primary_goal": "educate investors before conversion",
            "desired_action": "review opportunities",
        },
        "knowledge_brief": [
            {
                "label": "risk note",
                "content": "Fixed-income returns must be evaluated alongside credit quality and liquidity.",
            }
        ],
        "template_fit_brief": {
            "template_layout_dna": "x" * 5000,
            "sequence_pack": {"slides": [{"headline_hint": "oversized irrelevant transport"}] * 30},
        },
        "prompt_intelligence_brief": {
            "starter_texts": ["Start with the investor misconception before explaining the proof."],
            "global_rules": ["Keep claims specific and educational."],
            "summary": "Use proof-first investor education.",
        },
        "research_editorial_brief": {
            "active": True,
            "angle": "risk-adjusted income beats headline yield chasing",
            "thesis": "The best yield is the one the investor can understand and hold.",
            "insight_hierarchy": ["Category audience_insight", "risk clarity", "liquidity fit", "portfolio role"],
            "outline": [{"index": "1", "role": "hook", "purpose": "challenge headline yield"}],
            "fact_model": {
                "verified_facts": [
                    {
                        "label": "risk disclosure",
                        "value": "Credit risk and liquidity risk should be reviewed before investing.",
                        "source_title": "Investor education note",
                        "source_url": "https://example.com/risk",
                    }
                ]
            },
        },
        "format_family_plan": {
            "family": "static",
            "format": "static",
            "content_structure": ["hook", "proof", "cta"],
        },
        "content_plan": {
            "format_family": "static",
            "sequence_contract": "single_surface_hierarchy",
            "planning_rules": ["make the risk/proof relationship explicit"],
        },
        "visual_plan": {"oversized_transport": "y" * 5000},
    }
    live_research = {
        "status": "complete",
        "summary": "Investors respond better when risk, liquidity, and return are explained together.",
        "verified_facts": [
            {
                "label": "liquidity",
                "value": "Liquidity varies by instrument.",
                "source_title": "Market guide",
                "source_url": "https://example.com/liquidity",
            }
        ],
        "inferences": ["Lead with trust and proof before product push."],
        "uncertainties": ["Do not imply guaranteed returns."],
        "ranked_sources": [{"title": "Market guide", "url": "https://example.com/liquidity"}],
        "queries": ["large raw search transport that should not be needed"] * 50,
    }

    old_payload = {
        "brand_copy_brief": compiled_context["brand_copy_brief"],
        "audience_brief": compiled_context["audience_brief"],
        "objective_brief": compiled_context["objective_brief"],
        "knowledge_brief": compiled_context["knowledge_brief"],
        "template_fit_brief": compiled_context["template_fit_brief"],
        "prompt_intelligence_brief": compiled_context["prompt_intelligence_brief"],
        "research_editorial_brief": compiled_context["research_editorial_brief"],
        "format_family_plan": compiled_context["format_family_plan"],
        "content_plan": compiled_context["content_plan"],
        "visual_plan": compiled_context["visual_plan"],
        "live_research": live_research,
    }
    compact = service._research_summary_context_payload(
        compiled_context=compiled_context,
        live_research=live_research,
    )

    assert "template_fit_brief" not in compact
    assert "visual_plan" not in compact
    assert "fear of losing capital" in str(compact["audience_brief"])
    assert compact["research_editorial_brief"]["thesis"] == compiled_context["research_editorial_brief"]["thesis"]
    assert compact["research_editorial_brief"]["angle"] == compiled_context["research_editorial_brief"]["angle"]
    assert compact["research_editorial_brief"]["insight_hierarchy"][0] == "Category audience_insight"
    assert compact["research_editorial_brief"]["fact_model"]["verified_facts"][0]["source_url"]
    assert compact["live_research"]["verified_facts"][0]["source_url"] == "https://example.com/liquidity"
    assert "queries" not in compact["live_research"]
    assert compact["format_family_plan"]["family"] == "static"
    assert compact["content_plan"]["sequence_contract"] == "single_surface_hierarchy"
    assert service._estimate_tokens(str(compact)) < service._estimate_tokens(str(old_payload)) * 0.35
