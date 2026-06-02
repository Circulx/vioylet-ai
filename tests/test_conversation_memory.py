from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from app.services.conversation_memory import ConversationMemoryService


def _fake_entry(*, memory_text: str, storage_path: str, created_at: datetime | None = None):
    return SimpleNamespace(
        id=uuid4(),
        created_at=created_at or datetime.now(timezone.utc),
        memory_text=memory_text,
        storage_path=storage_path,
        generated_asset_id=uuid4(),
        content_version_id=uuid4(),
        asset_role="ai_image",
        metadata_json={"mime_type": "image/png", "width": 1080, "height": 1080},
    )


def test_remove_display_inability_claims_keeps_useful_description() -> None:
    sanitized = ConversationMemoryService._remove_display_inability_claims(
        "Unfortunately, I can't display the image itself, but it breaks down the India-New Zealand FTA in a LinkedIn carousel."
    )

    assert "can't display" not in sanitized.lower()
    assert sanitized == "It breaks down the India-New Zealand FTA in a LinkedIn carousel."


@pytest.mark.asyncio
async def test_retrieve_image_assets_returns_not_found_for_explicit_unrelated_topic() -> None:
    service = ConversationMemoryService.__new__(ConversationMemoryService)
    service.entries = SimpleNamespace(
        list_image_entries=AsyncMock(
            return_value=[
                _fake_entry(
                    memory_text=(
                        "Generated image asset for session 'Chat Session'. "
                        "Prompt: Generate a carousel about bond mistakes and fixed deposits. "
                        "Headline: Common mistakes retail investors make with bonds. "
                        "Format: carousel. Platform: linkedin."
                    ),
                    storage_path="tenant/brand/generated/bonds-carousel.png",
                )
            ]
        )
    )
    service.vectors = SimpleNamespace(search=lambda namespace, query, k: [])
    service.providers = SimpleNamespace()
    service.delivery = SimpleNamespace()
    service.storage = SimpleNamespace()
    service._namespace = lambda tenant_id, brand_space_id: "memory/test"
    service._serialize_entry_asset = lambda entry: {
        "asset_id": str(entry.generated_asset_id),
        "content_version_id": str(entry.content_version_id),
        "mime_type": "image/png",
        "storage_path": entry.storage_path,
        "asset_url": "https://example.test/bonds-carousel.png",
        "width": 1080,
        "height": 1080,
        "asset_role": "ai_image",
        "memory_entry_id": str(entry.id),
        "memory_text": entry.memory_text,
    }
    service._llm_select_candidate_indexes = lambda **kwargs: {
        "selected_indexes": [],
        "reason": "No candidate mentions New Zealand.",
        "selection_state": "no_relevant_match",
    }

    result = await service.retrieve_image_assets(
        tenant_id=uuid4(),
        brand_space_id=uuid4(),
        session_id=uuid4(),
        query="show me the earlier carousel images about new-zealand",
    )

    assert result["status"] == "not_found"
    assert result["assets"] == []
    assert result["selected_asset"] is None


