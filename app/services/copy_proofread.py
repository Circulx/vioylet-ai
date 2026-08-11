from __future__ import annotations

"""Copy quality: spelling + grammar pass for Creative Blueprint text.

Local spellcheck is always applied (lazy singleton + thread offload).
Optional LLM polish is time-boxed so the pipeline never hangs.
"""

import asyncio
import re
from typing import TYPE_CHECKING, Any, Iterable

from app.core.logging import get_logger
from app.services.llm.openai_service import OpenAIService

if TYPE_CHECKING:
    from app.graph.models.layer7c_models import CreativeBlueprint

logger = get_logger(__name__)

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]{2,}")
_LLM_PROOFREAD_TIMEOUT_SEC = 45.0
_SPELL: Any = None
_SPELL_LOCK = asyncio.Lock()

_PROTECTED_TERMS = {
    "jiraaf",
    "cognixia",
    "violyt",
    "linkedin",
    "instagram",
    "sebi",
    "epfo",
    "epf",
    "gsecs",
    "g-secs",
    "etfs",
    "etf",
    "cta",
    "roi",
    "saas",
    "fintech",
    "b2b",
    "b2c",
    "usd",
    "fdi",
    "udan",
    "uae",
    "usa",
    "uk",
}


_DETERMINISTIC_FIXES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bESD\b", re.I), "USD"),
    (re.compile(r"\bESDs\b", re.I), "USD"),
    (re.compile(r"\bHAE\b"), "UAE"),
    (re.compile(r"\bASA\b"), "USA"),
    (re.compile(r"\bADAN\b", re.I), "UDAN"),
    (re.compile(r"\bADAN\s+Scheme\b", re.I), "UDAN Scheme"),
    (re.compile(r"\bEmp\b"), "Import"),
    (re.compile(r"\bImpp\b", re.I), "Import"),
    (re.compile(r"\betch\b", re.I), "tech"),
    (re.compile(r"\bhadge\b", re.I), "hedge"),
    (re.compile(r"\bCONUTY\b", re.I), "Country"),
    (re.compile(r"\binvestmet\b", re.I), "investment"),
    (re.compile(r"\bgrewth\b", re.I), "growth"),
]


def _deterministic_token_fix(text: str) -> str:
    t = text or ""
    for pat, repl in _DETERMINISTIC_FIXES:
        t = pat.sub(repl, t)
    return t


def _blueprint_cls():
    from app.graph.models.layer7c_models import CreativeBlueprint

    return CreativeBlueprint


def _build_spellchecker():
    from spellchecker import SpellChecker

    spell = SpellChecker(distance=2)
    spell.word_frequency.load_words(_PROTECTED_TERMS)
    return spell


async def _get_spellchecker():
    global _SPELL
    if _SPELL is not None:
        return _SPELL
    async with _SPELL_LOCK:
        if _SPELL is None:
            _SPELL = await asyncio.to_thread(_build_spellchecker)
            logger.info("copy_proofread.spellchecker_ready")
    return _SPELL


def _iter_string_paths(obj: Any, path: tuple = ()) -> Iterable[tuple[tuple, str]]:
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            yield from _iter_string_paths(item, path + (i,))
    elif isinstance(obj, dict):
        for key, value in obj.items():
            if key in {
                "format",
                "platform",
                "intent",
                "layout_archetype",
                "text_density",
                "zone_id",
                "role",
                "icon_hint",
            }:
                if isinstance(value, str):
                    continue
            yield from _iter_string_paths(value, path + (key,))


def _set_path(obj: Any, path: tuple, value: str) -> None:
    cur = obj
    for part in path[:-1]:
        cur = cur[part]
    cur[path[-1]] = value


def _local_spellcheck_text(text: str, spell) -> str:
    if not text:
        return text
    text = _deterministic_token_fix(text)
    if not spell:
        return text

    def replace(match: re.Match[str]) -> str:
        word = match.group(0)
        lower = word.lower()
        if lower in _PROTECTED_TERMS or any(ch.isdigit() for ch in word):
            return word
        if spell.unknown([lower]):
            candidates = spell.candidates(lower) or set()
            if not candidates:
                return word
            best = min(candidates, key=lambda c: (abs(len(c) - len(lower)), c))
            if word.isupper():
                return best.upper()
            if word[0].isupper():
                return best.capitalize()
            return best
        return word

    return _WORD_RE.sub(replace, text)


def _apply_local_spellcheck(blueprint: CreativeBlueprint, spell) -> CreativeBlueprint:
    CreativeBlueprint = _blueprint_cls()
    data = blueprint.model_dump()
    fixes = 0
    for path, value in _iter_string_paths(data):
        corrected = _local_spellcheck_text(value, spell)
        if corrected != value:
            _set_path(data, path, corrected)
            fixes += 1
    if fixes:
        logger.info("copy_proofread.local_fixes", fixes=fixes)
    return CreativeBlueprint.model_validate(data)


async def local_spellcheck_blueprint(blueprint: CreativeBlueprint) -> CreativeBlueprint:
    """Correct obvious misspellings without blocking the event loop."""
    try:
        spell = await _get_spellchecker()
    except Exception as exc:  # pragma: no cover
        logger.warning("copy_proofread.spellchecker_unavailable", error=str(exc))
        return blueprint
    return await asyncio.to_thread(_apply_local_spellcheck, blueprint, spell)


