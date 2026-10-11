import json
from pathlib import Path
import pytest
from dependency_guardian.config import AIFallbackPolicy, DetectionConfig
from dependency_guardian.contracts.findings import (
    CompatibilityClassification,
    DetectionMode,
    DetectionSource,
    Finding,
    RuleId,
    SeverityLevel,
)
from dependency_guardian.contracts.models import DetectionRequest
from dependency_guardian.orchestrator import DetectionOrchestrator
from dependency_guardian.providers.hosted import HostedAIProvider
from dependency_guardian.providers.mock import MockAIProvider
from dependency_guardian.providers.ollama import OllamaProvider

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def baseline_spec():
    return json.loads((FIXTURES_DIR / "baseline.json").read_text(encoding="utf-8"))


@pytest.fixture
def path_removed_spec():
    return json.loads((FIXTURES_DIR / "path_removed.json").read_text(encoding="utf-8"))


def test_algorithmic_mode_never_initializes_or_calls_ai_provider(baseline_spec, path_removed_spec):
    mock_ai = MockAIProvider()
    config = DetectionConfig(detection_mode=DetectionMode.ALGORITHMIC)
    orchestrator = DetectionOrchestrator(config=config, ai_provider=mock_ai)

    request = DetectionRequest(
        baseline_spec=baseline_spec,
        current_spec=path_removed_spec,
    )
    result = orchestrator.execute(request)

    assert result.success is True
    assert result.mode == DetectionMode.ALGORITHMIC
    assert result.ai_status == "skipped"
    assert mock_ai.call_count == 0
    assert len(result.findings) == 1
    assert result.findings[0].source == DetectionSource.ALGORITHMIC


def test_ai_mode_without_provider_reports_error_clearly(baseline_spec, path_removed_spec):
    config = DetectionConfig(
        detection_mode=DetectionMode.AI,
        ai_provider=None,
        ai_fallback_policy=AIFallbackPolicy.FAIL,
    )
    orchestrator = DetectionOrchestrator(config=config)

    request = DetectionRequest(baseline_spec=baseline_spec, current_spec=path_removed_spec)
    result = orchestrator.execute(request)

    assert result.success is False
    assert result.ai_status == "failed"
    assert "requires 'ai_provider' to be configured" in (result.ai_error or "")
    assert len(result.findings) == 0


def test_ai_mode_with_mock_provider_succeeds(baseline_spec, path_removed_spec):
    mock_ai = MockAIProvider(model_name="test-model")
    config = DetectionConfig(
        detection_mode=DetectionMode.AI,
        ai_provider="mock",
    )
    orchestrator = DetectionOrchestrator(config=config, ai_provider=mock_ai)

    request = DetectionRequest(baseline_spec=baseline_spec, current_spec=path_removed_spec)
    result = orchestrator.execute(request)

    assert result.success is True
    assert result.mode == DetectionMode.AI
    assert result.ai_status == "completed"
    assert mock_ai.call_count == 1


def test_ai_mode_fallback_to_algorithmic_policy(baseline_spec, path_removed_spec):
    mock_ai = MockAIProvider(available=False)  # Unavailable
    config = DetectionConfig(
        detection_mode=DetectionMode.AI,
        ai_provider="mock",
        ai_fallback_policy=AIFallbackPolicy.FALLBACK_TO_ALGORITHMIC,
    )
    orchestrator = DetectionOrchestrator(config=config, ai_provider=mock_ai)

    request = DetectionRequest(baseline_spec=baseline_spec, current_spec=path_removed_spec)
    result = orchestrator.execute(request)

    assert result.success is True
    assert result.fallback_triggered is True
    assert result.ai_status == "failed"
    assert len(result.findings) == 1
    assert result.findings[0].rule_id == RuleId.PATH_REMOVED.value


