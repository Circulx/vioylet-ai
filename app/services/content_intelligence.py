from __future__ import annotations

"""Content Intelligence Engine

Prompt → interpret → decompose → investigate → verify → insight → narrative → format architecture

This is the missing spine between Brand/Strategy (L2–L4) and Copy (L7).
"""

import re
from typing import Any

from app.core.logging import get_logger
from app.graph.models.content_intelligence_models import (
    ContentIntelligenceOutput,
    EvidenceItem,
    FormatArchitecture,
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

# Prefer quantifiable evidence language
_NUMBER_RE = re.compile(r"\d")
_SLOGAN_RE = re.compile(
    r"^(more|boosts?|changing|makes?|helps?|growing|easier|lower|travel|connect)\b",
    re.I,
)

# Common scheme / proper-noun fixes before creative use
_CLAIM_FIXES = [
    (re.compile(r"\bADAN\b", re.I), "UDAN"),
]


def _fix_claim(text: str) -> str:
    out = (text or "").strip()
    for pat, repl in _CLAIM_FIXES:
        out = pat.sub(repl, out)
    return out


def decompose_intent(user_prompt: str, fmt: str = "infographic") -> IntentDecomposition:
    """Rule-first intent decomposition — always produces investigable sub-questions."""
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

    if must_why:
        core = f"What is the economic rationale behind {topic}?"
    elif wants_data:
        core = f"What verified data points explain {topic}?"
    else:
        core = f"What should the audience understand about {topic}?"

    # Domain-aware sub-questions for infrastructure / airports
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
    elif wants_data or must_why:
        subs = [
            SubQuestion(question=f"What are the key quantified facts about {topic}?", evidence_needed="statistics with sources", priority=1),
            SubQuestion(question=f"What is changing over time regarding {topic}?", evidence_needed="growth / trend numbers", priority=1),
            SubQuestion(question=f"What programmes or policies drive {topic}?", evidence_needed="named schemes + budgets", priority=2),
            SubQuestion(question=f"Why does {topic} matter economically?", evidence_needed="so-what implication", priority=1),
            SubQuestion(question=f"What is the bigger strategic thesis?", evidence_needed="one insight sentence", priority=1),
        ]
        informational = "data_points" if wants_data else "explanation"
    else:
        subs = [
            SubQuestion(question=f"What is the core idea behind {topic}?", evidence_needed="clear explanation", priority=1),
            SubQuestion(question=f"What proof points support it?", evidence_needed="facts or examples", priority=2),
            SubQuestion(question=f"What should the reader take away?", evidence_needed="insight takeaway", priority=1),
        ]
        informational = "explanation"

    return IntentDecomposition(
        core_question=core,
        topic=topic or "topic",
        objective="financial_education_with_evidence" if "jiraaf" in lower else "explain_with_evidence",
        informational_need=informational,  # type: ignore[arg-type]
        sub_questions=subs,
        must_answer_why=must_why,
    )


def build_research_queries(intent: IntentDecomposition, brand_name: str = "") -> list[str]:
    queries: list[str] = []
    for sq in intent.sub_questions[:5]:
        q = f"{intent.topic}: {sq.question} {sq.evidence_needed}"
        if brand_name and "jiraaf" in brand_name.casefold():
            q += " India official statistics"
        queries.append(q.strip())
    # Always add an explicit stats query for data briefs
    if intent.informational_need == "data_points":
        queries.insert(
            0,
            f"{intent.topic} official statistics investment airports UDAN routes greenfield crore 2024 2025",
        )
    # Dedupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        key = q.casefold()
        if key not in seen:
            seen.add(key)
            out.append(q)
    return out[:6]


def evidence_from_live_research(live_research: dict[str, Any]) -> list[EvidenceItem]:
    """Map live research rows → typed evidence with confidence + approval gate."""
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
        confidence = 0.75 if has_number and raw.get("source_url") else (0.45 if has_number else 0.25)
        if is_slogan and not has_number:
            confidence = 0.15
            etype = "opinion"
        approved = confidence >= 0.55 and has_number and not is_slogan
        items.append(
            EvidenceItem(
                claim=claim or value,
                value=value,
                source_url=str(raw.get("source_url") or raw.get("url") or ""),
                source_title=str(raw.get("source_title") or raw.get("title") or ""),
                date=str(raw.get("date") or ""),
                confidence=confidence,
                evidence_type=etype,  # type: ignore[arg-type]
                approved_for_creative=approved,
            )
        )

    # Also mine summary sentences that contain numbers
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
                approved_for_creative=True,
            )
        )
    # Prefer approved statistics first
    items.sort(key=lambda e: (not e.approved_for_creative, -e.confidence))
    return items[:12]


