from typing import Any, Dict, List, Optional
from ..contracts.findings import Finding
from .base import (
    AIAnalysisRequest,
    AIAnalysisResponse,
    AIInvalidOutputError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
    BaseAIProvider,
)


class MockAIProvider(BaseAIProvider):
    """Deterministic test double for AI analysis orchestration testing."""

    def __init__(
        self,
        model_name: str = "mock-model",
        timeout_seconds: float = 5.0,
        available: bool = True,
        simulate_timeout: bool = False,
        simulate_invalid_output: bool = False,
        extra_findings: Optional[List[Finding]] = None,
        reasoning_map: Optional[Dict[str, str]] = None,
        custom_exception: Optional[Exception] = None,
    ):
        super().__init__(model_name=model_name, timeout_seconds=timeout_seconds)
        self._available = available
        self._simulate_timeout = simulate_timeout
        self._simulate_invalid_output = simulate_invalid_output
        self._extra_findings = extra_findings or []
        self._reasoning_map = reasoning_map or {}
        self._custom_exception = custom_exception
        self.call_count = 0
        self.last_request: Optional[AIAnalysisRequest] = None

    def is_available(self) -> bool:
        return self._available

    def analyze(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        self.call_count += 1
        self.last_request = request

        if self._custom_exception:
            raise self._custom_exception

        if not self._available:
            raise AIProviderUnavailableError("Mock AI provider is marked unavailable.")

        if self._simulate_timeout:
            raise AIProviderTimeoutError(f"Mock AI call exceeded {self.timeout_seconds}s timeout.")

        if self._simulate_invalid_output:
            # Simulate returning raw unvalidatable dictionary
            raw_bad = [{"bad_field": "corrupted", "rule_id": 123}]
            self.validate_finding_payloads(raw_bad)

        # Build response: enrich existing findings with reasoning if mapped
        out_findings: List[Finding] = []
        for f in request.algorithmic_findings:
            f_copy = f.model_copy()
            if f.fingerprint in self._reasoning_map:
                f_copy.ai_reasoning = self._reasoning_map[f.fingerprint]
            out_findings.append(f_copy)

        # Add any extra mock findings
        out_findings.extend(self._extra_findings)

        return AIAnalysisResponse(
            findings=out_findings,
            model_name=self.model_name,
            reasoning_summary="Mock AI analysis completed successfully.",
            raw_response="{'mock': true}",
        )
