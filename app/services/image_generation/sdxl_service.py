from __future__ import annotations

import hashlib
from io import BytesIO
from uuid import UUID, uuid4

from PIL import Image, ImageDraw, ImageFont

from app.core.config import get_settings
from app.core.logging import get_logger
from app.integrations.object_storage import get_object_storage

logger = get_logger(__name__)


class SdxlService:
    """Stable Diffusion XL Image Generation service or mock placeholder fallback."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.storage = get_object_storage()

    async def generate_and_save(
        self,
        tenant_id: str | UUID,
        brand_space_id: str | UUID,
        prompt: str,
        size: str = "1024x1024",
    ) -> str:
        """Fallback mock SDXL image generator to avoid breaking the pipeline."""
        logger.info("sdxl.generate_mock", size=size, prompt_len=len(prompt))

        # Size extraction
        size_map = {
            "1024x1024": (1024, 1024),
            "1200x627": (1200, 627),
            "1080x1080": (1080, 1080),
            "1200x675": (1200, 675),
            "1080x1920": (1080, 1920),
        }
        width, height = size_map.get(size, (1024, 1024))
        if "x" in size:
            try:
                width, height = map(int, size.split("x"))
            except ValueError:
                pass

        # Deterministic generation using PIL
        digest = hashlib.sha256(prompt.encode("utf-8")).digest()
        
        # Determine theme coloring
        bg_color = (245, 246, 248)
        primary_color = (26, 82, 118)
        accent_color = (
            100 + digest[0] % 100,
            120 + digest[1] % 100,
            140 + digest[2] % 100,
        )

        img = Image.new("RGB", (width, height), color=bg_color)
        draw = ImageDraw.Draw(img)

        # Draw a polished mock creative placeholder
        margin_w = int(width * 0.06)
        margin_h = int(height * 0.06)
        draw.rectangle(
            [margin_w, margin_h, width - margin_w, height - margin_h],
            fill=(255, 255, 255),
            outline=primary_color,
            width=3,
        )

        # Gradient-like accent bar at top
        draw.rectangle(
            [margin_w, margin_h, width - margin_w, margin_h + 8],
            fill=primary_color,
        )

        # Circle / visual decoration
        cx1 = int(width * 0.12)
        cy1 = int(height * 0.22)
        cx2 = int(width * 0.48)
        cy2 = int(height * 0.62)
        draw.ellipse([cx1, cy1, cx2, cy2], fill=accent_color)

        # Inner accent circle
        inner_w = int((cx2 - cx1) * 0.45)
        inner_h = int((cy2 - cy1) * 0.45)
        icx = (cx1 + cx2) // 2
        icy = (cy1 + cy2) // 2
        draw.ellipse([icx - inner_w, icy - inner_h, icx + inner_w, icy + inner_h], fill=(255, 255, 255, 200))

        # Try to load a font, fall back to default
        try:
            font_large = ImageFont.truetype("arial.ttf", max(28, int(height * 0.045)))
            font_medium = ImageFont.truetype("arial.ttf", max(18, int(height * 0.028)))
            font_small = ImageFont.truetype("arial.ttf", max(14, int(height * 0.020)))
        except (OSError, IOError):
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Title text
        title = "AI-Generated Visual Placeholder"
        draw.text(
            (int(width * 0.55), int(height * 0.20)),
            title,
            fill=primary_color,
            font=font_large,
        )

        # Prompt summary (truncated, wrapped)
        prompt_short = prompt[:200] + ("..." if len(prompt) > 200 else "")
        words = prompt_short.split()
        lines = []
        current_line = []
        max_chars_per_line = 45
        char_count = 0
        for word in words:
            if char_count + len(word) + 1 > max_chars_per_line:
                lines.append(" ".join(current_line))
                current_line = [word]
                char_count = len(word)
            else:
                current_line.append(word)
                char_count += len(word) + 1
        if current_line:
            lines.append(" ".join(current_line))

        y_offset = int(height * 0.32)
        for line in lines[:8]:
            draw.text(
                (int(width * 0.55), y_offset),
                line,
                fill=(80, 80, 80),
                font=font_medium,
            )
            y_offset += int(height * 0.045)

        # Footer label
        draw.text(
            (int(width * 0.55), int(height * 0.82)),
            "SDXL Fallback · DALL-E 3 unavailable",
            fill=(150, 150, 150),
            font=font_small,
        )
        draw.text(
            (int(width * 0.55), int(height * 0.87)),
            f"Size: {width}x{height}",
            fill=(150, 150, 150),
            font=font_small,
        )
        
        # Save to storage
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        
        filename = f"sdxl-fallback-{uuid4().hex[:8]}.png"
        stored = self.storage.save_bytes(
            tenant_id=UUID(str(tenant_id)),
            brand_space_id=UUID(str(brand_space_id)),
            category="generated",
            filename=filename,
            content=buffer.getvalue(),
        )

        return f"/storage/{stored.storage_path}"
