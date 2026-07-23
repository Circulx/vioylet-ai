from __future__ import annotations

"""In-chat text fix: wipe garbled AI text bands and redraw with real fonts.

Used by Edit → Save in the Violyt chat UI. Free, no external apps.
Does not draw brand-name logos — logo corner is left untouched.
"""

import re
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

from PIL import Image, ImageDraw, ImageFont

from app.core.logging import get_logger
from app.integrations.object_storage import get_object_storage

logger = get_logger(__name__)

_HEADLINE_COLOR = (27, 42, 74)  # navy
_SUPPORTING_COLOR = (70, 78, 96)
_BODY_COLOR = (55, 62, 80)
_CTA_COLOR = (255, 255, 255)
_CTA_BG = (232, 109, 47)  # orange accent


def _storage_path_from_url(image_url: str) -> str:
    """Convert /storage/{path} or full URL into relative storage path."""
    raw = (image_url or "").strip()
    if not raw:
        raise ValueError("image_url is required")
    # Strip origin if present
    if "://" in raw:
        raw = "/" + raw.split("://", 1)[1].split("/", 1)[-1]
    # Drop querystring
    raw = raw.split("?", 1)[0]
    if raw.startswith("/storage/"):
        return raw[len("/storage/") :]
    if raw.startswith("storage/"):
        return raw[len("storage/") :]
    return raw.lstrip("/")


def _parse_tenant_brand(storage_path: str) -> tuple[str, str]:
    parts = [p for p in storage_path.replace("\\", "/").split("/") if p]
    if len(parts) >= 2 and re.match(r"^[0-9a-fA-F-]{36}$", parts[0]):
        return parts[0], parts[1]
    if len(parts) >= 2:
        return parts[0], parts[1]
    raise ValueError(f"Cannot parse tenant/brand from path: {storage_path}")


