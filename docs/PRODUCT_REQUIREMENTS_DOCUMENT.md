# Product Requirements Document

## Document Purpose

This PRD describes the current product requirements for the Violyt platform based on the implemented codebase. It is intended for client, product, QA, and development stakeholders who need a shared understanding of what the product does, who it serves, and what behavior should be expected.

This document is product-facing. It does not replace the architecture, API, database, or AI implementation documents.

## Product Summary

Violyt is a multi-tenant SaaS platform for brand-aware content creation. The product allows platform owners and tenant teams to create Brand Spaces, upload brand knowledge and assets, generate brand-aligned content through chat and studio controls, render/export creative outputs, and share generated work for review.

The system is built around the Brand Space. A Brand Space stores structured brand inputs, uploaded files, processed brand intelligence, validation results, and resolved context that the AI generation pipeline uses when producing content.

## Product Goals

- Give tenant teams a controlled workspace for managing brand data, users, assets, and generated content.
- Generate content that uses validated Brand Space context instead of relying only on ad hoc prompts.
- Support text, visual, carousel, infographic, and document-oriented generation workflows through a shared studio panel.
- Preserve tenant and Brand Space isolation across authentication, data access, assets, history, and analytics.
- Provide traceable generation results through structured payloads, generation decisions, assets, and explainability metadata.
- Support collaboration through shareable review links, comments, and approval status.
- Give platform owners visibility into tenants, usage, users, and platform-level analytics.

## User Roles

| Role | Product Responsibility |
| --- | --- |
| Platform Owner / Super Admin | Creates and manages tenants, creates the initial Tenant Admin for each tenant, views platform analytics, manages tenant-level capacity, and can inspect tenant summaries. |
| Tenant Admin | Manages tenant profile, creates and manages Tenant Users and Brand Users, assigns Brand Space access, manages Brand Spaces, usage settings, and tenant-level workspace data. |
| Tenant User | Works inside tenant scope and can access permitted Brand Spaces and content workflows. |
| Brand User | Works only inside assigned Brand Spaces. |
| External Reviewer | Opens tokenized review links, views shared content, comments when allowed, and updates review status when allowed. |

## Role Hierarchy

The platform access model is hierarchical:

1. Platform Owner / Super Admin creates tenants and the tenant's initial Tenant Admin.
2. Tenant Admin creates and manages tenant-level users.
3. Tenant Admin assigns users as Tenant Users or Brand Users through role and Brand Space access.
4. Tenant Users can work within tenant scope according to permissions.
5. Brand Users are restricted to the Brand Spaces assigned to them.
6. External Reviewers do not use tenant login and only access shared content through review tokens.

Platform Owner / Super Admin access is intended for tenant administration, tenant visibility, usage management, and platform analytics. Brand Space content workflows are handled by tenant and brand-level users.

## Core Product Concepts

### Tenant

A tenant is a customer account or organization. Tenants contain users, Brand Spaces, usage limits, usage consumption, metadata, logo settings, and tenant-level analytics.

### Brand Space

A Brand Space is the main creative and knowledge container. It contains brand sections, lifecycle state, resolved brand context, personas, guardrails, objectives, attachments, templates, content history, chat sessions, review links, and usage.

Generation requires an active Brand Space.

### Brand Attachments and Knowledge

Users can upload brand files, references, logos, templates, mood boards, word banks, audience insights, and other knowledge. The backend validates the upload, stores the file, processes it with OCR/analysis where applicable, indexes searchable text, and refreshes resolved brand context.

### Studio Panel

The studio panel describes the intended output surface. It includes format, platform preset, file type, and optional size. Current format families include static, carousel, PDF, and infographic.

### Generated Content Version

Generated output is saved as a versioned content record. A version stores the prompt, studio panel, generated payload, blueprint payload, generation decision, explainability metadata, tone feedback, and related assets.

### Review Link

A review link gives an external reviewer token-based access to a specific generated content item without tenant authentication.

## Product Scope

### In Scope

