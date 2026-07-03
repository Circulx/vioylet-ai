"""Multi-signal relevance reranking for Layer 1 brand retrieval.

Scores each retrieved chunk across four weighted signals:
    campaign 0.40 | audience 0.30 | compliance 0.20 | visual 0.10

An LLM (gpt-4o-mini) produces the per-signal scores for AI-optimized
relevance. If the LLM is unavailable or fails, a deterministic heuristic
based on the base similarity score and the chunk's influence_area is used
as a fallback so retrieval never hard-fails on the reranking step.
"""

import json
from dataclasses import dataclass, asdict
from typing import Any

from openai import OpenAI

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RankedChunk:
    chunk_id: str
    source: str
    section: str
    content: str
    content_summary: str
    influence_area: str
    pinecone_score: float
    campaign_score: float
    audience_score: float
    compliance_score: float
    visual_score: float
    composite_score: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class MultiSignalReranker:
    """Reranks retrieved chunks using LLM-scored multi-signal relevance."""

    WEIGHTS = {
        "campaign": 0.40,
        "audience": 0.30,
        "compliance": 0.20,
        "visual": 0.10,
    }

    # Bias per influence_area used by the heuristic fallback.
    _AREA_BIAS = {
        "strategy": {"campaign": 0.9, "audience": 0.7, "compliance": 0.3, "visual": 0.3},
        "copy": {"campaign": 0.7, "audience": 0.8, "compliance": 0.4, "visual": 0.3},
        "audience": {"campaign": 0.6, "audience": 0.95, "compliance": 0.3, "visual": 0.2},
        "compliance": {"campaign": 0.4, "audience": 0.3, "compliance": 0.95, "visual": 0.2},
        "visual": {"campaign": 0.4, "audience": 0.3, "compliance": 0.2, "visual": 0.95},
    }

    def __init__(self) -> None:
        self.settings = get_settings()
        self.openai_client = None
        if self.settings.openai_api_key:
            self.openai_client = OpenAI(api_key=self.settings.openai_api_key)

    def rerank(self, chunks: list[dict[str, Any]], campaign_context: dict[str, Any]) -> list[RankedChunk]:
        """Score and sort chunks by composite relevance (descending)."""
        if not chunks:
            return []

        signal_scores = self._score_signals(chunks, campaign_context)

        ranked: list[RankedChunk] = []
        for chunk, signals in zip(chunks, signal_scores):
            composite = (
                signals["campaign"] * self.WEIGHTS["campaign"]
                + signals["audience"] * self.WEIGHTS["audience"]
                + signals["compliance"] * self.WEIGHTS["compliance"]
                + signals["visual"] * self.WEIGHTS["visual"]
            )
            ranked.append(
                RankedChunk(
                    chunk_id=chunk.get("chunk_id", ""),
                    source=chunk.get("source", ""),
                    section=chunk.get("section", "Unknown"),
                    content=chunk.get("content", ""),
                    content_summary=chunk.get("content_summary", ""),
                    influence_area=chunk.get("influence_area", "strategy"),
                    pinecone_score=round(float(chunk.get("base_score", 0.0)), 4),
                    campaign_score=round(signals["campaign"], 4),
                    audience_score=round(signals["audience"], 4),
                    compliance_score=round(signals["compliance"], 4),
                    visual_score=round(signals["visual"], 4),
                    composite_score=round(composite, 4),
                )
            )

        return sorted(ranked, key=lambda c: c.composite_score, reverse=True)

    def _score_signals(self, chunks: list[dict[str, Any]], campaign_context: dict[str, Any]) -> list[dict[str, float]]:
        """Return a list of {campaign, audience, compliance, visual} score dicts."""
        if self.openai_client:
            try:
                return self._llm_score(chunks, campaign_context)
            except Exception as e:  # noqa: BLE001
                logger.error(f"LLM reranking failed, falling back to heuristic: {e}")
        return [self._heuristic_score(chunk) for chunk in chunks]

    def _llm_score(self, chunks: list[dict[str, Any]], campaign_context: dict[str, Any]) -> list[dict[str, float]]:
        indexed = [
            {
                "index": i,
                "section": chunk.get("section", "Unknown"),
                "influence_area": chunk.get("influence_area", "strategy"),
                "content": (chunk.get("content") or chunk.get("content_summary") or "")[:600],
            }
            for i, chunk in enumerate(chunks)
        ]

        prompt = f"""You are Violyt's brand-retrieval reranker. Score how relevant each brand
knowledge chunk is to this campaign request across four independent signals.

CAMPAIGN REQUEST:
- prompt: {campaign_context.get('user_prompt', '')}
- platform: {campaign_context.get('platform', '')}
- format: {campaign_context.get('format', '')}

SIGNALS (score each 0.0-1.0):
- campaign: relevance to the campaign objective / topic of the prompt
- audience: relevance to the target audience and their motivations
- compliance: relevance to brand rules, guardrails, legal or claim constraints
- visual: relevance to visual identity, design, imagery

CHUNKS:
{json.dumps(indexed, ensure_ascii=False)}

Return ONLY valid JSON: an object with key "scores" whose value is an array,
one object per chunk in the SAME order, each:
{{"index": int, "campaign": float, "audience": float, "compliance": float, "visual": float}}
No prose. No markdown."""

        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise relevance scorer. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)
        rows = parsed.get("scores", parsed if isinstance(parsed, list) else [])

        by_index: dict[int, dict[str, float]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            idx = int(row.get("index", -1))
            by_index[idx] = {
                "campaign": self._clamp(row.get("campaign")),
                "audience": self._clamp(row.get("audience")),
                "compliance": self._clamp(row.get("compliance")),
                "visual": self._clamp(row.get("visual")),
            }

        # Fill any missing rows with the heuristic so lengths always match.
        return [by_index.get(i) or self._heuristic_score(chunk) for i, chunk in enumerate(chunks)]

    def _heuristic_score(self, chunk: dict[str, Any]) -> dict[str, float]:
        base = self._clamp(chunk.get("base_score", 0.5))
        area = chunk.get("influence_area", "strategy")
        bias = self._AREA_BIAS.get(area, self._AREA_BIAS["strategy"])
        return {
            "campaign": self._clamp(base * 0.6 + bias["campaign"] * 0.4),
            "audience": self._clamp(base * 0.6 + bias["audience"] * 0.4),
            "compliance": self._clamp(base * 0.6 + bias["compliance"] * 0.4),
            "visual": self._clamp(base * 0.6 + bias["visual"] * 0.4),
        }

    @staticmethod
    def _clamp(value: Any) -> float:
        try:
            v = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, v))
