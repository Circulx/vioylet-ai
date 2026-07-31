import json
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from types import SimpleNamespace

from PIL import Image

from app.ai.brand_asset_analysis import BrandAssetAnalyzer
from app.ai.rag.ocr import OCRService
from app.ai.template_vision import TemplateVisionAnalyzer


def test_pdf_page_images_are_scoped_per_uploaded_file(tmp_path) -> None:
    first_pdf = tmp_path / "first-palette.pdf"
    second_pdf = tmp_path / "second-palette.pdf"

    assert OCRService._pdf_page_images_dir(str(first_pdf)) == tmp_path / "_ocr" / "first-palette" / "page_images"
    assert OCRService._pdf_page_images_dir(str(second_pdf)) == tmp_path / "_ocr" / "second-palette" / "page_images"
    assert OCRService._pdf_page_images_dir(str(first_pdf)) != OCRService._scratch_root(str(first_pdf)) / "page_images"


def test_color_palette_pdf_without_page_images_uses_visual_candidate_fallback(tmp_path) -> None:
    image_path = tmp_path / "palette_page.png"
    image = Image.new("RGB", (80, 40), "#123456")
    image.paste(Image.new("RGB", (40, 40), "#FF8800"), (40, 0))
    image.save(image_path)

    pdf_path = tmp_path / "palette.pdf"

    class OcrStub:
        def __init__(self) -> None:
            self.visual_candidate_calls: list[str] = []

        def extract(self, _path, progress_callback=None):
            return {
                "text": "Visual identity palette guide",
                "images": [],
                "page_count": 1,
                "source_format": "pdf",
            }

        def extract_visual_candidates(self, path):
            self.visual_candidate_calls.append(str(path))
            return [str(image_path)]

    analyzer = BrandAssetAnalyzer.__new__(BrandAssetAnalyzer)
    analyzer.ocr = OcrStub()
    analyzer.vision = None
    analyzer._derive_reusable_assets = lambda **_kwargs: []

    outcome = analyzer.analyze(
        absolute_path=str(pdf_path),
        filename="palette.pdf",
        mime_type="application/pdf",
        requested_field_key="color_palette",
    )

    assert analyzer.ocr.visual_candidate_calls == [str(pdf_path)]
    assert outcome.image_candidates == [str(image_path)]
    extracted_hexes = {
        entry.get("hex_code")
        for entry in outcome.structured_data["palette_entries"]
    }
    assert {"#123456", "#FF8800"}.issubset(extracted_hexes)


def test_color_palette_page_prefers_exact_swatch_pixels_over_text_color_words(tmp_path) -> None:
    image_path = tmp_path / "palette_page.png"
    image = Image.new("RGB", (1000, 600), "#FBFFFF")
    for box, color in [
        ((520, 100, 710, 500), "#003A79"),
        ((710, 100, 910, 300), "#FF9E00"),
        ((710, 300, 810, 400), "#00CE8B"),
        ((810, 300, 910, 400), "#66757B"),
        ((710, 400, 810, 500), "#3D3DC3"),
        ((810, 400, 910, 500), "#FFC6C8"),
    ]:
        image.paste(Image.new("RGB", (box[2] - box[0], box[3] - box[1]), color), box[:2])
    image.save(image_path)

    analyzer = BrandAssetAnalyzer.__new__(BrandAssetAnalyzer)
    text = "\n".join(
        [
            "COLOR PALETTE",
            "Regal Blue",
            "Orange Peel",
            "Caribbean Green",
            "Moon Sand",
            "Governor Bay",
            "Pastel Heart",
        ]
    )

    structured, _normalized = analyzer._extract_palette(text, str(image_path), [str(image_path)])
    extracted_hexes = [entry.get("hex_code") for entry in structured["palette_entries"]]

    assert {"#003A79", "#FF9E00", "#00CE8B", "#66757B", "#3D3DC3", "#FFC6C8"}.issubset(
        set(extracted_hexes)
    )
    assert "blue" not in extracted_hexes
    assert "orange" not in extracted_hexes
    assert "#FBFFFF" not in extracted_hexes
    assert all(
        entry.get("source") in {"image_exact_swatch", "image_region_swatch"}
        for entry in structured["palette_entries"]
    )


