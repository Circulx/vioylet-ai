from app.graph.state import ViolytState
from app.graph.models.layer7_models import CopyOutput, CopySlide


async def layer7_copy_engine(state: ViolytState) -> dict:
    fmt = state.get("format", "static")
    format_plan = state.get("format_plan")
    slide_plan = format_plan.slide_plan if format_plan else []

    if fmt == "static":
        headline = "Predictability is a power, not a limitation."
        body = "Bonds can bring calm to a portfolio built for the long term."
        cta = "Explore fixed income strategies."
    else:
        headline = "What if boring was your edge?"
        body = "A closer look at why predictable income matters more than ever."
        cta = "Learn more"

    slide_copy = [
        CopySlide(
            slide_number=s.slide_number,
            headline=f"Slide {s.slide_number}: {s.role}",
            supporting_line=s.focus,
            body=f"Copy intent: {s.copy_intent}",
            cta="Next" if s.role != "cta" else cta,
        )
        for s in slide_plan
    ]
    if not slide_copy:
        slide_copy = [
            CopySlide(slide_number=1, headline=headline, body=body, cta=cta),
        ]

    return {
        "copy": CopyOutput(
            headline=headline,
            supporting_line="Calm, credible, and built for the long term.",
            body=body,
            cta=cta,
            hashtags=["#FixedIncome", "#Bonds", "#Investing"],
            slide_copy=slide_copy,
            claim_safety_notes=["Verify yield claims before publishing."],
        )
    }
