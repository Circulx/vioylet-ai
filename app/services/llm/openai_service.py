from __future__ import annotations

import time
from typing import Any, Type, TypeVar

from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class OpenAIService:
    """Async OpenAI client with retry, token tracking, and structured JSON output."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.openai_api_key
        self._model = model or settings.llm_model or "gpt-4o-mini"
        self._client: AsyncOpenAI | None = None
        if self._api_key:
            timeout = float(getattr(settings, "llm_request_timeout_seconds", 180.0) or 180.0)
            self._client = AsyncOpenAI(api_key=self._api_key, timeout=timeout)

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((OpenAIError,)),
        reraise=True,
    )
    async def complete_structured(
        self,
        system: str,
        user: str,
        output_model: Type[T],
        layer: str = "unknown",
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> tuple[T, dict[str, Any]]:
        """Return a validated Pydantic model plus metadata dict."""
        if not self._client:
            raise ValueError("OpenAI API key not configured")

        start = time.monotonic()
        logger.info("llm.request", model=self._model, layer=layer)

        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )

        latency_ms = int((time.monotonic() - start) * 1000)
        choice = response.choices[0]

        if choice.finish_reason == "length":
            logger.error("llm.truncated", model=self._model, layer=layer, max_tokens=max_tokens)
            raise OpenAIError(f"Output truncated at {max_tokens} tokens for {layer}")

        raw = choice.message.content or "{}"

        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0

        logger.info(
            "llm.response",
            model=self._model,
            layer=layer,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        parsed = output_model.model_validate_json(raw)

        metadata = {
            "layer": layer,
            "model": self._model,
            "latency_ms": latency_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
        return parsed, metadata

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((OpenAIError,)),
        reraise=True,
    )
    async def complete_text(
        self,
        system: str,
        user: str,
        layer: str = "unknown",
        temperature: float = 0.8,
        max_tokens: int = 4096,
    ) -> tuple[str, dict[str, Any]]:
        """Return plain text completion plus metadata dict. Used for prompt expansion."""
        if not self._client:
            raise ValueError("OpenAI API key not configured")

        start = time.monotonic()
        logger.info("llm.request", model=self._model, layer=layer)

        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )

        latency_ms = int((time.monotonic() - start) * 1000)
        choice = response.choices[0]

        if choice.finish_reason == "length":
            logger.error("llm.truncated", model=self._model, layer=layer, max_tokens=max_tokens)
            raise OpenAIError(f"Output truncated at {max_tokens} tokens for {layer}")

        text = choice.message.content or ""

        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0

        logger.info(
            "llm.response",
            model=self._model,
            layer=layer,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        metadata = {
            "layer": layer,
            "model": self._model,
            "latency_ms": latency_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
        return text, metadata