def test_color_palette_page_recovers_noisy_rendered_swatch_regions(tmp_path) -> None:
    image_path = tmp_path / "noisy_palette_page.png"
    image = Image.new("RGB", (600, 360), "#FBFFFF")
    base_colors = [
        ((260, 60, 390, 240), (0, 58, 121)),
        ((390, 60, 540, 170), (255, 158, 0)),
        ((390, 170, 465, 240), (0, 206, 139)),
    ]
    offsets = [-4, -2, 0, 2, 4]
    for box, base in base_colors:
        left, top, right, bottom = box
        for y in range(top, bottom):
            for x in range(left, right):
                delta = offsets[(x + y) % len(offsets)]
                image.putpixel(
                    (x, y),
                    tuple(max(0, min(255, channel + delta)) for channel in base),
                )
    image.save(image_path)

    analyzer = BrandAssetAnalyzer.__new__(BrandAssetAnalyzer)
    text = "COLOR PALETTE\nRegal Blue\nOrange Peel\nCaribbean Green"

    structured, _normalized = analyzer._extract_palette(text, str(image_path), [str(image_path)])
    extracted_hexes = [entry.get("hex_code") for entry in structured["palette_entries"]]

    expected = [(0, 58, 121), (255, 158, 0), (0, 206, 139)]
    extracted_rgb = [
        (
            int((entry.get("rgb_value") or {}).get("r") or 0),
            int((entry.get("rgb_value") or {}).get("g") or 0),
            int((entry.get("rgb_value") or {}).get("b") or 0),
        )
        for entry in structured["palette_entries"]
    ]
    for rgb in expected:
        assert any(analyzer._rgb_distance(rgb, candidate) <= 8 for candidate in extracted_rgb)


def test_color_palette_roles_use_vision_classification_first(tmp_path) -> None:
    image_path = tmp_path / "vision_palette.png"
    image = Image.new("RGB", (1000, 720), "#FBFFFF")
    swatches = [
        ("#003A79", (120, 110, 320, 250)),
        ("#FF9E00", (340, 110, 540, 250)),
        ("#00CE8B", (120, 390, 270, 520)),
        ("#66757B", (290, 390, 440, 520)),
        ("#3D3DC3", (460, 390, 610, 520)),
        ("#FFC6C8", (630, 390, 780, 520)),
    ]
    for color, box in swatches:
        image.paste(Image.new("RGB", (box[2] - box[0], box[3] - box[1]), color), box[:2])
    image.save(image_path)

    analyzer = BrandAssetAnalyzer.__new__(BrandAssetAnalyzer)
    analyzer.vision = SimpleNamespace(
        analyze_color_palette=lambda _path: {
            "primary_colors": [
                {"name": "Regal Blue", "hex": "#003B78", "evidence": "left primary swatch"},
                {"name": "Orange Peel", "hex": "#FF9F01", "evidence": "right primary swatch"},
            ],
            "secondary_colors": [
                {"name": "Caribbean Green", "hex": "#00CE8B", "evidence": "secondary row"},
                {"name": "Moon Sand", "hex": "#66757B", "evidence": "secondary row"},
            ],
            "accent_colors": [
                {"name": "Governor Bay", "hex": "#3D3DC3", "evidence": "additional swatch"},
                {"name": "Pastel Heart", "hex": "#FFC6C8", "evidence": "additional swatch"},
            ],
        }
    )

    structured, _normalized = analyzer._extract_palette(
        "COLOR PALETTE\nPrimary Colors\nSecondary Colors",
        str(image_path),
        [str(image_path)],
    )
    entries = structured["palette_entries"]
    roles_by_hex = {
        entry.get("hex_code"): (entry.get("role"), entry.get("source_section"), entry.get("source"))
        for entry in entries
    }

    assert roles_by_hex["#003A79"] == ("primary", "primary", "vision_palette_classification")
    assert roles_by_hex["#FF9E00"] == ("secondary", "primary", "vision_palette_classification")
    assert roles_by_hex["#00CE8B"] == ("accent", "secondary", "vision_palette_classification")
    assert roles_by_hex["#66757B"] == ("accent", "secondary", "vision_palette_classification")
    assert roles_by_hex["#3D3DC3"] == ("accent", "accent", "vision_palette_classification")
    assert roles_by_hex["#FFC6C8"] == ("accent", "accent", "vision_palette_classification")


