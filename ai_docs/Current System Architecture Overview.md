# Current System Architecture Overview

## Purpose of This Document

This document explains the current architecture of the Violyt / BrandLoveStudio.AI system as it exists in the codebase today. It is written for a development team that needs to continue the project without depending on extra briefing from the original implementation work.

The system is a multi-tenant SaaS application for brand-aware content creation. The backend owns tenant management, authentication, Brand Space configuration, knowledge ingestion, AI orchestration, deterministic rendering, generated asset storage, review links, analytics, usage limits, and background jobs. The frontend consumes the backend through versioned FastAPI endpoints.

This document covers the complete system shape. The deeper AI pipeline internals, individual AI modules, and orchestration decisions are covered separately in the documents dedicated to those topics.

## High-Level System View

At runtime, the application is made of four main pieces:

| Component | Runtime | Main Responsibility |
| --- | --- | --- |
| Frontend | Next.js app, exposed through the Docker stack as `violyt-frontend` | User workspace for tenants, Brand Spaces, content generation, chat, uploads, previews, and review workflows. |
| Backend API | FastAPI app served by Uvicorn from `main.py` | HTTP API surface, authentication, service orchestration, persistence, rendering requests, and storage access. |
| Worker | Python process running `scripts/run_worker.py` | Processes queued jobs such as knowledge asset processing, template analysis, and optional RAGAS evaluation. |
| PostgreSQL | Postgres 16 in Docker | Primary relational database for tenants, users, Brand Spaces, content history, assets, jobs, usage, and metadata. |

The backend also uses filesystem-backed storage by default:

| Storage Area | Default Location | Used For |
| --- | --- | --- |
| Object storage | `storage/` locally, `/app/storage` in Docker | Uploaded files, generated images, previews, exports, traces, template cache files, and RAGAS outputs. |
| Vector store | `vector_store/` locally, `/app/vector_store` in Docker | FAISS indexes and metadata for knowledge retrieval. |
| Generation traces | `storage/generation_traces/` | Debug payloads and trace artifacts from content generation and rendering. |

The object storage layer has an S3 adapter, but the Docker development stack is configured for local mounted storage.

```mermaid
flowchart LR
    User["User / Tenant Admin / Brand User"] --> Frontend["Next.js Frontend"]
    Frontend --> API["FastAPI Backend API\nmain.py + app/api/router.py"]

    API --> Services["Service Layer\napp/services"]
    Services --> Repos["Repository Layer\napp/repositories"]
    Repos --> DB[("PostgreSQL\nSQLAlchemy Models")]

    Services --> AI["AI Layer\napp/ai"]
    Services --> Renderer["RendererService\nPillow / DOCX / PDF"]
    Services --> Storage["Object Storage\nLocal or S3 Adapter"]
    Services --> Vector["FAISS Vector Store\nKnowledge Retrieval"]

    API --> PublicStorage["/storage Static Mount\nwhen enabled"]

    Worker["Worker Process\nscripts/run_worker.py"] --> JobService["JobService"]
    JobService --> DB
    Worker --> Services
    Worker --> Storage
    Worker --> Vector
```

## Deployment and Runtime Topology

The local Docker stack is defined in `docker-compose.yml`.

| Docker Service | Image / Command | Notes |
| --- | --- | --- |
| `api` | Builds from the backend `Dockerfile`, then runs `alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000` | Applies migrations before serving the API. Exposes port `8000`. Mounts `storage/` and `vector_store/`. |
| `worker` | Uses the same backend image and runs `python scripts/run_worker.py` | Shares code, environment, object storage, and vector store with the API. Depends on healthy API and Postgres. |
| `violyt-frontend` | Builds from the frontend Dockerfile | Runs the Next.js frontend. Exposes host port `3001` to container port `3000` in the current compose file. |
| `postgres` | `postgres:16` | Stores all relational application data. Exposes port `5432`. |

The API and worker both receive the same important environment overrides in Docker:

| Setting | Docker Value |
| --- | --- |
| `DATABASE_URL` | `postgresql+asyncpg://violyt:violyt@postgres:5432/violyt` |
| `ALEMBIC_DATABASE_URL` | `postgresql+psycopg://violyt:violyt@postgres:5432/violyt` |
| `OBJECT_STORAGE_BASE_PATH` | `/app/storage` |
| `VECTOR_STORE_BASE_PATH` | `/app/vector_store` |
| `GENERATION_TRACE_BASE_PATH` | `/app/storage/generation_traces` |
| `GENERATED_ASSETS_BASE_URL` | `http://localhost:8000/storage` |

The backend image is shared between the API and worker. That is an important operational detail because the worker imports the same services and repositories as the API instead of using a separate job framework or duplicated business logic.

## Application Startup

The FastAPI application is created in `main.py`.

Startup does the following:

1. Loads settings through `app.core.config.get_settings()`.
2. Creates the FastAPI app with the configured app name, debug mode, and lifespan handler.
3. During lifespan startup, opens an async database session and seeds RBAC plus the demo owner through `seed_rbac()` and `seed_demo_owner()`.
4. Adds CORS middleware using `settings.cors_origins`.
5. Includes the API router under `settings.api_v1_prefix`, which defaults to `/api/v1`.
6. Ensures the object storage directory exists.
7. Optionally mounts `/storage` as a static file route when `settings.expose_public_storage` is enabled.
8. Registers domain exception handlers for not-found, duplicate resource, generation failure, authorization, lifecycle, upload validation, guardrail, and usage-limit errors.

