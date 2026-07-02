You are working in d:\Violyt-Ai.

Do not rewrite the generation pipeline broadly. Make small, targeted changes only.

Shared ownership boundary:
- Feature 1 owns sample layout adaptation consistency.
- Feature 2 owns dynamic 2D / 3D visual treatment using brand assets.
- Feature 3 owns frozen prompt/RAG output structure for tables, charts, and creativity signals.

Do not rename, remove, or reshape existing shared fields without calling it out first:
- sample_page_blueprint
- module_counts
- visual_permissions
- carousel_slide_specs
- visual_focus
- image_zones
- blueprint_payload

Prefer additive metadata over changing existing contracts.

If you touch app/ai/orchestrator.py, inspect nearby Feature 1 / Feature 2 / Feature 3 logic first and keep changes scoped.

Do not hardcode model names, paths, brand names, asset IDs, tenant IDs, URLs, or environment-specific values.

Before editing, identify:
1. Root cause
2. Smallest safe change
3. Files to change
4. Merge-risk with the other feature branch

After editing, list:
1. Files modified
2. Verification commands run
3. Remaining merge or behavior risks