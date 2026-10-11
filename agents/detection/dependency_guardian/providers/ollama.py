import logging
from typing import Optional
from .base import (
    AIAnalysisRequest,
    AIAnalysisResponse,
    AIProviderUnavailableError,
    BaseAIProvider,
)

logger = logging.getLogger("dependency_guardian.providers.ollama")


class OllamaProvider(BaseAIProvider):
    """
    Extension point for local Ollama-powered detection and reasoning.
    Validates endpoint configuration without hardcoded models or auto-downloads.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: float = 30.0,
        max_input_bytes: int = 500_000,
    ):
        super().__init__(
            model_name=model_name or "llama3",
            timeout_seconds=timeout_seconds,
            max_input_bytes=max_input_bytes,
        )
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")

    def is_available(self) -> bool:
        """
        Check if Ollama server is running locally on base_url.
        Live connectivity check is disabled until phase 2.
        """
        return False

    def analyze(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        """
        Phase 1 extension point. Raises explicit unavailable error rather than
        pretending live Ollama inference completed.
        """
        raise AIProviderUnavailableError(
            f"Ollama provider '{self.model_name}' at {self.base_url} is prepared as an extension point. "
            f"Live external inference calls are reserved for Phase 2."
        )
