from io import BytesIO
from types import SimpleNamespace
import base64
import json

from PIL import Image

from app.ai.providers.base import PromptEnvelope
from app.ai.providers.openai_provider import OpenAIImageProvider, OpenAITextProvider
from app.ai.template_vision import TemplateVisionAnalyzer


def _png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (8, 8), color=(12, 34, 56)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_openai_image_provider_generate_omits_response_format() -> None:
    provider = OpenAIImageProvider()
    calls: list[dict] = []
    provider.client = SimpleNamespace(
        images=SimpleNamespace(
            generate=lambda **kwargs: calls.append(kwargs) or SimpleNamespace(
                data=[SimpleNamespace(b64_json=base64.b64encode(_png_bytes()).decode("ascii"))]
            )
        )
    )
    provider.storage = SimpleNamespace(
        save_bytes=lambda tenant_id, brand_space_id, category, filename, content: SimpleNamespace(storage_path="tenant/brand/generated/test.png")
    )

    asset = provider.generate("tenant", "brand", "Prompt", size="1024x1024")

    assert "response_format" not in calls[0]
    assert asset["storage_path"] == "tenant/brand/generated/test.png"
    assert asset["width"] == 8
    assert asset["height"] == 8


def test_openai_text_provider_records_responses_usage() -> None:
    provider = OpenAITextProvider()
    provider.client = SimpleNamespace(
        responses=SimpleNamespace(
            create=lambda **kwargs: SimpleNamespace(
                output_text='{"ok": true}',
                usage=SimpleNamespace(input_tokens=120, output_tokens=30, total_tokens=150),
            )
        )
    )

    result = provider.generate_structured_json(PromptEnvelope(system="System", user="User"), fallback={})

    assert result == {"ok": True}
    assert provider.last_usage == {
        "provider": "openai",
        "model": provider.settings.llm_model,
        "operation": "responses_structured_json",
        "input_tokens": 120,
        "output_tokens": 30,
        "total_tokens": 150,
        "raw_usage": {"input_tokens": 120, "output_tokens": 30, "total_tokens": 150},
    }


def test_openai_text_provider_records_chat_completion_usage_when_responses_unavailable() -> None:
    provider = OpenAITextProvider()
    provider.client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))],
                    usage=SimpleNamespace(prompt_tokens=90, completion_tokens=20, total_tokens=110),
                )
            )
        )
    )

    result = provider.generate_structured_json(PromptEnvelope(system="System", user="User"), fallback={})

    assert result == {"ok": True}
    assert provider.last_usage["operation"] == "chat_structured_json"
    assert provider.last_usage["input_tokens"] == 90
    assert provider.last_usage["output_tokens"] == 20
    assert provider.last_usage["total_tokens"] == 110


def test_template_vision_analyzer_reuses_cached_analysis(tmp_path) -> None:
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(_png_bytes())
    calls: list[dict] = []
    analyzer = TemplateVisionAnalyzer()
    analyzer.cache_enabled = True
    analyzer.cache_base_path = tmp_path / "vision-cache"
    analyzer.client = SimpleNamespace(
        responses=SimpleNamespace(
            create=lambda **kwargs: calls.append(kwargs) or SimpleNamespace(
                output_text=json.dumps(
                    {
                        "background_style": {"type": "flat", "primary_hex": "#ffffff"},
                        "layout_type": "infographic",
                        "page_blueprint": {"layout_category": "editorial_explainer"},
                        "premium_quality": {"overall_score": 0.9},
                    }
                ),
                usage=SimpleNamespace(input_tokens=100, output_tokens=20, total_tokens=120),
            )
        )
    )

    first = analyzer.analyze(str(image_path), fallback={})
    second = analyzer.analyze(str(image_path), fallback={})

    assert len(calls) == 1
    assert first["provider_usage"]["input_tokens"] == 100
    assert first["vision_cache"]["status"] == "miss"
    assert second["provider_usage"] is None
    assert second["vision_cache"]["status"] == "hit"
    assert second["layout_type"] == first["layout_type"]


def test_openai_image_provider_generate_uses_quality_for_default_mini_model() -> None:
    provider = OpenAIImageProvider()
    original_model = provider.settings.image_model
    original_quality = provider.settings.image_generation_quality
    provider.settings.image_model = "gpt-image-1-mini"
    provider.settings.image_generation_quality = "high"
    calls: list[dict] = []
    provider.client = SimpleNamespace(
        images=SimpleNamespace(
            generate=lambda **kwargs: calls.append(kwargs) or SimpleNamespace(
                data=[SimpleNamespace(b64_json=base64.b64encode(_png_bytes()).decode("ascii"))]
            )
        )
    )
    provider.storage = SimpleNamespace(
        save_bytes=lambda tenant_id, brand_space_id, category, filename, content: SimpleNamespace(storage_path="tenant/brand/generated/test.png")
    )

    try:
        provider.generate("tenant", "brand", "Prompt", size="1024x1024")
    finally:
        provider.settings.image_model = original_model
        provider.settings.image_generation_quality = original_quality

    assert calls[0]["model"] == "gpt-image-1-mini"
    assert calls[0]["quality"] == "high"


