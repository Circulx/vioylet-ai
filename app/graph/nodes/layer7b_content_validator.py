from __future__ import annotations

"""Layer 7.5: Content Validation & Cleanup.

Sits between Copy Engine (L7) and Visual Reasoning (L8).
Validates, spell-checks, truncates, and fact-flags all copy
before it is used for image generation.
"""

import re
from copy import deepcopy

from app.core.logging import get_logger
from app.graph.models.layer7_models import CopyOutput, CopySlide
from app.graph.models.layer7b_models import (
    ContentValidationOutput,
    FactFlag,
    SpellingFix,
    Truncation,
)
from app.graph.state import ViolytState

logger = get_logger(__name__)

# ── Limits for image-safe text (Jiraaf sample style: numbers > paragraphs) ──
MAX_HEADLINE_CHARS = 64
MAX_SUPPORTING_LINE_CHARS = 90
MAX_BODY_CHARS = 100
MAX_CTA_CHARS = 36
MAX_SLIDE_HEADLINE_CHARS = 50
MAX_SLIDE_BODY_CHARS = 90

# ── Common misspellings in AI output ────────────────────────────────────────
COMMON_FIXES: dict[str, str] = {
    "recieve": "receive",
    "acheive": "achieve",
    "occured": "occurred",
    "seperate": "separate",
    "definately": "definitely",
    "accomodate": "accommodate",
    "occassion": "occasion",
    "neccessary": "necessary",
    "goverment": "government",
    "enviroment": "environment",
    "managment": "management",
    "developement": "development",
    "recomend": "recommend",
    "guarentee": "guarantee",
    "garauntee": "guarantee",
    "guarantsed": "guaranteed",
    "maintainance": "maintenance",
    "performence": "performance",
    "consistant": "consistent",
    "independant": "independent",
    "occurence": "occurrence",
    "existance": "existence",
    "persistance": "persistence",
    "refered": "referred",
    "prefered": "preferred",
    "transfered": "transferred",
    "benificial": "beneficial",
    "calender": "calendar",
    "catagory": "category",
    "commited": "committed",
    "concious": "conscious",
    "embarass": "embarrass",
    "harrass": "harass",
    "millenial": "millennial",
    "noticable": "noticeable",
    "privelege": "privilege",
    "publically": "publicly",
    "succesful": "successful",
    "tommorow": "tomorrow",
    "untill": "until",
    "wierd": "weird",
    "yeild": "yield",
    "yeilds": "yields",
    "yizids": "yields",
    "investmet": "investment",
    "agroach": "approach",
    "grewth": "growth",
    "meximize": "maximize",
    "rcturns": "returns",
    "liquildity": "liquidity",
    "eunjoy": "enjoy",
    "riisk": "risk",
    "notlon": "notion",
    "belew": "below",
    "bresking": "breaking",
    "penaity": "penalty",
    "inerast": "interest",
    "intrate": "interest",
}

# ── AI filler / generic phrases to strip ────────────────────────────────────
AI_FILLER_PATTERNS = [
    r"\bin today's (?:fast-paced |ever-changing |dynamic |digital )?(?:world|landscape|era|environment)\b",
    r"\bgame[- ]?changer\b",
    r"\blook no further\b",
    r"\btake your .+ to the next level\b",
    r"\bseamlessly\b",
    r"\bholistic(?:ally)?\b",
    r"\bsynerg(?:y|ize|istic)\b",
    r"\bparadigm shift\b",
    r"\bnot just .+, but\b",
    r"\bimagine a world where\b",
]

# ── Financial / regulated claim patterns ────────────────────────────────────
FINANCIAL_CLAIM_PATTERNS = [
    (r"\b\d+(?:\.\d+)?%\s*(?:return|yield|interest|growth|p\.a\.|per annum|annually)\b", "high"),
    (r"\bguaranteed\s+(?:return|income|yield|growth)\b", "high"),
    (r"\brisk[- ]?free\b", "high"),
    (r"\b(?:SEBI|RBI|IRDA|IRDAI|AMFI)\b", "medium"),
    (r"\b(?:assured|fixed)\s+(?:return|income)\b", "medium"),
    (r"\b\d+(?:\.\d+)?x\s+(?:return|growth|multiplier)\b", "medium"),
    (r"\boutperform(?:s|ed|ing)?\b", "low"),
    (r"\bbeat(?:s|ing)?\s+(?:inflation|market|benchmark|FD)\b", "low"),
]


def _fix_spelling(text: str) -> tuple[str, list[SpellingFix]]:
    """Apply common spelling fixes and return corrected text + list of fixes."""
    fixes: list[SpellingFix] = []
    corrected = text
    for wrong, right in COMMON_FIXES.items():
        pattern = re.compile(re.escape(wrong), re.IGNORECASE)
        matches = pattern.findall(corrected)
        if matches:
            corrected = pattern.sub(right, corrected)
            for m in matches:
                fixes.append(SpellingFix(original=m, corrected=right, field=""))
    return corrected, fixes


