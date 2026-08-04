from __future__ import annotations

"""Classify creative layout intent from user prompt + selected format.

╔══════════════════════════════════════════════════════════════════╗
║  PROMPT → LAYOUT ROUTER (you should NOT rewrite prompts)        ║
╠══════════════════════════════════════════════════════════════════╣
║  Your prompt about…              → Layout              → Format ║
║  ─────────────────────────────────────────────────────────────  ║
║  Trade deficit / export-import   → static_ranking      → info   ║
║    (India–Russia dual-bar table)   (trade data board)           ║
║  Top-N / FDI / country ranks     → static_ranking      → info   ║
║  Bank penalties / key rules      → static_hub_facts    → static ║
║  Why / how / benefits / myths    → carousel_story      → carousel║
║    OR education poster if format=infographic/static             ║
╚══════════════════════════════════════════════════════════════════╝

Strong data intents (trade / rank / hub) OVERRIDE a mistaken carousel click.
"""

from dataclasses import dataclass
from typing import Literal

LayoutType = Literal["carousel_story", "static_hub_facts", "static_ranking"]

_HUB_KEYS = (
    "penalty",
    "penalties",
    "key rules",
    "top 5 bank",
    "top five bank",
    "top 5 banks",
    "premature withdrawal",
    "fd penalty",
    "fixed deposit penalty",
)

_RANK_KEYS_STRICT = (
    "top countries",
    "countries investing",
    "country-wise",
    "country wise",
    "top 5 countries",
    "top five countries",
    "top 10 countries",
    "top ten countries",
    "fdi inflow",
    "fdi into india",
    "foreign direct investment",
    "highest fdi",
    "top investors",
    "top investing",
    "ranking of",
    "ranked by",
    "rank the top",
)

# Broad keys — NEVER alone trigger ranking (too many false positives)
_RANK_KEYS_WEAK = (
    "fdi",
    "inflow",
    "inflows",
    "ranking",
    "inflation rate",
)

_EXPLAIN_KEYS = (
    "explain",
    "what is",
    "what are",
    "why ",
    "how ",
    "useful",
    "benefits",
    "benefit",
    "guide",
    "understand",
    "overview",
    "types of",
    "difference between",
    "meaning of",
    "introduction to",
)

# Bilateral / trade-deficit data boards (Jiraaf "India Buys 13x More From Russia" sample)
_DATA_BOARD_KEYS = (
    "trade deficit",
    "trade balance",
    "bilateral trade",
    "exports to",
    "imports from",
    "export vs import",
    "import vs export",
    "buys more from",
    "trade between",
    "analysing the trade",
    "analyzing the trade",
    "analyse the trade",
    "analyze the trade",
    "infographic analysing",
    "infographic analyzing",
    "india and russia",
    "india-russia",
    "india – russia",
    "india russia",
)

_STORY_KEYS = (
    "explain",
    "what is",
    "what are",
    "why ",
    "why liquidity",
    "liquidity",
    "useful",
    "predictable",
    "benefits",
    "benefit",
    "reasons",
    "checklist",
    "anatomy",
    "journey",
    "step-by-step",
    "step by step",
    "how ",
    "fallac",
    "fire",
    "capital control",
    "debenture",
    "ncd",
    "convertible",
    "inflation lie",
    "myth",
    "swipe",
    "carousel",
    "summit",
    "story",
    "sweeping",
    "auto-sweep",
    "auto sweep",
    "income",
    "bonds are",
    "bond appreciation",
)


@dataclass(frozen=True)
class LayoutDecision:
    layout_type: LayoutType
    suggested_format: Literal["static", "carousel", "infographic"]
    reason: str


def is_trade_data_board(user_prompt: str) -> bool:
    """True for India–Russia style trade deficit / export-import data tables."""
    text = (user_prompt or "").lower()
    if any(k in text for k in _DATA_BOARD_KEYS):
        # "india russia summit" without trade/deficit → not a data board
        if any(k in text for k in ("india and russia", "india-russia", "india – russia", "india russia")):
            if not any(
                k in text
                for k in (
                    "trade",
                    "deficit",
                    "export",
                    "import",
                    "balance",
                    "buys",
                    "analys",
                )
            ):
                return False
        return True
    if ("deficit" in text or "trade" in text) and (
        "analys" in text or "export" in text or "import" in text or "russia" in text
    ):
        return True
    return False


