# Tool Documentation: Development To User

## Document Purpose

This document explains the major tools and feature modules in the current Violyt codebase from development implementation to user-facing behavior.

Each section answers:

- What the tool does for the user.
- Where it appears in the product.
- Which backend routes and services support it.
- Which records, jobs, assets, or AI modules are involved.
- What the user should expect as output.

This document is a bridge between product usage and codebase understanding.

## System-Level Map

| Product Area | Frontend Area | Backend Routes | Main Services |
| --- | --- | --- | --- |
| Authentication | `frontend/app/auth/*`, auth components/hooks | `/api/v1/auth/*` | `AuthService` |
| Tenant management | tenants pages, platform owner dashboard | `/api/v1/tenants/*` | `TenantService`, `UsageLimitService`, `EmailService` |
| Brand Spaces | brand space pages and editor | `/api/v1/brands/*` | `BrandSpaceService`, `DataValidatorService` |
| Brand attachments | Brand Space upload fields | `/api/v1/brands/{brand_id}/attachments/*` | `BrandAssetService` |
| Knowledge | Brand knowledge/upload areas | `/api/v1/knowledge/*` | `KnowledgeService` |
| Templates | Template upload/recommend/apply flows | `/api/v1/templates/*` | `TemplateService` |
| Content generation | chat/workspace generation UI | `/api/v1/content/*` | `ContentService` |
| Chat | workspace chat | `/api/v1/chat/*` | `ChatService`, `ContentService`, `IntentRouterService`, `TextContentService`, `EvaluationService` |
| Rendering/export | preview/export actions | `/api/v1/render/*`, `/api/v1/content/export` | `RendererService`, `ContentService` |
| Review | review page and share flow | `/api/v1/review/*` | `ReviewService` |
| Folders | content organization | `/api/v1/folders/*` | `FolderService` |
| Social | social connection and prepared publish flow | `/api/v1/social/*` | `SocialService` |
| Analytics | dashboard and analytics pages | `/api/v1/analytics/*` | `AnalyticsService` |
| Jobs | processing status screens/diagnostics | `/api/v1/jobs/*` | `JobService`, worker |
| Storage | asset URLs and downloads | `/api/v1/storage/download` | `AssetDeliveryService`, storage adapter |

## Access and Scope Notes

- Tenant management is tenant-scoped and role-gated. Platform Owner / Super Admin can create and inspect tenants; Tenant Admin can manage users and settings inside the assigned tenant.
- Brand Space tools are Brand Space scoped. Most brand-scoped backend routes require the `X-Brand-Space-Id` header, and the frontend passes that scope when working inside a Brand Space.
- Platform Owner / Super Admin access is for tenant administration and platform analytics. Brand Space content workflows are handled by tenant and brand-level users.
- External reviewers do not use tenant authentication. They access shared content through review tokens.

## 1. Authentication Tool

### User Understanding

The authentication tool lets users log in, activate accounts, reset passwords, manage profile details, change passwords, and configure two-factor authentication.

### User Workflow

1. User opens login, activation, password reset, or 2FA page.
2. Frontend submits credentials or token data.
3. Backend returns tokens, a two-factor challenge, profile data, or confirmation messages.
4. Authenticated requests use bearer tokens.

### Development Understanding

| Layer | Files |
| --- | --- |
| Routes | `app/api/routes/auth.py` |
| Service | `app/services/auth.py` |
| Schemas | `app/schemas/auth.py` |
| Security helpers | `app/core/security.py`, `app/core/dependencies.py` |
| Frontend | `frontend/app/auth/*`, `frontend/hooks/useLogin.ts`, `frontend/hooks/useAuthProfile.ts`, `frontend/lib/api/endpoints.ts` |

### Main Endpoints

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/activate`
- `POST /api/v1/auth/forgot-password`
- `POST /api/v1/auth/reset-password`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`
- `GET /api/v1/auth/profile`
- `PUT /api/v1/auth/profile`
- `POST /api/v1/auth/change-password`
- `DELETE /api/v1/auth/profile`
- `GET /api/v1/auth/2fa/status`
- `POST /api/v1/auth/2fa/setup`
- `POST /api/v1/auth/2fa/enable`
- `POST /api/v1/auth/2fa/disable`
- `POST /api/v1/auth/2fa/verify`

### Expected User Output

