from __future__ import annotations

import io

from PIL import Image

from ocr_processor import GoogleVisionOCRProcessor


class _FakePageImage:
    def __init__(self, image: Image.Image) -> None:
        self.annotated = image
        self.original = image


class _FakePage:
    def __init__(self, image: Image.Image) -> None:
        self._image = image

    def to_image(self, resolution: int = 300) -> _FakePageImage:
        return _FakePageImage(self._image)


def test_resize_image_to_limits_caps_max_dimension() -> None:
    processor = GoogleVisionOCRProcessor()
    image = Image.new("RGB", (12000, 6000), color="white")

    resized, meta = processor._resize_image_to_limits(
        image,
        max_dimension=8000,
        max_total_pixels=25_000_000,
    )

    assert meta["resized"] is True
    assert meta["original_size"] == (12000, 6000)
    assert max(resized.size) <= 8000
    assert resized.width * resized.height <= 25_000_000


def test_render_pdf_page_for_ocr_outputs_jpeg_bytes_under_caps() -> None:
    processor = GoogleVisionOCRProcessor()
    page = _FakePage(Image.new("RGB", (13334, 7500), color="white"))

    payload, meta = processor._render_pdf_page_for_ocr(page)

    assert meta["resized"] is True
    assert meta["original_size"] == (13334, 7500)
    assert max(meta["final_size"]) <= processor.PDF_OCR_MAX_DIMENSION_PX
    assert meta["final_size"][0] * meta["final_size"][1] <= processor.PDF_OCR_MAX_TOTAL_PIXELS
    assert meta["format"] == "JPEG"
    assert payload[:2] == b"\xff\xd8"

    rendered = Image.open(io.BytesIO(payload))
    assert rendered.size == meta["final_size"]


def test_extract_exact_swatch_colors_uses_real_pixels_and_skips_page_background() -> None:
    processor = GoogleVisionOCRProcessor()
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

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    colors = processor.extract_exact_swatch_colors(buffer.getvalue())
    extracted_hexes = [color["hex"] for color in colors]

    assert {"#003A79", "#FF9E00", "#00CE8B", "#66757B", "#3D3DC3", "#FFC6C8"}.issubset(
        set(extracted_hexes)
    )
    assert "#FBFFFF" not in extracted_hexes
    assert "#FF9E01" not in extracted_hexes
    assert all(
        color["source"] in {"exact_swatch_pixels", "region_swatch_pixels"}
        for color in colors
    )


def test_extract_exact_swatch_colors_recovers_noisy_rendered_swatch_regions() -> None:
    processor = GoogleVisionOCRProcessor()
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

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    colors = processor.extract_exact_swatch_colors(buffer.getvalue())
    extracted_hexes = [color["hex"] for color in colors]

    expected = [(0, 58, 121), (255, 158, 0), (0, 206, 139)]
    extracted_rgb = [(color["r"], color["g"], color["b"]) for color in colors]
    for rgb in expected:
        assert any(processor._rgb_distance(rgb, candidate) <= 8 for candidate in extracted_rgb)
