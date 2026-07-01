# AI Orchestrator Flow: Image Generation Without Reference Images

This document explains only one path:

How the system generates an image when the user does not upload any reference image.

## Scope

This flow applies when:

- `generate_image` is `true`
- `reference_asset_ids` is empty
- no usable Brand Space reference creative is available
- no template/sample creative is required for the generation

In this case, the system still generates an image from text, brand context, planning metadata, and the generated content payload.

## Short Summary

No uploaded reference image does not block image generation.

Instead, the backend builds a detailed image prompt from:

- the user prompt
- the selected studio format
- brand context
- persona context
- objective context
- retrieved knowledge
- generated headline, body, CTA, and metadata
- visual planning rules
- layout and scene graph decisions

Then the image provider is called with a text prompt only.

## Step-By-Step Flow

## 1. Frontend Sends a Generation Request

The frontend sends a request similar to:

```json
{
  "prompt": "Create an Instagram post about retirement planning",
  "generate_image": true,
  "reference_asset_ids": []
}
```

The important parts are:

- `generate_image: true`
- `reference_asset_ids: []`

This means the user wants an image, but has not supplied any explicit reference image.

## 2. Content Service Resolves Requested Reference Assets

The backend first checks whether the user selected or uploaded reference assets.

Code location:

```text
app/services/content.py
_resolve_request_reference_assets(...)
```

Because `reference_asset_ids` is empty, the result is:

```python
request_reference_assets = []
```

## 3. Content Service Resolves Brand Reference Assets

Next, the backend checks the Brand Space context for existing visual assets.

Code location:

```text
app/services/content.py
_resolve_brand_reference_assets(...)
```

It looks for assets such as:

- reference creatives
- mood boards
- reusable design assets
- approved visual identity assets

If none are configured or usable, the result is:

```python
brand_reference_assets = []
```

## 4. Content Service Merges Reference Assets

The system merges requested assets and brand assets.

Code location:

```text
app/services/content.py
_merge_reference_assets_for_prompt(...)
```

In the no-reference case:

```python
reference_assets = []
```

This is allowed.

## 5. Content Service Calls the AI Orchestrator

The content service calls:

```python
self.orchestrator.generate(
    AIOrchestrationRequest(
        prompt=effective_prompt,
        reference_assets=tracked_reference_assets,
        asset_catalog=tracked_reference_assets,
        generate_image=effective_generate_image,
        ...
    )
)
```

For this flow, the orchestrator receives:

```python
reference_assets = []
asset_catalog = []
generate_image = True
```

## 6. Orchestrator Selects the No-Reference Strategy

The orchestrator checks whether a sample creative or template is available.

Code location:

```text
app/ai/orchestrator.py
select_generation_engine(...)
```

When there is no sample creative and no template:

```python
return GenerationStrategy.WITHOUT_REFERENCE
```

This strategy name can be misleading. It does not mean generation stops.

It means:

```text
Generate from prompt and context instead of from uploaded reference images.
```

## 7. No-Reference Strategy Routes to the Main AI Pipeline

Code location:

```text
app/ai/orchestrator.py
_dispatch_generation_strategy(...)
```

The no-reference branch does this:

```python
if strategy == GenerationStrategy.WITHOUT_REFERENCE:
    return self._generate_main_ai(request)
```

So the system continues into the normal generation pipeline.

## 8. Main AI Pipeline Builds Content and Visual Context

Inside `_generate_main_ai(...)`, the orchestrator builds the context needed for generation.

It uses:

- `request.prompt`
- `request.studio_panel`
- `request.resolved_brand_context`
- `request.persona_context`
- `request.objective_context`
- `request.retrieved_knowledge`
- `request.content_plan`
- `request.visual_plan`
- `request.layout_decision`

The system then creates or normalizes:

- message strategy
- generated headline
- generated body copy
- CTA
- proof points
- visual direction
- design style
- scene graph
- blueprint
- image prompt inputs

At this stage, uploaded reference images are not required because the visual idea is generated from text and brand intelligence.

## 9. Fallback Metadata Supplies a Visual Direction