- User login, activation, refresh, profile, password reset, password change, and two-factor flows.
- Platform owner tenant management.
- Tenant user management and Brand Space assignment.
- Tenant logo and metadata management.
- Brand Space creation, editing, section updates, finalization, publishing, unpublishing, archiving, restoring, and deletion.
- Brand Space validation and resolved context viewing.
- Brand attachment upload, listing, detail, reprocessing, unsync, and deletion.
- Knowledge upload, listing, status, deletion, and reprocessing.
- Template upload, analysis metadata, recommendation, application, and deletion.
- Content generation, rewrite, tone check, history, detail, copy, archive, delete, preview, and export.
- Chat sessions, messages, session update, session delete, generation cancellation, small-talk responses, strategy chat, text-only deliverables, evaluation/review responses, retrieval responses, and mixed follow-up workflows.
- Folder organization for generated content.
- Shareable review links, review comments, and review status.
- Social connection records and publish request scaffolding.
- Tenant, brand, usage, and platform analytics.
- Background jobs for processing and evaluation workflows.
- Asset storage and download access.

### Out of Scope or Limited

- Live social posting currently prepares and validates publish requests; it is not a complete live network posting system.
- The renderer is not a full interactive design editor.
- Some advanced AI-assisted capabilities, such as dedicated chart rendering, icon matching, and standalone visual planning, exist as supporting capabilities and are not exposed as separate finished user tools.
- When external AI providers are unavailable, fallback responses may keep the workflow running but should not be treated as final production-quality creative output.

## Functional Requirements

### Authentication and User Access

| Operation | Expected Result |
| --- | --- |
| Users can log in with email and password. | Valid credentials return an access token and refresh token, or a two-factor challenge when 2FA is enabled. |
| Users can activate accounts from activation tokens. | A valid activation token sets the password and returns tokens. |
| Users can manage their profile. | Profile read/update and account deactivation are available to authenticated users. |
| Users can enable and disable two-factor authentication. | Setup, enable, disable, status, and challenge verification endpoints are available. |
| Access is role and scope controlled. | Tenant and Brand Space routes enforce current principal, tenant scope, and Brand Space scope. |

### Tenant Management

| Operation | Expected Result |
| --- | --- |
| Platform owners can create tenants. | Tenant, admin user, usage limits, metadata, and activation delivery status are returned. |
| Platform owners can list and inspect tenants. | Tenant summaries include users, Brand Space counts, usage, token telemetry, metadata, and logo path when available. |
| Authorized users can update tenant data. | Tenant update flows persist tenant profile and metadata changes. |
| Tenant logos can be uploaded. | Uploaded logo is stored and reflected in tenant summary. |
| Tenant Admins can create Tenant Users and Brand Users. | User records include role codes, Brand Space assignments, activation state, and profile data. |
| Tenant users and Brand Users can be updated, viewed, and deactivated. | User changes persist profile, role, active state, and Brand Space access updates. |
| Usage limits and usage summaries are available. | Limits and consumption can be read and updated through tenant endpoints. |

### Brand Space Management

| Operation | Expected Result |
| --- | --- |
| Users can create Brand Spaces. | A draft Brand Space is created with identity/foundation/voice inputs where supplied. |
| Users can update Brand Space sections. | Section upsert APIs save versioned payloads and refresh resolved context. |
| Brand Spaces have lifecycle controls. | Finalize, publish, unpublish, archive, restore, and delete flows update lifecycle state. |
| Users can view Brand Space overview. | Overview includes brand data, sections, personas, guardrails, and objectives. |
| Users can view validation and resolved context. | Validation summaries and resolved context expose warnings, conflicts, excluded assets, and current context. |
| Generation is blocked unless the Brand Space is active. | Content generation service enforces active lifecycle state before expensive work starts. |

### Brand Attachments and Knowledge

| Operation | Expected Result |
| --- | --- |
| Users can upload files to Brand Space fields. | Uploads are preflight validated, stored, tracked, and queued for processing unless skipped. |
| Users can view attachments by Brand Space and field. | Attachment responses include processing state, routing, validation, reusable assets, and URLs where available. |
| Attachments can be reprocessed. | Reprocessing resets processing state and queues a background job. |
| Attachments can be unsynced or deleted. | Unsynced/deleted assets are excluded from resolved brand context and refresh validation state. |
| Users can upload general knowledge. | Knowledge files are stored and processed into searchable evidence where possible. |
| Knowledge can be listed, checked, deleted, and reprocessed. | Status and lifecycle fields reflect processing outcomes. |

