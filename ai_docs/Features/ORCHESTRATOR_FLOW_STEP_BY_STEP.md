# AI Orchestrator Flow Step by Step

**File explained:** `app/ai/orchestrator.py`

This document explains how `AIOrchestratorService` works in execution order.

It is written as a flow, not as a random function list.

## Before The Orchestrator Starts

The orchestrator does not receive raw frontend input directly.

Before `AIOrchestratorService` runs, `ContentService.generate()` prepares an `AIOrchestrationRequest`.

That request contains:

- tenant id
- Brand Space id
- user id
- user prompt
- Studio Panel settings
- resolved brand context
- persona context
- objective context
- retrieved knowledge
- template context
- reference assets
- asset catalog
- logo asset candidates
- layout decision
- content plan
- visual plan
- live research
- format family plan

Pipeline before orchestrator:

```text
Frontend / Chat
-> API route
-> ContentService.generate()
-> AIOrchestrationRequest
-> AIOrchestratorService.generate()
```

## Step 1: Enter The Orchestrator

### Function

```python
generate(request)
```

### What happens

`generate()` is the public entry point.

It receives the prepared request and starts orchestration.

### Why it matters

Every normal AI generation request enters through this function.

### Flow

```text
ContentService.generate()
-> AIOrchestratorService.generate()
```

## Step 2: Select Generation Strategy

### Main functions

```python
_select_generation_strategy_for_request()
select_generation_engine()
```

### What happens

The orchestrator decides which generation path should run.

It checks:

- requested format
- whether sample creative exists
- whether template exists
- whether template is pinned
- whether auto template selection is active

### Possible strategies

```python
MAIN_AI
DEV1_HARI
TEMPLATE_ADAPTANCE
CONTENT_INTELLIGENCE
WITHOUT_REFERENCE
```

### Simple behavior

```text
No sample and no template
-> WITHOUT_REFERENCE

Static or infographic with reference/sample
-> DEV1_HARI

Carousel with pinned template
-> TEMPLATE_ADAPTANCE

Carousel with auto template selection
-> CONTENT_INTELLIGENCE

Default
-> MAIN_AI
```

### Why it matters

This choice changes how strongly the AI follows templates, samples, carousel planning, and image-led rendering.

## Step 3: Dispatch To The Selected Path

### Function

```python
_dispatch_generation_strategy()
```

### What happens

The selected strategy is routed to the correct internal generation method.

### Flow

```text
generate()
-> _select_generation_strategy_for_request()
-> _dispatch_generation_strategy()
```

### Possible next functions

```python
_generate_main_ai()
_generate_template_adaptance()
_generate_content_intelligence()
```

## Step 4: Run The Selected Generation Engine

## Step 4A: Main AI Path

### Function

```python
_generate_main_ai()
```

### When it runs

This is the default generation path.

### What it does

It performs the full AI workflow:

- compile context
- resolve conflicts
- build prompt
- call text provider
- normalize text
- normalize metadata
- validate content semantics
- build scene graph
- validate scene graph
- build blueprint
- select references
- generate images/final render assets if needed
- return `AIOrchestrationResponse`

### Flow

```text
_dispatch_generation_strategy()
-> _generate_main_ai()
```

## Step 4B: Template Adaptation Path

### Function

```python
_generate_template_adaptance()
```

### When it runs

This runs when a template or sample reference must strongly guide the output.

### What it does

It focuses on:

- preserving selected template influence
- following sample layout behavior
- respecting `sample_page_blueprint`
- respecting `module_counts`
- respecting `visual_permissions`
- keeping carousel slide specs aligned with selected references

### Flow

```text
_dispatch_generation_strategy()
-> _generate_template_adaptance()
```

## Step 4C: Content Intelligence Path

### Function

```python
_generate_content_intelligence()
```

### When it runs

This is mainly for carousel flows where auto template/content planning is active.

### What it does

It focuses on:

- story progression
- slide roles
- content-specific visual focus
- carousel semantics
- avoiding template-only generic output

### Flow

```text
_dispatch_generation_strategy()
-> _generate_content_intelligence()
```

## Step 5: Compile And Resolve Context

### Main services used

```python
ContextCompilerService
ContextResolutionService
BrandIntelligenceService
```

### What happens

The orchestrator prepares the context for AI.

It reduces noisy backend data into useful instructions.

Context can include:

- brand identity
- tone
- guardrails
- audience
- personas
- objectives
- retrieved knowledge
- visual identity
- logo rules
- template metadata
- reference assets
- live research
- content plan
- visual plan

