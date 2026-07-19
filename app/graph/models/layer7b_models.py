from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from app.graph.models.layer7_models import CopyOutput


class SpellingFix(BaseModel):
    original: str
    corrected: str
    field: str


class GrammarFix(BaseModel):
    original: str
    corrected: str
    field: str


class Truncation(BaseModel):
    field: str
    original_len: int
    truncated_len: int


class FactFlag(BaseModel):
    claim: str
    field: str
    risk_level: str  # "low", "medium", "high"


class ContentValidationOutput(BaseModel):
    """Output from the content validation / cleanup layer."""

    validated_copy: CopyOutput
    spelling_fixes: List[SpellingFix]
    grammar_fixes: List[GrammarFix]
    truncations: List[Truncation]
    fact_flags: List[FactFlag]
    validation_passed: bool