def _load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates: list[Path] = []
    root = Path(__file__).resolve().parents[2]
    # Prefer project frontend fonts if present
    for family in ("Manrope", "DM_Sans"):
        family_dir = root / "frontend" / "public" / "fonts" / family
        if family_dir.exists():
            for p in sorted(family_dir.rglob("*.ttf")):
                name = p.name.lower()
                if bold and ("bold" in name or "semibold" in name or "700" in name):
                    candidates.insert(0, p)
                else:
                    candidates.append(p)
    # Windows / common system fonts
    windir = Path(r"C:\Windows\Fonts")
    if bold:
        candidates.extend(
            [
                windir / "segoeuib.ttf",
                windir / "arialbd.ttf",
                windir / "calibrib.ttf",
            ]
        )
    candidates.extend(
        [
            windir / "segoeui.ttf",
            windir / "arial.ttf",
            windir / "calibri.ttf",
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ]
    )
    for path in candidates:
        try:
            if path.exists():
                return ImageFont.truetype(str(path), size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _sample_fill(img: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """Average a few pixels just outside the wipe box for background match."""
    w, h = img.size
    x0, y0, x1, y1 = box
    samples: list[tuple[int, int, int]] = []
    px = img.load()
    probe_points = [
        (max(0, x0 - 4), min(h - 1, (y0 + y1) // 2)),
        (min(w - 1, x1 + 4), min(h - 1, (y0 + y1) // 2)),
        (min(w - 1, (x0 + x1) // 2), max(0, y0 - 4)),
        (min(w - 1, (x0 + x1) // 2), min(h - 1, y1 + 4)),
        (max(0, int(w * 0.05)), max(0, int(h * 0.02))),
    ]
    for x, y in probe_points:
        c = px[x, y]
        samples.append(c[:3])
    r = int(sum(s[0] for s in samples) / len(samples))
    g = int(sum(s[1] for s in samples) / len(samples))
    b = int(sum(s[2] for s in samples) / len(samples))
    return (r, g, b, 255)


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = (text or "").split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _draw_multiline(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    *,
    x: int,
    y: int,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    line_gap: int,
    center: bool = False,
    max_width: int | None = None,
) -> int:
    cy = y
    for line in lines:
        if center and max_width is not None:
            tw = int(draw.textlength(line, font=font))
            lx = x + max(0, (max_width - tw) // 2)
        else:
            lx = x
        draw.text((lx, cy), line, font=font, fill=fill)
        bbox = font.getbbox(line) if hasattr(font, "getbbox") else (0, 0, 0, int(getattr(font, "size", 16)))
        line_h = (bbox[3] - bbox[1]) if bbox else int(getattr(font, "size", 16))
        cy += int(line_h) + line_gap
    return cy


def apply_text_edits(
    *,
    image_url: str,
    headline: str = "",
    supporting_line: str = "",
    body: str = "",
    cta: str = "",
) -> str:
    """Wipe text bands (logo corner untouched) and redraw corrected copy. Returns new /storage URL."""
    storage = get_object_storage()
    storage_path = _storage_path_from_url(image_url)
    tenant_id, brand_id = _parse_tenant_brand(storage_path)
    image_bytes = storage.read_bytes(storage_path)

    img = Image.open(BytesIO(image_bytes)).convert("RGBA")
    w, h = img.size
    draw = ImageDraw.Draw(img)

    # Reserve tiny logo pocket — never overwrite real Brand Space logo
    logo_safe_left = int(w * 0.86)

    headline = (headline or "").strip()
    supporting_line = (supporting_line or "").strip()
    body = (body or "").strip()
    cta = (cta or "").strip()

    # ── Headline band (top center/left, clear of logo) ─────────────────────
    if headline:
        box = (int(w * 0.06), int(h * 0.03), logo_safe_left, int(h * 0.15))
        fill = _sample_fill(img, box)
        draw.rectangle(box, fill=fill)
        font_size = max(28, int(h * 0.045))
        font = _load_font(font_size, bold=True)
        max_tw = box[2] - box[0] - 8
        lines = _wrap_text(headline, font, max_tw, draw)[:3]
        _draw_multiline(
            draw,
            lines,
            x=box[0] + 4,
            y=box[1] + 6,
            font=font,
            fill=_HEADLINE_COLOR,
            line_gap=6,
            center=True,
            max_width=max_tw,
        )

    # ── Supporting line ────────────────────────────────────────────────────
    if supporting_line:
        box = (int(w * 0.08), int(h * 0.145), int(w * 0.92), int(h * 0.22))
        fill = _sample_fill(img, box)
        draw.rectangle(box, fill=fill)
        font = _load_font(max(16, int(h * 0.022)), bold=False)
        max_tw = box[2] - box[0] - 8
        lines = _wrap_text(supporting_line, font, max_tw, draw)[:3]
        _draw_multiline(
            draw,
            lines,
            x=box[0] + 4,
            y=box[1] + 4,
            font=font,
            fill=_SUPPORTING_COLOR,
            line_gap=4,
            center=True,
            max_width=max_tw,
        )

    # ── Body paragraph (mid card area) ─────────────────────────────────────
    if body:
        box = (int(w * 0.08), int(h * 0.23), int(w * 0.92), int(h * 0.42))
        fill = _sample_fill(img, box)
        # Soft rounded-ish fill via rectangle (good enough for correction)
        draw.rounded_rectangle(box, radius=18, fill=fill)
        font = _load_font(max(14, int(h * 0.018)), bold=False)
        max_tw = box[2] - box[0] - 28
        # Cap length so we don't overflow icons below
        truncated = body if len(body) < 420 else body[:417] + "…"
        lines = _wrap_text(truncated, font, max_tw, draw)[:8]
        _draw_multiline(
            draw,
            lines,
            x=box[0] + 14,
            y=box[1] + 14,
            font=font,
            fill=_BODY_COLOR,
            line_gap=5,
        )

    # ── CTA pill (bottom) ──────────────────────────────────────────────────
    if cta:
        font = _load_font(max(14, int(h * 0.02)), bold=True)
        pad_x, pad_y = 22, 10
        tw = int(draw.textlength(cta, font=font))
        pill_w = tw + pad_x * 2
        pill_h = int(h * 0.045) + pad_y
        cx = w // 2
        cy = int(h * 0.92)
        pill = (
            cx - pill_w // 2,
            cy - pill_h // 2,
            cx + pill_w // 2,
            cy + pill_h // 2,
        )
        draw.rounded_rectangle(pill, radius=pill_h // 2, fill=_CTA_BG)
        bbox = font.getbbox(cta) if hasattr(font, "getbbox") else (0, 0, 0, int(getattr(font, "size", 16)))
        text_h = (bbox[3] - bbox[1]) if bbox else int(getattr(font, "size", 16))
        draw.text(
            (cx - tw // 2, cy - text_h // 2 - 2),
            cta,
            font=font,
            fill=_CTA_COLOR,
        )

    out = BytesIO()
    img.convert("RGB").save(out, format="PNG", optimize=False)
    filename = f"edited-{uuid4().hex[:8]}.png"
    stored = storage.save_bytes(
        tenant_id=UUID(str(tenant_id)),
        brand_space_id=UUID(str(brand_id)),
        category="generated",
        filename=filename,
        content=out.getvalue(),
    )
    new_url = f"/storage/{stored.storage_path}"
    logger.info("image_text_edit.saved", source=storage_path, result=stored.storage_path)
    return new_url
