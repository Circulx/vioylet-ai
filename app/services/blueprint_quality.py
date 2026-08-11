from __future__ import annotations

"""Auto-check + auto-fix LLM blueprint mistakes BEFORE the approval card.

Flow: LLM drafts → finalize_blueprint_for_card() → user sees cleaned blueprint.
Only leave missing_critical for issues that cannot be safely invented (e.g. no research URLs).
"""

import re
from typing import TYPE_CHECKING, Any

from app.prompts.jiraaf_layout import LayoutType, source_domains_for_footer

if TYPE_CHECKING:
    from app.graph.models.layer7c_models import CreativeBlueprint

_TEASER_HEADLINE = re.compile(
    r"^\s*(what are your|are you aware|discover how|learn the|surprising costs|"
    r"did you know|ready to|unlock|ever wondered)\b",
    re.I,
)

CANONICAL_BANK_HUB = (
    "Axis Bank",
    "SBI",
    "HDFC Bank",
    "ICICI Bank",
    "PNB",
)

_BANK_ALIASES: dict[str, str] = {
    "axis": "Axis Bank",
    "axis bank": "Axis Bank",
    "sbi": "SBI",
    "state bank": "SBI",
    "state bank of india": "SBI",
    "obi": "SBI",
    "hdfc": "HDFC Bank",
    "hdfc bank": "HDFC Bank",
    "haft": "HDFC Bank",
    "haft bank": "HDFC Bank",
    "icici": "ICICI Bank",
    "icici bank": "ICICI Bank",
    "acini": "ICICI Bank",
    "acini bank": "ICICI Bank",
    "pnb": "PNB",
    "punjab national": "PNB",
    "punjab national bank": "PNB",
    "pub": "PNB",
}

# (pattern, replacement) — applied to every blueprint text field
_GLOBAL_TEXT_FIXES: list[tuple[re.Pattern[str], str]] = [
    # India schemes / proper nouns the LLM routinely misspells
    (re.compile(r"\bADAN\b"), "UDAN"),
    (re.compile(r"\bAdan\b"), "UDAN"),
    (re.compile(r"\badan\b"), "UDAN"),
    (re.compile(r"\bADAN\s+Scheme\b", re.I), "UDAN Scheme"),
    (re.compile(r"\bUdan\b"), "UDAN"),
    (re.compile(r"\bAds\b"), "FDs"),
    (re.compile(r"\bads\b"), "FDs"),
    (re.compile(r"\bAD\b"), "FD"),
    (re.compile(r"\bFDR\b"), "FDI"),  # common FDI misspelling in rankings
    (re.compile(r"\bASA\b"), "USA"),  # common USA misspelling in country ranks
    (re.compile(r"\bU\.S\.A\b"), "USA"),
    (re.compile(r"\bFinancrial\b"), "Financial"),
    (re.compile(r"\bfinancrial\b"), "financial"),
    (re.compile(r"\bfiexible\b", re.I), "flexible"),
    (re.compile(r"\binternationa!l\b", re.I), "international"),
    (re.compile(r"\bLeśs\b"), "Less"),
    (re.compile(r"\bleśs\b"), "less"),
    (re.compile(r"\bExplering\b"), "Exploring"),
    (re.compile(r"\bexplering\b"), "exploring"),
    (re.compile(r"\bcouid\b", re.I), "could"),
    (re.compile(r"\bduiable\b", re.I), "durable"),
    (re.compile(r"\bGldbally\b"), "Globally"),
    (re.compile(r"\bgldbally\b"), "globally"),
    (re.compile(r"\bcaurious\b", re.I), "cautious"),
    (re.compile(r"\badeption\b", re.I), "adoption"),
    (re.compile(r"\bimplicatiohs\b", re.I), "implications"),
    (re.compile(r"\balready\s+eve\b", re.I), "already use"),
    (re.compile(r"\beve\s+plastic\b", re.I), "use plastic"),
    # Image models often paint ₹ as "2"
    (re.compile(r"\b2\s+(\d[\d,]*(?:\s*[–-]\s*[\d,]*)?\s*crore)\b", re.I), r"₹\1"),
    (re.compile(r"\b2(10)\s+notes\b", re.I), r"₹\1 notes"),
    (re.compile(r"\b210\s+notes\b", re.I), "₹10 notes"),
    (re.compile(r"\bhotes\b", re.I), "notes"),
    (re.compile(r"\bIndid\b"), "India"),
    (re.compile(r"\bindid\b"), "India"),
    (re.compile(r"\berore\b", re.I), "crore"),
    (re.compile(r"\bbefors\b", re.I), "before"),
    (re.compile(r"\bsuppllers\b", re.I), "suppliers"),
    (re.compile(r"\bhedrily\b", re.I), "heavily"),
    (re.compile(r"\bpalymer\b", re.I), "polymer"),
    (re.compile(r"\baloption\b", re.I), "adoption"),
    (re.compile(r"\badeption\b", re.I), "adoption"),
    (re.compile(r"\bpliot\b", re.I), "pilot"),
    (re.compile(r"\bdurabllity\b", re.I), "durability"),
    (re.compile(r"\bimplicas-?\s*tions\b", re.I), "implications"),
    (re.compile(r"\bknowiedge\b", re.I), "knowledge"),
    (re.compile(r"\binfograpnics\b", re.I), "infographics"),
    (re.compile(r"\bthdught\b", re.I), "thought"),
    (re.compile(r"\breplacament\b", re.I), "replacement"),
    (re.compile(r"\bwny\b", re.I), "why"),
    (re.compile(r"\bsmail\b", re.I), "small"),
    (re.compile(r"\byaar\b", re.I), "year"),
    (re.compile(r"\bwornn\b", re.I), "worn"),
    (re.compile(r"\bHeres\b"), "Here's"),
    (re.compile(r"\bheres\b"), "here's"),
    (re.compile(r"\bdesignad\b", re.I), "designed"),
    (re.compile(r"\bcurrancy\b", re.I), "currency"),
    (re.compile(r"\bnate\b", re.I), "note"),
    (re.compile(r"\binvestmet\b", re.I), "investment"),
    (re.compile(r"\btecnlogy\b", re.I), "technology"),
    (re.compile(r"\btecnology\b", re.I), "technology"),
    (re.compile(r"\brestate\b", re.I), "real estate"),
    (re.compile(r"\bflucuations\b", re.I), "fluctuations"),
    (re.compile(r"\bfluctation\b", re.I), "fluctuation"),
    (re.compile(r"\bMealtime\b"), "Mid-term"),
    (re.compile(r"\bmealtime\b"), "mid-term"),
    (re.compile(r"\bagroach\b", re.I), "approach"),
    (re.compile(r"\bGrewth\b"), "Growth"),
    (re.compile(r"\bgrewth\b"), "growth"),
    (re.compile(r"\bMeximize\b"), "Maximize"),
    (re.compile(r"\bmeximize\b"), "maximize"),
    (re.compile(r"\brcturns\b", re.I), "returns"),
    (re.compile(r"\bliquildity\b", re.I), "liquidity"),
    (re.compile(r"\bEunjoy\b"), "Enjoy"),
    (re.compile(r"\beunjoy\b"), "enjoy"),
    (re.compile(r"\byizids\b", re.I), "yields"),
    (re.compile(r"\bRiisk\b"), "Risk"),
    (re.compile(r"\briisk\b"), "risk"),
    (re.compile(r"\bnotlon\b", re.I), "notion"),
    (re.compile(r"\bbresking\b", re.I), "breaking"),
    (re.compile(r"\bpenaity\b", re.I), "penalty"),
    (re.compile(r"\bPenaity\b"), "Penalty"),
    (re.compile(r"\binerast\b", re.I), "interest"),
    (re.compile(r"\bintrate\b", re.I), "interest"),
    (re.compile(r"£"), "₹"),
    (re.compile(r"\bRs\.?\s*"), "₹"),
    (re.compile(r"\bINR\s*"), "₹"),
    (re.compile(r"[ \t]{2,}"), " "),
    (re.compile(r"\s+\.\.\.\s*$"), ""),
    (re.compile(r"\.\.\.$"), ""),
    (re.compile(r"\s+\."), "."),  # "returns ." → "returns."
]

