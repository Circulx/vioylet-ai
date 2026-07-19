from __future__ import annotations

import json
import time
from typing import Any, Type, TypeVar

import anthropic
from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class TruncatedOutputError(Exception):
    """Raised when LLM output is truncated due to max_tokens limit."""
    pass


class ClaudeService:
    """Async Anthropic client with retry, token tracking, structured output validation,
    JSON fence stripping, and automatic fallback to claude-opus-4-5 on outage/rate-limit.

    Note: Claude Sonnet 4.6 uses adaptive thinking by default and rejects temperature,
    top_p, and top_k parameters. The `temperature` argument is accepted for interface
    parity with OpenAIService but is silently ignored.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        fallback_model: str | None = None,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.anthropic_api_key
        self._model = model or settings.anthropic_model
        self._fallback_model = fallback_model or settings.anthropic_fallback_model
        self._client: anthropic.AsyncAnthropic | None = None
        if self._api_key:
            self._client = anthropic.AsyncAnthropic(api_key=self._api_key)

    # ── JSON extraction ───────────────────────────────────────────────────────

    @staticmethod
    def _extract_json(raw: str) -> str:
        """Extract valid JSON from Claude output.

        Handles:
        1. Plain JSON (no fences)
        2. ```json ... ``` fenced blocks
        3. Truncated output — walks character-by-character to find the last
           complete JSON object, then closes any missing braces.
        """
        raw = raw.strip()

        # Strip markdown code fences
        if raw.startswith("```"):
            lines = raw.split("\n")
            start_line = 1  # skip ```json or ``` opening line
            end_line = len(lines)
            for i in range(len(lines) - 1, 0, -1):
                if lines[i].strip().startswith("```"):
                    end_line = i
                    break
            raw = "\n".join(lines[start_line:end_line]).strip()

        # Fast path: already valid JSON
        try:
            json.loads(raw)
            return raw
        except json.JSONDecodeError:
            pass

        # Locate the first opening brace
        start_idx = raw.find("{")
        if start_idx == -1:
            return raw  # no JSON — let caller raise a clear Pydantic error

        # Walk character-by-character tracking brace depth.
        # This correctly handles nested objects and stops at the matching close.
        depth = 0
        in_string = False
        escape_next = False
        last_valid_end = -1

        for i, ch in enumerate(raw[start_idx:], start=start_idx):
            if escape_next:
                escape_next = False
                continue
            if in_string:
                if ch == "\\":
                    escape_next = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    last_valid_end = i
                    break

        if last_valid_end != -1:
            # Found a complete top-level object
            candidate = raw[start_idx: last_valid_end + 1]
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                pass

        # Output was truncated — take everything from the opening brace and
        # close the missing levels so Pydantic can at least partially parse it.
        truncated = raw[start_idx:]
        open_depth = 0
        in_str = False
        esc = False
        for ch in truncated:
            if esc:
                esc = False
                continue
            if in_str:
                if ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                open_depth += 1
            elif ch == "}":
                open_depth -= 1

        repaired = truncated + "}" * max(0, open_depth)
        return repaired

    # ── Core API call (retriable) ─────────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((anthropic.APITimeoutError, anthropic.InternalServerError, TruncatedOutputError, ValidationError)),
    )
    async def _call(
        self,
        model: str,
        system: str,
        user: str,
        output_model: Type[T],
        layer: str,
        max_tokens: int,
    ) -> tuple[T, dict[str, Any]]:
        if not self._client:
            raise ValueError("Anthropic API key not configured")

        start = time.monotonic()
        logger.info("llm.request", model=model, layer=layer)

        message = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )

        latency_ms = int((time.monotonic() - start) * 1000)
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens

        # Claude Sonnet 4.6 adaptive thinking returns a ThinkingBlock BEFORE
        # the TextBlock. We must find the first TextBlock explicitly.
        raw_text = ""
        for block in message.content:
            block_type = getattr(block, "type", "")
            if block_type == "text" and hasattr(block, "text"):
                raw_text = block.text
                break

        logger.info(
            "llm.response",
            model=model,
            layer=layer,
            stop_reason=message.stop_reason,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            raw_text_length=len(raw_text),
        )

        if message.stop_reason == "max_tokens" and not raw_text.strip():
            logger.error("llm.truncated_empty", model=model, layer=layer, max_tokens=max_tokens)
            raise TruncatedOutputError(f"Output fully truncated at {max_tokens} tokens for {layer}")

        raw = self._extract_json(raw_text)
        parsed = output_model.model_validate_json(raw)

        return parsed, {
            "layer": layer,
            "model": model,
            "latency_ms": latency_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }

    # ── Public interface ──────────────────────────────────────────────────────

    async def complete_structured(
        self,
        system: str,
        user: str,
        output_model: Type[T],
        layer: str = "unknown",
        max_tokens: int = 16000,
        temperature: float | None = None,
    ) -> tuple[T, dict[str, Any]]:
        """Return a validated Pydantic model plus metadata dict.

        Falls back to claude-opus-4-5 on RateLimitError or InternalServerError.
        """
        try:
            return await self._call(self._model, system, user, output_model, layer, max_tokens)
        except (anthropic.RateLimitError, anthropic.InternalServerError) as exc:
            if not self._fallback_model or self._fallback_model == self._model:
                raise
            logger.warning(
                "claude.fallback",
                primary=self._model,
                fallback=self._fallback_model,
                reason=repr(exc),
            )
            return await self._call(self._fallback_model, system, user, output_model, layer, max_tokens)
