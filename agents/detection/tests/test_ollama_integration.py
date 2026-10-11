"""
Unit and integration test suite for Ollama AI Provider, Hybrid Mode,
Risk Insights, and Regression Test Generation in Dependency Guardian.

Uses httpx.MockTransport for deterministic, fast offline verification
without requiring a live Ollama instance or external services.
"""
import ast
import json
from pathlib import Path
from typing import Any, Dict, List
import httpx
import pytest

from dependency_guardian.contracts.findings import (
    CompatibilityClassification,
    DetectionMode,
    DetectionSource,
    Finding,
    RuleId,
    SeverityLevel,
)
from dependency_guardian.contracts.models import DetectionRequest
from dependency_guardian.config import AIFallbackPolicy, DetectionConfig
from dependency_guardian.orchestrator import DetectionOrchestrator
from dependency_guardian.providers.base import (
    AIAnalysisRequest,
    AIInvalidOutputError,
    AIProviderError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)
from dependency_guardian.providers.ollama import OllamaProvider
from dependency_guardian.insights import format_insights_text
from dependency_guardian.test_generator import (
    RegressionTestGenerator,
    TestCaseModel,
    TestExecutionSummary,
    validate_test_code_safety,
)
from dependency_guardian.cli import run as run_cli


@pytest.fixture
def sample_specs():
    v1 = {
        "openapi": "3.1.0",
        "info": {"title": "Test Service", "version": "1.0.0"},
        "paths": {
            "/api/v1/products": {
                "get": {
                    "parameters": [{"name": "category", "in": "query", "required": False}],
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/v1/payments/{id}/receipt": {
                "get": {"responses": {"200": {"description": "Receipt"}}}
            },
        },
        "components": {"schemas": {"Product": {"type": "object", "properties": {"id": {"type": "integer"}}}}},
    }
    v2 = {
        "openapi": "3.1.0",
        "info": {"title": "Test Service", "version": "2.0.0"},
        "paths": {
            "/api/v1/products": {
                "get": {
                    "parameters": [
                        {"name": "category", "in": "query", "required": False},
                        {"name": "store_id", "in": "query", "required": True},
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
        "components": {"schemas": {"Product": {"type": "object", "properties": {"id": {"type": "integer"}}}}},
    }
    return v1, v2


# ==============================================================================
# 1. Ollama Provider Unit Tests with Mocked HTTP Transport
# ==============================================================================

def test_ollama_is_available_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags"
        return httpx.Response(200, json={"models": [{"name": "qwen2.5-coder:3b"}]})

    provider = OllamaProvider(base_url="http://mock-ollama:11434", transport=httpx.MockTransport(handler))
    assert provider.is_available() is True


def test_ollama_is_available_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    provider = OllamaProvider(base_url="http://mock-ollama:11434", transport=httpx.MockTransport(handler))
    assert provider.is_available() is False


def test_ollama_get_health_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": [{"name": "qwen2.5-coder:3b"}, {"name": "llama3:latest"}]})

    provider = OllamaProvider(base_url="http://mock-ollama:11434", transport=httpx.MockTransport(handler))
    health = provider.get_health_status()
    assert health["reachable"] is True
    assert health["model_available"] is True
    assert "qwen2.5-coder:3b" in health["installed_models"]
    assert health["selected_model"] == "qwen2.5-coder:3b"


def test_ollama_connection_refusal_raises_actionable_error(sample_specs):
    v1, v2 = sample_specs

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    provider = OllamaProvider(base_url="http://offline-ollama:11434", transport=httpx.MockTransport(handler))
    with pytest.raises(AIProviderUnavailableError, match="Ensure Ollama is running"):
        provider.analyze(AIAnalysisRequest(baseline_spec=v1, current_spec=v2))


def test_ollama_timeout_raises_timeout_error(sample_specs):
    v1, v2 = sample_specs

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "qwen2.5-coder:3b"}]})
        raise httpx.TimeoutException("Read timed out")

    provider = OllamaProvider(base_url="http://mock-ollama:11434", transport=httpx.MockTransport(handler))
    with pytest.raises(AIProviderTimeoutError, match="timed out"):
        provider.analyze(AIAnalysisRequest(baseline_spec=v1, current_spec=v2))


def test_ollama_missing_model_404_raises_unavailable_error(sample_specs):
    v1, v2 = sample_specs

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "other-model:latest"}]})
        return httpx.Response(404, text="model not found")

    provider = OllamaProvider(
        base_url="http://mock-ollama:11434",
        model_name="nonexistent-model",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(AIProviderUnavailableError, match="ollama pull"):
        provider.analyze(AIAnalysisRequest(baseline_spec=v1, current_spec=v2))


def test_ollama_invalid_json_output_raises_error(sample_specs):
    v1, v2 = sample_specs

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "qwen2.5-coder:3b"}]})
        return httpx.Response(200, json={"message": {"content": "This is plain text not JSON!"}})

    provider = OllamaProvider(base_url="http://mock-ollama:11434", transport=httpx.MockTransport(handler))
    with pytest.raises(AIInvalidOutputError, match="not valid JSON"):
        provider.analyze(AIAnalysisRequest(baseline_spec=v1, current_spec=v2))


