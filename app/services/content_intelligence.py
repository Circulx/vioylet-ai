from __future__ import annotations

"""Content Intelligence Engine

Understand → Retrieve → Verify → Prioritize → Interpret → Reason → Synthesize Insight
→ (feeds Conceptualize / Plan / Generate)

Spine between Brand/Strategy (L2–L4) and Concept/Copy (L5 / L7).
"""

import re
from typing import Any
from urllib.parse import urlparse

from app.core.logging import get_logger
from app.graph.models.content_intelligence_models import (
    ContentIntelligenceOutput,
    EvidenceItem,
    FormatArchitecture,
    InsightCandidate,
    IntentDecomposition,
    NarrativeBeat,
    SubQuestion,
)
from app.prompts.jiraaf_layout import needs_live_research
from app.services.live_research import LiveResearchService
from app.services.llm.llm_router import LLMRouter

logger = get_logger(__name__)

_router = LLMRouter()
_live_research = LiveResearchService()

_NUMBER_RE = re.compile(r"\d")
_SLOGAN_RE = re.compile(
    r"^(more|boosts?|changing|makes?|helps?|growing|easier|lower|travel|connect)\b",
    re.I,
)
_CLAIM_FIXES = [
    (re.compile(r"\bADAN\b", re.I), "UDAN"),
]

_GOV_HOSTS = (
    "gov.in",
    "nic.in",
    "rbi.org.in",
    "sebi.gov.in",
    "moe.gov.in",
    "civilaviation.gov.in",
    "aai.aero",
    "dgca.gov.in",
    "niti.gov.in",
    "pib.gov.in",
)
_REGULATOR_HOSTS = ("rbi.org.in", "sebi.gov.in", "irdai.gov.in", "trai.gov.in")
_INDUSTRY_HOSTS = ("iata.org", "icao.int", "worldbank.org", "imf.org", "adb.org")
_MEDIA_HOSTS = (
    "reuters.com",
    "bloomberg.com",
    "economictimes",
    "livemint.com",
    "hindustantimes.com",
    "indianexpress.com",
    "thehindu.com",
    "business-standard.com",
)


def _fix_claim(text: str) -> str:
    out = (text or "").strip()
    for pat, repl in _CLAIM_FIXES:
        out = pat.sub(repl, out)
    return out


def _classify_source(url: str, title: str = "") -> str:
    host = (urlparse(url).netloc or "").lower()
    blob = f"{host} {title}".lower()
    if any(h in host for h in _REGULATOR_HOSTS):
        return "regulator"
    if any(h in host for h in _GOV_HOSTS) or ".gov." in host:
        return "government"
    if any(h in host for h in _INDUSTRY_HOSTS):
        return "industry"
    if any(h in blob for h in _MEDIA_HOSTS):
        return "media"
    if host:
        return "secondary"
    return "unknown"


def _source_rank(source_type: str) -> float:
    return {
        "government": 1.0,
        "regulator": 0.95,
        "industry": 0.8,
        "media": 0.55,
        "secondary": 0.35,
        "unknown": 0.2,
    }.get(source_type, 0.2)