### Why it matters

The AI should not guess from raw database payloads. It needs a compact, resolved, high-signal context.

### Flow

```text
_generate_main_ai()
-> compile context
-> resolve conflicts
```

## Step 6: Build Text Prompt

### Main service/function

```python
PromptIntelligenceService
```

### What happens

The orchestrator builds the prompt envelope for the text model.

The prompt tells the model:

- what to generate
- which brand rules to follow
- which format to use
- what JSON structure to return
- what claims are allowed
- what visual metadata is required
- what to avoid

### Why it matters

Bad prompt structure creates bad or unusable AI output.

### Flow

```text
compiled context
-> PromptIntelligenceService
-> text prompt envelope
```

## Step 7: Call Text Provider

### Main service

```python
ProviderRouter
```

### Possible providers

```python
OpenAITextProvider
AnthropicTextProvider
```

### What happens

The orchestrator asks `ProviderRouter` for the configured text provider.

Then it requests structured JSON/text from the provider.

### Why it matters

The provider returns the first AI-generated structured payload.

### Flow

```text
text prompt envelope
-> ProviderRouter
-> OpenAITextProvider or AnthropicTextProvider
-> raw model response
```

## Step 8: Normalize Text Payload

### Function

```python
normalize_text_payload()
```

### What happens

The raw model response is cleaned into the expected structure.

Expected structure:

```json
{
  "headline": "...",
  "body": "...",
  "cta": "...",
  "hashtags": [],
  "metadata": {}
}
```

### It fixes

- missing fields
- malformed payloads
- invalid text
- prompt echo
- inconsistent metadata shape

### Flow

```text
raw model response
-> normalize_text_payload()
```

## Step 9: Normalize Metadata

### Function

```python
normalize_metadata_payload()
```

### What happens

The metadata inside the text payload is cleaned and stabilized.

Important metadata fields include:

- `carousel_slide_specs`
- `visual_focus`
- `proof_points`
- `stat_highlights`
- `claim_evidence_pairs`
- `static_panel_spec`
- `infographic_section_specs`

### Why it matters

The later visual pipeline depends on metadata. If metadata is weak, the image and scene graph become weak.

### Flow

```text
normalize_text_payload()
-> normalize_metadata_payload()
```

## Step 10: Repair Prompt Echo

### Function

```python
_repair_prompt_echo_text_payload()
```

### What happens

The orchestrator checks if the model simply repeated the user prompt instead of writing real content.

Example bad output:

```text
Create a LinkedIn carousel about investment mistakes
```

Instead of:

```text
5 mistakes that quietly weaken your investment plan
```

### Why it matters

Prompt echo looks like broken generation to the user.

### Flow

```text
normalized text
-> _repair_prompt_echo_text_payload()
```

## Step 11: Validate Content Semantics

### Function

```python
_validate_content_semantics()
```

### What happens

The orchestrator checks whether the generated content actually satisfies the prompt and format.

It checks:

- weak headline
- missing support points
- repeated carousel slides
- unsupported exact claims
- fake chart/table risk
- weak CTA
- missing evidence section
- poor infographic sectioning
- weak visual focus

### Why it matters

This prevents fluent but incorrect output.

### Flow

```text
normalized + repaired text
-> _validate_content_semantics()
```

## Step 12: Repair Text Semantics If Needed

### Function

```python
_repair_text_payload_semantics_if_needed()
```

### What happens

If semantic validation fails, the orchestrator creates a targeted repair instruction and asks the model to fix the payload.

It then normalizes and validates again.

### Flow

```text
_validate_content_semantics()
-> if failed
-> _repair_text_payload_semantics_if_needed()
-> normalize_text_payload()
-> _validate_content_semantics()
```

### Why it matters

This improves weak content before visual generation begins.

## Step 13: Build Carousel Slide Specs If Needed

### Main functions

```python
_build_carousel_slide_specs()
_sanitize_carousel_slide_specs()
_fallback_carousel_slide_specs()
_validate_carousel_semantic_progression()
```

### What happens

If the output is a carousel, the orchestrator builds a slide-by-slide plan.

Each slide can include:

- slide index
- story role
- headline
- body points
- CTA
- visual focus
- representation plan
- render execution contract

### Why it matters

Carousel output needs progression, not random slides.

### Flow

```text
metadata
-> _build_carousel_slide_specs()
-> _sanitize_carousel_slide_specs()
-> _validate_carousel_semantic_progression()
```

## Step 14: Build Or Normalize Scene Graph

### Main functions

