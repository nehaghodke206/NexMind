import logging
from typing import Optional
from .base import (
    AIAnalysisRequest,
    AIAnalysisResponse,
    AIProviderUnavailableError,
    BaseAIProvider,
)

logger = logging.getLogger("dependency_guardian.providers.hosted")


class HostedAIProvider(BaseAIProvider):
    """
    Extension point for remote hosted AI providers (e.g., OpenAI, Anthropic).
    Safely isolates credentials and validates configuration.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: float = 30.0,
        max_input_bytes: int = 500_000,
    ):
        super().__init__(
            model_name=model_name or "gpt-4o",
            timeout_seconds=timeout_seconds,
            max_input_bytes=max_input_bytes,
        )
        self.api_key = api_key
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")

    def is_available(self) -> bool:
        """
        Check if API credentials are configured.
        Live external API network requests are disabled in Phase 1.
        """
        return bool(self.api_key)

    def analyze(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        """
        Phase 1 extension point. Raises explicit unavailable error.
        """
        if not self.api_key:
            raise AIProviderUnavailableError("Hosted AI provider requires 'ai_api_key' to be configured.")

        raise AIProviderUnavailableError(
            f"Hosted AI provider '{self.model_name}' at {self.base_url} is prepared as an extension point. "
            f"Live external inference calls are reserved for Phase 2."
        )