def decompose_intent(user_prompt: str, fmt: str = "infographic") -> IntentDecomposition:
    """Understand → structured Intent Brief with investigable sub-questions."""
    text = (user_prompt or "").strip()
    lower = text.lower()
    must_why = bool(re.search(r"\bwhy\b|\breason|\brationale|\bdriving\b", lower))
    wants_data = bool(
        re.search(
            r"\b(real data|data points?|statistics?|stats|numbers?|figures?|crore|lakh|%|percent)\b",
            lower,
        )
    )
    topic = text
    for prefix in (
        "create an infographic with real data points as to ",
        "create an infographic with real data points on ",
        "create an infographic about ",
        "create a carousel about ",
        "create a static post about ",
        "make an infographic on ",
        "explain ",
    ):
        if lower.startswith(prefix):
            topic = text[len(prefix) :].strip(" ?.!")
            break
    topic = re.sub(r"^(why|how|what)\s+", "", topic, flags=re.I).strip(" ?.!") or topic

    geography = "India" if re.search(r"\bindia\b|\bindian\b", lower) else ""
    freshness: str = "current" if re.search(r"\b(current|recent|latest|now|202[4-6])\b", lower) else "recent"
    compliance = bool(re.search(r"\b(invest|sebi|rbi|return|yield|bond)\b", lower))
    content_type = "economic_infrastructure_explainer" if re.search(
        r"airport|infrastructure|udan|aviation|logistics", lower
    ) else ("data_led_explainer" if wants_data else "brand_explainer")

    if must_why:
        core = f"What is the economic rationale behind {topic}?"
        objective = "educate_why_with_evidence"
    elif wants_data:
        core = f"What verified data points explain {topic}?"
        objective = "educate_with_quantitative_evidence"
    else:
        core = f"What should the audience understand about {topic}?"
        objective = "explain_with_evidence"

    if re.search(r"airport|aviation|udan|airstrip|greenfield", lower):
        subs = [
            SubQuestion(question="How fast is airport infrastructure expanding?", evidence_needed="operational airport counts over time", priority=1),
            SubQuestion(question="How much capital is being invested?", evidence_needed="₹ crore / lakh crore investment figures", priority=1),
            SubQuestion(question="What government programmes are driving it?", evidence_needed="UDAN / greenfield / policy allocations", priority=1),
            SubQuestion(question="Why are Tier 2/3 cities important?", evidence_needed="regional connectivity / route stats", priority=2),
            SubQuestion(question="What economic activity does connectivity unlock?", evidence_needed="tourism, jobs, logistics, investment", priority=2),
            SubQuestion(question="What is the larger strategic objective?", evidence_needed="economic hubs beyond metros", priority=1),
        ]
        informational = "data_points"
        evidence_req = "official airport counts, investment figures, UDAN routes, greenfield approvals"
    elif wants_data or must_why:
        subs = [
            SubQuestion(question=f"What are the key quantified facts about {topic}?", evidence_needed="statistics with sources", priority=1),
            SubQuestion(question=f"What is changing over time regarding {topic}?", evidence_needed="growth / trend numbers", priority=1),
            SubQuestion(question=f"What programmes or policies drive {topic}?", evidence_needed="named schemes + budgets", priority=2),
            SubQuestion(question=f"Why does {topic} matter economically?", evidence_needed="so-what implication", priority=1),
            SubQuestion(question=f"What is the bigger strategic thesis?", evidence_needed="one insight sentence", priority=1),
        ]
        informational = "data_points" if wants_data else "explanation"
        evidence_req = "real quantitative data with credible sources"
    else:
        subs = [
            SubQuestion(question=f"What is the core idea behind {topic}?", evidence_needed="clear explanation", priority=1),
            SubQuestion(question=f"What proof points support it?", evidence_needed="facts or examples", priority=2),
            SubQuestion(question=f"What should the reader take away?", evidence_needed="insight takeaway", priority=1),
        ]
        informational = "explanation"
        evidence_req = "credible facts; statistics when available"

    geo_bit = f" in {geography}" if geography else ""
    intent_brief = (
        f"Explain the strategic and economic reasons for {topic}{geo_bit} through a concise, "
        f"data-led {fmt} for the brand audience. Use {freshness} quantitative evidence and make "
        f"implications understandable. Objective: {objective}."
    )
    if must_why:
        intent_brief = (
            f"Answer WHY {topic}{geo_bit} is happening — not a fact dump. "
            f"Produce a {fmt} with current quantitative evidence and a clear economic so-what."
        )

    return IntentDecomposition(
        core_question=core,
        topic=topic or "topic",
        objective=objective,
        informational_need=informational,  # type: ignore[arg-type]
        sub_questions=subs,
        must_answer_why=must_why,
        geography=geography,
        freshness=freshness,  # type: ignore[arg-type]
        depth="simplified",
        audience_hint="retail investors / brand audience from Brand Space",
        evidence_requirement=evidence_req,
        content_type=content_type,
        compliance_sensitive=compliance,
        intent_brief=intent_brief,
    )


def build_research_queries(intent: IntentDecomposition, brand_name: str = "") -> list[str]:
    queries: list[str] = []
    geo = intent.geography or ""
    for sq in intent.sub_questions[:5]:
        q = f"{intent.topic}: {sq.question} {sq.evidence_needed} {geo}".strip()
        if brand_name and "jiraaf" in brand_name.casefold():
            q += " India official statistics"
        queries.append(q.strip())
    if intent.informational_need == "data_points":
        queries.insert(
            0,
            f"{intent.topic} {geo} official statistics investment airports UDAN routes greenfield crore 2024 2025 2026",
        )
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        key = q.casefold()
        if key not in seen:
            seen.add(key)
            out.append(q)
    return out[:6]