def test_hybrid_mode_enriches_algorithmic_findings_with_ai_reasoning(baseline_spec, path_removed_spec):
    # Setup mock to enrich findings with specific reasoning
    mock_ai = MockAIProvider(
        model_name="mock-reasoner",
        reasoning_map={
            Finding.generate_fingerprint("/users/{id}", "*", "paths./users/{id}", RuleId.PATH_REMOVED.value):
                "Endpoint deletion breaks client calls and requires routing fallback.",
        },
    )
    config = DetectionConfig(
        detection_mode=DetectionMode.HYBRID,
        ai_provider="mock",
    )
    orchestrator = DetectionOrchestrator(config=config, ai_provider=mock_ai)

    request = DetectionRequest(baseline_spec=baseline_spec, current_spec=path_removed_spec)
    result = orchestrator.execute(request)

    assert result.success is True
    assert result.mode == DetectionMode.HYBRID
    assert result.ai_status == "completed"
    assert len(result.findings) == 1
    f = result.findings[0]
    assert f.source == DetectionSource.HYBRID
    assert f.ai_reasoning == "Endpoint deletion breaks client calls and requires routing fallback."
    assert f.confidence == 1.0


def test_hybrid_mode_preserves_deterministic_findings_when_ai_times_out(baseline_spec, path_removed_spec):
    mock_ai = MockAIProvider(simulate_timeout=True)
    config = DetectionConfig(
        detection_mode=DetectionMode.HYBRID,
        ai_provider="mock",
        ai_fallback_policy=AIFallbackPolicy.FALLBACK_TO_ALGORITHMIC,
    )
    orchestrator = DetectionOrchestrator(config=config, ai_provider=mock_ai)

    request = DetectionRequest(baseline_spec=baseline_spec, current_spec=path_removed_spec)
    result = orchestrator.execute(request)

    # Findings must NEVER be lost
    assert len(result.findings) == 1
    assert result.findings[0].rule_id == RuleId.PATH_REMOVED.value
    assert result.ai_status == "failed"
    assert result.fallback_triggered is True


def test_hybrid_merge_never_allows_ai_to_convert_breaking_to_non_breaking(baseline_spec, path_removed_spec):
    algo_engine = orchestrator = None
    fingerprint = Finding.generate_fingerprint("/users/{id}", "*", "paths./users/{id}", RuleId.PATH_REMOVED.value)

    # AI tries to return a non-breaking finding with the same fingerprint
    tampered_ai_finding = Finding(
        rule_id=RuleId.PATH_REMOVED.value,
        fingerprint=fingerprint,
        compatibility=CompatibilityClassification.NON_BREAKING,  # Tampered!
        severity=SeverityLevel.LOW,
        path="/users/{id}",
        schema_location="paths./users/{id}",
        message="AI claims it is safe",
        confidence=0.5,
        source=DetectionSource.AI,
    )
    mock_ai = MockAIProvider(extra_findings=[tampered_ai_finding])
    config = DetectionConfig(detection_mode=DetectionMode.HYBRID, ai_provider="mock")
    orch = DetectionOrchestrator(config=config, ai_provider=mock_ai)

    result = orch.execute(DetectionRequest(baseline_spec=baseline_spec, current_spec=path_removed_spec))

    # The deterministic finding must retain BREAKING compatibility
    path_f = [f for f in result.findings if f.fingerprint == fingerprint][0]
    assert path_f.compatibility == CompatibilityClassification.BREAKING
    assert path_f.severity == SeverityLevel.HIGH


def test_hosted_and_ollama_providers_raise_explicit_unavailable_errors(baseline_spec):
    hosted = HostedAIProvider(api_key="fake-key")
    with pytest.raises(Exception, match="extension point"):
        from dependency_guardian.providers.base import AIAnalysisRequest
        hosted.analyze(AIAnalysisRequest(baseline_spec=baseline_spec, current_spec=baseline_spec))

    ollama = OllamaProvider()
    assert ollama.is_available() is False
    with pytest.raises(Exception, match="extension point"):
        ollama.analyze(AIAnalysisRequest(baseline_spec=baseline_spec, current_spec=baseline_spec))

