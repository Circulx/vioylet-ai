from __future__ import annotations

from app.services.generation_trace import GenerationTraceService


def test_generation_trace_cost_estimation_uses_exact_provider_usage(tmp_path) -> None:
    service = GenerationTraceService(base_dir=tmp_path, enabled=True)
    trace_id = "20260618-test-static"
    service.write_payload(trace_id, "manifest", {"metadata": {"format": "static"}})
    service.write_payload(
        trace_id,
        "planning_provider_usage",
        {
            "usage": {
                "provider": "openai",
                "model": "configured-text-model",
                "operation": "responses_structured_json",
                "input_tokens": 1000,
                "output_tokens": 250,
                "total_tokens": 1250,
            }
        },
    )
    service.write_payload(
        trace_id,
        "final_render_generation",
        {
            "slide_count": 1,
            "assets": [
                {
                    "metadata": {
                        "provider_usage": {
                            "provider": "openai",
                            "model": "configured-image-model",
                            "operation": "image_generate",
                            "input_tokens": 100,
                            "output_tokens": 5000,
                            "total_tokens": 5100,
                        }
                    }
                }
            ],
        },
    )

    report = service.build_cost_estimation(trace_id)

    assert report is not None
    assert report["format"] == "static"
    assert report["accuracy"]["exact_provider_usage_records"] == 2
    assert report["totals"]["text_input_tokens"] == 1000
    assert report["totals"]["image_output_tokens"] == 5000
    assert report["totals"]["image_calls"] == 1
    assert report["totals"]["estimated_usd"] > 0


def test_generation_trace_cost_estimation_backfills_old_trace_from_prompt_files(tmp_path) -> None:
    service = GenerationTraceService(base_dir=tmp_path, enabled=True)
    trace_id = "20260618-old-carousel"
    service.write_payload(trace_id, "manifest", {"metadata": {"format": "carousel"}})
    service.write_payload(
        trace_id,
        "planning_prompt",
        {"system": "You plan carousels.", "user": "Create a five slide carousel."},
    )
    service.write_payload(
        trace_id,
        "planning_response",
        {"headline": "A", "metadata": {"carousel_slide_specs": [{"headline": "One"}]}},
    )
    service.write_payload(trace_id, "final_render_generation", {"slide_count": 5, "assets": [{}, {}, {}, {}, {}]})

    report = service.build_cost_estimation(trace_id)

    assert report is not None
    assert report["format"] == "carousel"
    assert report["accuracy"]["estimated_text_records"] >= 1
    assert report["accuracy"]["estimated_image_call_records"] == 1
    assert report["totals"]["image_calls"] == 5
    assert report["totals"]["estimated_usd"] > 0


def test_generation_trace_cost_estimation_counts_nested_vision_usage(tmp_path) -> None:
    service = GenerationTraceService(base_dir=tmp_path, enabled=True)
    trace_id = "20260618-vision-usage"
    service.write_payload(trace_id, "manifest", {"metadata": {"format": "static"}})
    service.write_payload(
        trace_id,
        "final_render_output_quality_attempt_01",
        {
            "report": {
                "vision_quality": {
                    "provider_usage": {
                        "provider": "openai",
                        "model": "configured-vision-model",
                        "operation": "template_vision_analysis",
                        "input_tokens": 2000,
                        "output_tokens": 300,
                        "total_tokens": 2300,
                    }
                }
            }
        },
    )

    report = service.build_cost_estimation(trace_id)

    assert report is not None
    assert report["accuracy"]["exact_provider_usage_records"] == 1
    assert report["totals"]["text_input_tokens"] == 2000
    assert report["totals"]["text_output_tokens"] == 300
    assert report["phases"][0]["phase"] == "final_render"


def test_generation_trace_cost_estimation_dedupes_copied_provider_usage(tmp_path) -> None:
    service = GenerationTraceService(base_dir=tmp_path, enabled=True)
    trace_id = "20260618-copied-usage"
    provider_usage = {
        "provider": "openai",
        "model": "configured-vision-model",
        "operation": "template_vision_analysis",
        "input_tokens": 2000,
        "output_tokens": 300,
        "total_tokens": 2300,
    }
    service.write_payload(trace_id, "manifest", {"metadata": {"format": "static"}})
    service.write_payload(
        trace_id,
        "final_render_generation",
        {"assets": [{"metadata": {"output_quality_assessment": {"vision_quality": {"provider_usage": provider_usage}}}}]},
    )
    service.write_payload(
        trace_id,
        "final_render_output_quality_attempt_01",
        {"report": {"vision_quality": {"provider_usage": provider_usage}}},
    )
    service.write_payload(
        trace_id,
        "final_render_output_quality_visible_with_warnings",
        {"quality_report": {"vision_quality": {"provider_usage": provider_usage}}},
    )

    report = service.build_cost_estimation(trace_id)

    assert report is not None
    assert report["accuracy"]["exact_provider_usage_records"] == 1
    assert report["totals"]["text_input_tokens"] == 2000
    assert report["totals"]["text_output_tokens"] == 300


def test_brand_usage_report_compaction_keeps_summary_without_heavy_payloads() -> None:
    heavy_report = {
        "trace_id": "trace-1",
        "mode": "content.generate",
        "prompt": "Create a static LinkedIn post",
        "section_payloads": {"brand_voice": {"raw": "x" * 10000}},
        "runtime_brand_context": {"deep": {"raw": "y" * 10000}},
        "sources_used": {"deep": {"raw": "s" * 10000}},
        "explainability": {
            "render_authority": "ai",
            "compiled_context": {"heavy": "z" * 10000},
            "final_render_assets": [
                {
                    "asset_id": "asset-1",
                    "mime_type": "image/png",
                    "storage_path": "generated/demo.png",
                    "metadata": {"provider_usage": {"input_tokens": 10, "output_tokens": 20}},
                }
            ],
        },
    }

    compact = GenerationTraceService._compact_brand_usage_report(heavy_report)

    assert compact["trace_id"] == "trace-1"
    assert compact["mode"] == "content.generate"
    assert compact["section_payloads"]["brand_voice"]["raw"].endswith("x")
    assert len(compact["section_payloads"]["brand_voice"]["raw"]) < 1800
    assert compact["sources_used"]["deep"]["raw"].endswith("s")
    assert len(compact["sources_used"]["deep"]["raw"]) < 1800
    assert compact["explainability"]["render_authority"] == "ai"
    assert compact["explainability"]["compiled_context_summary"]["section_count"] == 1
    assert compact["explainability"]["final_render_assets"][0]["asset_id"] == "asset-1"
