"""Document ingestion service for brand guideline processing."""

import json
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

import docx
import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Controlled category values based on brand sections
CONTROLLED_CATEGORIES = [
    "identity",
    "foundations",
    "voice_tone",
    "personas",
    "guardrails",
    "knowledge",
    "objectives",
    "visual_identity",
    "prompt_intelligence",
    "review",
]

# Controlled influence area values
CONTROLLED_INFLUENCE_AREAS = [
    "strategy",
    "copy",
    "visual",
    "compliance",
    "audience",
]

# Maps backend section_code → brand space tab layer label
# Used as metadata in Pinecone so retrieval can filter by tab/layer
SECTION_TO_BRAND_TAB: dict[str, str] = {
    "identity": "identity_layer",
    "foundations": "strategic_layer",
    "voice_tone": "tone_layer",
    "personas": "persona_layer",
    "guardrails": "guardrail_layer",
    "knowledge": "learning_layer",
    "prompt_intelligence": "instruction_layer",
    "objectives": "objective_layer",
    "visual_identity": "visual_layer",
    "review": "review_layer",
}

# Default influence area for each brand-space category. Lets the UI upload path
# tag chunks deterministically by their tab without an extra LLM call per chunk.
CATEGORY_TO_INFLUENCE: dict[str, str] = {
    "identity": "strategy",
    "foundations": "strategy",
    "voice_tone": "copy",
    "personas": "audience",
    "guardrails": "compliance",
    "knowledge": "strategy",
    "objectives": "strategy",
    "visual_identity": "visual",
    "prompt_intelligence": "strategy",
    "review": "strategy",
}


def normalize_category(value: str | None) -> str:
    """Coerce an arbitrary field_key/channel/category into a controlled category."""
    normalized = str(value or "").strip().lower()
    if normalized in CONTROLLED_CATEGORIES:
        return normalized
    # Common aliases coming from brand-space tabs / asset channels.
    aliases = {
        "brand": "knowledge",
        "brand_summary": "knowledge",
        "tone": "voice_tone",
        "voice": "voice_tone",
        "strategy": "foundations",
        "audience": "personas",
        "persona": "personas",
        "compliance": "guardrails",
        "rules": "guardrails",
        "visual": "visual_identity",
        "visuals": "visual_identity",
        "objective": "objectives",
    }
    return aliases.get(normalized, "knowledge")


