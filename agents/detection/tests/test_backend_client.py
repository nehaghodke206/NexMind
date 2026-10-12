from dependency_guardian.client.backend import BackendClient
from dependency_guardian.contracts.findings import (
    CompatibilityClassification,
    DetectionMode,
    DetectionSource,
    Finding,
    RuleId,
    SeverityLevel,
)
from dependency_guardian.contracts.models import DetectionResult, DiffSummary


def test_finding_to_backend_observation_mapping():
    finding = Finding(
        rule_id=RuleId.RESPONSE_FIELD_REMOVED.value,
        fingerprint="test:fingerprint:123",
        compatibility=CompatibilityClassification.BREAKING,
        severity=SeverityLevel.HIGH,
        path="/users/{id}",
        method="GET",
        schema_location="paths./users/{id}.get.responses.200.content.application/json.schema.properties.name",
        previous_value={"type": "string"},
        current_value=None,
        message="Property 'name' was removed from response.",
        evidence={"removed_property": "name"},
        confidence=1.0,
        source=DetectionSource.ALGORITHMIC,
    )

    obs = finding.to_backend_observation(scan_id="scan-123", dependency_id="dep-456")
    assert obs["dependency_id"] == "dep-456"
    assert obs["observation_type"] == "response_shape"
    assert obs["endpoint"] == "/users/{id}"
    assert obs["method"] == "GET"
    assert obs["fingerprint"] == "test:fingerprint:123"
    assert obs["payload"]["finding_id"] == finding.id
    assert obs["payload"]["rule_id"] == RuleId.RESPONSE_FIELD_REMOVED.value
    assert obs["payload"]["compatibility"] == "breaking"
    assert obs["payload"]["severity"] == "high"


def test_finding_to_backend_incident_mapping():
    finding = Finding(
        rule_id=RuleId.RESPONSE_FIELD_REMOVED.value,
        fingerprint="test:fingerprint:123",
        compatibility=CompatibilityClassification.BREAKING,
        severity=SeverityLevel.HIGH,
        path="/users/{id}",
        method="GET",
        schema_location="paths./users/{id}.get.responses.200.content.application/json.schema.properties.name",
        previous_value={"type": "string"},
        current_value=None,
        message="Property 'name' was removed from response.",
        evidence={"removed_property": "name"},
        confidence=1.0,
        source=DetectionSource.ALGORITHMIC,
    )

    inc = finding.to_backend_incident(
        dependency_id="dep-456",
        observation_ids=["obs-1", "obs-2"],
        affected_files=["src/api.ts"],
    )
    assert inc["dependency_id"] == "dep-456"
    assert "[GET] /users/{id}" in inc["title"]
    assert inc["change_type"] == "field_removed"
    assert inc["severity"] == "high"
    assert inc["confidence"] == 1.0
    assert inc["fingerprint"] == "test:fingerprint:123"
    assert inc["observation_ids"] == ["obs-1", "obs-2"]
    assert inc["affected_files"] == ["src/api.ts"]


def test_backend_client_graceful_offline_degradation():
    # Use unroutable local address to ensure offline behavior
    client = BackendClient(base_url="http://127.0.0.1:59999/api/v1", timeout=0.1)

    assert client.is_available() is False

    result = DetectionResult(
        success=True,
        mode=DetectionMode.ALGORITHMIC,
        findings=[],
        summary=DiffSummary(),
    )

    sync_res = client.sync_detection_result(
        project_id="proj-123",
        dependency_id="dep-456",
        result=result,
    )

    assert sync_res["synced"] is False
    assert "offline" in sync_res["reason"].lower()


def test_backend_client_requires_valid_project_and_dependency_ids():
    client = BackendClient(base_url="http://127.0.0.1:8000/api/v1")
    dummy_result = DetectionResult(
        success=True,
        mode=DetectionMode.ALGORITHMIC,
        findings=[],
        summary=DiffSummary(),
    )

    import pytest
    with pytest.raises(ValueError, match="valid, non-empty project_id"):
        client.start_scan(project_id="")

    with pytest.raises(ValueError, match="valid, non-empty project_id"):
        client.sync_detection_result(project_id="  ", dependency_id="dep-1", result=dummy_result)

    with pytest.raises(ValueError, match="valid, non-empty dependency_id"):
        client.sync_detection_result(project_id="proj-1", dependency_id="", result=dummy_result)


def test_finding_to_backend_incident_maps_field_rename_and_affected_files():
    finding = Finding(
        rule_id="RULE-FIELD-RENAMED",
        fingerprint="test:rename:123",
        compatibility=CompatibilityClassification.BREAKING,
        severity=SeverityLevel.HIGH,
        path="/items",
        method="PUT",
        schema_location="items.sku",
        previous_value="sku",
        current_value="item_sku",
        message="Property 'sku' was renamed to 'item_sku'",
        evidence={"renamed_from": "sku", "renamed_to": "item_sku", "file": "src/inventory.py"},
        confidence=1.0,
        source=DetectionSource.ALGORITHMIC,
    )

    inc = finding.to_backend_incident(dependency_id="dep-456")
    assert inc["change_type"] == "field_rename"
    assert inc["affected_files"] == ["src/inventory.py"]
    assert inc["evidence"]["evidence_details"]["renamed_to"] == "item_sku"