def test_ollama_pure_ai_mode_grounding_rejects_hallucinated_endpoints(sample_specs):
    v1, v2 = sample_specs

    ai_json = {
        "summary": "Detected contract changes",
        "findings": [
            {
                "rule_id": "RULE-PATH-REMOVED",
                "compatibility": "breaking",
                "severity": "high",
                "path": "/api/v1/payments/{id}/receipt",  # Valid path from v1
                "method": "GET",
                "message": "Receipt path removed",
            },
            {
                "rule_id": "RULE-PATH-REMOVED",
                "compatibility": "breaking",
                "severity": "high",
                "path": "/api/v1/hallucinated_fake_endpoint",  # Hallucinated path!
                "method": "GET",
                "message": "Invented path",
            },
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "qwen2.5-coder:3b"}]})
        return httpx.Response(200, json={"message": {"content": json.dumps(ai_json)}})

    provider = OllamaProvider(base_url="http://mock-ollama:11434", transport=httpx.MockTransport(handler))
    resp = provider.analyze(AIAnalysisRequest(baseline_spec=v1, current_spec=v2))

    paths = [f.path for f in resp.findings]
    assert "/api/v1/payments/{id}/receipt" in paths
    assert "/api/v1/hallucinated_fake_endpoint" not in paths, "Hallucinated endpoint must be rejected"


def test_ollama_hybrid_mode_preserves_deterministic_classifications(sample_specs):
    v1, v2 = sample_specs
    algo_finding = Finding(
        rule_id=RuleId.PATH_REMOVED.value,
        fingerprint="fp-receipt-removed",
        compatibility=CompatibilityClassification.BREAKING,
        severity=SeverityLevel.HIGH,
        path="/api/v1/payments/{id}/receipt",
        method="GET",
        schema_location="paths./api/v1/payments/{id}/receipt",
        message="Receipt endpoint was removed",
        source=DetectionSource.ALGORITHMIC,
    )

    ai_json = {
        "summary": "API evolved with breaking changes",
        "enriched_findings": [
            {
                "fingerprint": "fp-receipt-removed",
                "reasoning": "Callers fetching receipts will encounter 404.",
                "remediation": "Migrate to payment details endpoint.",
                "test_suggestion": "Verify receipt endpoint returns 404.",
            }
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "qwen2.5-coder:3b"}]})
        return httpx.Response(200, json={"message": {"content": json.dumps(ai_json)}})

    provider = OllamaProvider(base_url="http://mock-ollama:11434", transport=httpx.MockTransport(handler))
    resp = provider.analyze(AIAnalysisRequest(baseline_spec=v1, current_spec=v2, algorithmic_findings=[algo_finding]))

    assert len(resp.findings) == 1
    enriched = resp.findings[0]
    # Deterministic rule_id and compatibility preserved
    assert enriched.rule_id == RuleId.PATH_REMOVED.value
    assert enriched.compatibility == CompatibilityClassification.BREAKING
    assert enriched.severity == SeverityLevel.HIGH
    # AI enrichment injected
    assert "Callers fetching receipts" in (enriched.ai_reasoning or "")
    assert enriched.evidence.get("remediation") == "Migrate to payment details endpoint."


