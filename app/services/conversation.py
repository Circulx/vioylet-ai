from __future__ import annotations

from typing import Any

from app.ai.providers.base import PromptEnvelope
from app.ai.providers.router import ProviderRouter


class ConversationService:
    def __init__(self) -> None:
        self.providers = ProviderRouter()

    def reply(
        self,
        *,
        message: str,
        brand_name: str | None = None,
        session_context: dict[str, Any] | None = None,
        brand_summary: str | None = None,
        recent_messages: list[dict[str, str]] | None = None,
        mode: str = "small_talk",
    ) -> dict[str, Any]:
        recent_messages = recent_messages or []
        provider = self.providers.get_text_provider("generation")
        fallback = self._fallback_reply(message=message, brand_name=brand_name, mode=mode)
        reply_text = provider.generate_text(
            PromptEnvelope(
                system=(
                    "You are a conversational content copilot inside a brand-safe content studio. "
                    "Reply naturally like a thoughtful teammate. "
                    "Do not generate an image unless the user explicitly asks for one. "
                    "When the user is greeting you, greet them back and offer concise help. "
                    "When the user is exploring a strategy, stay conversational and practical. "
                    "Use the brand summary as the primary factual source for brand questions such as target audience, colors, tone, motivations, or positioning. "
                    "Use only the recent messages for conversational continuity. "
                    "If the brand summary does not contain a factual detail, say you do not have that detail yet instead of inventing it."
                ),
                user=(
                    f"Brand: {brand_name or 'the current brand'}\n"
                    f"Mode: {mode}\n"
                    f"Brand summary: {brand_summary or 'No brand summary available.'}\n"
                    f"Recent messages: {recent_messages}\n"
                    f"User message: {message}\n"
                    "Return only the assistant reply."
                ),
            ),
            fallback=fallback,
        )
        return {
            "message_text": reply_text.strip() or fallback,
            "structured_payload": {
                "mode": "conversation",
                "conversation_mode": mode,
                "brand_name": brand_name,
            },
        }

    @staticmethod
    def _fallback_reply(*, message: str, brand_name: str | None, mode: str) -> str:
        if mode == "small_talk":
            return (
                f"Hi! I'm ready to help with {brand_name or 'your brand'} content. "
                "You can ask me to brainstorm, write copy, review tone, or generate visuals."
            )
        return (
            "I can help you think this through. "
            "Tell me the channel, audience, and what outcome you want, and I'll shape the next step with you."
        )
