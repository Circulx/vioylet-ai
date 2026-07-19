import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import asyncio
from PIL import Image
from app.services.renderer import RendererService
from app.ai.contracts import RendererInput, BlueprintPayload, BlueprintZone, StructuredTextPayload

async def main():
    # Instantiate RendererService with None session (mock DB session)
    renderer = RendererService(session=None)
    
    # We want a 1080x1350 canvas for LinkedIn portrait infographic
    size = {"width": 1080, "height": 1920}
    
    # Construct RendererInput payload
    payload = RendererInput(
        tenant_id="11111111-1111-1111-1111-111111111111",
        brand_space_id="1eeb4475-24ca-41dd-8cad-80bb50e0ca74",
        content_version_id="33333333-3333-3333-3333-333333333333",
        studio_panel={
            "format": "infographic",
            "platform_preset": "linkedin",
            "file_type": "png",
            "size": size
        },
        blueprint=BlueprintPayload(
            layout_type="infographic",
            zones=[
                BlueprintZone(zone_id="headline", role="headline", x=0, y=0, width=100, height=100, max_lines=3),
                BlueprintZone(zone_id="body", role="body", x=0, y=100, width=100, height=100, max_lines=7),
                BlueprintZone(zone_id="cta", role="cta", x=0, y=200, width=100, height=50, max_lines=2),
            ],
            hierarchy=["headline", "body", "cta"],
            text_blocks=[],
            image_zones=[],
            logo_rules={},
            cta_placement={"alignment": "left"},
            platform_preset="linkedin",
            export_format="png",
            overflow_strategy={"mode": "shrink_then_wrap"},
        ),
        text=StructuredTextPayload(
            headline="Why Every Portfolio Needs Bonds",
            body="Figures shown are indicative. Actual results may vary. Read all risk related documents carefully.",
            cta="Build a resilient portfolio today.",
            hashtags=["#Jiraaf", "#Investing", "#FixedIncome", "#Bonds"],
            metadata={
                "section_label": "THE PROBLEM",
                "supporting_line": "Predictable income, lower volatility, and better diversification.",
                "problem_statement": "Many investors chase only equity returns.",
                "solution_statement": "Balanced portfolios include bonds for income and stability.",
                "customer_quote": "Bonds transformed my portfolio. I now earn steady income while sleeping peacefully.",
                "customer_name": "Rohit S.",
                "infographic_section_specs": [
                    {"section_label": "Predictable Income", "stat": "5-8%", "body": "Regular income stream from coupon payments.", "icon_hint": "growth"},
                    {"section_label": "Diversification", "stat": "Spread Risk", "body": "Reduces overall portfolio volatility.", "icon_hint": "chart"},
                    {"section_label": "Capital Safety", "stat": "AAA-rated", "body": "High-quality bonds protect your principal.", "icon_hint": "shield"},
                    {"section_label": "Monthly Payouts", "stat": "12x/Year", "body": "Regular cash flow for investors.", "icon_hint": "calendar"},
                    {"section_label": "Low Volatility", "stat": "Stable", "body": "Stable returns even during market downturns.", "icon_hint": "wallet"},
                ],
                "stat_highlights": [
                    "5-8% annual yield",
                    "40% lower volatility",
                    "AAA-rated options",
                    "Monthly payouts"
                ],
                "process_steps": [
                    "Assess Goals",
                    "Allocate Assets",
                    "Monitor Regularly",
                    "Rebalance Quarterly"
                ],
                "brand_colors": {
                    "primary": "#33206F",
                    "secondary": "#F59A23",
                    "accent": "#FFC857",
                    "dark_text": "#222222",
                    "secondary_text": "#5B5B5B",
                    "background": "#FFFFFF",
                    "surface": "#FAFAFC",
                    "border": "#ECECEC",
                    "success": "#2EAF62",
                    "blue": "#4F8EF7",
                    "gray": "#9EA3AE"
                }
            },
        ),
        brand_visual_rules={
            "brand_colors": {
                "primary": "#33206F",
                "secondary": "#F59A23",
                "accent": "#FFC857",
                "dark_text": "#222222",
                "secondary_text": "#5B5B5B",
                "background": "#FFFFFF",
                "surface": "#FAFAFC",
                "border": "#ECECEC",
                "success": "#2EAF62",
                "blue": "#4F8EF7",
                "gray": "#9EA3AE"
            }
        }
    )
    
    # We will pass a simple dict to emulate the page text structure
    page_text = {
        "headline": payload.text.headline,
        "supporting_line": payload.text.metadata.get("supporting_line"),
        "cta": payload.text.cta,
        "body": payload.text.body,
        "problem_statement": payload.text.metadata.get("problem_statement"),
        "solution_statement": payload.text.metadata.get("solution_statement"),
        "infographic_section_specs": payload.text.metadata.get("infographic_section_specs"),
        "stat_highlights": payload.text.metadata.get("stat_highlights"),
        "customer_quote": payload.text.metadata.get("customer_quote"),
        "customer_name": payload.text.metadata.get("customer_name"),
        "process_steps": payload.text.metadata.get("process_steps"),
        "hashtags": payload.text.hashtags,
        "show_image": False
    }
    
    # Execute page rendering
    img, details = renderer._render_page(payload, size, page_text)
    
    # Save the output image
    output_path = Path("scratch/bonds_infographic.png")
    img.save(output_path)
    print(f"Infographic successfully rendered and saved to: {output_path.absolute()}")
    print("Render Details:")
    for k, v in details.items():
        if k != "zones_used" and k != "text_fit":
            print(f"  {k}: {v}")

if __name__ == "__main__":
    asyncio.run(main())