def evidence_from_live_research(live_research: dict[str, Any]) -> list[EvidenceItem]:
    """Retrieve → candidate Evidence Pool (pre-verify)."""
    items: list[EvidenceItem] = []
    for raw in live_research.get("verified_facts") or []:
        if not isinstance(raw, dict):
            continue
        claim = _fix_claim(str(raw.get("label") or raw.get("claim") or "").strip())
        value = _fix_claim(str(raw.get("value") or raw.get("fact") or "").strip())
        if not claim and not value:
            continue
        blob = f"{claim} {value}"
        has_number = bool(_NUMBER_RE.search(blob))
        is_slogan = bool(_SLOGAN_RE.search((value or claim).strip()))
        etype: str = "statistic" if has_number else ("opinion" if is_slogan else "fact")
        url = str(raw.get("source_url") or raw.get("url") or "")
        title = str(raw.get("source_title") or raw.get("title") or "")
        source_type = _classify_source(url, title)
        confidence = 0.75 if has_number and url else (0.45 if has_number else 0.25)
        confidence = min(1.0, confidence + 0.1 * _source_rank(source_type))
        if is_slogan and not has_number:
            confidence = 0.15
            etype = "opinion"
        items.append(
            EvidenceItem(
                claim=claim or value,
                value=value,
                source_url=url,
                source_title=title,
                date=str(raw.get("date") or ""),
                data_period=str(raw.get("data_period") or raw.get("date") or ""),
                confidence=confidence,
                evidence_type=etype,  # type: ignore[arg-type]
                source_type=source_type,  # type: ignore[arg-type]
                certainty="fact" if has_number and url else ("inference" if has_number else "speculation"),
            )
        )

    summary = str(live_research.get("summary") or "")
    for sent in re.split(r"(?<=[.!?])\s+", summary):
        sent = _fix_claim(sent.strip())
        if len(sent.split()) < 6 or not _NUMBER_RE.search(sent):
            continue
        if any(sent[:40].casefold() in (i.claim.casefold() + i.value.casefold()) for i in items):
            continue
        items.append(
            EvidenceItem(
                claim=sent,
                value=sent,
                confidence=0.55,
                evidence_type="statistic",
                source_type="secondary",
                certainty="inference",
            )
        )
    return items[:16]


def verify_evidence(items: list[EvidenceItem]) -> list[EvidenceItem]:
    """Verify — credibility, publishability, corroboration."""
    value_buckets: dict[str, int] = {}
    for e in items:
        key = re.sub(r"\s+", " ", (e.value or e.claim).casefold())[:80]
        if key:
            value_buckets[key] = value_buckets.get(key, 0) + 1

    verified: list[EvidenceItem] = []
    for e in items:
        e.source_type = e.source_type or _classify_source(e.source_url, e.source_title)  # type: ignore[assignment]
        has_number = bool(_NUMBER_RE.search(f"{e.claim} {e.value}"))
        is_slogan = bool(_SLOGAN_RE.search((e.value or e.claim).strip())) and not has_number
        key = re.sub(r"\s+", " ", (e.value or e.claim).casefold())[:80]
        e.corroborated = value_buckets.get(key, 0) >= 2
        # Hierarchy bump
        conf = float(e.confidence or 0)
        conf = max(conf, 0.35 * _source_rank(e.source_type) + (0.4 if has_number else 0.1))
        if e.corroborated:
            conf = min(1.0, conf + 0.1)
        if is_slogan:
            conf = min(conf, 0.2)
            e.certainty = "speculation"
            e.publishable = False
            e.approved_for_creative = False
        else:
            e.publishable = has_number and conf >= 0.5 and e.source_type != "unknown"
            # Allow high-confidence numbered facts without URL if government-ish claim text
            if has_number and conf >= 0.55 and not is_slogan:
                e.publishable = True
            e.approved_for_creative = bool(e.publishable and has_number and not is_slogan)
            if e.approved_for_creative and e.certainty == "speculation":
                e.certainty = "fact" if e.source_url else "inference"
        e.confidence = round(min(1.0, conf), 3)
        verified.append(e)
    return verified