def test_color_palette_vision_does_not_assign_same_color_to_multiple_roles(tmp_path) -> None:
    image_path = tmp_path / "duplicate_vision_palette.png"
    image = Image.new("RGB", (400, 160), "#FBFFFF")
    image.paste(Image.new("RGB", (120, 100), "#003A79"), (40, 30))
    image.paste(Image.new("RGB", (120, 100), "#FF9E00"), (220, 30))
    image.save(image_path)

    analyzer = BrandAssetAnalyzer.__new__(BrandAssetAnalyzer)
    analyzer.vision = SimpleNamespace(
        analyze_color_palette=lambda _path: {
            "primary_colors": [{"name": "Regal Blue", "hex": "#003A79"}],
            "secondary_colors": [{"name": "Regal Blue Again", "hex": "#003A79"}],
            "accent_colors": [{"name": "Orange Peel", "hex": "#FF9E00"}],
        }
    )

    structured, _normalized = analyzer._extract_palette("", str(image_path), [str(image_path)])
    entries = structured["palette_entries"]
    hexes = [entry.get("hex_code") for entry in entries]

    assert hexes.count("#003A79") == 1
    assert {entry.get("role") for entry in entries if entry.get("hex_code") == "#003A79"} == {"primary"}
    assert len(hexes) == len(set(hexes))


def test_color_palette_roles_follow_primary_and_secondary_layout_headings(tmp_path) -> None:
    image_path = tmp_path / "sectioned_palette.png"
    image = Image.new("RGB", (1000, 720), "#FBFFFF")
    swatches = [
        ("#003A79", (120, 110, 320, 250)),
        ("#FF9E00", (340, 110, 540, 250)),
        ("#00CE8B", (120, 390, 270, 520)),
        ("#66757B", (290, 390, 440, 520)),
        ("#3D3DC3", (460, 390, 610, 520)),
        ("#FFC6C8", (630, 390, 780, 520)),
    ]
    for color, box in swatches:
        image.paste(Image.new("RGB", (box[2] - box[0], box[3] - box[1]), color), box[:2])
    image.save(image_path)

    analysis = {
        "page_dimensions": {"image_width_px": 1000, "image_height_px": 720},
        "sentences": [
            {"text": "Primary Colors", "bounding_box": {"x": 120, "y": 60, "width": 260, "height": 34}},
            {"text": "Secondary Colors", "bounding_box": {"x": 120, "y": 335, "width": 300, "height": 34}},
        ],
        "dominant_colors": [
            {
                "hex": color,
                "r": int(color[1:3], 16),
                "g": int(color[3:5], 16),
                "b": int(color[5:7], 16),
                "regions": [{"x": box[0], "y": box[1], "w": box[2] - box[0], "h": box[3] - box[1]}],
            }
            for color, box in swatches
        ],
    }
    image_path.with_name(f"{image_path.stem}_analysis.json").write_text(
        json.dumps(analysis),
        encoding="utf-8",
    )

    analyzer = BrandAssetAnalyzer.__new__(BrandAssetAnalyzer)
    structured, _normalized = analyzer._extract_palette(
        "COLOR PALETTE\nPrimary Colors\nSecondary Colors",
        str(image_path),
        [str(image_path)],
    )
    roles_by_hex = {
        entry.get("hex_code"): (entry.get("role"), entry.get("source_section"))
        for entry in structured["palette_entries"]
    }

    assert roles_by_hex["#003A79"] == ("primary", "primary")
    assert roles_by_hex["#FF9E00"] == ("secondary", "primary")
    assert roles_by_hex["#00CE8B"] == ("accent", "secondary")
    assert roles_by_hex["#66757B"] == ("accent", "secondary")
    assert roles_by_hex["#3D3DC3"] == ("accent", "secondary")
    assert roles_by_hex["#FFC6C8"] == ("accent", "secondary")


