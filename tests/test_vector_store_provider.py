from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.ai.brand_asset_analysis import AssetProcessingOutcome
from app.ai.rag.retrieval import KnowledgeRetrievalService
from app.core.config import get_settings
from app.integrations.vector_store import FaissVectorStoreProvider, PgVectorStoreProvider, get_vector_store_provider
from app.services.brand_assets import BrandAssetService


def test_vector_store_incremental_upsert_preserves_existing_documents() -> None:
    settings = get_settings()
    original_provider = settings.vector_store_provider
    original_base_path = settings.vector_store_base_path
    original_openai_key = settings.openai_api_key
    temp_root = Path("tests") / f"tmp-vector-store-{uuid4()}"
    temp_root.mkdir(parents=True, exist_ok=True)
    settings.vector_store_provider = "faiss"
    settings.vector_store_base_path = str(temp_root)
    settings.openai_api_key = None
    try:
        provider = FaissVectorStoreProvider()
        namespace = provider.namespace("tenant-1", "brand-1", "brand")
        provider.upsert_documents(
            namespace,
            [
                {
                    "content": "First brand guideline",
                    "metadata": {"chunk_id": "chunk-1", "source_id": "asset-1"},
                }
            ],
        )
        provider.upsert_documents(
            namespace,
            [
                {
                    "content": "Second audience insight",
                    "metadata": {"chunk_id": "chunk-2", "source_id": "asset-2"},
                }
            ],
        )

        docs = json.loads((temp_root / namespace.replace("/", "__") / "documents.json").read_text(encoding="utf-8"))

        assert {doc["metadata"]["chunk_id"] for doc in docs} == {"chunk-1", "chunk-2"}
    finally:
        settings.vector_store_provider = original_provider
        settings.vector_store_base_path = original_base_path
        settings.openai_api_key = original_openai_key
        if temp_root.exists():
            for child in sorted(temp_root.rglob("*"), reverse=True):
                if child.is_file():
                    child.unlink()
                elif child.is_dir():
                    child.rmdir()
            temp_root.rmdir()


def test_retrieval_service_indexes_structured_documents_with_metadata() -> None:
    settings = get_settings()
    original_provider = settings.vector_store_provider
    original_base_path = settings.vector_store_base_path
    original_openai_key = settings.openai_api_key
    temp_root = Path("tests") / f"tmp-retrieval-store-{uuid4()}"
    temp_root.mkdir(parents=True, exist_ok=True)
    settings.vector_store_provider = "faiss"
    settings.vector_store_base_path = str(temp_root)
    settings.openai_api_key = None
    try:
        retrieval = KnowledgeRetrievalService()
        retrieval.index_documents(
            tenant_id="tenant-1",
            brand_space_id="brand-1",
            channel="visual_identity",
            source_id="asset-1",
            documents=[
                {
                    "content": "Category color_palette. Palette cues: primary #003975, secondary #FFA400.",
                    "metadata": {
                        "document_type": "structured_summary",
                        "asset_id": "asset-1",
                        "structured_signal_score": 5,
                    },
                }
            ],
        )

        namespace = retrieval.vector_store.namespace("tenant-1", "brand-1", "visual_identity")
        docs = json.loads((temp_root / namespace.replace("/", "__") / "documents.json").read_text(encoding="utf-8"))

        assert docs[0]["metadata"]["document_type"] == "structured_summary"
        assert docs[0]["metadata"]["structured_signal_score"] == 5
        assert docs[0]["metadata"]["source_id"] == "asset-1"
    finally:
        settings.vector_store_provider = original_provider
        settings.vector_store_base_path = original_base_path
        settings.openai_api_key = original_openai_key
        if temp_root.exists():
            for child in sorted(temp_root.rglob("*"), reverse=True):
                if child.is_file():
                    child.unlink()
                elif child.is_dir():
                    child.rmdir()
            temp_root.rmdir()


class _TinyEmbeddings:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [1.0, 0.0]


class _FakeCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple | None]] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def execute(self, sql: str, params: tuple | None = None) -> None:
        self.executed.append((sql, params))

    def fetchall(self):
        return [("Matched visual rule", {"chunk_id": "chunk-1", "source_id": "asset-1"}, 0.12)]


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def cursor(self) -> _FakeCursor:
        return self._cursor

    def commit(self) -> None:
        self.commits += 1


def test_pgvector_provider_upserts_searches_and_deletes_with_shared_database() -> None:
    cursor = _FakeCursor()
    connection = _FakeConnection(cursor)
    provider = PgVectorStoreProvider(
        connection_factory=lambda: connection,
        embeddings=_TinyEmbeddings(),
    )

    namespace = provider.namespace("tenant-1", "brand-1", "visual_identity")
    provider.upsert_documents(
        namespace,
        [
            {
                "content": "Use the primary blue for investor education graphics.",
                "metadata": {"chunk_id": "chunk-1", "source_id": "asset-1"},
            }
        ],
    )
    results = provider.search(namespace, "primary color", k=1)
    provider.delete_source(namespace, "asset-1")

    executed_sql = "\n".join(sql for sql, _params in cursor.executed)
    assert "CREATE EXTENSION IF NOT EXISTS vector" in executed_sql
    assert "INSERT INTO retrieval_vector_documents" in executed_sql
    assert "ORDER BY embedding <=>" in executed_sql
    assert "DELETE FROM retrieval_vector_documents" in executed_sql
    assert results[0].content == "Matched visual rule"
    assert results[0].metadata["source_id"] == "asset-1"
    assert connection.commits >= 3


