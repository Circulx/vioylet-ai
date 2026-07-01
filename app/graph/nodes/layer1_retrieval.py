from app.graph.state import ViolytState
from app.graph.models.layer1_models import BrandContextOutput, RetrievedChunk


async def layer1_retrieval(state: ViolytState) -> dict:
    brand_id = state.get("brand_id", "unknown")
    query = f"brand:{brand_id} {state.get('user_prompt', '')}".strip()

    return {
        "brand_context": BrandContextOutput(
            brand_id=brand_id,
            retrieved_sections=["brand_positioning", "tone_of_voice", "visual_identity"],
            high_relevance_context=[
                RetrievedChunk(
                    chunk_id="chunk-001",
                    source="brand_guidelines.pdf",
                    section="brand_positioning",
                    content_summary="Brand stands for calm, credible financial maturity.",
                    relevance_score=0.92,
                    used_in_output=True,
                    influence_area="strategy",
                ),
            ],
            medium_relevance_context=[
                RetrievedChunk(
                    chunk_id="chunk-002",
                    source="brand_voice.md",
                    section="tone_of_voice",
                    content_summary="Authoritative but accessible language.",
                    relevance_score=0.68,
                    used_in_output=True,
                    influence_area="copy",
                ),
            ],
            low_relevance_context=[],
            missing_context=[],
            brand_isolation_status="pass",
            retrieval_confidence=0.88,
            retrieval_query=query,
            total_chunks_retrieved=2,
        )
    }