```python
normalize_scene_graph_payload()
_fallback_scene_graph()
_fallback_image_led_scene_graph()
```

### What happens

The orchestrator creates or cleans a `GenerationSceneGraph`.

Scene graph contains:

- canvas
- layers
- elements
- geometry
- text
- visual assets
- style
- validation hints

### Why it matters

Scene graph is the structured visual plan for rendering/export/image-led generation.

### Flow

```text
AI scene graph response
-> normalize_scene_graph_payload()
-> fallback scene graph if needed
```

## Step 15: Validate Scene Graph

### Function

```python
validate_scene_graph()
```

### What happens

The orchestrator checks if the scene graph is safe and usable.

It checks:

- missing required elements
- geometry outside canvas
- text/logo collisions
- palette safety
- asset binding safety
- layout risks

### Flow

```text
normalized scene graph
-> validate_scene_graph()
```

### If validation fails

The orchestrator may:

- repair scene graph
- request a fresh replan
- use fallback scene graph
- ignore scene graph for final render if safer

## Step 16: Build Blueprint

### Main service

```python
BlueprintService
```

### What happens

The orchestrator builds a `BlueprintPayload`.

Blueprint contains:

- layout type
- zones
- hierarchy
- text blocks
- image zones
- logo rules
- CTA placement
- platform preset
- export format
- source mode
- adaptation plan
- composition plan

### Why it matters

`blueprint_payload` is a shared contract used by downstream content/export/render flows.

### Flow

```text
scene graph + text payload + layout decision
-> BlueprintService
-> blueprint_payload
```

## Step 17: Select Reference Images

### Main functions

```python
_select_reference_image_assets()
_conditioning_reference_image_assets()
_layout_analysis_reference_image_assets()
_filter_logo_bearing_conditioning_reference_images()
```

### What happens

The orchestrator decides which reference assets are useful and safe.

It separates:

- selected references
- safe conditioning references
- layout-only references
- logo-bearing references to skip
- text-heavy references to avoid

### Why it matters

Bad reference images can cause the AI to copy wrong text, wrong layout, or fake logos.

### Flow

```text
request.reference_assets
-> _select_reference_image_assets()
-> _conditioning_reference_image_assets()
-> image/final render prompt
```

## Step 18: Apply Logo Safety

### Main functions

```python
_brand_logo_placement_policy()
_logo_safe_zone_guidance()
_select_logo_candidate_for_render()
```

### What happens

The orchestrator prepares logo safety rules.

It tells AI:

- do not generate the logo
- reserve empty logo area
- do not put text in logo-safe zone
- exact logo will be overlaid later

### Why it matters

Brand logo must stay exact and should not be recreated by AI.

### Flow

```text
brand logo context
-> logo placement policy
-> logo safe zone guidance
-> prompt / scene graph / final render
```

## Step 19: Apply Data Visualization Safety

### Main functions

```python
_data_visualization_contract()
_data_list_surface_contract()
_data_visualization_has_content_anchor()
_numeric_data_visualization_requested()
```

### What happens

The orchestrator checks chart/table/data visual requests.

It prevents:

- fake numeric charts
- fake dashboards
- unsupported tables
- unbacked exact values

### Why it matters

If the prompt has no real numbers, the AI should not invent chart data.

### Flow

```text
prompt + metadata + proof points
-> data visualization checks
-> prompt safety instructions
```

## Step 20: Resolve Visual Treatment

### Main functions

```python
_resolve_visual_treatment_preference()
_normalize_structured_visual_metadata()
_dynamic_visual_art_direction_section()
```

### What happens

The orchestrator decides visual treatment.

Possible treatments include:

- 2D
- 3D
- isometric
- flat editorial
- product dashboard
- icon system
- photo composite
- document evidence
- data module
- brand-led

### Why it matters

This controls whether the output feels flat, 3D, data-driven, product-like, icon-led, etc.

### Flow

```text
prompt + metadata + brand assets + sample permissions
-> visual treatment preference
-> dynamic visual art direction
```

## Step 21: Build Image Prompt Or Final Render Prompt

### Normal image prompt

```python
build_image_prompt()
```

Used for supporting image generation.

### Final render prompt

```python
build_final_render_prompt()
```

Used when the AI should generate the final creative image.

### Carousel slide prompt

```python
build_carousel_slide_render_prompt()
```

Used for per-slide carousel rendering.

### What prompt includes

- final copy
- visual focus
- brand colors
- typography hints
- reference guidance
- logo-safe zone
- template/sample adaptation rules
- data visualization rules
- text containment rules
- quality floor