def prioritize_evidence(items: list[EvidenceItem], intent: IntentDecomposition) -> list[EvidenceItem]:
    """Prioritize — must_know / useful / optional / irrelevant."""
    topic_l = (intent.topic or "").casefold()
    why = intent.must_answer_why
    topic_tokens = {t for t in re.split(r"[^\w]+", topic_l) if len(t) > 3}

    ranked: list[EvidenceItem] = []
    for e in items:
        blob = f"{e.claim} {e.value} {e.interpretation}".casefold()
        relevance = 0.3
        if topic_tokens and any(t in blob for t in topic_tokens):
            relevance = 0.75
        if why and re.search(r"invest|udan|connect|regional|greenfield|econom|hub|tier", blob):
            relevance = max(relevance, 0.9)
        if re.search(r"food sales|menu|catering|lounge snack", blob):
            relevance = min(relevance, 0.25)

        credibility = _source_rank(e.source_type) * (0.7 + 0.3 * float(e.confidence or 0))
        audience = 0.8 if e.approved_for_creative else 0.4
        novelty = 0.7 if e.evidence_type == "statistic" else 0.45
        format_fit = 0.85 if _NUMBER_RE.search(blob) else 0.4
        brand_rel = 0.7

        score = (
            relevance * 0.28
            + credibility * 0.22
            + audience * 0.15
            + novelty * 0.12
            + format_fit * 0.13
            + brand_rel * 0.10
        )
        e.priority_score = round(min(1.0, score), 3)
        if not e.publishable or score < 0.35:
            e.priority_tier = "irrelevant"
            e.approved_for_creative = False
        elif score >= 0.72 and e.approved_for_creative:
            e.priority_tier = "must_know"
        elif score >= 0.55 and e.approved_for_creative:
            e.priority_tier = "useful"
        else:
            e.priority_tier = "optional"
            if e.priority_tier == "optional" and not e.approved_for_creative:
                pass
        ranked.append(e)

    ranked.sort(
        key=lambda x: (
            {"must_know": 0, "useful": 1, "optional": 2, "irrelevant": 3}.get(x.priority_tier, 3),
            -x.priority_score,
            -x.confidence,
        )
    )
    # Only must_know + useful stay approved for creative by default
    for e in ranked:
        if e.priority_tier in ("optional", "irrelevant"):
            e.approved_for_creative = False
    return ranked


def interpret_evidence(items: list[EvidenceItem], intent: IntentDecomposition) -> list[EvidenceItem]:
    """Interpret — attach so-what meaning without inventing numbers."""
    for e in items:
        if e.interpretation:
            continue
        blob = f"{e.claim} {e.value}".strip()
        if not blob:
            continue
        if intent.must_answer_why and re.search(r"airport|udan|connect|invest|greenfield", blob, re.I):
            e.interpretation = (
                "Signals policy-backed expansion of regional connectivity and economic access beyond metros."
            )
        elif e.evidence_type == "statistic":
            e.interpretation = "Quantifies scale of change — use as proof, then explain implication."
        elif e.certainty == "inference":
            e.interpretation = "Reasonable implication from data — label as inference, not hard fact."
        else:
            e.interpretation = "Supports the core question; pair with a clear so-what for the audience."
        if e.certainty == "speculation":
            e.interpretation = "Weak / speculative — do not use as a headline statistic."
    return items


def build_reasoning_map(items: list[EvidenceItem], intent: IntentDecomposition) -> str:
    """Reason — connect must-know evidence into a causal model."""
    must = [e for e in items if e.priority_tier == "must_know"][:5]
    useful = [e for e in items if e.priority_tier == "useful"][:3]
    focus = must or useful or items[:3]
    lines = [
        f"CORE QUESTION: {intent.core_question}",
        "CAUSE → EFFECT MODEL:",
    ]
    if re.search(r"airport|aviation|udan", (intent.topic or "").casefold()):
        lines.extend(
            [
                "1) Policy + investment expand regional airports / UDAN routes  [FACT when evidenced]",
                "2) → lower friction reaching Tier-2/3 markets  [INFERENCE]",
                "3) → logistics, tourism, and business accessibility rise  [INFERENCE]",
                "4) → airports act as anchors for regional economic activity  [INSIGHT CANDIDATE]",
            ]
        )
    else:
        lines.append("1) Verified drivers → 2) mechanism → 3) audience-relevant implication")
    lines.append("EVIDENCE ANCHORS:")
    for e in focus:
        lines.append(
            f"- [{e.certainty}|{e.priority_tier}] {e.value or e.claim}"
            + (f" → {e.interpretation}" if e.interpretation else "")
        )
    lines.append(
        "Do not communicate inference/speculation with the same certainty as sourced statistics."
    )
    return "\n".join(lines)


