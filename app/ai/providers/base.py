from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class PromptEnvelope:
    # Groups prompt envelope behavior for provider contracts.
    # Callers use this class to produce or evaluate data consumed by adapter implementations.
    system: str
    user: str


class TextGenerationProvider(ABC):
    # Groups text generation provider behavior for provider contracts.
    # Callers use this class to produce or evaluate data consumed by adapter implementations.
    provider_name: str

    @abstractmethod
    def generate_structured_json(self, envelope: PromptEnvelope, fallback: dict[str, Any]) -> dict[str, Any]:
        # Generates structured json from prompt envelope and fallback payload for adapter implementations.
        # The main branch stays readable while this function handles the local edge case.
        raise NotImplementedError

    @abstractmethod
    def generate_text(self, envelope: PromptEnvelope, fallback: str) -> str:
        # Generates text from prompt envelope and fallback payload for adapter implementations.
        # The helper owns a small rule that would distract from the surrounding flow.
        raise NotImplementedError


class ImageGenerationBackend(ABC):
    # Groups image generation backend behavior for provider contracts.
    # Callers use this class to produce or evaluate data consumed by adapter implementations.
    provider_name: str

    @abstractmethod
    def generate(self, tenant_id, brand_space_id, prompt: str, size: str | None = None) -> dict[str, Any]:
        # Generates generate from tenant id, brand space id, and prompt text for adapter implementations.
        # The helper owns a small rule that would distract from the surrounding flow.
        raise NotImplementedError

    @abstractmethod
    def edit(
        self,
        tenant_id,
        brand_space_id,
        prompt: str,
        image_paths: list[str],
        size: str | None = None,
        mask_png_bytes: bytes | None = None,
    ) -> dict[str, Any]:
        # Centralizes edit from tenant id, brand space id, and prompt text for adapter implementations.
        # The main branch stays readable while this function handles the local edge case.
        raise NotImplementedError
