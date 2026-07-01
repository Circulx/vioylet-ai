from app.graph.state import ViolytState
from app.graph.models.layer5_models import CreativeConceptsOutput, Concept


async def layer5_concept_engine(state: ViolytState) -> dict:
    concepts = [
        Concept(
            concept_id="c1",
            concept_name="The Discipline Dividend",
            core_idea="Predictability is the reward of discipline.",
            hook="What if boring was your edge?",
            narrative_angle="Discipline creates compounding calm.",
            visual_angle="Clean chart rising quietly.",
            brand_fit_reason="Directly expresses the brand's calm-credible positioning.",
            risk_level="low",
        ),
        Concept(
            concept_id="c2",
            concept_name="Numbers That Don't Lie",
            core_idea="Bonds offer measurable predictability.",
            hook="Three numbers that change how you see income.",
            narrative_angle="Evidence over emotion.",
            visual_angle="Data visualization on neutral background.",
            brand_fit_reason="Matches data-forward visual behavior.",
            risk_level="medium",
        ),
        Concept(
            concept_id="c3",
            concept_name="Quiet Confidence",
            core_idea="Maturity beats noise in wealth building.",
            hook="The quietest portfolios often sleep the best.",
            narrative_angle="Emotional reassurance through restraint.",
            visual_angle="Soft negative space with a single focal point.",
            brand_fit_reason="Owns the emotional territory of trust.",
            risk_level="low",
        ),
    ]
    recommended = concepts[0]

    return {
        "creative_concepts": CreativeConceptsOutput(
            all_concepts=concepts,
            recommended_concept=recommended,
            selection_reason="Strongest brand-fit and lowest risk while still distinctive.",
            rejected_concepts=[],
            diversity_score=0.82,
        )
    }
