#!/usr/bin/env python3
"""Generate client-facing Violyt / BrandLoveStudio.AI Architecture PDF."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

OUT = Path(__file__).resolve().parents[1] / "docs" / "client" / "Violyt_Architecture_Document.pdf"

NAVY = colors.HexColor("#003975")
ORANGE = colors.HexColor("#FFA400")
ICE = colors.HexColor("#E8F0F8")
DARK = colors.HexColor("#1A2332")
MUTED = colors.HexColor("#4A5568")
LINE = colors.HexColor("#CBD5E1")


def styles():
    base = getSampleStyleSheet()
    s = {
        "cover_title": ParagraphStyle(
            "cover_title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=34,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=14,
            leading=18,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "cover_meta": ParagraphStyle(
            "cover_meta",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=NAVY,
            spaceBefore=16,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12.5,
            leading=16,
            textColor=NAVY,
            spaceBefore=12,
            spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "h3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=DARK,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=DARK,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=12.5,
            textColor=DARK,
            leftIndent=4,
        ),
        "mono": ParagraphStyle(
            "mono",
            parent=base["Code"],
            fontName="Courier",
            fontSize=7.5,
            leading=10,
            textColor=DARK,
            backColor=ICE,
            leftIndent=4,
            rightIndent=4,
            spaceBefore=4,
            spaceAfter=8,
        ),
        "caption": ParagraphStyle(
            "caption",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=10,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceBefore=2,
            spaceAfter=10,
        ),
        "footer": ParagraphStyle(
            "footer",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
        "toc": ParagraphStyle(
            "toc",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=16,
            textColor=DARK,
            leftIndent=8,
        ),
        "th": ParagraphStyle(
            "th",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.white,
        ),
        "td": ParagraphStyle(
            "td",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=DARK,
        ),
    }
    return s


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, A4[1] - 12 * mm, A4[0] - 18 * mm, A4[1] - 12 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, A4[1] - 10 * mm, "Violyt / BrandLoveStudio.AI — Architecture Document")
    canvas.drawRightString(A4[0] - 18 * mm, A4[1] - 10 * mm, "Confidential")
    canvas.line(18 * mm, 12 * mm, A4[0] - 18 * mm, 12 * mm)
    canvas.drawCentredString(A4[0] / 2, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


def bullets(items, style):
    return ListFlowable(
        [ListItem(Paragraph(i, style), leftIndent=12, bulletColor=ORANGE) for i in items],
        bulletType="bullet",
        start="•",
        leftIndent=14,
        bulletFontSize=9,
        spaceBefore=2,
        spaceAfter=8,
    )


def table(headers, rows, col_widths):
    s = styles()
    data = [[Paragraph(h, s["th"]) for h in headers]]
    for row in rows:
        data.append([Paragraph(str(c), s["td"]) for c in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ICE]),
                ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def build():
    s = styles()
    story = []

    # —— Cover ——
    story.append(Spacer(1, 45 * mm))
    story.append(HRFlowable(width="100%", thickness=3, color=ORANGE, spaceAfter=10))
    story.append(Paragraph("Violyt / BrandLoveStudio.AI", s["cover_title"]))
    story.append(Paragraph("System Architecture Document", s["cover_sub"]))
    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="40%", thickness=1.5, color=NAVY, spaceBefore=4, spaceAfter=14))
    story.append(
        Paragraph(
            "Multi-tenant SaaS platform for brand-aware marketing creative generation<br/>"
            "with LangGraph AI pipeline, Brand Space grounding, and premium image output.",
            s["cover_meta"],
        )
    )
    story.append(Spacer(1, 28 * mm))
    story.append(Paragraph(f"Version 1.0 &nbsp;|&nbsp; {date.today().isoformat()}", s["cover_meta"]))
    story.append(Paragraph("Prepared for client review", s["cover_meta"]))
    story.append(Paragraph("Status: Current implementation (codebase-aligned)", s["cover_meta"]))
    story.append(PageBreak())

    # —— TOC ——
    story.append(Paragraph("1. Table of Contents", s["h1"]))
    toc = [
        "1. Table of Contents",
        "2. Executive Summary",
        "3. Product Purpose &amp; Scope",
        "4. High-Level System Architecture",
        "5. Technology Stack",
        "6. Deployment Topology (Docker)",
        "7. Creative Intelligence Pipeline (L1–L10)",
        "8. End-to-End Generation Flow",
        "9. Brand Space, Knowledge &amp; RAG",
        "10. API Surface Overview",
        "11. Security, Tenancy &amp; Roles",
        "12. External Integrations",
        "13. Storage &amp; Data Assets",
        "14. Frontend Workspace",
        "15. Non-Functional Considerations",
        "16. Glossary",
    ]
    for line in toc:
        story.append(Paragraph(line, s["toc"]))
    story.append(PageBreak())

    # —— Exec summary ——
    story.append(Paragraph("2. Executive Summary", s["h1"]))
    story.append(
        Paragraph(
            "Violyt (also referred to as BrandLoveStudio.AI) is a production-oriented, multi-tenant "
            "platform that turns brand knowledge and campaign briefs into finished social creatives. "
            "Tenants configure Brand Spaces (identity, voice, visuals, guardrails, knowledge). Users "
            "prompt the Studio workspace; a structured AI pipeline retrieves brand context, plans "
            "strategy and layout, drafts copy, prepares an approvable Creative Blueprint, then "
            "generates premium images with exact brand logo compositing.",
            s["body"],
        )
    )
    story.append(
        Paragraph(
            "The system is designed for fintech-grade brand fidelity (exemplified by Jiraaf creative DNA: "
            "ice-blue backgrounds, navy typography, orange accents, SEBI carousel footers where applicable) "
            "while remaining brand-configurable for other tenants.",
            s["body"],
        )
    )
    story.append(
        bullets(
            [
                "<b>Primary creative path:</b> LangGraph pipeline (L1→L7c approval → L8 image generation).",
                "<b>Secondary path:</b> ContentService / AI Orchestrator for broader content workflows.",
                "<b>Delivery:</b> FastAPI backend, Next.js frontend, PostgreSQL, Redis, Docker Compose.",
                "<b>Grounding:</b> Brand RAG (Pinecone namespaces), OCR on brand assets, live research for data creatives.",
            ],
            s["bullet"],
        )
    )

    # —— Purpose ——
    story.append(Paragraph("3. Product Purpose &amp; Scope", s["h1"]))
    story.append(Paragraph("3.1 In scope", s["h2"]))
    story.append(
        bullets(
            [
                "Multi-tenant auth, RBAC, usage limits, and tenant administration",
                "Brand Space lifecycle, section configuration, and asset upload",
                "Knowledge ingestion (OCR → chunk → embed → vector retrieve)",
                "Chat / Studio creative generation (static, carousel, infographic)",
                "Blueprint approval gate before image generation",
                "AI image generation with logo overlay and brand colour locks",
                "Jobs/workers, analytics scaffolding, review links, export helpers",
            ],
            s["bullet"],
        )
    )
    story.append(Paragraph("3.2 Out of scope / scaffolding", s["h2"]))
    story.append(
        bullets(
            [
                "Full live social network publishing (connect/publish scaffolding only)",
                "Complete L10 quality evaluation (currently a pass-through stub in default runs)",
                "Third-party Brand Space marketplaces",
            ],
            s["bullet"],
        )
    )

    # —— HLD ——
    story.append(Paragraph("4. High-Level System Architecture", s["h1"]))
    story.append(
        Paragraph(
            "Clients interact with a Next.js workspace. All business logic and AI orchestration "
            "run on the FastAPI backend. PostgreSQL is the system of record; object storage holds "
            "uploads and generated assets; a vector store grounds generation in brand documents.",
            s["body"],
        )
    )
    diagram = """
