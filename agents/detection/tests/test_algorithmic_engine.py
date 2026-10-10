import json
from pathlib import Path
import pytest
from dependency_guardian.contracts.findings import (
    CompatibilityClassification,
    DetectionSource,
    Finding,
    RuleId,
    SeverityLevel,
)
from dependency_guardian.engines.algorithmic import AlgorithmicDetectionEngine

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def baseline_spec():
    return json.loads((FIXTURES_DIR / "baseline.json").read_text(encoding="utf-8"))


@pytest.fixture
def engine():
    return AlgorithmicDetectionEngine()


def test_identical_specifications_produce_zero_findings(engine, baseline_spec):
    identical_spec = json.loads((FIXTURES_DIR / "identical.json").read_text(encoding="utf-8"))
    findings = engine.detect(baseline_spec, identical_spec)
    assert len(findings) == 0


def test_path_removed_detection(engine, baseline_spec):
    curr = json.loads((FIXTURES_DIR / "path_removed.json").read_text(encoding="utf-8"))
    findings = engine.detect(baseline_spec, curr)

    path_findings = [f for f in findings if f.rule_id == RuleId.PATH_REMOVED.value]
    assert len(path_findings) == 1
    f = path_findings[0]
    assert f.path == "/users/{id}"
    assert f.compatibility == CompatibilityClassification.BREAKING
    assert f.severity == SeverityLevel.HIGH
    assert f.confidence == 1.0
    assert f.source == DetectionSource.ALGORITHMIC
    assert f.review_required is False
    assert f.evidence["removed_path"] == "/users/{id}"


def test_method_removed_detection(engine, baseline_spec):
    curr = json.loads((FIXTURES_DIR / "method_removed.json").read_text(encoding="utf-8"))
    findings = engine.detect(baseline_spec, curr)

    method_findings = [f for f in findings if f.rule_id == RuleId.METHOD_REMOVED.value]
    assert len(method_findings) == 1
    f = method_findings[0]
    assert f.path == "/users/{id}"
    assert f.method == "DELETE"
    assert f.compatibility == CompatibilityClassification.BREAKING
    assert f.severity == SeverityLevel.HIGH
    assert f.schema_location == "paths./users/{id}.delete"


def test_response_field_removed_detection(engine, baseline_spec):
    curr = json.loads((FIXTURES_DIR / "response_field_removed.json").read_text(encoding="utf-8"))
    findings = engine.detect(baseline_spec, curr)

    resp_findings = [f for f in findings if f.rule_id == RuleId.RESPONSE_FIELD_REMOVED.value]
    assert len(resp_findings) >= 1
    f = resp_findings[0]
    assert f.compatibility == CompatibilityClassification.BREAKING
    assert f.severity == SeverityLevel.HIGH
    assert "name" in f.schema_location
    assert f.evidence["removed_property"] == "name"


def test_type_changed_detection(engine, baseline_spec):
    curr = json.loads((FIXTURES_DIR / "type_changed.json").read_text(encoding="utf-8"))
    findings = engine.detect(baseline_spec, curr)

    type_findings = [f for f in findings if f.rule_id == RuleId.FIELD_TYPE_CHANGED.value]
    assert len(type_findings) >= 1
    f = type_findings[0]
    assert f.compatibility == CompatibilityClassification.BREAKING
    assert f.previous_value == "integer"
    assert f.current_value == "string"


def test_required_param_added_detection(engine, baseline_spec):
    curr = json.loads((FIXTURES_DIR / "required_param_added.json").read_text(encoding="utf-8"))
    findings = engine.detect(baseline_spec, curr)

    param_findings = [f for f in findings if f.rule_id == RuleId.REQUIRED_PARAM_ADDED.value]
    assert len(param_findings) == 1
    f = param_findings[0]
    assert f.path == "/users"
    assert f.method == "GET"
    assert f.compatibility == CompatibilityClassification.BREAKING
    assert f.evidence["parameter_name"] == "tenant_id"


def test_required_field_added_detection(engine, baseline_spec):
    curr = json.loads((FIXTURES_DIR / "required_field_added.json").read_text(encoding="utf-8"))
    findings = engine.detect(baseline_spec, curr)

    req_findings = [f for f in findings if f.rule_id == RuleId.REQUIRED_FIELD_ADDED.value]
    assert len(req_findings) >= 1
    f = req_findings[0]
    assert f.compatibility == CompatibilityClassification.BREAKING
    assert f.evidence["field"] == "phone"


def test_enum_value_removed_detection(engine, baseline_spec):
    curr = json.loads((FIXTURES_DIR / "enum_value_removed.json").read_text(encoding="utf-8"))
    findings = engine.detect(baseline_spec, curr)

    enum_findings = [f for f in findings if f.rule_id == RuleId.ENUM_VALUE_REMOVED.value]
    assert len(enum_findings) >= 1
    f = enum_findings[0]
    assert "guest" in f.evidence["removed_values"]


