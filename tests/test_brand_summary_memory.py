from types import SimpleNamespace
from uuid import uuid4

from app.services.brand_summary_memory import BrandSummaryMemoryService


def test_brand_summary_documents_include_postgres_audience_sections() -> None:
    brand = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        name="The Good Fish Company",
        description="Fresh seafood brand",
        industry_category="Food and beverage",
        sub_industry="Seafood",
        geography_country=None,
        geography_city=None,
        audience_type=None,
        resolved_brand_context={},
    )
    sections = [
        SimpleNamespace(
            section_code="identity",
            payload={
                "brand_name": "The Good Fish Company",
                "audience_type": "Health-conscious families",
                "target_geography": {"country": "India"},
            },
        ),
        SimpleNamespace(
            section_code="personas",
            payload={
                "personas": [
                    {
                        "name": "Urban seafood buyers",
                        "audience_goals": ["Buy fresh fish safely"],
                        "content_behavior": {
                            "selected_audiences": ["Health-conscious families", "Home cooks"]
                        },
                    }
                ]
            },
        ),
    ]

    docs = BrandSummaryMemoryService._build_documents(brand, sections=sections)
    combined = "\n".join(doc["content"] for doc in docs)

    assert "Audience type: Health-conscious families" in combined
    assert "PostgreSQL form section personas" in combined
    assert "Urban seafood buyers" in combined
    assert "Buy fresh fish safely" in combined