┌──────────────┐     HTTPS/REST      ┌─────────────────────┐
│  Next.js UI  │ ──────────────────► │  FastAPI (/api/v1)  │
│  (Studio)    │ ◄────────────────── │  Auth + RBAC        │
└──────────────┘                     └──────────┬──────────┘
                                                │
                ┌───────────────────────────────┼───────────────────────────────┐
                ▼                               ▼                               ▼
     ┌──────────────────┐           ┌──────────────────┐           ┌──────────────────┐
     │ Domain Services  │           │ LangGraph Pipe   │           │ Background       │
     │ Brand / Chat /   │           │ L1…L7c → L8      │           │ Worker + Redis   │
     │ Content / Jobs   │           │ Creative DNA     │           │ (Celery/poller)  │
     └────────┬─────────┘           └────────┬─────────┘           └────────┬─────────┘
              │                              │                              │
              ▼                              ▼                              ▼
     ┌──────────────────┐           ┌──────────────────┐           ┌──────────────────┐
     │ PostgreSQL 16    │           │ LLM + Image APIs │           │ Object Storage   │
     │ Tenants, Brands, │           │ OpenAI / Claude  │           │ /storage/...     │
     │ Content, Jobs    │           │ gpt-image / DALL·E│          │ + Pinecone RAG   │
     └──────────────────┘           └──────────────────┘           └──────────────────┘
