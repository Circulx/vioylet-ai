from __future__ import annotations

from app.services.llm.claude_service import ClaudeService
from app.services.llm.openai_service import OpenAIService


class LLMRouter:
    """Assigns the right model service per layer according to the blueprint."""

    # Keep Claude for strategy layers; use OpenAI for copy/blueprint to avoid
    # Claude adaptive-thinking timeouts (RetryError / APITimeoutError).
    CLAUDE_LAYERS = {
        "l2_brand_intelligence",
        "l4_strategic_reasoning",
        "l5_concept_engine",
        "l10_evaluation",
        "repair",
    }

    def __init__(self) -> None:
        self._claude = ClaudeService()
        self._openai = OpenAIService()

    def get_service(self, layer: str) -> ClaudeService | OpenAIService:
        if layer in self.CLAUDE_LAYERS:
            return self._claude
        return self._openai

    def assign(self, layer: str) -> str:
        if layer in self.CLAUDE_LAYERS:
            return "claude"
        return "openai"
