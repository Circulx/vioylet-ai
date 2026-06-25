# Utility helpers collect shared formatting, parsing, and normalization rules used across services.
from __future__ import annotations

import re
from datetime import datetime, timezone


def slugify(value: str) -> str:
    # Handles slugify as a reusable helper for services that need the same formatting or normalization rule.
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return normalized.strip("-")


def current_period_key() -> str:
    # Handles current period key as a reusable helper for services that need the same formatting or
    # normalization rule.
    return datetime.now(timezone.utc).strftime("%Y-%m")