"""
    story.append(Preformatted(diagram.strip("\n"), s["mono"]))
    story.append(Paragraph("Figure 1 — Logical system context", s["caption"]))

    story.append(Paragraph("4.1 Layered backend design", s["h2"]))
    story.append(
        table(
            ["Layer", "Responsibility", "Key locations"],
            [
                ["API", "Versioned REST, validation, HTTP errors", "main.py, app/api/"],
                ["Auth", "JWT, roles, tenant/brand scope", "app/core/, app/services/auth.py"],
                ["Services", "Business logic &amp; orchestration", "app/services/"],
                ["Graph", "Creative pipeline L1–L10", "app/graph/"],
                ["Prompts", "Layer prompts + brand DNA locks", "app/prompts/"],
                ["Repos", "SQLAlchemy models &amp; repositories", "app/models/, app/repositories/"],
                ["Integrations", "Storage, vectors, providers", "app/integrations/, app/ai/"],
                ["Workers", "Async ingestion &amp; jobs", "app/workers/, scripts/"],
            ],
            [28 * mm, 75 * mm, 65 * mm],
        )
    )
    story.append(Spacer(1, 4 * mm))

    # —— Stack ——
    story.append(Paragraph("5. Technology Stack", s["h1"]))
    story.append(
        table(
            ["Area", "Technology"],
            [
                ["Backend", "Python 3.12+, FastAPI, Uvicorn, SQLAlchemy async, Alembic, Pydantic"],
                ["Frontend", "Next.js 16, React 19, TypeScript, Tailwind, TanStack Query"],
                ["Database", "PostgreSQL 16"],
                ["Cache / broker", "Redis 7; Celery broker; Postgres job poller"],
                ["Orchestration", "LangGraph state machine"],
                ["LLMs", "OpenAI + Anthropic Claude (routed per pipeline layer)"],
                ["Image generation", "OpenAI gpt-image / DALL·E path; SDXL service stub"],
                ["RAG / embeddings", "OpenAI embeddings; Pinecone namespaces; FAISS abstraction"],
                ["OCR / Vision", "Google Cloud Vision + local OCR processors"],
                ["Rendering aids", "Pillow compositing (logo, SEBI footer on carousels)"],
                ["Email", "SMTP transactional mail"],
            ],
            [40 * mm, 128 * mm],
        )
    )

    story.append(PageBreak())

    # —— Docker ——
    story.append(Paragraph("6. Deployment Topology (Docker)", s["h1"]))
    story.append(
        Paragraph(
            "Local and self-hosted stacks are defined in <b>docker-compose.yml</b> "
            "(and server variant under <b>deploy/</b>).",
            s["body"],
        )
    )
    story.append(
        table(
            ["Service", "Role", "Host port"],
            [
                ["api", "FastAPI; migrations then Uvicorn; mounts storage", "8000"],
                ["worker", "Background jobs (scripts/run_worker.py)", "—"],
                ["violyt-frontend", "Next.js workspace UI", "3001 → 3000"],
                ["postgres", "Primary database", "5432"],
                ["redis", "Cache + Celery broker", "6379"],
            ],
            [40 * mm, 90 * mm, 38 * mm],
        )
    )
    story.append(Spacer(1, 3 * mm))
    story.append(
        Paragraph(
            "Note: Backend images are built locally as <b>violyt-backend:local</b> / "
            "<b>violyt-frontend:local</b> — they are not pulled from Docker Hub. "
            "API health is exposed at <b>GET /health</b>. Generated files are served under "
            "<b>/storage/…</b>.",
            s["body"],
        )
    )

    # —— Pipeline ——
    story.append(Paragraph("7. Creative Intelligence Pipeline (L1–L10)", s["h1"]))
    story.append(
        Paragraph(
            "The primary Studio path uses a two-phase LangGraph. Phase 1 produces an approvable "
            "Creative Blueprint. Phase 2 generates images only after explicit approval, reducing "
            "wasted image cost and improving brand control.",
            s["body"],
        )
    )
    pipe = """
