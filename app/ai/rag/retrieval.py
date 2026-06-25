from __future__ import annotations

from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.integrations.vector_store import FaissVectorStoreProvider


class KnowledgeRetrievalService:
    # Groups knowledge retrieval service behavior for knowledge retrieval.
    # Callers use this class to produce or evaluate data consumed by compiled context grounding.
    def __init__(self) -> None:
        # Initializes settings, clients, and helper services needed by compiled context grounding.
        # Public methods reuse these collaborators instead of rebuilding them for each request.
        self.vector_store = FaissVectorStoreProvider()
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=120)

    def index_documents(
        self,
        tenant_id: str,
        brand_space_id: str,
        channel: str,
        source_id: str,
        documents: list[dict[str, Any]],
    ) -> None:
        # Centralizes index documents from tenant id, brand space id, and channel for compiled context grounding.
        # The helper owns a small rule that would distract from the surrounding flow.
        docs: list[dict[str, Any]] = []
        for index, document in enumerate(documents):
            if not isinstance(document, dict):
                continue
            content = str(document.get("content") or "").strip()
            if not content:
                continue
            incoming_metadata = dict(document.get("metadata") or {})
            document_type = str(incoming_metadata.get("document_type") or "raw_ocr").strip().lower() or "raw_ocr"
            # Chunk metadata keeps the source/channel identity attached after FAISS search returns a match.
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
        # Extracts index asset from tenant id, brand space id, and channel for compiled context grounding.
        # The extracted signal becomes prompt context, metadata, or ranking input.
        chunks = self.splitter.split_text(text or "")
        docs = []
        for index, chunk in enumerate(chunks):
            # Raw OCR is indexed through the same document path so ranking sees one consistent metadata shape.
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
        # Extracts delete asset from tenant id, brand space id, and channel for compiled context grounding.
        # Later planning can reuse the structured value instead of scanning the source again.
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
        # Centralizes search from tenant id, brand space id, and channel for compiled context grounding.
        # The main branch stays readable while this function handles the local edge case.
        namespace = self.vector_store.namespace(tenant_id, brand_space_id, channel)
        # Callers receive plain dictionaries so context compilation stays decoupled from the vector-store classes.
        return [
            {"content": item.content, "score": item.score, "metadata": item.metadata}
            for item in self.vector_store.search(namespace, query, k=k)
        ]
