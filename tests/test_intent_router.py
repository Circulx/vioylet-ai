from app.services.intent_router import IntentRouterService


def _router_with_llm(monkeypatch, **payload) -> IntentRouterService:
    router = IntentRouterService()
    response = {
        "mode": "content_only",
        "confidence": 0.95,
        "reason": "test_intent",
        "deliverable_type": None,
        "uses_previous_output": False,
        "workflow_type": None,
        "revision_scope": None,
    }
    response.update(payload)
    monkeypatch.setattr(router, "_classify_with_llm", lambda **kwargs: response)
    return router


def test_intent_router_routes_greeting_to_small_talk(monkeypatch) -> None:
    router = _router_with_llm(monkeypatch, mode="small_talk", reason="greeting")
    decision = router.route("Hi")
    assert decision.mode == "small_talk"


def test_intent_router_routes_text_deliverable_to_content_only(monkeypatch) -> None:
    router = _router_with_llm(
        monkeypatch,
        mode="content_only",
        deliverable_type="linkedin_post",
        reason="text_deliverable",
    )
    decision = router.route("Write a LinkedIn post on bond duration risk.")
    assert decision.mode == "content_only"
    assert decision.deliverable_type == "linkedin_post"


def test_intent_router_routes_visual_request_to_visual_generation(monkeypatch) -> None:
    router = _router_with_llm(monkeypatch, mode="visual_generation", reason="visual_request")
    decision = router.route("Generate a LinkedIn carousel on bond mistakes.")
    assert decision.mode == "visual_generation"


def test_intent_router_routes_tone_review_to_evaluation(monkeypatch) -> None:
    router = _router_with_llm(
        monkeypatch,
        mode="evaluation",
        uses_previous_output=True,
        reason="evaluation_request",
    )
    decision = router.route("Check tone consistency: This copy feels too salesy.")
    assert decision.mode == "evaluation"


def test_intent_router_keeps_visual_follow_up_in_visual_mode(monkeypatch) -> None:
    router = _router_with_llm(
        monkeypatch,
        mode="visual_generation",
        uses_previous_output=True,
        reason="visual_follow_up",
    )
    decision = router.route(
        "Make slide 2 sharper and reduce the text.",
        {"last_response_mode": "visual_generation"},
    )
    assert decision.mode == "visual_generation"
    assert decision.uses_previous_output is True


def test_intent_router_treats_fresh_carousel_brief_as_new_generation_even_after_visual_turn(monkeypatch) -> None:
    router = _router_with_llm(
        monkeypatch,
        mode="visual_generation",
        uses_previous_output=False,
        reason="fresh_visual_generation_request",
    )
    decision = router.route(
        (
            "Write a LinkedIn carousel for Jiraaf on the India-New Zealand Free Trade Agreement. "
            "Length: 4-6 slides. Open with a hook that makes the reader swipe."
        ),
        {"last_response_mode": "visual_generation"},
    )

    assert decision.mode == "visual_generation"
    assert decision.uses_previous_output is False
    assert decision.reason == "llm_selected:fresh_visual_generation_request"


def test_intent_router_treats_standalone_brief_with_plain_language_it_as_new_generation(monkeypatch) -> None:
    router = _router_with_llm(
        monkeypatch,
        mode="visual_generation",
        uses_previous_output=False,
        reason="fresh_visual_generation_request",
    )
    decision = router.route(
        (
            "Write a LinkedIn carousel for Jiraaf, an Indian alternative investments platform, "
            "on the India-New Zealand Free Trade Agreement signed on 27 April 2026. "
            "Tone: conversational, analytical, intelligent. "
            "Angle: Go beyond the headline numbers. Look at how the deal is structured, "
            "what India negotiated, and why it matters strategically - not just what India gained."
        ),
        {"last_response_mode": "visual_generation"},
    )

    assert decision.mode == "visual_generation"
    assert decision.uses_previous_output is False
    assert decision.reason == "llm_selected:fresh_visual_generation_request"


def test_intent_router_treats_long_census_visual_brief_as_fresh_generation(monkeypatch) -> None:
    router = _router_with_llm(
        monkeypatch,
        mode="visual_generation",
        uses_previous_output=False,
        reason="fresh_visual_generation_request",
    )
    decision = router.route(
        (
            "Create a LinkedIn carousel post for Jiraaf on the topic: How Census 2027 could impact India's "
            "financial future. Keep it relevant for working professionals who are interested in wealth creation "
            "but may not track policy-level events closely. Structure it like a story: Start with a strong hook, "
            "explain what the census is simply, show why people ignore it, then connect it to money and end with "
            "a strong thought-provoking closing. Keep text short per slide."
        ),
        {"last_response_mode": "visual_generation"},
    )

    assert decision.mode == "visual_generation"
    assert decision.uses_previous_output is False
    assert decision.revision_scope is None
    assert decision.reason == "llm_selected:fresh_visual_generation_request"


def test_intent_router_keeps_text_follow_up_in_content_mode(monkeypatch) -> None:
    router = _router_with_llm(
        monkeypatch,
        mode="content_only",
        deliverable_type="linkedin_post",
        uses_previous_output=True,
        reason="content_rewrite_follow_up",
        revision_scope={
            "targeted_fields": [],
            "slide_indexes": [],
            "slide_targets": [],
            "preserve_visuals": False,
            "preserve_copy": False,
            "change_layout": False,
            "change_tone": True,
            "only_targeted": False,
        },
    )
    decision = router.route(
        "Rewrite this to sound more analytical.",
        {"last_response_mode": "content_only", "last_text_deliverable_type": "linkedin_post"},
    )
    assert decision.mode == "content_only"
    assert decision.uses_previous_output is True