def test_orchestrator_hybrid_mode_fallback_when_ollama_unavailable(sample_specs):
    v1, v2 = sample_specs
    config = DetectionConfig(
        detection_mode=DetectionMode.HYBRID,
        ai_provider="ollama",
        ai_base_url="http://127.0.0.1:99999",
        ai_fallback_policy=AIFallbackPolicy.FALLBACK_TO_ALGORITHMIC,
    )
    orchestrator = DetectionOrchestrator(config=config)
    req = DetectionRequest(baseline_spec=v1, current_spec=v2, mode=DetectionMode.HYBRID)
    result = orchestrator.execute(req)

    assert result.success is True
    assert result.mode == DetectionMode.HYBRID
    assert result.ai_status == "failed"
    assert result.fallback_triggered is True
    assert result.summary.total_findings > 0
    assert result.summary.breaking_count > 0


# ==============================================================================
# 2. AI Risk Insights Generation Tests
# ==============================================================================

def test_ollama_generate_risk_insights(sample_specs):
    v1, v2 = sample_specs
    finding = Finding(
        rule_id=RuleId.PATH_REMOVED.value,
        fingerprint="fp-test",
        compatibility=CompatibilityClassification.BREAKING,
        severity=SeverityLevel.HIGH,
        path="/api/v1/payments/{id}/receipt",
        schema_location="paths./api/v1/payments/{id}/receipt",
        message="Endpoint removed",
    )

    insights_json = {
        "executive_summary": "High risk evolution: 1 breaking path removed.",
        "consumer_impact_analysis": "Payment receipt callers will experience broken integrations.",
        "top_breaking_changes": ["Removed /api/v1/payments/{id}/receipt"],
        "recommended_fixes": ["Switch callers to receipt PDF service"],
        "recommended_order_of_resolution": ["1. Update mobile clients"],
        "recommended_regression_tests": ["Assert GET /api/v1/payments/1/receipt returns 404"],
        "assumptions_and_limitations": "Assumes standard HTTP consumer clients.",
        "facts_extracted_from_openapi": ["GET /api/v1/payments/{id}/receipt absent"],
        "ai_generated_hypotheses": ["Legacy mobile apps might lack fallback."],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "qwen2.5-coder:3b"}]})
        return httpx.Response(200, json={"message": {"content": json.dumps(insights_json)}})

    provider = OllamaProvider(base_url="http://mock-ollama:11434", transport=httpx.MockTransport(handler))
    insights = provider.generate_risk_insights([finding], v1, v2)

    assert insights["executive_summary"] == "High risk evolution: 1 breaking path removed."
    assert len(insights["top_breaking_changes"]) == 1
    assert "Switch callers" in insights["recommended_fixes"][0]
    # Check text formatting
    txt = format_insights_text(insights)
    assert "EXECUTIVE SUMMARY" in txt
    assert "CONSUMER IMPACT ANALYSIS" in txt
    assert "GROUNDING: FACTS" in txt


# ==============================================================================
# 3. Regression Test Generator & Safety Validation Tests
# ==============================================================================

def test_ast_safety_validator_accepts_clean_code():
    clean_code = """
def test_valid(client):
    resp = client.get("/api/v1/products")
    assert resp.status_code == 200
"""
    # Must not raise
    validate_test_code_safety(clean_code)


def test_ast_safety_validator_rejects_forbidden_imports():
    bad_code = """
import os
def test_malicious():
    os.system("rm -rf /")
"""
    with pytest.raises(ValueError, match="Forbidden module import"):
        validate_test_code_safety(bad_code)


def test_ast_safety_validator_rejects_eval_and_exec():
    bad_code = """
def test_bad():
    eval("__import__('os').system('ls')")
"""
    with pytest.raises(ValueError, match="Forbidden function call"):
        validate_test_code_safety(bad_code)


def test_regression_test_generator_candidate_artifacts(tmp_path):
    findings = [
        Finding(
            rule_id=RuleId.PATH_REMOVED.value,
            fingerprint="fp1",
            compatibility=CompatibilityClassification.BREAKING,
            severity=SeverityLevel.HIGH,
            path="/api/v1/payments/{payment_id}/receipt",
            schema_location="paths./api/v1/payments/{payment_id}/receipt",
            message="Receipt path removed",
        ),
        Finding(
            rule_id=RuleId.REQUIRED_PARAM_ADDED.value,
            fingerprint="fp2",
            compatibility=CompatibilityClassification.BREAKING,
            severity=SeverityLevel.HIGH,
            path="/api/v1/products",
            schema_location="paths./api/v1/products.get.parameters.store_id",
            message="store_id parameter required",
        ),
    ]

    generator = RegressionTestGenerator()
    candidates = generator.generate_candidate_tests(findings, target_version="v2", output_dir=tmp_path)

    assert len(candidates) >= 2
    json_path = tmp_path / "candidate_tests.json"
    py_path = tmp_path / "test_candidate_regression_v2.py"
    assert json_path.is_file()
    assert py_path.is_file()

    # Verify approval workflow
    approved_file = generator.approve_candidate_tests(tmp_path, target_version="v2")
    assert approved_file.is_file()
    assert "STATUS: APPROVED" in approved_file.read_text()


