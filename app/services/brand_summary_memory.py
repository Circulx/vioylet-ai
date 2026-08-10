# Service classes hold business workflows between the HTTP layer, repositories, and integrations.
from __future__ import annotations

import json
import re
from typing import Any
from uuid import UUID

from app.integrations.vector_store import FaissVectorStoreProvider
from app.models.brand import BrandConfigurationSection, BrandSpace


class BrandSummaryMemoryService:
    # Business layer for brand summary memory; routes and workers pass validated inputs here and receive domain
    # results back.
    def __init__(self) -> None:
        # Wires the repositories and helper services this workflow reuses across its public methods.
        self.vectors = FaissVectorStoreProvider()

    @staticmethod
    def _clean_text(value: Any, *, limit: int | None = None) -> str:
        # Internal helper for clean text; it keeps the public service method focused on orchestration instead of
        # low-level shaping.
        text = " ".join(str(value or "").split()).strip()
        if limit is None or len(text) <= limit:
            return text
        return text[:limit].rstrip(" ,.;:")

    @staticmethod
    def _namespace(tenant_id: UUID, brand_space_id: UUID) -> str:
        # Internal helper for namespace; it keeps the public service method focused on orchestration instead of
        # low-level shaping.
        return FaissVectorStoreProvider().namespace(
            str(tenant_id),
            str(brand_space_id),
            "brand_summary",
        )

    @classmethod
    def _json_summary(cls, value: Any, *, limit: int = 1200) -> str:
        # Internal helper for json summary; it keeps the public service method focused on orchestration instead
        # of low-level shaping.
        if value in (None, "", [], {}):
            return ""
        try:
            serialized = json.dumps(value, ensure_ascii=True, sort_keys=True)
        except TypeError:
            serialized = str(value)
        return cls._clean_text(serialized, limit=limit)

    @classmethod
    def _section_payload_map(
        cls,
        sections: list[BrandConfigurationSection] | list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        # Internal helper for section payload map; it keeps the public service method focused on orchestration
        # instead of low-level shaping.
        payloads: dict[str, Any] = {}
        for section in sections or []:
            if isinstance(section, dict):
                section_code = str(section.get("section_code") or "").strip()
                payload = section.get("payload")
            else:
                section_code = str(getattr(section, "section_code", "") or "").strip()
                payload = getattr(section, "payload", None)
            if section_code:
                payloads[section_code] = payload if isinstance(payload, dict) else {}
        return payloads

    @classmethod
    def _compact_payload(cls, value: Any) -> Any:
        # Internal helper for compact payload; it keeps the public service method focused on orchestration
        # instead of low-level shaping.
        if isinstance(value, dict):
            compacted: dict[str, Any] = {}
            for key, raw_value in value.items():
                key_text = str(key)
                normalized_key = key_text.casefold()
                if "asset" in normalized_key or normalized_key in {"storage_path", "asset_url", "metadata_json"}:
                    continue
                compacted_value = cls._compact_payload(raw_value)
                if compacted_value not in (None, "", [], {}):
                    compacted[key_text] = compacted_value
            return compacted
        if isinstance(value, list):
            compacted_items = [cls._compact_payload(item) for item in value[:8]]
            return [item for item in compacted_items if item not in (None, "", [], {})]
        return value

    @classmethod
    def _query_terms(cls, query: str) -> set[str]:
        # Internal helper for query terms; it keeps the public service method focused on orchestration instead
        # of low-level shaping.
        return {
            token
            for token in re.findall(r"[a-z0-9]+", str(query or "").casefold())
            if len(token) > 2
        }

    @classmethod
    def _score_document_for_query(cls, doc: dict[str, Any], query_terms: set[str]) -> int:
        # Internal helper for document for query; it keeps the public service method focused on orchestration
        # instead of low-level shaping.
        if not query_terms:
            return 0
        searchable = (
            f"{doc.get('content', '')} "
            f"{(doc.get('metadata') or {}).get('section', '')}"
        ).casefold()
        return sum(1 for term in query_terms if term in searchable)

    @classmethod
    def _relevant_fallback_documents(
        cls,
        docs: list[dict[str, Any]],
        *,
        query: str,
        existing_contents: set[str],
        limit: int,
    ) -> list[str]:
        # Internal helper for relevant fallback documents; it keeps the public service method focused on
        # orchestration instead of low-level shaping.
        query_terms = cls._query_terms(query)
        scored: list[tuple[int, int, dict[str, Any]]] = []
        for index, doc in enumerate(docs):
            metadata = doc.get("metadata") or {}
            section = str(metadata.get("section") or "")
            if not section.startswith("form_"):
                continue
            content = cls._clean_text(doc.get("content"), limit=1800)
            if not content or content in existing_contents:
                continue
            score = cls._score_document_for_query(doc, query_terms)
            if score > 0:
                scored.append((score, -index, doc))
        scored.sort(reverse=True)
        return [
            cls._clean_text(doc["content"], limit=1800)
            for _score, _index, doc in scored[:limit]
        ]

    @classmethod
    def _build_documents(
        cls,
        brand: BrandSpace,
        *,
        sections: list[BrandConfigurationSection] | list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        # Internal helper for documents; it keeps the public service method focused on orchestration instead of
        # low-level shaping.
        context = dict(getattr(brand, "resolved_brand_context", {}) or {})
        identity = context.get("identity", {}) if isinstance(context.get("identity"), dict) else {}
        audience = context.get("audience_insights", {}) if isinstance(context.get("audience_insights"), dict) else {}
        voice_tone = context.get("voice_tone", {}) if isinstance(context.get("voice_tone"), dict) else {}
        visual_identity = context.get("visual_identity", {}) if isinstance(context.get("visual_identity"), dict) else {}
        foundations = context.get("foundations", {}) if isinstance(context.get("foundations"), dict) else {}
        guardrails = context.get("guardrails", {}) if isinstance(context.get("guardrails"), dict) else {}
        personas = context.get("personas", {}) if isinstance(context.get("personas"), dict) else {}
        default_persona = context.get("default_persona", {}) if isinstance(context.get("default_persona"), dict) else {}
        objectives = context.get("objectives", {}) if isinstance(context.get("objectives"), dict) else {}
        section_payloads = cls._section_payload_map(sections)
        identity_payload = section_payloads.get("identity") if isinstance(section_payloads.get("identity"), dict) else {}
        target_geography = (
            identity_payload.get("target_geography", {})
            if isinstance(identity_payload.get("target_geography"), dict)
            else {}
        )
        audience_type = (
            getattr(brand, "audience_type", None)
            or identity.get("audience_type")
            or identity_payload.get("audience_type")
            or ""
        )
        geography_country = (
            getattr(brand, "geography_country", None)
            or target_geography.get("country")
            or ""
        )
        geography_city = (
            getattr(brand, "geography_city", None)
            or target_geography.get("city")
            or ""
        )

        docs: list[dict[str, Any]] = []

        overall_summary = cls._clean_text(
            (
                f"Brand summary for {getattr(brand, 'name', '')}. "
                f"Tagline: {getattr(brand, 'tagline', None) or identity.get('brand_tagline') or identity_payload.get('brand_tagline') or ''}. "
                f"Description: {getattr(brand, 'description', '')}. "
                f"Industry: {getattr(brand, 'industry_category', None) or identity_payload.get('industry_category') or ''}. "
                f"Sub-industry: {getattr(brand, 'sub_industry', None) or identity_payload.get('sub_industry') or ''}. "
                f"Audience type: {audience_type}. "
                f"Country: {geography_country}. "
                f"City: {geography_city}. "
                f"Foundations: {cls._json_summary(foundations, limit=900)}."
            ),
            limit=2400,
        )
        docs.append(
            {
                "content": overall_summary,
                "metadata": {
                    "chunk_id": f"brand_summary:{brand.id}:overall",
                    "source_id": f"brand_summary:{brand.id}",
                    "section": "overall",
                },
            }
        )

        section_payloads = {
            "identity": identity,
            "audience": audience,
            "personas": personas,
            "default_persona": default_persona,
            "voice_tone": voice_tone,
            "visual_identity": visual_identity,
            "guardrails": guardrails,
            "objectives": objectives,
        }
        # Builds the grouped response or persistence payload one record at a time because later steps expect
        # this exact shape.
        for section, payload in section_payloads.items():
            summary = cls._json_summary(payload, limit=2200)
            if not summary:
                continue
            docs.append(
                {
                    "content": cls._clean_text(
                        f"Brand {section.replace('_', ' ')} summary for {brand.name}. {summary}",
                        limit=2600,
                    ),
                    "metadata": {
                        "chunk_id": f"brand_summary:{brand.id}:{section}",
                        "source_id": f"brand_summary:{brand.id}",
                        "section": section,
                    },
                }
            )

        # Builds the grouped response or persistence payload one record at a time because later steps expect
        # this exact shape.
        for section_code, payload in cls._section_payload_map(sections).items():
            compacted = cls._compact_payload(payload)
            summary = cls._json_summary(compacted, limit=2200)
            if not summary:
                continue
            docs.append(
                {
                    "content": cls._clean_text(
                        f"PostgreSQL form section {section_code.replace('_', ' ')} for {getattr(brand, 'name', '')}. {summary}",
                        limit=2600,
                    ),
                    "metadata": {
                        "chunk_id": f"brand_summary:{brand.id}:form:{section_code}",
                        "source_id": f"brand_summary:{brand.id}",
                        "section": f"form_{section_code}",
                    },
                }
            )
        return docs

    def upsert_brand_summary(
        self,
        brand: BrandSpace,
        *,
        sections: list[BrandConfigurationSection] | list[dict[str, Any]] | None = None,
    ) -> None:
        # Runs the brand summary service flow by coordinating repositories, validators, and integrations, then
        # returns domain data.
        docs = self._build_documents(brand, sections=sections)
        if not docs:
            return
        self.vectors.upsert_documents(
            self._namespace(brand.tenant_id, brand.id),
            docs,
        )

    def retrieve_brand_summary(
        self,
        *,
        brand: BrandSpace,
        query: str,
        limit: int = 3,
        sections: list[BrandConfigurationSection] | list[dict[str, Any]] | None = None,
    ) -> str:
        # Runs the retrieve brand summary service flow by coordinating repositories, validators, and
        # integrations, then returns domain data.
        namespace = self._namespace(brand.tenant_id, brand.id)
        docs = self._build_documents(brand, sections=sections)
        results = self.vectors.search(namespace, self._clean_text(query, limit=600), k=limit)
        if not results:
            self.upsert_brand_summary(brand, sections=sections)
            results = self.vectors.search(namespace, self._clean_text(query, limit=600), k=limit)
        # This guard handles missing or invalid input early so the main workflow can stay straightforward.
        if not results:
            fallback_lines = self._relevant_fallback_documents(
                docs,
                query=query,
                existing_contents=set(),
                limit=limit,
            )
            if fallback_lines:
                return "\n".join(fallback_lines)
            return "\n".join(doc["content"] for doc in docs[:limit])

        seen: set[str] = set()
        lines: list[str] = []
        # Builds the grouped response or persistence payload one record at a time because later steps expect
        # this exact shape.
        for result in results:
            content = self._clean_text(result.content, limit=1800)
            if not content or content in seen:
                continue
            seen.add(content)
            lines.append(content)
            if len(lines) >= limit:
                break
        fallback_lines = self._relevant_fallback_documents(
            docs,
            query=query,
            existing_contents=seen,
            limit=2,
        )
        for content in fallback_lines:
            if content in seen:
                continue
            seen.add(content)
            lines.append(content)
        return "\n".join(lines)