async def synthesize_insight_and_narrative(
    *,
    user_prompt: str,
    intent: IntentDecomposition,
    evidence: list[EvidenceItem],
    brand_name: str,
    brand_notes: str,
    fmt: str,
) -> ContentIntelligenceOutput:
    """One structured LLM call: thesis + narrative beats + format architecture."""
    approved = [e for e in evidence if e.approved_for_creative] or evidence[:6]
    evidence_lines = "\n".join(
        f"- [{e.evidence_type}|conf={e.confidence:.2f}|approved={e.approved_for_creative}] "
        f"{e.claim}"
        + (f" = {e.value}" if e.value and e.value != e.claim else "")
        + (f" ({e.source_url})" if e.source_url else "")
        for e in approved
    ) or "- (no verified statistics yet — stay cautious, do not invent numbers)"

    system = f"""You are Violyt's Content Intelligence Engine for brand "{brand_name or 'the brand'}".
You do NOT write final social copy yet. You produce the thinking layer:
insight thesis + narrative architecture + format architecture.

Rules:
- Prefer STATISTICS over slogans. Prefer APPROVED evidence.
- Spell UDAN correctly (never ADAN).
- For financial education brands (e.g. Jiraaf): accessible, evidence-led, no sensationalism, no unsupported causality.
- Insight thesis must answer WHY / SO-WHAT — not "India has more airports".
- Narrative beats must follow: hook → scale → why → effect → idea → takeaway.
- Infographic architecture: 1 hero statistic, 3–5 supporting data points, 1 core insight, short copy.
- Never invent precise numbers not present in evidence. If evidence is thin, say so in thesis cautiously.

Return ONLY valid JSON matching ContentIntelligenceOutput fields we ask for below.
"""

    user = f"""USER BRIEF:
{user_prompt}

FORMAT SELECTED: {fmt}

INTENT:
Core question: {intent.core_question}
Topic: {intent.topic}
Must answer WHY: {intent.must_answer_why}
Sub-questions:
{chr(10).join(f'- {s.question}' for s in intent.sub_questions)}

BRAND THINKING CONSTRAINTS:
{brand_notes or 'Use evidence. Stay credible. Explain economic implications accessibly.'}

APPROVED / CANDIDATE EVIDENCE:
{evidence_lines}

Produce JSON with:
{{
  "insight_thesis": "one clear thesis sentence answering the core question",
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
    "core_insight": "so-what insight",
    "copy_density": "short",
    "hierarchy_notes": "what is primary vs secondary visually",
    "visual_plan": "hero visual + supporting icon cards plan"
  }},
  "brand_thinking_notes": ["how brand constraints shaped selection/framing"],
  "qa_self_score": {{
    "answers_why": 0,
    "has_real_data": 0,
    "claims_verified": 0,
    "narrative_coherent": 0,
    "on_brand_beyond_aesthetics": 0
  }}
}}
Scores are 0-10 integers. Be honest.
"""

    class _Synth(ContentIntelligenceOutput):
        # Reuse model but intent/evidence filled by caller
        pass

    # Lightweight partial model via generic structured call into dict then merge
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
            insight_thesis=(
                f"{intent.topic} is expanding to unlock economic activity beyond major metros."
                if intent.must_answer_why
                else f"Key verified facts about {intent.topic}."
            ),
            narrative_beats=[
                NarrativeBeat(role="hook", message=intent.core_question),
                NarrativeBeat(role="scale", message="Infrastructure and investment are scaling.", supporting_stat=(approved[0].value if approved else "")),
                NarrativeBeat(role="why", message="Connectivity expands access for Tier 2/3 economies."),
                NarrativeBeat(role="effect", message="Business, tourism, logistics and jobs follow routes."),
                NarrativeBeat(role="idea", message="Airports can act as regional economic anchors."),
                NarrativeBeat(role="takeaway", message="Track the data behind the expansion thesis."),
            ],
            format_architecture=FormatArchitecture(
                format_name=fmt,
                hero_statistic=approved[0].value if approved else "",
                supporting_data_points=[e.value or e.claim for e in approved[:5]],
                core_insight="Connectivity creates new centres of economic activity.",
                hierarchy_notes="Hero stat dominant; supporting cards secondary; insight near CTA.",
                visual_plan="Hero network/airport visual + 4–5 statistic cards + insight strip.",
            ),
            brand_thinking_notes=["Fallback synthesis — LLM unavailable"],
            qa_self_score={"answers_why": 5, "has_real_data": 4, "claims_verified": 4, "narrative_coherent": 5, "on_brand_beyond_aesthetics": 5},
        )
        latency = 0
        tokens_in = 0
        tokens_out = 0

    # Ensure format architecture has evidence-backed stats if LLM left them empty
    fa = partial.format_architecture
    if not fa.hero_statistic and approved:
        fa.hero_statistic = approved[0].value or approved[0].claim
    if len(fa.supporting_data_points) < 3:
        fa.supporting_data_points = [e.value or e.claim for e in approved[:5]]
    if not fa.core_insight:
        fa.core_insight = partial.insight_thesis

    out = ContentIntelligenceOutput(
        intent=intent,
        research_queries=[],
        evidence=evidence,
        insight_thesis=_fix_claim(partial.insight_thesis),
        narrative_beats=partial.narrative_beats or [],
        format_architecture=fa,
        brand_thinking_notes=partial.brand_thinking_notes or [],
        qa_self_score=partial.qa_self_score or {},
    )
    # Attach token meta via attribute for the node
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
    """Full spine: decompose → research → verify → insight → narrative → format."""
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
            # Pack sub-questions into the research prompt so search covers them
            research_prompt = (
                f"{user_prompt}\n\nCORE QUESTION: {intent.core_question}\n"
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
    brand_notes = brand_thinking_constraints(brand_intelligence, brand_name)
    package = await synthesize_insight_and_narrative(
        user_prompt=user_prompt,
        intent=intent,
        evidence=evidence,
        brand_name=brand_name,
        brand_notes=brand_notes,
        fmt=fmt,
    )
    package.research_queries = queries
    package.live_research = live_research
    package.brand_thinking_notes = list(
        dict.fromkeys((package.brand_thinking_notes or []) + [brand_notes[:240]])
    )

    meta = {
        "latency_ms": int(getattr(package, "_latency_ms", 0) or 0),
        "input_tokens": int(getattr(package, "_input_tokens", 0) or 0),
        "output_tokens": int(getattr(package, "_output_tokens", 0) or 0),
        "approved_evidence": sum(1 for e in evidence if e.approved_for_creative),
        "total_evidence": len(evidence),
    }
    return package, meta


def content_intelligence_prompt_block(package: ContentIntelligenceOutput | None) -> str:
    """Serialize intelligence package for L7 / L7c prompts."""
    if not package:
        return ""
    beats = "\n".join(
        f"- [{b.role}] {b.message}"
        + (f" | STAT: {b.supporting_stat}" if b.supporting_stat else "")
        for b in (package.narrative_beats or [])
    )
    approved = [e for e in package.evidence if e.approved_for_creative]
    ev = "\n".join(
        f"- {e.claim}"
        + (f" → {e.value}" if e.value and e.value != e.claim else "")
        + f" [conf={e.confidence:.2f}]"
        for e in approved[:8]
    ) or "- (insufficient approved statistics — do not invent precise numbers)"
    fa = package.format_architecture
    return f"""
════════════════════════════════════════
CONTENT INTELLIGENCE PACKAGE (AUTHORITATIVE — LOCK THIS)
════════════════════════════════════════
CORE QUESTION: {package.intent.core_question}
INSIGHT THESIS (story must serve this): {package.insight_thesis}

NARRATIVE ARCHITECTURE:
{beats or '- (build hook→scale→why→effect→idea→takeaway)'}

APPROVED EVIDENCE ONLY (prefer these; never use unapproved slogans as 'data'):
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
If scores for answers_why/has_real_data are below 6, strengthen evidence and thesis before writing copy.
SPELLING: UDAN never ADAN. Complete sentences only.
"""
