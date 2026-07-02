from types import SimpleNamespace

import pytest

from app.services.live_research import LiveResearchService


@pytest.mark.asyncio
async def test_live_research_force_returns_not_configured_when_no_backend_exists() -> None:
    service = LiveResearchService()
    service.settings.live_research_enabled = True
    service.settings.brave_search_api_key = None
    service.openai_search_client = None

    result = await service.gather(
        "Create a static post about savings habits.",
        {"platform_preset": "instagram", "format": "static"},
        {"knowledge_brief": []},
        force=True,
    )

    assert result["status"] == "not_configured"
    assert result["summary"]
    assert result["queries"]


@pytest.mark.asyncio
async def test_live_research_uses_openai_web_search_when_configured() -> None:
    service = LiveResearchService()
    service.settings.live_research_enabled = True
    service.settings.live_research_search_backend = "openai"
    service.settings.brave_search_api_key = None
    service.openai_search_client = object()
    service.research_provider = SimpleNamespace(
        client=True,
        generate_structured_json=lambda envelope, fallback: {
            "summary": "The FTA was signed on 27 April 2026.",
            "verified_facts": [
                {
                    "label": "FTA signing date",
                    "value": "27 April 2026",
                    "source_title": "Trade ministry note",
                    "source_url": "https://example.com/fta",
                }
            ],
        },
    )

    async def _fake_plan_queries(prompt, studio_panel, compiled_context):  # noqa: ARG001
        return {
            "needs_live_research": True,
            "queries": ["India New Zealand FTA 27 April 2026"],
            "facts_to_verify": ["signing date"],
            "preferred_sources": [],
        }

    async def _fake_openai_web_search(query):  # noqa: ARG001
        return [{"url": "https://example.com/fta", "title": "Trade ministry note", "snippet": "FTA signed"}]

    async def _fake_fetch_url_text(client, url):  # noqa: ARG001
        return {
            "url": url,
            "title": "Trade ministry note",
            "content": "India and New Zealand signed the FTA on 27 April 2026.",
        }

    service._plan_queries = _fake_plan_queries
    service._openai_web_search = _fake_openai_web_search
    service._fetch_url_text = _fake_fetch_url_text

    result = await service.gather(
        "Write a LinkedIn carousel about the India-New Zealand FTA signed on 27 April 2026.",
        {"platform_preset": "linkedin", "format": "carousel"},
        {"knowledge_brief": []},
        force=True,
    )

    assert result["status"] == "completed"
    assert result["verified_facts"][0]["value"] == "27 April 2026"
    assert result["sources"][0]["url"] == "https://example.com/fta"


@pytest.mark.asyncio
async def test_live_research_gather_synthesizes_verified_facts_from_mocked_sources() -> None:
    service = LiveResearchService()
    service.settings.live_research_enabled = True
    service.settings.live_research_search_backend = "brave"
    service.settings.brave_search_api_key = "test-key"
    service.research_provider = SimpleNamespace(
        client=True,
        generate_structured_json=lambda envelope, fallback: {
            "summary": "FDI inflow reached USD 100 billion in 2025.",
            "verified_facts": [
                {
                    "label": "FDI inflow",
                    "value": "USD 100 billion",
                    "source_title": "Economic report",
                    "source_url": "https://example.com/fdi",
                }
            ],
        },
    )

    async def _fake_plan_queries(prompt, studio_panel, compiled_context):  # noqa: ARG001
        return {
            "needs_live_research": True,
            "queries": ["india fdi inflow 2025"],
            "facts_to_verify": ["exact values"],
            "preferred_sources": [],
        }

    async def _fake_brave_search(client, query):  # noqa: ARG001
        return [{"url": "https://example.com/fdi", "title": "Economic report", "snippet": "FDI inflow data"}]

    async def _fake_fetch_url_text(client, url):  # noqa: ARG001
        return {
            "url": url,
            "title": "Economic report",
            "content": "FDI inflow reached USD 100 billion in 2025.",
        }

    service._plan_queries = _fake_plan_queries
    service._brave_search = _fake_brave_search
    service._fetch_url_text = _fake_fetch_url_text

    result = await service.gather(
        "Create a data-led post about FDI inflows into India.",
        {"platform_preset": "linkedin", "format": "static"},
        {"knowledge_brief": []},
        force=True,
    )

    assert result["status"] == "completed"
    assert result["verified_facts"][0]["value"] == "USD 100 billion"
    assert result["sources"][0]["url"] == "https://example.com/fdi"


@pytest.mark.asyncio
async def test_live_research_fallback_planner_requires_research_for_top_n_ranking() -> None:
    service = LiveResearchService()
    service.research_provider = SimpleNamespace(client=None)

    plan = await service._plan_queries(
        "Create a static post comparing a metric and create a top 10 ranking.",
        {"platform_preset": "linkedin", "format": "static"},
        {"knowledge_brief": []},
    )

    assert plan["needs_live_research"] is True
    assert "distinct source-backed rows for the requested top 10 ranking" in plan["facts_to_verify"]


@pytest.mark.asyncio
async def test_live_research_preserves_requested_top_ten_verified_facts() -> None:
    service = LiveResearchService()
    service.settings.live_research_enabled = True
    service.settings.live_research_search_backend = "openai"
    service.settings.brave_search_api_key = None
    service.openai_search_client = object()
    facts = [
        {
            "label": f"Rank {index}",
            "value": f"Value {index}",
            "source_title": "Ranking source",
            "source_url": "https://example.com/ranking",
        }
        for index in range(1, 11)
    ]
    captured = {}

    def _generate_structured_json(envelope, fallback):  # noqa: ANN001, ANN202, ARG001
        captured["system"] = envelope.system
        captured["user"] = envelope.user
        return {"summary": "Source-backed ranking rows.", "verified_facts": facts}

    service.research_provider = SimpleNamespace(client=True, generate_structured_json=_generate_structured_json)

    async def _fake_plan_queries(prompt, studio_panel, compiled_context):  # noqa: ARG001
        return {
            "needs_live_research": True,
            "queries": ["top 10 ranking data"],
            "facts_to_verify": ["distinct source-backed rows"],
            "preferred_sources": [],
        }

    async def _fake_openai_web_search(query):  # noqa: ARG001
        return [{"url": "https://example.com/ranking", "title": "Ranking source", "snippet": "Ranking rows"}]

    async def _fake_fetch_url_text(client, url):  # noqa: ARG001
        return {
            "url": url,
            "title": "Ranking source",
            "content": "Ranking source includes ten distinct rows for the requested table.",
        }

    service._plan_queries = _fake_plan_queries
    service._openai_web_search = _fake_openai_web_search
    service._fetch_url_text = _fake_fetch_url_text

    result = await service.gather(
        "Create a static post comparing a metric and create a top 10 ranking.",
        {"platform_preset": "linkedin", "format": "static"},
        {"knowledge_brief": []},
        force=True,
    )

    assert result["status"] == "completed"
    assert result["verified_fact_limit"] == 10
    assert len(result["verified_facts"]) == 10
    assert "up to 10 distinct verified_facts" in captured["system"]
    assert "Requested verified fact limit: 10" in captured["user"]