async def llm_proofread_blueprint(blueprint: CreativeBlueprint) -> CreativeBlueprint:
    """LLM grammar + spelling polish with a hard timeout."""
    CreativeBlueprint = _blueprint_cls()
    service = OpenAIService(model="gpt-4o-mini")
    system = """You are a professional copy editor for marketing creatives.
Fix ONLY spelling, grammar, punctuation, and obvious typos.
Do NOT rewrite voice, invent new claims, change meaning, or remove structure.
Keep numbers, brand names, product names, hashtags, URLs, and CTAs intact.
Return the same CreativeBlueprint JSON with corrected text fields only.
No markdown. No preamble. Raw JSON only."""
    user = (
        "Proofread this Creative Blueprint JSON. Fix spelling/grammar typos "
        "(examples: reguiar→regular, Invast→Invest, ESD→USD, etch→tech, HAE→UAE, "
        "portfoil→portfolio, approned→approved).\n\n"
        f"{blueprint.model_dump_json()}"
    )

    async def _run():
        return await service.complete_structured(
            system=system,
            user=user,
            output_model=CreativeBlueprint,
            layer="copy_proofread",
            temperature=0.0,
            max_tokens=8000,
        )

    try:
        polished, meta = await asyncio.wait_for(_run(), timeout=_LLM_PROOFREAD_TIMEOUT_SEC)
        polished.format = blueprint.format
        polished.platform = blueprint.platform
        logger.info(
            "copy_proofread.llm_ok",
            latency_ms=meta.get("latency_ms"),
            output_tokens=meta.get("output_tokens"),
        )
        return polished
    except asyncio.TimeoutError:
        logger.warning("copy_proofread.llm_timeout", timeout_sec=_LLM_PROOFREAD_TIMEOUT_SEC)
        return blueprint
    except Exception as exc:
        logger.warning("copy_proofread.llm_failed", error=str(exc))
        return blueprint


async def proofread_blueprint(
    blueprint: CreativeBlueprint,
    *,
    use_llm: bool = True,
) -> CreativeBlueprint:
    """Quality pass. Local spellcheck always; LLM optional and time-boxed."""
    step1 = await local_spellcheck_blueprint(blueprint)
    if not use_llm:
        return step1
    step2 = await llm_proofread_blueprint(step1)
    return await local_spellcheck_blueprint(step2)


NO_AI_LOGO_RULE = (
    "\n\nABSOLUTE BRAND / WATERMARK BAN (NON-NEGOTIABLE — READ TWICE):\n"
    "- Do NOT invent ANY watermark, stamp, seal, ghost logo, translucent brand shape, "
    "giant letter mark, monogram, or faded brand silhouette in the background.\n"
    "- Do NOT invent giraffe / stylized J marks as decoration.\n"
    "- Do NOT invent brand marketing lines like \"Follow Jiraaf…\", \"Follow JIRAAF for more…\", "
    "or any brand-name CTA — leave brand presence to the real logo only.\n"
    "- NEVER draw JIRAAF / Jiraaf / brand-name wordmark text anywhere in the image.\n"
    "- NEVER draw placeholder labels: \"Brand Logo\", \"Logo\", \"Your Logo Here\", "
    "\"brand logo\", or any dashed / dotted rectangle with logo text inside.\n"
    "- NEVER draw a second logo box, watermark frame, or template placeholder in any corner.\n"
    "- Leave ONLY a plain empty ice-blue top-right corner — no text, no box, no icon there.\n"
    "- The real logo is composited later by backend — you must NOT pre-draw it.\n"
    "- Keep the FULL headline clear — never clip it for a logo band.\n"
    "- Background stays clean ice-blue / soft white — no orange ghost marks behind content.\n"
)

SPELLING_ACCURACY_RULE = (
    "\n\nERROR-FREE VISUAL TEXT (NON-NEGOTIABLE — follow every rule):\n"
    "1) QUOTED STRINGS ONLY — Render ONLY the exact strings inside double quotes. "
    "Copy letter-by-letter. Do not invent, truncate, hyphenate, or remix words.\n"
    "2) FONT — Bold clean sans-serif / block lettering only. Sharp edges, even spacing, "
    "no decorative or serif display fonts that blur letters.\n"
    "3) CONTRAST — Dark navy (#003975) text on ice-blue (#E8F0F8) or white cards. "
    "Never light-on-light or busy-background text.\n"
    "4) SHORT + CLEAR — Prefer short headlines and short bullets. Dense paragraphs cause "
    "spelling errors — keep each card to at most 2 short lines (≤10 words each).\n"
    "5) NO GIBBERISH — Never output broken tokens or hyphenated junk "
    "(bresking, penaity, guarantsed, sub-ject, gawmwaas).\n"
    "6) NO WATERMARKS / black blobs / stamp marks / brand-name text / giant J marks.\n"
    "7) FULL HEADLINE — Never cut the headline with \"...\". Fit the complete quoted headline.\n"
    "8) CURRENCY — India retail: use ₹ only. Never £. Never invent extra card sentences.\n"
)

HUB_CARD_ICON_RULE = (
    "\n\nHUB / FACT-CARD ICON RULE (NON-NEGOTIABLE):\n"
    "- Every fact card MUST include a LARGE HD PREMIUM clay-3D icon "
    "(4K-sharp studio product render, satin materials, gold accents, strong shadows — "
    "not flat clipart, not low-poly, not blurry).\n"
    "- For bank penalty hubs: 5 cards = 5 DIFFERENT premium HD 3D icons "
    "(e.g. classical bank, vault door, gold coin stack, shield, debit-card stack) "
    "placed above or beside each bank name.\n"
    "- Do NOT leave cards as text-only. Do NOT draw official trademark bank logos "
    "(Axis/SBI/HDFC/ICICI/PNB logo marks) — AI garbles trademarks. "
    "Use clear HD premium 3D icons + the exact bank NAME as typography.\n"
    "- Center hub also needs a strong HD PREMIUM clay-3D bank/building icon.\n"
)

# Kept as alias for older imports
ERROR_FREE_VISUAL_TEXT_RULE = SPELLING_ACCURACY_RULE