def test_vector_store_factory_defaults_to_faiss(monkeypatch) -> None:
    settings = get_settings()
    temp_root = Path("tests") / f"tmp-factory-store-{uuid4()}"
    monkeypatch.setattr(settings, "vector_store_provider", "faiss")
    monkeypatch.setattr(settings, "vector_store_base_path", str(temp_root))
    monkeypatch.setattr(settings, "openai_api_key", None)

    try:
        assert isinstance(get_vector_store_provider(), FaissVectorStoreProvider)
    finally:
        if temp_root.exists():
            for child in sorted(temp_root.rglob("*"), reverse=True):
                if child.is_file():
                    child.unlink()
                elif child.is_dir():
                    child.rmdir()
            temp_root.rmdir()


def test_structured_retrieval_documents_include_quality_metadata_and_channel_specific_docs() -> None:
    asset = SimpleNamespace(
        id=uuid4(),
        original_filename="palette-guide.pdf",
        field_key="color_palette",
        asset_category="color_palette",
    )
    outcome = AssetProcessingOutcome(
        routed_category="color_palette",
        channel="visual_identity",
        extracted_text="Primary color #003975\nSecondary color #FFA400",
        page_count=1,
        structured_data={
            "summary": "Palette system: primary #003975, secondary #FFA400.",
            "palette_entries": [
                {"role": "primary", "hex_code": "#003975"},
                {"role": "secondary", "hex_code": "#FFA400"},
            ],
            "visual_evidence_units": [
                {
                    "kind": "palette",
                    "summary": "Palette system: primary #003975, secondary #FFA400.",
                    "source": "hybrid",
                }
            ],
            "analysis_quality": {
                "analysis_quality_score": 8.7,
                "summary_quality_score": 7.9,
                "ocr_signal_score": 6.8,
                "ocr_noise_ratio": 0.1,
                "promotional_line_ratio": 0.0,
                "selected_line_count": 2,
                "candidate_line_count": 2,
                "evidence_types": ["palette"],
            },
        },
        normalized_data={"summary": "Palette system: primary #003975, secondary #FFA400."},
        routing={},
        warnings=[],
        confidence=0.95,
        validation_state="clean",
        template_analysis=None,
        template_tags=[],
        image_candidates=[],
        derived_assets=[],
        source_format="pdf",
    )

    documents = BrandAssetService._structured_retrieval_documents(asset, outcome)

    document_types = {item["metadata"]["document_type"] for item in documents}
    assert "structured_summary" in document_types
    assert "structured_palette" in document_types
    assert "structured_visual_unit" in document_types
    assert all(item["metadata"]["analysis_quality_score"] == 8.7 for item in documents)
    assert all(item["metadata"]["visual_grounding_allowed"] is True for item in documents)


def test_structured_retrieval_documents_split_template_structure_from_template_copy() -> None:
    asset = SimpleNamespace(
        id=uuid4(),
        original_filename="template-guide.pdf",
        field_key="brand_knowledge_templates",
        asset_category="template",
    )
    outcome = AssetProcessingOutcome(
        routed_category="template",
        channel="template",
        extracted_text="Why Investors Are Moving From FDs To Bonds In 2026",
        page_count=1,
        structured_data={
            "structure_summary": "Layout editorial split. Palette: primary #003975, secondary #FFA400.",
            "style_summary": "Layout editorial split. Palette: primary #003975, secondary #FFA400.",
            "summary": "Layout editorial split. Palette: primary #003975, secondary #FFA400.",
            "copy_lines": ["Why Investors Are Moving From FDs To Bonds In 2026", "Apply now"],
            "analysis_quality": {
                "analysis_quality_score": 8.4,
                "summary_quality_score": 7.8,
                "ocr_signal_score": 6.9,
                "ocr_noise_ratio": 0.1,
                "promotional_line_ratio": 0.2,
                "selected_line_count": 3,
                "candidate_line_count": 4,
                "evidence_types": ["layout", "palette", "zones"],
            },
        },
        normalized_data={
            "structure_summary": "Layout editorial split. Palette: primary #003975, secondary #FFA400.",
            "summary": "Layout editorial split. Palette: primary #003975, secondary #FFA400.",
            "copy_lines": ["Why Investors Are Moving From FDs To Bonds In 2026", "Apply now"],
        },
        routing={},
        warnings=[],
        confidence=0.93,
        validation_state="clean",
        template_analysis={
            "layout_type": "editorial_split",
            "editable_zones": [{"role": "headline"}, {"role": "illustration"}, {"role": "cta"}],
            "color_usage": [
                {"role": "primary", "hex_code": "#003975"},
                {"role": "secondary", "hex_code": "#FFA400"},
            ],
            "font_families": ["Manrope"],
            "structure_summary": "Layout editorial split. Palette: primary #003975, secondary #FFA400.",
            "summary": "Layout editorial split. Palette: primary #003975, secondary #FFA400.",
            "copy_lines": ["Why Investors Are Moving From FDs To Bonds In 2026", "Apply now"],
            "analysis_quality": {
                "analysis_quality_score": 8.4,
                "summary_quality_score": 7.8,
                "ocr_signal_score": 6.9,
                "ocr_noise_ratio": 0.1,
                "promotional_line_ratio": 0.2,
                "selected_line_count": 3,
                "candidate_line_count": 4,
                "evidence_types": ["layout", "palette", "zones"],
            },
        },
        template_tags=[],
        image_candidates=[],
        derived_assets=[],
        source_format="pdf",
    )

    documents = BrandAssetService._structured_retrieval_documents(asset, outcome)
    document_map = {item["metadata"]["document_type"]: item for item in documents}

    assert "structured_layout" in document_map
    assert "structured_template_copy" in document_map
    assert "Why Investors Are Moving From FDs To Bonds In 2026" not in document_map["structured_summary"]["content"]
    assert document_map["structured_template_copy"]["metadata"]["visual_grounding_allowed"] is False
