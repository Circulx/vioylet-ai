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

logger = get_logger(__name__)

_LOGO_MAX_WIDTH_RATIO = 0.12
# Minimum logo short-side in pixels (prevents tiny, unreadable logos).
_LOGO_MIN_PX = 48
# Padding from the canvas edge when placing the logo (in pixels).
_LOGO_EDGE_PADDING = 32
# Logo background fill color (used only for solid-background logos without transparency).
_LOGO_BG_COLOR = (255, 255, 255, 0)  # transparent


def _make_background_transparent(img: Image.Image) -> Image.Image:
    """Detect solid white/light/dark background at corners and key it out to transparent, then trim excess padding."""
    img = img.convert("RGBA")
    datas = img.getdata()
    w, h = img.size
    if w <= 2 or h <= 2:
        return img

    corners = [
        datas[0],                   # Top-left
        datas[w - 1],               # Top-right
        datas[w * (h - 1)],         # Bottom-left
        datas[w * h - 1]            # Bottom-right
    ]

    from collections import Counter
    corner_colors = [c[:3] for c in corners]
    most_common_color, count = Counter(corner_colors).most_common(1)[0]

    # If at least 2 corners match, check if it's a solid white, black or gray background
    if count >= 2:
        r_bg, g_bg, b_bg = most_common_color
        is_white = r_bg > 215 and g_bg > 215 and b_bg > 215
        is_black = r_bg < 40 and g_bg < 40 and b_bg < 40
        is_gray = 110 < r_bg < 150 and 110 < g_bg < 150 and 110 < b_bg < 150

        if is_white or is_black or is_gray:
            new_data = []
            tolerance = 45  # tolerance for compression artifacts in JPEGs
            for item in datas:
                r, g, b, a = item
                if abs(r - r_bg) < tolerance and abs(g - g_bg) < tolerance and abs(b - b_bg) < tolerance:
                    new_data.append((r, g, b, 0))  # Set transparency
                else:
                    new_data.append(item)
            img.putdata(new_data)

            # Auto-crop bounding box to trim away empty margins
            bbox = img.getbbox()
            if bbox:
                img = img.crop(bbox)

    return img


def _composite_logo(
    base_bytes: bytes,
    logo_bytes: bytes,
    logo_zone_instruction: str | None,
    canvas_width: int,
    canvas_height: int,
) -> bytes:
    """Composite the brand logo onto the base image and return the merged PNG bytes.

    Args:
        base_bytes: Raw bytes of the AI-generated base image.
        logo_bytes: Raw bytes of the brand logo file (any PIL-supported format).
        logo_zone_instruction: Free-text description of where to place the logo
            (e.g. "bottom-right corner, 40px margin").
        canvas_width: Width of the generated canvas.
        canvas_height: Height of the generated canvas.

    Returns:
        PNG bytes of the composited image.
    """
    base_img = Image.open(BytesIO(base_bytes)).convert("RGBA")
    logo_raw = Image.open(BytesIO(logo_bytes))
    logo_img = _make_background_transparent(logo_raw).convert("RGBA")

    # Scale logo so it fits within max width ratio while keeping aspect ratio
    max_logo_w = max(int(canvas_width * _LOGO_MAX_WIDTH_RATIO), _LOGO_MIN_PX)
    logo_w, logo_h = logo_img.size
    scale = min(max_logo_w / logo_w, (max_logo_w * logo_h / logo_w) / logo_h if logo_h else 1)
    # Always scale down if needed; never scale up past original size
    if scale < 1.0:
        new_w = max(int(logo_w * scale), _LOGO_MIN_PX)
        new_h = max(int(logo_h * scale), _LOGO_MIN_PX)
        logo_img = logo_img.resize((new_w, new_h), Image.LANCZOS)
    logo_w, logo_h = logo_img.size

    # Force logo placement to top-right corner always per user request
    pad = _LOGO_EDGE_PADDING

    # Determine coordinates for the logo icon (top-right)
    x = canvas_width - logo_w - pad
    y = pad

    # Paste logo icon with alpha channel as mask
    base_img.paste(logo_img, (x, y), logo_img)

    out = BytesIO()
    base_img.convert("RGB").save(out, format="PNG", optimize=False)
    return out.getvalue()


