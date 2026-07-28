from __future__ import annotations

"""Canonical export sizes for Violyt creatives (format × platform).

L8, DALL·E mapping, and the chat Studio size picker should all follow this matrix.
"""

# (width, height) — export pixels the product promises
FormatPlatformSize = tuple[int, int]

_SIZES: dict[str, dict[str, FormatPlatformSize]] = {
    "static": {
        "linkedin": (1200, 627),
        "instagram": (1080, 1080),
        "x": (1200, 675),
        "twitter": (1200, 675),
        "facebook": (1200, 628),
        "default": (1080, 1080),
    },
    "carousel": {
        # Jiraaf education carousels are 4:5 portrait on LinkedIn/IG
        "linkedin": (1080, 1350),
        "instagram": (1080, 1350),
        "x": (1080, 1080),  # X carousels fit better square
        "twitter": (1080, 1080),
        "default": (1080, 1350),
    },
    "infographic": {
        "linkedin": (1080, 1350),
        "instagram": (1080, 1350),
        "x": (1080, 1350),
        "twitter": (1080, 1350),
        "default": (1080, 1350),
    },
}


def resolve_export_size(format_name: str, platform: str) -> FormatPlatformSize:
    """Return (width, height) for the selected format + platform."""
    fmt = (format_name or "static").strip().lower()
    plat = (platform or "linkedin").strip().lower()
    if fmt == "video":
        fmt = "static"
    if fmt not in _SIZES:
        fmt = "static"
    table = _SIZES[fmt]
    return table.get(plat) or table.get("default") or (1080, 1080)


def size_string(format_name: str, platform: str) -> str:
    w, h = resolve_export_size(format_name, platform)
    return f"{w}x{h}"


def canvas_label(format_name: str, platform: str) -> str:
    w, h = resolve_export_size(format_name, platform)
    if w == h:
        ratio = "1:1 square"
    elif h > w:
        ratio = "4:5 portrait" if abs(h / w - 1.25) < 0.05 else "portrait"
    else:
        ratio = "landscape"
    return f"{w}x{h} {ratio}"