def test_intent_router_extracts_text_revision_scope_for_cta_only(monkeypatch) -> None:
    router = _router_with_llm(
        monkeypatch,
        mode="content_only",
        deliverable_type="linkedin_post",
        uses_previous_output=True,
        reason="content_rewrite_follow_up",
        revision_scope={
            "targeted_fields": ["cta"],
            "slide_indexes": [],
            "slide_targets": [],
            "preserve_visuals": False,
            "preserve_copy": False,
            "change_layout": False,
            "change_tone": True,
            "only_targeted": True,
        },
    )
    decision = router.route(
        "Rewrite only the CTA and make it more analytical.",
        {"last_response_mode": "content_only", "last_text_deliverable_type": "linkedin_post"},
    )
    assert decision.mode == "content_only"
    assert decision.revision_scope is not None
    assert decision.revision_scope["targeted_fields"] == ["cta"]
    assert decision.revision_scope["only_targeted"] is True
    assert decision.revision_scope["change_tone"] is True


def test_intent_router_extracts_visual_revision_scope_for_slide_specific_follow_up(monkeypatch) -> None:
    router = _router_with_llm(
        monkeypatch,
        mode="visual_generation",
        uses_previous_output=True,
        reason="visual_follow_up",
        revision_scope={
            "targeted_fields": [],
            "slide_indexes": [3],
            "slide_targets": [],
            "preserve_visuals": True,
            "preserve_copy": False,
            "change_layout": False,
            "change_tone": False,
            "only_targeted": False,
        },
    )
    decision = router.route(
        "Make slide 3 sharper but keep the visuals the same.",
        {"last_response_mode": "visual_generation"},
    )
    assert decision.mode == "visual_generation"
    assert decision.revision_scope is not None
    assert decision.revision_scope["slide_indexes"] == [3]
    assert decision.revision_scope["preserve_visuals"] is True


def test_intent_router_preserves_true_visual_follow_up_reuse(monkeypatch) -> None:
    router = _router_with_llm(
        monkeypatch,
        mode="visual_generation",
        uses_previous_output=True,
        reason="visual_follow_up",
        revision_scope={
            "targeted_fields": [],
            "slide_indexes": [2],
            "slide_targets": [],
            "preserve_visuals": False,
            "preserve_copy": False,
            "change_layout": False,
            "change_tone": False,
            "only_targeted": False,
        },
    )
    decision = router.route(
        "Make slide 2 shorter and keep the same design.",
        {"last_response_mode": "visual_generation"},
    )

    assert decision.mode == "visual_generation"
    assert decision.uses_previous_output is True
    assert decision.revision_scope is not None
    assert decision.revision_scope["slide_indexes"] == [2]


def test_intent_router_routes_copy_to_carousel_as_mixed_workflow(monkeypatch) -> None:
    router = _router_with_llm(
        monkeypatch,
        mode="visual_generation",
        workflow_type="repurpose_text_to_visual",
        reason="repurpose_text_to_visual",
    )
    decision = router.route(
        "Turn it into a carousel for LinkedIn.",
        {"last_response_mode": "content_only", "last_text_deliverable_type": "linkedin_post"},
    )

    assert decision.mode == "visual_generation"
    assert decision.workflow_plan is not None
    assert decision.workflow_plan["type"] == "repurpose_text_to_visual"
    assert decision.uses_previous_output is False


def test_intent_router_routes_review_then_generate_as_mixed_workflow(monkeypatch) -> None:
    router = _router_with_llm(
        monkeypatch,
        mode="content_only",
        workflow_type="review_then_generate",
        reason="review_then_generate",
    )
    decision = router.route(
        "Review this document, then generate a LinkedIn post from it.",
        {},
    )

    assert decision.mode == "content_only"
    assert decision.workflow_plan is not None
    assert decision.workflow_plan["type"] == "review_then_generate"


def test_intent_router_allows_llm_to_promote_plain_chat_into_strategy_mode(monkeypatch) -> None:
    router = _router_with_llm(
        monkeypatch,
        mode="strategy_chat",
        reason="user_is_asking_for_advice_not_a_deliverable",
    )
    decision = router.route("I want to understand bond duration risk before we write anything.")

    assert decision.mode == "strategy_chat"
    assert decision.reason.startswith("llm_selected:")


def test_intent_router_allows_llm_to_select_retrieval(monkeypatch) -> None:
    router = _router_with_llm(
        monkeypatch,
        mode="retrieval",
        uses_previous_output=True,
        reason="user_is_asking_for_a_previous_generated_image",
    )
    decision = router.route("Can you show the image we created earlier?")

    assert decision.mode == "retrieval"
    assert decision.uses_previous_output is True
    assert decision.reason.startswith("llm_selected:")


def test_intent_router_allows_llm_to_select_evaluation(monkeypatch) -> None:
    router = _router_with_llm(
        monkeypatch,
        mode="evaluation",
        uses_previous_output=True,
        reason="user_is_asking_for_review_and_scoring",
    )
    decision = router.route(
        "Tell me whether this copy is aligned with the brand tone.",
        {"last_response_mode": "content_only"},
    )

    assert decision.mode == "evaluation"
    assert decision.uses_previous_output is True
    assert decision.reason.startswith("llm_selected:")
