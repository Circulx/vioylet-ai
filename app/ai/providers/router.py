from __future__ import annotations

from app.ai.providers.anthropic_provider import AnthropicTextProvider
from app.ai.providers.base import ImageGenerationBackend, TextGenerationProvider
from app.ai.providers.image_generation import ImageGenerationProvider
from app.ai.providers.openai_provider import OpenAIImageProvider, OpenAITextProvider
from app.core.config import get_settings


class ProviderRouter:
    # Creates configured text and image providers behind one lookup surface.
    # The orchestrator asks for capabilities here instead of depending directly on OpenAI or Anthropic classes.
    def __init__(self) -> None:
        # Initializes settings, clients, and helper services needed by orchestrator provider lookup.
        # Public methods reuse these collaborators instead of rebuilding them for each request.
        self.settings = get_settings()
        self.text_providers: dict[str, TextGenerationProvider] = {
            "openai": OpenAITextProvider(),
            "anthropic": AnthropicTextProvider(),
        }
        self.image_providers: dict[str, ImageGenerationBackend] = {
            "openai": OpenAIImageProvider(),
            "mock": ImageGenerationProvider(),
        }

    def get_text_provider(self, purpose: str) -> TextGenerationProvider:
        # Extracts text provider from purpose for orchestrator provider lookup.
        # Later planning can reuse the structured value instead of scanning the source again.
        preferred = self.settings.research_provider if purpose == "research" else self.settings.text_provider
        fallback = self.settings.fallback_text_provider
        provider = self.text_providers.get(preferred)
        if provider and getattr(provider, "client", True):
            return provider
        # Missing API clients fall back silently so local/dev runs can still complete with the configured backup.
        return self.text_providers[fallback]

    def get_image_provider(self) -> ImageGenerationBackend:
        # Centralizes image provider for orchestrator provider lookup.
        # The main branch stays readable while this function handles the local edge case.
        preferred = self.image_providers.get(self.settings.image_provider)
        if preferred and getattr(preferred, "client", True):
            return preferred
        # Image generation follows the same routing contract as text providers.
        return self.image_providers[self.settings.fallback_image_provider]