_COUNTRY_ALIASES: dict[str, str] = {
    "asa": "USA",
    "usa": "USA",
    "u s a": "USA",
    "u.s.a": "USA",
    "u.s.": "USA",
    "united states": "USA",
    "united states of america": "USA",
    "uk": "UK",
    "u.k.": "UK",
    "u.k": "UK",
    "united kingdom": "UK",
    "britain": "UK",
    "great britain": "UK",
    "india": "India",
    "japan": "Japan",
    "germany": "Germany",
    "china": "China",
    "singapore": "Singapore",
    "australia": "Australia",
    "france": "France",
    "canada": "Canada",
}


def _canonical_country_label(raw: str) -> str | None:
    key = re.sub(r"[^a-z0-9.\s]", "", (raw or "").lower()).strip()
    key = re.sub(r"\s+", " ", key)
    if key in _COUNTRY_ALIASES:
        return _COUNTRY_ALIASES[key]
    return None


def repair_ranking_countries(
    blueprint: CreativeBlueprint,
    *,
    layout_type: LayoutType,
) -> CreativeBlueprint:
    """Fix garbled country labels on ranking creatives (ASA→USA, etc.)."""
    from app.graph.models.layer7c_models import BlueprintInfographicSection

    if layout_type != "static_ranking":
        return blueprint

    notes = list(blueprint.brand_alignment_notes or [])
    fixed_any = False
    cleaned = []
    for sec in blueprint.sections or []:
        label = (sec.section_label or "").strip()
        canon = _canonical_country_label(label)
        if canon and canon != label:
            label = canon
            fixed_any = True
        cleaned.append(
            BlueprintInfographicSection(
                section_label=label,
                stat=sec.stat,
                includes=list(sec.includes or []),
                body=sec.body or "",
                icon_hint=sec.icon_hint,
            )
        )
    blueprint.sections = cleaned
    if fixed_any:
        notes.append("Auto-fixed: country labels (e.g. ASA→USA)")
        blueprint.brand_alignment_notes = notes[:8]
    return blueprint


def _is_bank_penalty_hub(user_prompt: str, headline: str = "") -> bool:
    text = f"{user_prompt or ''} {headline or ''}".lower()
    return any(
        k in text
        for k in (
            "penalty",
            "penalties",
            "premature withdrawal",
            "fd penalty",
            "fixed deposit penalty",
            "top 5 bank",
            "top five bank",
            "bank's penalty",
            "banks penalty",
        )
    )


def _is_india_retail_money(user_prompt: str, headline: str = "") -> bool:
    text = f"{user_prompt or ''} {headline or ''}".lower()
    if any(k in text for k in ("fdi", "dpiit", "inflow", "usd", "dollar")):
        return False
    return any(
        k in text
        for k in (
            "fd ",
            "fixed deposit",
            "penalty",
            "savings",
            "bank",
            "₹",
            "rupee",
            "inflation lie",
            "premature",
        )
    )


def _canonical_bank_label(raw: str) -> str | None:
    key = re.sub(r"[^a-z0-9\s]", "", (raw or "").lower()).strip()
    key = re.sub(r"\s+", " ", key)
    if key in _BANK_ALIASES:
        return _BANK_ALIASES[key]
    for alias, canon in _BANK_ALIASES.items():
        if alias in key or key in alias:
            return canon
    return None


def _fix_text(text: str, *, india_retail: bool = False) -> str:
    if not text or not isinstance(text, str):
        return text
    out = text.strip()
    for pat, repl in _GLOBAL_TEXT_FIXES:
        out = pat.sub(repl, out)
    if india_retail:
        # Prefer ₹ over lone $ for retail India (keep $ if clearly USD-labeled)
        if "usd" not in out.lower() and "dollar" not in out.lower():
            out = re.sub(r"\$(\d)", r"₹\1", out)
    return out.strip()


def _walk_fix_strings(obj: Any, *, india_retail: bool) -> Any:
    if isinstance(obj, str):
        return _fix_text(obj, india_retail=india_retail)
    if isinstance(obj, list):
        return [_walk_fix_strings(v, india_retail=india_retail) for v in obj]
    if isinstance(obj, dict):
        skip = {"url", "source_url", "sources"}  # don't mutate URLs
        return {
            k: (
                v
                if k in skip
                else _walk_fix_strings(v, india_retail=india_retail)
            )
            for k, v in obj.items()
        }
    return obj


