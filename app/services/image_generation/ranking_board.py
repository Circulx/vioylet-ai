from __future__ import annotations

"""Deterministic ranking board renderer (Pillow).

ROOT CAUSE: gpt-image / DALL·E cannot reliably bake:
- brand ice-blue background (often invents dark navy)
- letter-perfect country names
- correct country↔flag pairs
- no duplicated phrases / garbled text

For static_ranking country boards we draw from the approved blueprint
(real fonts + real flag PNGs + Brand Space logo composite).
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
    "holland": "nl",
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
    "mauritius": "mu",
    "venezuela": "ve",
    "zimbabwe": "zw",
    "iran": "ir",
    "cyprus": "cy",
    "luxembourg": "lu",
    "ireland": "ie",
    "hong kong": "hk",
    "belgium": "be",
    "denmark": "dk",
    "finland": "fi",
    "austria": "at",
    "portugal": "pt",
    "greece": "gr",
    "israel": "il",
    "qatar": "qa",
    "kuwait": "kw",
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
            Path(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                if bold
                else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            ),
            Path(
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
                if bold
                else "/System/Library/Fonts/Supplemental/Arial.ttf"
            ),
        ]
    )
    for path in candidates:
        try:
            if path.exists():
                return ImageFont.truetype(str(path), size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_rounded_flag(
    base: Image.Image,
    flag: Image.Image,
    xy: tuple[int, int],
    size: tuple[int, int],
    radius: int = 8,
) -> None:
    """Paste flag as a soft rounded tile (sample look)."""
    w, h = size
    flag_r = flag.resize((w, h), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    # Soft contact shadow under flag
    shadow = Image.new("RGBA", (w + 4, h + 4), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (2, 3, w + 1, h + 2), radius=radius, fill=(0, 40, 80, 35)
    )
    base.paste(shadow, (xy[0] - 1, xy[1] - 1), shadow)
    tile = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    tile.paste(flag_r, (0, 0), flag_r)
    out = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    out.paste(tile, (0, 0), mask)
    base.paste(out, xy, out)


def _draw_coin_chart_icon(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    size: int,
    orange: tuple[int, int, int],
) -> None:
    """Tiny gold coin + rising bars — matches sample row icon (not a $ sign)."""
    gold = (212, 168, 67)
    gold_dark = (174, 130, 53)
    r = max(8, size // 2)
    # Coin
    draw.ellipse((cx - r, cy - r + 2, cx + r - 4, cy + r - 2), fill=gold_dark)
    draw.ellipse((cx - r - 1, cy - r, cx + r - 5, cy + r - 4), fill=gold)
    # Rising bars behind/beside coin
    bar_w = max(3, size // 7)
    base_y = cy + r - 2
    for i, h_frac in enumerate((0.35, 0.55, 0.8)):
        bh = int(size * h_frac)
        bx0 = cx + r // 3 + i * (bar_w + 2)
        draw.rounded_rectangle(
            (bx0, base_y - bh, bx0 + bar_w, base_y),
            radius=1,
            fill=orange,
        )


def _country_iso(label: str) -> str | None:
    key = re.sub(r"[^a-z0-9.\s]", "", (label or "").lower()).strip()
    key = re.sub(r"\s+", " ", key)
    if key in _COUNTRY_ISO:
        return _COUNTRY_ISO[key]
    # Prefer longer name matches first to avoid weak substring hits
    for name, code in sorted(_COUNTRY_ISO.items(), key=lambda x: -len(x[0])):
        if len(name) < 3:
            continue
        if name == key or key.startswith(name + " ") or key.endswith(" " + name):
            return code
        if f" {name} " in f" {key} ":
            return code
    return None


def _fetch_flag(iso: str, width_px: int = 80) -> Image.Image | None:
    """Download a real flat flag PNG (flagcdn). Widths: 20/40/80/160/320/640."""
    code = (iso or "").lower().strip()
    if not code:
        return None
    # flagcdn only serves specific widths — map request to nearest supported
    supported = (20, 40, 80, 160, 320, 640)
    w = min(supported, key=lambda s: abs(s - int(width_px or 80)))
    urls = [
        f"https://flagcdn.com/w{w}/{code}.png",
        f"https://flagcdn.com/w80/{code}.png",
        f"https://flagcdn.com/w40/{code}.png",
        f"https://flagcdn.com/40x30/{code}.png",
    ]
    for url in urls:
        try:
            with urlopen(url, timeout=8) as resp:
                data = resp.read()
            return Image.open(BytesIO(data)).convert("RGBA")
        except Exception as exc:
            logger.warning(
                "ranking_board.flag_fetch_failed",
                iso=code,
                url=url,
                error=str(exc)[:120],
            )
    return None


def _truncate(text: str, max_chars: int) -> str:
    t = " ".join((text or "").split())
    if len(t) <= max_chars:
        return t
    cut = t[: max_chars - 1].rsplit(" ", 1)[0]
    return (cut or t[: max_chars - 1]) + "…"


def _dedupe_phrase(text: str, max_words: int = 6) -> str:
    """Remove accidental repeated halves ('Leading FDI source Leading FDI source')."""
    t = " ".join((text or "").split()).strip()
    if not t:
        return ""
    words = t.split()
    n = len(words)
    if n >= 4 and n % 2 == 0:
        half = n // 2
        if words[:half] == words[half:]:
            words = words[:half]
    # Collapse immediate word doubles: "tech tech"
    cleaned: list[str] = []
    for w in words:
        if cleaned and cleaned[-1].lower() == w.lower():
            continue
        cleaned.append(w)
    return " ".join(cleaned[:max_words])


# AI / LLM common garbles on ranking boards — fix before paint (infographic only)
_TEXT_FIXES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bESD\b", re.I), "USD"),
    (re.compile(r"\bESDs\b", re.I), "USD"),
    (re.compile(r"US\s*\$", re.I), "USD "),
    (re.compile(r"\$"), ""),
    (re.compile(r"\bEmp\b"), "Import"),
    (re.compile(r"\bImpp\b", re.I), "Import"),
    (re.compile(r"\bHAE\b"), "UAE"),
    (re.compile(r"\bASA\b"), "USA"),
    (re.compile(r"\bCONUTY\b", re.I), "Country"),
    (re.compile(r"\bhadge\b", re.I), "hedge"),
    (re.compile(r"\betch\b", re.I), "tech"),
    (re.compile(r"\binvestmet\b", re.I), "investment"),
    (re.compile(r"\bgrewth\b", re.I), "growth"),
    (re.compile(r"\binfrastruture\b", re.I), "infrastructure"),
    (re.compile(r"\bmanufacuring\b", re.I), "manufacturing"),
]


def sanitize_ranking_text(text: str) -> str:
    """Fix known garbled tokens so Pillow never paints ESD / etch / HAE."""
    t = " ".join((text or "").split()).strip()
    if not t:
        return ""
    for pat, repl in _TEXT_FIXES:
        t = pat.sub(repl, t)
    return _dedupe_phrase(t, max_words=12) if len(t.split()) <= 12 else t


def sanitize_ranking_rows(rows: list[dict]) -> list[dict]:
    """Sanitize every label/stat/fact before render."""
    out: list[dict] = []
    for row in rows or []:
        label = sanitize_ranking_text(str(row.get("label") or ""))
        stat = sanitize_ranking_text(str(row.get("stat") or ""))
        # Prefer USD spelling in amounts
        if re.search(r"\b\d", stat) and not re.search(r"\b(USD|₹|INR|%|Bn|bn|B)\b", stat):
            # leave as-is if already has currency
            pass
        facts_in = row.get("facts") or []
        if not isinstance(facts_in, list):
            facts_in = [facts_in]
        facts = []
        for f in facts_in:
            p = sanitize_ranking_text(str(f))
            p = _dedupe_phrase(p, max_words=6)
            if p and p.lower() not in {label.lower(), stat.lower()}:
                facts.append(p)
        if label:
            out.append({"label": label, "stat": stat, "facts": facts[:2]})
    return out


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
    """Paint ranking board matching sample_top_countries_investing.png EXACTLY.

    Anatomy (locked):
    - ice-blue BG · centered navy headline · soft supporting · short orange accent
    - EACH row: orange rank square | rounded flag | NAME + one short phrase | ₹ amount | coin icon
    - thin light dividers · compact orange CTA
    """
    bg = _hex_rgb(JIRAAF_BG)  # #E8F0F8 — NEVER dark navy
    navy = _hex_rgb(JIRAAF_NAVY)
    orange = _hex_rgb(JIRAAF_ORANGE)
    gray = (74, 85, 104)
    white = (255, 255, 255)
    divider = (210, 220, 232)

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    portrait = height >= width
    left = int(width * 0.08)
    right = int(width * 0.08)
    content_w = width - left - right
    top = int(height * 0.06)

    # --- Header (centered like sample) ---
    hl_font = _load_font(max(30, int(height * 0.042)), bold=True)
    hl = _truncate(sanitize_ranking_text(headline or "Ranking"), 42)
    hb = draw.textbbox((0, 0), hl, font=hl_font)
    hw = hb[2] - hb[0]
    draw.text(((width - hw) // 2, top), hl, font=hl_font, fill=navy)

    y = top + int(height * 0.055)
    if supporting_line:
        sub_font = _load_font(max(16, int(height * 0.024)), bold=False)
        sub = _truncate(sanitize_ranking_text(supporting_line), 56)
        sb = draw.textbbox((0, 0), sub, font=sub_font)
        sw = sb[2] - sb[0]
        draw.text(((width - sw) // 2, y), sub, font=sub_font, fill=gray)
        y += int(height * 0.038)
    # Short centered orange accent (sample DNA)
    accent_w = int(width * 0.14)
    ax0 = (width - accent_w) // 2
    draw.line(
        (ax0, y, ax0 + accent_w, y),
        fill=orange,
        width=max(3, int(height * 0.004)),
    )
    y += int(height * 0.028)

    usable_rows = [r for r in (rows or []) if (r.get("label") or "").strip()][:10]
    n = max(len(usable_rows), 1)
    table_bottom = int(height * (0.86 if cta or source_footer else 0.92))
    table_h = max(table_bottom - y, 80)
    row_h = max(int(table_h / n), 56 if portrait else 44)

    name_font = _load_font(max(18, int(height * 0.028)), bold=True)
    phrase_font = _load_font(max(14, int(height * 0.020)), bold=False)
    amount_font = _load_font(max(18, int(height * 0.028)), bold=True)
    rank_font = _load_font(max(14, int(height * 0.020)), bold=True)

    badge = max(28, min(40, int(row_h * 0.42)))
    flag_h = max(28, min(44, int(row_h * 0.52)))
    flag_w = int(flag_h * 1.45)
    icon_sz = max(26, min(36, int(row_h * 0.42)))

    for i, row in enumerate(usable_rows):
        ry = y + i * row_h
        # Thin divider under each row (sample)
        if i < n - 1:
            div_y = ry + row_h - 2
            draw.line((left, div_y, width - right, div_y), fill=divider, width=1)

        label = sanitize_ranking_text(str(row.get("label") or "").strip())
        # Never paint HAE / ASA
        if label.upper() == "HAE":
            label = "UAE"
        if label.upper() == "ASA":
            label = "USA"
        stat = sanitize_ranking_text(str(row.get("stat") or "").strip())
        # Prefer ₹ for India-facing ranks when amount is bare number
        if stat and re.match(r"^[\d.,]+\s*[Bb]?$", stat.strip()):
            num = stat.strip().rstrip("Bb").strip()
            stat = f"₹{num}B" if not num.endswith("B") else f"₹{num}"
        elif stat and re.match(r"^[\d.,]+$", stat.strip()):
            stat = f"₹{stat.strip()}B"

        facts = row.get("facts") or []
        if not isinstance(facts, list):
            facts = [str(facts)]
        phrase = ""
        for f in facts:
            p = _dedupe_phrase(sanitize_ranking_text(str(f)), max_words=5)
            if not p:
                continue
            if p.lower() in {label.lower(), stat.lower()}:
                continue
            # Skip if it looks like an amount duplicate
            if "₹" in p or re.search(r"\b\d+\s*B\b", p, re.I):
                continue
            phrase = p
            break
        if not phrase:
            phrase = "Strong economic ties"

        mid_y = ry + row_h // 2

        # 1) Orange rounded rank square
        bx0 = left
        by0 = mid_y - badge // 2
        draw.rounded_rectangle(
            (bx0, by0, bx0 + badge, by0 + badge),
            radius=6,
            fill=orange,
        )
        rank_txt = str(i + 1)
        rb = draw.textbbox((0, 0), rank_txt, font=rank_font)
        rw, rh = rb[2] - rb[0], rb[3] - rb[1]
        draw.text(
            (bx0 + (badge - rw) // 2, by0 + (badge - rh) // 2 - 1),
            rank_txt,
            font=rank_font,
            fill=white,
        )

        # 2) Real rounded flag for THIS country
        iso = _country_iso(label)
        fx = bx0 + badge + int(width * 0.018)
        fy = mid_y - flag_h // 2
        flag_img = _fetch_flag(iso, width_px=160) if iso else None
        if flag_img is not None:
            _draw_rounded_flag(img, flag_img, (fx, fy), (flag_w, flag_h), radius=7)
        else:
            draw.rounded_rectangle(
                (fx, fy, fx + flag_w, fy + flag_h),
                radius=7,
                fill=(200, 210, 220),
            )

        # 3) Name + ONE short phrase (simple retail tone)
        nx = fx + flag_w + int(width * 0.02)
        name_h = draw.textbbox((0, 0), "Ag", font=name_font)[3]
        phrase_h = draw.textbbox((0, 0), "Ag", font=phrase_font)[3]
        block_h = name_h + 4 + phrase_h
        name_y = mid_y - block_h // 2
        draw.text((nx, name_y), _truncate(label, 18), font=name_font, fill=navy)
        draw.text(
            (nx, name_y + name_h + 2),
            _truncate(phrase, 28),
            font=phrase_font,
            fill=gray,
        )

        # 4) Amount + 5) coin/chart icon on the right
        amount = _truncate(stat, 12) if stat else ""
        icon_x = width - right - icon_sz
        _draw_coin_chart_icon(draw, icon_x + icon_sz // 2, mid_y, icon_sz, orange)
        if amount:
            ab = draw.textbbox((0, 0), amount, font=amount_font)
            aw = ab[2] - ab[0]
            ah = ab[3] - ab[1]
            ax = icon_x - int(width * 0.02) - aw
            draw.text((ax, mid_y - ah // 2 - 1), amount, font=amount_font, fill=navy)

    # Compact CTA — sample language short (≤4 words), never long paragraph button
    if cta:
        cta_font = _load_font(max(14, int(height * 0.020)), bold=True)
        cta_txt = _truncate(_dedupe_phrase(cta, max_words=4), 22) or "Explore more"
        bbox = draw.textbbox((0, 0), cta_txt, font=cta_font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        pad_x, pad_y = 22, 10
        max_pill_w = int(width * 0.42)
        while tw + pad_x * 2 > max_pill_w and len(cta_txt) > 6:
            cta_txt = cta_txt[:-2].rstrip("…") + "…"
            bbox = draw.textbbox((0, 0), cta_txt, font=cta_font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        cx = width // 2
        cy = int(height * 0.925)
        pill = (
            cx - tw // 2 - pad_x,
            cy - th // 2 - pad_y,
            cx + tw // 2 + pad_x,
            cy + th // 2 + pad_y,
        )
        draw.rounded_rectangle(pill, radius=14, fill=orange)
        draw.text((cx - tw // 2, cy - th // 2 - 1), cta_txt, font=cta_font, fill=white)

    if source_footer:
        src_font = _load_font(max(11, int(height * 0.014)), bold=False)
        draw.text(
            (left, height - int(height * 0.035)),
            _truncate(sanitize_ranking_text(source_footer), 80),
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
    size: str = "1080x1350",
    logo_storage_path: str | None = None,
    logo_zone_instruction: str | None = None,
) -> str:
    """Render ranking board, composite Brand Space logo, save, return /storage URL."""
    try:
        w, h = map(int, size.split("x"))
    except Exception:
        w, h = 1080, 1350

    png = render_ranking_board_png(
        width=w,
        height=h,
        headline=sanitize_ranking_text(headline),
        supporting_line=sanitize_ranking_text(supporting_line),
        cta=sanitize_ranking_text(cta),
        source_footer=sanitize_ranking_text(source_footer),
        rows=sanitize_ranking_rows(rows),
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
    logger.info(
        "ranking_board.saved",
        storage_path=stored.storage_path,
        size=f"{w}x{h}",
        rows=len(rows or []),
    )
    return f"/storage/{stored.storage_path}"
