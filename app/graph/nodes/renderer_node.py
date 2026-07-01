from app.graph.state import ViolytState


async def renderer_node(state: ViolytState) -> dict:
    scene_graph = state.get("scene_graph")
    platform = state.get("platform", "linkedin")
    fmt = state.get("format", "static")

    return {
        "final_output": {
            "platform": platform,
            "format": fmt,
            "canvas_ratio": scene_graph.platform_ratio if scene_graph else "1200x627",
            "asset_url": "https://example.com/mock/final_render.png",
            "render_status": "success",
            "message": "Creative rendered from scene graph.",
        }
    }
