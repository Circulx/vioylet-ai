from __future__ import annotations

import json
import logging
from typing import Any

from app.ai.providers.base import PromptEnvelope, TextGenerationProvider
from app.core.config import get_settings


logger = logging.getLogger(__name__)


class AnthropicTextProvider(TextGenerationProvider):
    # Wraps Anthropic text generation behind the shared TextGenerationProvider interface.
    # ProviderRouter can swap this adapter into JSON or plain-text flows without changing orchestration code.
    provider_name = "anthropic"

    def __init__(self) -> None:
        # Initializes settings, clients, and helper services needed by provider routing.
        # Public methods reuse these collaborators instead of rebuilding them for each request.
        self.settings = get_settings()
        self.client = None
        if self.settings.anthropic_api_key:
            try:
                from anthropic import Anthropic

                self.client = Anthropic(api_key=self.settings.anthropic_api_key)
            except Exception:  # noqa: BLE001
                self.client = None

    def generate_structured_json(self, envelope: PromptEnvelope, fallback: dict[str, Any]) -> dict[str, Any]:
        # Generates structured json from prompt envelope and fallback payload for provider routing.
        # The helper owns a small rule that would distract from the surrounding flow.
        if not self.client:
            return fallback
        try:
            response = self.client.messages.create(
                model=self.settings.anthropic_model,
                system=envelope.system,
                max_tokens=1200,
                messages=[{"role": "user", "content": f"{envelope.user}\n\nReturn JSON only."}],
            )
            text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Anthropic structured generation failed, using fallback: %s", exc)
            return fallback
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Anthropic can occasionally return prose despite the instruction, so callers keep their deterministic fallback.
            return fallback

    def generate_text(self, envelope: PromptEnvelope, fallback: str) -> str:
        # Generates text from prompt envelope and fallback payload for provider routing.
        # The helper owns a small rule that would distract from the surrounding flow.
        if not self.client:
            return fallback
        try:
            response = self.client.messages.create(
                model=self.settings.anthropic_model,
                system=envelope.system,
                max_tokens=1200,
                messages=[{"role": "user", "content": envelope.user}],
            )
            text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Anthropic text generation failed, using fallback: %s", exc)
            return fallback
        # Empty provider text is treated like a failure so orchestration always receives usable content.
        return text or fallback