```mermaid
sequenceDiagram
    participant Runtime as Uvicorn
    participant App as FastAPI main.py
    participant DB as AsyncSessionLocal
    participant Bootstrap as Bootstrap Services
    participant Router as app.api.router
    participant Storage as Object Storage Directory

    Runtime->>App: import main:app
    App->>App: load Settings
    App->>App: configure CORS
    App->>Router: include /api/v1 router
    App->>Storage: create storage base path
    Runtime->>App: lifespan startup
    App->>DB: open async session
    DB->>Bootstrap: seed_rbac()
    DB->>Bootstrap: seed_demo_owner()
    App-->>Runtime: ready
```

## Backend Layering Pattern

The backend follows a consistent layered structure:

```mermaid
flowchart TD
    Routes["API Routes\napp/api/routes"] --> Schemas["Pydantic Schemas\napp/schemas"]
    Routes --> Dependencies["Auth / Scope Dependencies\napp/core/dependencies.py"]
    Routes --> Services["Service Layer\napp/services"]
    Services --> Repositories["Repository Layer\napp/repositories"]
    Repositories --> Models["SQLAlchemy Models\napp/models"]
    Models --> DB[("PostgreSQL")]

    Services --> AI["AI Modules\napp/ai"]
    Services --> Integrations["Storage / Vector Integrations\napp/integrations"]
    Services --> Utils["Shared Utilities\napp/utils"]
```

The important boundaries are:

| Layer | Folder | Responsibility |
| --- | --- | --- |
| API routes | `app/api/routes` | Define HTTP endpoints, apply FastAPI dependencies, validate request bodies, call services, and return response schemas. |
| Schemas | `app/schemas` | Pydantic contracts for requests and responses. These are the API-facing shapes used by the frontend. |
| Core | `app/core` | Settings, JWT security, role and brand-scope dependencies, shared enums, and domain exceptions. |
| Services | `app/services` | Business workflows. Services coordinate repositories, AI modules, storage, vector retrieval, rendering, usage enforcement, and background jobs. |
| Repositories | `app/repositories` | Thin SQLAlchemy query layer. Repositories keep persistence details out of service code. |
| Models | `app/models` | SQLAlchemy ORM models and table definitions. |
| Integrations | `app/integrations` | Storage and vector-store adapters. |
| AI | `app/ai` | Prompting, orchestration, providers, layout decisions, RAG, image generation, context compilation, guardrails, and generated output contracts. |
| Workers | `app/workers` and `scripts/run_worker.py` | Background job polling and dispatch. |
| Utilities | `app/utils` | Shared helpers for file handling, text normalization, palette role derivation, image opening, footer layout, and input access tracking. |

The route layer is intentionally thin. Most behavior sits in services because the same workflows need to be reusable from HTTP requests, background jobs, and scripts.

## API Surface

All route modules are registered by `app/api/router.py` under `/api/v1`.

| Prefix | Route Module | Main Capability |
| --- | --- | --- |
| `/auth` | `app.api.routes.auth` | Login, activation, password reset, refresh, profile, and two-factor flows. |
| `/tenants` | `app.api.routes.tenant` | Tenant creation, tenant metadata, logo upload, users, usage limits, and tenant-level summaries. |
| `/brands` | `app.api.routes.brand` | Brand Space lifecycle, sections, publishing, validation summaries, and resolved brand context. |
| `/brands` | `app.api.routes.brand_assets` | Brand attachment upload, listing, reprocessing, unsync, delete, and serialization. |
| `/knowledge` | `app.api.routes.knowledge` | General knowledge upload, listing, status, deletion, and reprocessing. |
| `/content` | `app.api.routes.content` | Content generation, rewrite, tone check, history, detail, export, copy, archive, and delete. |
| `/chat` | `app.api.routes.chat` | Chat sessions, message sending, history, cancellation, and generated content linkage. |
| `/folders` | `app.api.routes.folder` | Content folder creation, listing, rename, delete, and moving content. |
| `/templates` | `app.api.routes.template` | Template upload, analysis, metadata, apply, recommendations, and deletion. |
| `/render` | `app.api.routes.render` | Layout rendering, preview rendering, export rendering, and render status. |
| `/review` | `app.api.routes.review` | Share links, public review payloads, comments, and review status updates. |
| `/social` | `app.api.routes.social` | Social connection records, publish requests, and disconnect flows. |
| `/analytics` | `app.api.routes.analytics` | Platform, tenant, brand, and usage analytics. |
| `/jobs` | `app.api.routes.jobs` | Job listing and status lookups. |
| `/storage` | `app.api.routes.storage` | Asset download endpoint. |

The API is also self-documented at `/docs` through FastAPI/OpenAPI when the backend is running.

## Authentication, Authorization, and Scope

Authentication is JWT-based and implemented in `app/core/security.py` and `app/services/auth.py`.

The main security pieces are:

| Piece | Implementation |
| --- | --- |
| Password hashing | `passlib` with bcrypt, with password bytes truncated to bcrypt's 72-byte limit. |
| JWT creation and decoding | `create_access_token()`, `create_refresh_token()`, and `decode_token()` in `app/core/security.py`. |
| Current principal | `CurrentPrincipal` and `get_current_principal()` in `app/core/dependencies.py`. |
| Role checks | `require_roles()` and helper methods on `CurrentPrincipal`. |
| Brand scope checks | `get_brand_scope_header()`, `require_brand_scope()`, `assert_brand_access()`, and `assert_tenant_access()`. |
| Social token encryption | `app/core/crypto.py`, using a configured social encryption key or a derived key from the app secret. |

The system is multi-tenant and brand-scoped. Most routes use the authenticated principal plus a brand scope header before they allow access to Brand Space data. Super-admin, tenant-admin, and brand-user roles are represented through role codes and user-role records.

```mermaid
sequenceDiagram
    participant Client as Frontend
    participant Route as FastAPI Route
    participant Auth as Core Dependencies
    participant Service as Service Layer
    participant Repo as Repository
    participant DB as PostgreSQL

    Client->>Route: Request with JWT and brand scope
    Route->>Auth: get_current_principal()
    Auth->>DB: load user, tenant, roles
    Route->>Auth: require_brand_scope()
    Route->>Auth: assert_brand_access()
    Route->>Service: call workflow with tenant_id, brand_space_id, user_id
    Service->>Repo: scoped queries
    Repo->>DB: tenant/brand-filtered persistence access
    DB-->>Service: ORM records
    Service-->>Route: domain result
    Route-->>Client: response schema
```

## Domain Model Overview

The model layer is grouped by domain.

### Tenant and Identity Model

Implemented in `app/models/tenant.py`.

| Table | Purpose |
| --- | --- |
| `tenants` | Tenant account metadata, contact information, logo path, active state, and JSON metadata. |
| `users` | Users under a tenant or platform-level users. Stores profile fields, hashed password, activation state, and metadata. |
| `roles` | Role definitions such as platform, tenant, or brand roles. |
| `permissions` | Permission records used for RBAC. |
| `role_permissions` | Many-to-many relationship between roles and permissions. |
| `user_roles` | Assigns roles to users, optionally scoped to a Brand Space. |
| `activation_tokens` | User activation token records. |

### Brand Space Model

Implemented in `app/models/brand.py`.

| Table | Purpose |
| --- | --- |
| `brand_spaces` | Primary brand workspace. Stores lifecycle state, default persona, overview snapshot, and resolved brand context. |
| `brand_configuration_sections` | Versioned Brand Space sections such as identity, foundations, voice, personas, guardrails, knowledge, objectives, visual identity, prompt intelligence, and review. |
| `personas` | Audience/persona records connected to a Brand Space. |
| `guardrails` | Tone, language, restricted topics, blocked words, and custom generation rules. |
| `objectives` | Brand/business objectives used during generation. |
| `brand_space_members` | Brand-level membership and management access. |

### Knowledge, Template, and Content Model

Implemented mainly in `app/models/knowledge.py` and `app/models/content.py`.

| Table | Purpose |
| --- | --- |
| `knowledge_assets` | Uploaded files and processed knowledge/brand assets. Stores channel, field key, classification, extracted text, normalized data, validation state, and storage path. |
| `templates` | Uploaded or derived templates with analysis and matcher features. |
| `template_metadata` | Zone maps, sizing rules, platform rules, editable fields, and export rules for templates. |
| `sessions` | Chat or content sessions with studio panel and conversational context. |
| `chat_messages` | User and assistant messages, linked content versions, structured payloads, and citations. |
| `content_folders` | Brand-scoped content organization. |
| `content_history` | Generated content versions, prompts, studio panel, generated payload, blueprint payload, explainability metadata, token counts, and tone feedback. |
| `generated_assets` | Generated or rendered files associated with content, templates, and storage paths. |

### Brand Asset Intelligence Model

Implemented in `app/models/brand_assets.py`.

This group contains the structured outputs created from brand attachment processing:

| Table Group | Tables |
| --- | --- |
| Logos | `brand_logo_assets`, `brand_logo_metadata` |
| Audience insight | `audience_insight_assets`, `audience_insight_structured_data` |
| Visual references and mood boards | `visual_reference_assets`, `mood_board_assets`, `reusable_brand_assets` |
| Brand style system | `color_palette_entries`, `typography_guides` |
| Word banks and guardrail support | `word_bank_uploads`, `positive_words`, `negative_words`, `replaceable_words` |
| Processing and validation | `asset_processing_status`, `asset_validation_results`, `asset_category_routing`, `data_conflicts`, `resolved_brand_context_snapshots` |
| Legal and CTA support | `brand_legal_assets`, `brand_cta_templates` |

The resolved Brand Space context is built from a combination of manually entered section data and processed brand assets. `DataValidatorService.refresh_brand_context()` is the service that consolidates these inputs and stores a clean context back onto the Brand Space.

### Collaboration, Jobs, Usage, and Analytics

Implemented in `app/models/collaboration.py`.