def test_status_code_removed_detection(engine, baseline_spec):
    curr = json.loads((FIXTURES_DIR / "status_code_removed.json").read_text(encoding="utf-8"))
    findings = engine.detect(baseline_spec, curr)

    status_findings = [f for f in findings if f.rule_id == RuleId.STATUS_CODE_REMOVED.value]
    assert len(status_findings) == 1
    f = status_findings[0]
    assert f.path == "/users/{id}"
    assert f.method == "DELETE"
    assert f.evidence["removed_status_code"] == "200"
    assert f.compatibility == CompatibilityClassification.BREAKING


def test_optional_field_added_detection(engine, baseline_spec):
    curr = json.loads((FIXTURES_DIR / "optional_field_added.json").read_text(encoding="utf-8"))
    findings = engine.detect(baseline_spec, curr)

    opt_findings = [f for f in findings if f.rule_id == RuleId.FIELD_ADDED_OPTIONAL.value]
    assert len(opt_findings) >= 1
    f = opt_findings[0]
    assert f.compatibility == CompatibilityClassification.NON_BREAKING
    assert f.severity == SeverityLevel.LOW
    assert f.evidence["added_property"] == "avatar_url"


def test_optional_param_added_detection(engine, baseline_spec):
    curr = json.loads((FIXTURES_DIR / "optional_param_added.json").read_text(encoding="utf-8"))
    findings = engine.detect(baseline_spec, curr)

    opt_param_findings = [
        f for f in findings
        if f.rule_id == RuleId.FIELD_ADDED_OPTIONAL.value and "parameters" in f.schema_location
    ]
    assert len(opt_param_findings) == 1
    f = opt_param_findings[0]
    assert f.compatibility == CompatibilityClassification.NON_BREAKING
    assert f.severity == SeverityLevel.LOW
    assert f.evidence["parameter_name"] == "include_inactive"


def test_request_field_removed_detection(engine, baseline_spec):
    curr = json.loads((FIXTURES_DIR / "request_field_removed.json").read_text(encoding="utf-8"))
    findings = engine.detect(baseline_spec, curr)

    req_removed = [f for f in findings if f.rule_id == RuleId.REQUEST_FIELD_REMOVED.value]
    assert len(req_removed) >= 1
    f = req_removed[0]
    assert f.compatibility == CompatibilityClassification.POTENTIALLY_BREAKING
    assert f.severity == SeverityLevel.MEDIUM
    assert f.review_required is True
    assert f.evidence["removed_property"] == "email"


def test_circular_reference_handled_without_infinite_recursion(engine):
    curr = json.loads((FIXTURES_DIR / "circular_ref.json").read_text(encoding="utf-8"))
    findings = engine.detect(curr, curr)
    assert len(findings) == 0


def test_empty_and_invalid_specifications_safe(engine, baseline_spec):
    empty_spec = json.loads((FIXTURES_DIR / "empty_spec.json").read_text(encoding="utf-8"))
    invalid_spec = json.loads((FIXTURES_DIR / "invalid_spec.json").read_text(encoding="utf-8"))

    # Empty vs empty
    assert engine.detect(empty_spec, empty_spec) == []
    # Invalid vs invalid
    assert engine.detect(invalid_spec, invalid_spec) == []
    # Non-dict inputs
    assert engine.detect(None, None) == []  # type: ignore
    assert engine.detect([], {}) == []  # type: ignore


def test_all_findings_conform_to_canonical_contract(engine, baseline_spec):
    curr = json.loads((FIXTURES_DIR / "path_removed.json").read_text(encoding="utf-8"))
    findings = engine.detect(baseline_spec, curr)

    for f in findings:
        # Validate against Pydantic model
        dumped = f.model_dump()
        revalidated = Finding.model_validate(dumped)
        assert revalidated.id == f.id
        assert revalidated.fingerprint == f.fingerprint
        assert revalidated.confidence == 1.0
        assert revalidated.source == DetectionSource.ALGORITHMIC


def test_stable_fingerprint_deterministic_across_invocations(engine, baseline_spec):
    curr = json.loads((FIXTURES_DIR / "path_removed.json").read_text(encoding="utf-8"))
    run1 = engine.detect(baseline_spec, curr)
    run2 = engine.detect(baseline_spec, curr)

    assert len(run1) == len(run2)
    for f1, f2 in zip(run1, run2):
        assert f1.fingerprint == f2.fingerprint
        assert f1.rule_id == f2.rule_id
        assert f1.schema_location == f2.schema_location