def is_education_explain_intent(user_prompt: str) -> bool:
    """True when user wants explanation / education — NOT a ranked list board."""
    text = (user_prompt or "").lower()
    return any(k in text for k in _STORY_KEYS) or any(k in text for k in _EXPLAIN_KEYS)


def is_explicit_ranking_intent(user_prompt: str) -> bool:
    """True ONLY for real ranked lists / trade data boards — NOT general explain topics."""
    import re

    text = (user_prompt or "").lower()
    if is_trade_data_board(user_prompt):
        return True

    # Explicit top-N + list entity (countries, banks, nations…)
    if re.search(r"\btop[\s\-]?\d{1,2}\b", text) and any(
        w in text for w in ("countr", "nation", "bank", "rank", "fdi", "invest", "inflation")
    ):
        return True
    if re.search(
        r"\btop[\s\-]+(ten|twelve|fifteen|eleven|five|six|seven|eight|nine|three|four)\b",
        text,
    ) and any(w in text for w in ("countr", "nation", "bank", "rank", "fdi")):
        return True

    if any(k in text for k in _RANK_KEYS_STRICT):
        return True

    # Weak keys only count WITH list/rank context — not bare "fdi" or "explain fdi"
    if any(k in text for k in _RANK_KEYS_WEAK):
        if any(
            w in text
            for w in (
                "top ",
                "top-",
                "rank",
                "countr",
                "nation",
                "compare",
                " vs ",
                "versus",
                "highest",
                "lowest",
            )
        ):
            return True

    return False


# Horizontal bar chart static (oil consumption, % comparisons) — separate from Top Countries ranking
_HORIZONTAL_BAR_KEYS = (
    "oil",
    "consumption",
    "consuming",
    "mb/d",
    "barrel",
    "barrels",
    "largest",
    "biggest",
    "market share",
    "gdp",
    "economy size",
    "energy demand",
    "petroleum",
    "crude",
)


def is_static_horizontal_bar_intent(user_prompt: str) -> bool:
    """True for static horizontal-bar data charts (oil, consumption) — NOT country FDI top-N."""
    text = (user_prompt or "").lower()
    return any(k in text for k in _HORIZONTAL_BAR_KEYS)


def static_ranking_style(user_prompt: str) -> Literal["horizontal_bar", "vertical_countries", "trade_board"]:
    """Pick static ranking visual — keeps Top Countries vertical; horizontal bar is additive."""
    if is_trade_data_board(user_prompt):
        return "trade_board"
    if is_static_horizontal_bar_intent(user_prompt):
        return "horizontal_bar"
    return "vertical_countries"


def _prefer_data_format(
    selected: str,
    *,
    default: Literal["static", "infographic"] = "infographic",
) -> Literal["static", "carousel", "infographic"]:
    """Keep static/infographic if user picked them; else force data-friendly format."""
    if selected in ("static", "infographic"):
        return selected  # type: ignore[return-value]
    return default


def classify_layout(
    user_prompt: str,
    selected_format: str | None = None,
) -> LayoutDecision:
    """Pick layout from prompt intent. Ranking ONLY when user asked for a list/rank."""
    text = (user_prompt or "").lower()
    fmt = (selected_format or "").strip().lower()
    if fmt not in ("static", "carousel", "infographic"):
        fmt = ""

    is_hub = any(k in text for k in _HUB_KEYS)
    is_trade = is_trade_data_board(user_prompt)
    is_explain = is_education_explain_intent(user_prompt)
    is_rank = is_explicit_ranking_intent(user_prompt)

    # Explain-only wins over weak rank keywords (e.g. "explain FDI" ≠ country rank board).
    # Hybrid "top 7 countries + describe why India…" keeps static_ranking — insight goes in annotation/callout.
    if is_explain and not is_rank and not is_trade and not is_hub:
        pass  # education path below
    elif is_explain and is_rank:
        is_explain = False  # data ranking board + optional insight text — NOT education cards

    # ── Strong data intents first ──
    if is_hub:
        out = _prefer_data_format(fmt, default="static")
        return LayoutDecision("static_hub_facts", out, "intent_hub_facts")
    if is_trade:
        out = _prefer_data_format(fmt, default="infographic")
        return LayoutDecision("static_ranking", out, "intent_trade_data_board")
    if is_rank:
        out = _prefer_data_format(fmt, default="infographic")
        return LayoutDecision("static_ranking", out, "intent_ranking_board")

    # ── Education / explain → headings + explanation cards (NOT ranking board) ──
    if fmt == "carousel":
        return LayoutDecision("carousel_story", "carousel", "user_selected_carousel")
    if fmt in ("infographic", "static"):
        return LayoutDecision(
            "carousel_story",
            fmt,  # type: ignore[arg-type]
            "education_poster_headings_explain",
        )

    # ── No format selected ──
    if is_explain:
        return LayoutDecision("carousel_story", "carousel", "auto_carousel_story")
    return LayoutDecision("carousel_story", "carousel", "auto_carousel_story")