def apply_text_hygiene(
    blueprint: CreativeBlueprint,
    *,
    user_prompt: str,
) -> CreativeBlueprint:
    """Fix common LLM typos across all blueprint copy fields."""
    india = _is_india_retail_money(user_prompt, blueprint.headline or "")
    data = blueprint.model_dump()
    # Preserve sources URLs untouched
    sources = data.pop("sources", None)
    cleaned = _walk_fix_strings(data, india_retail=india)
    if sources is not None:
        cleaned["sources"] = sources
    bp = type(blueprint).model_validate(cleaned)

    # RBI topics: never bake "OBI" (common AI typo for RBI)
    prompt_l = (user_prompt or "").lower()
    if "rbi" in prompt_l or "reserve bank" in prompt_l or "polymer" in prompt_l or "plastic" in prompt_l:
        for field in ("headline", "supporting_line", "body", "hook", "cta", "customer_quote", "title", "purpose"):
            val = getattr(bp, field, None)
            if isinstance(val, str) and val:
                setattr(bp, field, re.sub(r"\bOBI\b", "RBI", val))
                setattr(bp, field, re.sub(r"\bObi\b", "RBI", getattr(bp, field)))
        for sec in bp.sections or []:
            if sec.section_label:
                sec.section_label = re.sub(r"\bOBI\b", "RBI", sec.section_label)
            if sec.body:
                sec.body = re.sub(r"\bOBI\b", "RBI", sec.body)
            if sec.includes:
                sec.includes = [re.sub(r"\bOBI\b", "RBI", str(x)) for x in sec.includes]
        if bp.story_flow:
            bp.story_flow = [re.sub(r"\bOBI\b", "RBI", str(x)) for x in bp.story_flow]
    return bp


def _is_usable_source_url(url: str) -> bool:
    """Drop fake/relative URLs that 404 when opened from the blueprint card."""
    from urllib.parse import urlparse

    raw = (url or "").strip()
    if not raw:
        return False
    if not raw.lower().startswith(("http://", "https://")):
        return False
    try:
        parsed = urlparse(raw)
    except Exception:
        return False
    host = (parsed.netloc or "").lower().removeprefix("www.")
    if not host or "." not in host:
        return False
    # Block obvious placeholders
    blocked_hosts = (
        "example.com",
        "localhost",
        "invalid",
        "placeholder",
        "test.com",
        "sample.com",
        "fake.com",
        "dummy.com",
    )
    if any(bad == host or host.endswith("." + bad) or bad in host for bad in blocked_hosts):
        return False
    # Prefer real TLDs; reject single-label or IP-less junk
    if host.endswith((".local", ".test", ".invalid", ".example")):
        return False
    if len(raw) < 12:
        return False
    return True


def attach_sources_from_research(
    blueprint: CreativeBlueprint,
    live_research: dict[str, Any] | None,
    *,
    user_prompt: str = "",
) -> CreativeBlueprint:
    """Merge verified research URLs into blueprint.sources + source_footer.

    Never keep LLM-hallucinated article URLs that 404 — prefer research-backed
    links only, then topic-safe official homepages as last resort.
    """
    from app.graph.models.layer7c_models import BlueprintSource

    research = live_research or {}
    sources: list = []
    seen: set[str] = set()
    research_urls: set[str] = set()

    def _add(title: str, url: str) -> None:
        url = (url or "").strip()
        title = (title or "").strip()
        if not _is_usable_source_url(url):
            return
        key = url.casefold()
        if key in seen:
            return
        sources.append(BlueprintSource(title=title or url, url=url))
        seen.add(key)

    for fact in research.get("verified_facts") or []:
        url = str(fact.get("source_url") or "").strip()
        if _is_usable_source_url(url):
            research_urls.add(url.casefold())
        _add(
            str(fact.get("source_title") or fact.get("label") or "").strip(),
            url,
        )

    for src in research.get("sources") or []:
        if not isinstance(src, dict):
            continue
        url = str(src.get("url") or src.get("source_url") or "").strip()
        if _is_usable_source_url(url):
            research_urls.add(url.casefold())
        _add(
            str(src.get("title") or src.get("source_title") or "").strip(),
            url,
        )

    # Keep blueprint sources ONLY if they match research (drop invented 404 links)
    for s in blueprint.sources or []:
        url = (getattr(s, "url", "") or "").strip()
        if url.casefold() in research_urls:
            _add(getattr(s, "title", "") or "", url)

    # Topic-safe official homepage fallbacks (never deep article paths that 404)
    if not sources:
        prompt_bits = " ".join(
            [
                user_prompt or "",
                blueprint.headline or "",
                blueprint.supporting_line or "",
                blueprint.body or "",
                blueprint.purpose or "",
                " ".join((s.section_label or "") + " " + (s.body or "") for s in (blueprint.sections or [])),
            ]
        ).lower()
        if any(k in prompt_bits for k in ("rbi", "polymer", "plastic note", "currency note")):
            _add("Reserve Bank of India", "https://www.rbi.org.in/")
        elif any(k in prompt_bits for k in ("fdi", "dpiit", "inflow")):
            _add("DPIIT", "https://dpiit.gov.in/")
        elif any(k in prompt_bits for k in ("oil", "petroleum", "crude")):
            _add("PPAC", "https://ppac.gov.in/")

    blueprint.sources = sources[:8]
    domains = source_domains_for_footer(
        [{"url": s.url} for s in blueprint.sources],
        limit=2,
    )
    if domains:
        blueprint.source_footer = "Source: " + " · ".join(domains)
    elif not (blueprint.source_footer or "").strip() and sources:
        blueprint.source_footer = "Source: " + (sources[0].title or sources[0].url)[:80]
    elif not sources:
        # Clear fake footer that pointed at dead links
        footer = (blueprint.source_footer or "").strip()
        if footer and ("http://" in footer.lower() or "https://" in footer.lower()):
            blueprint.source_footer = None
    return blueprint


def _audience_for_platform(platform: str) -> str:
    p = (platform or "").strip().lower()
    if p in ("instagram", "ig"):
        return "Indian Instagram users / retail savers"
    if p in ("x", "twitter"):
        return "Indian X (Twitter) users / retail savers"
    if p in ("linkedin", "li"):
        return "Indian LinkedIn professionals / retail savers"
    return "Indian retail savers / professionals"


