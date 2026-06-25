# Core application plumbing lives here: settings, security helpers, dependency gates, and shared errors.
class DomainError(Exception):
    """Base domain error."""
# Represents a domain-level failure for DomainError; route handlers translate it into a stable API response.


class AuthorizationError(DomainError):
    """Raised when a user cannot perform an action."""
# Represents a domain-level failure for AuthorizationError; route handlers translate it into a stable API
# response.


class LifecycleError(DomainError):
    """Raised when a lifecycle transition is invalid."""
# Represents a domain-level failure for LifecycleError; route handlers translate it into a stable API
# response.


class UsageLimitExceededError(DomainError):
    """Raised when tenant quota is exceeded."""
# Represents a domain-level failure for UsageLimitExceededError; route handlers translate it into a stable API
# response.


class GuardrailViolationError(DomainError):
    """Raised when a prompt or response violates brand guardrails."""
# Represents a domain-level failure for GuardrailViolationError; route handlers translate it into a stable API
# response.


class NotFoundError(DomainError):
    """Raised when a requested entity is missing."""
# Represents a domain-level failure for NotFoundError; route handlers translate it into a stable API response.


class DuplicateResourceError(DomainError):
    """Raised when a unique resource already exists."""
# Represents a domain-level failure for DuplicateResourceError; route handlers translate it into a stable API
# response.


class UploadValidationError(DomainError):
    """Raised when an uploaded file fails preflight validation."""
# Represents a domain-level failure for UploadValidationError; route handlers translate it into a stable API
# response.


class GenerationFailureError(DomainError):
    """Raised when the generation pipeline cannot produce a final user-safe output."""
# Represents a domain-level failure for GenerationFailureError; route handlers translate it into a stable API
# response.

    def __init__(
        self,
        reason_summary: str,
        *,
        failure_type: str,
        reason_code: str,
        user_safe_message: str,
        retryable: bool,
        rule_source: str | None = None,
        suggested_next_action: str | None = None,
        details: dict | None = None,
    ) -> None:
        # Stores the initial state GenerationFailureError needs before its other methods are called.
        super().__init__(reason_summary)
        self.failure_type = failure_type
        self.reason_code = reason_code
        self.reason_summary = reason_summary
        self.user_safe_message = user_safe_message
        self.retryable = retryable
        self.rule_source = rule_source
        self.suggested_next_action = suggested_next_action
        self.details = details or {}

    def to_payload(self) -> dict:
        # Handles to payload for shared backend configuration, dependency injection, or error handling.
        return {
            "failure_type": self.failure_type,
            "reason_code": self.reason_code,
            "reason_summary": self.reason_summary,
            "user_safe_message": self.user_safe_message,
            "retryable": self.retryable,
            "rule_source": self.rule_source,
            "suggested_next_action": self.suggested_next_action,
            "details": self.details,
        }


class ChatGenerationCancelledError(DomainError):
    """Raised when a user cancels an in-flight chat generation."""
    # Represents a domain-level failure for ChatGenerationCancelledError; route handlers translate it into a
    # stable API response.
