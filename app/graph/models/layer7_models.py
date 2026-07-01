from pydantic import BaseModel
from typing import List, Optional


class CopySlide(BaseModel):
    slide_number: int
    headline: str
    supporting_line: Optional[str] = None
    body: str
    cta: Optional[str] = None


class CopyOutput(BaseModel):
    headline: str
    supporting_line: Optional[str] = None
    body: str
    cta: str
    hashtags: List[str]
    slide_copy: List[CopySlide]
    claim_safety_notes: List[str]