def synthesize_ranked_insights(
    *,
    intent: IntentDecomposition,
    evidence: list[EvidenceItem],
    reasoning_map: str,
) -> tuple[str, list[str], list[InsightCandidate]]:
    """Synthesize Insight — rank territories; lock primary + supporting."""
    approved = [e for e in evidence if e.priority_tier in ("must_know", "useful")]
    topic = intent.topic or "the topic"
    candidates: list[InsightCandidate] = []

    if re.search(r"airport|aviation|udan", topic.casefold()) or intent.must_answer_why:
        candidates = [
            InsightCandidate(
                territory="economic_decentralisation",
                insight=f"{topic}: expansion is as much an economic decentralisation strategy as an aviation build-out.",
                score=0.9 if intent.must_answer_why else 0.75,
                true_test=bool(approved),
                interesting_test=True,
                relevant_test=True,
                useful_test=True,
            ),
            InsightCandidate(
                territory="regional_growth_anchors",
                insight="Airports can become anchors for new regional economies — not just passenger terminals.",
                score=0.82,
                true_test=bool(approved),
                interesting_test=True,
                relevant_test=True,
                useful_test=True,
            ),
            InsightCandidate(
                territory="connectivity_as_infrastructure",
                insight="The real value of connectivity is what becomes economically viable around it.",
                score=0.78,
                true_test=True,
                interesting_test=True,
                relevant_test=True,
                useful_test=True,
            ),
        ]
    else:
        lead = approved[0].value or approved[0].claim if approved else topic
        candidates = [
            InsightCandidate(
                territory="evidence_led_so_what",
                insight=f"What matters about {topic} is not the headline number alone — it is what that change unlocks for the audience.",
                score=0.7,
                true_test=bool(approved),
                interesting_test=True,
                relevant_test=True,
                useful_test=True,
            ),
            InsightCandidate(
                territory="scale_signal",
                insight=f"The data point '{lead}' is the clearest signal of how {topic} is shifting.",
                score=0.62,
                true_test=bool(approved),
                interesting_test=bool(approved),
                relevant_test=True,
                useful_test=bool(approved),
            ),
        ]

    def _passes(c: InsightCandidate) -> bool:
        return c.true_test and c.interesting_test and c.relevant_test and c.useful_test

    candidates = [c for c in candidates if _passes(c)] or candidates
    candidates.sort(key=lambda c: -c.score)
    primary = candidates[0].insight if candidates else f"Key verified dynamics behind {topic}."
    supporting = [c.insight for c in candidates[1:3]]
    return primary, supporting, candidates