### Content Generation and Chat

| Operation | Expected Result |
| --- | --- |
| Users can generate content from a prompt and studio panel. | Response includes generated payload, blueprint payload, generation decision, explainability metadata, tone feedback, and assets. |
| Generation uses Brand Space context. | The backend loads resolved context, personas, objectives, knowledge, templates, references, session memory, and visual planning before orchestration. |
| Users can request image/visual generation. | Generated assets or final render assets are stored and linked to content versions. |
| Users can rewrite existing content. | Rewrite creates a new version without overwriting the original. |
| Users can run tone checks. | Tone response includes score, matched signals, deviations, and rewrite suggestions. |
| Users can export generated content. | Export returns preview and export assets plus renderer metadata. |
| Users can create and manage chat sessions. | Chat sessions can be created, listed, updated, deleted, and used for messages. |
| Chat messages can trigger generation. | User and assistant messages are persisted, and assistant messages can link to generated content. |
| Users can cancel active chat generation. | Cancel endpoint marks pending work for the session as cancelled where supported. |
| Chat can route different user intents. | The backend can distinguish conversational replies, strategy discussion, text-only deliverables, visual generation, evaluation/review, retrieval, and mixed workflows. |

### Templates and Rendering

| Operation | Expected Result |
| --- | --- |
| Users can upload templates. | Template files are stored and queued/analyzed for metadata. |
| Templates can be listed and inspected. | Template detail includes template record and metadata. |
| Templates can be recommended. | Recommendation considers prompt, studio panel, platform fit, export fit, and template metadata. |
| Templates can be applied to a prompt. | Apply returns template context, metadata, prompt, and studio panel data. |
| Users can request layout, preview, and export rendering. | Render responses include preview/export assets and renderer metadata. |
| Renderer preserves structured contracts. | Renderer consumes blueprint, scene graph, text, template metadata, logo path, image assets, and visual rules. |

### Review, Folders, Social, Analytics, Jobs, and Storage

| Operation | Expected Result |
| --- | --- |
| Users can create share links. | Share link contains token, status, and external comment permission. |
| Reviewers can view shared content. | Public token endpoint returns content and comments for valid token. |
| Reviewers can comment and update status. | Comment and status endpoints update review records. |
| Users can organize content in folders. | Folder create, list, rename, delete, and move content flows are supported. |
| Users can store social connection records. | Connect, list, publish request, and disconnect endpoints exist. |
| Analytics are available by platform, tenant, brand, and usage scope. | Analytics responses return scope and metric payloads. |
| Users can inspect background jobs. | Job list and status endpoints expose queued/processing/succeeded/failed/cancelled state. |
| Stored assets can be downloaded. | Storage download endpoint serves valid stored asset paths according to backend rules. |

## Key User Workflows

### Platform Owner Tenant Setup

1. Platform owner logs in.
2. Platform owner creates a tenant and tenant admin.
3. Platform owner configures tenant usage limits and metadata.
4. Tenant admin receives or uses activation flow.
5. Tenant appears in platform analytics and tenant list.

### Tenant Admin Brand Setup

1. Tenant admin creates a Brand Space.
2. Tenant admin fills brand sections.
3. Tenant admin uploads brand attachments such as logo, reference creatives, mood boards, knowledge, word banks, and templates.
4. Worker processes uploads.
5. Validation refreshes resolved brand context.
6. Tenant admin finalizes and publishes the Brand Space.

### Tenant Admin User Management

1. Tenant admin opens tenant user management.
2. Tenant admin creates Tenant Users or Brand Users.
3. Tenant admin assigns Brand Space access for Brand Users.
4. Tenant admin updates user profile, role, active state, or Brand Space assignments when needed.
5. Deactivated users lose access according to backend authorization rules.

### Brand User Content Generation

