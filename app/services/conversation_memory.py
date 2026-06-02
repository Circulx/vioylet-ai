from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
import hashlib
from math import isfinite
import logging
import re
from typing import Any
from uuid import UUID

from app.ai.providers.base import PromptEnvelope
from app.ai.providers.router import ProviderRouter
from app.core.enums import AssetRole
from app.integrations.object_storage import LocalObjectStorage
from app.integrations.vector_store import FaissVectorStoreProvider, SearchResult
from app.models.content import ChatMessage, ContentSession, ContentVersion, GeneratedAsset
from app.models.memory import ConversationMemoryEntry
from app.repositories.content import AssetRepository
from app.repositories.memory import ConversationMemoryRepository
from app.services.asset_delivery import AssetDeliveryService


logger = logging.getLogger(__name__)


class ConversationMemoryService:
    IMAGE_ASSET_ROLES = {
        AssetRole.AI_IMAGE,
        AssetRole.RENDER_PREVIEW,
        AssetRole.RENDER_EXPORT,
    }
    QUERY_STOPWORDS = {
        "a",
        "an",
        "and",
        "for",
        "from",
        "i",
        "in",
        "is",
        "it",
        "me",
        "of",
        "on",
        "our",
        "please",
        "the",
        "to",
        "we",
    }
    TOKEN_PATTERN = re.compile(r"[a-z0-9']+")
    SLIDE_NUMBER_PATTERNS = (
        re.compile(r"(?:^|[/_.-])(?:slide|page)[_.-]?(\d{1,3})(?=\D*$)", re.IGNORECASE),
        re.compile(r"(?:^|[/_.-])(\d{1,3})(?=\D*$)", re.IGNORECASE),
    )

    def __init__(self, session) -> None:
        self.session = session
        self.entries = ConversationMemoryRepository(session)
        self.assets = AssetRepository(session)
        self.vectors = FaissVectorStoreProvider()
        self.providers = ProviderRouter()
        self.delivery = AssetDeliveryService()
        self.storage = LocalObjectStorage()

    @staticmethod
    def _namespace(tenant_id: UUID, brand_space_id: UUID) -> str:
        return FaissVectorStoreProvider().namespace(
            str(tenant_id),
            str(brand_space_id),
            "conversation_memory",
        )

    @staticmethod
    def _clean_text(value: Any, *, limit: int | None = None) -> str:
        text = " ".join(str(value or "").split()).strip()
        if limit is None or len(text) <= limit:
            return text
        return text[:limit].rstrip(" ,.;:")

    @classmethod
    def _tokens(cls, value: str | None) -> set[str]:
        return {
            token
            for token in cls.TOKEN_PATTERN.findall(str(value or "").casefold())
            if len(token) > 2 and token not in cls.QUERY_STOPWORDS
        }

    @staticmethod
    def _isoformat(value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _search_score(result: SearchResult | None) -> float:
        if result is None:
            return 0.0
        score = float(result.score)
        if not isfinite(score):
            return 0.0
        return 1.0 / (1.0 + max(score, 0.0))

    @classmethod
    def _overlap_score(cls, query: str, memory_text: str) -> float:
        query_tokens = cls._tokens(query)
        if not query_tokens:
            return 0.0
        overlap = query_tokens & cls._tokens(memory_text)
        if not overlap:
            return 0.0
        return len(overlap) / max(len(query_tokens), 1)

    @staticmethod
    def _recency_score(*, position: int, total: int) -> float:
        if total <= 1:
            return 1.0
        return 1.0 - (position / max(total - 1, 1))

    def _llm_select_candidate_indexes(
        self,
        *,
        query: str,
        candidates: list[dict[str, Any]],
        limit: int,
    ) -> dict[str, Any] | None:
        provider = self.providers.get_text_provider("generation")
        fallback = {
            "selected_indexes": [],
            "reason": "provider_unavailable",
            "selection_state": "provider_unavailable",
        }
        try:
            response = provider.generate_structured_json(
                PromptEnvelope(
                    system=(
                        "You choose which previously generated images are most relevant to the user's retrieval request. "
                        "Return JSON only. "
                        "The candidates are ordered from newest to oldest. "
                        "Use the user's wording semantically, including references like previous, last, first, earlier, same, that one, or topic/style cues. "
                        "If the user is clearly asking for the last or latest generated image without extra topic/entity qualifiers, "
                        "prefer selecting a single best newest candidate and mark selection_state as generic_recency. "
                        "If the request is ambiguous or could match multiple prior images, you may return up to the requested limit so the user can choose in the frontend. "
                        "Select up to the requested limit of candidate indexes. "
                        "Do not invent indexes. "
                        "Prefer exact semantic matches when available. "
                        "If the query includes specific topical, entity, or subject cues and none of the candidates match them, "
                        "return no indexes and mark selection_state as no_relevant_match. "
                        "Do not select an unrelated image just because it is the newest one."
                    ),
                    user=(
                        f"User query: {query}\n"
                        f"Selection limit: {limit}\n"
                        f"Candidates: {candidates}\n"
                        "Return a JSON object with keys: selected_indexes, reason, selection_state. "
                        "selection_state must be one of: match_found, generic_recency, no_relevant_match."
                    ),
                ),
                fallback=fallback,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("conversation_memory.llm_selection_failed: %s", exc)
            return None

        raw_indexes = response.get("selected_indexes")
        if not isinstance(raw_indexes, list):
            return None
        selected: list[int] = []
        seen: set[int] = set()
        for value in raw_indexes:
            try:
                index = int(value)
            except (TypeError, ValueError):
                continue
            if index < 0 or index >= len(candidates) or index in seen:
                continue
            seen.add(index)
            selected.append(index)
            if len(selected) >= limit:
                break
        selection_state = self._clean_text(response.get("selection_state"), limit=40).lower() or "match_found"
        return {
            "selected_indexes": selected,
            "reason": self._clean_text(response.get("reason"), limit=240),
            "selection_state": selection_state,
        }

    def _llm_describe_selected_asset(
        self,
        *,
        query: str,
        candidate: dict[str, Any],
        fallback: str,
    ) -> str:
        provider = self.providers.get_text_provider("generation")
        try:
            response = provider.generate_text(
                PromptEnvelope(
                    system=(
                        "You answer a user's question about a previously generated image using only the provided memory summary. "
                        "Do not evaluate tone, score the asset, or give compliance feedback unless the user explicitly asks for evaluation. "
                        "Never say you cannot display, show, open, or render the image; the application handles image display separately. "
                        "Describe what the image is about in a concise, helpful way based on the remembered prompt, headline, body, CTA, format, and platform. "
                        "If the memory is incomplete, say what is known from the saved generation context."
                    ),
                    user=(
                        f"User query: {query}\n"
                        f"Selected image candidate: {candidate}\n"
                        "Answer the user's question in 1-3 short sentences."
                    ),
                ),
                fallback=fallback,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("conversation_memory.llm_description_failed: %s", exc)
            return fallback
        sanitized = self._remove_display_inability_claims(response)
        return self._clean_text(sanitized, limit=600) or fallback

    @classmethod
    def _remove_display_inability_claims(cls, value: str | None) -> str:
        text = str(value or "")
        text = re.sub(
            r"\b(?:unfortunately|sorry|however)?,?\s*(?:i\s+)?(?:can(?:not|'t)|am unable to)\s+"
            r"(?:display|show|open|render)\s+(?:the\s+)?(?:image|asset|visual)(?:\s+itself)?(?:,?\s*but\s*)?",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = cls._clean_text(text, limit=600)
        if text:
            return text[0].upper() + text[1:]
        return text

    @classmethod
    def _message_memory_text(cls, message: ChatMessage, session: ContentSession) -> str:
        payload = message.structured_payload or {}
        mode = cls._clean_text(payload.get("mode") or payload.get("intent_mode"), limit=40)
        assistant_assets = payload.get("assets") if isinstance(payload.get("assets"), list) else []
        asset_summary = ""
        if assistant_assets:
            asset_roles = [
                cls._clean_text(item.get("asset_role"), limit=40)
                for item in assistant_assets
                if isinstance(item, dict) and cls._clean_text(item.get("asset_role"), limit=40)
            ]
            if asset_roles:
                asset_summary = f" Assets: {', '.join(asset_roles[:4])}."
        return cls._clean_text(
            (
                f"Conversation {message.role} message in session '{session.title or 'Chat Session'}'. "
                f"Mode: {mode or 'conversation'}. "
                f"Message: {message.message_text}.{asset_summary}"
            ),
            limit=4000,
        )

    @classmethod
    def _content_memory_text(cls, content_version: ContentVersion, session: ContentSession) -> str:
        payload = content_version.generated_payload or {}
        headline = cls._clean_text(payload.get("headline"), limit=220)
        body = cls._clean_text(payload.get("body"), limit=420)
        cta = cls._clean_text(payload.get("cta"), limit=120)
        return cls._clean_text(
            (
                f"Generated content summary for session '{session.title or 'Chat Session'}'. "
                f"Prompt: {content_version.prompt}. "
                f"Headline: {headline}. "
                f"Body: {body}. "
                f"CTA: {cta}. "
                f"Format: {cls._clean_text((content_version.studio_panel or {}).get('format'), limit=40)}."
            ),
            limit=4000,
        )

    @classmethod
    def _asset_memory_text(
        cls,
        *,
        asset: GeneratedAsset,
        content_version: ContentVersion,
        session: ContentSession,
    ) -> str:
        payload = content_version.generated_payload or {}
        headline = cls._clean_text(payload.get("headline"), limit=220)
        body = cls._clean_text(payload.get("body"), limit=320)
        cta = cls._clean_text(payload.get("cta"), limit=120)
        format_name = cls._clean_text((content_version.studio_panel or {}).get("format"), limit=40)
        platform = cls._clean_text((content_version.studio_panel or {}).get("platform_preset"), limit=40)
        return cls._clean_text(
            (
                f"Generated image asset for session '{session.title or 'Chat Session'}'. "
                f"Prompt: {content_version.prompt}. "
                f"Headline: {headline}. "
                f"Body: {body}. "
                f"CTA: {cta}. "
                f"Format: {format_name}. "
                f"Platform: {platform}. "
                f"Asset role: {asset.asset_role}. "
                f"Asset address: {asset.storage_path}."
            ),
            limit=4000,
        )

    @classmethod
    def _displayed_asset_memory_text(
        cls,
        *,
        asset: dict[str, Any],
        content_version: ContentVersion,
        session: ContentSession,
    ) -> str:
        payload = content_version.generated_payload or {}
        headline = cls._clean_text(payload.get("headline"), limit=220)
        body = cls._clean_text(payload.get("body"), limit=320)
        cta = cls._clean_text(payload.get("cta"), limit=120)
        format_name = cls._clean_text((content_version.studio_panel or {}).get("format"), limit=40)
        platform = cls._clean_text((content_version.studio_panel or {}).get("platform_preset"), limit=40)
        storage_path = cls._clean_text(asset.get("storage_path"), limit=512)
        return cls._clean_text(
            (
                f"Final displayed image asset for session '{session.title or 'Chat Session'}'. "
                f"Prompt: {content_version.prompt}. "
                f"Headline: {headline}. "
                f"Body: {body}. "
                f"CTA: {cta}. "
                f"Format: {format_name}. "
                f"Platform: {platform}. "
                f"Asset role: {asset.get('asset_role')}. "
                f"Asset address: {storage_path}."
            ),
            limit=4000,
        )

    async def _upsert_entry(
        self,
        *,
        tenant_id: UUID,
        brand_space_id: UUID,
        session_id: UUID,
        source_key: str,
        entry_type: str,
        memory_text: str,
        role: str | None = None,
        chat_message_id: UUID | None = None,
        content_version_id: UUID | None = None,
        generated_asset_id: UUID | None = None,
        storage_path: str | None = None,
        asset_role: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> ConversationMemoryEntry:
        entry = await self.entries.get_by_source_key(source_key)
        if entry is None:
            entry = ConversationMemoryEntry(
                tenant_id=tenant_id,
                brand_space_id=brand_space_id,
                session_id=session_id,
                source_key=source_key,
                entry_type=entry_type,
                memory_text=memory_text,
                role=role,
                chat_message_id=chat_message_id,
                content_version_id=content_version_id,
                generated_asset_id=generated_asset_id,
                storage_path=storage_path,
                asset_role=asset_role,
                metadata_json=metadata_json or {},
            )
            await self.entries.add(entry)
        else:
            entry.entry_type = entry_type
            entry.memory_text = memory_text
            entry.role = role
            entry.chat_message_id = chat_message_id
            entry.content_version_id = content_version_id
            entry.generated_asset_id = generated_asset_id
            entry.storage_path = storage_path
            entry.asset_role = asset_role
            entry.metadata_json = metadata_json or {}
            await self.session.flush()
            await self.session.refresh(entry)

        namespace = self._namespace(tenant_id, brand_space_id)
        self.vectors.upsert_documents(
            namespace,
            [
                {
                    "content": memory_text,
                    "metadata": {
                        "chunk_id": str(entry.id),
                        "source_id": source_key,
                        "entry_type": entry_type,
                        "session_id": str(session_id),
                        "chat_message_id": str(chat_message_id) if chat_message_id else "",
                        "content_version_id": str(content_version_id) if content_version_id else "",
                        "generated_asset_id": str(generated_asset_id) if generated_asset_id else "",
                        "storage_path": storage_path or "",
                        "asset_role": asset_role or "",
                        "created_at": self._isoformat(entry.created_at) or "",
                    },
                }
            ],
        )
        return entry

    async def index_chat_message(self, *, message: ChatMessage, session: ContentSession) -> ConversationMemoryEntry:
        return await self._upsert_entry(
            tenant_id=message.tenant_id,
            brand_space_id=message.brand_space_id,
            session_id=message.session_id,
            source_key=f"chat_message:{message.id}",
            entry_type="chat_message",
            role=message.role,
            chat_message_id=message.id,
            memory_text=self._message_memory_text(message, session),
            metadata_json={
                "mode": self._clean_text((message.structured_payload or {}).get("mode"), limit=40),
                "content_version_id": str(message.content_version_id) if message.content_version_id else None,
            },
        )

    async def index_content_version_summary(
        self,
        *,
        session: ContentSession,
        content_version: ContentVersion,
    ) -> ConversationMemoryEntry:
        return await self._upsert_entry(
            tenant_id=content_version.tenant_id,
            brand_space_id=content_version.brand_space_id,
            session_id=content_version.session_id,
            source_key=f"content_version:{content_version.id}",
            entry_type="generated_content",
            content_version_id=content_version.id,
            memory_text=self._content_memory_text(content_version, session),
            metadata_json={
                "format": self._clean_text((content_version.studio_panel or {}).get("format"), limit=40),
                "platform": self._clean_text((content_version.studio_panel or {}).get("platform_preset"), limit=40),
            },
        )

    async def index_generated_assets(
        self,
        *,
        session: ContentSession,
        content_version: ContentVersion,
        assets: Iterable[GeneratedAsset | dict[str, Any]],
    ) -> list[ConversationMemoryEntry]:
        indexed: list[ConversationMemoryEntry] = []
        for asset in assets:
            if isinstance(asset, dict):
                storage_path = self._clean_text(asset.get("storage_path"), limit=512)
                if not storage_path:
                    continue
                metadata = {}
                if isinstance(asset.get("metadata_json"), dict):
                    metadata.update(asset["metadata_json"])
                if isinstance(asset.get("metadata"), dict):
                    metadata.update(asset["metadata"])
                mime_type = self._clean_text(asset.get("mime_type") or metadata.get("mime_type"), limit=120) or "image/png"
                if not mime_type.startswith("image/"):
                    continue
                asset_role = self._clean_text(
                    asset.get("asset_role") or metadata.get("asset_role") or AssetRole.RENDER_EXPORT.value,
                    limit=100,
                )
                if asset_role not in {role.value for role in self.IMAGE_ASSET_ROLES}:
                    continue
                width = asset.get("width", metadata.get("width"))
                height = asset.get("height", metadata.get("height"))
                metadata_json = {
                    **metadata,
                    "mime_type": mime_type,
                    "width": width,
                    "height": height,
                    "asset_role": asset_role,
                    "storage_path": storage_path,
                    "displayed_asset": True,
                    "source": "render_payload",
                }
                source_digest = hashlib.sha1(f"{storage_path}:{asset_role}".encode("utf-8")).hexdigest()[:16]
                indexed.append(
                    await self._upsert_entry(
                        tenant_id=content_version.tenant_id,
                        brand_space_id=content_version.brand_space_id,
                        session_id=content_version.session_id,
                        source_key=f"displayed_asset:{content_version.id}:{source_digest}",
                        entry_type="generated_image",
                        content_version_id=content_version.id,
                        generated_asset_id=None,
                        storage_path=storage_path,
                        asset_role=asset_role,
                        memory_text=self._displayed_asset_memory_text(
                            asset={**asset, "storage_path": storage_path, "asset_role": asset_role},
                            content_version=content_version,
                            session=session,
                        ),
                        metadata_json=metadata_json,
                    )
                )
                continue

            if not str(asset.mime_type or "").startswith("image/"):
                continue
            if str(asset.asset_role) not in {role.value for role in self.IMAGE_ASSET_ROLES}:
                continue
            indexed.append(
                await self._upsert_entry(
                    tenant_id=asset.tenant_id,
                    brand_space_id=asset.brand_space_id,
                    session_id=content_version.session_id,
                    source_key=f"generated_asset:{asset.id}",
                    entry_type="generated_image",
                    content_version_id=content_version.id,
                    generated_asset_id=asset.id,
                    storage_path=asset.storage_path,
                    asset_role=str(asset.asset_role),
                    memory_text=self._asset_memory_text(
                        asset=asset,
                        content_version=content_version,
                        session=session,
                    ),
                    metadata_json={
                        "mime_type": asset.mime_type,
                        "width": asset.width,
                        "height": asset.height,
                        "asset_role": str(asset.asset_role),
                        "storage_path": asset.storage_path,
                    },
                )
            )
        return indexed

    def _serialize_entry_asset(self, entry: ConversationMemoryEntry) -> dict[str, Any] | None:
        storage_path = self._clean_text(entry.storage_path, limit=512)
        if not storage_path or not self.storage.exists(storage_path):
            return None
        metadata = entry.metadata_json or {}
        displayed_asset = bool(metadata.get("displayed_asset"))
        return {
            "asset_id": str(entry.generated_asset_id) if entry.generated_asset_id else None,
            "content_version_id": str(entry.content_version_id) if entry.content_version_id else None,
            "mime_type": self._clean_text(metadata.get("mime_type"), limit=120) or "image/png",
            "storage_path": storage_path,
            "asset_url": self.delivery.build_signed_url(
                storage_path=storage_path,
                filename=storage_path.rsplit("/", 1)[-1],
            ),
            "width": metadata.get("width"),
            "height": metadata.get("height"),
            "asset_role": self._clean_text(entry.asset_role, limit=100) or AssetRole.AI_IMAGE.value,
            "memory_entry_id": str(entry.id),
            "memory_text": self._clean_text(entry.memory_text, limit=240),
            "displayed_asset": displayed_asset,
            "metadata": metadata,
            "slide_index": metadata.get("slide_index")
            or metadata.get("page_index")
            or metadata.get("page_number")
            or metadata.get("reference_slide_index"),
        }

    def _serialize_generated_asset(self, asset: GeneratedAsset) -> dict[str, Any] | None:
        storage_path = self._clean_text(asset.storage_path, limit=512)
        if not storage_path or not self.storage.exists(storage_path):
            return None
        return {
            "asset_id": str(asset.id),
            "content_version_id": str(asset.content_version_id) if asset.content_version_id else None,
            "mime_type": self._clean_text(asset.mime_type, limit=120) or "image/png",
            "storage_path": storage_path,
            "asset_url": self.delivery.build_signed_url(
                storage_path=storage_path,
                filename=storage_path.rsplit("/", 1)[-1],
            ),
            "width": asset.width,
            "height": asset.height,
            "asset_role": self._clean_text(asset.asset_role, limit=100) or AssetRole.AI_IMAGE.value,
            "memory_entry_id": None,
            "memory_text": None,
        }

    @classmethod
    def _asset_slide_index(cls, asset: GeneratedAsset, *, fallback: int) -> int:
        metadata = asset.metadata_json or {}
        for key in ("slide_index", "page_index", "page_number", "reference_slide_index"):
            try:
                value = int(metadata.get(key) or 0)
            except (TypeError, ValueError):
                value = 0
            if value > 0:
                return value
        storage_path = str(asset.storage_path or "")
        for pattern in cls.SLIDE_NUMBER_PATTERNS:
            match = pattern.search(storage_path)
            if not match:
                continue
            try:
                value = int(match.group(1))
            except (TypeError, ValueError):
                value = 0
            if value > 0:
                return value
        return fallback

    @staticmethod
    def _asset_role_priority_value(role: str | None) -> int:
        role = str(role or "")
        if role == AssetRole.RENDER_PREVIEW.value:
            return 0
        if role == AssetRole.RENDER_EXPORT.value:
            return 1
        if role == AssetRole.AI_IMAGE.value:
            return 2
        return 3

    @classmethod
    def _asset_role_priority(cls, asset: GeneratedAsset) -> int:
        return cls._asset_role_priority_value(str(asset.asset_role or ""))

    @classmethod
    def _sorted_slide_assets(cls, assets: list[GeneratedAsset]) -> list[GeneratedAsset]:
        position_by_identity = {id(asset): index for index, asset in enumerate(assets, start=1)}
        return sorted(
            assets,
            key=lambda item: (
                cls._asset_slide_index(item, fallback=position_by_identity.get(id(item), 999)),
                cls._asset_role_priority(item),
                item.created_at,
                str(item.id),
            ),
        )

    @classmethod
    def _serialized_asset_slide_index(cls, asset: dict[str, Any], *, fallback: int) -> int:
        metadata = asset.get("metadata") if isinstance(asset.get("metadata"), dict) else {}
        for key in ("slide_index", "page_index", "page_number", "reference_slide_index"):
            try:
                value = int(asset.get(key) or metadata.get(key) or 0)
            except (TypeError, ValueError):
                value = 0
            if value > 0:
                return value
        storage_path = str(asset.get("storage_path") or "")
        for pattern in cls.SLIDE_NUMBER_PATTERNS:
            match = pattern.search(storage_path)
            if not match:
                continue
            try:
                value = int(match.group(1))
            except (TypeError, ValueError):
                value = 0
            if value > 0:
                return value
        return fallback

    @classmethod
    def _sorted_serialized_assets(cls, assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        position_by_identity = {id(asset): index for index, asset in enumerate(assets, start=1)}
        return sorted(
            assets,
            key=lambda item: (
                cls._serialized_asset_slide_index(item, fallback=position_by_identity.get(id(item), 999)),
                cls._asset_role_priority_value(str(item.get("asset_role") or "")),
                str(item.get("storage_path") or ""),
            ),
        )

    async def _expand_assets_for_content_version(self, asset: dict[str, Any]) -> list[dict[str, Any]]:
        content_version_id = asset.get("content_version_id")
        if not content_version_id:
            return [asset]
        try:
            assets = await self.assets.list_by_content(UUID(str(content_version_id)))
        except (TypeError, ValueError):
            return [asset]

        image_assets = [
            item
            for item in assets
            if str(item.mime_type or "").startswith("image/")
            and str(item.asset_role) in {role.value for role in self.IMAGE_ASSET_ROLES}
        ]
        if not image_assets:
            return [asset]

        render_exports = [item for item in image_assets if str(item.asset_role) == AssetRole.RENDER_EXPORT.value]
        final_render_assets = [
            item
            for item in image_assets
            if (item.metadata_json or {}).get("render_source") == "ai"
            and (item.metadata_json or {}).get("generation_stage") == "final_render"
        ]
        final_render_slide_count = max(
            [
                int((item.metadata_json or {}).get("slide_count") or 0)
                for item in final_render_assets
                if str((item.metadata_json or {}).get("slide_count") or "").strip().isdigit()
            ],
            default=0,
        )
        if final_render_assets and (final_render_slide_count > 1 or len(final_render_assets) > 1):
            preferred_assets = final_render_assets
        elif render_exports:
            preferred_assets = render_exports
        else:
            preferred_assets = image_assets
        preferred_assets = self._sorted_slide_assets(preferred_assets)

        expanded: list[dict[str, Any]] = []
        seen_storage_paths: set[str] = set()
        lead_memory_entry_id = asset.get("memory_entry_id")
        lead_memory_text = asset.get("memory_text")
        for item in preferred_assets:
            serialized = self._serialize_generated_asset(item)
            if not serialized:
                continue
            if serialized["storage_path"] in seen_storage_paths:
                continue
            seen_storage_paths.add(serialized["storage_path"])
            serialized["memory_entry_id"] = lead_memory_entry_id
            serialized["memory_text"] = lead_memory_text
            expanded.append(serialized)
        return expanded or [asset]

    async def _expand_selected_asset(
        self,
        asset: dict[str, Any],
        *,
        displayed_assets_by_content_version: dict[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        content_version_id = str(asset.get("content_version_id") or "").strip()
        displayed_assets = displayed_assets_by_content_version.get(content_version_id)
        if displayed_assets:
            return displayed_assets
        return await self._expand_assets_for_content_version(asset)

    @staticmethod
    def _selection_option_for_asset(asset: dict[str, Any], *, rank: int) -> dict[str, Any]:
        return {
            "rank": rank,
            "asset_id": asset.get("asset_id"),
            "content_version_id": asset.get("content_version_id"),
            "memory_entry_id": asset.get("memory_entry_id"),
            "asset_url": asset.get("asset_url"),
            "storage_path": asset.get("storage_path"),
            "label": f"Option {rank}",
            "summary": asset.get("memory_text"),
            "asset_role": asset.get("asset_role"),
            "width": asset.get("width"),
            "height": asset.get("height"),
        }

    async def retrieve_image_assets(
        self,
        *,
        tenant_id: UUID,
        brand_space_id: UUID,
        session_id: UUID,
        query: str,
        limit: int = 3,
    ) -> dict[str, Any]:
        entries = await self.entries.list_image_entries(
            tenant_id=tenant_id,
            brand_space_id=brand_space_id,
            session_id=session_id,
            limit=max(limit * 10, 40),
        )
        if not entries:
            return {
                "status": "not_found",
                "message": "I couldn't find any previously generated images in this conversation yet.",
                "assets": [],
                "matched_entries": [],
            }

        query_text = self._clean_text(query, limit=600)
        namespace = self._namespace(tenant_id, brand_space_id)
        search_results = self.vectors.search(namespace, query_text, k=max(limit * 4, 12))
        search_by_entry_id: dict[str, SearchResult] = {}
        for result in search_results:
            entry_id = str(result.metadata.get("chunk_id") or "").strip()
            if entry_id:
                search_by_entry_id[entry_id] = result

        scored_entries: list[tuple[float, float, ConversationMemoryEntry]] = []
        total = len(entries)
        for position, entry in enumerate(entries):
            search_result = search_by_entry_id.get(str(entry.id))
            vector_score = self._search_score(search_result)
            overlap_score = self._overlap_score(query_text, entry.memory_text)
            score = 0.0
            score += vector_score * 0.7
            score += overlap_score * 0.25
            score += self._recency_score(position=position, total=total) * 0.05
            scored_entries.append((score, overlap_score, entry))

        scored_entries.sort(key=lambda item: (-item[0], item[2].created_at))
        candidate_pool: list[dict[str, Any]] = []
        fallback_assets: list[dict[str, Any]] = []
        fallback_matches: list[dict[str, Any]] = []
        seen_storage_paths: set[str] = set()
        candidate_limit = max(limit * 4, 8)
        displayed_assets_by_content_version: dict[str, list[dict[str, Any]]] = {}
        displayed_storage_paths_by_content_version: dict[str, set[str]] = {}
        for score, overlap_score, entry in scored_entries:
            serialized = self._serialize_entry_asset(entry)
            if not serialized:
                continue
            if serialized.get("displayed_asset"):
                content_version_id = str(serialized.get("content_version_id") or "").strip()
                storage_path = str(serialized.get("storage_path") or "").strip()
                if content_version_id and storage_path:
                    seen_for_content = displayed_storage_paths_by_content_version.setdefault(content_version_id, set())
                    if storage_path not in seen_for_content:
                        seen_for_content.add(storage_path)
                        displayed_assets_by_content_version.setdefault(content_version_id, []).append(serialized)
            if len(candidate_pool) >= candidate_limit:
                continue
            if serialized["storage_path"] in seen_storage_paths:
                continue
            seen_storage_paths.add(serialized["storage_path"])
            fallback_assets.append(serialized)
            fallback_matches.append(
                {
                    "memory_entry_id": str(entry.id),
                    "storage_path": serialized["storage_path"],
                    "score": round(score, 4),
                    "overlap_score": round(overlap_score, 4),
                }
            )
            candidate_pool.append(
                {
                    "index": len(candidate_pool),
                    "memory_entry_id": str(entry.id),
                    "created_at": self._isoformat(entry.created_at),
                    "storage_path": serialized["storage_path"],
                    "asset_role": serialized["asset_role"],
                    "memory_text": self._clean_text(entry.memory_text, limit=320),
                    "fallback_score": round(score, 4),
                    "overlap_score": round(overlap_score, 4),
                }
            )

        for content_version_id, assets in displayed_assets_by_content_version.items():
            displayed_assets_by_content_version[content_version_id] = self._sorted_serialized_assets(assets)

        if not fallback_assets:
            return {
                "status": "not_found",
                "message": "I found conversation history, but none of the previous image addresses are available anymore.",
                "assets": [],
                "matched_entries": [],
            }

        selection_result = self._llm_select_candidate_indexes(
            query=query_text,
            candidates=candidate_pool,
            limit=limit,
        )
        if selection_result is not None:
            selected_indexes = selection_result.get("selected_indexes") or []
            selection_state = selection_result.get("selection_state")
        else:
            selected_indexes = []
            selection_state = None

        if selected_indexes:
            llm_assets: list[dict[str, Any]] = []
            llm_matches: list[dict[str, Any]] = []
            selected_candidates: list[dict[str, Any]] = []
            for index in selected_indexes:
                if index >= len(candidate_pool):
                    continue
                selected_candidate = candidate_pool[index]
                matched_asset = next(
                    (
                        asset
                        for asset in fallback_assets
                        if asset["memory_entry_id"] == selected_candidate["memory_entry_id"]
                    ),
                    None,
                )
                if matched_asset is None:
                    continue
                selected_candidates.append(selected_candidate)
                llm_assets.append(matched_asset)
                llm_matches.append(
                    {
                        "memory_entry_id": selected_candidate["memory_entry_id"],
                        "storage_path": selected_candidate["storage_path"],
                        "score": selected_candidate["fallback_score"],
                        "overlap_score": selected_candidate["overlap_score"],
                    }
                )
            if llm_assets:
                lead_candidate = selected_candidates[0] if selected_candidates else candidate_pool[0]
                expanded_assets = await self._expand_selected_asset(
                    llm_assets[0],
                    displayed_assets_by_content_version=displayed_assets_by_content_version,
                )
                descriptive_message = self._llm_describe_selected_asset(
                    query=query_text,
                    candidate=lead_candidate,
                    fallback="Here is the most relevant previously generated image from this conversation history.",
                )
                return {
                    "status": "found",
                    "message": descriptive_message,
                    "assets": expanded_assets,
                    "matched_entries": llm_matches,
                    "selected_asset": expanded_assets[0] if expanded_assets else None,
                    "selection_required": len(llm_assets) > 1,
                    "selection_prompt": (
                        "I found a few relevant previously generated images. Choose the one you want to use."
                        if len(llm_assets) > 1
                        else None
                    ),
                    "selection_options": [
                        self._selection_option_for_asset(asset, rank=index + 1)
                        for index, asset in enumerate(llm_assets, start=0)
                    ],
                }

        if selection_state == "no_relevant_match":
            return {
                "status": "not_found",
                "message": "I found previously generated images in this conversation, but none of them match that request closely enough.",
                "assets": [],
                "matched_entries": [],
                "selected_asset": None,
                "selection_required": False,
                "selection_prompt": None,
                "selection_options": [],
            }

        lead_candidate = candidate_pool[0] if candidate_pool else None
        lead_overlap = float(lead_candidate.get("overlap_score", 0.0)) if lead_candidate is not None else 0.0
        lead_score = float(lead_candidate.get("fallback_score", 0.0)) if lead_candidate is not None else 0.0
        if lead_candidate is None or (lead_overlap < 0.25 and lead_score < 0.35):
            return {
                "status": "not_found",
                "message": "I found previous image history, but nothing looked relevant enough to that request.",
                "assets": [],
                "matched_entries": [],
                "selected_asset": None,
                "selection_required": False,
                "selection_prompt": None,
                "selection_options": [],
            }
        fallback_message = "Here is the most relevant previously generated image from this conversation history."
        if lead_candidate is not None:
            fallback_message = self._llm_describe_selected_asset(
                query=query_text,
                candidate=lead_candidate,
                fallback=fallback_message,
            )
        expanded_fallback_assets = (
            await self._expand_selected_asset(
                fallback_assets[0],
                displayed_assets_by_content_version=displayed_assets_by_content_version,
            )
            if fallback_assets
            else []
        )
        return {
            "status": "found",
            "message": fallback_message,
            "assets": expanded_fallback_assets or fallback_assets[:limit],
            "matched_entries": fallback_matches[:limit],
            "selected_asset": (expanded_fallback_assets[0] if expanded_fallback_assets else fallback_assets[0]) if fallback_assets else None,
            "selection_required": len(fallback_assets[:limit]) > 1,
            "selection_prompt": (
                "I found a few relevant previously generated images. Choose the one you want to use."
                if len(fallback_assets[:limit]) > 1
                else None
            ),
            "selection_options": [
                self._selection_option_for_asset(asset, rank=index + 1)
                for index, asset in enumerate(fallback_assets[:limit], start=0)
            ],
        }
