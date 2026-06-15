from __future__ import annotations

import logging
import json
from pathlib import Path
import re
from typing import Any
from uuid import UUID

from docx import Document
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.brand_asset_analysis import BrandAssetAnalyzer
from app.ai.rag.ocr import OCRService
from app.ai.template_vision import TemplateVisionAnalyzer
from app.core.enums import JobType, UsageMetricCode
from app.core.exceptions import NotFoundError
from app.core.studio import resolve_studio_panel_defaults
from app.integrations.object_storage import get_object_storage
from app.models.knowledge import Template, TemplateMetadata
from app.repositories.brand import BrandSpaceRepository
from app.repositories.knowledge import TemplateMetadataRepository, TemplateRepository
from app.schemas.template import TemplateMetadataUpsertRequest, TemplateRecommendationResponse, TemplateUploadRequest
from app.services.asset_delivery import AssetDeliveryService
from app.services.jobs import JobService
from app.services.upload_preflight import UploadPreflightService
from app.services.usage import UsageLimitService

logger = logging.getLogger(__name__)

SLIDE_ROLE_TEMPLATE_MAP: dict[str, str] = {
    "hook": "HOOK_MINIMAL",
    "problem": "PROBLEM_STAT",
    "insight": "SPLIT_VIEW",
    "data": "DATA_GRID",
    "cta": "CENTER_FOCUS",
}

DEFAULT_SLIDE_ROLE = "hook"
DEFAULT_TEMPLATE_ID = SLIDE_ROLE_TEMPLATE_MAP[DEFAULT_SLIDE_ROLE]