### Flow

```text
text + metadata + scene graph + references + logo rules
-> build_image_prompt()
or build_final_render_prompt()
or build_carousel_slide_render_prompt()
```

## Step 22: Generate Image Assets

### Main functions

```python
_generate_image_with_retries()
_generate_final_render_image_with_sample_guard()
render_final_assets_only()
```

### What happens

The orchestrator sends image prompts to the configured image provider.

It may generate:

- supporting AI image asset
- final render asset
- carousel slide assets
- infographic final render

### Retry behavior

If generation fails or quality is low, the orchestrator can retry.

### Flow

```text
image/final render prompt
-> image provider
-> generated image asset
```

## Step 23: Assess Final Render Quality

### Main functions

```python
_assess_final_render_output_image()
_append_final_render_output_quality_repair_prompt()
_append_sample_similarity_repair_prompt()
```

### What happens

The orchestrator checks whether the generated final render is acceptable.

It checks:

- topic fit
- visible text/claim risks
- requested structure
- data surface quality
- content/visual balance
- visual metaphor relevance
- sample similarity

### If quality is low

It creates a repair prompt and retries.

### Flow

```text
generated final render
-> quality assessment
-> repair prompt if needed
-> retry generation
```

## Step 24: Build Final Response

### Response model

```python
AIOrchestrationResponse
```

### Response contains

- `message_strategy`
- `text`
- `creative_decision`
- `scene_graph`
- `validation_report`
- `repair_attempts`
- `blueprint`
- `image_assets`
- `final_render_assets`
- `final_render_asset`
- `render_authority`
- `explainability`
- `tone_analysis`
- `generation_trace`

### Flow

```text
all generated outputs
-> AIOrchestrationResponse
-> ContentService
```

## Step 25: ContentService Persists Result

This is outside `orchestrator.py`, but it is the next pipeline step.

`ContentService` stores:

- `content_history.generated_payload`
- `content_history.blueprint_payload`
- `content_history.explainability_metadata`
- `generated_assets`

Then the frontend can display generated content and assets.

## Full Orchestrator Flow

```text
Frontend / Chat
  |
  v
API Route
  |
  v
ContentService.generate()
  |
  v
AIOrchestrationRequest
  |
  v
AIOrchestratorService.generate()
  |
  v
_select_generation_strategy_for_request()
  |
  v
_dispatch_generation_strategy()
  |
  +--> _generate_main_ai()
  |
  +--> _generate_template_adaptance()
  |
  +--> _generate_content_intelligence()
          |
          v
      Compile and resolve context
          |
          v
      Build text prompt
          |
          v
      Call text provider
          |
          v
      normalize_text_payload()
          |
          v
      normalize_metadata_payload()
          |
          v
      _repair_prompt_echo_text_payload()
          |
          v
      _validate_content_semantics()
          |
          +--> _repair_text_payload_semantics_if_needed()
          |
          v
      _build_carousel_slide_specs() if carousel
          |
          v
      normalize_scene_graph_payload()
          |
          v
      validate_scene_graph()
          |
          +--> fallback / repair / fresh replan if needed
          |
          v
      BlueprintService builds blueprint_payload
          |
          v
      _select_reference_image_assets()
          |
          v
      _conditioning_reference_image_assets()
          |
          v
      logo safety + data visualization safety + visual treatment
          |
          v
      build_image_prompt() or build_final_render_prompt()
          |
          v
      _generate_image_with_retries()
      or _generate_final_render_image_with_sample_guard()
          |
          v
      _assess_final_render_output_image()
          |
          +--> repair/retry if needed
          |
          v
      AIOrchestrationResponse
          |
          v
ContentService persists content and assets
```

## Most Important Contracts Protected In This Flow

These fields are shared with other features and should not be renamed or reshaped casually:

- `sample_page_blueprint`
- `module_counts`
- `visual_permissions`
- `carousel_slide_specs`
- `visual_focus`
- `image_zones`
- `blueprint_payload`

## Short Summary

The orchestrator works like this:

```text
Request
-> choose strategy
-> compile context
-> generate text
-> normalize text/metadata
-> validate and repair content
-> plan carousel if needed
-> build scene graph
-> validate scene graph
-> build blueprint
-> select references
-> apply logo/data/visual safety
-> build image prompt
-> generate final visual assets
-> assess and repair quality
-> return AIOrchestrationResponse
```

In simple words:

> `AIOrchestratorService` converts brand context, user prompt, templates, references, and knowledge into safe structured copy, visual planning, blueprint data, and AI-rendered assets.