- Access and refresh tokens.
- Current user profile and roles.
- 2FA setup details or challenge verification.
- Password/profile confirmation messages.

## 2. Tenant Management Tool

### User Understanding

Tenant management lets platform owners and tenant admins manage tenant account details, users, logos, capacity, usage limits, and Brand Space summaries.

### User Workflow

1. Platform owner creates a tenant and tenant admin.
2. Tenant logo and metadata can be uploaded or updated.
3. Tenant users are created, edited, assigned roles, assigned Brand Spaces, or deactivated.
4. Usage limits and usage summaries are reviewed.

### Development Understanding

| Layer | Files |
| --- | --- |
| Routes | `app/api/routes/tenant.py` |
| Service | `app/services/tenant.py`, `app/services/usage.py` |
| Email support | `app/services/email.py` |
| Repository | `app/repositories/tenant.py` |
| Models | `app/models/tenant.py`, `app/models/collaboration.py` |
| Schemas | `app/schemas/tenant.py` |
| Frontend | `frontend/app/(mainContent)/tenants/*`, `frontend/components/tenants/*`, `frontend/components/platformOwner/*`, `frontend/hooks/tenantAdmins/*` |

### Main Endpoints

- `POST /api/v1/tenants`
- `GET /api/v1/tenants`
- `GET /api/v1/tenants/{tenant_id}`
- `PUT /api/v1/tenants/{tenant_id}`
- `DELETE /api/v1/tenants/{tenant_id}`
- `POST /api/v1/tenants/{tenant_id}/logo`
- `PUT /api/v1/tenants/{tenant_id}/brand-usage-targets`
- `GET /api/v1/tenants/{tenant_id}/users`
- `POST /api/v1/tenants/{tenant_id}/users`
- `GET /api/v1/tenants/{tenant_id}/users/{user_id}`
- `PUT /api/v1/tenants/{tenant_id}/users/{user_id}`
- `POST /api/v1/tenants/{tenant_id}/users/{user_id}/deactivate`
- `GET /api/v1/tenants/{tenant_id}/brand-spaces`
- `PUT /api/v1/tenants/{tenant_id}/usage-limits`
- `GET /api/v1/tenants/{tenant_id}/usage-summary`

### Expected User Output

- Tenant list and tenant detail.
- Tenant logo, metadata, usage, and capacity details.
- Tenant user records with role and Brand Space assignments.
- Activation delivery metadata for new users where available.

## 3. Brand Space Tool

### User Understanding

Brand Spaces are the workspaces where brand identity, tone, knowledge, objectives, assets, and generated content live. A user sets up a Brand Space before generating brand-aware content.

### User Workflow

1. User creates a Brand Space.
2. User fills brand setup sections.
3. User uploads assets and knowledge.
4. User checks validation/resolved context.
5. User finalizes or publishes the Brand Space.
6. Active Brand Space becomes available for generation workflows.

### Development Understanding

| Layer | Files |
| --- | --- |
| Routes | `app/api/routes/brand.py` |
| Service | `app/services/brand.py`, `app/services/data_validation.py` |
| Repository | `app/repositories/brand.py` |
| Models | `app/models/brand.py` |
| Schemas | `app/schemas/brand.py` |
| Frontend | `frontend/app/(mainContent)/brand_space/*`, `frontend/components/brandSpaces/*` |

### Main Endpoints

- `POST /api/v1/brands`
- `GET /api/v1/brands`
- `GET /api/v1/brands/{brand_id}`
- `GET /api/v1/brands/{brand_id}/usage`
- `PUT /api/v1/brands/{brand_id}`
- `PUT /api/v1/brands/{brand_id}/sections`
- `PUT /api/v1/brands/{brand_id}/sections/{section_code}`
- `POST /api/v1/brands/{brand_id}/finalize`
- `POST /api/v1/brands/{brand_id}/publish`
- `POST /api/v1/brands/{brand_id}/unpublish`
- `POST /api/v1/brands/{brand_id}/archive`
- `POST /api/v1/brands/{brand_id}/restore`
- `DELETE /api/v1/brands/{brand_id}`
- `GET /api/v1/brands/{brand_id}/overview`
- `GET /api/v1/brands/{brand_id}/validation`
- `GET /api/v1/brands/{brand_id}/resolved-context`

### Expected User Output