def test_openai_image_provider_generate_records_usage_metadata() -> None:
    provider = OpenAIImageProvider()
    calls: list[dict] = []
    provider.client = SimpleNamespace(
        images=SimpleNamespace(
            generate=lambda **kwargs: calls.append(kwargs) or SimpleNamespace(
                data=[SimpleNamespace(b64_json=base64.b64encode(_png_bytes()).decode("ascii"))],
                usage={"input_tokens": 210, "output_tokens": 6240, "total_tokens": 6450},
            )
        )
    )
    provider.storage = SimpleNamespace(
        save_bytes=lambda tenant_id, brand_space_id, category, filename, content: SimpleNamespace(storage_path="tenant/brand/generated/test.png")
    )

    asset = provider.generate("tenant", "brand", "Prompt", size="1024x1536")

    assert asset["provider_usage"]["operation"] == "image_generate"
    assert asset["provider_usage"]["input_tokens"] == 210
    assert asset["provider_usage"]["output_tokens"] == 6240
    assert provider.last_usage == asset["provider_usage"]


def test_openai_image_provider_extracts_image_from_url_when_base64_missing(monkeypatch) -> None:
    provider = OpenAIImageProvider()
    provider.client = None

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return _png_bytes()

    monkeypatch.setattr(
        "app.ai.providers.openai_provider.urlopen",
        lambda url, timeout=120: _Response(),
    )

    image_bytes = provider._extract_image_bytes(SimpleNamespace(data=[SimpleNamespace(url="https://example.com/image.png")]))

    assert image_bytes.startswith(b"\x89PNG")


def test_openai_image_provider_edit_uses_quality_but_omits_input_fidelity_for_mini_model() -> None:
    provider = OpenAIImageProvider()
    original_model = provider.settings.image_model
    original_quality = provider.settings.image_generation_quality
    original_fidelity = provider.settings.image_edit_input_fidelity
    provider.settings.image_model = "gpt-image-1-mini"
    provider.settings.image_generation_quality = "high"
    provider.settings.image_edit_input_fidelity = "high"
    calls: list[dict] = []
    provider.client = SimpleNamespace(
        images=SimpleNamespace(
            edit=lambda **kwargs: calls.append(kwargs) or SimpleNamespace(
                data=[SimpleNamespace(b64_json=base64.b64encode(_png_bytes()).decode("ascii"))]
            )
        )
    )
    provider.storage = SimpleNamespace(
        save_bytes=lambda tenant_id, brand_space_id, category, filename, content: SimpleNamespace(storage_path="tenant/brand/generated/test.png")
    )

    try:
        asset = provider.edit("tenant", "brand", "Place the real logo", image_paths=[__file__], size="1024x1024")
    finally:
        provider.settings.image_model = original_model
        provider.settings.image_generation_quality = original_quality
        provider.settings.image_edit_input_fidelity = original_fidelity

    assert "input_fidelity" not in calls[0]
    assert calls[0]["quality"] == "high"
    assert asset["storage_path"] == "tenant/brand/generated/test.png"


def test_openai_image_provider_generate_uses_configured_quality_for_non_mini_model() -> None:
    provider = OpenAIImageProvider()
    original_model = provider.settings.image_model
    original_quality = provider.settings.image_generation_quality
    provider.settings.image_model = "gpt-image-1"
    provider.settings.image_generation_quality = "high"
    calls: list[dict] = []
    provider.client = SimpleNamespace(
        images=SimpleNamespace(
            generate=lambda **kwargs: calls.append(kwargs) or SimpleNamespace(
                data=[SimpleNamespace(b64_json=base64.b64encode(_png_bytes()).decode("ascii"))]
            )
        )
    )
    provider.storage = SimpleNamespace(
        save_bytes=lambda tenant_id, brand_space_id, category, filename, content: SimpleNamespace(storage_path="tenant/brand/generated/test.png")
    )

    try:
        provider.generate("tenant", "brand", "Prompt", size="1024x1024")
    finally:
        provider.settings.image_model = original_model
        provider.settings.image_generation_quality = original_quality

    assert calls[0]["quality"] == "high"


def test_openai_image_provider_edit_uses_configured_quality_and_fidelity_for_non_mini_model() -> None:
    provider = OpenAIImageProvider()
    original_model = provider.settings.image_model
    original_quality = provider.settings.image_generation_quality
    original_fidelity = provider.settings.image_edit_input_fidelity
    provider.settings.image_model = "gpt-image-1"
    provider.settings.image_generation_quality = "high"
    provider.settings.image_edit_input_fidelity = "high"
    calls: list[dict] = []
    provider.client = SimpleNamespace(
        images=SimpleNamespace(
            edit=lambda **kwargs: calls.append(kwargs) or SimpleNamespace(
                data=[SimpleNamespace(b64_json=base64.b64encode(_png_bytes()).decode("ascii"))]
            )
        )
    )
    provider.storage = SimpleNamespace(
        save_bytes=lambda tenant_id, brand_space_id, category, filename, content: SimpleNamespace(storage_path="tenant/brand/generated/test.png")
    )

    try:
        provider.edit("tenant", "brand", "Place the real logo", image_paths=[__file__], size="1024x1024")
    finally:
        provider.settings.image_model = original_model
        provider.settings.image_generation_quality = original_quality
        provider.settings.image_edit_input_fidelity = original_fidelity

    assert calls[0]["quality"] == "high"
    assert calls[0]["input_fidelity"] == "high"
