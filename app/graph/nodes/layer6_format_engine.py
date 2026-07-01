from app.graph.state import ViolytState
from app.graph.models.layer6_models import FormatPlanOutput, SlidePlan


async def layer6_format_engine(state: ViolytState) -> dict:
    fmt = state.get("format", "static")
    platform = state.get("platform", "linkedin")

    if fmt == "carousel":
        slide_plan = [
            SlidePlan(slide_number=1, role="hook", focus="challenge assumption", copy_intent="short provocative headline", visual_intent="bold minimal background"),
            SlidePlan(slide_number=2, role="insight", focus="predictability", copy_intent="one evidence sentence", visual_intent="clean chart accent"),
            SlidePlan(slide_number=3, role="proof", focus="bonds", copy_intent="supporting line", visual_intent="data point"),
            SlidePlan(slide_number=4, role="brand truth", focus="maturity", copy_intent="brand statement", visual_intent="logo safe zone"),
            SlidePlan(slide_number=5, role="cta", focus="next step", copy_intent="clear CTA", visual_intent="button-like element"),
        ]
    elif fmt == "infographic":
        slide_plan = [
            SlidePlan(slide_number=1, role="title", focus="main insight", copy_intent="headline + subhead", visual_intent="hierarchy top"),
            SlidePlan(slide_number=2, role="body", focus="data breakdown", copy_intent="bullet insights", visual_intent="data visuals"),
            SlidePlan(slide_number=3, role="cta", focus="close", copy_intent="CTA", visual_intent="bottom lockup"),
        ]
    else:
        slide_plan = [
            SlidePlan(slide_number=1, role="single", focus="one message", copy_intent="headline + supporting line + CTA", visual_intent="single focal visual"),
        ]

    return {
        "format_plan": FormatPlanOutput(
            format_strategy=f"{fmt}-native structure for {platform}",
            content_structure="hook → insight → proof → CTA" if fmt != "static" else "single message hierarchy",
            copy_density="medium",
            visual_density="medium",
            layout_archetype="editorial minimal",
            slide_plan=slide_plan,
            notes="Format plan generated from strategic reasoning.",
        )
    }