def test_brand_asset_analyzer_selects_cover_dense_and_cta_pages() -> None:
    analyzer = BrandAssetAnalyzer.__new__(BrandAssetAnalyzer)
    workspace = Path("storage") / "_test_artifacts" / "brand_analysis" / Path(mkdtemp()).name
    workspace.mkdir(parents=True, exist_ok=True)

    try:
        images = []
        analysis_paths = []
        page_specs = [
            (
                "page_1.png",
                {
                    "page_dimensions": {"image_width_px": 1000, "image_height_px": 1000},
                    "sentences": [
                        {"text": "Planning your retirement", "bounding_box": {"x": 60, "y": 70, "width": 500, "height": 90}},
                    ],
                },
            ),
            (
                "page_2.png",
                {
                    "page_dimensions": {"image_width_px": 1000, "image_height_px": 1000},
                    "sentences": [
                        {"text": "What to know", "bounding_box": {"x": 40, "y": 60, "width": 420, "height": 70}},
                        {"text": "Step 1", "bounding_box": {"x": 40, "y": 150, "width": 320, "height": 60}},
                        {"text": "Step 2", "bounding_box": {"x": 40, "y": 240, "width": 320, "height": 60}},
                        {"text": "Step 3", "bounding_box": {"x": 40, "y": 330, "width": 320, "height": 60}},
                    ],
                },
            ),
            (
                "page_3.png",
                {
                    "page_dimensions": {"image_width_px": 1000, "image_height_px": 1000},
                    "sentences": [
                        {"text": "Get started today", "bounding_box": {"x": 60, "y": 100, "width": 420, "height": 70}},
                        {"text": "Learn more", "bounding_box": {"x": 60, "y": 820, "width": 240, "height": 50}},
                    ],
                },
            ),
        ]

        for filename, analysis in page_specs:
            image_path = workspace / filename
            image_path.write_bytes(b"placeholder")
            analysis_path = workspace / f"{image_path.stem}_analysis.json"
            analysis_path.write_text(json.dumps(analysis), encoding="utf-8")
            images.append(str(image_path))
            analysis_paths.append(str(analysis_path))

        selected = analyzer._select_representative_visual_pages(
            absolute_path=str(workspace / "deck.pdf"),
            images=images,
            analysis_paths=analysis_paths,
        )

        assert [record["page_index"] for record in selected] == [1, 2, 3]
        assert selected[1]["density_score"] > selected[0]["density_score"]
        assert selected[2]["cta_score"] > 0
    finally:
        rmtree(workspace, ignore_errors=True)


def test_template_vision_analyze_pages_merges_partial_page_results() -> None:
    class StubAnalyzer:
        def __init__(self) -> None:
            self.results = {
                "page-1": {
                    "background_style": {"type": "gradient", "description": "deep blue gradient"},
                    "layout_type": "editorial explainer",
                    "editable_zones": [{"role": "headline"}],
                    "component_motifs": {"numbered_badges": {"detected": True}},
                    "visual_hierarchy": {"focal_role": "headline", "density": "airy"},
                    "content_structure": {"storytelling": "benefit stack", "cta_prominence": "measured"},
                    "image_treatment": {"style": "diagram led"},
                    "brand_cues": {"tone_keywords": ["trustworthy"]},
                    "page_blueprint": {"layout_category": "cover_or_hero_visual", "module_counts": {"text_block_count": 2}},
                    "ocr_structure": {"readable_text_blocks": 2, "text_truncation_or_crop_risk": "medium"},
                    "premium_quality": {"overall_score": 0.86},
                },
                "page-2": {
                    "background_style": {"type": "gradient", "description": "deep blue gradient"},
                    "layout_type": "editorial explainer",
                    "editable_zones": [{"role": "headline"}, {"role": "proof_module"}],
                    "component_motifs": {"text_background_boxes": {"detected": True}},
                    "visual_hierarchy": {"focal_role": "proof_module", "density": "dense"},
                    "content_structure": {"storytelling": "data story", "cta_prominence": "subtle"},
                    "image_treatment": {"style": "editorial illustration"},
                    "brand_cues": {"trust_markers": ["data cues"]},
                    "page_blueprint": {"layout_category": "card_callout_grid", "module_counts": {"card_module_count": 3}},
                    "ocr_structure": {"readable_text_blocks": 5, "text_truncation_or_crop_risk": "medium"},
                    "premium_quality": {"overall_score": 0.9},
                },
                "page-3": None,
            }

        def analyze(self, image_path, fallback):
            return self.results.get(image_path, fallback)

    fallback = {
        "background_style": {"type": "flat"},
        "layout_type": "template",
        "editable_zones": [],
        "component_motifs": {},
    }

    merged = TemplateVisionAnalyzer.analyze_pages(
        StubAnalyzer(),
        ["page-1", "page-2", "page-3"],
        fallback,
    )

    assert merged["layout_type"] == "editorial explainer"
    assert merged["analysis_confidence"] == 0.6667
    assert len(merged["page_analysis_summary"]) == 2
    assert merged["component_motifs"]["numbered_badges"]["page_support"] == 1
    assert merged["component_motifs"]["text_background_boxes"]["page_support_ratio"] == 0.5
    assert merged["visual_hierarchy"]["focal_role"] in {"headline", "proof_module"}
    assert merged["content_structure"]["cta_prominence"] in {"measured", "subtle"}
    assert merged["image_treatment"]["style"] in {"diagram led", "editorial illustration"}
    assert merged["page_blueprint"]["layout_category"] in {"cover_or_hero_visual", "card_callout_grid"}
    assert merged["ocr_structure"]["readable_text_blocks"] == 3.5
    assert merged["ocr_structure"]["text_truncation_or_crop_risk"] == "medium"
    assert merged["premium_quality"]["overall_score"] == 0.88
