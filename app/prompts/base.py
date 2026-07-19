from abc import ABC, abstractmethod
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class BasePromptBuilder(ABC):
    """Base class for all Violyt prompt builders."""

    PROMPT_VERSION: str = "1.0"

    @abstractmethod
    def build_system(self, **kwargs: Any) -> str:
        raise NotImplementedError

    @abstractmethod
    def build_user(self, **kwargs: Any) -> str:
        raise NotImplementedError

    def log_prompt(self, layer: str, token_estimate: int | None = None) -> None:
        logger.info(
            "prompt.built",
            layer=layer,
            version=self.PROMPT_VERSION,
            token_estimate=token_estimate,
        )
