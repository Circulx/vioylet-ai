from pydantic import BaseModel, Field
from typing import List, Literal


class RetrievedChunk(BaseModel):
    chunk_id: str
    source: str
    section: str
    content_summary: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    used_in_output: bool
    influence_area: Literal["strategy", "copy", "visual", "compliance", "audience"]


class BrandContextOutput(BaseModel):
    brand_id: str
    retrieved_sections: List[str]
    high_relevance_context: List[RetrievedChunk]
    medium_relevance_context: List[RetrievedChunk]
    low_relevance_context: List[RetrievedChunk]
    missing_context: List[str]
    brand_isolation_status: Literal["pass", "warning", "fail"]
    retrieval_confidence: float = Field(ge=0.0, le=1.0)
    retrieval_query: str
    total_chunks_retrieved: int
