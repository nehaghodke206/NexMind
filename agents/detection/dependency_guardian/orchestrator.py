import logging
import time
from typing import Any, Dict, List, Optional
from .config import AIFallbackPolicy, DetectionConfig
from .contracts.findings import (
    CompatibilityClassification,
    DetectionMode,
    DetectionSource,
    Finding,
)
from .contracts.models import DetectionRequest, DetectionResult, DiffSummary
from .engines.algorithmic import AlgorithmicDetectionEngine
from .engines.base import BaseDetectionEngine
from .providers.base import (
    AIAnalysisRequest,
    AIProviderError,
    BaseAIProvider,
)
from .providers.hosted import HostedAIProvider
from .providers.mock import MockAIProvider
from .providers.ollama import OllamaProvider

logger = logging.getLogger("dependency_guardian.orchestrator")


class DetectionOrchestrator:
    """
    Coordinates detection mode execution, engine invocation, AI provider integration,
    error handling, merge policies, and normalization.
    """

    def __init__(
        self,
        config: DetectionConfig,
        algorithmic_engine: Optional[BaseDetectionEngine] = None,
        ai_provider: Optional[BaseAIProvider] = None,
    ):
        self.config = config
        self.algo_engine = algorithmic_engine or AlgorithmicDetectionEngine()
        self._custom_ai_provider = ai_provider

    def _resolve_ai_provider(self) -> BaseAIProvider:
        """Resolve and initialize the configured AI provider."""
        if self._custom_ai_provider:
            return self._custom_ai_provider

        provider_name = (self.config.ai_provider or "").lower().strip()
        if provider_name == "ollama":
            return OllamaProvider(
                base_url=self.config.ai_base_url,
                model_name=self.config.ai_model,
                timeout_seconds=self.config.ai_timeout_seconds,
            )
        elif provider_name in ("hosted", "openai", "anthropic"):
            return HostedAIProvider(
                api_key=self.config.ai_api_key,
                base_url=self.config.ai_base_url,
                model_name=self.config.ai_model,
                timeout_seconds=self.config.ai_timeout_seconds,
            )
        elif provider_name == "mock":
            return MockAIProvider(
                model_name=self.config.ai_model or "mock-model",
                timeout_seconds=self.config.ai_timeout_seconds,
            )
        else:
            raise ValueError(
                f"Unknown or unconfigured AI provider: '{self.config.ai_provider}'. "
                f"Supported providers: 'ollama', 'hosted', 'mock'."
            )

    def execute(self, request: DetectionRequest) -> DetectionResult:
        """
        Execute detection pipeline according to the effective mode.

        Precedence for mode:
        1. Explicit request.mode override
        2. Configured self.config.detection_mode
        """
        start_time = time.perf_counter()
        effective_mode = request.mode or self.config.detection_mode

        # Validate inputs
        if not isinstance(request.baseline_spec, dict) or not isinstance(request.current_spec, dict):
            raise ValueError("Both baseline_spec and current_spec must be parsed dictionaries.")

        logger.info("Executing detection in mode: %s", effective_mode.value)

        if effective_mode == DetectionMode.ALGORITHMIC:
            result = self._run_algorithmic_mode(request)
        elif effective_mode == DetectionMode.AI:
            result = self._run_ai_mode(request)
        elif effective_mode == DetectionMode.HYBRID:
            result = self._run_hybrid_mode(request)
        else:
            raise ValueError(f"Unsupported detection mode: {effective_mode}")

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        result.execution_time_ms = round(elapsed_ms, 2)
        return result

    def _run_algorithmic_mode(self, request: DetectionRequest) -> DetectionResult:
        """Execute deterministic algorithmic engine. No AI provider initialized or called."""
        findings = self.algo_engine.detect(
            baseline_spec=request.baseline_spec,
            current_spec=request.current_spec,
            context=request.context,
        )
        return DetectionResult(
            success=True,
            mode=DetectionMode.ALGORITHMIC,
            findings=findings,
            summary=DiffSummary.from_findings(findings),
            ai_status="skipped",
            ai_error=None,
            fallback_triggered=False,
        )

    def _run_ai_mode(self, request: DetectionRequest) -> DetectionResult:
        """Execute AI-based analysis mode."""
        # Ensure configuration is valid for AI mode
        try:
            self.config.validate_for_mode()
            provider = self._resolve_ai_provider()
        except Exception as exc:
            logger.error("AI provider initialization failed: %s", exc)
            if self.config.ai_fallback_policy == AIFallbackPolicy.FALLBACK_TO_ALGORITHMIC:
                logger.warning("Applying fallback to algorithmic detection due to AI setup error.")
                algo_findings = self.algo_engine.detect(request.baseline_spec, request.current_spec, request.context)
                return DetectionResult(
                    success=True,
                    mode=DetectionMode.AI,
                    findings=algo_findings,
                    summary=DiffSummary.from_findings(algo_findings),
                    ai_status="failed",
                    ai_error=str(exc),
                    fallback_triggered=True,
                )
            return DetectionResult(
                success=False,
                mode=DetectionMode.AI,
                findings=[],
                summary=DiffSummary(),
                ai_status="failed",
                ai_error=str(exc),
                fallback_triggered=False,
            )

        ai_req = AIAnalysisRequest(
            baseline_spec=request.baseline_spec,
            current_spec=request.current_spec,
            algorithmic_findings=[],
            context=request.context,
        )

        try:
            ai_resp = provider.analyze(ai_req)
            validated_findings = provider.validate_finding_payloads(
                [f.model_dump() for f in ai_resp.findings]
            )
            return DetectionResult(
                success=True,
                mode=DetectionMode.AI,
                findings=validated_findings,
                summary=DiffSummary.from_findings(validated_findings),
                ai_status="completed",
                ai_error=None,
                fallback_triggered=False,
            )
        except Exception as exc:
            logger.error("AI provider execution failed: %s", exc)
            if self.config.ai_fallback_policy == AIFallbackPolicy.FALLBACK_TO_ALGORITHMIC:
                logger.warning("Falling back to algorithmic detection following AI execution error.")
                algo_findings = self.algo_engine.detect(request.baseline_spec, request.current_spec, request.context)
                return DetectionResult(
                    success=True,
                    mode=DetectionMode.AI,
                    findings=algo_findings,
                    summary=DiffSummary.from_findings(algo_findings),
                    ai_status="failed",
                    ai_error=str(exc),
                    fallback_triggered=True,
                )
            return DetectionResult(
                success=False,
                mode=DetectionMode.AI,
                findings=[],
                summary=DiffSummary(),
                ai_status="failed",
                ai_error=str(exc),
                fallback_triggered=False,
            )

    def _run_hybrid_mode(self, request: DetectionRequest) -> DetectionResult:
        """Execute hybrid pipeline: algorithmic baseline followed by AI reasoning enrichment."""
        # 1. Deterministic detection first
        algo_findings = self.algo_engine.detect(
            baseline_spec=request.baseline_spec,
            current_spec=request.current_spec,
            context=request.context,
        )

        # 2. Check AI provider configuration
        try:
            self.config.validate_for_mode()
            provider = self._resolve_ai_provider()
        except Exception as exc:
            logger.warning("AI provider setup failed in hybrid mode: %s. Preserving deterministic findings.", exc)
            return DetectionResult(
                success=self.config.ai_fallback_policy != AIFallbackPolicy.FAIL,
                mode=DetectionMode.HYBRID,
                findings=algo_findings,
                summary=DiffSummary.from_findings(algo_findings),
                ai_status="failed",
                ai_error=str(exc),
                fallback_triggered=True,
            )

        # 3. Call AI provider with compact diff & context
        ai_req = AIAnalysisRequest(
            baseline_spec=request.baseline_spec,
            current_spec=request.current_spec,
            algorithmic_findings=algo_findings,
            context=request.context,
        )

        try:
            ai_resp = provider.analyze(ai_req)
            merged_findings = self._merge_hybrid_findings(algo_findings, ai_resp.findings)
            return DetectionResult(
                success=True,
                mode=DetectionMode.HYBRID,
                findings=merged_findings,
                summary=DiffSummary.from_findings(merged_findings),
                ai_status="completed",
                ai_error=None,
                fallback_triggered=False,
            )
        except Exception as exc:
            logger.warning("AI reasoning failed in hybrid mode: %s. Preserving deterministic findings.", exc)
            # Deterministic evidence is NEVER silently discarded
            is_success = self.config.ai_fallback_policy != AIFallbackPolicy.FAIL
            return DetectionResult(
                success=is_success,
                mode=DetectionMode.HYBRID,
                findings=algo_findings,
                summary=DiffSummary.from_findings(algo_findings),
                ai_status="failed",
                ai_error=str(exc),
                fallback_triggered=True,
            )

    def _merge_hybrid_findings(
        self,
        algo_findings: List[Finding],
        ai_findings: List[Finding],
    ) -> List[Finding]:
        """
        Merge policy for hybrid mode:
        1. Preserve all deterministic findings and their evidence as authoritative ground truth.
        2. Enrich matching findings (by fingerprint) with AI reasoning.
        3. Never allow AI to convert confirmed breaking changes to non-breaking.
        4. Validate novel AI findings, tag as source='ai', and require review if uncertain.
        """
        algo_map = {f.fingerprint: f.model_copy(deep=True) for f in algo_findings}
        novel_ai_findings: List[Finding] = []

        for ai_f in ai_findings:
            if ai_f.fingerprint in algo_map:
                existing = algo_map[ai_f.fingerprint]
                # Inject AI reasoning
                existing.ai_reasoning = ai_f.ai_reasoning or ai_f.message
                existing.source = DetectionSource.HYBRID
            else:
                # Novel finding proposed by AI
                validated = ai_f.model_copy(deep=True)
                validated.source = DetectionSource.AI
                # AI cannot declare breaking changes without human review
                if validated.compatibility == CompatibilityClassification.BREAKING:
                    validated.review_required = True
                novel_ai_findings.append(validated)

        merged = list(algo_map.values()) + novel_ai_findings
        merged.sort(key=lambda f: (f.path, f.method or "", f.schema_location, f.rule_id))
        return merged
