from __future__ import annotations

import base64
import json
from io import BytesIO
from contextlib import ExitStack
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.request import urlopen

from openai import OpenAI
from PIL import Image

from app.ai.providers.base import ImageGenerationBackend, PromptEnvelope, TextGenerationProvider
from app.core.config import get_settings
from app.integrations.object_storage import LocalObjectStorage


class OpenAITextProvider(TextGenerationProvider):
    # Wraps OpenAI text calls behind the shared TextGenerationProvider interface.
    # It handles JSON/text API differences, fallback behavior, and token usage capture for diagnostics.
    provider_name = "openai"

    def __init__(self) -> None:
        # Initializes settings, clients, and helper services needed by provider routing.
        # Public methods reuse these collaborators instead of rebuilding them for each request.
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key) if self.settings.openai_api_key else None
        self.last_usage: dict[str, Any] | None = None

    def _supports_responses_api(self) -> bool:
        # Checks supports responses api for provider routing.
        # The boolean result controls the nearby policy or validation branch.
        return bool(self.client and getattr(self.client, "responses", None))

    @staticmethod
    def _plain_value(value: Any) -> Any:
        # Centralizes plain from input value for provider routing.
        # The main branch stays readable while this function handles the local edge case.
        if value in ("", None, [], {}):
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, list):
            return [item for item in (OpenAITextProvider._plain_value(item) for item in value) if item is not None]
        if isinstance(value, dict):
            return {
                str(key): cleaned
                for key, item in value.items()
                if (cleaned := OpenAITextProvider._plain_value(item)) is not None
            }
        if hasattr(value, "model_dump"):
            try:
                return OpenAITextProvider._plain_value(value.model_dump())
            except Exception:  # noqa: BLE001
                pass
        if hasattr(value, "__dict__"):
            return OpenAITextProvider._plain_value(vars(value))
        return str(value)

    @classmethod
    def _extract_usage(cls, response: Any, *, model: str, operation: str) -> dict[str, Any] | None:
        # Extracts usage from response, model, and operation for provider routing.
        # It calls _plain_value to turn raw evidence into the structured signal the caller needs.
        usage = cls._plain_value(getattr(response, "usage", None))
        if not isinstance(usage, dict) or not usage:
            return None
        input_tokens = usage.get("input_tokens", usage.get("prompt_tokens"))
        output_tokens = usage.get("output_tokens", usage.get("completion_tokens"))
        total_tokens = usage.get("total_tokens")
        if total_tokens is None and isinstance(input_tokens, int) and isinstance(output_tokens, int):
            total_tokens = input_tokens + output_tokens
        normalized = {
            "provider": cls.provider_name,
            "model": model,
            "operation": operation,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "raw_usage": usage,
        }
        return {key: val for key, val in normalized.items() if val is not None}

    def _remember_usage(self, response: Any, *, model: str, operation: str) -> None:
        # Records remember usage from response, model, and operation for provider routing.
        # Usage metadata stays beside the provider result for trace and cost diagnostics.
        self.last_usage = self._extract_usage(response, model=model, operation=operation)

    def _chat_completion_text(self, *, system: str, user: str) -> str:
        # Calls chat completion text from system and user for provider routing.
        # The result is normalized before orchestration or evaluation reads it.
        if not self.client:
            self.last_usage = None
            return ""
        response = self.client.chat.completions.create(
            model=self.settings.tone_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        self._remember_usage(response, model=self.settings.tone_model, operation="chat_text")
        return (response.choices[0].message.content or "").strip() if getattr(response, "choices", None) else ""

    def _chat_completion_json(self, *, system: str, user: str) -> str:
        # Calls chat completion json from system and user for provider routing.
        # The result is normalized before orchestration or evaluation reads it.
        if not self.client:
            self.last_usage = None
            return ""
        response = self.client.chat.completions.create(
            model=self.settings.llm_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
        )
        self._remember_usage(response, model=self.settings.llm_model, operation="chat_structured_json")
        return (response.choices[0].message.content or "").strip() if getattr(response, "choices", None) else ""

    def generate_structured_json(self, envelope: PromptEnvelope, fallback: dict[str, Any]) -> dict[str, Any]:
        # Sends a JSON-oriented PromptEnvelope to OpenAI and parses the provider response.
        # Fallback data is returned when the client is unavailable or the response path cannot produce usable JSON.
        if not self.client:
            self.last_usage = None
            return fallback
        if self._supports_responses_api():
            # Prefer Responses when available because it gives consistent JSON-mode output and usage metadata.
            response = self.client.responses.create(
                model=self.settings.llm_model,
                input=[
                    {"role": "system", "content": envelope.system},
                    {"role": "user", "content": envelope.user},
                ],
                text={"format": {"type": "json_object"}},
            )
            self._remember_usage(response, model=self.settings.llm_model, operation="responses_structured_json")
            text = response.output_text or json.dumps(fallback)
        else:
            # Older SDK/client combinations still use Chat Completions, so the provider keeps both paths alive.
            text = self._chat_completion_json(system=envelope.system, user=envelope.user) or json.dumps(fallback)
        return json.loads(text)

    def generate_text(self, envelope: PromptEnvelope, fallback: str) -> str:
        # Sends a plain-text PromptEnvelope to OpenAI and returns the provider answer or fallback string.
        # This supports evaluation or helper flows that need natural language instead of structured JSON.
        if not self.client:
            self.last_usage = None
            return fallback
        if self._supports_responses_api():
            # Plain-text generations use the tone model, while structured JSON stays on the main LLM model.
            response = self.client.responses.create(
                model=self.settings.tone_model,
                input=[
                    {"role": "system", "content": envelope.system},
                    {"role": "user", "content": envelope.user},
                ],
            )
            self._remember_usage(response, model=self.settings.tone_model, operation="responses_text")
            return response.output_text or fallback
        return self._chat_completion_text(system=envelope.system, user=envelope.user) or fallback


class OpenAIImageProvider(ImageGenerationBackend):
    # Wraps OpenAI image generation and editing behind the shared ImageGenerationBackend interface.
    # It stores generated bytes through LocalObjectStorage and returns asset metadata for final rendering.
    provider_name = "openai"

    def __init__(self) -> None:
        # Initializes settings, clients, and helper services needed by provider routing.
        # Public methods reuse these collaborators instead of rebuilding them for each request.
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key) if self.settings.openai_api_key else None
        self.storage = LocalObjectStorage()
        self.last_usage: dict[str, Any] | None = None

    def _configured_image_quality(self, model_name: str) -> str | None:
        # Resolves image quality from model name for provider routing.
        # This hides source-specific naming and path quirks from the main flow.
        configured = str(getattr(self.settings, "image_generation_quality", "high") or "").strip().lower()
        if not configured or configured == "auto":
            return "high"
        return configured

    def _configured_input_fidelity(self, model_name: str) -> str | None:
        # Resolves input fidelity from model name for provider routing.
        # The caller receives the canonical identifier/path/config value expected by the next step.
        if "mini" in model_name:
            return None
        configured = str(getattr(self.settings, "image_edit_input_fidelity", "high") or "").strip().lower()
        if not configured or configured == "auto":
            return "high"
        return configured

    def _image_edit_options(self, size: str) -> dict[str, Any]:
        # Builds image edit options from size for provider routing.
        # It calls _configured_image_quality and _configured_input_fidelity while assembling the payload or prompt text.
        model_name = str(self.settings.image_model or "").strip().lower()
        options: dict[str, Any] = {
            "model": self.settings.image_model,
            "size": size,
            "output_format": "png",
        }
        # `gpt-image-1-mini` does not currently accept `input_fidelity`, and
        # sending it causes the logo edit pass to fail before the model can
        # apply the real uploaded logo. Quality remains config-driven.
        quality = self._configured_image_quality(model_name)
        input_fidelity = self._configured_input_fidelity(model_name)
        if quality:
            options["quality"] = quality
        if input_fidelity:
            options["input_fidelity"] = input_fidelity
        return options

    def _image_generate_options(self, size: str) -> dict[str, Any]:
        # Builds image options from size for provider routing.
        # It calls _configured_image_quality while assembling the payload or prompt text.
        model_name = str(self.settings.image_model or "").strip().lower()
        options: dict[str, Any] = {
            "model": self.settings.image_model,
            "size": size,
        }
        quality = self._configured_image_quality(model_name)
        if quality:
            options["quality"] = quality
        return options

    @staticmethod
    def _extract_image_bytes(result: Any) -> bytes:
        # Extracts image bytes from result for provider routing.
        # The extracted signal becomes prompt context, metadata, or ranking input.
        data = list(getattr(result, "data", []) or [])
        if not data:
            raise RuntimeError("OpenAI image response did not contain any image data")
        item = data[0]
        image_b64 = getattr(item, "b64_json", None) or getattr(item, "b64", None)
        if image_b64:
            return base64.b64decode(image_b64)
        image_url = getattr(item, "url", None)
        if image_url:
            with urlopen(image_url, timeout=120) as response:  # noqa: S310 - trusted provider URL
                return response.read()
        raise RuntimeError("OpenAI image response did not include retrievable image bytes")

    def generate(self, tenant_id, brand_space_id, prompt: str, size: str | None = None) -> dict[str, Any]:
        # Generates a new image with OpenAI, stores the bytes, and returns persisted image metadata.
        # The orchestrator uses that metadata when an AI-created visual becomes part of the final render.
        if not self.client:
            self.last_usage = None
            raise RuntimeError("OpenAI image provider unavailable")
        options = self._image_generate_options(size or "1024x1024")
        # Generation returns provider bytes only; storage happens here so callers receive durable asset metadata.
        result = self.client.images.generate(
            prompt=prompt,
            **options,
        )
        self.last_usage = OpenAITextProvider._extract_usage(result, model=self.settings.image_model, operation="image_generate")
        image_bytes = self._extract_image_bytes(result)
        image = Image.open(BytesIO(image_bytes))
        stored = self.storage.save_bytes(
            tenant_id=tenant_id,
            brand_space_id=brand_space_id,
            category="generated",
            filename=f"generated-{brand_space_id}.png",
            content=image_bytes,
        )
        payload = {
            "mime_type": "image/png",
            "storage_path": stored.storage_path,
            "width": image.width,
            "height": image.height,
            "asset_role": "ai_image",
            "provider": self.provider_name,
            "model": self.settings.image_model,
            "size": size or "1024x1024",
            "quality": options.get("quality"),
            "provider_usage": self.last_usage,
        }
        return {key: val for key, val in payload.items() if val is not None}

    def edit(
        self,
        tenant_id,
        brand_space_id,
        prompt: str,
        image_paths: list[str],
        size: str | None = None,
        mask_png_bytes: bytes | None = None,
    ) -> dict[str, Any]:
        # Edits uploaded/reference images through OpenAI image editing and stores the resulting asset.
        # Logo-aware and template-aware flows use the returned metadata as the visual source for composition.
        if not self.client:
            self.last_usage = None
            raise RuntimeError("OpenAI image provider unavailable")
        if not image_paths:
            raise ValueError("image_paths must include at least one base image path")

        with ExitStack() as stack:
            image_files = [stack.enter_context(open(path, "rb")) for path in image_paths]
            kwargs: dict[str, Any] = {
                "image": image_files,
                "prompt": prompt,
                **self._image_edit_options(size or "1024x1024"),
            }
            if mask_png_bytes:
                mask_file = stack.enter_context(NamedTemporaryFile(suffix=".png"))
                mask_file.write(mask_png_bytes)
                mask_file.flush()
                # The temp file keeps the mask open long enough for the SDK multipart upload.
                kwargs["mask"] = stack.enter_context(open(mask_file.name, "rb"))
            result = self.client.images.edit(**kwargs)

        self.last_usage = OpenAITextProvider._extract_usage(result, model=self.settings.image_model, operation="image_edit")
        image_bytes = self._extract_image_bytes(result)
        image = Image.open(BytesIO(image_bytes))
        stored = self.storage.save_bytes(
            tenant_id=tenant_id,
            brand_space_id=brand_space_id,
            category="generated",
            filename=f"edited-{brand_space_id}.png",
            content=image_bytes,
        )
        payload = {
            "mime_type": "image/png",
            "storage_path": stored.storage_path,
            "width": image.width,
            "height": image.height,
            "asset_role": "ai_image",
            "provider": self.provider_name,
            "model": self.settings.image_model,
            "size": size or "1024x1024",
            "quality": kwargs.get("quality"),
            "input_fidelity": kwargs.get("input_fidelity"),
            "provider_usage": self.last_usage,
        }
        return {key: val for key, val in payload.items() if val is not None}