class IngestionService:
    """Service for ingesting brand guideline documents into Pinecone."""

    def __init__(self):
        self.settings = get_settings()
        self.openai_client = None
        self.pinecone_client = None
        self.pinecone_index = None

        # Initialize OpenAI client if API key is available
        if self.settings.openai_api_key:
            self.openai_client = OpenAI(api_key=self.settings.openai_api_key)

        # Initialize Pinecone client if API key is available
        if self.settings.pinecone_api_key:
            self.pinecone_client = Pinecone(api_key=self.settings.pinecone_api_key)
            try:
                self.pinecone_index = self.pinecone_client.Index(self.settings.pinecone_index_name)
            except Exception as e:
                logger.error(f"Failed to initialize Pinecone index: {e}")

        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.settings.ingestion_chunk_size,
            chunk_overlap=self.settings.ingestion_chunk_overlap,
            length_function=len,
        )

    def parse_document(self, file_path: str) -> str:
        """Extract text from DOCX, PDF, or TXT file.

        Args:
            file_path: Path to the document file

        Returns:
            Extracted text as string
        """
        path = Path(file_path)
        extension = path.suffix.lower()

        if extension == ".docx":
            return self._parse_docx(file_path)
        elif extension == ".pdf":
            return self._parse_pdf(file_path)
        elif extension == ".txt":
            return self._parse_txt(file_path)
        else:
            raise ValueError(f"Unsupported file type: {extension}")

    def _parse_docx(self, file_path: str) -> str:
        """Extract text from DOCX file preserving heading structure."""
        doc = docx.Document(file_path)
        text_parts = []

        for paragraph in doc.paragraphs:
            if paragraph.style.name.startswith("Heading"):
                # Add heading with marker
                text_parts.append(f"\n## {paragraph.text}\n")
            else:
                text_parts.append(paragraph.text)

        return "\n".join(text_parts)

    def _parse_pdf(self, file_path: str) -> str:
        """Extract text from PDF file page by page."""
        text_parts = []

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        return "\n\n".join(text_parts)

    def _parse_txt(self, file_path: str) -> str:
        """Extract text from TXT file with encoding detection."""
        # Try common encodings
        encodings = ["utf-8", "latin-1", "cp1252"]

        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue

        # Fallback to binary read with error handling
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def chunk_text(self, text: str) -> list[str]:
        """Split text into chunks of specified size.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        chunks = self.text_splitter.split_text(text)
        return chunks

    def classify_chunk(self, chunk: str) -> dict[str, Any]:
        """Classify a text chunk using LLM.

        Args:
            chunk: Text chunk to classify

        Returns:
            Dictionary with category, section, influence_area, and content_summary
        """
        if not self.openai_client:
            # Fallback to defaults if no LLM available
            return {
                "category": "general",
                "section": "Unknown",
                "influence_area": "strategy",
                "content_summary": chunk[:80] + "..." if len(chunk) > 80 else chunk,
            }

        categories_str = ", ".join(CONTROLLED_CATEGORIES)
        influence_areas_str = ", ".join(CONTROLLED_INFLUENCE_AREAS)

        prompt = f"""Classify the following brand guideline text chunk.

Available categories: {categories_str}
Available influence areas: {influence_areas_str}

Text chunk:
{chunk}

Return a JSON object with:
- category: one of the available categories
- section: a brief section name (e.g., "Color Palette", "Tone Guidelines")
- influence_area: one of the available influence areas
- content_summary: a brief 1-2 sentence summary of the content