class DalleService:
    """Async OpenAI Image Generation service (gpt-image-1 or dall-e-3) with brand logo overlay."""

    def __init__(self, api_key: str | None = None) -> None:
        self.settings = get_settings()
        self.api_key = api_key or self.settings.openai_api_key
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
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
        """
        if not self.client:
            logger.error("dalle.client_not_configured")
            raise ValueError("OpenAI API key not configured for DALL-E")

        # ── Map platform format sizes to supported DALL-E canvas sizes ──────────
        # gpt-image-1: 1024×1024, 1536×1024 (landscape), 1024×1536 (portrait)
        # dall-e-3:    1024×1024, 1792×1024,              1024×1792
        is_gpt_image = "gpt-image" in self.model
        square_size = "1024x1024"
        landscape_size = "1536x1024" if is_gpt_image else "1792x1024"
        portrait_size = "1024x1536" if is_gpt_image else "1024x1792"

        dalle_size = square_size
        canvas_width, canvas_height = 1024, 1024
        if size:
            w, h = map(int, size.split("x"))
            if w > h:
                dalle_size = landscape_size
                canvas_width, canvas_height = (1536, 1024) if is_gpt_image else (1792, 1024)
            elif w < h:
                dalle_size = portrait_size
                canvas_width, canvas_height = (1024, 1536) if is_gpt_image else (1024, 1792)

        logger.info(
            "dalle.generate_start",
            model=self.model,
            size=dalle_size,
            prompt_len=len(prompt),
            has_logo=bool(logo_storage_path),
            has_client=bool(self.client),
        )

        # ── Call gpt-image-1 ─────────────────────────────────────────────────────
        try:
            kwargs: dict = {
                "model": self.model,
                "prompt": prompt[:6000],
                "size": dalle_size,
                "n": 1,
            }
            if is_gpt_image:
                kwargs["quality"] = "high"
            else:
                kwargs["quality"] = "standard"
            response = await self.client.images.generate(**kwargs)
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

        # gpt-image-1 returns base64 in data[0].b64_json; dall-e-3 returns URL in data[0].url
        image_url = getattr(data[0], "url", None)
        b64_json = getattr(data[0], "b64_json", None)

        if b64_json:
            # Log the raw b64 content for diagnostics
            logger.info(
                "dalle.b64_raw",
                b64_len=len(b64_json),
                b64_preview=b64_json[:200] if b64_json else "empty",
            )
            logger.info("dalle.decode_base64", b64_len=len(b64_json))
            image_bytes = base64.b64decode(b64_json)
            logger.info("dalle.decode_complete", decoded_len=len(image_bytes))
        elif image_url:
            logger.info("dalle.download_start", url=image_url[:60])
            import asyncio

            loop = asyncio.get_running_loop()

            def _download() -> bytes:
                with urlopen(image_url, timeout=60) as resp:
                    return resp.read()

            image_bytes = await loop.run_in_executor(None, _download)
        else:
            raise RuntimeError(
                f"Image response did not include url or b64_json (model={self.model})"
            )

        # ── Optional: composite brand logo onto the generated image ──────────────
        if logo_storage_path:
            try:
                logo_bytes = self.storage.read_bytes(logo_storage_path)
                if logo_bytes:
                    image_bytes = _composite_logo(
                        base_bytes=image_bytes,
                        logo_bytes=logo_bytes,
                        logo_zone_instruction=logo_zone_instruction,
                        canvas_width=canvas_width,
                        canvas_height=canvas_height,
                    )
                    logger.info(
                        "dalle.logo_composited",
                        logo_path=logo_storage_path,
                        zone="top-right",
                    )
                else:
                    logger.warning(
                        "dalle.logo_empty_bytes",
                        logo_path=logo_storage_path,
                    )
            except Exception as logo_exc:
                # Logo composite failure must never break the pipeline —
                # fall back to the base image without a logo.
                logger.warning(
                    "dalle.logo_composite_failed",
                    logo_path=logo_storage_path,
                    error=str(logo_exc)[:300],
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