| Table | Purpose |
| --- | --- |
| `review_links` | Shareable review links for generated content. |
| `review_comments` | Internal or external review comments. |
| `social_connections` | Brand-scoped social connection metadata and encrypted tokens. |
| `analytics` | Analytics snapshot records. |
| `usage_limits` | Tenant-level limits for users, Brand Spaces, content generations, image generations, and OCR pages. |
| `usage_consumption` | Period-based usage consumption records. |
| `jobs` | Background job queue records with lease ownership, retry count, heartbeat, result payload, and status. |

## Main Service Map

The service layer is the real application core. Routes call services, services call repositories and integrations, and workers reuse the same services.

| Service | Role in the System |
| --- | --- |
| `AuthService` | Login, activation, password reset, token refresh, profile updates, password changes, and two-factor flows. |
| `TenantService` | Tenant CRUD, tenant users, tenant logo uploads, usage configuration, and tenant summaries. |
| `BrandSpaceService` | Brand Space creation, section upserts, publishing/unpublishing, archiving, restore, usage summary, and active-state enforcement. |
| `BrandAssetService` | Brand attachment upload, processing, classification, structured asset creation, cleanup, reprocessing, and resolved-context refresh. |
| `KnowledgeService` | General knowledge upload, OCR/text extraction, vector indexing, deletion, and reprocessing. |
| `ContentService` | Main content generation, rewrite, tone check, history, detail, export, copy, session memory, trace writing, AI orchestration, and render handoff. |
| `ChatService` | Chat session and message workflows, including generated content linkage and cancellation handling. |
| `RendererService` | Deterministic image/document/PDF rendering from renderer payloads, scene graphs, templates, and generated assets. |
| `TemplateService` | Template upload, analysis, metadata extraction, recommendations, application, and template detail. |
| `DataValidatorService` | Rebuilds resolved Brand Space context from sections and processed assets; records validation results and conflicts. |
| `JobService` | Creates, claims, heartbeats, completes, retries, and fails background jobs. |
| `UsageLimitService` | Enforces and records tenant usage consumption. |
| `ReviewService` | Review link and comment workflows. |
| `SocialService` | Social connection and publishing records. |
| `AnalyticsService` | Analytics lookup and summary flows. |
| `GenerationTraceService` | Writes generation and rendering debug artifacts under the trace storage path. |

## Storage Architecture

The system separates relational records from binary or generated files.

### Object Storage

Implemented in `app/integrations/object_storage.py`.

The storage contract is:

| Method | Purpose |
| --- | --- |
| `build_relative_path()` | Creates tenant/brand/category-based storage paths. |
| `save_bytes()` | Stores uploaded or generated bytes and returns a `StoredObject`. |
| `read_bytes()` | Reads stored file content. |
| `exists()` | Checks whether a stored object exists. |
| `delete()` | Deletes a stored object. |
| `absolute_path()` | Resolves a local path for downstream libraries that need file access. |

There are two storage implementations:

| Adapter | Behavior |
| --- | --- |
| `LocalObjectStorage` | Stores files under `settings.object_storage_base_path`. Used by the current Docker stack. |
| `S3ObjectStorage` | Stores objects in S3 and maintains a local cache for file-based processing. Requires `AWS_S3_BUCKET` when selected. |

Uploaded and generated files store their storage path in PostgreSQL. The bytes themselves live in object storage.

### Vector Store

Implemented in `app/integrations/vector_store.py`.

The vector store uses FAISS through LangChain. If an OpenAI API key is configured, it uses `OpenAIEmbeddings` with the configured embedding model. If no OpenAI key is available, it falls back to deterministic hash embeddings. That fallback is useful for local development and smoke testing, but it is not semantically equivalent to production embeddings.

Vector namespaces follow this pattern:

```text
{tenant_id}/{brand_space_id}/{channel}
```

Each namespace stores:

| File Type | Purpose |
| --- | --- |
| `index.faiss` | FAISS vector index. |
| `documents.json` | Stored chunk metadata and content mirror. |

Knowledge ingestion deletes old chunks for an asset before re-indexing it, so reprocessing an asset keeps the namespace from accumulating stale chunks for that source.

## Background Job Architecture

There is no separate queue broker in the current implementation. The database `jobs` table acts as the queue. The worker process polls for queued or claimable jobs, leases them, processes them, and updates their status.

```mermaid
sequenceDiagram
    participant API as API Service
    participant Jobs as JobService
    participant DB as jobs table
    participant Worker as Worker Loop
    participant Domain as Knowledge/Template/RAGAS Service

    API->>Jobs: create(job_type, payload)
    Jobs->>DB: insert queued job
    Worker->>Jobs: claim_pending(worker_id)
    Jobs->>DB: lease jobs and mark processing
    Worker->>Domain: dispatch by job_type
    Worker->>Jobs: heartbeat during processing
    Domain-->>Worker: result or exception
    Worker->>Jobs: set_status(succeeded) or fail_or_retry()
    Jobs->>DB: persist result, retry, or failure
```

The worker entrypoint is `scripts/run_worker.py`, which calls `app.workers.runner.run_worker_loop()`.

Current worker dispatch supports:

| Job Type | Worker Action |
| --- | --- |
| `KNOWLEDGE_PROCESS` | Calls `KnowledgeService.process_asset()`. If the asset has a `field_key`, that service delegates to `BrandAssetService.process_asset()`. |
| `TEMPLATE_ANALYSIS` | Calls `TemplateService.analyze()`. |
| `RAGAS_EVALUATION` | Runs `scripts.ragas_evaluation.evaluate_traces()` in a thread and stores evaluation output paths in the job result. |
| Other job type | Marks the job as succeeded with a no-op result. |

Retries are handled by `JobService.fail_or_retry()`. A failed job is requeued until `retry_count` reaches `max_retries`; after that, it is marked failed.

## Knowledge and Brand Asset Processing Flow

Knowledge and Brand Asset processing are closely related but not identical.

### General Knowledge Upload

General knowledge upload flows through `KnowledgeService.upload()`.

```mermaid
flowchart TD
    Client["Frontend uploads knowledge file"] --> Route["/api/v1/knowledge upload route"]
    Route --> Service["KnowledgeService.upload()"]
    Service --> Preflight["UploadPreflightService\nsize/type/page checks"]
    Service --> Storage["LocalObjectStorage.save_bytes()"]
    Service --> DBAsset["knowledge_assets row"]
    Service --> Job["JobService.create(KNOWLEDGE_PROCESS)"]
    Job --> JobsTable[("jobs")]
    Worker["Worker"] --> Process["KnowledgeService.process_asset()"]
    Process --> OCR["OCRService.extract()"]
    Process --> Vector["KnowledgeRetrievalService.index_asset()"]
    Process --> DBUpdate["Update lifecycle, extracted text, summary, last_indexed_at"]
```

The general knowledge processing path extracts text, indexes it into FAISS, stores a summary/extracted text on the asset row, enforces OCR usage, and updates lifecycle state.

### Brand Attachment Upload

Brand-specific files are uploaded through `BrandAssetService.upload()`. They are still stored as `knowledge_assets`, but they carry a `field_key`, category, channel, validation state, and processing status.

```mermaid
flowchart TD
    Client["Frontend uploads Brand Space attachment"] --> Route["/api/v1/brands attachment route"]
    Route --> Service["BrandAssetService.upload()"]
    Service --> Preflight["UploadPreflightService"]
    Service --> Storage["Object Storage"]
    Service --> AssetRow["knowledge_assets\nfield_key + asset_category"]
    Service --> Status["asset_processing_status"]
    Service --> Job["KNOWLEDGE_PROCESS job"]
    Worker --> Process["BrandAssetService.process_asset()"]
    Process --> Analyzer["BrandAssetAnalyzer"]
    Analyzer --> StructuredTables["logo / palette / typography /\naudience / references / word banks / legal / CTA tables"]
    Process --> Validator["DataValidatorService.refresh_brand_context()"]
    Validator --> Brand["brand_spaces.resolved_brand_context"]
```

This path is important because the generated content pipeline depends heavily on `brand_spaces.resolved_brand_context`. The validator combines manual Brand Space sections and processed asset intelligence into one context object that the AI pipeline can consume.

## Content Generation Architecture

The main generation entrypoint is `POST /api/v1/content/generate`, handled by `app/api/routes/content.py` and `ContentService.generate()`.

At a high level, generation does this:

1. The route validates the request with `ContentGenerateRequest`.
2. The route enforces brand scope and tenant/brand access.
3. `ContentService.generate()` verifies the Brand Space is active.
4. The resolved brand context is refreshed.
5. A content/chat session is created or loaded.
6. Session memory and request lineage are applied.
7. Prompt text is sanitized and normalized.
8. Runtime brand context, persona context, objective context, logo candidates, and reference assets are prepared.
9. Template recommendations and reference assets are resolved and filtered for the requested format.
10. Planning hints and generation decisions are built.
11. Knowledge retrieval and live research may contribute context.
12. The AI orchestrator receives an `AIOrchestrationRequest`.
13. The orchestrator returns message strategy, structured text, creative decision, scene graph, validation report, blueprint, generated image assets, and final-render assets where applicable.
14. The service persists a `content_history` row and `generated_assets` rows.
15. The route attaches generated assets and returns `ContentVersionResponse`.

```mermaid
sequenceDiagram
    participant Client as Frontend
    participant Route as Content Route
    participant Content as ContentService
    participant Brand as DataValidatorService
    participant Template as TemplateService
    participant RAG as Knowledge Retrieval
    participant AI as AIOrchestratorService
    participant Render as RendererService
    participant DB as PostgreSQL
    participant Storage as Object Storage

    Client->>Route: POST /api/v1/content/generate
    Route->>Route: validate request and brand access
    Route->>Content: generate(tenant_id, brand_space_id, user_id, payload)
    Content->>Brand: refresh_brand_context()
    Brand->>DB: read sections/assets, write resolved context
    Content->>Template: recommend()
    Content->>RAG: retrieve relevant knowledge
    Content->>AI: generate(AIOrchestrationRequest)
    AI-->>Content: orchestration response
    Content->>Render: render when backend render/export is needed
    Render->>Storage: save previews/exports
    Content->>DB: persist content_history and generated_assets
    Route-->>Client: ContentVersionResponse
```

The orchestration response is stored in two main places:

| Persisted Field | Contents |
| --- | --- |
| `content_history.generated_payload` | Final generated content structure. |
| `content_history.blueprint_payload` | Layout/blueprint information used by renderer and frontend. |
| `content_history.explainability_metadata` | Layout decisions, creative decisions, scene graph, validation reports, token usage, traces, and related debugging metadata. |
| `generated_assets` rows | Rendered or generated image/export records with storage paths and metadata. |

## Rendering and Export Flow

Rendering is handled by `RendererService`.

Renderer inputs are built from stored content, blueprint data, scene graph data, image assets, template metadata, and studio panel settings. The renderer uses Pillow for image composition, `python-docx` for DOCX output, and ReportLab/Pillow paths for PDF/image export behavior.

```mermaid
flowchart TD
    Content["ContentVersion\npayload + blueprint + explainability"] --> RenderInput["RendererInput"]
    Assets["GeneratedAsset rows\nand storage paths"] --> RenderInput
    TemplateMeta["TemplateMetadata\nzone map + sizing rules"] --> RenderInput
    RenderInput --> Renderer["RendererService.render()"]
    Renderer --> Image["Image preview/export"]
    Renderer --> Docx["DOCX export"]
    Renderer --> Pdf["PDF export"]
    Image --> Storage["Object Storage"]
    Docx --> Storage
    Pdf --> Storage
    Storage --> API["Download/static URL"]
```

The renderer is deterministic relative to its input payloads. The AI layer may generate scene graph and creative decisions, but the backend renderer owns actual file output when backend rendering is selected.

## Template Architecture

Templates are represented by two primary database tables:

| Table | Purpose |
| --- | --- |
| `templates` | Stores uploaded template files, activity state, analysis JSON, matcher features, tags, kind, and origin information. |
| `template_metadata` | Stores zone maps, sizing rules, platform rules, editable fields, and export rules. |

`TemplateService` handles upload, analysis, detail, recommendation, application, and deletion. The content generation pipeline can use a preselected template or can let planning/template recommendation select candidates automatically.

Template data feeds:

| Consumer | How It Uses Template Data |
| --- | --- |
| `ContentService` | Recommends templates and prepares template context before orchestration. |
| `AIOrchestratorService` | Uses template candidates/context for generation strategy and layout adaptation. |
| `RendererService` | Uses `TemplateMetadata` sizing and zone information during rendering. |
| `DataValidatorService` | Uses template intelligence when resolving visual identity and design-system context. |

## AI Integration Boundary

The AI layer lives in `app/ai`, but the rest of the backend only touches it through a few clear service boundaries.

| AI Boundary | Called From | Purpose |
| --- | --- | --- |
| `AIOrchestratorService` | `ContentService` | Main generation orchestration. Produces text payloads, creative decisions, scene graphs, validation reports, image assets, and final payloads. |
| `ToneIntelligenceService` | `ContentService` | Tone evaluation for content and Brand Space context. |
| `BrandIntelligenceService` | `ContentService`, `DataValidatorService` | Converts personas/objectives and brand context into structured generation-ready forms. |
| `LayoutDecisionEngine` | `ContentService` | Helps resolve layout/generation decision inputs. |
| `SessionMemoryPlanner` | `ContentService` | Helps keep follow-up requests connected to prior content/session context. |
| `BrandAssetAnalyzer` | `BrandAssetService` | Extracts structured brand intelligence from uploaded brand attachments. |
| `OCRService` and `KnowledgeRetrievalService` | `KnowledgeService`, `BrandAssetService` | Extracts text and indexes/retrieves knowledge. |

Provider selection is configured through settings. The code includes OpenAI and Anthropic provider support, plus image provider routing and fallback provider settings. Model names and provider choices come from configuration, not hardcoded service calls.

## Configuration Architecture

Configuration is centralized in `app/core/config.py` through a Pydantic `Settings` class loaded from environment variables and `.env`.

Important configuration groups:

| Group | Examples |
| --- | --- |
| App/runtime | `app_name`, `environment`, `debug`, `api_v1_prefix`, `cors_origins` |
| Security | `secret_key`, JWT expiry settings, `jwt_algorithm`, `social_encryption_key` |
| Database | `database_url`, `alembic_database_url` |
| Storage | `object_storage_provider`, `object_storage_base_path`, `generated_assets_base_url`, `asset_download_base_url`, static storage exposure |
| Vector/RAG | `vector_store_provider`, `vector_store_base_path`, `embedding_model` |
| AI providers | `openai_api_key`, `anthropic_api_key`, text/research/image provider settings, model settings |
| Rendering | default dimensions, font path, image quality settings, renderer policy flags |
| Trace/evaluation | generation trace path, payload flags, cost estimation, automatic RAGAS evaluation |
| Worker | poll interval, batch size, lease seconds, heartbeat seconds |
| Upload validation | max file bytes, PDF pages, presentation pages, image megapixels |
| Email/demo | SMTP fields and demo owner seed settings |

Because settings are cached through `@lru_cache`, runtime code typically calls `get_settings()` instead of constructing `Settings` directly.

## Error Handling

The system uses domain-specific exceptions from `app/core/exceptions.py`. `main.py` maps those exceptions into HTTP responses.

| Exception | HTTP Behavior |
| --- | --- |
| `NotFoundError` | `404` with a simple detail message. |
| `DuplicateResourceError` | `409` with a detail message. |
| `GenerationFailureError` | `400` with `detail` plus a structured `failure` payload. |
| `AuthorizationError`, `GuardrailViolationError`, `LifecycleError`, `UploadValidationError`, `UsageLimitExceededError` | `400` with a detail message. |

