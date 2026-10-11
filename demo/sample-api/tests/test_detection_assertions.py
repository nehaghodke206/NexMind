"""
Automated validation assertions for Dependency Guardian detecting API contract changes.
Verifies stable rule IDs, compatibility classifications, schema locations, and orchestrator modes.
"""
import json
from pathlib import Path
import pytest

from dependency_guardian.contracts.findings import (
    CompatibilityClassification,
    DetectionMode,
    RuleId,
)
from dependency_guardian.contracts.models import DetectionRequest
from dependency_guardian.config import DetectionConfig
from dependency_guardian.engines.algorithmic import AlgorithmicDetectionEngine
from dependency_guardian.orchestrator import DetectionOrchestrator
from dependency_guardian.cli import run as run_cli


CONTRACTS_DIR = Path(__file__).resolve().parents[1] / "contracts"
V1_SPEC_PATH = CONTRACTS_DIR / "openapi-v1.json"
V2_SPEC_PATH = CONTRACTS_DIR / "openapi-v2.json"


@pytest.fixture(scope="module")
def specs():
    assert V1_SPEC_PATH.is_file(), f"v1 contract missing at {V1_SPEC_PATH}"
    assert V2_SPEC_PATH.is_file(), f"v2 contract missing at {V2_SPEC_PATH}"
    with open(V1_SPEC_PATH, "r", encoding="utf-8") as f:
        v1 = json.load(f)
    with open(V2_SPEC_PATH, "r", encoding="utf-8") as f:
        v2 = json.load(f)
    return v1, v2


def test_algorithmic_comparison_assertions(specs):
    v1, v2 = specs
    engine = AlgorithmicDetectionEngine()
    findings = engine.detect(v1, v2)

    assert len(findings) > 0, "Expected non-zero findings comparing v1 against v2"

    rule_ids = {f.rule_id for f in findings}
    breaking_findings = [f for f in findings if f.compatibility == CompatibilityClassification.BREAKING]
    non_breaking_findings = [f for f in findings if f.compatibility == CompatibilityClassification.NON_BREAKING]

    # Verify breaking changes exist
    assert len(breaking_findings) >= 7, f"Expected at least 7 breaking findings, got {len(breaking_findings)}"
    assert len(non_breaking_findings) >= 5, f"Expected non-breaking findings, got {len(non_breaking_findings)}"

    # 1. Assert RULE-PATH-REMOVED for /api/v1/payments/{payment_id}/receipt
    path_removed = [
        f for f in findings
        if f.rule_id == RuleId.PATH_REMOVED.value
        and f.path == "/api/v1/payments/{payment_id}/receipt"
    ]
    assert len(path_removed) == 1, "Expected RULE-PATH-REMOVED for receipt path"
    assert path_removed[0].compatibility == CompatibilityClassification.BREAKING

    # 2. Assert RULE-METHOD-REMOVED for DELETE /api/v1/products/{product_id}
    method_removed = [
        f for f in findings
        if f.rule_id == RuleId.METHOD_REMOVED.value
        and f.path == "/api/v1/products/{product_id}"
        and f.method == "DELETE"
    ]
    assert len(method_removed) == 1, "Expected RULE-METHOD-REMOVED for DELETE /api/v1/products/{product_id}"
    assert method_removed[0].compatibility == CompatibilityClassification.BREAKING

    # 3. Assert RULE-REQUIRED-PARAM-ADDED for store_id on GET /api/v1/products
    req_param = [
        f for f in findings
        if f.rule_id == RuleId.REQUIRED_PARAM_ADDED.value
        and f.path == "/api/v1/products"
        and f.method == "GET"
        and "store_id" in f.schema_location
    ]
    assert len(req_param) == 1, "Expected RULE-REQUIRED-PARAM-ADDED for store_id parameter"
    assert req_param[0].compatibility == CompatibilityClassification.BREAKING

    # 4. Assert RULE-REQUIRED-FIELD-ADDED for currency on POST /api/v1/payments
    req_field = [
        f for f in findings
        if f.rule_id == RuleId.REQUIRED_FIELD_ADDED.value
        and f.path == "/api/v1/payments"
        and f.method == "POST"
        and "currency" in f.message
    ]
    assert len(req_field) == 1, "Expected RULE-REQUIRED-FIELD-ADDED for currency field"
    assert req_field[0].compatibility == CompatibilityClassification.BREAKING

    # 5. Assert RULE-ENUM-VALUE-REMOVED for crypto on POST /api/v1/payments
    enum_removed = [
        f for f in findings
        if f.rule_id == RuleId.ENUM_VALUE_REMOVED.value
        and f.path == "/api/v1/payments"
        and f.method == "POST"
        and "crypto" in f.message
    ]
    assert len(enum_removed) >= 1, "Expected RULE-ENUM-VALUE-REMOVED for crypto"
    assert enum_removed[0].compatibility == CompatibilityClassification.BREAKING

    # 6. Assert RULE-RESPONSE-FIELD-REMOVED for stock on /api/v1/products
    resp_field = [
        f for f in findings
        if f.rule_id == RuleId.RESPONSE_FIELD_REMOVED.value
        and "products" in f.path
        and "stock" in f.message
    ]
    assert len(resp_field) >= 1, "Expected RULE-RESPONSE-FIELD-REMOVED for stock"
    assert all(f.compatibility == CompatibilityClassification.BREAKING for f in resp_field)

    # 7. Assert RULE-FIELD-TYPE-CHANGED for amount on /api/v1/payments
    type_changed = [
        f for f in findings
        if f.rule_id == RuleId.FIELD_TYPE_CHANGED.value
        and "payments" in f.path
        and "amount" in f.schema_location
    ]
    assert len(type_changed) >= 1, "Expected RULE-FIELD-TYPE-CHANGED for amount"
    assert all(f.compatibility == CompatibilityClassification.BREAKING for f in type_changed)

    # 8. Assert RULE-FIELD-ADDED-OPTIONAL for search query param and discount_amount
    search_param = [
        f for f in findings
        if f.rule_id == RuleId.FIELD_ADDED_OPTIONAL.value
        and f.path == "/api/v1/users"
        and "search" in f.schema_location
    ]
    assert len(search_param) == 1, "Expected RULE-FIELD-ADDED-OPTIONAL for search param"
    assert search_param[0].compatibility == CompatibilityClassification.NON_BREAKING

    discount_field = [
        f for f in findings
        if f.rule_id == RuleId.FIELD_ADDED_OPTIONAL.value
        and "orders" in f.path
        and "discount_amount" in f.schema_location
    ]
    assert len(discount_field) >= 1, "Expected RULE-FIELD-ADDED-OPTIONAL for discount_amount"
    assert all(f.compatibility == CompatibilityClassification.NON_BREAKING for f in discount_field)