If the model or planning step needs fallback visual metadata, the orchestrator has a safe default.

Example fallback metadata:

```python
{
    "visual_direction": "Premium brand-safe visual that explains the requested content with a clear, content-specific focal concept.",
    "design_style": "editorial brand campaign creative",
    "image_prompt": "Premium brand campaign visual with no text, built around the concrete idea in the user prompt."
}
```

This prevents the image path from depending on uploaded references.

## 10. Image Prompt Is Built From Text and Context

For normal image asset generation, the orchestrator builds a text prompt.

Code location:

```text
app/ai/orchestrator.py
build_image_prompt(...)
```

The prompt includes information such as:

- user request
- generated headline/body/CTA
- proof points
- stat highlights
- visual direction
- brand palette
- typography guidance
- layout decision
- visual explanation plan
- logo safe-area rules
- anti-hallucination rules

In the no-reference path, reference images are either empty or described as not authoritative.

The image model still receives a full text prompt.

## 11. Image Provider Generates From Text Only

The orchestrator calls:

```python
image_provider.generate(
    tenant_id=tenant_id,
    brand_space_id=brand_space_id,
    prompt=image_prompt,
    size=image_size,
)
```

Code location:

```text
app/ai/orchestrator.py
_generate_image_with_retries(...)
```

The key point:

```text
No image paths are passed here.
Only the text prompt is passed.
```

## 12. OpenAI Provider Calls Text-To-Image Generation

When OpenAI is configured, the provider calls:

```python
self.client.images.generate(
    prompt=prompt,
    **options,
)
```

Code location:

```text
app/ai/providers/openai_provider.py
OpenAIImageProvider.generate(...)
```

This is text-to-image generation.

It does not require a reference image.

## 13. Generated Image Is Stored

The generated image bytes are saved to object storage.

The provider returns a payload similar to:

```python
{
    "mime_type": "image/png",
    "storage_path": "...",
    "width": 1024,
    "height": 1024,
    "asset_role": "ai_image",
    "provider": "openai"
}
```

The orchestrator wraps this as a `GeneratedImageAsset`.

## 14. Generated Asset Is Returned

The generated image can appear in the response as:

```python
response.image_assets
```

or, for AI final-render formats:

```python
response.final_render_assets
```

## AI Final Render Path

For formats such as:

- static
- carousel
- infographic
- poster
- story

the system may use the AI final-render path.

In that path, the prompt is built by:

```text
app/ai/orchestrator.py
build_final_render_prompt(...)
```

Then final render generation calls:

```text
app/ai/orchestrator.py
_generate_final_render_image_with_sample_guard(...)
```

This function has two branches:

```python
if reference_image_paths:
    asset = self._edit_image_with_retries(...)
else:
    asset = self._generate_image_with_retries(...)
```

So when there are no reference image paths, it directly generates a new image from the final render prompt.

## Simple Flow Diagram

```text
User prompt
  |
  v
generate_image = true
reference_asset_ids = []
  |
  v
ContentService resolves requested reference assets
  |
  v
request_reference_assets = []
  |
  v
ContentService resolves brand reference assets
  |
  v
brand_reference_assets = []
  |
  v
Merge reference assets
  |
  v
reference_assets = []
  |
  v
AIOrchestrator.generate(...)
  |
  v
GenerationStrategy.WITHOUT_REFERENCE
  |
  v
_generate_main_ai(...)
  |
  v
Build text payload, metadata, layout, scene graph
  |
  v
Build image prompt from prompt + brand + content + visual plan
  |
  v
image_provider.generate(prompt=image_prompt)
  |
  v
OpenAI images.generate(prompt=...)
  |
  v
Generated PNG saved to storage
  |
  v
Generated asset returned to frontend
```

## Important Takeaway

The system does not need uploaded reference images to generate an image.

Uploaded reference images are used for visual grounding, style matching, or layout guidance.

When no reference image exists, the system switches to prompt-led generation:

```text
prompt + brand context + generated copy + visual plan -> image prompt -> generated image
```

That is why images can still be generated without any reference image upload.