def polish_blueprint_meta(
    blueprint: CreativeBlueprint,
    *,
    layout_type: LayoutType,
    user_prompt: str,
) -> CreativeBlueprint:
    """Fill empty Purpose / Audience / Tone so the approval card isn't blank."""
    platform = (blueprint.platform or "linkedin").strip().lower()
    if platform in ("twitter",):
        platform = "x"
        blueprint.platform = "x"

    if not (blueprint.purpose or "").strip():
        if layout_type == "static_hub_facts":
            blueprint.purpose = "Educate with short, accurate fact cards"
        elif layout_type == "static_ranking":
            blueprint.purpose = "Show ranked data clearly at a glance"
        elif blueprint.format == "infographic":
            blueprint.purpose = "Educate with a dense sample-style infographic"
        else:
            blueprint.purpose = "Educate with a short swipe story"

    # Always align audience with SELECTED platform (never force LinkedIn for IG/X)
    audience = (blueprint.audience or "").strip()
    audience_l = audience.lower()
    wrong_linkedin = "linkedin" in audience_l and platform in ("instagram", "x")
    wrong_ig = "instagram" in audience_l and platform in ("linkedin", "x")
    wrong_x = (("twitter" in audience_l or audience_l.startswith("indian x")) and platform in ("linkedin", "instagram"))
    if not audience or wrong_linkedin or wrong_ig or wrong_x:
        blueprint.audience = _audience_for_platform(platform)

    if not (blueprint.tone or "").strip():
        blueprint.tone = "simple, educational, sample-style"
    if not (blueprint.intent or "").strip():
        blueprint.intent = "awareness"

    # Fill empty story fields so the approval card isn't blank
    is_explain = blueprint.format in ("infographic", "static") or layout_type == "carousel_story"
    if is_explain:
        if not (blueprint.hook or "").strip() and (blueprint.headline or "").strip():
            blueprint.hook = (blueprint.headline or "").strip()
        if not blueprint.story_flow and blueprint.sections:
            blueprint.story_flow = [
                (s.section_label or f"Section {i}").strip()
                for i, s in enumerate(blueprint.sections[:5], start=1)
                if (s.section_label or "").strip()
            ]
        if not (blueprint.customer_quote or "").strip():
            for sec in reversed(list(blueprint.sections or [])):
                if (sec.body or "").strip():
                    blueprint.customer_quote = sec.body.strip()[:220]
                    break
                if sec.includes:
                    blueprint.customer_quote = " ".join(str(x) for x in sec.includes[:2]).strip()[:220]
                    break
        if not (blueprint.supporting_line or "").strip() and (blueprint.body or "").strip():
            blueprint.supporting_line = (blueprint.body or "").strip()[:160]
        if not (blueprint.body or "").strip() and (blueprint.supporting_line or "").strip():
            # Keep body readable on card when LLM left it empty
            if layout_type == "carousel_story":
                blueprint.body = (blueprint.supporting_line or "").strip()

    # Off-topic CTA repair (e.g. "Explore bond investments!" on RBI/currency explain)
    cta = (blueprint.cta or "").strip()
    prompt_l = (user_prompt or "").lower()
    cta_l = cta.lower()
    topic_is_currency = any(
        k in prompt_l
        for k in (
            "polymer",
            "plastic note",
            "currency note",
            "rbi testing",
            "rbi trial",
            "plastic currency",
        )
    )
    cta_is_bond = any(k in cta_l for k in ("bond", "invest", "portfolio", "fd ", "fixed deposit"))
    if topic_is_currency and cta_is_bond:
        blueprint.cta = "Learn more"
    if not (blueprint.cta or "").strip() and blueprint.format in ("infographic", "static"):
        blueprint.cta = "Learn more"

    if layout_type == "carousel_story" and blueprint.format == "infographic":
        # Dedupe repeated section headings
        seen: set[str] = set()
        for i, sec in enumerate(blueprint.sections or []):
            label = (sec.section_label or "").strip()
            key = label.casefold()
            if key and key in seen:
                sec.section_label = f"{label} ({i + 1})"
            elif key:
                seen.add(key)

    if layout_type == "static_hub_facts" and _is_bank_penalty_hub(
        user_prompt, blueprint.headline or ""
    ):
        if not (blueprint.hook or "").strip():
            blueprint.hook = (
                "Know the FD premature-withdrawal rules before you break a deposit."
            )
        if not blueprint.story_flow:
            blueprint.story_flow = [
                "Show five major banks",
                "Each card: short ₹/% penalty rule",
                "Encourage checking your bank before withdrawing early",
            ]
    return blueprint


def repair_bank_hub_sections(
    blueprint: CreativeBlueprint,
    *,
    user_prompt: str,
) -> CreativeBlueprint:
    """Force real bank names for penalty hubs; map garbled AI labels to the sample five."""
    from app.graph.models.layer7c_models import BlueprintInfographicSection

    headline = blueprint.headline or blueprint.title or ""
    if not _is_bank_penalty_hub(user_prompt, headline):
        return blueprint

    sections = list(blueprint.sections or [])
    by_bank: dict[str, Any] = {}
    leftovers: list[Any] = []
    for sec in sections:
        canon = _canonical_bank_label(sec.section_label or "")
        if canon and canon not in by_bank:
            by_bank[canon] = sec
        else:
            leftovers.append(sec)

    rebuilt: list = []
    leftover_i = 0
    for bank in CANONICAL_BANK_HUB:
        src = by_bank.get(bank)
        if src is None and leftover_i < len(leftovers):
            src = leftovers[leftover_i]
            leftover_i += 1
        if src is None:
            rebuilt.append(
                BlueprintInfographicSection(
                    section_label=bank,
                    includes=["Premature withdrawal penalty — verify on bank site"],
                    body="",
                )
            )
            continue
        includes = [_fix_text(x, india_retail=True) for x in (src.includes or [])]
        # Drop empty / placeholder includes
        includes = [x for x in includes if x and x.lower() not in ("n/a", "tbd", "-")]
        if not includes and (src.stat or "").strip():
            includes = [_fix_text(src.stat or "", india_retail=True)]
        if not includes and (src.body or "").strip():
            includes = [_fix_text((src.body or "")[:120], india_retail=True)]
        # Keep card lines short but COMPLETE — never cut mid-phrase
        short_includes: list[str] = []
        for line in includes[:2]:
            short_includes.append(_clip_complete(str(line).replace("£", "₹"), 16))
        includes = [x for x in short_includes if x]
        rebuilt.append(
            BlueprintInfographicSection(
                section_label=bank,
                stat=_fix_text(src.stat or "", india_retail=True) or None,
                includes=includes,
                body="",  # hub cards: facts in includes only
                icon_hint=src.icon_hint or "bank",
            )
        )

    blueprint.sections = rebuilt
    if not blueprint.headline or _TEASER_HEADLINE.search(blueprint.headline or ""):
        blueprint.headline = "Bank's Penalty Rates and Key Rules"
    blueprint.title = blueprint.headline
    blueprint.body = ""
    blueprint.customer_quote = None
    blueprint.customer_name = None
    notes = list(blueprint.brand_alignment_notes or [])
    notes.append("Auto-fixed: bank names -> Axis Bank, SBI, HDFC Bank, ICICI Bank, PNB")
    blueprint.brand_alignment_notes = notes[:8]
    return blueprint


