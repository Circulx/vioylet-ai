from __future__ import annotations

from typing import Any

from app.integrations.vector_store import get_vector_store_provider


class _FallbackTextSplitter:
    def __init__(self, *, chunk_size: int, chunk_overlap: int) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> list[str]:
        normalized = str(text or "").strip()
        if not normalized:
            return []
        chunks: list[str] = []
        start = 0
        while start < len(normalized):
            end = min(start + self.chunk_size, len(normalized))
            if end < len(normalized):
                boundary = max(
                    normalized.rfind("\n\n", start, end),
                    normalized.rfind("\n", start, end),
                    normalized.rfind(". ", start, end),
                    normalized.rfind(" ", start, end),
                )
                if boundary > start + max(self.chunk_size // 2, 1):
                    end = boundary + 1
            chunk = normalized[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(normalized):
                break
            start = max(end - self.chunk_overlap, start + 1)
        return chunks


def _build_text_splitter(chunk_size: int = 900, chunk_overlap: int = 120):
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        return RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    except Exception:  # noqa: BLE001 - optional ML dependencies can break package import
        return _FallbackTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)


class KnowledgeRetrievalService:
    def __init__(self) -> None:
        self.vector_store = get_vector_store_provider()
        self.splitter = _build_text_splitter(chunk_size=900, chunk_overlap=120)

    def index_documents(
        self,
        tenant_id: str,
        brand_space_id: str,
        channel: str,
        source_id: str,
        documents: list[dict[str, Any]],
    ) -> None:
        docs: list[dict[str, Any]] = []
        for index, document in enumerate(documents):
            if not isinstance(document, dict):
                continue
            content = str(document.get("content") or "").strip()
            if not content:
                continue
            incoming_metadata = dict(document.get("metadata") or {})
            document_type = str(incoming_metadata.get("document_type") or "raw_ocr").strip().lower() or "raw_ocr"
            docs.append(
                {
                    "content": content,
                    "metadata": {
                        "chunk_id": incoming_metadata.get("chunk_id") or f"{source_id}-{document_type}-{index}",
                        "source_id": source_id,
                        "channel": channel,
                        "document_type": document_type,
                        **incoming_metadata,
                    },
                }
            )
        if docs:
            namespace = self.vector_store.namespace(tenant_id, brand_space_id, channel)
            self.vector_store.upsert_documents(namespace, docs)

    def index_asset(
        self,
        tenant_id: str,
        brand_space_id: str,
        channel: str,
        source_id: str,
        text: str,
        metadata: dict[str, Any],
    ) -> None:
        chunks = self.splitter.split_text(text or "")
        docs = []
        for index, chunk in enumerate(chunks):
            docs.append(
                {
                    "content": chunk,
                    "metadata": {
                        "chunk_id": f"{source_id}-raw_ocr-{index}",
                        "document_type": "raw_ocr",
                        **metadata,
                    },
                }
            )
        self.index_documents(
            tenant_id=tenant_id,
            brand_space_id=brand_space_id,
            channel=channel,
            source_id=source_id,
            documents=docs,
        )

    def delete_asset(self, tenant_id: str, brand_space_id: str, channel: str, source_id: str) -> None:
        namespace = self.vector_store.namespace(tenant_id, brand_space_id, channel)
        self.vector_store.delete_source(namespace, source_id)

    def search(
        self,
        tenant_id: str,
        brand_space_id: str,
        channel: str,
        query: str,
        k: int = 4,
    ) -> list[dict[str, Any]]:
        namespace = self.vector_store.namespace(tenant_id, brand_space_id, channel)
        return [
            {"content": item.content, "score": item.score, "metadata": item.metadata}
            for item in self.vector_store.search(namespace, query, k=k)
        ]
