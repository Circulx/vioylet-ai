from __future__ import annotations

"""Deterministic LinkedIn ranking board renderer.

ROOT CAUSE FIX: gpt-image / DALL·E cannot reliably bake:
- letter-perfect country names
- correct country↔flag pairs
- aligned ranking tables
- no watermarks / invented rows

For static_ranking creatives we draw the board ourselves from the approved
blueprint (real fonts + real flag PNGs + Brand Space logo composite).
"""

import re
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen
from uuid import UUID, uuid4

from PIL import Image, ImageDraw, ImageFont

from app.core.logging import get_logger
from app.integrations.object_storage import get_object_storage
from app.prompts.brand_copy_tone import JIRAAF_BG, JIRAAF_NAVY, JIRAAF_ORANGE
from app.services.image_generation.dalle_service import _composite_logo

logger = get_logger(__name__)

# Common country labels → ISO 3166-1 alpha-2 for flagcdn
_COUNTRY_ISO: dict[str, str] = {
    "india": "in",
    "usa": "us",
    "u.s.a": "us",
    "u.s.": "us",
    "united states": "us",
    "united states of america": "us",
    "uk": "gb",
    "u.k.": "gb",
    "u.k": "gb",
    "united kingdom": "gb",
    "britain": "gb",
    "great britain": "gb",
    "germany": "de",
    "japan": "jp",
    "china": "cn",
    "australia": "au",
    "canada": "ca",
    "france": "fr",
    "brazil": "br",
    "russia": "ru",
    "turkey": "tr",
    "argentina": "ar",
    "south africa": "za",
    "singapore": "sg",
    "indonesia": "id",
    "mexico": "mx",
    "italy": "it",
    "spain": "es",
    "south korea": "kr",
    "korea": "kr",
    "saudi arabia": "sa",
    "uae": "ae",
    "united arab emirates": "ae",
    "netherlands": "nl",
    "switzerland": "ch",
    "sweden": "se",
    "norway": "no",
    "poland": "pl",
    "thailand": "th",
    "vietnam": "vn",
    "malaysia": "my",
    "philippines": "ph",
    "egypt": "eg",
    "nigeria": "ng",
    "pakistan": "pk",
    "bangladesh": "bd",
    "new zealand": "nz",
    "european central bank": "eu",
    "ecb": "eu",
    "eurozone": "eu",
    "euro area": "eu",
    "bank of england": "gb",
    "boe": "gb",
    "bank of japan": "jp",
    "boj": "jp",
    "people's bank": "cn",
    "people's bank of china": "cn",
    "pboc": "cn",
    "federal reserve": "us",
    "fed": "us",
    "rbi": "in",
    "reserve bank of india": "in",
}