def repair_data_layout(
    blueprint: CreativeBlueprint,
    *,
    layout_type: LayoutType,
    user_prompt: str,
) -> CreativeBlueprint:
    """Kill teasers, fake quotes, and textbook bodies on data creatives."""
    if layout_type not in ("static_hub_facts", "static_ranking"):
        return blueprint

    notes = list(blueprint.brand_alignment_notes or [])
    sections = blueprint.sections or []

    # Teaser headline → factual when we already have data sections
    if _TEASER_HEADLINE.search(blueprint.headline or "") and len(sections) >= 3:
        if _is_bank_penalty_hub(user_prompt, blueprint.headline or ""):
            blueprint.headline = "Bank's Penalty Rates and Key Rules"
        elif layout_type == "static_ranking":
            blueprint.headline = (blueprint.title or blueprint.headline or "Key rankings").strip()
            if _TEASER_HEADLINE.search(blueprint.headline):
                blueprint.headline = "Top rankings at a glance"
        notes.append("Auto-fixed: teaser headline -> factual title")

    # Data posters: no long essays / fake social proof
    if (blueprint.body or "").strip() and len(blueprint.body or "") > 60:
        blueprint.body = ""
        notes.append("Auto-fixed: cleared long body on data layout")
    if blueprint.customer_quote:
        blueprint.customer_quote = None
        blueprint.customer_name = None
        notes.append("Auto-fixed: removed fake testimonial on data layout")

    # Section hygiene: empty body on hub/rank; move body→includes if needed
    from app.graph.models.layer7c_models import BlueprintInfographicSection

    cleaned_sections = []
    for sec in sections:
        includes = list(sec.includes or [])
        body = (sec.body or "").strip()
        if body and not includes:
            includes = [body[:140]]
        # Short facts only — but COMPLETE sentences (never mid-phrase cuts)
        short_incs = []
        for x in includes:
            if not x:
                continue
            cleaned = _fix_text(str(x), india_retail=True).replace("£", "₹")
            short_incs.append(_clip_complete(cleaned, 18))
        cleaned_sections.append(
            BlueprintInfographicSection(
                section_label=_clip_complete(
                    _fix_text(sec.section_label or "", india_retail=True), 12
                ),
                stat=_fix_text(sec.stat or "", india_retail=True) or None,
                includes=short_incs[:2],
                body="",
                icon_hint=sec.icon_hint,
            )
        )
    blueprint.sections = cleaned_sections
    blueprint.brand_alignment_notes = notes[:8]
    return blueprint


_STORY_ROLES = (
    "hook",
    "define",
    "impact",
    "implication",
    "proof",
    "myth_bust",
    "cta",
)

_STORY_ROLE_HINTS = {
    "hook": "Open with a sharp question or tension — invite the swipe",
    "define": "Plain definition — what this actually means",
    "impact": "How it hits India / markets / savers",
    "implication": "Who is affected and what changes in practice",
    "proof": "Concrete signal, rule, or example that proves the point",
    "myth_bust": "Myth vs truth — clear the confusion",
    "cta": "Close with one short next step — no new lecture",
}


def repair_carousel_slides(
    blueprint: CreativeBlueprint,
    *,
    layout_type: LayoutType,
) -> CreativeBlueprint:
    """Force 4–7 slides that advance a continuous swipe storyline."""
    from app.graph.models.layer7c_models import BlueprintSlide

    if layout_type != "carousel_story" and blueprint.format != "carousel":
        return blueprint
    if blueprint.format != "carousel":
        return blueprint

    notes = list(blueprint.brand_alignment_notes or [])
    slides = list(blueprint.slides or [])

    for s in slides:
        if len(s.body or "") > 160:
            s.body = (s.body or "")[:157].rstrip(" .")

    if len(slides) > 7:
        slides = slides[:7]
        notes.append("Auto-fixed: trimmed carousel to 7 slides")

    if len(slides) < 4:
        beats = list(blueprint.story_flow or [])
        if not beats:
            beats = [
                blueprint.hook or blueprint.headline or "What is this really about?",
                "Here is the simple definition",
                "Here is how it hits the Indian economy",
                blueprint.cta or "Save this and swipe again later",
            ]
        while len(beats) < 4:
            beats.append(f"Next beat {len(beats) + 1}")
        for i in range(len(slides), min(7, max(4, len(beats)))):
            text = beats[i] if i < len(beats) else beats[-1]
            role = _STORY_ROLES[i] if i < len(_STORY_ROLES) else "insight"
            slides.append(
                BlueprintSlide(
                    slide_number=i + 1,
                    role=role,
                    headline=_fix_text(str(text)[:80]),
                    body="",
                    cta=blueprint.cta if role == "cta" else None,
                )
            )
        notes.append("Auto-fixed: padded carousel to at least 4 story beats")

    # Assign progressive storyline roles + de-dupe identical headlines
    seen_headlines: set[str] = set()
    n = len(slides)
    for i, s in enumerate(slides):
        role = _STORY_ROLES[i] if i < len(_STORY_ROLES) else ("cta" if i == n - 1 else "insight")
        if i == n - 1:
            role = "cta"
        s.role = role
        s.slide_number = i + 1
        hl = (s.headline or "").strip()
        key = hl.casefold()
        if not hl or key in seen_headlines:
            # Force a distinct beat headline from role hint + existing body
            hint = _STORY_ROLE_HINTS.get(role, "Next story beat")
            seed = (s.body or hl or hint).split(".")[0].strip()
            words = seed.split()[:8] or hint.split()[:8]
            s.headline = _fix_text(" ".join(words)) or f"Beat {i + 1}"
            notes.append(f"Auto-fixed: unique storyline headline on slide {i + 1}")
        seen_headlines.add((s.headline or "").strip().casefold())
        if role == "cta" and not (s.cta or "").strip():
            s.cta = blueprint.cta or "Save this for later"

    # story_flow = swipe narrative (one line per slide)
    blueprint.story_flow = [
        f"{i}. [{s.role}] {s.headline}" for i, s in enumerate(slides, start=1)
    ]
    if not (blueprint.hook or "").strip() and slides:
        blueprint.hook = slides[0].headline
    blueprint.slides = slides
    notes.append("Storyline locked: each slide advances hook→define→impact→…→CTA")
    blueprint.brand_alignment_notes = notes[:8]
    return blueprint