This keeps service code focused on domain failures while the API layer owns HTTP translation.

## Typical End-to-End Workflows

### Tenant and User Setup

```mermaid
flowchart TD
    CreateTenant["Create tenant"] --> TenantService["TenantService"]
    TenantService --> TenantRows["tenants / users / roles"]
    TenantService --> Email["EmailService\nactivation email if configured"]
    UserActivation["User activation"] --> AuthService["AuthService"]
    AuthService --> JWT["Access + refresh token"]
```

Tenant creation and user management are handled through `TenantService`. RBAC is seeded at application startup, and demo-owner seeding is controlled by configuration.

### Brand Space Setup

```mermaid
flowchart TD
    CreateBrand["Create Brand Space"] --> BrandService["BrandSpaceService.create_brand()"]
    BrandService --> Sections["brand_configuration_sections"]
    BrandService --> Personas["personas"]
    BrandService --> Guardrails["guardrails"]
    BrandService --> Objectives["objectives"]
    UploadAssets["Upload brand attachments"] --> BrandAssetService["BrandAssetService"]
    BrandAssetService --> ProcessedAssets["structured brand asset tables"]
    ProcessedAssets --> Validator["DataValidatorService.refresh_brand_context()"]
    Sections --> Validator
    Validator --> Resolved["brand_spaces.resolved_brand_context"]
    Publish["Publish Brand Space"] --> Active["Brand lifecycle active"]
```

The generation service requires an active Brand Space. Brand setup is not just a form-fill flow; it builds the context that generation later depends on.

### Content Generation

```mermaid
flowchart TD
    Request["ContentGenerateRequest"] --> Access["Auth + brand access"]
    Access --> Context["Gather brand/persona/objective/session context"]
    Context --> Refresh["Refresh resolved brand context"]
    Refresh --> Planning["Template, reference, layout, research, and memory planning"]
    Planning --> AIRequest["AIOrchestrationRequest"]
    AIRequest --> AI["AIOrchestratorService"]
    AI --> Persist["content_history + generated_assets"]
    Persist --> Response["ContentVersionResponse"]
```

This is the central workflow of the product. It touches most subsystems: auth, Brand Space context, knowledge retrieval, template recommendation, AI orchestration, rendering, storage, tracing, usage, and persistence.

### Background Processing

```mermaid
flowchart TD
    Upload["Upload asset/template"] --> JobRow["jobs row queued"]
    WorkerPoll["Worker polls jobs table"] --> Claim["claim_pending"]
    Claim --> Dispatch{"job_type"}
    Dispatch -->|KNOWLEDGE_PROCESS| Knowledge["KnowledgeService / BrandAssetService"]
    Dispatch -->|TEMPLATE_ANALYSIS| Template["TemplateService.analyze"]
    Dispatch -->|RAGAS_EVALUATION| Ragas["scripts.ragas_evaluation"]
    Knowledge --> Complete["set_status succeeded or fail_or_retry"]
    Template --> Complete
    Ragas --> Complete
```

The queue is simple and database-backed. This is easy to run locally and avoids additional infrastructure, but it also means job throughput and concurrency depend on database polling and lease logic.

## Communication Between Components

The backend is not event-driven in the distributed-systems sense. Communication is mostly direct Python calls inside the API or worker process.

| Source | Target | Communication Style |
| --- | --- | --- |
| Frontend | Backend API | HTTP JSON requests to `/api/v1/...`. |
| API routes | Services | Direct async Python method calls. |
| Services | Repositories | Direct async Python method calls using a shared `AsyncSession`. |
| Repositories | PostgreSQL | SQLAlchemy async queries. |
| Services | Object storage | Direct adapter calls. |
| Services | Vector store | Direct adapter/retrieval service calls. |
| Services | AI providers | Provider interfaces under `app/ai/providers`. |
| API/Services | Worker | Indirectly through `jobs` table records. |
| Worker | Services | Direct Python method calls after claiming jobs. |

This design keeps deployment simple: the API, worker, database, object storage directory, and vector store directory are enough to run the system locally.

## Important Design Decisions in the Current Architecture

### The Service Layer Owns Business Flow

The codebase consistently keeps route handlers thin. Routes validate inputs, enforce access, and call services. Services then coordinate repositories, storage, AI modules, rendering, and jobs. This is why the worker can reuse the same business logic that the API uses.

### Brand Context Is Materialized

The system does not rebuild the entire Brand Space context from scratch inside every generation prompt. `DataValidatorService.refresh_brand_context()` materializes a resolved context onto `brand_spaces.resolved_brand_context` and writes snapshots. This gives the generation pipeline a stable context object to consume.

### Uploaded Assets Are Database Records Plus Stored Files

The database stores metadata and storage paths. The file bytes live in object storage. This applies to knowledge files, brand attachments, generated images, previews, exports, and template files.

### The Worker Uses PostgreSQL as a Queue

The job queue is implemented with the `jobs` table, leases, heartbeats, retries, and status fields. There is no Redis, Celery, or external broker in the current implementation.

