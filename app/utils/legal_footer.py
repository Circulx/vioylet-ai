from __future__ import annotations

import re
from typing import Any


LEGAL_FOOTER_MARKERS = (
    "disclaimer",
    "subject to",
    "read all",
    "offer document",
    "offer-related",
    "offer related",
    "sebi",
    "registration number",
    "stock broker",
    "nse member",
    "registered address",
    "private limited",
    "guaranteed",
    "assured returns",
    "credit risk",
    "credit risks",
    "market risk",
    "market risks",
    "default risk",
    "default risks",
    "default in payment",
)

LEGAL_FOOTER_ANCHORS = (
    "disclaimer",
    "subject to",
    "sebi",
    "registration number",
)

LEGAL_FOOTER_STOP_PREFIXES = (
    "follow ",
    "sources:",
    "source:",
    "visit ",
    "website:",
)


def expand_legal_footer_text(
    footer_text: Any,
    *,
    source_text: Any = None,
    structured_data: dict[str, Any] | None = None,
) -> str:
    """Prefer the full OCR legal footer when a saved footer only contains the final disclaimer line."""
    baseline = _normalize_text(footer_text)
    structured_data = structured_data if isinstance(structured_data, dict) else {}
    text_sources = [
        source_text,
        structured_data.get("text"),
        structured_data.get("extracted_text"),
        structured_data.get("ocr_text"),
        structured_data.get("copy_lines"),
    ]

    best = baseline
    for value in text_sources:
        candidate = _extract_legal_footer_block(value)
        if _is_better_legal_footer(candidate, best):
            best = candidate
    return best


def _extract_legal_footer_block(value: Any) -> str:
    lines = _legal_text_lines(value)
    if not lines:
        return ""

    anchor_indices = [
        index
        for index, line in enumerate(lines)
        if _is_legal_anchor_line(line)
    ]
    if not anchor_indices:
        return ""

    anchor_index = next(
        (
            index
            for index in reversed(anchor_indices)
            if "disclaimer" in lines[index].casefold()
        ),
        anchor_indices[-1],
    )

    start = anchor_index
    while start > 0 and _is_legal_prefix_line(lines[start - 1]):
        start -= 1

    end = anchor_index
    while end + 1 < len(lines) and _is_legal_continuation_line(lines[end + 1]):
        end += 1

    block = lines[start : end + 1]
    if len(block) < 2 and not any("disclaimer" in line.casefold() for line in block):
        return ""
    return _normalize_text(" ".join(block))


def _legal_text_lines(value: Any) -> list[str]:
    if isinstance(value, list):
        raw_lines: list[str] = []
        for item in value:
            if isinstance(item, dict):
                raw_lines.append(str(item.get("text") or item.get("line") or item.get("content") or ""))
            else:
                raw_lines.append(str(item or ""))
    else:
        raw_lines = re.split(r"[\r\n]+", str(value or ""))

    lines: list[str] = []
    for raw_line in raw_lines:
        line = _normalize_text(raw_line)
        if line:
            lines.append(line)
    return lines


def _is_legal_anchor_line(line: str) -> bool:
    lowered = line.casefold()
    return any(marker in lowered for marker in LEGAL_FOOTER_ANCHORS)


def _is_legal_prefix_line(line: str) -> bool:
    lowered = line.casefold()
    if any(lowered.startswith(prefix) for prefix in LEGAL_FOOTER_STOP_PREFIXES):
        return False
    return any(marker in lowered for marker in LEGAL_FOOTER_MARKERS)


def _is_legal_continuation_line(line: str) -> bool:
    lowered = line.casefold()
    if any(lowered.startswith(prefix) for prefix in LEGAL_FOOTER_STOP_PREFIXES):
        return False
    return any(marker in lowered for marker in LEGAL_FOOTER_MARKERS)


def _is_better_legal_footer(candidate: str, current: str) -> bool:
    if not candidate:
        return False
    if not current:
        return True
    if candidate.casefold() == current.casefold():
        return False
    if len(candidate) <= len(current) + 30:
        return False
    return _legal_signal_count(candidate) >= max(2, _legal_signal_count(current))


def _legal_signal_count(text: str) -> int:
    lowered = text.casefold()
    return sum(1 for marker in LEGAL_FOOTER_MARKERS if marker in lowered)


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()
