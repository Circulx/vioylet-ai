"""Embeds structured brand-space form data (all tabs) into Pinecone.

When a user fills out the 9 brand-space tabs, the structured fields are saved
to PostgreSQL.  This service converts those fields into text chunks, embeds
them, and upserts them to the brand's Pinecone namespace so that Layer 1
retrieval can surface both document chunks *and* structured profile data.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.services.vectorstore.ingestion_service import (
    CATEGORY_TO_INFLUENCE,
    IngestionService,
    SECTION_TO_BRAND_TAB,
    normalize_category,
)

logger = get_logger(__name__)

# Stable asset-id prefix for profile-derived vectors so we can delete
# old profile vectors before re-upserting.
PROFILE_ASSET_PREFIX = "brand_profile"


class BrandProfileEmbedder:
    """Converts brand-space structured data → text chunks → Pinecone vectors."""

    def __init__(self) -> None:
        self.ingestion = IngestionService()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def embed_brand_profile(
        self,
        brand_id: str | UUID,
        *,
        brand_name: str,
        description: str = "",
        industry_category: str | None = None,
        overview_snapshot: dict[str, Any] | None = None,
        sections: list[dict[str, Any]] | None = None,
        personas: list[dict[str, Any]] | None = None,
        guardrails: list[dict[str, Any]] | None = None,
        objectives: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Embed all structured brand-space fields and upsert to Pinecone.

        Returns a summary dict with counts of upserted vectors.
        """
        brand_id_str = str(brand_id)
        overview_snapshot = overview_snapshot or {}
        sections = sections or []
        personas = personas or []
        guardrails = guardrails or []
        objectives = objectives or []

        chunks: list[dict[str, Any]] = []

        # 1 — Core identity
        chunks.extend(
            self._chunks_for_identity(
                brand_name=brand_name,
                description=description,
                industry_category=industry_category,
            )
        )

        # 2 — Foundations (from overview_snapshot or sections)
        foundations = overview_snapshot.get("foundations") or self._section_payload(sections, "foundations")
        if foundations:
            chunks.extend(self._chunks_for_foundations(foundations))

        # 3 — Voice & Tone
        voice_tone = overview_snapshot.get("voice_tone") or self._section_payload(sections, "voice_tone")
        if voice_tone:
            chunks.extend(self._chunks_for_voice_tone(voice_tone))

        # 4 — Visual Identity
        visual_identity = overview_snapshot.get("visual_identity") or self._section_payload(sections, "visual_identity")
        if visual_identity:
            chunks.extend(self._chunks_for_visual_identity(visual_identity))

        # 5 — Personas / Target Audience
        if personas:
            chunks.extend(self._chunks_for_personas(personas))

        # 6 — Guardrails / Brand Rules
        if guardrails:
            chunks.extend(self._chunks_for_guardrails(guardrails))

        # 7 — Objectives
        if objectives:
            chunks.extend(self._chunks_for_objectives(objectives))

        # 8 — Prompt Intelligence
        prompt_intel = self._section_payload(sections, "prompt_intelligence")
        if prompt_intel:
            chunks.extend(self._chunks_for_prompt_intelligence(prompt_intel))

        if not chunks:
            logger.warning(f"brand_profile_embedder.skip brand_id={brand_id_str} reason=no_data")
            return {"brand_id": brand_id_str, "total_chunks": 0}

        # Delete old profile vectors before re-upserting
        self.ingestion.delete_asset_vectors(brand_id_str, PROFILE_ASSET_PREFIX)

        upserted = self.ingestion.upsert_to_pinecone(
            brand_id_str,
            chunks,
            doc_id=PROFILE_ASSET_PREFIX,
        )

        logger.info(
            f"brand_profile_embedder.complete brand_id={brand_id_str} "
            f"chunks={len(chunks)} upserted={upserted}"
        )
        return {
            "brand_id": brand_id_str,
            "total_chunks": upserted,
            "sections_embedded": [c["category"] for c in chunks],
        }

    # ------------------------------------------------------------------
    # Section → text chunk converters
    # ------------------------------------------------------------------

    def _make_chunk(
        self,
        *,
        category: str,
        section: str,
        content: str,
    ) -> dict[str, Any]:
        """Build a chunk dict with normalised metadata."""
        normalized = normalize_category(category)
        return {
            "content": content,
            "category": normalized,
            "section": section,
            "influence_area": CATEGORY_TO_INFLUENCE.get(normalized, "strategy"),
            "content_summary": (content[:157] + "...") if len(content) > 160 else content,
            "filename": "brand_profile",
        }

    def _chunks_for_identity(
        self,
        *,
        brand_name: str,
        description: str,
        industry_category: str | None,
    ) -> list[dict[str, Any]]:
        lines: list[str] = []
        if brand_name:
            lines.append(f"Brand Name: {brand_name}")
        if description:
            lines.append(f"Brand Description: {description}")
        if industry_category:
            lines.append(f"Industry Category: {industry_category}")
        if not lines:
            return []
        return [self._make_chunk(
            category="identity",
            section="Brand Identity",
            content="\n".join(lines),
        )]

    def _chunks_for_foundations(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        lines: list[str] = []
        field_map = {
            "brand_mission": "Brand Mission",
            "brand_vision": "Brand Vision",
            "brand_promise": "Brand Promise",
            "market_positioning": "Market Positioning",
            "role_of_digital_platforms": "Role of Digital Platforms",
            "business_problem_or_opportunity": "Business Problem / Opportunity",
            "perception_challenge": "Perception Challenge",
            "human_insight": "Human Insight",
            "brand_advantage": "Brand Advantage",
        }
        for key, label in field_map.items():
            val = data.get(key)
            if val:
                lines.append(f"{label}: {val}")
        social_challenges = data.get("social_media_challenges", [])
        if social_challenges:
            lines.append(f"Social Media Challenges: {', '.join(social_challenges)}")
        if not lines:
            return []
        return [self._make_chunk(
            category="foundations",
            section="Brand Foundations",
            content="\n".join(lines),
        )]

    def _chunks_for_voice_tone(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        lines: list[str] = []
        tone_attrs = data.get("tone_attributes") or data.get("core_tone_attributes") or []
        if tone_attrs:
            lines.append(f"Tone Attributes: {', '.join(tone_attrs)}")
        tone_weights = data.get("tone_intensity") or data.get("core_tone_attribute_weights") or {}
        if tone_weights:
            weight_strs = [f"{k}: {v}" for k, v in tone_weights.items()]
            lines.append(f"Tone Intensity Weights: {', '.join(weight_strs)}")
        for key, label in [
            ("primary_emotion", "Primary Emotion"),
            ("secondary_emotion", "Secondary Emotion"),
            ("avoided_emotion", "Avoided Emotion"),
            ("content_complexity", "Content Complexity"),
            ("sentence_length", "Sentence Length"),
            ("perspective", "Perspective"),
        ]:
            val = data.get(key)
            if val:
                lines.append(f"{label}: {val}")
        if not lines:
            return []
        return [self._make_chunk(
            category="voice_tone",
            section="Voice & Tone",
            content="\n".join(lines),
        )]

    def _chunks_for_visual_identity(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        lines: list[str] = []
        for key, label in [
            ("brand_mood", "Brand Mood"),
            ("visual_style", "Visual Style"),
            ("typography", "Typography"),
        ]:
            val = data.get(key)
            if val:
                if isinstance(val, dict):
                    val = json.dumps(val, indent=2)
                lines.append(f"{label}: {val}")
        color_palette = data.get("brand_color_palette") or data.get("primary_color")
        if color_palette:
            if isinstance(color_palette, dict):
                color_strs = [f"{k}: {v}" for k, v in color_palette.items()]
                lines.append(f"Color Palette: {', '.join(color_strs)}")
            else:
                lines.append(f"Primary Color: {color_palette}")
        secondary = data.get("secondary_color")
        if secondary:
            lines.append(f"Secondary Color: {secondary}")
        logo_placement = data.get("logo_placement")
        if logo_placement:
            if isinstance(logo_placement, dict):
                positions = logo_placement.get("allowed_positions", [])
                if positions:
                    lines.append(f"Logo Placements: {', '.join(positions)}")
            else:
                lines.append(f"Logo Placement: {logo_placement}")
        if not lines:
            return []
        return [self._make_chunk(
            category="visual_identity",
            section="Visual Identity",
            content="\n".join(lines),
        )]

    def _chunks_for_personas(self, personas: list[dict[str, Any]]) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []
        for persona in personas:
            lines: list[str] = []
            name = persona.get("name", "")
            role = persona.get("role", "")
            if name:
                lines.append(f"Persona Name: {name}")
            if role:
                lines.append(f"Role: {role}")
            for key, label in [
                ("audience_goals", "Goals"),
                ("motivations", "Motivations"),
                ("fears_and_pain_points", "Fears & Pain Points"),
                ("objections", "Objections"),
            ]:
                vals = persona.get(key, [])
                if vals:
                    lines.append(f"{label}: {', '.join(vals)}")
            demographics = persona.get("demographics", {})
            if demographics:
                demo_strs = [f"{k}: {v}" for k, v in demographics.items() if v]
                if demo_strs:
                    lines.append(f"Demographics: {', '.join(demo_strs)}")
            psychographics = persona.get("psychographics", {})
            if psychographics:
                psy_strs = [f"{k}: {v}" for k, v in psychographics.items() if v]
                if psy_strs:
                    lines.append(f"Psychographics: {', '.join(psy_strs)}")
            content_behavior = persona.get("content_behavior", {})
            if content_behavior:
                cb_strs = [f"{k}: {v}" for k, v in content_behavior.items() if v]
                if cb_strs:
                    lines.append(f"Content Behavior: {', '.join(cb_strs)}")
            if len(lines) <= 1:
                continue
            chunks.append(self._make_chunk(
                category="personas",
                section=f"Persona: {name or role or 'Unknown'}",
                content="\n".join(lines),
            ))
        return chunks

    def _chunks_for_guardrails(self, guardrails: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not guardrails:
            return []
        data = guardrails[0]  # single guardrail record per brand
        lines: list[str] = []
        for key, label in [
            ("positive_word_bank", "Positive Word Bank"),
            ("replaceable_words", "Replaceable Words"),
            ("negative_word_bank", "Negative Word Bank"),
            ("dos", "Do's"),
            ("donts", "Don'ts"),
            ("forbidden_prompt_patterns", "Forbidden Prompt Patterns"),
            ("restricted_topics", "Restricted Topics"),
            ("restricted_claims", "Restricted Claims"),
            ("blocked_words", "Blocked Words"),
            ("custom_rules", "Custom Rules"),
        ]:
            vals = data.get(key, [])
            if vals:
                lines.append(f"{label}: {', '.join(vals)}")
        if not lines:
            return []
        return [self._make_chunk(
            category="guardrails",
            section="Brand Rules & Guardrails",
            content="\n".join(lines),
        )]

    def _chunks_for_objectives(self, objectives: list[dict[str, Any]]) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []
        for obj in objectives:
            lines: list[str] = []
            name = obj.get("name", "")
            if name:
                lines.append(f"Objective: {name}")
            description = obj.get("description")
            if description:
                lines.append(f"Description: {description}")
            content_type = obj.get("content_type")
            if content_type:
                lines.append(f"Content Type: {content_type}")
            platform_scope = obj.get("platform_scope")
            if platform_scope:
                lines.append(f"Platform Scope: {platform_scope}")
            config = obj.get("configuration", {})
            if config:
                config_strs = [f"{k}: {v}" for k, v in config.items() if v]
                if config_strs:
                    lines.append(f"Configuration: {', '.join(config_strs)}")
            if len(lines) <= 1:
                continue
            chunks.append(self._make_chunk(
                category="objectives",
                section=f"Objective: {name or 'Unknown'}",
                content="\n".join(lines),
            ))
        return chunks

    def _chunks_for_prompt_intelligence(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        lines: list[str] = []
        prompt_starters = data.get("prompt_starters", [])
        if prompt_starters:
            starter_strs = []
            for starter in prompt_starters:
                if isinstance(starter, dict):
                    starter_strs.append(starter.get("label", str(starter)))
                else:
                    starter_strs.append(str(starter))
            lines.append(f"Prompt Starters: {', '.join(starter_strs)}")
        platform_rules = data.get("platform_rules", {})
        if platform_rules:
            rule_strs = [f"{k}: {v}" for k, v in platform_rules.items() if v]
            if rule_strs:
                lines.append(f"Platform Rules: {', '.join(rule_strs)}")
        if not lines:
            return []
        return [self._make_chunk(
            category="prompt_intelligence",
            section="Prompt Intelligence",
            content="\n".join(lines),
        )]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _section_payload(sections: list[dict[str, Any]], section_code: str) -> dict[str, Any]:
        """Extract the payload dict for a given section_code from a list of sections."""
        for section in sections:
            if section.get("section_code") == section_code:
                return section.get("payload", {})
        return {}
