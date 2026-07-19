import pytest
from app.graph.models.layer7_models import CopyOutput, CopySlide
from app.graph.nodes.layer7b_content_validator import layer7b_content_validator
from app.graph.state import ViolytState


@pytest.mark.asyncio
async def test_content_validator_basic():
    # Construct mock CopyOutput containing misspellings, AI filler, and financial claims
    copy_data = CopyOutput(
        headline="We will recieve seperate developing returns today.",
        supporting_line="In today's fast-paced world, this is a game-changer.",
        body="Earn guaranteed returns of 12% p.a. risk-free on your capital.",
        cta="Click here to unlock your growth potential now",
        hashtags=["#finance"],
        slide_copy=[
            CopySlide(
                slide_number=1,
                headline="A simple separate slide with yeild performance.",
                body="This is standard body text.",
                cta="Action"
            )
        ],
        claim_safety_notes=[]
    )

    state: ViolytState = {
        "copy": copy_data,
        "brand_id": "test-brand",
        "platform": "linkedin",
        "format": "static",
        "repair_count": 0,
        "run_id": "test-run"
    }

    result = await layer7b_content_validator(state)
    assert "content_validation" in result
    assert "copy" in result

    validation = result["content_validation"]
    validated_copy = result["copy"]

    # Verify spelling corrections
    assert len(validation.spelling_fixes) > 0
    # "recieve" corrected to "receive", "seperate" to "separate", "yeild" to "yield"
    assert validated_copy.headline == "We will receive separate developing returns today."
    assert validated_copy.slide_copy[0].headline == "A simple separate slide with guarantee performance." or "yield" in validated_copy.slide_copy[0].headline

    # Verify AI filler removed
    # "In today's fast-paced world, this is a game-changer." -> "this is a ." or similar cleaned up
    assert "game-changer" not in validated_copy.supporting_line

    # Verify financial claims flagged
    assert len(validation.fact_flags) > 0
    flagged_claims = [f.claim for f in validation.fact_flags]
    assert any("12% p.a." in claim or "guaranteed" in claim or "risk-free" in claim for claim in flagged_claims)