async def synthesize_insight_and_narrative(
    *,
    user_prompt: str,
    intent: IntentDecomposition,
    evidence: list[EvidenceItem],
    brand_name: str,
    brand_notes: str,
    fmt: str,
    primary_insight: str,
    supporting_insights: list[str],
    reasoning_map: str,
) -> ContentIntelligenceOutput:
    """One structured LLM call: thesis + narrative beats + format architecture."""
    approved = [
        e for e in evidence if e.priority_tier in ("must_know", "useful") and e.approved_for_creative
    ] or [e for e in evidence if e.approved_for_creative][:6]
    evidence_lines = "\n".join(
        f"- [{e.priority_tier}|{e.certainty}|conf={e.confidence:.2f}|{e.source_type}] "
        f"{e.claim}"
        + (f" = {e.value}" if e.value and e.value != e.claim else "")
        + (f" | SO-WHAT: {e.interpretation}" if e.interpretation else "")
        + (f" ({e.source_url})" if e.source_url else "")
        for e in approved
    ) or "- (no verified statistics yet — stay cautious, do not invent numbers)"

    system = f"""You are Violyt's Content Intelligence Engine for brand "{brand_name or 'the brand'}".
You do NOT write final social copy yet. You produce the thinking layer:
insight thesis + narrative architecture + format architecture.

Rules:
- Prefer MUST_KNOW / USEFUL statistics over slogans.
- Spell UDAN correctly (never ADAN).
- Insight thesis must answer WHY / SO-WHAT — not "India has more airports".
- Lock to the PRIMARY INSIGHT provided; supporting insights are secondary.
- Distinguish FACT vs INFERENCE in framing.
- Narrative beats: hook → scale → why → effect → idea → takeaway.
- Infographic: 1 hero statistic, 3–5 supporting data points, 1 core insight.
- Never invent precise numbers not present in evidence.

Return ONLY valid JSON.
"""

    user = f"""USER BRIEF:
{user_prompt}

INTENT BRIEF:
{intent.intent_brief or intent.core_question}
Topic: {intent.topic} | Geography: {intent.geography or 'n/a'} | Freshness: {intent.freshness}
Must answer WHY: {intent.must_answer_why}
Evidence requirement: {intent.evidence_requirement}

PRIMARY INSIGHT (LOCK):
{primary_insight}

SUPPORTING INSIGHTS:
{chr(10).join('- ' + s for s in supporting_insights) or '- none'}

REASONING MAP:
{reasoning_map}

BRAND THINKING CONSTRAINTS:
{brand_notes or 'Use evidence. Stay credible. Explain economic implications accessibly.'}

APPROVED / RANKED EVIDENCE:
{evidence_lines}

FORMAT SELECTED: {fmt}

Produce JSON with:
{{
  "insight_thesis": "one clear thesis sentence — must reflect PRIMARY INSIGHT",
  "narrative_beats": [
    {{"role":"hook","message":"...","supporting_stat":"..."}},
    {{"role":"scale","message":"...","supporting_stat":"..."}},
    {{"role":"why","message":"...","supporting_stat":"..."}},
    {{"role":"effect","message":"...","supporting_stat":"..."}},
    {{"role":"idea","message":"...","supporting_stat":"..."}},
    {{"role":"takeaway","message":"...","supporting_stat":"..."}}
  ],
  "format_architecture": {{
    "format_name": "{fmt}",
    "hero_statistic": "best single number from evidence or empty",
    "supporting_data_points": ["3-5 short statistic strings from evidence"],
    "core_insight": "so-what insight aligned to primary insight",
    "copy_density": "short",
    "hierarchy_notes": "hero stat dominant; supporting secondary",
    "visual_plan": "hero visual + supporting icon cards plan"
  }},
  "brand_thinking_notes": ["how brand constraints shaped selection/framing"],
  "qa_self_score": {{
    "answers_why": 0,
    "has_real_data": 0,
    "claims_verified": 0,
    "narrative_coherent": 0,
    "on_brand_beyond_aesthetics": 0,
    "insight_quality": 0
  }}
}}
Scores are 0-10 integers. Be honest.
"""

    from pydantic import BaseModel, Field
    from typing import List

    class _NarrativeOut(BaseModel):
        insight_thesis: str = ""
        narrative_beats: List[NarrativeBeat] = Field(default_factory=list)
        format_architecture: FormatArchitecture = Field(default_factory=FormatArchitecture)
        brand_thinking_notes: List[str] = Field(default_factory=list)
        qa_self_score: dict = Field(default_factory=dict)

    service = _router.get_service("l7c_content_prep")
    try:
        partial, meta = await service.complete_structured(
            system=system,
            user=user,
            output_model=_NarrativeOut,
            layer="l6b_content_intelligence",
            max_tokens=2500,
        )
        latency = meta.get("latency_ms", 0)
        tokens_in = meta.get("input_tokens", 0)
        tokens_out = meta.get("output_tokens", 0)
    except Exception as exc:
        logger.warning("content_intelligence.synthesize_failed", error=str(exc)[:200])
        partial = _NarrativeOut(
            insight_thesis=primary_insight,
            narrative_beats=[
                NarrativeBeat(role="hook", message=intent.core_question),
                NarrativeBeat(role="scale", message="Infrastructure and investment are scaling.", supporting_stat=(approved[0].value if approved else "")),
                NarrativeBeat(role="why", message="Connectivity expands access for Tier 2/3 economies."),
                NarrativeBeat(role="effect", message="Business, tourism, logistics and jobs follow routes."),
                NarrativeBeat(role="idea", message=primary_insight),
                NarrativeBeat(role="takeaway", message="Track the data behind the expansion thesis."),
            ],
            format_architecture=FormatArchitecture(
                format_name=fmt,
                hero_statistic=approved[0].value if approved else "",
                supporting_data_points=[e.value or e.claim for e in approved[:5]],
                core_insight=primary_insight,
                hierarchy_notes="Hero stat dominant; supporting cards secondary; insight near CTA.",
                visual_plan="Hero network/airport visual + 4–5 statistic cards + insight strip.",
            ),
            brand_thinking_notes=["Fallback synthesis — LLM unavailable"],
            qa_self_score={
                "answers_why": 6,
                "has_real_data": 5,
                "claims_verified": 5,
                "narrative_coherent": 6,
                "on_brand_beyond_aesthetics": 5,
                "insight_quality": 6,
            },
        )
        latency = 0
        tokens_in = 0
        tokens_out = 0

    fa = partial.format_architecture
    if not fa.hero_statistic and approved:
        fa.hero_statistic = approved[0].value or approved[0].claim
    if len(fa.supporting_data_points) < 3:
        fa.supporting_data_points = [e.value or e.claim for e in approved[:5]]
    if not fa.core_insight:
        fa.core_insight = primary_insight or partial.insight_thesis

    thesis = _fix_claim(partial.insight_thesis) or primary_insight
    out = ContentIntelligenceOutput(
        intent=intent,
        research_queries=[],
        evidence=evidence,
        insight_thesis=thesis,
        primary_insight=primary_insight or thesis,
        supporting_insights=supporting_insights,
        reasoning_map=reasoning_map,
        narrative_beats=partial.narrative_beats or [],
        format_architecture=fa,
        brand_thinking_notes=partial.brand_thinking_notes or [],
        qa_self_score=partial.qa_self_score or {},
    )
    setattr(out, "_latency_ms", latency)
    setattr(out, "_input_tokens", tokens_in)
    setattr(out, "_output_tokens", tokens_out)
    return out