def _strip_ai_filler(text: str) -> str:
    """Remove generic AI filler phrases."""
    cleaned = text
    for pattern in AI_FILLER_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    # Clean up double spaces left behind
    cleaned = re.sub(r"  +", " ", cleaned).strip()
    return cleaned


def _truncate(text: str, max_len: int) -> tuple[str, int | None]:
    """Truncate text to max_len. Returns (text, original_len_if_truncated)."""
    if len(text) <= max_len:
        return text, None
    original_len = len(text)
    # Truncate at last word boundary before max_len
    truncated = text[:max_len].rsplit(" ", 1)[0]
    if not truncated:
        truncated = text[:max_len]
    return truncated.rstrip("., ") + "…", original_len


def _scan_fact_flags(text: str, field: str) -> list[FactFlag]:
    """Scan text for financial/regulatory claims that need verification."""
    flags: list[FactFlag] = []
    for pattern, risk in FINANCIAL_CLAIM_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            flags.append(FactFlag(
                claim=match if isinstance(match, str) else match[0],
                field=field,
                risk_level=risk,
            ))
    return flags


def _validate_field(
    text: str,
    field_name: str,
    max_chars: int,
    all_spelling_fixes: list[SpellingFix],
    all_truncations: list[Truncation],
    all_fact_flags: list[FactFlag],
) -> str:
    """Run full validation pipeline on a single text field."""
    if not text:
        return text

    # 1. Spelling fixes
    corrected, fixes = _fix_spelling(text)
    for fix in fixes:
        fix.field = field_name
    all_spelling_fixes.extend(fixes)

    # 2. Strip AI filler
    corrected = _strip_ai_filler(corrected)

    # 3. Fact flags
    flags = _scan_fact_flags(corrected, field_name)
    all_fact_flags.extend(flags)

    # 4. Truncation
    corrected, orig_len = _truncate(corrected, max_chars)
    if orig_len is not None:
        all_truncations.append(Truncation(
            field=field_name,
            original_len=orig_len,
            truncated_len=len(corrected),
        ))

    return corrected


async def layer7b_content_validator(state: ViolytState) -> dict:
    """Validate and clean all copy before visual rendering."""
    copy: CopyOutput | None = state.get("copy")
    if not copy:
        logger.error("content_validator.missing_copy")
        raise ValueError("Layer 7 copy is required for content validation")

    all_spelling_fixes: list[SpellingFix] = []
    all_truncations: list[Truncation] = []
    all_fact_flags: list[FactFlag] = []

    # Deep-copy to avoid mutating original
    validated = deepcopy(copy)

    # Validate main copy fields
    validated.headline = _validate_field(
        validated.headline, "headline", MAX_HEADLINE_CHARS,
        all_spelling_fixes, all_truncations, all_fact_flags,
    )
    if validated.supporting_line:
        validated.supporting_line = _validate_field(
            validated.supporting_line, "supporting_line", MAX_SUPPORTING_LINE_CHARS,
            all_spelling_fixes, all_truncations, all_fact_flags,
        )
    validated.body = _validate_field(
        validated.body, "body", MAX_BODY_CHARS,
        all_spelling_fixes, all_truncations, all_fact_flags,
    )
    validated.cta = _validate_field(
        validated.cta, "cta", MAX_CTA_CHARS,
        all_spelling_fixes, all_truncations, all_fact_flags,
    )

    # Validate slide copy
    new_slides: list[CopySlide] = []
    for slide in validated.slide_copy:
        slide.headline = _validate_field(
            slide.headline, f"slide_{slide.slide_number}_headline",
            MAX_SLIDE_HEADLINE_CHARS,
            all_spelling_fixes, all_truncations, all_fact_flags,
        )
        slide.body = _validate_field(
            slide.body, f"slide_{slide.slide_number}_body",
            MAX_SLIDE_BODY_CHARS,
            all_spelling_fixes, all_truncations, all_fact_flags,
        )
        if slide.cta:
            slide.cta = _validate_field(
                slide.cta, f"slide_{slide.slide_number}_cta",
                MAX_CTA_CHARS,
                all_spelling_fixes, all_truncations, all_fact_flags,
            )
        new_slides.append(slide)
    validated.slide_copy = new_slides

    validation_passed = (
        len(all_spelling_fixes) == 0
        and len(all_fact_flags) == 0
    )

    validation_output = ContentValidationOutput(
        validated_copy=validated,
        spelling_fixes=all_spelling_fixes,
        grammar_fixes=[],  # LLM-based grammar pass can be added later
        truncations=all_truncations,
        fact_flags=all_fact_flags,
        validation_passed=validation_passed,
    )

    logger.info(
        "content_validator.complete",
        spelling_fixes=len(all_spelling_fixes),
        truncations=len(all_truncations),
        fact_flags=len(all_fact_flags),
        passed=validation_passed,
    )

    return {
        "content_validation": validation_output,
        "copy": validated,  # Overwrite copy with validated version
    }