- Brand Space record with lifecycle state.
- Section data and overview.
- Validation warnings, conflicts, excluded assets, and resolved context.
- Usage summary for the Brand Space.

## 4. Brand Attachment Tool

### User Understanding

The Brand Attachment tool lets users upload brand-related files such as logos, mood boards, references, templates, word banks, typography guides, palettes, and audience documents. These uploads are processed into reusable brand intelligence.

### User Workflow

1. User uploads a file against a Brand Space field.
2. Backend validates size, MIME type, page count, and image dimensions.
3. File is stored and processed.
4. Processed data updates validation and resolved brand context.
5. User can list, inspect, reprocess, unsync, or delete attachments.

### Development Understanding

| Layer | Files |
| --- | --- |
| Routes | `app/api/routes/brand_assets.py` |
| Service | `app/services/brand_assets.py`, `app/services/upload_preflight.py`, `app/services/data_validation.py` |
| AI | `app/ai/brand_asset_analysis.py`, `app/ai/rag/ocr.py`, `app/ai/rag/retrieval.py` |
| Models | `app/models/knowledge.py`, `app/models/brand_assets.py` |
| Schemas | `app/schemas/brand_assets.py` |
| Worker | `app/workers/runner.py` |

### Main Endpoints

- `POST /api/v1/brands/{brand_id}/attachments/{field_key}`
- `GET /api/v1/brands/{brand_id}/attachments`
- `GET /api/v1/brands/{brand_id}/attachments/fields/{field_key}`
- `GET /api/v1/brands/{brand_id}/attachments/assets/{asset_id}`
- `POST /api/v1/brands/{brand_id}/attachments/assets/{asset_id}/reprocess`
- `POST /api/v1/brands/{brand_id}/attachments/assets/{asset_id}/unsync`
- `DELETE /api/v1/brands/{brand_id}/attachments/assets/{asset_id}`

### Data and Processing

- Original file metadata is stored in `knowledge_assets`.
- Normalized data can be stored in brand asset tables for logos, palettes, typography, audience insights, references, mood boards, word banks, legal assets, CTA templates, and reusable assets.
- Processing status and validation records are exposed to the frontend.
- Searchable text is indexed in the vector store when applicable.

### Expected User Output

- Attachment lifecycle state.
- Processing status and warnings.
- Classification/routing details.
- Reusable assets and generated asset URLs where available.
- Updated validation and resolved brand context after processing.

## 5. Knowledge Tool

### User Understanding

The Knowledge tool lets users upload general brand, strategy, metadata, template, or campaign-history documents that can support generation through retrieval.

### User Workflow

1. User uploads a knowledge file.
2. Backend stores the file and creates a processing job.
3. Worker extracts text and indexes it.
4. Generation can retrieve relevant knowledge for future prompts.

### Development Understanding

| Layer | Files |
| --- | --- |
| Routes | `app/api/routes/knowledge.py` |
| Service | `app/services/knowledge.py` |
| AI/RAG | `app/ai/rag/ocr.py`, `app/ai/rag/retrieval.py` |
| Repository | `app/repositories/knowledge.py` |
| Models | `app/models/knowledge.py` |
| Worker | `app/workers/runner.py` |

### Main Endpoints

- `POST /api/v1/knowledge/upload`
- `GET /api/v1/knowledge/list`
- `GET /api/v1/knowledge/{knowledge_id}/status`
- `DELETE /api/v1/knowledge/{knowledge_id}`
- `POST /api/v1/knowledge/{knowledge_id}/reprocess`

### Expected User Output

- Knowledge asset lifecycle.
- Extracted text summary where available.
- Processing errors when extraction/indexing fails.
- Searchable evidence for future generation.

## 6. Template Tool

### User Understanding

The Template tool lets users upload design templates or reference layouts, inspect metadata, receive template recommendations, and apply a template to a generation request.

### User Workflow

1. User uploads a template.
2. Backend stores and analyzes it.
3. User can list templates or view template metadata.
4. Generation can recommend or use templates based on prompt and studio panel.

### Development Understanding

| Layer | Files |
| --- | --- |
| Routes | `app/api/routes/template.py` |
| Service | `app/services/template.py` |
| AI | `app/ai/template_vision.py`, `app/ai/brand_asset_analysis.py`, `app/ai/layout_decision.py` |
| Models | `app/models/knowledge.py` |
| Schemas | `app/schemas/template.py` |