def _collect_remaining_gaps(
    blueprint: CreativeBlueprint,
    *,
    layout_type: LayoutType,
    user_prompt: str,
) -> list[str]:
    """Only issues that cannot be safely auto-invented."""
    missing: list[str] = []
    sections = blueprint.sections or []
    slides = blueprint.slides or []

    if layout_type == "static_hub_facts":
        if len(sections) < 4:
            missing.append("hub_still_needs_more_fact_sections")
        empty_facts = sum(1 for s in sections if not (s.includes or s.stat))
        if empty_facts >= 2:
            missing.append("some_fact_cards_still_empty")

    elif layout_type == "static_ranking":
        from app.prompts.jiraaf_layout import requested_rank_count

        needed = requested_rank_count(user_prompt)
        row_count = len(sections)
        if needed and row_count < needed:
            missing.append(f"ranking_needs_{needed}_rows_has_{row_count}")
        elif row_count < 3 and len(blueprint.stat_highlights or []) < 3:
            missing.append("ranking_still_needs_rows")

    elif layout_type == "carousel_story" and blueprint.format == "carousel":
        if len(slides) < 4:
            missing.append("carousel_still_under_4_slides")

    has_stats = bool(
        blueprint.stat_highlights
        or any((s.stat or "").strip() for s in sections)
        or any(s.includes for s in sections)
        or re.search(r"[%₹$¥]|percent|rate|inflow|penalty", user_prompt or "", re.I)
    )
    if has_stats and layout_type in ("static_hub_facts", "static_ranking"):
        if not blueprint.sources and not blueprint.source_footer:
            missing.append("sources_required_for_data_creative")

    if not (blueprint.headline or "").strip():
        missing.append("headline_missing")

    return missing


def _is_polymer_explain_topic(user_prompt: str, blueprint: CreativeBlueprint) -> bool:
    haystack_parts = [
        user_prompt or "",
        blueprint.headline or "",
        blueprint.title or "",
        blueprint.supporting_line or "",
        blueprint.customer_quote or "",
        blueprint.body or "",
    ]
    for sec in blueprint.sections or []:
        haystack_parts.append(sec.section_label or "")
        haystack_parts.append(sec.body or "")
        haystack_parts.extend(str(x) for x in (sec.includes or []))
    haystack = " ".join(haystack_parts).lower()
    return any(
        k in haystack
        for k in (
            "polymer",
            "plastic note",
            "plastic currency",
            "currency note",
            "plastic banknote",
            "rbi testing",
            "rbi trial",
            "reserve bank",
            "₹10 / ₹20",
            "₹10/₹20",
            "10 and ₹20",
            "10 & ₹20",
            " rbi ",
            " rbi",
            "rbi ",
        )
    )


def repair_explain_infographic_copy(
    blueprint: CreativeBlueprint,
    *,
    layout_type: LayoutType,
    user_prompt: str,
) -> CreativeBlueprint:
    """Hard-lock polymer/RBI explain copy to sample DNA — stops LLM drift + bad headlines."""
    from app.graph.models.layer7c_models import BlueprintInfographicSection

    if blueprint.format not in ("infographic",) or layout_type != "carousel_story":
        return blueprint
    if not _is_polymer_explain_topic(user_prompt, blueprint):
        return blueprint

    blueprint.headline = "RBI TO TEST PLASTIC CURRENCY NOTES"
    blueprint.title = blueprint.headline
    blueprint.supporting_line = (
        "Testing plastic notes for durability, security and sustainability."
    )
    blueprint.sections = [
        BlueprintInfographicSection(
            section_label="Why is RBI planning this?",
            includes=[],
            body="More durable, secure, cost-effective and eco-friendly currency.",
            icon_hint="bank building, RBI seal",
        ),
        BlueprintInfographicSection(
            section_label="Top reasons for switching",
            includes=[
                "Longer Life | Notes last much longer than paper",
                "Cost Effective | Lower printing and logistics costs",
                "Stronger Security | Harder to counterfeit",
                "Water Resistant | Stays cleaner in daily use",
                "Eco Friendly | Less paper waste over time",
                "Future Ready | Modern durable currency system",
            ],
            body="",
            icon_hint="shield, coins, padlock, droplets, recycle, leaf shield",
        ),
        BlueprintInfographicSection(
            section_label="Trial before rollout",
            includes=[],
            body="Tests in select cities before a nationwide launch.",
            icon_hint="map pins, clipboard checklist",
        ),
    ]
    blueprint.customer_quote = "Innovating today for a stronger tomorrow"
    blueprint.cta = "A SMARTER STEP TOWARDS A STRONGER INDIA"
    blueprint.source_footer = "Source: rbi.org.in"
    blueprint = apply_text_hygiene(blueprint, user_prompt=user_prompt)
    notes = list(blueprint.brand_alignment_notes or [])
    notes.insert(0, "Locked: clean explain pattern from sample_infographic_explain_rbi_plastic_perfect.png")
    blueprint.brand_alignment_notes = notes[:8]
    return blueprint


_GENERIC_HEADLINE_WORDS = {
    "education",
    "finance",
    "awareness",
    "investing",
    "investment",
    "overview",
    "explainer",
    "basics",
    "fundamentals",
    "insights",
    "insight",
    "update",
    "news",
    "info",
    "information",
    "financial literacy",
    "did you know",
}


