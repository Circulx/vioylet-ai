from __future__ import annotations

"""DALL-E / gpt-image-1 image generation service with brand logo overlay.

After generating the base image, the service optionally composites the brand
logo onto the image using PIL.  This is the only reliable way to embed an
exact brand logo — AI models cannot accurately render arbitrary logos.
"""

import base64
import re
from io import BytesIO
from urllib.request import urlopen
from uuid import UUID, uuid4

from openai import AsyncOpenAI
from PIL import Image

from app.core.config import get_settings
from app.core.logging import get_logger
from app.integrations.object_storage import get_object_storage
from app.prompts.brand_copy_tone import JIRAAF_SEBI_DISCLAIMER

logger = get_logger(__name__)

# Keep logo compact — Brand Space assets often ship with large empty padding.
_LOGO_MAX_WIDTH_RATIO = 0.11
# Minimum logo short-side in pixels (prevents tiny, unreadable logos).
_LOGO_MIN_PX = 36
# Padding from the canvas edge when placing the logo (in pixels).
_LOGO_EDGE_PADDING = 12
# Logo background fill color (used only for solid-background logos without transparency).
_LOGO_BG_COLOR = (255, 255, 255, 0)  # transparent
_SEBI_FOOTER_COLOR = (55, 70, 95, 255)  # darker navy-gray — readable on ice-blue
_SEBI_FOOTER_BG = (232, 240, 248, 255)  # ice-blue #E8F0F8


def _flatten_rgba_to_brand_bg(img: Image.Image) -> Image.Image:
    """Flatten any transparency onto Jiraaf's ice-blue background.

    Some generated images and composited logo assets can retain transparency.
    Saving RGBA directly as RGB turns transparent areas black, which caused the
    sudden black-slide bug. Always flatten before saving.
    """
    rgba = img.convert("RGBA")
    bg = Image.new("RGBA", rgba.size, _SEBI_FOOTER_BG)
    bg.alpha_composite(rgba)
    return bg


