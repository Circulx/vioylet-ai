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
    (re.compile(r"\bAds\b"), "FDs"),
    (re.compile(r"\bads\b"), "FDs"),
    (re.compile(r"\bAD\b"), "FD"),
    (re.compile(r"\bFDR\b"), "FDI"),  # common FDI misspelling in rankings
    (re.compile(r"\bASA\b"), "USA"),  # common USA misspelling in country ranks
    (re.compile(r"\bU\.S\.A\b"), "USA"),
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
    return type(blueprint).model_validate(cleaned)


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
        # Keep card lines SHORT — long lines cause AI image gibberish
        short_includes: list[str] = []
        for line in includes[:2]:
            words = str(line).replace("£", "₹").split()
            short_includes.append(" ".join(words[:10]))
        includes = short_includes
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
        # Short facts only — long card text causes AI image gibberish
        short_incs = []
        for x in includes:
            if not x:
                continue
            cleaned = _fix_text(str(x), india_retail=True).replace("£", "₹")
            short_incs.append(" ".join(cleaned.split()[:10]))
        cleaned_sections.append(
            BlueprintInfographicSection(
                section_label=_fix_text(sec.section_label or "", india_retail=True),
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


def attach_sources_from_research(
    blueprint: CreativeBlueprint,
    live_research: dict[str, Any] | None,
) -> CreativeBlueprint:
    """Merge verified research URLs into blueprint.sources + source_footer."""
    from app.graph.models.layer7c_models import BlueprintSource

    research = live_research or {}
    sources: list = list(blueprint.sources or [])
    seen = {s.url.strip().casefold() for s in sources if s.url}

    for fact in research.get("verified_facts") or []:
        url = str(fact.get("source_url") or "").strip()
        title = str(fact.get("source_title") or fact.get("label") or "").strip()
        if url and url.casefold() not in seen:
            sources.append(BlueprintSource(title=title or url, url=url))
            seen.add(url.casefold())

    for src in research.get("sources") or []:
        if not isinstance(src, dict):
            continue
        url = str(src.get("url") or src.get("source_url") or "").strip()
        title = str(src.get("title") or src.get("source_title") or "").strip()
        if url and url.casefold() not in seen:
            sources.append(BlueprintSource(title=title or url, url=url))
            seen.add(url.casefold())

    blueprint.sources = sources[:8]
    domains = source_domains_for_footer(
        [{"url": s.url} for s in blueprint.sources],
        limit=2,
    )
    if domains:
        blueprint.source_footer = "Source: " + " · ".join(domains)
    return blueprint


def polish_blueprint_meta(
    blueprint: CreativeBlueprint,
    *,
    layout_type: LayoutType,
    user_prompt: str,
) -> CreativeBlueprint:
    """Fill empty Purpose / Audience / Tone so the approval card isn't blank."""
    if not (blueprint.purpose or "").strip():
        if layout_type == "static_hub_facts":
            blueprint.purpose = "Educate with short, accurate fact cards"
        elif layout_type == "static_ranking":
            blueprint.purpose = "Show ranked data clearly at a glance"
        else:
            blueprint.purpose = "Educate with a short swipe story"
    if not (blueprint.audience or "").strip():
        blueprint.audience = "Indian LinkedIn professionals / retail savers"
    if not (blueprint.tone or "").strip():
        blueprint.tone = "simple, educational, sample-style"
    if not (blueprint.intent or "").strip():
        blueprint.intent = "awareness"
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
    blueprint = attach_sources_from_research(blueprint, live_research)

    if layout_type == "static_hub_facts":
        blueprint = repair_bank_hub_sections(blueprint, user_prompt=user_prompt)

    blueprint = repair_data_layout(
        blueprint, layout_type=layout_type, user_prompt=user_prompt
    )
    blueprint = repair_ranking_countries(blueprint, layout_type=layout_type)
    blueprint = repair_carousel_slides(blueprint, layout_type=layout_type)
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