def repair_generic_headline(
    blueprint: CreativeBlueprint,
    *,
    layout_type: LayoutType,
) -> CreativeBlueprint:
    """Rebuild a single-word/generic-category headline (e.g. 'EDUCATION') into a real
    sentence/question — sample DNA (RBI polymer, oil bars) always uses a full statement."""
    is_explain = blueprint.format in ("infographic", "static") or layout_type == "carousel_story"
    if not is_explain:
        return blueprint

    headline = (blueprint.headline or blueprint.title or "").strip()
    words = headline.split()
    is_weak = (
        not headline
        or len(words) <= 2
        or headline.strip(" ?!.").lower() in _GENERIC_HEADLINE_WORDS
    )
    if not is_weak:
        return blueprint

    candidate = (blueprint.supporting_line or "").strip()
    if not candidate and blueprint.sections:
        first = blueprint.sections[0]
        candidate = (first.section_label or "").strip()
        if not candidate and first.includes:
            candidate = str(first.includes[0]).split("|")[0].strip()
    if not candidate:
        candidate = (blueprint.body or "").strip()
    if not candidate:
        return blueprint

    rebuilt = _truncate_words(candidate, 10).rstrip(".,;: ")
    if rebuilt and rebuilt[-1] not in "?!.":
        rebuilt += "?" if rebuilt.lower().startswith(("why", "how", "what", "should", "can", "is", "are", "will")) else ""
    blueprint.headline = rebuilt or headline
    blueprint.title = blueprint.headline
    return blueprint


_DANGLING_ENDS = {
    "a", "an", "the", "and", "or", "but", "with", "of", "to", "for", "by", "in",
    "on", "at", "from", "into", "as", "is", "are", "was", "were", "be", "will",
    "hit", "reach", "about", "than", "that", "this", "these", "those", "their",
    "its", "our", "your", "vs", "versus",
}


def _truncate_words(text: str, max_words: int) -> str:
    """Backward-compatible hard clip — prefer `_clip_complete` for user-facing copy."""
    words = re.sub(r"\s+", " ", (text or "").strip()).split()
    return " ".join(words[:max_words]).strip()


def _clip_complete(text: str, max_words: int, *, min_words: int = 4) -> str:
    """Clip text without leaving mid-sentence / dangling fragments.

    Prefer a full sentence ending (.!?) within the budget. If none, keep up to
    max_words but never end on a dangling connector word (with/and/the/…).
    """
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned:
        return ""
    words = cleaned.split()
    if len(words) <= max_words:
        # Still reject dangling endings on already-short fragments
        if words and words[-1].rstrip(".,;:").casefold() in _DANGLING_ENDS:
            return " ".join(words[:-1]).rstrip(".,;:")
        return cleaned

    window = words[:max_words]
    # Prefer last sentence end inside the window
    joined = " ".join(window)
    for sep in (". ", "! ", "? "):
        idx = joined.rfind(sep)
        if idx >= min_words:
            candidate = joined[: idx + 1].strip()
            if len(candidate.split()) >= min_words:
                return candidate

    # Drop trailing dangling words
    while window and window[-1].rstrip(".,;:").casefold() in _DANGLING_ENDS:
        window = window[:-1]
    result = " ".join(window).rstrip(".,;:")
    # If we still look like a fragment, try one more word from original if it closes
    if result and result[-1] not in ".!?" and len(words) > max_words:
        # Prefer ending with a number+unit pair (e.g. "450 million")
        extra = words[max_words : max_words + 2]
        probe = (result + " " + " ".join(extra)).strip()
        if any(u in probe.casefold() for u in ("million", "billion", "crore", "lakh", "%", "₹")):
            # Take until unit word
            probe_words = probe.split()
            for i, w in enumerate(probe_words):
                if w.casefold().rstrip(".,") in {
                    "million", "billion", "crore", "lakh", "percent", "passengers",
                    "airports", "routes",
                } or w.endswith("%"):
                    return " ".join(probe_words[: i + 1]).rstrip(".,;:")
    return result


def condense_explain_blueprint_copy(
    blueprint: CreativeBlueprint,
    *,
    layout_type: LayoutType,
) -> CreativeBlueprint:
    """Trim explain infographic copy so image model can bake it without overflow.

    Never leave mid-sentence fragments on the approval card.
    """
    from app.graph.models.layer7c_models import BlueprintInfographicSection

    if blueprint.format not in ("infographic",) or layout_type != "carousel_story":
        return blueprint

    blueprint.headline = _clip_complete(blueprint.headline or blueprint.title or "", 12)
    blueprint.title = blueprint.headline
    blueprint.supporting_line = _clip_complete(blueprint.supporting_line or "", 20)
    blueprint.customer_quote = _clip_complete(blueprint.customer_quote or "", 22)

    condensed: list[BlueprintInfographicSection] = []
    for sec in blueprint.sections or []:
        includes_out: list[str] = []
        for raw in (sec.includes or [])[:3]:
            fact = str(raw).strip()
            if "|" in fact:
                title, rest = [p.strip() for p in fact.split("|", 1)]
                includes_out.append(
                    f"{_clip_complete(title, 6)} | {_clip_complete(rest, 16)}"
                )
            else:
                includes_out.append(_clip_complete(fact, 20))
        condensed.append(
            BlueprintInfographicSection(
                section_label=_clip_complete(sec.section_label or "", 12),
                includes=includes_out,
                body=_clip_complete(sec.body or "", 24),
                icon_hint=sec.icon_hint,
                stat=sec.stat,
            )
        )
    blueprint.sections = condensed
    return blueprint