def test_execute_approved_tests_missing_file_raises(tmp_path):
    generator = RegressionTestGenerator()
    with pytest.raises(FileNotFoundError):
        generator.execute_approved_tests(tmp_path / "nonexistent.py")


# ==============================================================================
# 4. CLI Multi-Mode & Subcommand Tests
# ==============================================================================

def test_cli_algorithmic_mode(tmp_path, sample_specs):
    v1, v2 = sample_specs
    v1_file = tmp_path / "v1.json"
    v2_file = tmp_path / "v2.json"
    v1_file.write_text(json.dumps(v1))
    v2_file.write_text(json.dumps(v2))

    out_file = tmp_path / "out.json"
    argv = [
        str(v1_file),
        str(v2_file),
        "--mode", "algorithmic",
        "--format", "json",
        "--output", str(out_file),
    ]
    exit_code = run_cli(argv)
    assert exit_code == 0
    assert out_file.is_file()
    data = json.loads(out_file.read_text())
    assert data["mode"] == "algorithmic"
    assert data["summary"]["breaking_count"] > 0


def test_cli_fail_on_breaking_flag(tmp_path, sample_specs):
    v1, v2 = sample_specs
    v1_file = tmp_path / "v1.json"
    v2_file = tmp_path / "v2.json"
    v1_file.write_text(json.dumps(v1))
    v2_file.write_text(json.dumps(v2))

    argv = [
        str(v1_file),
        str(v2_file),
        "--mode", "algorithmic",
        "--fail-on-breaking",
    ]
    # Breaking changes exist, must return exit code 1
    exit_code = run_cli(argv)
    assert exit_code == 1


def test_cli_hybrid_with_mock_provider(tmp_path, sample_specs):
    v1, v2 = sample_specs
    v1_file = tmp_path / "v1.json"
    v2_file = tmp_path / "v2.json"
    v1_file.write_text(json.dumps(v1))
    v2_file.write_text(json.dumps(v2))

    out_file = tmp_path / "out-hybrid.json"
    argv = [
        str(v1_file),
        str(v2_file),
        "--mode", "hybrid",
        "--provider", "mock",
        "--format", "json",
        "--output", str(out_file),
    ]
    exit_code = run_cli(argv)
    assert exit_code == 0
    assert out_file.is_file()
    data = json.loads(out_file.read_text())
    assert data["mode"] == "hybrid"
    assert data["ai_provider"] == "mock"
    assert data["ai_status"] == "completed"


def test_live_ollama_real_inference_smoke():
    """Opt-in live integration test verifying genuine inference against local Ollama."""
    provider = OllamaProvider(timeout_seconds=60.0)
    if not provider.is_available():
        pytest.skip("Local Ollama service is not running; skipping live inference test.")

    health = provider.get_health_status()
    assert health["reachable"] is True
    assert health["model_available"] is True
    assert len(health["installed_models"]) > 0

    finding = Finding(
        rule_id=RuleId.PATH_REMOVED.value,
        fingerprint="fp-live-smoke",
        compatibility=CompatibilityClassification.BREAKING,
        severity=SeverityLevel.HIGH,
        path="/api/v1/payments/{payment_id}/receipt",
        schema_location="paths./api/v1/payments/{payment_id}/receipt",
        message="Receipt path removed in v2",
    )
    resp = provider.analyze(AIAnalysisRequest(
        baseline_spec={"info": {"title": "API", "version": "1.0"}, "paths": {"/api/v1/payments/{payment_id}/receipt": {}}},
        current_spec={"info": {"title": "API", "version": "2.0"}, "paths": {}},
        algorithmic_findings=[finding],
    ))
    assert resp.model_name in health["installed_models"]
    assert len(resp.findings) == 1
    assert resp.findings[0].ai_reasoning is not None
