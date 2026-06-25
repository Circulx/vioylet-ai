from __future__ import annotations

import re

from app.core.exceptions import GuardrailViolationError


class GuardrailService:
    # Groups guardrail service behavior for guardrail checks.
    # Callers use this class to produce or evaluate data consumed by safe output handling.
    def validate_prompt(self, prompt: str, guardrails: dict) -> dict:
        # Builds prompt from prompt text and guardrails for safe output handling.
        # This keeps payload shape decisions close to the code that understands the inputs.
        violations: list[str] = []
        lowered = prompt.lower()
        for blocked in guardrails.get("blocked_words", []):
            if blocked.lower() in lowered:
                violations.append(f"Blocked word detected: {blocked}")
        for topic in guardrails.get("restricted_topics", []):
            if topic.lower() in lowered:
                violations.append(f"Restricted topic detected: {topic}")
        for claim in guardrails.get("restricted_claims", []):
            if claim.lower() in lowered:
                violations.append(f"Restricted claim detected: {claim}")
        for pattern in guardrails.get("forbidden_prompt_patterns", []):
            if re.search(pattern, prompt, flags=re.IGNORECASE):
                violations.append(f"Forbidden prompt pattern detected: {pattern}")
        if violations:
            # Fail fast here so unsafe prompt or output text never reaches downstream generation.
            raise GuardrailViolationError("; ".join(violations))
        return {"status": "passed", "violations": []}

    def validate_output(self, content: str, guardrails: dict) -> dict:
        # Centralizes output from generated content and guardrails for safe output handling.
        # The main branch stays readable while this function handles the local edge case.
        return self.validate_prompt(content, guardrails)

