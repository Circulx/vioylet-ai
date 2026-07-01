from pydantic import BaseModel
from typing import List, Literal, Optional


class SceneElement(BaseModel):
    element_id: str
    element_type: Literal["background", "visual", "copy", "logo", "cta", "decorative"]
    content: str
    position: dict
    style: dict
    asset_url: Optional[str] = None


class SceneGraphOutput(BaseModel):
    platform: str
    platform_ratio: str
    canvas_width: int
    canvas_height: int
    layers: List[str]
    elements: List[SceneElement]
    styles: dict
    assets: List[str]