def ensure_explain_sections(
    blueprint: CreativeBlueprint,
    *,
    layout_type: LayoutType,
    user_prompt: str,
) -> CreativeBlueprint:
    """Seed sample-style explain sections when LLM left sections empty."""
    from app.graph.models.layer7c_models import BlueprintInfographicSection

    if layout_type not in ("carousel_story",) and blueprint.format not in ("infographic",):
        return blueprint
    if layout_type in ("static_hub_facts", "static_ranking"):
        return blueprint
    if blueprint.sections and len(blueprint.sections) >= 2:
        return blueprint

    is_polymer = _is_polymer_explain_topic(user_prompt, blueprint)

    if is_polymer:
        seeded = [
            BlueprintInfographicSection(
                section_label="Why is RBI planning this?",
                includes=[],
                body=(
                    "RBI aims to modernize Indian currency by making it more durable, "
                    "secure, cost-effective and eco-friendly."
                ),
                icon_hint="bank building, RBI seal",
            ),
            BlueprintInfographicSection(
                section_label="Top reasons for switching to plastic currency",
                includes=[
                    "Longer Life | Plastic notes last much longer than paper",
                    "Cost Effective | Lower printing, storage and logistics costs",
                    "Stronger Security | Advanced features make counterfeiting harder",
                    "Water & Dirt Resistant | Resists moisture and dirt, stays cleaner",
                    "Environment Friendly | Longer life reduces paper use and waste",
                    "Better for the Economy | Fewer replacements save public money",
                    "Consumer Convenience | Cleaner notes that are easier to handle",
                    "Future Ready | Supports a modern, durable currency system",
                ],
                body="",
                icon_hint="shield, coins, padlock, droplets, recycle, chart, wallet, leaf shield",
            ),
            BlueprintInfographicSection(
                section_label="Trial before rollout",
                includes=[],
                body="RBI will run closed-door tests in select cities before a nationwide launch.",
                icon_hint="map pins, clipboard checklist",
            ),
        ]
        if not (blueprint.customer_quote or "").strip():
            blueprint.customer_quote = (
                "Innovating today for a stronger, smarter and sustainable tomorrow"
            )
        if not (blueprint.source_footer or "").strip():
            blueprint.source_footer = "Source: rbi.org.in"
        if not (blueprint.supporting_line or "").strip():
            blueprint.supporting_line = (
                "RBI is testing plastic notes in select cities to improve durability, security and sustainability."
            )
        if not (blueprint.cta or "").strip():
            blueprint.cta = "A SMARTER STEP TOWARDS A STRONGER INDIA"
        if not (blueprint.headline or "").strip():
            blueprint.headline = "RBI TO TEST PLASTIC CURRENCY NOTES"
            blueprint.title = blueprint.headline
        elif "obi" in (blueprint.headline or "").lower():
            blueprint.headline = "RBI TO TEST PLASTIC CURRENCY NOTES"
            blueprint.title = blueprint.headline
    else:
        facts = list(blueprint.proof_points or [])[:6]
        if not facts and (blueprint.body or "").strip():
            facts = [(blueprint.body or "").strip()[:120]]
        if not facts:
            facts = [
                "Why it matters | Clear benefit for Indian savers with real ₹/% impact.",
                "How it works | Simple practical change explained in plain language.",
                "What to watch | One key signal to track before wider adoption.",
            ]
        # Pack into sample-like sections
        while len(facts) < 6:
            facts.append(facts[-1])
        seeded = [
            BlueprintInfographicSection(
                section_label="Why it matters",
                includes=[str(f)[:140] for f in facts[:3]],
                body="",
                icon_hint="icons",
            ),
            BlueprintInfographicSection(
                section_label="How it works",
                includes=[str(f)[:140] for f in facts[3:6]],
                body="Here's the simple view before wider adoption:",
                icon_hint="clay-3D",
            ),
            BlueprintInfographicSection(
                section_label="What to watch",
                includes=[],
                body=(
                    str(facts[0]).split("|")[-1].strip()[:180]
                    if facts
                    else "Watch the next official update before drawing conclusions."
                ),
                icon_hint="text",
            ),
        ]
        if not (blueprint.customer_quote or "").strip():
            blueprint.customer_quote = (
                "Start with the facts, then decide what this means for your money."
            )

    blueprint.sections = seeded
    notes = list(blueprint.brand_alignment_notes or [])
    notes.append("Auto-fixed: seeded explain sections (LLM left sections empty)")
    blueprint.brand_alignment_notes = notes[:8]
    return blueprint


def finalize_blueprint_for_card(
    blueprint: CreativeBlueprint,
    *,
    layout_type: LayoutType,
    user_prompt: str,
    live_research: dict[str, Any] | None = None,
) -> CreativeBlueprint:
    """Single gate: check + fix ALL safe LLM mistakes, then show on the card.

    Order:
    1) text hygiene (typos, ₹, FDR→FDI, no trailing ...)
    2) attach research sources
    3) bank hub name lock
    4) data-layout repairs (no teaser / fake quote / long body)
    5) carousel 4–7 pad/trim
    6) fill purpose/audience/tone
    7) leftover gaps only in missing_critical
    """
    blueprint.layout_type = layout_type
    if not blueprint.layout_archetype:
        blueprint.layout_archetype = layout_type

    blueprint = apply_text_hygiene(blueprint, user_prompt=user_prompt)
    blueprint = attach_sources_from_research(
        blueprint, live_research, user_prompt=user_prompt
    )

    if layout_type == "static_hub_facts":
        blueprint = repair_bank_hub_sections(blueprint, user_prompt=user_prompt)

    blueprint = repair_data_layout(
        blueprint, layout_type=layout_type, user_prompt=user_prompt
    )
    blueprint = repair_ranking_countries(blueprint, layout_type=layout_type)
    blueprint = repair_carousel_slides(blueprint, layout_type=layout_type)
    blueprint = ensure_explain_sections(
        blueprint, layout_type=layout_type, user_prompt=user_prompt
    )
    blueprint = repair_explain_infographic_copy(
        blueprint, layout_type=layout_type, user_prompt=user_prompt
    )
    blueprint = repair_generic_headline(blueprint, layout_type=layout_type)
    blueprint = condense_explain_blueprint_copy(
        blueprint, layout_type=layout_type
    )
    blueprint = polish_blueprint_meta(
        blueprint, layout_type=layout_type, user_prompt=user_prompt
    )

    # Re-run bank lock after hygiene (labels may have changed)
    if layout_type == "static_hub_facts":
        blueprint = repair_bank_hub_sections(blueprint, user_prompt=user_prompt)

    missing = _collect_remaining_gaps(
        blueprint, layout_type=layout_type, user_prompt=user_prompt
    )
    blueprint.missing_critical = missing

    checklist = [
        "llm_mistakes_auto_checked",
        f"layout_type={layout_type}",
        "orange_accent_required",
        "content_must_fit_no_truncation",
        "text_hygiene_applied",
    ]
    if layout_type == "carousel_story":
        checklist.append("sebi_footer_carousel_only")
    else:
        checklist.append("no_sebi_on_static_infographic")
    if _is_bank_penalty_hub(user_prompt, blueprint.headline or ""):
        checklist.append("bank_names_locked")
    if blueprint.source_footer:
        checklist.append(f"source_footer={blueprint.source_footer}")
    seen: set[str] = set()
    blueprint.validation_checklist = [
        c for c in checklist if not (c in seen or seen.add(c))
    ][:12]

    notes = list(blueprint.brand_alignment_notes or [])
    notes.insert(0, "Gate: LLM draft auto-checked & fixed before approval card")
    blueprint.brand_alignment_notes = notes[:8]
    return blueprint


# Back-compat aliases used by older call sites
def validate_blueprint(
    blueprint: CreativeBlueprint,
    *,
    layout_type: LayoutType,
    user_prompt: str,
) -> CreativeBlueprint:
    return finalize_blueprint_for_card(
        blueprint,
        layout_type=layout_type,
        user_prompt=user_prompt,
        live_research=None,
    )