Return only the JSON, no other text."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a brand guideline classifier. Return only valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            result_text = response.choices[0].message.content.strip()

            # Strip markdown code fences if present
            if result_text.startswith("```"):
                result_text = result_text.split("```", 2)[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            parsed = json.loads(result_text)

            # Handle cases where the model returns a list instead of an object
            if isinstance(parsed, list):
                parsed = parsed[0] if parsed and isinstance(parsed[0], dict) else {}

            result = {
                "category": parsed.get("category", "general"),
                "section": parsed.get("section", "Unknown"),
                "influence_area": parsed.get("influence_area", "strategy"),
                "content_summary": parsed.get("content_summary", ""),
            }

            # Validate category and influence_area
            if result.get("category") not in CONTROLLED_CATEGORIES:
                result["category"] = "general"
            if result.get("influence_area") not in CONTROLLED_INFLUENCE_AREAS:
                result["influence_area"] = "strategy"

            return result

        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            return {
                "category": "general",
                "section": "Unknown",
                "influence_area": "strategy",
                "content_summary": chunk[:80] + "..." if len(chunk) > 80 else chunk,
            }

    def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for text using OpenAI.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")

        try:
            logger.info(f"Using embedding model: {self.settings.ingestion_embedding_model}")
            response = self.openai_client.embeddings.create(
                model=self.settings.ingestion_embedding_model,
                input=text,
                dimensions=self.settings.ingestion_embedding_dimensions,
            )
            logger.info(f"Embedding dimension: {len(response.data[0].embedding)}")
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    def upsert_to_pinecone(
        self,
        brand_id: str,
        chunks: list[dict[str, Any]],
        *,
        doc_id: str | None = None,
    ) -> int:
        """Upsert chunks to Pinecone under brand namespace.

        Args:
            brand_id: Brand ID for namespace isolation
            chunks: List of chunk dictionaries with content and metadata
            doc_id: Stable per-document/asset id used to build unique vector ids.
                Prevents one document's chunks from overwriting another's. When not
                provided a random id is generated so ad-hoc ingests never collide.

        Returns:
            Number of vectors successfully upserted.
        """
        if not self.pinecone_index:
            raise ValueError("Pinecone index not initialized")

        namespace = f"brand:{brand_id}"
        source_id = str(doc_id or uuid4())
        vectors = []

        for i, chunk in enumerate(chunks):
            try:
                embedding = self.generate_embedding(chunk["content"])
                category = chunk.get("category", "general")
                brand_tab = SECTION_TO_BRAND_TAB.get(category, category)
                vectors.append(
                    {
                        "id": f"{brand_id}:{source_id}:{i}",
                        "values": embedding,
                        "metadata": {
                            "content": chunk["content"],
                            "category": category,
                            "brand_tab": brand_tab,
                            "section": chunk.get("section", "Unknown"),
                            "influence_area": chunk.get("influence_area", "strategy"),
                            "content_summary": chunk.get("content_summary", ""),
                            "asset_id": source_id,
                            "filename": chunk.get("filename", ""),
                        },
                    }
                )
            except Exception as e:
                logger.error(f"Failed to generate embedding for chunk {i}: {e}")
                continue

        upserted = 0
        # Pinecone caps upsert batch sizes, so send in chunks of 100.
        for start in range(0, len(vectors), 100):
            batch = vectors[start : start + 100]
            try:
                self.pinecone_index.upsert(vectors=batch, namespace=namespace)
                upserted += len(batch)
            except Exception as e:
                logger.error(f"Pinecone upsert failed: {e}")
                raise
        if upserted:
            logger.info(f"Upserted {upserted} chunks to Pinecone namespace: {namespace}")
        return upserted

    def delete_asset_vectors(self, brand_id: str, asset_id: str) -> None:
        """Delete all Pinecone vectors previously ingested for a knowledge asset.

        Called before re-ingesting so reprocessing/edits never leave stale chunks.
        Uses a metadata filter on asset_id, which is set by ingest_asset_text.
        """
        if not self.pinecone_index:
            return
        namespace = f"brand:{brand_id}"
        try:
            self.pinecone_index.delete(filter={"asset_id": str(asset_id)}, namespace=namespace)
            logger.info(f"Deleted vectors for asset {asset_id} in namespace {namespace}")
        except Exception as e:  # noqa: BLE001
            # Serverless indexes may not support delete-by-filter; log and continue
            # since re-upsert uses deterministic ids that overwrite the same chunks.
            logger.warning(f"delete_asset_vectors skipped for asset {asset_id}: {e}")

    def ingest_asset_text(
        self,
        brand_id: str,
        asset_id: str,
        text: str,
        *,
        category: str,
        filename: str = "",
        section: str = "Uploaded Document",
    ) -> dict[str, Any]:
        """Ingest already-extracted text for a brand-space knowledge asset.

        This is the single entry point used by the Brand Space UI upload pipeline:
        the asset's brand-space tab decides the category metadata, the text is
        chunked, embedded, and upserted to the brand's Pinecone namespace with that
        category so Layer 1 retrieval can filter/align by tab.
        """
        if not self.pinecone_index or not self.openai_client:
            logger.warning(
                "ingest_asset_text skipped: pinecone/openai not configured "
                f"(brand_id={brand_id}, asset_id={asset_id})"
            )
            return {"brand_id": brand_id, "asset_id": asset_id, "total_chunks": 0}

        logger.info(f"ingest_asset_text.start brand_id={brand_id} asset_id={asset_id} category={category} text_length={len(text)}")

        normalized = normalize_category(category)
        influence_area = CATEGORY_TO_INFLUENCE.get(normalized, "strategy")

        logger.info(f"ingest_asset_text.chunking brand_id={brand_id} asset_id={asset_id}")
        chunks = self.chunk_text(text or "")
        logger.info(f"ingest_asset_text.chunked brand_id={brand_id} asset_id={asset_id} chunks={len(chunks)}")

        classified_chunks = [
            {
                "content": chunk,
                "category": normalized,
                "section": section,
                "influence_area": influence_area,
                "content_summary": (chunk[:157] + "...") if len(chunk) > 160 else chunk,
                "filename": filename,
            }
            for chunk in chunks
            if chunk.strip()
        ]
        logger.info(f"ingest_asset_text.classified brand_id={brand_id} asset_id={asset_id} classified={len(classified_chunks)}")

        # Remove any prior vectors for this asset so edits don't leave stale chunks.
        logger.info(f"ingest_asset_text.deleting_old brand_id={brand_id} asset_id={asset_id}")
        self.delete_asset_vectors(brand_id, asset_id)
        logger.info(f"ingest_asset_text.upserting brand_id={brand_id} asset_id={asset_id}")
        upserted = self.upsert_to_pinecone(brand_id, classified_chunks, doc_id=asset_id)
        logger.info(f"ingest_asset_text.upserted brand_id={brand_id} asset_id={asset_id} upserted={upserted}")

        return {
            "brand_id": brand_id,
            "asset_id": asset_id,
            "category": normalized,
            "total_chunks": upserted,
        }

    def process_document(self, brand_id: str, file_path: str) -> dict[str, Any]:
        """Process a document end-to-end: parse, chunk, classify, embed, and upsert.

        Args:
            brand_id: Brand ID for namespace isolation
            file_path: Path to the document file

        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing document: {file_path} for brand: {brand_id}")

        # Step 1: Parse document
        text = self.parse_document(file_path)
        logger.info(f"Extracted {len(text)} characters from document")

        # Step 2: Chunk text
        chunks = self.chunk_text(text)
        logger.info(f"Split into {len(chunks)} chunks")

        # Step 3: Classify each chunk
        classified_chunks = []
        for chunk in chunks:
            classification = self.classify_chunk(chunk)
            classified_chunks.append(
                {
                    "content": chunk,
                    "category": classification["category"],
                    "section": classification["section"],
                    "influence_area": classification["influence_area"],
                    "content_summary": classification["content_summary"],
                }
            )

        # Step 4: Upsert to Pinecone. Use the file path as a stable doc id so
        # re-ingesting the same file overwrites its own chunks instead of others'.
        doc_id = uuid5(NAMESPACE_URL, f"{brand_id}:{Path(file_path).name}").hex
        self.upsert_to_pinecone(brand_id, classified_chunks, doc_id=doc_id)

        return {
            "brand_id": brand_id,
            "file_path": file_path,
            "total_chunks": len(chunks),
            "categories": {c["category"] for c in classified_chunks},
            "influence_areas": {c["influence_area"] for c in classified_chunks},
        }

    def search_pinecone(self, brand_id: str, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """Search Pinecone for relevant chunks.

        Args:
            brand_id: Brand ID for namespace isolation
            query: Search query
            top_k: Number of results to return

        Returns:
            List of matching chunks with metadata and scores
        """
        if not self.pinecone_index:
            raise ValueError("Pinecone index not initialized")

        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")

        namespace = f"brand:{brand_id}"

        # Generate query embedding
        query_embedding = self.generate_embedding(query)

        # Search Pinecone
        results = self.pinecone_index.query(
            vector=query_embedding,
            namespace=namespace,
            top_k=top_k,
            include_metadata=True,
        )

        # Format results
        formatted_results = []
        for match in results.matches:
            formatted_results.append(
                {
                    "content": match.metadata.get("content", ""),
                    "category": match.metadata.get("category", "general"),
                    "section": match.metadata.get("section", "Unknown"),
                    "influence_area": match.metadata.get("influence_area", "strategy"),
                    "content_summary": match.metadata.get("content_summary", ""),
                    "score": match.score,
                }
            )

        return formatted_results