@pytest.mark.asyncio
async def test_retrieve_image_assets_keeps_generic_recent_image_fallback_when_llm_unavailable() -> None:
    service = ConversationMemoryService.__new__(ConversationMemoryService)
    newest = _fake_entry(
        memory_text=(
            "Generated image asset for session 'Chat Session'. "
            "Prompt: Generate a LinkedIn finance carousel. "
            "Headline: FD Bonds explained. "
            "Format: carousel. Platform: linkedin. Asset address: tenant/brand/generated/fd-bonds.png."
        ),
        storage_path="tenant/brand/generated/fd-bonds.png",
        created_at=datetime.now(timezone.utc),
    )
    older = _fake_entry(
        memory_text=(
            "Generated image asset for session 'Chat Session'. "
            "Prompt: Generate a static bond teaser. "
            "Headline: Build fixed-income confidence. "
            "Format: static. Platform: linkedin. Asset address: tenant/brand/generated/bond-teaser.png."
        ),
        storage_path="tenant/brand/generated/bond-teaser.png",
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    service.entries = SimpleNamespace(list_image_entries=AsyncMock(return_value=[newest, older]))
    service.vectors = SimpleNamespace(search=lambda namespace, query, k: [])
    service.providers = SimpleNamespace()
    service.delivery = SimpleNamespace()
    service.storage = SimpleNamespace()
    service._namespace = lambda tenant_id, brand_space_id: "memory/test"
    service._serialize_entry_asset = lambda entry: {
        "asset_id": str(entry.generated_asset_id),
        "content_version_id": str(entry.content_version_id),
        "mime_type": "image/png",
        "storage_path": entry.storage_path,
        "asset_url": f"https://example.test/{entry.storage_path.rsplit('/', 1)[-1]}",
        "width": 1080,
        "height": 1080,
        "asset_role": "ai_image",
        "memory_entry_id": str(entry.id),
        "memory_text": entry.memory_text,
    }
    service._llm_select_candidate_indexes = lambda **kwargs: None
    service._llm_describe_selected_asset = lambda **kwargs: "Here is the last generated image from this conversation."

    result = await service.retrieve_image_assets(
        tenant_id=uuid4(),
        brand_space_id=uuid4(),
        session_id=uuid4(),
        query="can you show me the last generated image",
    )

    assert result["status"] == "found"
    assert result["selected_asset"]["storage_path"].endswith("fd-bonds.png")
    assert result["assets"][0]["storage_path"].endswith("fd-bonds.png")


@pytest.mark.asyncio
async def test_retrieve_image_assets_expands_carousel_to_all_content_version_slides() -> None:
    shared_content_version_id = uuid4()
    service = ConversationMemoryService.__new__(ConversationMemoryService)
    lead_entry = _fake_entry(
        memory_text=(
            "Generated image asset for session 'Chat Session'. "
            "Prompt: Generate a LinkedIn carousel about FD Bonds. "
            "Headline: FD Bonds explained. "
            "Format: carousel. Platform: linkedin."
        ),
        storage_path="tenant/brand/generated/fd-carousel-slide-1.png",
    )
    lead_entry.content_version_id = shared_content_version_id
    service.entries = SimpleNamespace(list_image_entries=AsyncMock(return_value=[lead_entry]))
    service.vectors = SimpleNamespace(search=lambda namespace, query, k: [])
    service.providers = SimpleNamespace()
    service.delivery = SimpleNamespace()
    service.storage = SimpleNamespace()
    service._namespace = lambda tenant_id, brand_space_id: "memory/test"
    service._serialize_entry_asset = lambda entry: {
        "asset_id": str(entry.generated_asset_id),
        "content_version_id": str(entry.content_version_id),
        "mime_type": "image/png",
        "storage_path": entry.storage_path,
        "asset_url": "https://example.test/fd-carousel-slide-1.png",
        "width": 1080,
        "height": 1080,
        "asset_role": "render_export",
        "memory_entry_id": str(entry.id),
        "memory_text": entry.memory_text,
    }
    service._llm_select_candidate_indexes = lambda **kwargs: {
        "selected_indexes": [0],
        "reason": "Matched the latest FD Bonds carousel.",
        "selection_state": "match_found",
    }
    service._llm_describe_selected_asset = lambda **kwargs: "Here is the FD Bonds carousel from this conversation."
    service.assets = SimpleNamespace(
        list_by_content=AsyncMock(
            return_value=[
                SimpleNamespace(
                    id=uuid4(),
                    content_version_id=shared_content_version_id,
                    asset_role="render_export",
                    mime_type="image/png",
                    storage_path="tenant/brand/generated/fd-carousel-slide-1.png",
                    width=1080,
                    height=1080,
                    created_at=datetime.now(timezone.utc),
                ),
                SimpleNamespace(
                    id=uuid4(),
                    content_version_id=shared_content_version_id,
                    asset_role="render_export",
                    mime_type="image/png",
                    storage_path="tenant/brand/generated/fd-carousel-slide-2.png",
                    width=1080,
                    height=1080,
                    created_at=datetime.now(timezone.utc) + timedelta(milliseconds=1),
                ),
            ]
        )
    )
    service._serialize_generated_asset = lambda asset: {
        "asset_id": str(asset.id),
        "content_version_id": str(asset.content_version_id),
        "mime_type": "image/png",
        "storage_path": asset.storage_path,
        "asset_url": f"https://example.test/{asset.storage_path.rsplit('/', 1)[-1]}",
        "width": 1080,
        "height": 1080,
        "asset_role": asset.asset_role,
        "memory_entry_id": None,
        "memory_text": None,
    }

    result = await service.retrieve_image_assets(
        tenant_id=uuid4(),
        brand_space_id=uuid4(),
        session_id=uuid4(),
        query="show me the last generated image",
    )

    assert result["status"] == "found"
    assert len(result["assets"]) == 2
    assert result["assets"][0]["storage_path"].endswith("fd-carousel-slide-1.png")
    assert result["assets"][1]["storage_path"].endswith("fd-carousel-slide-2.png")


@pytest.mark.asyncio
async def test_retrieve_image_assets_keeps_ai_final_carousel_preview_and_exports_in_slide_order() -> None:
    shared_content_version_id = uuid4()
    now = datetime.now(timezone.utc)
    service = ConversationMemoryService.__new__(ConversationMemoryService)
    lead_entry = _fake_entry(
        memory_text=(
            "Generated image asset for session 'Chat Session'. "
            "Prompt: Generate a LinkedIn carousel about FD Bonds. "
            "Headline: FD Bonds explained. Format: carousel. Platform: linkedin."
        ),
        storage_path="tenant/brand/generated/fd-carousel-slide-3.png",
    )
    lead_entry.content_version_id = shared_content_version_id
    service.entries = SimpleNamespace(list_image_entries=AsyncMock(return_value=[lead_entry]))
    service.vectors = SimpleNamespace(search=lambda namespace, query, k: [])
    service.providers = SimpleNamespace()
    service.delivery = SimpleNamespace()
    service.storage = SimpleNamespace()
    service._namespace = lambda tenant_id, brand_space_id: "memory/test"
    service._serialize_entry_asset = lambda entry: {
        "asset_id": str(entry.generated_asset_id),
        "content_version_id": str(entry.content_version_id),
        "mime_type": "image/png",
        "storage_path": entry.storage_path,
        "asset_url": "https://example.test/fd-carousel-slide-3.png",
        "width": 1080,
        "height": 1080,
        "asset_role": "render_export",
        "memory_entry_id": str(entry.id),
        "memory_text": entry.memory_text,
    }
    service._llm_select_candidate_indexes = lambda **kwargs: {
        "selected_indexes": [0],
        "reason": "Matched the latest FD Bonds carousel.",
        "selection_state": "match_found",
    }
    service._llm_describe_selected_asset = lambda **kwargs: "Here is the FD Bonds carousel from this conversation."
    service.assets = SimpleNamespace(
        list_by_content=AsyncMock(
            return_value=[
                SimpleNamespace(
                    id=uuid4(),
                    content_version_id=shared_content_version_id,
                    asset_role="render_export",
                    mime_type="image/png",
                    storage_path="tenant/brand/generated/fd-carousel-slide-3.png",
                    width=1080,
                    height=1080,
                    created_at=now,
                    metadata_json={
                        "render_source": "ai",
                        "generation_stage": "final_render",
                        "slide_index": 3,
                        "slide_count": 3,
                    },
                ),
                SimpleNamespace(
                    id=uuid4(),
                    content_version_id=shared_content_version_id,
                    asset_role="render_export",
                    mime_type="image/png",
                    storage_path="tenant/brand/generated/fd-carousel-slide-2.png",
                    width=1080,
                    height=1080,
                    created_at=now + timedelta(milliseconds=2),
                    metadata_json={
                        "render_source": "ai",
                        "generation_stage": "final_render",
                        "slide_index": 2,
                        "slide_count": 3,
                    },
                ),
                SimpleNamespace(
                    id=uuid4(),
                    content_version_id=shared_content_version_id,
                    asset_role="render_preview",
                    mime_type="image/png",
                    storage_path="tenant/brand/generated/fd-carousel-slide-1.png",
                    width=1080,
                    height=1080,
                    created_at=now + timedelta(milliseconds=4),
                    metadata_json={
                        "render_source": "ai",
                        "generation_stage": "final_render",
                        "slide_index": 1,
                        "slide_count": 3,
                    },
                ),
            ]
        )
    )
    service._serialize_generated_asset = lambda asset: {
        "asset_id": str(asset.id),
        "content_version_id": str(asset.content_version_id),
        "mime_type": "image/png",
        "storage_path": asset.storage_path,
        "asset_url": f"https://example.test/{asset.storage_path.rsplit('/', 1)[-1]}",
        "width": 1080,
        "height": 1080,
        "asset_role": asset.asset_role,
        "memory_entry_id": None,
        "memory_text": None,
    }

    result = await service.retrieve_image_assets(
        tenant_id=uuid4(),
        brand_space_id=uuid4(),
        session_id=uuid4(),
        query="show me the last generated image",
    )

    assert result["status"] == "found"
    assert [asset["storage_path"].rsplit("/", 1)[-1] for asset in result["assets"]] == [
        "fd-carousel-slide-1.png",
        "fd-carousel-slide-2.png",
        "fd-carousel-slide-3.png",
    ]


@pytest.mark.asyncio
async def test_index_generated_assets_stores_final_displayed_render_payload_path() -> None:
    service = ConversationMemoryService.__new__(ConversationMemoryService)
    captured: list[dict] = []

    async def fake_upsert_entry(**kwargs):
        captured.append(kwargs)
        return SimpleNamespace(id=uuid4())

    service._upsert_entry = fake_upsert_entry
    tenant_id = uuid4()
    brand_space_id = uuid4()
    session_id = uuid4()
    content_version_id = uuid4()
    session = SimpleNamespace(id=session_id, title="Chat Session")
    content_version = SimpleNamespace(
        id=content_version_id,
        tenant_id=tenant_id,
        brand_space_id=brand_space_id,
        session_id=session_id,
        prompt="Generate a static post about the FTA",
        generated_payload={
            "headline": "Why This FTA Matters",
            "body": "India's evolving trade strategy.",
            "cta": "Small deal. Bigger shape.",
        },
        studio_panel={"format": "static", "platform_preset": "instagram"},
    )

    await service.index_generated_assets(
        session=session,
        content_version=content_version,
        assets=[
            {
                "storage_path": "tenant/brand/generated/final-with-logo-and-disclaimer.png",
                "asset_role": "render_preview",
                "mime_type": "image/png",
                "width": 1024,
                "height": 1536,
                "metadata": {
                    "logo_composited_by_service": True,
                    "legal_footer_composited_by_service": True,
                },
            }
        ],
    )

    assert captured
    assert captured[0]["generated_asset_id"] is None
    assert captured[0]["storage_path"] == "tenant/brand/generated/final-with-logo-and-disclaimer.png"
    assert captured[0]["metadata_json"]["displayed_asset"] is True
    assert captured[0]["metadata_json"]["logo_composited_by_service"] is True
    assert captured[0]["metadata_json"]["legal_footer_composited_by_service"] is True
    assert "Final displayed image asset" in captured[0]["memory_text"]


@pytest.mark.asyncio
async def test_retrieve_image_assets_prefers_displayed_final_paths_over_raw_db_assets() -> None:
    shared_content_version_id = uuid4()
    now = datetime.now(timezone.utc)
    raw_entry = SimpleNamespace(
        id=uuid4(),
        created_at=now,
        memory_text=(
            "Generated image asset for session 'Chat Session'. "
            "Prompt: Generate a static post about the FTA. Headline: Why This FTA Matters."
        ),
        storage_path="tenant/brand/generated/raw-ai-draft.png",
        generated_asset_id=uuid4(),
        content_version_id=shared_content_version_id,
        asset_role="ai_image",
        metadata_json={"mime_type": "image/png", "width": 1024, "height": 1536},
    )
    displayed_slide_2 = SimpleNamespace(
        id=uuid4(),
        created_at=now + timedelta(milliseconds=1),
        memory_text=(
            "Final displayed image asset for session 'Chat Session'. "
            "Prompt: Generate a static post about the FTA. Headline: Why This FTA Matters."
        ),
        storage_path="tenant/brand/generated/final-with-logo-slide-2.png",
        generated_asset_id=None,
        content_version_id=shared_content_version_id,
        asset_role="render_export",
        metadata_json={
            "mime_type": "image/png",
            "width": 1024,
            "height": 1536,
            "displayed_asset": True,
            "slide_index": 2,
            "legal_footer_composited_by_service": True,
        },
    )
    displayed_slide_1 = SimpleNamespace(
        id=uuid4(),
        created_at=now + timedelta(milliseconds=2),
        memory_text=displayed_slide_2.memory_text,
        storage_path="tenant/brand/generated/final-with-logo-slide-1.png",
        generated_asset_id=None,
        content_version_id=shared_content_version_id,
        asset_role="render_preview",
        metadata_json={
            "mime_type": "image/png",
            "width": 1024,
            "height": 1536,
            "displayed_asset": True,
            "slide_index": 1,
            "logo_composited_by_service": True,
            "legal_footer_composited_by_service": True,
        },
    )

    service = ConversationMemoryService.__new__(ConversationMemoryService)
    service.entries = SimpleNamespace(
        list_image_entries=AsyncMock(return_value=[raw_entry, displayed_slide_2, displayed_slide_1])
    )
    service.vectors = SimpleNamespace(search=lambda namespace, query, k: [])
    service.providers = SimpleNamespace()
    service.delivery = SimpleNamespace(
        build_signed_url=lambda storage_path, filename: f"https://example.test/{filename}"
    )
    service.storage = SimpleNamespace(exists=lambda storage_path: True)
    service.assets = SimpleNamespace(list_by_content=AsyncMock(return_value=[]))
    service._namespace = lambda tenant_id, brand_space_id: "memory/test"
    service._llm_select_candidate_indexes = lambda **kwargs: {
        "selected_indexes": [0],
        "reason": "Selected the matching generated image.",
        "selection_state": "match_found",
    }
    service._llm_describe_selected_asset = lambda **kwargs: "Here is the last generated image."

    result = await service.retrieve_image_assets(
        tenant_id=uuid4(),
        brand_space_id=uuid4(),
        session_id=uuid4(),
        query="show me the last generated image",
    )

    assert result["status"] == "found"
    assert [asset["storage_path"].rsplit("/", 1)[-1] for asset in result["assets"]] == [
        "final-with-logo-slide-1.png",
        "final-with-logo-slide-2.png",
    ]
    assert "raw-ai-draft.png" not in [asset["storage_path"].rsplit("/", 1)[-1] for asset in result["assets"]]
    service.assets.list_by_content.assert_not_awaited()


@pytest.mark.asyncio
async def test_retrieve_image_assets_returns_complete_displayed_carousel_not_limited_to_top_three() -> None:
    shared_content_version_id = uuid4()
    now = datetime.now(timezone.utc)

    def displayed_entry(slide_index: int):
        return SimpleNamespace(
            id=uuid4(),
            created_at=now + timedelta(milliseconds=slide_index),
            memory_text=(
                "Final displayed image asset for session 'Chat Session'. "
                "Prompt: Generate a LinkedIn carousel about FTA updates. "
                "Headline: Why This FTA Matters."
            ),
            storage_path=f"tenant/brand/generated/final-carousel-slide-{slide_index}.png",
            generated_asset_id=None,
            content_version_id=shared_content_version_id,
            asset_role="render_export" if slide_index > 1 else "render_preview",
            metadata_json={
                "mime_type": "image/png",
                "width": 1024,
                "height": 1536,
                "displayed_asset": True,
                "slide_index": slide_index,
                "slide_count": 5,
            },
        )

    entries = [displayed_entry(index) for index in [5, 4, 3, 2, 1]]
    service = ConversationMemoryService.__new__(ConversationMemoryService)
    service.entries = SimpleNamespace(list_image_entries=AsyncMock(return_value=entries))
    service.vectors = SimpleNamespace(search=lambda namespace, query, k: [])
    service.providers = SimpleNamespace()
    service.delivery = SimpleNamespace(
        build_signed_url=lambda storage_path, filename: f"https://example.test/{filename}"
    )
    service.storage = SimpleNamespace(exists=lambda storage_path: True)
    service.assets = SimpleNamespace(list_by_content=AsyncMock(return_value=[]))
    service._namespace = lambda tenant_id, brand_space_id: "memory/test"
    service._llm_select_candidate_indexes = lambda **kwargs: {
        "selected_indexes": [0],
        "reason": "Selected the matching carousel.",
        "selection_state": "match_found",
    }
    service._llm_describe_selected_asset = lambda **kwargs: "Here is the full carousel."

    result = await service.retrieve_image_assets(
        tenant_id=uuid4(),
        brand_space_id=uuid4(),
        session_id=uuid4(),
        query="show me the last generated carousel",
        limit=3,
    )

    assert result["status"] == "found"
    assert [asset["storage_path"].rsplit("/", 1)[-1] for asset in result["assets"]] == [
        "final-carousel-slide-1.png",
        "final-carousel-slide-2.png",
        "final-carousel-slide-3.png",
        "final-carousel-slide-4.png",
        "final-carousel-slide-5.png",
    ]
    service.assets.list_by_content.assert_not_awaited()