### AI Outputs Are Persisted as Explainable Contracts

Generation results are not treated as a single blob of text. The system stores structured payloads: generated payload, blueprint payload, scene graph, creative decision, validation report, trace metadata, final render assets, and usage. This is important for debugging and for future feature work.

### Rendering Is a Backend Responsibility

When backend rendering is used, `RendererService` composes files from structured inputs. This gives the backend control over exact logos, legal/footer overlays, exports, and deterministic layout behavior.

## Current Dependency Summary

Major Python dependencies from `pyproject.toml` include:

| Dependency Area | Libraries |
| --- | --- |
| Web/API | FastAPI, Uvicorn, Pydantic, Pydantic Settings |
| Database | SQLAlchemy, asyncpg, psycopg, Alembic |
| Auth/security | PyJWT, passlib/bcrypt, cryptography |
| AI providers | OpenAI, Anthropic |
| Retrieval | FAISS, LangChain Community, LangChain OpenAI |
| OCR/document parsing | Google Cloud Vision, PyMuPDF, pdfplumber, python-docx, python-pptx |
| Rendering/image processing | Pillow, CairoSVG, ReportLab, matplotlib, OpenCV headless, scikit-image |
| Evaluation | datasets, ragas |
| HTTP/utilities | httpx, email-validator |

## File and Folder Map

| Path | Role |
| --- | --- |
| `main.py` | FastAPI application assembly, startup seeding, static storage mounting, healthcheck, and exception handlers. |
| `app/api` | Versioned API router and route modules. |
| `app/core` | Settings, security, dependency guards, enums, and exceptions. |
| `app/db` | SQLAlchemy base and async session factory. |
| `app/models` | ORM table definitions. |
| `app/repositories` | Database access layer. |
| `app/schemas` | API request/response contracts. |
| `app/services` | Business workflows and orchestration between subsystems. |
| `app/ai` | AI orchestration, prompt/context handling, providers, RAG, image generation, tone/brand intelligence, and contracts. |
| `app/integrations` | Object storage and vector store adapters. |
| `app/workers` | Worker loop and job dispatch. |
| `scripts` | Worker entrypoint, smoke scripts, debug scripts, RAGAS evaluation, and maintenance utilities. |
| `contracts` | Frontend API contract artifacts. |
| `alembic` | Database migrations. |
| `storage` | Local object storage mount. |
| `vector_store` | Local FAISS vector store mount. |
| `frontend` | Frontend workspace present in this repository, while Docker compose currently builds from `../violyt-frontend`. |

## System Boundaries and Integration Points

The current system integrates with external services through configuration-backed adapters:

| External Area | Current Integration |
| --- | --- |
| LLM text generation | OpenAI and Anthropic provider classes under `app/ai/providers`. |
| Image generation | Image provider routing under `app/ai/providers/image_generation.py` and provider settings. |
| Embeddings | OpenAI embeddings when configured; deterministic hash embeddings otherwise. |
| OCR | Google Cloud Vision is available through dependencies and OCR service code; document/image extraction also uses local parsing libraries. |
| Object storage | Local filesystem by default; S3 adapter available. |
| Email | SMTP settings available for tenant/user email flows. |
| Live research | Configurable live research settings, including Brave/OpenAI-style search configuration in settings. |
| RAGAS evaluation | Optional job-driven evaluation using trace artifacts. |

## Operational Notes for the Next Team

1. Run migrations before starting the API. The Docker command already does this with `alembic upgrade head`.
2. The API seeds RBAC and the demo owner during startup through the FastAPI lifespan hook.
3. The worker must run separately for knowledge processing, template analysis, and optional RAGAS evaluation.
4. Local development relies on mounted `storage/` and `vector_store/` folders. Do not treat database rows as sufficient backup for uploaded/generated files.
5. Generation debugging depends heavily on `storage/generation_traces/` when tracing is enabled.
6. The frontend should use the backend through `/api/v1` endpoints and generated contract shapes from the schemas/contracts.
7. Brand Spaces must be active before normal content generation can run.
8. Processed brand assets are not just files; they update structured tables and then refresh `resolved_brand_context`.
9. Job processing is database-polled. If jobs appear stuck, inspect `jobs.status`, `lease_owner`, `lease_expires_at`, `heartbeat_at`, `retry_count`, and `error_message`.
10. The current architecture keeps most implementation contracts in Python/Pydantic models. Before changing field names or JSON payload shapes, check frontend contracts, persisted content payloads, renderer expectations, and AI orchestration contracts.

## Architecture Summary

The current system is a layered FastAPI application backed by PostgreSQL, local/S3-compatible object storage, a FAISS vector store, a reusable service layer, and a simple database-backed worker queue. The central product concept is the Brand Space. Brand Space sections, uploaded brand assets, processed intelligence, knowledge retrieval, and templates are consolidated into a resolved brand context. Content generation then uses that context, the selected studio panel, session memory, reference/template data, and AI orchestration to produce structured content, generated assets, render payloads, and persisted history.

The system is built to make AI output traceable and operationally maintainable: generation results are stored as structured payloads, render decisions are preserved in explainability metadata, uploaded assets remain linked to their processed intelligence, and background processing reuses the same service layer as the API. This is the main architectural thread the next team should preserve while continuing the project.