### Main Endpoints

- `POST /api/v1/templates/upload`
- `GET /api/v1/templates/list`
- `GET /api/v1/templates/{template_id}`
- `PUT /api/v1/templates/{template_id}/metadata`
- `POST /api/v1/templates/apply`
- `POST /api/v1/templates/recommend`
- `DELETE /api/v1/templates/{template_id}`

### Expected User Output

- Template list and details.
- Template analysis and matcher features.
- Recommendation scores, match types, reasons, and adaptation plans.
- Template context used by generation and rendering.

## 7. Content Generation Tool

### User Understanding

The Content Generation tool creates brand-aware content and visual assets from user prompts. It supports generation, rewrite, tone check, history, detail, copy, archive, delete, preview, and export workflows.

### User Workflow

1. User selects a Brand Space.
2. User enters a prompt and studio panel settings.
3. User may choose persona, objective, template, references, and image generation.
4. Backend generates content and assets.
5. User can rewrite, export, copy, archive, delete, or share the result.

### Development Understanding

| Layer | Files |
| --- | --- |
| Routes | `app/api/routes/content.py` |
| Service | `app/services/content.py` |
| AI | `app/ai/orchestrator.py`, `app/ai/contracts.py`, `app/ai/context_compiler.py`, `app/ai/prompt_intelligence.py`, `app/ai/blueprint.py`, `app/ai/layout_decision.py`, `app/ai/session_memory.py`, `app/ai/tone_intelligence.py` |
| Providers | `app/ai/providers/*` |
| Rendering | `app/services/renderer.py` |
| Models | `app/models/content.py` |
| Traces | `app/services/generation_trace.py` |
| Frontend | `frontend/components/chat/WorkspaceChat.tsx`, `frontend/hooks/useContentWorkspace.ts` |

### Main Endpoints

- `POST /api/v1/content/generate`
- `POST /api/v1/content/rewrite`
- `POST /api/v1/content/tone-check`
- `GET /api/v1/content/history`
- `GET /api/v1/content/{content_id}`
- `POST /api/v1/content/export`
- `POST /api/v1/content/copy`
- `POST /api/v1/content/{content_id}/archive`
- `DELETE /api/v1/content/{content_id}`

### Generation Inputs

- Prompt.
- Studio panel.
- Brand Space scope.
- Optional persona and objective.
- Optional template.
- Optional reference assets.
- Image generation flag.
- Session context where applicable.

### Generation Outputs

- `generated_payload`: headline, body, CTA, hashtags, and metadata.
- `blueprint_payload`: renderer-facing layout contract.
- `generation_decision`: mode, selected template, rationale, scores, and adaptation hints.
- `explainability_metadata`: context, decisions, traces, validation, assets, and provider metadata.
- `tone_feedback` and tone score.
- Asset references for generated or rendered files.

### Important Development Rule

The shared AI payload fields are contract-sensitive. Preserve fields such as `sample_page_blueprint`, `module_counts`, `visual_permissions`, `carousel_slide_specs`, `visual_focus`, `image_zones`, and `blueprint_payload` unless every consumer is intentionally updated.

## 8. Chat Tool

### User Understanding

The Chat tool lets users interact conversationally with the generation system. Chat sessions preserve prompt history and can generate linked content versions.

### User Workflow

1. User creates or opens a chat session.
2. User sends a message with studio settings.
3. Backend classifies the message intent.
4. Backend chooses a conversational reply, strategy reply, text-only deliverable, visual/content generation, evaluation, retrieval, or mixed-workflow path.
5. Backend creates user and assistant messages.
6. Assistant response can include generated content, text-only output, evaluation scorecards, assets, and references.
7. User can rename/delete sessions or cancel generation.

### Development Understanding

| Layer | Files |
| --- | --- |
| Routes | `app/api/routes/chat.py` |
| Service | `app/services/chat.py`, `app/services/content.py`, `app/services/chat_cancellation.py`, `app/services/conversation.py`, `app/services/text_content.py`, `app/services/evaluation.py`, `app/services/intent_router.py`, `app/services/mixed_workflow.py`, `app/services/conversation_memory.py`, `app/services/brand_summary_memory.py` |
| Models | `app/models/content.py` |
| Schemas | `app/schemas/chat.py` |
| Frontend | `frontend/components/chat/WorkspaceChat.tsx`, `frontend/hooks/useContentWorkspace.ts` |

