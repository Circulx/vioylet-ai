from app.graph.state import ViolytState
from app.graph.models.layer4_models import StrategicReasoningOutput, RejectedApproach


async def layer4_strategic_reasoning(state: ViolytState) -> dict:
    return {
        "strategic_reasoning": StrategicReasoningOutput(
            strategic_problem="Bonds feel inaccessible and boring to modern investors.",
            brand_truth="Predictability is a form of power, not a limitation.",
            recommended_approach="Reframe predictable income as disciplined confidence.",
            rejected_approaches=[
                RejectedApproach(
                    approach_name="Generic safety pitch",
                    rejection_reason="Too interchangeable; lacks brand-specific tension.",
                ),
                RejectedApproach(
                    approach_name="Comparison chart first",
                    rejection_reason="Too rational; misses emotional reassurance.",
                ),
            ],
            attention_strategy="Challenge the assumption that predictable means boring.",
            emotional_strategy="Quiet confidence and financial maturity.",
            visual_strategy="Minimal editorial layout with data-forward accent.",
            content_pacing_strategy="Hook → insight → proof → CTA.",
        )
    }