def normalize_slide_role(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def template_id_for_slide_role(slide_role: Any) -> str:
    role = normalize_slide_role(slide_role)
    return SLIDE_ROLE_TEMPLATE_MAP.get(role, DEFAULT_TEMPLATE_ID)


def template_fallback_used_for_slide_role(slide_role: Any) -> bool:
    return normalize_slide_role(slide_role) not in SLIDE_ROLE_TEMPLATE_MAP


class TemplateService:
    TEMPLATE_MATCH_STOPWORDS = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "into",
        "is",
        "it",
        "its",
        "linkedin",
        "of",
        "on",
        "or",
        "platform",
        "post",
        "the",
        "this",
        "to",
        "with",
        "x",
        "about",
        "break",
        "breakdown",
        "can",
        "create",
        "creating",
        "focus",
        "give",
        "how",
        "include",
        "including",
        "practical",
        "show",
        "smarter",
        "structured",
        "your",
        "jiraaf",
    }
    TEMPLATE_TOPIC_GENERIC_TOKENS = TEMPLATE_MATCH_STOPWORDS | {
        "adaptation",
        "brand",
        "carousel",
        "client",
        "content",
        "creative",
        "document",
        "format",
        "guide",
        "image",
        "layout",
        "page",
        "pages",
        "pdf",
        "prompt",
        "reference",
        "sample",
        "slide",
        "slides",
        "style",
        "template",
        "visual",
        "working",
        "professional",
        "professionals",
    }

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.templates = TemplateRepository(session)
        self.metadata = TemplateMetadataRepository(session)
        self.brands = BrandSpaceRepository(session)
        self.storage = get_object_storage()
        self.jobs = JobService(session)
        self.vision = TemplateVisionAnalyzer()
        self.brand_asset_analyzer = BrandAssetAnalyzer()
        self.ocr = OCRService()
        self.usage = UsageLimitService(session)
        self.preflight = UploadPreflightService()
        self.asset_delivery = AssetDeliveryService()

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-z0-9]+", text.lower())
            if len(token) > 2 and token not in TemplateService.TEMPLATE_MATCH_STOPWORDS
        }

    @classmethod
    def _specific_topic_tokens(cls, tokens: set[str]) -> set[str]:
        specific: set[str] = set()
        for token in tokens:
            normalized = str(token or "").strip().lower()
            if not normalized or normalized in cls.TEMPLATE_TOPIC_GENERIC_TOKENS:
                continue
            if len(normalized) <= 3 and not re.fullmatch(r"\d{2}s", normalized):
                continue
            specific.add(normalized)
        return specific

    @classmethod
    def _collect_analysis_text_fragments(cls, value: Any, *, limit: int = 80) -> list[str]:
        fragments: list[str] = []

        def visit(item: Any) -> None:
            if len(fragments) >= limit:
                return
            if isinstance(item, str):
                text = item.strip()
                if text:
                    fragments.append(text)
                return
            if isinstance(item, dict):
                for child in item.values():
                    visit(child)
                    if len(fragments) >= limit:
                        return
                return
            if isinstance(item, (list, tuple)):
                for child in item:
                    visit(child)
                    if len(fragments) >= limit:
                        return

        visit(value)
        return fragments

    @staticmethod
    def _export_formats_for_template(storage_path: str) -> list[str]:
        suffix = Path(storage_path).suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
            return ["png", "jpg", "pdf"]
        if suffix in {".doc", ".docx", ".pdf"}:
            return ["pdf", "doc"]
        return ["png", "jpg", "pdf", "doc"]

    @staticmethod
    def _resolve_vision_source(absolute_path: str, extracted: dict) -> str | None:
        suffix = Path(absolute_path).suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg", ".webp"} and Path(absolute_path).exists():
            return absolute_path
        for image_path in extracted.get("images", []) or []:
            candidate = Path(str(image_path))
            if candidate.exists():
                return str(candidate)
        return None

    @staticmethod
    def _default_template_zones(width: int, height: int) -> list[dict[str, int | str]]:
        pad_x = max(48, int(width * 0.06))
        pad_y = max(40, int(height * 0.06))
        return [
            {"zone_id": "logo", "role": "logo", "x": width - pad_x - 180, "y": pad_y, "width": 180, "height": 80},
            {"zone_id": "headline", "role": "headline", "x": pad_x, "y": pad_y, "width": width - (pad_x * 2), "height": max(140, int(height * 0.18)), "max_lines": 3},
            {"zone_id": "body", "role": "body", "x": pad_x, "y": pad_y + max(150, int(height * 0.2)), "width": width - (pad_x * 2), "height": max(180, int(height * 0.24)), "max_lines": 8},
            {"zone_id": "image", "role": "image", "x": pad_x, "y": pad_y + max(360, int(height * 0.46)), "width": width - (pad_x * 2), "height": max(220, int(height * 0.28))},
            {"zone_id": "cta", "role": "cta", "x": pad_x, "y": height - pad_y - 100, "width": min(360, width - (pad_x * 2)), "height": 100, "max_lines": 2},
        ]

    @classmethod
    def _normalize_editable_zones(
        cls,
        editable_zones: list[dict[str, Any]] | None,
        width: int,
        height: int,
    ) -> list[dict[str, Any]]:
        defaults = cls._default_template_zones(width, height)
        fallback_by_role = {
            str(zone.get("role", "")): zone
            for zone in defaults
            if zone.get("role")
        }
        if not editable_zones:
            return defaults

        normalized: list[dict[str, Any]] = []
        for index, zone in enumerate(editable_zones):
            if not isinstance(zone, dict):
                continue
            role = str(zone.get("role") or zone.get("zone_id") or "").strip().lower()
            if not role:
                continue
            fallback = fallback_by_role.get(role) or defaults[min(index, len(defaults) - 1)]

            def _value_for(key: str, fallback_key: str) -> int:
                raw = zone.get(key)
                if isinstance(raw, (int, float)):
                    numeric = float(raw)
                    if 0 <= numeric <= 1:
                        scale = width if key in {"x", "width"} else height
                        return max(int(numeric * scale), 0)
                    return max(int(numeric), 0)
                return int(fallback[fallback_key])

            normalized.append(
                {
                    "zone_id": str(zone.get("zone_id") or fallback.get("zone_id") or role),
                    "role": role,
                    "x": _value_for("x", "x"),
                    "y": _value_for("y", "y"),
                    "width": max(_value_for("width", "width"), 1),
                    "height": max(_value_for("height", "height"), 1),
                    "max_lines": zone.get("max_lines", fallback.get("max_lines")),
                }
            )
        return normalized or defaults

    @staticmethod
    def _editable_fields_from_zones(zones: list[dict[str, Any]]) -> list[str]:
        allowed_roles = {"headline", "body", "cta", "logo", "image", "header", "footer"}
        roles = {
            str(zone.get("role", "")).strip().lower()
            for zone in zones
            if isinstance(zone, dict) and zone.get("role")
        }
        editable_fields = sorted(role for role in roles if role in allowed_roles)
        if "icons" not in editable_fields:
            editable_fields.append("icons")
        return editable_fields

    @staticmethod
    def _extract_docx_text(absolute_path: str, extracted: dict[str, object]) -> str:
        source_format = str(extracted.get("source_format") or "").lower()
        if source_format != "docx" and not absolute_path.lower().endswith(".docx"):
            return ""
        document = Document(absolute_path)
        return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())

    @classmethod
    def _template_surface_policy(
        cls,
        *,
        text: str,
        source_format: str,
        zone_roles: set[str],
        rich_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        word_count = len(re.findall(r"[A-Za-z0-9]+", text))
        text_length = len(text.strip())
        text_zone_count = len(zone_roles & {"headline", "body", "header", "footer", "proof_point", "stat_highlight", "cta"})
        style_map_count = len(rich_analysis.get("text_style_map", []) or [])
        heading_signal_count = sum(
            1
            for key in ("heading", "header", "footer")
            if str(rich_analysis.get(key) or "").strip()
        )
        raster_like = source_format.lower() in {"png", "jpg", "jpeg", "webp", "pdf"}

        risk_score = 0
        if raster_like:
            risk_score += 2
        if text_length >= 160:
            risk_score += 2
        elif text_length >= 80:
            risk_score += 1
        if word_count >= 24:
            risk_score += 2
        elif word_count >= 12:
            risk_score += 1
        if text_zone_count >= 3:
            risk_score += 1
        if style_map_count >= 3:
            risk_score += 1
        if heading_signal_count >= 2:
            risk_score += 1

        if risk_score >= 5:
            text_overlay_risk = "high"
        elif risk_score >= 3:
            text_overlay_risk = "medium"
        else:
            text_overlay_risk = "low"

        overlay_safe = not (
            raster_like
            and text_overlay_risk == "high"
            and (text_zone_count >= 2 or word_count >= 16 or text_length >= 120)
        )
        return {
            "surface_kind": "overlay_safe" if overlay_safe else "reference_only_flattened_text",
            "text_overlay_risk": text_overlay_risk,
            "overlay_safe": overlay_safe,
            "text_word_count": word_count,
            "text_character_count": text_length,
        }

    @staticmethod
    def _read_analysis_text(analysis_path: str | None) -> str:
        if not analysis_path:
            return ""
        path = Path(analysis_path)
        if not path.exists():
            return ""

        raw_text = path.read_text(encoding="utf-8", errors="replace").strip()
        if not raw_text:
            return ""
        if path.suffix.lower() != ".json":
            return raw_text
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            return raw_text
        return json.dumps(parsed, ensure_ascii=False, indent=2)

    @classmethod
    def _extract_font_names(cls, families: list[dict[str, Any]] | list[str] | None) -> set[str]:
        names: set[str] = set()
        for family in families or []:
            if isinstance(family, dict):
                candidate = str(family.get("name") or "").strip().lower()
            else:
                candidate = str(family).strip().lower()
            if candidate:
                names.add(candidate)
        return names

    @classmethod
    def _extract_palette_tokens(cls, entries: list[dict[str, Any]] | dict[str, Any] | None) -> set[str]:
        tokens: set[str] = set()
        if isinstance(entries, dict):
            iterable = [{"hex_code": value} for _key, value in entries.items()]
        else:
            iterable = entries or []
        for entry in iterable:
            if not isinstance(entry, dict):
                continue
            hex_code = str(entry.get("hex_code") or entry.get("value") or "").strip().lower()
            if hex_code:
                tokens.add(hex_code)
        return tokens

    @classmethod
    def _derive_content_patterns(cls, text: str, layout_type: str, zone_roles: set[str]) -> set[str]:
        lowered = text.lower()
        patterns: set[str] = set()
        if layout_type:
            patterns.add(layout_type)
        if any(token in lowered for token in ["launch", "introducing", "new product", "announcement"]):
            patterns.add("announcement")
        if any(token in lowered for token in ["benefit", "why", "how", "step", "insight", "explainer", "education"]):
            patterns.add("explainer")
        if any(token in lowered for token in ["compare", "comparison", "versus", "vs", "case 01", "case 02"]):
            patterns.add("comparison")
        if any(token in lowered for token in ["offer", "discount", "limited time", "sale", "register", "apply now"]):
            patterns.add("promotion")
        if any(token in lowered for token in ["testimonial", "customer", "review", "client story"]):
            patterns.add("testimonial")
        if any(token in lowered for token in ["data", "stat", "chart", "graph", "ranking", "rank", "percent", "report", "metrics", "inflation", "gdp", "growth", "economy"]):
            patterns.add("data_visualization")
        if "cta" in zone_roles:
            patterns.add("conversion")
        if "image" in zone_roles:
            patterns.add("visual_first")
        if len(zone_roles & {"body", "proof_point", "stat_highlight"}) >= 2 or "data" in lowered or "ranking" in lowered:
            patterns.add("information_dense")
        return patterns

    @staticmethod
    def _normalize_format_family(value: Any) -> str | None:
        text = str(value or "").strip().lower()
        if not text:
            return None
        if text in {"carousel", "carousal", "slides", "multi_slide", "multi-slide", "multi_page", "multi-page"}:
            return "carousel"
        if text in {"infographic", "multi_section", "multi-section", "explainer_board", "explainer-board"}:
            return "infographic"
        if text in {"static", "single", "single_panel", "single-panel", "poster", "thumbnail", "post"}:
            return "static"
        return None

    @classmethod
    def _derive_format_family(
        cls,
        *,
        template: Template,
        metadata: TemplateMetadata | None,
        layout_type: str,
        page_count: int,
        zone_roles: set[str],
    ) -> str:
        explicit_candidates = [
            template.matcher_features_json.get("format_family") if isinstance(template.matcher_features_json, dict) else None,
            template.analysis_json.get("format_family"),
            ((template.analysis_json.get("editorial_dna") or {}) if isinstance(template.analysis_json.get("editorial_dna"), dict) else {}).get("format_family"),
            (metadata.zone_map.get("format_family") if metadata and isinstance(metadata.zone_map, dict) else None),
            layout_type,
            template.kind,
        ]
        for candidate in explicit_candidates:
            normalized = cls._normalize_format_family(candidate)
            if normalized:
                return normalized
        if page_count >= 3:
            return "carousel"
        if layout_type in {"infographic", "multi_section", "comparison"}:
            return "infographic"
        if len(zone_roles & {"body", "proof_point", "stat_highlight", "image"}) >= 3:
            return "infographic"
        return "static"

    @classmethod
    def _template_profile(cls, template: Template, metadata: TemplateMetadata | None) -> dict[str, Any]:
        matcher = template.matcher_features_json or {}
        zone_roles = {
            str(zone.get("role")).strip().lower()
            for zone in (metadata.zone_map.get("zones", []) if metadata else [])
            if isinstance(zone, dict) and zone.get("role")
        }
        keyword_source = " ".join(
            filter(
                None,
                [
                    template.name,
                    template.description or "",
                    *template.tags,
                    str(matcher.get("layout_type") or ""),
                    " ".join(str(pattern) for pattern in matcher.get("content_patterns", []) or []),
                ],
            )
        )
        title_source = " ".join(
            filter(
                None,
                [
                    template.name,
                    template.description or "",
                    str(template.analysis_json.get("source_filename") or ""),
                    str(template.analysis_json.get("filename") or ""),
                ],
            )
        )
        content_patterns = {
            str(pattern).strip().lower()
            for pattern in matcher.get("content_patterns", []) or []
            if str(pattern).strip()
        }
        analysis_text = " ".join(cls._collect_analysis_text_fragments(template.analysis_json))
        matcher_text = " ".join(cls._collect_analysis_text_fragments(matcher))
        layout_type = str(
            matcher.get("layout_type")
            or (metadata.zone_map.get("layout_type") if metadata else "")
            or template.analysis_json.get("layout_type")
            or template.kind
        ).strip().lower()
        if layout_type:
            content_patterns.add(layout_type)
        page_count = 0
        if metadata and isinstance(getattr(metadata, "sizing_rules", None), dict):
            for raw_count in (
                metadata.sizing_rules.get("page_count"),
                metadata.sizing_rules.get("slide_count"),
            ):
                try:
                    parsed = int(raw_count or 0)
                except (TypeError, ValueError):
                    parsed = 0
                if parsed > 0:
                    page_count = parsed
                    break
        if page_count <= 0:
            for raw_count in (
                template.analysis_json.get("page_count"),
                template.analysis_json.get("preflight_page_count"),
            ):
                try:
                    parsed = int(raw_count or 0)
                except (TypeError, ValueError):
                    parsed = 0
                if parsed > 0:
                    page_count = parsed
                    break
        format_family = cls._derive_format_family(
            template=template,
            metadata=metadata,
            layout_type=layout_type,
            page_count=page_count,
            zone_roles=zone_roles,
        )
        return {
            "tokens": cls._tokenize(keyword_source),
            "title_tokens": cls._tokenize(title_source),
            "ocr_tokens": cls._tokenize(
                " ".join(
                    filter(
                        None,
                        [
                            analysis_text,
                            matcher_text,
                            str(template.analysis_json.get("extracted_text_preview") or ""),
                            str(template.analysis_json.get("heading") or ""),
                            str(template.analysis_json.get("header") or ""),
                            str(template.analysis_json.get("footer") or ""),
                        ],
                    )
                )
            ),
            "layout_type": layout_type,
            "zone_roles": zone_roles,
            "supports_logo": "logo" in zone_roles,
            "supports_cta": "cta" in zone_roles,
            "supports_image": "image" in zone_roles,
            "supports_body": "body" in zone_roles,
            "multi_section_capable": len(zone_roles & {"body", "proof_point", "stat_highlight", "image"}) >= 2
            or layout_type in {"infographic", "carousel", "multi_section"},
            "platform_hints": set((metadata.platform_rules.get("supported_platforms", []) if metadata else []) or matcher.get("supported_platforms", []) or []),
            "export_formats": set((metadata.export_rules.get("supported_formats", []) if metadata else []) or matcher.get("supported_exports", []) or []),
            "palette_tokens": cls._extract_palette_tokens(matcher.get("palette", [])),
            "font_names": cls._extract_font_names(matcher.get("font_families", [])),
            "content_patterns": content_patterns,
            "brand_score": float(matcher.get("brand_score", template.analysis_json.get("brand_score", 0.0) or 0.0)),
            "editable_fields": set(metadata.editable_fields if metadata else []),
            "page_count": page_count,
            "surface_kind": str(
                matcher.get("surface_kind")
                or template.analysis_json.get("surface_kind")
                or "overlay_safe"
            ).strip().lower(),
            "text_overlay_risk": str(
                matcher.get("text_overlay_risk")
                or template.analysis_json.get("text_overlay_risk")
                or "low"
            ).strip().lower(),
            "overlay_safe": bool(
                matcher.get("overlay_safe", template.analysis_json.get("overlay_safe", True))
            ),
            "format_family": format_family,
        }

    @staticmethod
    def _deterministic_template_token(value: Any) -> str:
        return re.sub(r"[^A-Z0-9]+", "_", str(value or "").strip().upper()).strip("_")

    @classmethod
    def _logical_template_id_for_template(
        cls,
        template: Template,
        metadata: TemplateMetadata | None,
    ) -> str:
        matcher = template.matcher_features_json if isinstance(template.matcher_features_json, dict) else {}
        analysis = template.analysis_json if isinstance(template.analysis_json, dict) else {}
        zone_map = metadata.zone_map if metadata and isinstance(metadata.zone_map, dict) else {}
        candidates = [
            matcher.get("deterministic_template_id"),
            matcher.get("logical_template_id"),
            matcher.get("template_rule_id"),
            analysis.get("deterministic_template_id"),
            analysis.get("logical_template_id"),
            analysis.get("template_rule_id"),
            zone_map.get("deterministic_template_id"),
            zone_map.get("logical_template_id"),
            zone_map.get("template_rule_id"),
            template.name,
            Path(str(template.storage_path or "")).stem,
            *(template.tags or []),
        ]
        valid_ids = set(SLIDE_ROLE_TEMPLATE_MAP.values())
        for candidate in candidates:
            token = cls._deterministic_template_token(candidate)
            if token in valid_ids:
                return token
        return ""

    @classmethod
    def _requested_template_role_flags(cls, studio_panel: dict[str, Any]) -> list[tuple[str, bool]]:
        requested_roles = studio_panel.get("slide_roles") or studio_panel.get("roles")
        if isinstance(requested_roles, list):
            raw_roles = [role for role in requested_roles if normalize_slide_role(role)]
        else:
            raw_role = (
                studio_panel.get("slide_role")
                or studio_panel.get("role")
                or studio_panel.get("story_role")
            )
            raw_roles = [raw_role] if normalize_slide_role(raw_role) else []
        if not raw_roles:
            format_name = str(studio_panel.get("format") or "").strip().lower()
            if format_name in {"carousel", "instagram_carousel", "linkedin_carousel"}:
                raw_roles = list(SLIDE_ROLE_TEMPLATE_MAP.keys())
            else:
                raw_roles = [DEFAULT_SLIDE_ROLE]
        ordered_roles: list[tuple[str, bool]] = []
        seen_roles: set[str] = set()
        for raw_role in raw_roles:
            role = normalize_slide_role(raw_role)
            fallback_used = role not in SLIDE_ROLE_TEMPLATE_MAP
            mapped_role = role if not fallback_used else DEFAULT_SLIDE_ROLE
            if mapped_role not in seen_roles:
                ordered_roles.append((mapped_role, fallback_used))
                seen_roles.add(mapped_role)
            elif fallback_used:
                ordered_roles = [
                    (existing_role, existing_fallback or existing_role == mapped_role)
                    for existing_role, existing_fallback in ordered_roles
                ]
        return ordered_roles or [(DEFAULT_SLIDE_ROLE, True)]

    @classmethod
    def _requested_template_roles(cls, studio_panel: dict[str, Any]) -> list[str]:
        return [role for role, _fallback_used in cls._requested_template_role_flags(studio_panel)]

    @classmethod
    def _sequence_recommendation_signature(value: Any) -> tuple[str, int] | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        raw = raw.split("?", 1)[0]
        stem = Path(raw).name
        if "." in stem:
            stem = Path(stem).stem
        normalized = re.sub(r"[\s_]+", "-", stem.strip())
        match = re.match(r"^(?P<family>.+?)-(?P<index>\d+)(?:-[0-9a-f]{8,})?$", normalized, flags=re.IGNORECASE)
        if not match:
            return None
        try:
            slide_index = int(match.group("index"))
        except ValueError:
            return None
        if slide_index <= 0:
            return None
        family = re.sub(r"[-_\s]+", "-", match.group("family")).strip("-").upper()
        return (family, slide_index) if family else None

    @staticmethod
    async def upload(self, tenant_id: UUID, brand_space_id: UUID, payload: TemplateUploadRequest) -> Template:
        preflight = self.preflight.validate_base64_upload(
            filename=payload.filename,
            mime_type=payload.mime_type,
            content_base64=payload.content_base64,
        )
        stored = self.storage.save_bytes(tenant_id, brand_space_id, "templates", payload.filename, preflight.content)
        template = Template(
            tenant_id=tenant_id,
            brand_space_id=brand_space_id,
            name=payload.name,
            description=payload.description,
            kind=payload.kind,
            storage_path=stored.storage_path,
            analysis_json={
                "status": "queued",
                "source_format": preflight.detected_extension.lstrip("."),
                "file_size_bytes": preflight.size_bytes,
                "preflight_page_count": preflight.page_count,
                "preflight_hints": preflight.hints or {},
            },
            tags=payload.tags,
        )
        await self.templates.add(template)
        await self.metadata.add(
            TemplateMetadata(
                tenant_id=tenant_id,
                brand_space_id=brand_space_id,
                template_id=template.id,
                zone_map={},
                sizing_rules={},
                platform_rules={},
                editable_fields=[],
                export_rules={},
            )
        )
        await self.session.commit()
        await self.jobs.create(
            tenant_id=tenant_id,
            brand_space_id=brand_space_id,
            job_type=JobType.TEMPLATE_ANALYSIS,
            payload={"template_id": str(template.id)},
        )
        return template

    async def analyze(self, template_id: UUID) -> Template:
        template = await self.templates.get(template_id)
        if not template:
            raise NotFoundError("Template not found")
        template.analysis_json = {
            **(template.analysis_json or {}),
            "status": "processing",
        }
        await self.session.commit()

        width = 1080
        height = 1080
        absolute_path = self.storage.absolute_path(template.storage_path)
        template_kind = template.kind
        extracted = {"text": "", "images": [], "page_count": 0}
        page_count = 0
        try:
            extracted = self.ocr.extract(absolute_path)
            text = extracted.get("text", "")
            if not text:
                text = self._extract_docx_text(absolute_path, extracted)

            analysis_path = extracted.get("analysis_path")
            analysis_text = self._read_analysis_text(analysis_path)
            if analysis_text:
                text = "\n\n".join(part for part in [text, analysis_text] if part).strip()

            image_texts: list[str] = []
            for image_path in extracted.get("images", []) or []:
                if image_path == absolute_path:
                    continue
                try:
                    image_text = self.ocr.extract(str(image_path)).get("text", "")
                except Exception:  # noqa: BLE001
                    image_text = ""
                if image_text:
                    image_texts.append(image_text)
            if image_texts:
                text = "\n\n".join(part for part in [text, *image_texts] if part).strip()

            page_count = int(extracted.get("page_count") or 0)
            if text or extracted.get("images") or analysis_path:
                usage_amount = max(page_count, 1)
                await self.usage.enforce(template.tenant_id, UsageMetricCode.OCR_PAGES, usage_amount)
                await self.usage.increment(template.tenant_id, UsageMetricCode.OCR_PAGES, usage_amount)

            vision_source = self._resolve_vision_source(absolute_path, extracted)
            if vision_source:
                with Image.open(vision_source) as image:
                    width, height = image.size
            elif Path(absolute_path).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                with Image.open(absolute_path) as image:
                    width, height = image.size
        except Exception as exc:  # noqa: BLE001
            template.analysis_json = {
                **(template.analysis_json or {}),
                "status": "failed",
                "error": str(exc),
                "page_count": page_count,
            }
            await self.session.commit()
            raise

        heuristic = {
            "background_style": {"dominant_mode": "graphic", "source": "heuristic"},
            "layout_type": template_kind,
            "editable_zones": self._default_template_zones(width, height),
            "icons": [],
            "platform_hints": ["instagram", "linkedin", "x", "youtube_thumbnail"],
        }
        vision_source = self._resolve_vision_source(absolute_path, extracted)
        vision = self.vision.analyze(vision_source, heuristic) if vision_source else heuristic
        normalized_zones = self._normalize_editable_zones(
            vision.get("editable_zones", heuristic["editable_zones"]),
            width,
            height,
        )
        _structured, normalized, rich_analysis = self.brand_asset_analyzer._extract_template_intelligence(
            text=text,
            absolute_path=absolute_path,
            images=extracted.get("images", []) or [],
            category="template",
            analysis_paths=extracted.get("analysis_paths", []) or [],
        )
        zone_roles = {
            str(zone.get("role")).strip().lower()
            for zone in normalized_zones
            if isinstance(zone, dict) and zone.get("role")
        }
        matcher_features = {
            "palette": normalized.get("palette", []),
            "font_families": normalized.get("font_families", []),
            "layout_type": rich_analysis.get("layout_type", vision.get("layout_type", template_kind)),
            "brand_score": rich_analysis.get("brand_score", vision.get("brand_score", template.analysis_json.get("brand_score", 0.0))),
            "zone_roles": sorted(zone_roles),
            "content_patterns": sorted(
                self._derive_content_patterns(
                    text,
                    rich_analysis.get("layout_type", vision.get("layout_type", template_kind)),
                    zone_roles,
                )
            ),
            "supported_platforms": vision.get("platform_hints", ["instagram", "linkedin", "x", "youtube_thumbnail"]),
            "supported_exports": self._export_formats_for_template(absolute_path),
        }
        surface_policy = self._template_surface_policy(
            text=text,
            source_format=str(extracted.get("source_format") or Path(absolute_path).suffix.lower().lstrip(".")),
            zone_roles=zone_roles,
            rich_analysis=rich_analysis,
        )
        matcher_features.update(
            {
                "surface_kind": surface_policy["surface_kind"],
                "text_overlay_risk": surface_policy["text_overlay_risk"],
                "overlay_safe": surface_policy["overlay_safe"],
            }
        )
        template.analysis_json = {
            "status": "indexed",
            "layout_type": rich_analysis.get("layout_type", vision.get("layout_type", template_kind)),
            "deterministic": True,
            "canvas_size": {"width": width, "height": height},
            "background_style": rich_analysis.get("background_style", vision.get("background_style", {})),
            "icons": rich_analysis.get("icons", vision.get("icons", [])),
            "page_count": page_count,
            "source_format": extracted.get("source_format") or Path(absolute_path).suffix.lower().lstrip("."),
            "analysis_source": "ocr_vision" if vision_source else "ocr_text",
            "extracted_text_preview": (text[:1500] if text else ""),
            "heading": rich_analysis.get("heading"),
            "header": rich_analysis.get("header"),
            "footer": rich_analysis.get("footer"),
            "heading_style": rich_analysis.get("heading_style"),
            "header_style": rich_analysis.get("header_style"),
            "footer_style": rich_analysis.get("footer_style"),
            "color_usage": rich_analysis.get("color_usage", []),
            "font_families": rich_analysis.get("font_families", []),
            "font_colors": rich_analysis.get("font_colors", []),
            "font_size_hints": rich_analysis.get("font_size_hints", []),
            "text_style_map": rich_analysis.get("text_style_map", []),
            "gradients": rich_analysis.get("gradients", []),
            "zones": normalized_zones,
            "surface_kind": surface_policy["surface_kind"],
            "text_overlay_risk": surface_policy["text_overlay_risk"],
            "overlay_safe": surface_policy["overlay_safe"],
            "text_word_count": surface_policy["text_word_count"],
            "text_character_count": surface_policy["text_character_count"],
            # Design DNA from vision AI â€” saved so zone_map can carry them forward
            "visual_mood": vision.get("visual_mood", ""),
            "design_style": vision.get("design_style", ""),
            "composition_style": vision.get("composition_style", ""),
            "typography_dna": vision.get("typography_dna", {}),
            "component_motifs": vision.get("component_motifs", {}),
            "infographic_elements": vision.get("infographic_elements", {}),
            "layout_dna": rich_analysis.get("layout_dna", {}),
            "composition_logic": rich_analysis.get("composition_logic", {}),
            "visual_craft_dna": rich_analysis.get("visual_craft_dna", {}),
            "subject_semantics": rich_analysis.get("subject_semantics", {}),
            "logo_anchor": vision.get("logo_anchor", ""),
            "editorial_dna": rich_analysis.get("editorial_dna", {}),
        }
        template.matcher_features_json = matcher_features
        metadata = await self.metadata.get_by_template(template.id)
        if metadata:
            metadata.zone_map = {
                "layout_type": template.analysis_json["layout_type"],
                "zones": template.analysis_json["zones"],
                "canvas_size": {"width": width, "height": height},
                "icons": template.analysis_json["icons"],
                "background_style": template.analysis_json["background_style"],
                "text_style_map": template.analysis_json.get("text_style_map", []),
                "gradients": template.analysis_json.get("gradients", []),
                # Design DNA fields from Vision AI analysis
                "typography_dna": template.analysis_json.get("typography_dna", {}),
                "component_motifs": template.analysis_json.get("component_motifs", {}),
                "infographic_elements": template.analysis_json.get("infographic_elements", {}),
                "layout_dna": template.analysis_json.get("layout_dna", {}),
                "composition_logic": template.analysis_json.get("composition_logic", {}),
                "visual_craft_dna": template.analysis_json.get("visual_craft_dna", {}),
                "subject_semantics": template.analysis_json.get("subject_semantics", {}),
                "logo_anchor": template.analysis_json.get("logo_anchor", ""),
                "visual_mood": template.analysis_json.get("visual_mood", ""),
                "design_style": template.analysis_json.get("design_style", ""),
                "composition_style": template.analysis_json.get("composition_style", ""),
                "editorial_dna": template.analysis_json.get("editorial_dna", {}),
                "surface_kind": template.analysis_json.get("surface_kind"),
                "text_overlay_risk": template.analysis_json.get("text_overlay_risk"),
                "overlay_safe": template.analysis_json.get("overlay_safe"),
            }
            metadata.sizing_rules = {
                "width": width,
                "height": height,
                "page_count": page_count,
            }
            metadata.platform_rules = {
                "supported_platforms": vision.get("platform_hints", ["instagram", "linkedin", "x", "youtube_thumbnail"]),
                "analysis_status": "indexed",
            }
            metadata.editable_fields = self._editable_fields_from_zones(normalized_zones)
            metadata.export_rules = {"supported_formats": self._export_formats_for_template(absolute_path)}
        await self.session.commit()
        logger.info(
            "template.analyze.complete template_id=%s brand_space_id=%s layout_type=%s page_count=%s zone_count=%s style_map_count=%s gradient_count=%s surface_kind=%s text_overlay_risk=%s overlay_safe=%s",
            template.id,
            template.brand_space_id,
            template.analysis_json.get("layout_type"),
            page_count,
            len(template.analysis_json.get("zones", []) or []),
            len(template.analysis_json.get("text_style_map", []) or []),
            len(template.analysis_json.get("gradients", []) or []),
            template.analysis_json.get("surface_kind"),
            template.analysis_json.get("text_overlay_risk"),
            template.analysis_json.get("overlay_safe"),
        )
        return template

    async def list(self, tenant_id: UUID, brand_space_id: UUID) -> list[Template]:
        return await self.templates.list_by_brand(brand_space_id, tenant_id)

    async def recommend(
        self,
        tenant_id: UUID,
        brand_space_id: UUID,
        prompt: str,
        studio_panel: dict,
        brand_context: dict[str, Any] | None = None,
        limit: int = 5,
    ) -> list[TemplateRecommendationResponse]:
        resolved_panel = resolve_studio_panel_defaults(studio_panel)
        requested_format_family = self._normalize_format_family(resolved_panel.get("format"))
        requested_role_flags = self._requested_template_role_flags(resolved_panel)
        requested_roles = [role for role, _fallback_used in requested_role_flags]
        fallback_by_role = {role: fallback_used for role, fallback_used in requested_role_flags}
        requested_template_ids = {
            role: SLIDE_ROLE_TEMPLATE_MAP[role]
            for role in requested_roles
            if role in SLIDE_ROLE_TEMPLATE_MAP
        }
        templates = await self.templates.list_by_brand(brand_space_id, tenant_id)
        deterministic_recommendations: list[TemplateRecommendationResponse] = []
        for template in templates:
            metadata = await self.metadata.get_by_template(template.id)
            logical_template_id = self._logical_template_id_for_template(template, metadata)
            if not logical_template_id:
                continue
            matching_roles = [
                role
                for role, expected_template_id in requested_template_ids.items()
                if expected_template_id == logical_template_id
            ]
            if not matching_roles:
                continue
            template_profile = self._template_profile(template, metadata)
            matcher = template.matcher_features_json or {}
            slide_role = matching_roles[0]
            role_rank = min(requested_roles.index(role) for role in matching_roles if role in requested_roles)
            signature = self._sequence_recommendation_signature(template.name) or self._sequence_recommendation_signature(template.storage_path)
            recommendation_group_key = signature[0] if signature else ""
            sequence_position = signature[1] if signature else 0
            score = float(100 - role_rank)
            adaptation_plan = {
                "deterministic_template_id": logical_template_id,
                "slide_role": slide_role,
            }
            template_fallback_used = bool(fallback_by_role.get(slide_role, False))
            deterministic_recommendations.append(
                TemplateRecommendationResponse(
                    template_id=template.id,
                    name=template.name,
                    display_name=template.name,
                    asset_url=self.asset_delivery.build_signed_url(
                        storage_path=template.storage_path,
                        filename=Path(template.storage_path).name,
                    ),
                    score=score,
                    match_type="exact_template",
                    decision_confidence=1.0,
                    format_family=str(template_profile.get("format_family") or ""),
                    is_primary_adaptation=role_rank == 0,
                    selection_reason="Deterministic Rule Match",
                    recommendation_group_key=recommendation_group_key or None,
                    reasons=[
                        f"Deterministic template rule: {slide_role} -> {logical_template_id}",
                    ],
                    score_breakdown={
                        "deterministic_rule_match": 1.0,
                        "role_rank": float(role_rank),
                    },
                    adaptation_plan=adaptation_plan,
                    metadata={
                        "deterministic_template_id": logical_template_id,
                        "slide_role": slide_role,
                        "template_fallback_used": template_fallback_used,
                        "kind": template.kind,
                        "tags": template.tags,
                        "supported_platforms": metadata.platform_rules.get("supported_platforms", []) if metadata else [],
                        "supported_exports": metadata.export_rules.get("supported_formats", []) if metadata else [],
                        "editable_fields": metadata.editable_fields if metadata else [],
                        "format_family": template_profile.get("format_family"),
                        "adaptation_score": score,
                        "page_count": int(template_profile.get("page_count") or 0),
                        "layout_type": template_profile.get("layout_type"),
                        "sequence_family": recommendation_group_key or None,
                        "sequence_position": sequence_position or None,
                        "surface_kind": matcher.get("surface_kind") or template.analysis_json.get("surface_kind"),
                        "text_overlay_risk": matcher.get("text_overlay_risk") or template.analysis_json.get("text_overlay_risk"),
                        "overlay_safe": bool(
                            matcher.get(
                                "overlay_safe",
                                template.analysis_json.get("overlay_safe", True),
                            )
                        ),
                    },
                )
            )
        deterministic_recommendations.sort(
            key=lambda item: (
                requested_roles.index(str(item.metadata.get("slide_role") or "hook"))
                if str(item.metadata.get("slide_role") or "hook") in requested_roles
                else len(requested_roles),
                -float(item.score or 0.0),
            )
        )
        logger.info(
            "template.recommend.deterministic brand_space_id=%s prompt_chars=%s platform=%s format=%s roles=%s mapping=%s candidate_count=%s recommendations=%s",
            brand_space_id,
            len(prompt or ""),
            resolved_panel.get("platform_preset"),
            resolved_panel.get("format"),
            requested_roles,
            requested_template_ids,
            len(templates),
            [
                {
                    "template_id": item.template_id,
                    "name": item.name,
                    "deterministic_template_id": item.metadata.get("deterministic_template_id"),
                    "slide_role": item.metadata.get("slide_role"),
                    "template_fallback_used": item.metadata.get("template_fallback_used"),
                }
                for item in deterministic_recommendations[:limit]
            ],
        )
        return deterministic_recommendations[:limit]

    async def detail(self, tenant_id: UUID, brand_space_id: UUID, template_id: UUID) -> tuple[Template, TemplateMetadata | None]:
        template = await self.templates.get_scoped(template_id, tenant_id, brand_space_id)
        if not template:
            raise NotFoundError("Template not found")
        metadata = await self.metadata.get_by_template(template_id)
        return template, metadata

    async def update_metadata(
        self,
        tenant_id: UUID,
        brand_space_id: UUID,
        template_id: UUID,
        payload: TemplateMetadataUpsertRequest,
    ) -> TemplateMetadata:
        template = await self.templates.get_scoped(template_id, tenant_id, brand_space_id)
        if not template:
            raise NotFoundError("Template not found")
        metadata = await self.metadata.get_by_template(template_id)
        if not metadata:
            raise NotFoundError("Template metadata not found")
        metadata.zone_map = payload.zone_map
        metadata.sizing_rules = payload.sizing_rules
        metadata.platform_rules = payload.platform_rules
        metadata.editable_fields = payload.editable_fields
        metadata.export_rules = payload.export_rules
        await self.session.commit()
        return metadata

    async def delete(self, tenant_id: UUID, brand_space_id: UUID, template_id: UUID) -> None:
        template = await self.templates.get_scoped(template_id, tenant_id, brand_space_id)
        if not template:
            raise NotFoundError("Template not found")
        self.storage.delete(template.storage_path)
        await self.templates.delete(template)
        await self.session.commit()