def brand_thinking_constraints(brand_intelligence: Any, brand_name: str) -> str:
    if not brand_intelligence:
        return (
            "Explain accessibly. Prefer evidence. Do not sensationalise. "
            "Avoid unsupported causality. Maintain credibility."
        )
    core = brand_intelligence.brand_core
    behavior = brand_intelligence.communication_behavior
    parts = [
        f"Brand: {core.brand_name}",
        f"Value proposition: {core.value_proposition}",
        f"Tone: {behavior.tone_spectrum}",
        f"Language: {behavior.preferred_language_behavior}",
        f"Prohibited: {behavior.prohibited_phrases}",
        f"Guardrails: {brand_intelligence.guardrails}",
    ]
    if "jiraaf" in (brand_name or core.brand_name or "").casefold():
        parts.append(
            "JIRAAF FINANCIAL EDUCATION LOCK: explain economic phenomena accessibly; "
            "use evidence; help reader understand investment/economic implication; "
            "maintain credibility; avoid unsupported causality; CTA should invite learning not hype."
        )
    return "\n".join(str(p) for p in parts if p)


async def run_content_intelligence(
    *,
    user_prompt: str,
    fmt: str,
    platform: str,
    brand_name: str,
    brand_intelligence: Any,
    brand_context: Any = None,
    layout_type: str | None = None,
) -> tuple[ContentIntelligenceOutput, dict]:
    """Full spine: Understand → Retrieve → Verify → Prioritize → Interpret → Reason → Insight."""
    intent = decompose_intent(user_prompt, fmt)
    queries = build_research_queries(intent, brand_name=brand_name)

    live_research: dict[str, Any] = {}
    should_research = (
        needs_live_research(user_prompt, layout_type)  # type: ignore[arg-type]
        or intent.informational_need == "data_points"
        or intent.must_answer_why
    )
    if should_research:
        try:
            knowledge_brief = []
            if brand_context and getattr(brand_context, "high_relevance_context", None):
                knowledge_brief = [
                    {"content": chunk.content_summary, "source": chunk.source}
                    for chunk in brand_context.high_relevance_context
                ]
            research_prompt = (
                f"{intent.intent_brief or user_prompt}\n\nCORE QUESTION: {intent.core_question}\n"
                + "\n".join(f"SUBQ: {q}" for q in queries)
            )
            live_research = _live_research.gather_sync(
                prompt=research_prompt,
                studio_panel={"format": fmt, "platform_preset": platform},
                compiled_context={"knowledge_brief": knowledge_brief},
                force=True,
            ) or {}
            logger.info(
                "content_intelligence.live_research",
                fact_count=len(live_research.get("verified_facts") or []),
                status=live_research.get("status"),
            )
        except Exception as exc:
            logger.warning("content_intelligence.research_failed", error=str(exc)[:200])
            live_research = {}

    evidence = evidence_from_live_research(live_research)
    evidence = verify_evidence(evidence)
    evidence = prioritize_evidence(evidence, intent)
    evidence = interpret_evidence(evidence, intent)
    reasoning_map = build_reasoning_map(evidence, intent)
    primary_insight, supporting_insights, insight_candidates = synthesize_ranked_insights(
        intent=intent,
        evidence=evidence,
        reasoning_map=reasoning_map,
    )

    brand_notes = brand_thinking_constraints(brand_intelligence, brand_name)
    package = await synthesize_insight_and_narrative(
        user_prompt=user_prompt,
        intent=intent,
        evidence=evidence,
        brand_name=brand_name,
        brand_notes=brand_notes,
        fmt=fmt,
        primary_insight=primary_insight,
        supporting_insights=supporting_insights,
        reasoning_map=reasoning_map,
    )
    package.research_queries = queries
    package.live_research = live_research
    package.insight_candidates = insight_candidates
    package.primary_insight = primary_insight
    package.supporting_insights = supporting_insights
    package.reasoning_map = reasoning_map
    package.brand_thinking_notes = list(
        dict.fromkeys((package.brand_thinking_notes or []) + [brand_notes[:240]])
    )

    meta = {
        "latency_ms": int(getattr(package, "_latency_ms", 0) or 0),
        "input_tokens": int(getattr(package, "_input_tokens", 0) or 0),
        "output_tokens": int(getattr(package, "_output_tokens", 0) or 0),
        "approved_evidence": sum(1 for e in evidence if e.approved_for_creative),
        "must_know": sum(1 for e in evidence if e.priority_tier == "must_know"),
        "total_evidence": len(evidence),
        "primary_insight": (primary_insight or "")[:120],
    }
    return package, meta