### Main Endpoints

- `POST /api/v1/chat/sessions`
- `GET /api/v1/chat/sessions`
- `PATCH /api/v1/chat/sessions/{session_id}`
- `DELETE /api/v1/chat/sessions/{session_id}`
- `POST /api/v1/chat/sessions/{session_id}/cancel`
- `GET /api/v1/chat/sessions/{session_id}/messages`
- `POST /api/v1/chat/sessions/{session_id}/messages`
- `DELETE /api/v1/chat/messages/{message_id}`

### Expected User Output

- Session list.
- Paginated messages.
- Generated assistant message linked to content version.
- Conversational or strategy response when no generation is needed.
- Text-only deliverable when the user asks for copy rather than a visual.
- Evaluation/review response when the user asks to assess prior content or selected assets.
- Retrieval-style response when the user asks to inspect or reuse available uploaded material.
- Cancel/delete confirmation where applicable.

### Chat Intent Modes

| Mode | User Meaning | Main Development Path |
| --- | --- | --- |
| Small talk | User greets or asks a simple conversational question. | `IntentRouterService` routes to `ConversationService`. |
| Strategy chat | User asks for advice, brainstorming, or planning. | `ConversationService` with brand summary and recent memory. |
| Content only | User asks for copy such as a post, blog, email, caption, thread, newsletter, script, or description. | `TextContentService`. |
| Visual generation | User asks for a static, carousel, infographic, poster, thumbnail, or other visual creative. | `ContentService` and `AIOrchestratorService`. |
| Evaluation | User asks to review, score, or assess prior content or assets. | `EvaluationService` and tone/asset review helpers. |
| Retrieval | User asks to find or reference uploaded material. | Chat service memory, asset delivery, and retrieval helpers. |
| Mixed workflow | User asks to apply a prior review, repurpose text into a visual, or continue from previous output. | `MixedWorkflowService` plus content/text/evaluation services. |

## 9. Rendering and Export Tool

### User Understanding

The Rendering and Export tool turns generated content, visual plans, templates, images, and brand assets into preview and export files.

### User Workflow

1. User clicks preview/export or generation returns render assets.
2. Backend resolves content, assets, logo, template metadata, blueprint, and studio panel.
3. Renderer or AI-final-render export path creates files.
4. Frontend receives preview and export asset references.

### Development Understanding

| Layer | Files |
| --- | --- |
| Routes | `app/api/routes/render.py`, `app/api/routes/content.py` |
| Services | `app/services/renderer.py`, `app/services/content.py`, `app/services/asset_delivery.py` |
| Contracts | `app/ai/contracts.py` |
| Models | `app/models/content.py` |
| Storage | `app/integrations/object_storage.py` |

### Main Endpoints

- `POST /api/v1/render/layout`
- `POST /api/v1/render/preview`
- `POST /api/v1/render/export`
- `GET /api/v1/render/{content_id}/status`
- `POST /api/v1/content/export`

### Expected User Output

- Preview image asset.
- Export assets in requested file type where supported.
- Renderer metadata including page count, manifest, template, logo, scene graph, and asset paths where available.

## 10. Review Tool

### User Understanding

The Review tool lets authenticated users share generated content through a tokenized review link. External reviewers can view content, add comments, and update status when allowed.

### User Workflow

1. User creates a share link for generated content.
2. Reviewer opens review URL.
3. Reviewer views shared content and assets.
4. Reviewer comments or changes review status.

### Development Understanding

| Layer | Files |
| --- | --- |
| Routes | `app/api/routes/review.py` |
| Service | `app/services/review.py` |
| Repository | `app/repositories/collaboration.py` |
| Models | `app/models/collaboration.py` |
| Schemas | `app/schemas/review.py` |
| Frontend | `frontend/app/review/[token]/page.tsx`, `frontend/components/sharing/ShareReviewScreen.tsx` |

### Main Endpoints

- `POST /api/v1/review/share-link`
- `GET /api/v1/review/{token}`
- `POST /api/v1/review/{token}/comment`
- `POST /api/v1/review/{token}/status`

### Expected User Output

- Share token.
- Review detail payload with content and comments.
- Comment and status updates.