def test_orchestrator_hybrid_mode_with_mock_provider(specs):
    v1, v2 = specs
    config = DetectionConfig(
        detection_mode=DetectionMode.HYBRID,
        ai_provider="mock",
    )
    orchestrator = DetectionOrchestrator(config)
    request = DetectionRequest(
        baseline_spec=v1,
        current_spec=v2,
        mode=DetectionMode.HYBRID,
    )
    result = orchestrator.execute(request)

    assert result.mode == DetectionMode.HYBRID
    assert result.ai_status == "completed"
    assert result.summary.total_findings > 0
    assert result.summary.breaking_count > 0
    # Hybrid mode enriches findings with AI reasoning
    assert any(f.ai_reasoning is not None for f in result.findings)


def test_orchestrator_ollama_extension_point_graceful_handling(specs):
    v1, v2 = specs
    config = DetectionConfig(
        detection_mode=DetectionMode.HYBRID,
        ai_provider="ollama",
        ai_base_url="http://127.0.0.1:99999",
    )
    orchestrator = DetectionOrchestrator(config)
    request = DetectionRequest(
        baseline_spec=v1,
        current_spec=v2,
        mode=DetectionMode.HYBRID,
    )
    result = orchestrator.execute(request)

    # When Ollama is unavailable, orchestrator preserves deterministic findings
    assert result.mode == DetectionMode.HYBRID
    assert result.ai_status == "failed"
    assert result.ai_error is not None
    assert result.summary.total_findings > 0
    assert result.summary.breaking_count > 0


def test_cli_execution_and_report_generation(tmp_path):
    out_json = tmp_path / "findings.json"
    argv = [
        str(V1_SPEC_PATH),
        str(V2_SPEC_PATH),
        "--format", "json",
        "--output", str(out_json),
    ]
    exit_code = run_cli(argv)
    assert exit_code == 0
    assert out_json.is_file()

    with open(out_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "findings" in data
    assert "summary" in data
    assert data["summary"]["breaking_count"] > 0