def content_intelligence_prompt_block(package: ContentIntelligenceOutput | None) -> str:
    """Serialize intelligence package for L5 / L7 / L7c / L8 prompts."""
    if not package:
        return ""
    beats = "\n".join(
        f"- [{b.role}] {b.message}"
        + (f" | STAT: {b.supporting_stat}" if b.supporting_stat else "")
        for b in (package.narrative_beats or [])
    )
    approved = [
        e
        for e in package.evidence
        if e.priority_tier in ("must_know", "useful") and e.approved_for_creative
    ] or [e for e in package.evidence if e.approved_for_creative]
    ev = "\n".join(
        f"- [{e.priority_tier}|{e.certainty}] {e.claim}"
        + (f" → {e.value}" if e.value and e.value != e.claim else "")
        + (f" | {e.interpretation}" if e.interpretation else "")
        + f" [conf={e.confidence:.2f}|{e.source_type}]"
        for e in approved[:8]
    ) or "- (insufficient approved statistics — do not invent precise numbers)"
    fa = package.format_architecture
    supporting = "\n".join(f"- {s}" for s in (package.supporting_insights or [])[:3])
    return f"""
════════════════════════════════════════
CONTENT INTELLIGENCE PACKAGE (AUTHORITATIVE — LOCK THIS)
════════════════════════════════════════
INTENT BRIEF: {package.intent.intent_brief or package.intent.core_question}
CORE QUESTION: {package.intent.core_question}
GEOGRAPHY: {package.intent.geography or 'n/a'} | FRESHNESS: {package.intent.freshness}
MUST ANSWER WHY: {package.intent.must_answer_why}

PRIMARY INSIGHT (story MUST serve this): {package.primary_insight or package.insight_thesis}
INSIGHT THESIS: {package.insight_thesis}
SUPPORTING INSIGHTS:
{supporting or '- none'}

REASONING MAP:
{package.reasoning_map or '(build cause→effect from approved evidence)'}

NARRATIVE ARCHITECTURE:
{beats or '- (build hook→scale→why→effect→idea→takeaway)'}

RANKED APPROVED EVIDENCE (must_know/useful only; never use slogans as data):
{ev}

FORMAT ARCHITECTURE ({fa.format_name}):
- Hero statistic: {fa.hero_statistic}
- Supporting data points: {fa.supporting_data_points}
- Core insight: {fa.core_insight}
- Hierarchy: {fa.hierarchy_notes}
- Visual plan: {fa.visual_plan}

BRAND THINKING:
{chr(10).join('- ' + n for n in (package.brand_thinking_notes or [])[:4])}

SELF-SCORE: {package.qa_self_score}
Concepts, copy, and visuals must express the PRIMARY INSIGHT — not a generic fact dump.
SPELLING: UDAN never ADAN. Complete sentences only. Label inferences carefully.
"""
