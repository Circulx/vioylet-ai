from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

import numpy as np
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

from app.core.config import get_settings


@dataclass(slots=True)
class SearchResult:
    content: str
    score: float
    metadata: dict[str, Any]


class HashEmbeddings:
    def __init__(self, dimensions: int = 256) -> None:
        self.dimensions = dimensions

    def _embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = list(digest) * ((self.dimensions // len(digest)) + 1)
        arr = np.array(values[: self.dimensions], dtype=np.float32)
        norm = np.linalg.norm(arr) or 1.0
        return (arr / norm).tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class VectorStoreProvider(Protocol):
    def upsert_documents(self, namespace: str, docs: list[dict[str, Any]]) -> None: ...
    def delete_source(self, namespace: str, source_id: str) -> None: ...
    def search(self, namespace: str, query: str, k: int = 4) -> list[SearchResult]: ...
    def namespace(self, tenant_id: str, brand_space_id: str, channel: str) -> str: ...


def _build_embeddings() -> OpenAIEmbeddings | HashEmbeddings:
    settings = get_settings()
    return (
        OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.openai_api_key)
        if settings.openai_api_key
        else HashEmbeddings()
    )


def _jsonb(value: dict[str, Any]) -> Any:
    try:
        from psycopg.types.json import Jsonb
    except ImportError:
        return json.dumps(value)
    return Jsonb(value)


class FaissVectorStoreProvider:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_path = Path(settings.vector_store_base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._embeddings = _build_embeddings()

    def _namespace_path(self, namespace: str) -> Path:
        path = self.base_path / namespace.replace("/", "__")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _metadata_path(self, namespace: str) -> Path:
        return self._namespace_path(namespace) / "documents.json"

    def _load_documents(self, namespace: str) -> list[dict[str, Any]]:
        metadata_path = self._metadata_path(namespace)
        if metadata_path.exists():
            return json.loads(metadata_path.read_text(encoding="utf-8"))
        return []

    def _save_documents(self, namespace: str, docs: list[dict[str, Any]]) -> None:
        self._metadata_path(namespace).write_text(json.dumps(docs, indent=2), encoding="utf-8")

    def _rebuild_index(self, namespace: str, docs: list[dict[str, Any]]) -> None:
        namespace_path = self._namespace_path(namespace)
        if not docs:
            for child in namespace_path.iterdir():
                if child.is_file():
                    child.unlink()
            self._save_documents(namespace, [])
            return
        texts = [doc["content"] for doc in docs]
        metadatas = [doc["metadata"] for doc in docs]
        index = FAISS.from_texts(texts=texts, embedding=self._embeddings, metadatas=metadatas)
        index.save_local(str(namespace_path))
        self._save_documents(namespace, docs)

    def upsert_documents(self, namespace: str, docs: list[dict[str, Any]]) -> None:
        stored = self._load_documents(namespace)
        existing_by_id = {doc["metadata"]["chunk_id"]: doc for doc in stored if "chunk_id" in doc["metadata"]}
        incoming_ids = [
            doc["metadata"]["chunk_id"]
            for doc in docs
            if "chunk_id" in doc.get("metadata", {})
        ]
        namespace_path = self._namespace_path(namespace)
        index_file = namespace_path / "index.faiss"
        can_append_incrementally = bool(incoming_ids) and all(chunk_id not in existing_by_id for chunk_id in incoming_ids)
        if can_append_incrementally and index_file.exists():
            vectorstore = FAISS.load_local(
                str(namespace_path),
                self._embeddings,
                allow_dangerous_deserialization=True,
            )
            texts = [doc["content"] for doc in docs]
            metadatas = [doc["metadata"] for doc in docs]
            if hasattr(self._embeddings, "embed_documents"):
                vectorstore.add_embeddings(
                    text_embeddings=list(zip(texts, self._embeddings.embed_documents(texts), strict=False)),
                    metadatas=metadatas,
                )
            else:
                vectorstore.add_texts(
                    texts=texts,
                    metadatas=metadatas,
                )
            vectorstore.save_local(str(namespace_path))
            stored.extend(docs)
            self._save_documents(namespace, stored)
            return
        for doc in docs:
            existing_by_id[doc["metadata"]["chunk_id"]] = doc
        self._rebuild_index(namespace, list(existing_by_id.values()))

    def delete_source(self, namespace: str, source_id: str) -> None:
        docs = [doc for doc in self._load_documents(namespace) if doc["metadata"].get("source_id") != source_id]
        self._rebuild_index(namespace, docs)

    def search(self, namespace: str, query: str, k: int = 4) -> list[SearchResult]:
        namespace_path = self._namespace_path(namespace)
        index_file = namespace_path / "index.faiss"
        if not index_file.exists():
            return []
        vectorstore = FAISS.load_local(
            str(namespace_path),
            self._embeddings,
            allow_dangerous_deserialization=True,
        )
        results = vectorstore.similarity_search_with_score(query, k=k)
        return [
            SearchResult(content=doc.page_content, score=float(score), metadata=doc.metadata)
            for doc, score in results
        ]

    def namespace(self, tenant_id: str, brand_space_id: str, channel: str) -> str:
        return f"{tenant_id}/{brand_space_id}/{channel}"


class PgVectorStoreProvider:
    table_name = "retrieval_vector_documents"

    def __init__(
        self,
        *,
        connection_factory: Callable[[], Any] | None = None,
        embeddings: Any | None = None,
    ) -> None:
        self.settings = get_settings()
        self._connection_factory = connection_factory or self._connect
        self._embeddings = embeddings or _build_embeddings()
        self._ensure_schema()

    def _database_url(self) -> str:
        url = str(self.settings.alembic_database_url or self.settings.database_url)
        return (
            url.replace("postgresql+psycopg://", "postgresql://", 1)
            .replace("postgresql+asyncpg://", "postgresql://", 1)
            .replace("postgres+asyncpg://", "postgresql://", 1)
        )

    def _connect(self):
        import psycopg

        return psycopg.connect(self._database_url())

    @staticmethod
    def _vector_literal(values: list[float]) -> str:
        return "[" + ",".join(repr(float(value)) for value in values) + "]"

    def _execute_schema(self, cursor: Any) -> None:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                namespace TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                embedding vector NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (namespace, chunk_id)
            )
            """
        )
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS ix_{self.table_name}_namespace ON {self.table_name} (namespace)"
        )
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS ix_{self.table_name}_source ON {self.table_name} (namespace, source_id)"
        )

    def _ensure_schema(self) -> None:
        try:
            with self._connection_factory() as connection:
                with connection.cursor() as cursor:
                    self._execute_schema(cursor)
                connection.commit()
        except Exception as exc:  # noqa: BLE001 - psycopg exposes provider-specific errors
            raise RuntimeError(
                "pgvector vector store is unavailable. Ensure Postgres has the pgvector extension "
                "and VECTOR_STORE_PROVIDER is set correctly."
            ) from exc

    def upsert_documents(self, namespace: str, docs: list[dict[str, Any]]) -> None:
        prepared_docs = [
            doc
            for doc in docs
            if str((doc.get("metadata") or {}).get("chunk_id") or "").strip()
            and str(doc.get("content") or "").strip()
        ]
        if not prepared_docs:
            return
        texts = [str(doc["content"]) for doc in prepared_docs]
        vectors = self._embeddings.embed_documents(texts)
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                for doc, vector in zip(prepared_docs, vectors, strict=False):
                    metadata = dict(doc.get("metadata") or {})
                    chunk_id = str(metadata["chunk_id"])
                    source_id = str(metadata.get("source_id") or "")
                    cursor.execute(
                        f"""
                        INSERT INTO {self.table_name}
                            (namespace, chunk_id, source_id, content, metadata, embedding, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s::vector, NOW())
                        ON CONFLICT (namespace, chunk_id) DO UPDATE SET
                            source_id = EXCLUDED.source_id,
                            content = EXCLUDED.content,
                            metadata = EXCLUDED.metadata,
                            embedding = EXCLUDED.embedding,
                            updated_at = NOW()
                        """,
                        (
                            namespace,
                            chunk_id,
                            source_id,
                            str(doc["content"]),
                            _jsonb(metadata),
                            self._vector_literal(vector),
                        ),
                    )
            connection.commit()

    def delete_source(self, namespace: str, source_id: str) -> None:
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"DELETE FROM {self.table_name} WHERE namespace = %s AND source_id = %s",
                    (namespace, source_id),
                )
            connection.commit()

    def search(self, namespace: str, query: str, k: int = 4) -> list[SearchResult]:
        query_vector = self._vector_literal(self._embeddings.embed_query(query or ""))
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT content, metadata, embedding <=> %s::vector AS score
                    FROM {self.table_name}
                    WHERE namespace = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (query_vector, namespace, query_vector, int(k)),
                )
                rows = cursor.fetchall()
        return [
            SearchResult(content=str(row[0]), score=float(row[2]), metadata=dict(row[1] or {}))
            for row in rows
        ]

    def namespace(self, tenant_id: str, brand_space_id: str, channel: str) -> str:
        return f"{tenant_id}/{brand_space_id}/{channel}"


def get_vector_store_provider() -> VectorStoreProvider:
    provider = str(get_settings().vector_store_provider or "faiss").strip().lower()
    if provider == "pgvector":
        return PgVectorStoreProvider()
    return FaissVectorStoreProvider()