def _ensure_light_brand_background(img: Image.Image) -> Image.Image:
    """If AI returned a near-black canvas, rekey dark background to ice-blue.

    Corner-sample check: when most edge samples are near-black, treat contiguous
    near-black pixels as background (keeps navy icons/text). Fixes sudden black slides.
    """
    rgba = img.convert("RGBA")
    w, h = rgba.size
    if w < 8 or h < 8:
        return rgba

    px = rgba.load()
    sample_pts = [
        (2, 2),
        (w // 2, 2),
        (w - 3, 2),
        (2, h // 2),
        (w - 3, h // 2),
        (2, h - 3),
        (w // 2, h - 3),
        (w - 3, h - 3),
    ]
    dark = 0
    for x, y in sample_pts:
        r, g, b, _a = px[x, y]
        if (r + g + b) / 3 < 45:
            dark += 1
    if dark < 5:
        return rgba

    # Rekey near-black background pixels to brand ice-blue (preserve colored content)
    datas = list(rgba.getdata())
    out = []
    br, bg_, bb_, ba_ = _SEBI_FOOTER_BG
    for r, g, b, a in datas:
        if (r + g + b) / 3 < 38 and abs(r - g) < 18 and abs(g - b) < 18:
            out.append((br, bg_, bb_, 255))
        else:
            out.append((r, g, b, a))
    rgba.putdata(out)
    logger.info("dalle.black_bg_rekeyed", dark_corners=dark, size=f"{w}x{h}")
    return rgba


def _make_background_transparent(img: Image.Image) -> Image.Image:
    """Key out solid logo padding (white / light / ice-blue / gray / black) and tight-crop.

    Brand Space logos often ship with a large opaque light background. That empty
    padding made the composited logo look huge and pushed headlines away.
    """
    img = img.convert("RGBA")
    w, h = img.size
    if w <= 2 or h <= 2:
        return img

    datas = list(img.getdata())
    corners = [
        datas[0][:3],
        datas[w - 1][:3],
        datas[w * (h - 1)][:3],
        datas[w * h - 1][:3],
    ]
    from collections import Counter

    most_common_color, count = Counter(corners).most_common(1)[0]
    r_bg, g_bg, b_bg = most_common_color
    lum = (r_bg + g_bg + b_bg) / 3

    # Treat common logo pads as removable background
    is_white = r_bg > 200 and g_bg > 200 and b_bg > 200
    is_black = lum < 40
    is_gray = abs(r_bg - g_bg) < 18 and abs(g_bg - b_bg) < 18 and 90 < lum < 180
    # Ice-blue / soft brand pads (e.g. #E8F0F8-ish)
    is_ice = (
        r_bg > 200
        and g_bg > 210
        and b_bg > 220
        and b_bg >= g_bg >= r_bg - 10
    )
    # Near-white cream pads
    is_cream = r_bg > 230 and g_bg > 225 and b_bg > 210 and lum > 220

    if count >= 2 and (is_white or is_black or is_gray or is_ice or is_cream):
        tolerance = 52 if (is_white or is_ice or is_cream) else 40
        new_data = []
        for r, g, b, a in datas:
            if abs(r - r_bg) < tolerance and abs(g - g_bg) < tolerance and abs(b - b_bg) < tolerance:
                new_data.append((r, g, b, 0))
            else:
                new_data.append((r, g, b, a))
        img.putdata(new_data)

    # Always tight-crop to non-transparent content (removes leftover empty margins)
    bbox = img.getbbox()
    if bbox:
        # Small safety inset only if crop is tiny
        img = img.crop(bbox)

    return img


def _sample_corner_fill(base_img: Image.Image, canvas_width: int, canvas_height: int) -> tuple[int, int, int, int]:
    """Pick a fill color from just outside the small logo wipe zone (matches background)."""
    px = base_img.load()
    # Sample left of the compact logo corner so we don't pull headline colors.
    xs = [
        max(0, int(canvas_width * 0.88)),
        max(0, int(canvas_width * 0.90)),
        max(0, int(canvas_width * 0.92)),
    ]
    y = min(16, canvas_height - 1)
    samples = [px[x, y][:3] for x in xs]
    r = int(sum(s[0] for s in samples) / len(samples))
    g = int(sum(s[1] for s in samples) / len(samples))
    b = int(sum(s[2] for s in samples) / len(samples))
    return (r, g, b, 255)


def _wipe_top_right_corner(
    base_img: Image.Image,
    canvas_width: int,
    canvas_height: int,
    *,
    width_ratio: float = 0.14,
    height_ratio: float = 0.09,
) -> Image.Image:
    """Remove AI-hallucinated logos / 'Brand Logo' placeholders before compositing.

    Keep wipe SMALL so it never eats into the headline (user saw 'o..' truncation).
    """
    from PIL import ImageDraw

    wipe_w = min(int(canvas_width * width_ratio), canvas_width)
    wipe_h = min(int(canvas_height * height_ratio), canvas_height)
    wipe_box = (canvas_width - wipe_w, 0, canvas_width, wipe_h)
    fill = _sample_corner_fill(base_img, canvas_width, canvas_height)
    ImageDraw.Draw(base_img).rectangle(wipe_box, fill=fill)
    return base_img


def _composite_logo(
    base_bytes: bytes,
    logo_bytes: bytes,
    logo_zone_instruction: str | None,
    canvas_width: int,
    canvas_height: int,
) -> bytes:
    """Wipe a small top-right pocket, then paste the Brand Space logo AS-IS (icon + wordmark OK)."""
    base_img = Image.open(BytesIO(base_bytes)).convert("RGBA")
    # Clear AI-drawn fake logos / placeholder boxes before placing the real asset.
    base_img = _wipe_top_right_corner(base_img, canvas_width, canvas_height)
    logo_raw = Image.open(BytesIO(logo_bytes))
    logo_img = _make_background_transparent(logo_raw).convert("RGBA")
    # Tight crop again after any residual alpha fringe
    content_box = logo_img.getbbox()
    if content_box:
        logo_img = logo_img.crop(content_box)

    max_logo_w = max(int(canvas_width * _LOGO_MAX_WIDTH_RATIO), _LOGO_MIN_PX)
    max_logo_h = max(int(canvas_height * 0.065), _LOGO_MIN_PX)
    logo_w, logo_h = logo_img.size
    scale = min(max_logo_w / max(logo_w, 1), max_logo_h / max(logo_h, 1), 1.0)
    new_w = max(int(logo_w * scale), 1)
    new_h = max(int(logo_h * scale), 1)
    if new_h > max_logo_h:
        shrink = max_logo_h / new_h
        new_w = max(int(new_w * shrink), 1)
        new_h = max_logo_h
    logo_img = logo_img.resize((new_w, new_h), Image.LANCZOS)
    logo_w, logo_h = logo_img.size

    pad = _LOGO_EDGE_PADDING

    x = canvas_width - logo_w - pad
    y = pad
    base_img.paste(logo_img, (x, y), logo_img)

    out = BytesIO()
    fixed = _ensure_light_brand_background(base_img)
    _flatten_rgba_to_brand_bg(fixed).convert("RGB").save(out, format="PNG", optimize=False)
    return out.getvalue()


def _load_footer_font(size: int):
    """Prefer a clean sans on Windows/macOS; fall back to PIL default."""
    from PIL import ImageFont

    candidates = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap_footer_lines(text: str, font, max_width: int, draw) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _composite_sebi_footer(
    base_bytes: bytes,
    canvas_width: int,
    canvas_height: int,
    footer_text: str | None = None,
) -> bytes:
    """Paint exact SEBI disclaimer into a bottom safe strip — never rely on the image model."""
    from PIL import ImageDraw

    text = (footer_text or JIRAAF_SEBI_DISCLAIMER).strip()
    if not text:
        return base_bytes

    base_img = Image.open(BytesIO(base_bytes)).convert("RGBA")
    draw = ImageDraw.Draw(base_img)

    # Larger, readable disclaimer (was ~9–11px and nearly invisible).
    font_size = max(13, min(16, int(canvas_width * 0.0135)))
    font = _load_footer_font(font_size)
    side_pad = max(16, int(canvas_width * 0.035))
    max_text_w = canvas_width - side_pad * 2
    lines = _wrap_footer_lines(text, font, max_text_w, draw)
    line_gap = max(2, int(font_size * 0.28))
    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_heights.append(max(bbox[3] - bbox[1], font_size))
    text_block_h = sum(line_heights) + line_gap * max(len(lines) - 1, 0)
    band_pad_y = max(8, int(canvas_height * 0.007))
    band_h = text_block_h + band_pad_y * 2
    # Hard cap: footer band up to ~14% so larger type still fits
    max_band = int(canvas_height * 0.14)
    if band_h > max_band:
        font_size = max(11, font_size - 2)
        font = _load_footer_font(font_size)
        lines = _wrap_footer_lines(text, font, max_text_w, draw)
        line_heights = [
            max(
                draw.textbbox((0, 0), l, font=font)[3] - draw.textbbox((0, 0), l, font=font)[1],
                font_size,
            )
            for l in lines
        ]
        text_block_h = sum(line_heights) + line_gap * max(len(lines) - 1, 0)
        band_h = min(text_block_h + band_pad_y * 2, max_band)

    # Wipe footer strip only — leave chips / ranking rows above intact
    y0 = canvas_height - band_h
    draw.rectangle((0, y0, canvas_width, canvas_height), fill=_SEBI_FOOTER_BG)

    y = y0 + band_pad_y
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = max(side_pad, (canvas_width - tw) // 2)
        draw.text((x, y), line, font=font, fill=_SEBI_FOOTER_COLOR)
        y += line_heights[i] + line_gap

    out = BytesIO()
    fixed = _ensure_light_brand_background(base_img)
    _flatten_rgba_to_brand_bg(fixed).convert("RGB").save(out, format="PNG", optimize=False)
    return out.getvalue()


def _resize_to_export(image_bytes: bytes, target_w: int, target_h: int) -> bytes:
    """Stretch API canvas to exact export size — no letterbox bars, no crop.

    Letterboxing 2:3 → 4:5 left ice-blue side strips that look like a second
    background. Stretching keeps one seamless full-bleed field (slight aspect
    change is acceptable for social export).
    """
    img = _ensure_light_brand_background(Image.open(BytesIO(image_bytes)))
    src_w, src_h = img.size
    if src_w <= 0 or src_h <= 0 or target_w <= 0 or target_h <= 0:
        return image_bytes
    if (src_w, src_h) == (target_w, target_h):
        out = BytesIO()
        _flatten_rgba_to_brand_bg(img).convert("RGB").save(out, format="PNG", optimize=False)
        return out.getvalue()

    img = img.resize((target_w, target_h), Image.LANCZOS)
    out = BytesIO()
    _flatten_rgba_to_brand_bg(img).convert("RGB").save(out, format="PNG", optimize=False)
    return out.getvalue()


class DalleService:
    """Async OpenAI Image Generation service (gpt-image-1 or dall-e-3) with brand logo overlay."""

    def __init__(self, api_key: str | None = None) -> None:
        self.settings = get_settings()
        self.api_key = api_key or self.settings.openai_api_key
        self.image_timeout_s = float(
            getattr(self.settings, "image_generation_timeout_seconds", 180) or 180
        )
        self.image_quality = str(
            getattr(self.settings, "image_quality", "medium") or "medium"
        ).strip().lower()
        self.client = (
            AsyncOpenAI(api_key=self.api_key, timeout=self.image_timeout_s)
            if self.api_key
            else None
        )
        self.storage = get_object_storage()
        self.model = getattr(self.settings, "image_model", "gpt-image-1") or "gpt-image-1"

    async def generate_and_save(
        self,
        tenant_id: str | UUID,
        brand_space_id: str | UUID,
        prompt: str,
        size: str = "1024x1024",
        logo_storage_path: str | None = None,
        logo_zone_instruction: str | None = None,
        composite_sebi_footer: bool = False,
        wipe_reserved_corner: bool = False,
        quality: str | None = None,
    ) -> str:
        """Call gpt-image-1, optionally composite the brand logo, save, and return URL path.

        Args:
            tenant_id: Tenant UUID.
            brand_space_id: Brand space UUID.
            prompt: The fully-expanded art direction prompt.
            size: Requested canvas size (e.g. "1200x627").
            logo_storage_path: Optional filesystem path to the brand logo asset.
                If provided, the logo will be composited onto the generated image.
            logo_zone_instruction: Free-text description of logo placement
                (e.g. "bottom-right corner, 40px margin").
            composite_sebi_footer: When True, paint exact SEBI legal footer via Pillow.
                Pass True for carousel slides only — static/infographic must stay False.
        """
        if not self.client:
            logger.error("dalle.client_not_configured")
            raise ValueError("OpenAI API key not configured for DALL-E")

        # Target export size (product size). API only supports 3 aspect buckets — we resize after.
        export_w, export_h = map(int, size.split("x")) if size and "x" in size else (1024, 1024)
        is_gpt_image = "gpt-image" in self.model
        square_size = "1024x1024"
        landscape_size = "1536x1024" if is_gpt_image else "1792x1024"
        portrait_size = "1024x1536" if is_gpt_image else "1024x1792"

        dalle_size = square_size
        if export_w > export_h:
            dalle_size = landscape_size
        elif export_w < export_h:
            dalle_size = portrait_size

        logger.info(
            "dalle.generate_start",
            model=self.model,
            export_size=f"{export_w}x{export_h}",
            api_size=dalle_size,
            prompt_len=len(prompt),
            has_logo=bool(logo_storage_path),
            has_client=bool(self.client),
            timeout_s=self.image_timeout_s,
        )

        # ── Call gpt-image-1 ─────────────────────────────────────────────────────
        import asyncio

        try:
            kwargs: dict = {
                "model": self.model,
                "prompt": prompt[:6000],
                "size": dalle_size,
                "n": 1,
            }
            if is_gpt_image:
                default_q = self.image_quality if self.image_quality in ("low", "medium", "high") else "medium"
                q = (quality or default_q).strip().lower()
                if q not in ("low", "medium", "high"):
                    q = default_q
                kwargs["quality"] = q
            else:
                kwargs["quality"] = "hd" if self.image_quality == "high" else "standard"
            logger.info(
                "dalle.generate_params",
                model=self.model,
                size=dalle_size,
                quality=kwargs.get("quality"),
                timeout_s=self.image_timeout_s,
            )
            response = await asyncio.wait_for(
                self.client.images.generate(**kwargs),
                timeout=self.image_timeout_s,
            )
        except asyncio.TimeoutError as e:
            logger.error("dalle.generate_timeout", timeout_s=self.image_timeout_s, model=self.model)
            raise TimeoutError(
                f"Image generation timed out after {self.image_timeout_s:.0f}s "
                f"(model={self.model}). Try IMAGE_QUALITY=medium."
            ) from e
        except Exception as e:
            logger.error(
                "dalle.generate_failed",
                error_type=type(e).__name__,
                error_msg=str(e)[:500],
                prompt_snippet=prompt[:200],
            )
            raise

        data = response.data
        if not data:
            raise RuntimeError("DALL-E response did not contain image data")

        image_url = getattr(data[0], "url", None)
        b64_json = getattr(data[0], "b64_json", None)

        if b64_json:
            logger.info("dalle.decode_base64", b64_len=len(b64_json))
            image_bytes = base64.b64decode(b64_json)
        elif image_url:
            logger.info("dalle.download_start", url=image_url[:60])
            loop = asyncio.get_running_loop()

            def _download() -> bytes:
                with urlopen(image_url, timeout=60) as resp:
                    return resp.read()

            image_bytes = await loop.run_in_executor(None, _download)
        else:
            raise RuntimeError(
                f"Image response did not include url or b64_json (model={self.model})"
            )

        # Resize API canvas → exact export size (Instagram/LinkedIn/X)
        try:
            image_bytes = _resize_to_export(image_bytes, export_w, export_h)
            logger.info("dalle.resized_to_export", export=f"{export_w}x{export_h}")
        except Exception as resize_exc:
            logger.warning("dalle.resize_failed", error=str(resize_exc)[:200])

        # Strip AI-hallucinated corner logos even when no Brand Space asset is available.
        if wipe_reserved_corner and not logo_storage_path:
            try:
                base_img = Image.open(BytesIO(image_bytes))
                real_w, real_h = base_img.size
                wiped = _wipe_top_right_corner(
                    base_img.convert("RGBA"), real_w, real_h
                )
                out = BytesIO()
                _flatten_rgba_to_brand_bg(wiped).convert("RGB").save(out, format="PNG", optimize=False)
                image_bytes = out.getvalue()
                logger.info("dalle.corner_wiped", canvas=f"{real_w}x{real_h}")
            except Exception as wipe_exc:
                logger.warning("dalle.corner_wipe_failed", error=str(wipe_exc)[:200])

        # Logo composite using REAL image dimensions after resize
        if logo_storage_path:
            try:
                logo_bytes = self.storage.read_bytes(logo_storage_path)
                if logo_bytes:
                    base_img = Image.open(BytesIO(image_bytes))
                    real_w, real_h = base_img.size
                    image_bytes = _composite_logo(
                        base_bytes=image_bytes,
                        logo_bytes=logo_bytes,
                        logo_zone_instruction=logo_zone_instruction,
                        canvas_width=real_w,
                        canvas_height=real_h,
                    )
                    logger.info(
                        "dalle.logo_composited",
                        logo_path=logo_storage_path,
                        zone="top-right",
                        canvas=f"{real_w}x{real_h}",
                    )
                else:
                    logger.warning("dalle.logo_empty_bytes", logo_path=logo_storage_path)
            except Exception as logo_exc:
                logger.warning(
                    "dalle.logo_composite_failed",
                    logo_path=logo_storage_path,
                    error=str(logo_exc)[:300],
                )

        # Exact SEBI footer via Pillow (AI text bake alone drops it constantly)
        if composite_sebi_footer:
            try:
                base_img = Image.open(BytesIO(image_bytes))
                real_w, real_h = base_img.size
                image_bytes = _composite_sebi_footer(
                    base_bytes=image_bytes,
                    canvas_width=real_w,
                    canvas_height=real_h,
                )
                logger.info(
                    "dalle.sebi_footer_composited",
                    canvas=f"{real_w}x{real_h}",
                )
            except Exception as footer_exc:
                logger.warning(
                    "dalle.sebi_footer_failed",
                    error=str(footer_exc)[:300],
                )

        # ── Save final image to object storage ───────────────────────────────────
        filename = f"dalle-{uuid4().hex[:8]}.png"
        stored = self.storage.save_bytes(
            tenant_id=UUID(str(tenant_id)),
            brand_space_id=UUID(str(brand_space_id)),
            category="generated",
            filename=filename,
            content=image_bytes,
        )

        logger.info("dalle.save_complete", storage_path=stored.storage_path)

        # Build the final public URL mapping to /storage static path
        return f"/storage/{stored.storage_path}"