1. Brand user opens an assigned Brand Space.
2. User selects output format, platform, file type, and optional template/reference assets.
3. User enters a prompt in chat or content workspace.
4. For chat, backend first classifies whether the request is conversational, strategic, text-only, visual generation, evaluation, retrieval, or a mixed follow-up.
5. Backend gathers brand context, session memory, templates, retrieval evidence, and planning metadata when generation is needed.
6. AI orchestration creates structured content, visual decisions, blueprints, and assets.
7. Output is saved to content history and shown to the user.
8. User exports, rewrites, copies, archives, deletes, or shares the output.

### External Review

1. Authenticated user creates a review link for generated content.
2. External reviewer opens the tokenized link.
3. Reviewer views generated payload and assets.
4. Reviewer comments or updates status when allowed.
5. Authenticated users can inspect review feedback.

## Non-Functional Requirements

| Area | Requirement |
| --- | --- |
| Security | Authentication uses bearer tokens. Sensitive social connector secrets are encrypted. Routes enforce role, tenant, and Brand Space scope. |
| Tenant Isolation | Tenant-owned and Brand Space-owned records must be filtered by tenant and brand scope. |
| Auditability | Generated content stores structured payloads, blueprint payloads, generation decisions, explainability metadata, assets, and token usage where available. |
| Reliability | Background jobs use status, retry, lease, and heartbeat fields. |
| Configurability | Provider choices, model names, storage paths, vector paths, renderer defaults, upload limits, worker settings, and trace options are configuration-backed. |
| Performance | Expensive upload processing runs through background jobs. Generation writes compact traces by default. |
| Maintainability | Route handlers stay thin; services own workflows; repositories own database access; provider SDK details stay behind provider adapters. |
| Compatibility | Shared payload fields should be extended additively rather than renamed or removed. |

## Success Metrics

- Tenants and Brand Spaces can be created and managed without manual database work.
- Active Brand Spaces can generate content successfully with expected structured response fields.
- Uploaded brand assets process into validation and resolved context data.
- Generated outputs include usable assets for preview/export.
- Review links work without tenant authentication.
- Usage summaries and analytics reflect generated activity.
- Background jobs move from queued to terminal states with useful errors when failures occur.
- Developers can trace generation decisions from request to response.

## Product Risks and Dependencies

| Risk | Product Impact | Mitigation |
| --- | --- | --- |
| Brand input quality | Generated output may become generic or less brand-specific if uploaded assets or Brand Space data are incomplete. | Validate uploads, expose warnings, refresh resolved context, and improve brand curation. |
| External AI provider availability | Fallback output may keep the workflow running but can be lower quality than intended provider output. | Monitor provider status and review generation metadata when quality looks degraded. |
| Social publishing integration | Social publish currently prepares validated dispatch records rather than completing live network posting. | Complete provider-specific publishing integrations before treating this as live social posting. |
| Generation regression sensitivity | Changes to shared generation behavior can affect multiple output formats. | Use scoped changes, regression testing, and preserved shared fields. |
| Background worker availability | Upload processing, template analysis, and evaluations may stay queued if the worker is not running. | Run worker alongside API and monitor job status. |
| Asset storage availability | Stored asset records require matching storage/vector files to remain available. | Preserve storage and vector volumes and rebuild indexes when needed. |

## Current Implementation Notes

- Chat is more than a wrapper around content generation. It uses intent routing, conversation memory, brand summary memory, text-only generation, evaluation, retrieval, and mixed-workflow helpers before deciding whether to call the full visual/content generation path.
- Text-only deliverables such as blogs, LinkedIn posts, captions, X posts/threads, YouTube descriptions, newsletters, emails, scripts, and general copy are supported through backend service logic even when they do not require final visual rendering.
- Evaluation/review workflows can inspect text and selected reference assets, produce scorecards, and carry findings into a later generation request.
- Some services are internal support capabilities rather than standalone user tools. They improve generation quality, memory, planning, scoring, traces, or asset delivery behind the visible workflows.

## Acceptance Checklist for Client Delivery

- Product stakeholders understand the roles and workflows.
- Tenant, Brand Space, generation, review, and analytics flows are described.
- In-scope and limited areas are clearly separated.
- Functional requirements map to implemented modules and route surfaces.
- Non-functional expectations are documented.
- Risks and dependencies are visible before sign-off.
