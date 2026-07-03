"""Layer 1 brand context retrieval service.

Runs namespace-isolated retrieval, multi-signal reranking, relevance-tier
classification, brand-isolation status, and produces a full retrieval log
plus a validated BrandContextOutput.
"""

from typing import Any

from app.core.logging import get_logger
from app.graph.models.layer1_models import BrandContextOutput, RetrievedChunk
from app.services.vectorstore.ingestion_service import IngestionService
from app.services.vectorstore.reranker import MultiSignalReranker, RankedChunk

logger = get_logger(__name__)

# Composite-score thresholds for relevance tiers.
HIGH_THRESHOLD = 0.60
MEDIUM_THRESHOLD = 0.40

# How many top chunks are marked used_in_output / count toward confidence.
USED_IN_OUTPUT_TOP_N = 8

_VALID_INFLUENCE_AREAS = {"strategy", "copy", "visual", "compliance", "audience"}


class BrandRetrievalService:
    """Production brand retrieval for Layer 1 of the Violyt pipeline."""

    def __init__(self) -> None:
        self._ingestion = IngestionService()
        self._reranker = MultiSignalReranker()

    def build_query(self, user_prompt: str, brand_id: str, platform: str, format: str) -> str:
        parts = [p for p in [user_prompt, platform, format] if p]
        return " ".join(parts).strip() or brand_id

    def retrieve(
        self,
        brand_id: str,
        user_prompt: str,
        platform: str = "",
        format: str = "",
        k: int = 20,
    ) -> dict[str, Any]:
        """Retrieve, rerank, and classify brand context.

        Returns a dict with:
            output:        BrandContextOutput (validated)
            retrieval_log: dict with per-chunk trace
            ranked_chunks: list of dicts including per-signal score breakdown + tier
        """
        namespace = f"brand:{brand_id}"
        query = self.build_query(user_prompt, brand_id, platform, format)
        logger.info(f"retrieval.start brand_id={brand_id} namespace={namespace} k={k}")

        raw_matches = self._query_namespace(brand_id, query, k)
        total = len(raw_matches)

        campaign_context = {"user_prompt": user_prompt, "platform": platform, "format": format}
        ranked = self._reranker.rerank(raw_matches, campaign_context)

        high, medium, low = self._classify(ranked)
        confidence = self._confidence(ranked)
        isolation_status = self._isolation_status(total, confidence)

        retrieved_sections = sorted({c.section for c in ranked if c.section})
        missing_context = self._missing_context(high, medium, ranked)

        output = BrandContextOutput(
            brand_id=brand_id,
            retrieved_sections=retrieved_sections,
            high_relevance_context=[self._to_model(c, True) for c in high],
            medium_relevance_context=[self._to_model(c, True) for c in medium],
            low_relevance_context=[self._to_model(c, False) for c in low],
            missing_context=missing_context,
            brand_isolation_status=isolation_status,
            retrieval_confidence=round(confidence, 4),
            retrieval_query=query,
            total_chunks_retrieved=total,
        )

        retrieval_log = self._build_log(brand_id, namespace, query, ranked)
        ranked_chunks = self._ranked_payload(ranked)

        logger.info(
            f"retrieval.complete brand_id={brand_id} total={total} "
            f"high={len(high)} medium={len(medium)} low={len(low)} "
            f"confidence={confidence:.3f} isolation={isolation_status}"
        )

        return {
            "output": output,
            "retrieval_log": retrieval_log,
            "ranked_chunks": ranked_chunks,
        }

    def _query_namespace(self, brand_id: str, query: str, k: int) -> list[dict[str, Any]]:
        index = self._ingestion.pinecone_index
        if not index:
            raise ValueError("Pinecone index not initialized")

        namespace = f"brand:{brand_id}"
        query_embedding = self._ingestion.generate_embedding(query)
        results = index.query(
            vector=query_embedding,
            namespace=namespace,  # HARD isolation — only this brand's vectors
            top_k=k,
            include_metadata=True,
        )

        chunks: list[dict[str, Any]] = []
        for match in results.matches:
            meta = match.metadata or {}
            area = meta.get("influence_area", "strategy")
            if area not in _VALID_INFLUENCE_AREAS:
                area = "strategy"
            chunks.append(
                {
                    "chunk_id": match.id,
                    "source": meta.get("category", "brand_document"),
                    "section": meta.get("section", "Unknown"),
                    "content": meta.get("content", ""),
                    "content_summary": meta.get("content_summary", "") or meta.get("content", "")[:160],
                    "influence_area": area,
                    "base_score": float(match.score or 0.0),
                }
            )
        return chunks

    def _classify(self, ranked: list[RankedChunk]) -> tuple[list, list, list]:
        high, medium, low = [], [], []
        for c in ranked:
            if c.composite_score >= HIGH_THRESHOLD:
                high.append(c)
            elif c.composite_score >= MEDIUM_THRESHOLD:
                medium.append(c)
            else:
                low.append(c)
        return high, medium, low

    def _confidence(self, ranked: list[RankedChunk]) -> float:
        if not ranked:
            return 0.0
        top = ranked[:USED_IN_OUTPUT_TOP_N]
        return sum(c.composite_score for c in top) / len(top)

    def _isolation_status(self, total: int, confidence: float) -> str:
        if total == 0:
            return "fail"
        if confidence < MEDIUM_THRESHOLD:
            return "warning"
        return "pass"

    def _missing_context(self, high: list, medium: list, ranked: list[RankedChunk]) -> list[str]:
        present_areas = {c.influence_area for c in (high + medium)}
        expected = {"strategy", "copy", "visual", "compliance", "audience"}
        missing = [area for area in sorted(expected - present_areas)]
        if not ranked:
            missing.append("no_brand_data_indexed")
        return missing

    def _to_model(self, c: RankedChunk, used: bool) -> RetrievedChunk:
        return RetrievedChunk(
            chunk_id=c.chunk_id,
            source=c.source,
            section=c.section,
            content_summary=c.content_summary or c.content[:160],
            relevance_score=c.composite_score,
            used_in_output=used,
            influence_area=c.influence_area,
        )

    def _build_log(self, brand_id: str, namespace: str, query: str, ranked: list[RankedChunk]) -> dict[str, Any]:
        return {
            "brand_id": brand_id,
            "namespace": namespace,
            "query": query,
            "total_chunks": len(ranked),
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "source": c.source,
                    "section": c.section,
                    "relevance_score": c.composite_score,
                    "influence_area": c.influence_area,
                    "used_in_output": idx < USED_IN_OUTPUT_TOP_N,
                }
                for idx, c in enumerate(ranked)
            ],
        }

    def _ranked_payload(self, ranked: list[RankedChunk]) -> list[dict[str, Any]]:
        payload = []
        for idx, c in enumerate(ranked):
            if c.composite_score >= HIGH_THRESHOLD:
                tier = "high"
            elif c.composite_score >= MEDIUM_THRESHOLD:
                tier = "medium"
            else:
                tier = "low"
            row = c.as_dict()
            row["tier"] = tier
            row["used_in_output"] = idx < USED_IN_OUTPUT_TOP_N
            payload.append(row)
        return payload