PHASE 1 (default chat run)
  L1 Brand Retrieval  →  L2 Brand Intelligence  →  L3 Brief Interpreter  →  L4 Strategy
       L4 ──► L5 Concept Engine  ──┐
           └──► L6 Format Engine ──┴─► L7 Copy  →  L7b Validate  →  L7c Blueprint  →  AWAIT APPROVAL

PHASE 2 (after approve)
  L8 Visual Reasoning (image gen + logo)  →  Renderer (passthrough / finalize)  →  DONE

FULL / LEGACY (tests)
  … L8 → L9 Scene Graph → L10 Evaluation → (pass → renderer | repair → retry L5, max 2)
"""
    story.append(Preformatted(pipe.strip("\n"), s["mono"]))
    story.append(Paragraph("Figure 2 — Pipeline phases", s["caption"]))

    story.append(
        table(
            ["Layer", "Function"],
            [
                ["L1 Brand Retrieval", "Namespace-isolated RAG; brand document grounding; retrieval logs"],
                ["L2 Brand Intelligence", "Structured brand behaviour model; Redis-cached by brand version"],
                ["L3 Brief Interpreter", "Maps user prompt + platform/format into campaign brief"],
                ["L4 Strategic Reasoning", "Angles, narrative strategy from brand + brief"],
                ["L5 Concept Engine", "Multiple creative concepts with diversity controls"],
                ["L6 Format Engine", "Layout/slide plan for static, carousel, infographic (parallel with L5)"],
                ["L7 Copy Engine", "Final copy; optional live research; layout classification"],
                ["L7b Content Validator", "Spell/length/fact flags; image-safe string limits"],
                ["L7c Content Prep", "Creative Blueprint for human approval + quality finalize"],
                ["L8 Visual Reasoning", "Image prompts + gpt-image/DALL·E; brand colour/fit locks; logo"],
                ["L9 Scene Graph", "Structured scene zones (full graph)"],
                ["L10 Evaluation", "Quality gate (stub pass in default path)"],
                ["Repair / Renderer", "Retry loop to L5; Phase 2 image URL finalize"],
            ],
            [45 * mm, 123 * mm],
        )
    )
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("7.1 LLM routing (typical)", s["h2"]))
    story.append(
        bullets(
            [
                "<b>Anthropic Claude:</b> L2, L4, L5 (brand intelligence, strategy, concepts).",
                "<b>OpenAI:</b> L3, L6, L7, L7c, L8, L9 (brief, format, copy, blueprint, visuals).",
                "<b>Image:</b> OpenAI image models via DalleService with Pillow logo/SEBI composites.",
            ],
            s["bullet"],
        )
    )
    story.append(Paragraph("7.2 Brand creative DNA", s["h2"]))
    story.append(
        Paragraph(
            "Prompt locks in <b>app/prompts/brand_copy_tone.py</b> and layout routers in "
            "<b>jiraaf_layout.py</b> enforce sample-aligned layouts: ice-blue backgrounds, navy "
            "headlines, orange accents (≥~2% coverage), universal fit margins, topic-specific 3D "
            "icons, and carousel-only SEBI footers when required.",
            s["body"],
        )
    )

    story.append(PageBreak())

    # —— Flow ——
    story.append(Paragraph("8. End-to-End Generation Flow", s["h1"]))
    story.append(
        bullets(
            [
                "User enters a prompt in Studio (platform + format selected).",
                "<b>POST /api/v1/pipeline/run</b> — intent/layout may override format for data boards.",
                "Phase 1 graph runs L1→L7c; checkpoint saved; status <b>awaiting_blueprint_approval</b>.",
                "User reviews/edits blueprint → <b>POST /api/v1/pipeline/approve</b> (or reject).",
                "Phase 2 L8 generates image(s); logo composited; assets stored under tenant/brand paths.",
                "Frontend displays asset URLs; optional text edit endpoint for post-fixes.",
            ],
            s["bullet"],
        )
    )
    story.append(
        Paragraph(
            "Alternate path: <b>POST /api/v1/content/generate</b> uses ContentService + AIOrchestrator "
            "for planning, RAG, render, and history — still available for broader content workflows.",
            s["body"],
        )
    )

    # —— Brand / RAG ——
    story.append(Paragraph("9. Brand Space, Knowledge &amp; RAG", s["h1"]))
    story.append(
        Paragraph(
            "Brand Spaces are first-class tenant resources with lifecycle "
            "<b>draft → active → archived/deleted</b>. Ten section domains cover identity, foundations, "
            "voice, personas, guardrails, knowledge, prompt intelligence, objectives, visual identity, "
            "and review.",
            s["body"],
        )
    )
    story.append(
        bullets(
            [
                "Uploads → OCR/vision analysis → chunking → embeddings → Pinecone namespace <b>brand:{id}</b>.",
                "L1 retrieval is tenant/brand isolated and logged for auditability.",
                "Resolved brand context + snapshots feed downstream layers after validation.",
                "Logos and visual assets are stored for deterministic overlay on generated creatives.",
            ],
            s["bullet"],
        )
    )

    # —— API ——
    story.append(Paragraph("10. API Surface Overview", s["h1"]))
    story.append(Paragraph("Base path: <b>/api/v1</b>. Interactive docs: <b>/docs</b>.", s["body"]))
    story.append(
        table(
            ["Group", "Purpose"],
            [
                ["/auth", "Login, refresh, profile, 2FA, password reset"],
                ["/tenants", "Tenant admin, users, usage limits"],
                ["/brands", "Brand Space lifecycle, sections, retrieval"],
                ["/knowledge", "Knowledge upload / reprocess"],
                ["/chat", "Sessions and messages"],
                ["/pipeline", "LangGraph run / approve / reject / edit"],
                ["/content", "Generate, rewrite, history, export"],
                ["/templates", "Upload, recommend, apply"],
                ["/render", "Layout preview / export helpers"],
                ["/review", "External share &amp; comment links"],
                ["/analytics", "Platform / tenant / brand usage"],
                ["/jobs", "Background job status"],
                ["/social", "Connector scaffolding"],
            ],
            [40 * mm, 128 * mm],
        )
    )

    # —— Security ——
    story.append(Paragraph("11. Security, Tenancy &amp; Roles", s["h1"]))
    story.append(
        bullets(
            [
                "JWT bearer authentication; refresh tokens; optional 2FA.",
                "Roles: super_admin, tenant_admin, tenant_user, brand_user, external_reviewer.",
                "Data isolation by <b>tenant_id</b> and <b>brand_space_id</b>.",
                "Super Admin blocked from Brand Space content generation flows.",
                "Usage limits gate expensive AI actions.",
                "Social tokens encrypted at rest; secrets via environment configuration.",
            ],
            s["bullet"],
        )
    )

    story.append(PageBreak())

    # —— Integrations ——
    story.append(Paragraph("12. External Integrations", s["h1"]))
    story.append(
        table(
            ["Integration", "Use"],
            [
                ["OpenAI", "Text layers, embeddings, research, image generation"],
                ["Anthropic Claude", "Brand intelligence, strategy, concepts"],
                ["Pinecone", "Brand document vector index (namespaced)"],
                ["Google Cloud Vision", "OCR / document vision"],
                ["SMTP", "Transactional email"],
                ["Redis", "L2 brand cache + Celery broker"],
                ["Brave Search (optional)", "Alternate live research provider"],
            ],
            [45 * mm, 123 * mm],
        )
    )

    # —— Storage ——
    story.append(Paragraph("13. Storage &amp; Data Assets", s["h1"]))
    story.append(
        bullets(
            [
                "Object storage (local default): <b>{tenant}/{brand}/{category}/…</b> under OBJECT_STORAGE_BASE_PATH.",
                "Categories include uploads, generated images, logos, templates, pipeline checkpoints, traces.",
                "PostgreSQL stores tenants, brands, chat, content history, jobs, analytics events.",
                "Pipeline checkpoints enable resume after blueprint approval.",
            ],
            s["bullet"],
        )
    )

    # —— Frontend ——
    story.append(Paragraph("14. Frontend Workspace", s["h1"]))
    story.append(
        Paragraph(
            "The Next.js app under <b>frontend/</b> provides the Studio chat workspace, Brand Space "
            "administration surfaces, and pipeline approval UX. It talks to the backend via typed "
            "contracts (<b>contracts/frontend-api.ts</b>) and hooks such as <b>usePipeline</b>. "
            "Live API mode and mock UI mode are both supported for design review.",
            s["body"],
        )
    )

    # —— NFR ——
    story.append(Paragraph("15. Non-Functional Considerations", s["h1"]))
    story.append(
        bullets(
            [
                "<b>Cost control:</b> Blueprint approval before image generation; layer-specific model routing.",
                "<b>Brand safety:</b> Guardrails sections, copy validators, spelling/fit locks, logo overlay.",
                "<b>Observability:</b> Structured logs, retrieval logs, generation traces.",
                "<b>Scalability:</b> Stateless API containers; worker separation; Redis/Celery ready.",
                "<b>Portability:</b> Docker Compose for local; server compose for host deployments.",
                "<b>Extensibility:</b> Prompt builders and layout routers allow brand DNA upgrades without UI rewrites.",
            ],
            s["bullet"],
        )
    )

    # —— Glossary ——
    story.append(Paragraph("16. Glossary", s["h1"]))
    story.append(
        table(
            ["Term", "Meaning"],
            [
                ["Brand Space", "Tenant-scoped brand configuration + knowledge container"],
                ["Creative Blueprint", "L7c structured plan approved before image spend"],
                ["LangGraph", "Stateful multi-step AI orchestration framework"],
                ["RAG", "Retrieval-Augmented Generation from brand documents"],
                ["SEBI footer", "Regulatory disclaimer composited on Jiraaf carousels only"],
                ["Layout DNA", "Prompt locks that force sample-aligned visual structure"],
            ],
            [40 * mm, 128 * mm],
        )
    )

    story.append(Spacer(1, 10 * mm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ORANGE, spaceAfter=8))
    story.append(
        Paragraph(
            "This document reflects the implemented architecture of the Violyt / BrandLoveStudio.AI "
            "codebase. For operational runbooks, see internal docs: ARCHITECTURE.md, "
            "CREATIVE_GENERATION_ARCHITECTURE.md, DOCKER_SETUP.md, and API_CONTRACTS.md.",
            s["body"],
        )
    )
    story.append(Paragraph("— End of document —", s["caption"]))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Violyt / BrandLoveStudio.AI — Architecture Document",
        author="Violyt Engineering",
    )
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
