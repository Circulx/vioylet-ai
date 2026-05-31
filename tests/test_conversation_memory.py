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
