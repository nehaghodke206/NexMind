from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from ..contracts.findings import Finding


class AIAnalysisRequest(BaseModel):
    """Encapsulates input passed to AI provider for reasoning."""

    baseline_spec: Dict[str, Any]
    current_spec: Dict[str, Any]
    algorithmic_findings: List[Finding] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class AIAnalysisResponse(BaseModel):
    """Validated structured result from AI provider."""

    findings: List[Finding] = Field(default_factory=list)
    model_name: str
    reasoning_summary: Optional[str] = None
    raw_response: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class AIProviderError(Exception):
    """Base exception for AI provider operations."""


class AIProviderUnavailableError(AIProviderError):
    """Raised when the configured AI provider endpoint is unreachable or down."""


class AIProviderTimeoutError(AIProviderError):
    """Raised when the AI provider fails to respond within configured timeout."""


class AIInvalidOutputError(AIProviderError):
    """Raised when the AI provider produces malformed or unvalidatable output."""


class BaseAIProvider(ABC):
    """Provider-neutral abstract interface for AI analysis engines."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        timeout_seconds: float = 30.0,
        max_input_bytes: int = 500_000,
    ):
        self.model_name = model_name or "default"
        self.timeout_seconds = timeout_seconds
        self.max_input_bytes = max_input_bytes

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is reachable and active without running heavy inference."""
        raise NotImplementedError

    @abstractmethod
    def analyze(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        """
        Execute AI analysis on specifications or algorithmic diff.

        Must validate all output findings against the canonical Finding schema.
        Must respect timeout_seconds and max_input_bytes.
        """
        raise NotImplementedError

    def validate_finding_payloads(self, raw_items: List[Dict[str, Any]]) -> List[Finding]:
        """Validate a list of raw dicts against the canonical Finding schema."""
        validated: List[Finding] = []
        for i, item in enumerate(raw_items):
            try:
                validated.append(Finding.model_validate(item))
            except Exception as exc:
                raise AIInvalidOutputError(
                    f"AI provider output item {i} failed validation against finding contract: {exc}"
                ) from exc
        return validated
