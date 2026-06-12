from __future__ import annotations

from typing import Any, Callable

from PIL import Image, ImageDraw, ImageFont


FooterFontLoader = Callable[[int], ImageFont.ImageFont]


def _load_default_footer_font(size: int) -> ImageFont.ImageFont:
    for font_name in ("arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(font_name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def wrap_footer_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    *,
    max_width: int,
) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        left, _top, right, _bottom = draw.textbbox((0, 0), candidate, font=font)
        if current and (right - left) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def calculate_footer_safe_area(
    *,
    canvas_width: int,
    canvas_height: int,
    footer_text: Any,
    font_loader: FooterFontLoader | None = None,
) -> dict[str, Any]:
    text = " ".join(str(footer_text or "").split())
    width = max(int(canvas_width or 0), 1)
    height = max(int(canvas_height or 0), 1)
    if not text:
        return {
            "enabled": False,
            "position": "bottom_footer",
            "reserved_height": 0,
            "reserved_ratio": 0.0,
            "safe_bottom_inset": 0,
            "content_canvas_height": height,
            "content_safe_area": {"x": 0, "y": 0, "width": width, "height": height},
            "footer_strip_box": {"x": 0, "y": height, "width": width, "height": 0},
            "footer_text_box": {"x": 0, "y": height, "width": width, "height": 0},
            "footer_line_count": 0,
            "footer_font_size": 0,
            "footer_padding": {"x": 0, "y": 0},
        }

    load_font = font_loader or _load_default_footer_font
    scratch = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    draw = ImageDraw.Draw(scratch)

    minimum_text_strip_height = max(int(height * 0.052), 56)
    minimum_clear_strip_height = max(minimum_text_strip_height, int(height * 0.085))
    horizontal_padding = max(int(width * 0.04), 28)
    max_text_width = max(width - horizontal_padding * 2, 10)
    font_size = max(int(height * 0.0095), 11)
    font = load_font(font_size)
    lines = wrap_footer_lines(draw, text, font, max_width=max_text_width)
    spacing = max(font_size // 3, 2)
    line_boxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
    line_heights = [box[3] - box[1] for box in line_boxes]
    total_line_height = sum(line_heights) + max(len(lines) - 1, 0) * spacing
    vertical_padding = max(int(minimum_text_strip_height * 0.16), 8)
    text_strip_height = min(max(minimum_text_strip_height, total_line_height + vertical_padding * 2), height)
    wrapped_line_allowance = max(len(lines) - 2, 0) * spacing * 2
    clear_strip_height = min(
        max(minimum_clear_strip_height + wrapped_line_allowance, text_strip_height + wrapped_line_allowance),
        height,
    )
    clear_strip_top = max(height - clear_strip_height, 0)
    text_strip_top = clear_strip_top + max((clear_strip_height - text_strip_height) // 2, 0)
    max_text_height = max(text_strip_height - vertical_padding * 2, 1)

    return {
        "enabled": True,
        "position": "bottom_footer",
        "reserved_height": clear_strip_height,
        "reserved_ratio": round(clear_strip_height / max(float(height), 1.0), 4),
        "safe_bottom_inset": clear_strip_height,
        "content_canvas_height": clear_strip_top,
        "content_safe_area": {"x": 0, "y": 0, "width": width, "height": clear_strip_top},
        "footer_strip_box": {"x": 0, "y": clear_strip_top, "width": width, "height": clear_strip_height},
        "footer_text_box": {
            "x": horizontal_padding,
            "y": text_strip_top,
            "width": max_text_width,
            "height": text_strip_height,
        },
        "footer_line_count": len(lines),
        "footer_font_size": font_size,
        "footer_padding": {"x": horizontal_padding, "y": vertical_padding},
        "footer_text_max_height": max_text_height,
        "_lines": lines,
    }