def resolve_layout_type(
    user_prompt: str,
    selected_format: str | None = None,
    *,
    blueprint_layout: str | None = None,
) -> LayoutType:
    """Authoritative layout — always re-classify from prompt; ignore stale blueprint."""
    return classify_layout(user_prompt, selected_format).layout_type


def layout_cheat_sheet() -> str:
    """Human-readable routing table for UI / docs."""
    return (
        "Trade deficit / export-import -> data board (infographic)\n"
        "Top-N / FDI / country ranks ONLY when explicit -> ranking board (infographic)\n"
        "Explain / why / how / benefits -> headings + explanation cards (static/infographic)\n"
        "Bank penalties / key rules -> hub + fact cards (static)\n"
        "Why / how / benefits / myths -> carousel story (or education poster if static/infographic)\n"
        "You do NOT need to rewrite the prompt - intent picks the layout."
    )


def requested_rank_count(
    user_prompt: str,
    *,
    default: int | None = None,
    max_n: int = 15,
) -> int | None:
    """Parse user-requested top-N (e.g. 'top 10 ranking') — never hardcode 5/10.

    Returns None when the prompt does not state a count (caller keeps existing rows).
    """
    import re

    text = (user_prompt or "").lower()
    if not text:
        return default

    word_nums = {
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
        "fifteen": 15,
        "twenty": 20,
    }

    patterns = (
        r"\btop[\s\-]?(\d{1,2})\b",
        r"\btop[\s\-]+(ten|twelve|fifteen|twenty|eleven|five|six|seven|eight|nine|three|four)\b",
        r"\b(\d{1,2})\s*(?:country|countries|nation|nations|bank|banks|item|items|row|rows|rankings?)\b",
        r"\brank(?:ing|ed)?\s+(?:the\s+)?(?:top\s+)?(\d{1,2})\b",
        r"\brank(?:ing|ed)?\s+(?:the\s+)?(?:top\s+)?(ten|twelve|fifteen|twenty|five|six|seven|eight|nine)\b",
    )
    for pat in patterns:
        m = re.search(pat, text)
        if not m:
            continue
        raw = m.group(1)
        n = word_nums.get(raw) if raw.isalpha() else int(raw)
        if n is None:
            continue
        return min(max(int(n), 1), max_n)
    return default


def needs_live_research(user_prompt: str, layout_type: LayoutType | None = None) -> bool:
    """News/data/top-N/rates prompts should always research."""
    text = (user_prompt or "").lower()
    if layout_type in ("static_hub_facts", "static_ranking"):
        return True
    if is_trade_data_board(user_prompt):
        return True
    keys = (
        "latest",
        "current",
        "today",
        "news",
        "rate",
        "rates",
        "fdi",
        "inflation",
        "penalty",
        "top ",
        "summit",
        "invest",
        "inflow",
        "2024",
        "2025",
        "2026",
        "japan",
        "bank",
        "trade deficit",
        "trade balance",
        "export",
        "import",
        "russia",
    )
    return any(k in text for k in keys)


def source_domains_for_footer(sources: list[dict], limit: int = 2) -> list[str]:
    """Compact domains for image footer (Source: dpiit.gov.in)."""
    from urllib.parse import urlparse

    out: list[str] = []
    seen: set[str] = set()
    for src in sources or []:
        url = str(src.get("url") or src.get("source_url") or "").strip()
        if not url:
            continue
        try:
            host = urlparse(url).netloc.lower().removeprefix("www.")
        except Exception:
            continue
        if not host or host in seen:
            continue
        seen.add(host)
        out.append(host)
        if len(out) >= limit:
            break
    return out
