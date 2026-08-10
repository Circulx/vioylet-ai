from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.llm.openai_service import OpenAIService
from app.services.vectorstore.ingestion_service import IngestionService

logger = get_logger(__name__)


class BrandAutofillSuggestion(BaseModel):
    """Flat suggestion payload mapped onto BrandFormState on the frontend."""

    brand_name: str = ""
    brand_tagline: str = ""
    brand_description: str = ""
    industry_category: str = ""
    differentiators: str = ""
    core_tone_attributes: list[str] = Field(default_factory=list)
    primary_emotion: str = ""
    secondary_emotion: str = ""
    avoided_emotion: str = ""
    content_complexity: str = ""
    sentence_length: str = ""
    perspective: str = ""
    selected_audiences: list[str] = Field(default_factory=list)
    audience_goals: str = ""
    audience_motivations: str = ""
    audience_fears: str = ""
    audience_objections: str = ""
    logo_placements: list[str] = Field(default_factory=list)
    primary_color: str = ""
    secondary_color: str = ""
    typography: str = ""
    brand_mood: str = ""
    visual_style: str = ""
    selected_rules: list[str] = Field(default_factory=list)
    positive_word_bank: str = ""
    restricted_topics: str = ""
    restricted_claims: str = ""
    blocked_words_phrases: str = ""
    brand_mission: str = ""
    brand_vision: str = ""
    brand_promise: str = ""
    market_positioning: str = ""
    sources_used: int = 0
    notes: list[str] = Field(default_factory=list)


class BrandAutofillService:
    """Pull brand knowledge from the vector DB and suggest publish-ready form values."""

    def __init__(self) -> None:
        settings = get_settings()
        self._ingestion = IngestionService()
        self._llm = OpenAIService(model=settings.llm_model or "gpt-4o-mini")

    def _gather_context(self, brand_id: str, brand_name: str) -> list[str]:
        queries = [
            f"{brand_name} brand identity mission vision positioning industry",
            f"{brand_name} tone of voice personality language style",
            f"{brand_name} target audience persona customer",
            f"{brand_name} visual identity colors typography logo",
            f"{brand_name} brand rules compliance claims restricted words",
        ]
        seen: set[str] = set()
        chunks: list[str] = []
        for query in queries:
            try:
                hits = self._ingestion.search_pinecone(brand_id, query, top_k=6) or []
            except Exception as exc:
                logger.warning("brand_autofill.search_failed", brand_id=brand_id, error=str(exc))
                continue
            for hit in hits:
                text = str(hit.get("content") or hit.get("text") or hit.get("chunk") or "").strip()
                if not text:
                    meta = hit.get("metadata") or {}
                    text = str(meta.get("content") or meta.get("text") or "").strip()
                if not text:
                    continue
                key = text[:160].lower()
                if key in seen:
                    continue
                seen.add(key)
                chunks.append(text[:1200])
                if len(chunks) >= 18:
                    return chunks
        return chunks

    async def suggest(self, brand_id: UUID, brand_name: str, brand_description: str = "") -> BrandAutofillSuggestion:
        chunks = self._gather_context(str(brand_id), brand_name or "brand")
        if not chunks:
            raise ValueError(
                "No knowledge found in the vector DB for this Brand Space. "
                "Upload brand documents first, wait for indexing, then try again."
            )

        context_block = "\n\n---\n\n".join(chunks)
        system = """You are Violyt Brand Autofill. Extract a structured Brand Space profile from retrieved brand knowledge.
Return ONLY a JSON object matching the schema. Infer sensible marketing defaults when a detail is implied but not explicit.
Rules:
- Prefer facts from the documents over generic marketing fluff.
- core_tone_attributes: 3-6 short adjectives (e.g. Professional, Trustworthy, Approachable).
- brand_tagline: the official or best-supported tagline if one appears in the documents; otherwise leave blank.
- selected_audiences: 1-4 short audience labels (e.g. Retail Investors, HNIs, CXOs).
- logo_placements: choose from Top-left, Top-right, Bottom-left, Bottom-right, Center (pick 1-2).
- selected_rules: 2-5 short rule labels the brand should follow.
- primary_color / secondary_color: hex codes if known, else brand-appropriate hexes (#RRGGBB).
- typography: short style description (e.g. Modern sans-serif, Clean geometric).
- positive_word_bank / restricted_* / blocked_words_phrases: comma-separated or newline lists as plain strings.
- Do not invent fake legal/compliance claims; if unknown use cautious defaults.
"""
        user = f"""Brand name hint: {brand_name}
Brand description hint: {brand_description}

RETRIEVED BRAND KNOWLEDGE:
{context_block}

Fill BrandAutofillSuggestion JSON now."""

        suggestion, _meta = await self._llm.complete_structured(
            system=system,
            user=user,
            output_model=BrandAutofillSuggestion,
            layer="brand_autofill",
            max_tokens=4096,
        )
        suggestion.sources_used = len(chunks)
        if not suggestion.brand_name:
            suggestion.brand_name = brand_name
        if not suggestion.logo_placements:
            suggestion.logo_placements = ["Top-right"]
        if not suggestion.core_tone_attributes:
            suggestion.core_tone_attributes = ["Professional", "Clear", "Trustworthy"]
        if not suggestion.selected_audiences:
            suggestion.selected_audiences = ["Primary customers"]
        if len(suggestion.primary_color) < 4:
            suggestion.primary_color = "#121212"
        if len(suggestion.secondary_color) < 4:
            suggestion.secondary_color = "#4F46E5"
        if not suggestion.typography:
            suggestion.typography = "Modern sans-serif"
        if not suggestion.selected_rules:
            suggestion.selected_rules = ["Stay on-brand", "No unverified claims", "Clear CTAs"]
        if not suggestion.positive_word_bank:
            suggestion.positive_word_bank = "clarity, trust, value, outcomes"
        if not suggestion.restricted_topics:
            suggestion.restricted_topics = "competitor disparagement, speculative guarantees"
        if not suggestion.restricted_claims:
            suggestion.restricted_claims = "guaranteed returns, risk-free, #1 without proof"
        if not suggestion.blocked_words_phrases:
            suggestion.blocked_words_phrases = "guaranteed, risk-free, forever free"

        suggestion.notes = [
            f"Filled from {suggestion.sources_used} vector knowledge chunks.",
            "Logo and font-file uploads still need to be attached manually if missing.",
        ]
        return suggestion