## 11. Folder Tool

### User Understanding

The Folder tool lets users organize generated content inside a Brand Space.

### Development Understanding

| Layer | Files |
| --- | --- |
| Routes | `app/api/routes/folder.py` |
| Service | `app/services/folder.py` |
| Repository | `app/repositories/content.py` |
| Models | `app/models/content.py` |
| Schemas | `app/schemas/folder.py` |

### Main Endpoints

- `POST /api/v1/folders`
- `GET /api/v1/folders`
- `PUT /api/v1/folders/{folder_id}`
- `DELETE /api/v1/folders/{folder_id}`
- `POST /api/v1/folders/move`

### Expected User Output

- Folder list and folder detail.
- Rename/delete confirmation.
- Content moved into a folder.

## 12. Social Tool

### User Understanding

The Social tool stores social connection records and prepares publish requests for generated content. Current behavior prepares and validates publish requests; it is not a complete live network posting implementation.

### Development Understanding

| Layer | Files |
| --- | --- |
| Routes | `app/api/routes/social.py` |
| Service | `app/services/social.py` |
| Models | `app/models/collaboration.py` |
| Schemas | `app/schemas/social.py` |
| Security | `app/core/crypto.py` |

### Main Endpoints

- `GET /api/v1/social/list`
- `POST /api/v1/social/connect`
- `POST /api/v1/social/publish`
- `POST /api/v1/social/disconnect`

### Expected User Output

- Connected account records.
- Encrypted credential persistence.
- Publish request payload and status.
- Disconnect confirmation.

## 13. Analytics Tool

### User Understanding

The Analytics tool gives platform, tenant, Brand Space, and usage summaries.

### Development Understanding

| Layer | Files |
| --- | --- |
| Routes | `app/api/routes/analytics.py` |
| Service | `app/services/analytics.py` |
| Models | `app/models/collaboration.py`, `app/models/content.py`, tenant and brand models |
| Schemas | `app/schemas/analytics.py` |
| Frontend | `frontend/app/(mainContent)/analytics/page.tsx`, `frontend/components/platformOwner/PlatformOwnerAnalytics.tsx` |

### Main Endpoints

- `GET /api/v1/analytics/platform`
- `GET /api/v1/analytics/tenant`
- `GET /api/v1/analytics/brand/{brand_id}`
- `GET /api/v1/analytics/usage-summary`

### Expected User Output

- Metrics payload by requested scope.
- Usage and token telemetry where persisted.
- Tenant and Brand Space level activity summaries.

## 14. Jobs and Worker Tool

### User Understanding

Jobs represent background processing tasks. Users may see them indirectly as upload processing, template analysis, or evaluation status.

### Development Understanding

| Layer | Files |
| --- | --- |
| Routes | `app/api/routes/jobs.py` |
| Service | `app/services/jobs.py` |
| Worker | `app/workers/runner.py`, `scripts/run_worker.py` |
| Models | `app/models/collaboration.py` |
| Schemas | `app/schemas/job.py` |

### Main Endpoints

- `GET /api/v1/jobs/list`
- `GET /api/v1/jobs/{job_id}/status`

### Worker Responsibilities

- Claim queued jobs.
- Maintain heartbeat while processing.
- Dispatch knowledge processing.
- Dispatch template analysis.
- Dispatch optional RAGAS evaluation jobs.
- Mark jobs succeeded, failed, cancelled, or retryable.

### Expected User Output

- Job status.
- Retry count and error message when failed.
- Result payload when succeeded.

## 15. Storage and Asset Delivery Tool

### User Understanding

The Storage tool gives frontend users access to uploaded, generated, rendered, and exported files through asset URLs or download requests.

### Development Understanding

| Layer | Files |
| --- | --- |
| Routes | `app/api/routes/storage.py` |
| Services | `app/services/asset_delivery.py` |
| Integration | `app/integrations/object_storage.py` |
| Models | `app/models/content.py`, `app/models/knowledge.py` |

### Main Endpoint

- `GET /api/v1/storage/download`

### Expected User Output

- Downloadable file response for valid stored assets.
- Asset URLs in content, template, knowledge, and attachment responses where available.

## AI Pipeline Behind The Tools

The user experiences the AI pipeline through content generation, chat, templates, brand assets, and rendering. Development-wise, the pipeline crosses several layers:

1. `ContentService` prepares request context.
2. `DataValidatorService` refreshes resolved Brand Space context.
3. `KnowledgeService` and retrieval return relevant evidence.
4. `TemplateService` and `LayoutDecisionEngine` prepare template/layout decisions.
5. `SessionMemoryPlanner` handles continuation or rewrite context.
6. `AIOrchestratorService` builds structured generation response.
7. Provider adapters call configured text/image providers or fallbacks.
8. `RendererService` or AI-final-render delivery prepares preview/export assets.
9. `GenerationTraceService` writes trace payloads for debugging.
10. `ContentService` persists content versions and generated assets.

## Internal Support Modules

These modules are important to development understanding but are not always visible as separate user tools.

| Module | Role |
| --- | --- |
| `ConversationService` | Produces natural non-generation chat replies using brand summary and recent messages. |
| `ConversationMemoryService` | Persists and retrieves chat/session memory used by later responses. |
| `BrandSummaryMemoryService` | Builds compact brand summaries for chat and continuity. |
| `IntentRouterService` | Classifies a chat request into small talk, strategy, content-only, visual generation, evaluation, retrieval, or mixed workflow. |
| `TextContentService` | Generates text-only deliverables and supports review/evaluation helpers. |
| `EvaluationService` | Scores or reviews text and selected assets, then produces structured scorecards and findings. |
| `MixedWorkflowService` | Carries review results, prior text, and prior assets into follow-up generation workflows. |
| `ContentFormatGuideService` | Supplies format-specific content guidance to generation. |
| `ContentPlanningService` | Builds compact copy/content plans for format-aware generation. |
| `FormatFamilyPlanningService` | Determines format-family planning hints for static, carousel, infographic, and related surfaces. |
| `ResearchEditorialPlanningService` | Converts prompt, research, and knowledge into editorial planning metadata. |
| `LiveResearchService` | Performs configured live research when generation needs current or factual context. |
| `VisualPlanningService` | Builds visual planning metadata from prompt, research, and format context. |
| `BrandScoringService` | Scores generated output against brand, prompt, and image relevance signals. |
| `GenerationTraceService` | Writes trace payloads and cost/debug artifacts for generation and render diagnostics. |
| `ArtifactStateService` | Tracks useful generated or reviewed artifacts across chat workflows. |

## User-Facing Output Fields To Know

| Field | User Meaning | Developer Meaning |
| --- | --- | --- |
| `generated_payload` | The generated copy and metadata. | Structured text payload from the AI pipeline. |
| `blueprint_payload` | Layout information for preview/export. | Renderer-facing placement contract. |
| `generation_decision` | Why a template/layout/generation path was chosen. | Layout and creative decision metadata. |
| `explainability_metadata` | Debug and decision context. | Traceable AI, retrieval, render, validation, and provider metadata. |
| `assets` | Files the user can preview, export, or download. | Stored generated/rendered asset records. |
| `tone_feedback` | Brand/tone quality feedback. | Tone evaluation result. |
| `renderer_metadata` | Export/render details. | Render manifest and output metadata. |

## Operational Notes For Developers

- Run the API and worker together when testing uploads, template analysis, and background processing.
- Preserve storage and vector-store data when testing persistence-sensitive flows.
- Use generation traces when debugging AI quality or render failures.
- Treat provider fallback output as degraded behavior, even when responses are structurally valid.
- Keep route handlers thin and add business logic in services.
- Keep provider SDK details inside provider adapters.
- Keep shared AI fields stable and prefer additive metadata.

## Quick Verification Matrix

| Tool | Basic Verification |
| --- | --- |
| Auth | Login, profile read, 2FA status. |
| Tenant | Create/list tenant, create/list user, usage summary. |
| Brand Space | Create brand, update section, validate, publish. |
| Attachments | Upload file, watch job, list attachment, inspect validation. |
| Knowledge | Upload, process, list, reprocess/delete. |
| Template | Upload, detail, recommend. |
| Content | Generate, history, detail, export. |
| Chat | Create session, send message, list messages, cancel/delete. |
| Review | Create link, open token, comment, update status. |
| Analytics | Query platform/tenant/brand/usage endpoints. |
| Jobs | Confirm queued jobs become succeeded or failed with useful messages. |
| Storage | Download a known stored asset. |