def _hex_rgb(hex_code: str) -> tuple[int, int, int]:
    h = (hex_code or "").lstrip("#")
    if len(h) != 6:
        return (0, 57, 117)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates: list[Path] = []
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
            Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf"),
        ]
    )
    for path in candidates:
        try:
            if path.exists():
                return ImageFont.truetype(str(path), size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _country_iso(label: str) -> str | None:
    key = re.sub(r"[^a-z0-9.\s]", "", (label or "").lower()).strip()
    key = re.sub(r"\s+", " ", key)
    if key in _COUNTRY_ISO:
        return _COUNTRY_ISO[key]
    # partial contains
    for name, code in _COUNTRY_ISO.items():
        if name in key or key in name:
            return code
    return None


def _fetch_flag(iso: str, width_px: int = 40) -> Image.Image | None:
    """Download a real flat flag PNG (flagcdn). Cached per process via URL fetch."""
    code = (iso or "").lower().strip()
    if not code:
        return None
    urls = [
        f"https://flagcdn.com/w{width_px}/{code}.png",
        f"https://flagcdn.com/40x30/{code}.png",
    ]
    for url in urls:
        try:
            with urlopen(url, timeout=8) as resp:
                data = resp.read()
            img = Image.open(BytesIO(data)).convert("RGBA")
            return img
        except Exception as exc:
            logger.warning("ranking_board.flag_fetch_failed", iso=code, url=url, error=str(exc)[:120])
    return None


def _truncate(text: str, max_chars: int) -> str:
    t = " ".join((text or "").split())
    if len(t) <= max_chars:
        return t
    cut = t[: max_chars - 1].rsplit(" ", 1)[0]
    return (cut or t[: max_chars - 1]) + "…"


def render_ranking_board_png(
    *,
    width: int,
    height: int,
    headline: str,
    supporting_line: str = "",
    cta: str = "",
    source_footer: str = "",
    rows: list[dict],
) -> bytes:
    """Paint a strict LinkedIn landscape ranking table. Returns PNG bytes."""
    bg = _hex_rgb(JIRAAF_BG)
    navy = _hex_rgb(JIRAAF_NAVY)
    orange = _hex_rgb(JIRAAF_ORANGE)
    gray = (74, 85, 104)
    white = (255, 255, 255)
    row_bg = (255, 255, 255)
    divider = (210, 220, 232)

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    # Margins for LinkedIn 1200x627 — leave only a tight logo pocket on the right
    left = int(width * 0.035)
    right = int(width * 0.035)
    top = int(height * 0.05)
    content_w = width - left - right

    # Headline can use most of the width; logo is tight-cropped and small (~11%)
    hl_font = _load_font(max(26, int(height * 0.052)), bold=True)
    hl = _truncate(headline or "Ranking", 56)
    draw.text((left, top), hl, font=hl_font, fill=navy)

    y = top + int(height * 0.065)
    if supporting_line:
        sub_font = _load_font(max(14, int(height * 0.026)), bold=False)
        sub = _truncate(supporting_line, 78)
        draw.text((left, y), sub, font=sub_font, fill=gray)
        y += int(height * 0.045)
    else:
        y += int(height * 0.015)

    # Ranking table area
    usable_rows = [r for r in (rows or []) if (r.get("label") or "").strip()][:15]
    n = max(len(usable_rows), 1)
    table_bottom = int(height * (0.90 if not cta else 0.84))
    table_top = y
    table_h = max(table_bottom - table_top, 40)
    row_h = max(int(table_h / n), 28)

    name_font = _load_font(max(12, int(height * 0.026)), bold=True)
    stat_font = _load_font(max(12, int(height * 0.026)), bold=True)
    fact_font = _load_font(max(10, int(height * 0.020)), bold=False)

    flag_h = max(16, min(26, row_h - 8))
    flag_w = int(flag_h * 1.5)

    # Fixed non-overlapping columns (long names like "Bank of England" must not collide with %)
    col_flag = left
    col_name = left + flag_w + 10
    name_col_w = int(content_w * 0.26)
    col_stat = col_name + name_col_w + 8
    stat_col_w = int(content_w * 0.12)
    col_fact = col_stat + stat_col_w + 8
    fact_col_w = int(content_w * 0.28)
    col_fact2 = col_fact + fact_col_w + 8

    for i, row in enumerate(usable_rows):
        ry = table_top + i * row_h
        # Alternating soft row band for scanability
        if i % 2 == 0:
            draw.rounded_rectangle(
                (left - 4, ry, width - right + 4, ry + row_h - 2),
                radius=6,
                fill=row_bg,
            )
        else:
            draw.line((left, ry + row_h - 2, width - right, ry + row_h - 2), fill=divider, width=1)

        label = str(row.get("label") or "").strip()
        stat = str(row.get("stat") or "").strip()
        facts = row.get("facts") or []
        if not isinstance(facts, list):
            facts = [str(facts)]
        fact1 = _truncate(str(facts[0]) if facts else "", 32)
        fact2 = _truncate(str(facts[1]) if len(facts) > 1 else "", 32)

        # Real flag
        iso = _country_iso(label)
        flag_img = _fetch_flag(iso, width_px=40) if iso else None
        fy = ry + max(2, (row_h - flag_h) // 2)
        if flag_img is not None:
            flag_img = flag_img.resize((flag_w, flag_h), Image.LANCZOS)
            img.paste(flag_img, (col_flag, fy), flag_img if flag_img.mode == "RGBA" else None)
        else:
            draw.rounded_rectangle(
                (col_flag, fy, col_flag + flag_w, fy + flag_h),
                radius=3,
                fill=(200, 210, 220),
            )

        text_y = ry + max(4, (row_h - int(height * 0.026)) // 2)
        # Clip name to its column so it never overlaps the rate
        name_txt = _truncate(label, 22)
        # Further shrink by measured width if needed
        while name_txt and draw.textlength(name_txt, font=name_font) > name_col_w:
            name_txt = name_txt[:-2].rstrip("…") + "…"
            if len(name_txt) <= 4:
                break
        draw.text((col_name, text_y), name_txt, font=name_font, fill=navy)
        draw.text((col_stat, text_y), _truncate(stat, 12), font=stat_font, fill=orange)
        if fact1:
            draw.text((col_fact, text_y), fact1, font=fact_font, fill=gray)
        if fact2:
            draw.text((col_fact2, text_y), fact2, font=fact_font, fill=gray)

    # Optional CTA pill
    if cta:
        cta_font = _load_font(max(13, int(height * 0.026)), bold=True)
        cta_txt = _truncate(cta, 36)
        bbox = draw.textbbox((0, 0), cta_txt, font=cta_font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        pad_x, pad_y = 18, 8
        cx = width // 2
        cy = int(height * 0.92)
        pill = (
            cx - tw // 2 - pad_x,
            cy - th // 2 - pad_y,
            cx + tw // 2 + pad_x,
            cy + th // 2 + pad_y,
        )
        draw.rounded_rectangle(pill, radius=20, fill=orange)
        draw.text((cx - tw // 2, cy - th // 2 - 1), cta_txt, font=cta_font, fill=white)

    # Compact source line (not SEBI)
    if source_footer:
        src_font = _load_font(max(10, int(height * 0.018)), bold=False)
        draw.text(
            (left, height - int(height * 0.045)),
            _truncate(source_footer, 80),
            font=src_font,
            fill=gray,
        )

    out = BytesIO()
    img.save(out, format="PNG", optimize=False)
    return out.getvalue()


async def generate_ranking_board_and_save(
    *,
    tenant_id: str | UUID,
    brand_space_id: str | UUID,
    headline: str,
    supporting_line: str = "",
    cta: str = "",
    source_footer: str = "",
    rows: list[dict],
    size: str = "1200x627",
    logo_storage_path: str | None = None,
    logo_zone_instruction: str | None = None,
) -> str:
    """Render ranking board, composite Brand Space logo, save, return /storage URL."""
    try:
        w, h = map(int, size.split("x"))
    except Exception:
        w, h = 1200, 627

    png = render_ranking_board_png(
        width=w,
        height=h,
        headline=headline,
        supporting_line=supporting_line,
        cta=cta,
        source_footer=source_footer,
        rows=rows,
    )

    if logo_storage_path:
        try:
            storage = get_object_storage()
            logo_bytes = storage.read_bytes(logo_storage_path)
            if logo_bytes:
                png = _composite_logo(
                    base_bytes=png,
                    logo_bytes=logo_bytes,
                    logo_zone_instruction=logo_zone_instruction,
                    canvas_width=w,
                    canvas_height=h,
                )
        except Exception as exc:
            logger.warning("ranking_board.logo_composite_failed", error=str(exc)[:200])

    storage = get_object_storage()
    filename = f"rank-{uuid4().hex[:8]}.png"
    stored = storage.save_bytes(
        tenant_id=UUID(str(tenant_id)),
        brand_space_id=UUID(str(brand_space_id)),
        category="generated",
        filename=filename,
        content=png,
    )
    url = f"/storage/{stored.storage_path}"
    logger.info(
        "ranking_board.saved",
        url=url,
        rows=len(rows),
        size=f"{w}x{h}",
    )
    return url
