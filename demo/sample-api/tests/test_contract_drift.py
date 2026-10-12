"""
Targeted contract drift verification tests for Dependency Guardian Demo API.

Verifies:
1. OpenAPI specification exists, adheres to schema, covers demo endpoints, and is discoverable.
2. Defect 1 (Wrong Path): Client calls non-existent route, upstream returns 404, demo returns 502 with evidence.
3. Defect 2 (Wrong HTTP Method): Client uses POST for GET-only health route, upstream returns 405, demo returns 502 with evidence.
   AST reconciliation against openapi.json reports method mismatch discrepancies.
4. Defect 3 (Wrong Payload Schema): Client sends payload missing required 'name' field with invalid types,
   upstream rejects with 400/422, demo returns 502 with evidence.
5. Working endpoints remain 100% operational (HTTP 200/201).
"""
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from demo.sample_api.main import create_app, app
from demo.sample_api.client import BackendIntegrationClient
from dependency_guardian.repo_intelligence.traversal import find_spec_files
from dependency_guardian.repo_intelligence.endpoint_scanner import EndpointScanner
from dependency_guardian.engines.algorithmic import AlgorithmicDetectionEngine
from dependency_guardian.contracts.findings import RuleId, CompatibilityClassification
from dependency_guardian.api_intelligence import LiveApiValidator, LiveValidationOptions


DEMO_DIR = Path(__file__).resolve().parents[1]
SPEC_PATH = DEMO_DIR / "openapi.json"
CONFIG_PATH = DEMO_DIR / "dependency-guardian.yml"


@pytest.fixture
def test_client():
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def backend_client():
    return BackendIntegrationClient()


# =============================================================================
# 1. API Contract Discovery & Schema Completeness
# =============================================================================

def test_openapi_contract_discovery_and_structure():
    """Verify OpenAPI specification file exists, is discoverable, and defines required schemas."""
    assert SPEC_PATH.is_file(), f"Expected contract at {SPEC_PATH}"

    # Detector discovery check
    discovered = find_spec_files(DEMO_DIR)
    discovered_rel = [str(p.relative_to(DEMO_DIR)) for p in discovered]
    assert "openapi.json" in discovered_rel, f"openapi.json was not discovered by find_spec_files: {discovered_rel}"

    # Contract content check
    with open(SPEC_PATH, "r", encoding="utf-8") as f:
        spec = json.load(f)

    assert spec.get("openapi", "").startswith("3."), f"Expected OpenAPI 3.x, got {spec.get('openapi')}"
    assert "paths" in spec
    paths = spec["paths"]

    # Verify key demo routes exist in contract
    expected_paths = [
        "/health",
        "/api/backend/health",
        "/api/backend/projects",
        "/api/backend/projects/{project_id}",
        "/api/backend/projects/{project_id}/dependencies",
        "/api/broken/invalid-path",
        "/api/broken/method-mismatch",
        "/api/broken/payload-mismatch",
    ]
    for ep in expected_paths:
        assert ep in paths, f"Path '{ep}' missing from openapi.json"

    # Verify request & response schemas
    assert "components" in spec and "schemas" in spec["components"]
    assert "CreateProjectRequest" in spec["components"]["schemas"]
    create_req_schema = spec["components"]["schemas"]["CreateProjectRequest"]
    assert "name" in create_req_schema.get("required", [])
    assert create_req_schema["properties"]["name"]["type"] == "string"


# =============================================================================
# 2. Defect 1: Client Calls Wrong Endpoint Path
# =============================================================================

def test_defect_1_path_mismatch_drift(test_client, backend_client):
    """
    Defect 1: Client calls non-existent route '/api/v1/nonexistent-service'.
    Expected contract specifies valid upstream health integration.
    Verifies upstream 404, demo 502 Bad Gateway, and diagnostic error evidence.
    """
    # Direct client call to upstream
    raw_resp = backend_client.call_invalid_path()
    assert raw_resp.status_code == 404

    # Demo API endpoint wrapping the client call
    resp = test_client.get("/api/broken/invalid-path")
    assert resp.status_code == 502
    data = resp.json()
    assert "detail" in data
    detail = data["detail"]
    assert detail["error"] == "upstream_path_not_found"
    assert detail["upstream_status"] == 404
    assert "/api/v1/nonexistent-service" in detail["target_url"]


# =============================================================================
# 3. Defect 2: Client Uses Wrong HTTP Method
# =============================================================================

def test_defect_2_method_mismatch_drift(test_client, backend_client):
    """
    Defect 2: Client sends POST to GET-only upstream '/api/v1/health'.
    Expected contract specifies GET for health verification.
    Verifies upstream 405, demo 502 Bad Gateway, and AST reconciliation discrepancy.
    """
    # Direct client call to upstream
    raw_resp = backend_client.call_method_mismatch()
    assert raw_resp.status_code == 405

    # Demo API endpoint wrapping the client call
    resp = test_client.post("/api/broken/method-mismatch")
    assert resp.status_code == 502
    data = resp.json()
    assert "detail" in data
    detail = data["detail"]
    assert detail["error"] == "upstream_method_not_allowed"
    assert detail["method_used"] == "POST"
    assert detail["upstream_status"] == 405

    # Verify AST scanner reconciles contract method GET vs code method POST
    scanner = EndpointScanner(repo_root=DEMO_DIR)
    reconciled, discrepancies, _, _, _ = scanner.scan()

    disc_types = {(d.discrepancy_type, d.endpoint_path, d.method) for d in discrepancies}
    # openapi.json has GET /api/broken/method-mismatch -> ghost_endpoint (not in code AST)
    assert ("ghost_endpoint", "/api/broken/method-mismatch", "GET") in disc_types, (
        f"Expected ghost_endpoint for GET /api/broken/method-mismatch, found {disc_types}"
    )
    # main.py has POST /api/broken/method-mismatch -> undocumented_endpoint (not in openapi.json)
    assert ("undocumented_endpoint", "/api/broken/method-mismatch", "POST") in disc_types, (
        f"Expected undocumented_endpoint for POST /api/broken/method-mismatch, found {disc_types}"
    )


# =============================================================================
# 4. Defect 3: Client Sends Field with Wrong Name / Type
# =============================================================================

def test_defect_3_payload_schema_mismatch_drift(test_client, backend_client):
    """
    Defect 3: Client sends payload missing required 'name' field and passes invalid numeric/extra keys.
    Expected contract requires CreateProjectRequest with 'name' (string).
    Verifies upstream 400 Bad Request, demo 502 Bad Gateway, and structured validation details.
    """
    # Direct client call to upstream
    raw_resp = backend_client.call_payload_mismatch()
    assert raw_resp.status_code in {400, 422}
    err_body = raw_resp.json()
    # Check that error indicates missing required field
    err_str = json.dumps(err_body)
    assert "name" in err_str or "missing" in err_str

    # Demo API endpoint wrapping the client call
    resp = test_client.post("/api/broken/payload-mismatch")
    assert resp.status_code == 502
    data = resp.json()
    assert "detail" in data
    detail = data["detail"]
    assert detail["error"] == "upstream_payload_validation_failed"
    assert detail["upstream_status"] in {400, 422}
    assert "upstream_response" in detail


# =============================================================================
# 5. Working Endpoints Remain Functional
# =============================================================================

def test_working_endpoints_unaffected(test_client):
    """Verify that all working integrations remain fully operational."""
    # Self health
    r1 = test_client.get("/health")
    assert r1.status_code == 200
    assert r1.json()["status"] == "ok"

    # Upstream backend health
    r2 = test_client.get("/api/backend/health")
    assert r2.status_code == 200
    assert r2.json()["status"] == "connected"

    # Upstream projects list
    r3 = test_client.get("/api/backend/projects")
    assert r3.status_code == 200
    assert r3.json()["status"] == "success"

    # Upstream project create
    r4 = test_client.post(
        "/api/backend/projects",
        json={"name": "Contract Drift Test Project", "description": "Verification"},
    )
    assert r4.status_code == 201
    assert r4.json()["status"] == "created"


# =============================================================================
# 6. Algorithmic Detector Rule Assertions for Contract Differences
# =============================================================================

def test_algorithmic_detector_drift_rules():
    """Verify AlgorithmicDetectionEngine detects intentional contract deviations."""
    with open(SPEC_PATH, "r", encoding="utf-8") as f:
        baseline_spec = json.load(f)

    # Create a synthetic drifted spec: remove a path, change method, alter schema
    drifted_spec = json.loads(json.dumps(baseline_spec))
    # 1. Remove path
    del drifted_spec["paths"]["/api/backend/projects/{project_id}"]
    # 2. Modify method on /api/backend/health from GET to POST
    drifted_spec["paths"]["/api/backend/health"] = {
        "post": drifted_spec["paths"]["/api/backend/health"]["get"]
    }
    # 3. Add newly required field 'organization_id' to CreateProjectRequest
    drifted_spec["components"]["schemas"]["CreateProjectRequest"]["required"].append("organization_id")
    drifted_spec["components"]["schemas"]["CreateProjectRequest"]["properties"]["organization_id"] = {
        "type": "string"
    }

    engine = AlgorithmicDetectionEngine()
    findings = engine.detect(baseline_spec, drifted_spec)

    rule_ids = {f.rule_id for f in findings}
    assert RuleId.PATH_REMOVED.value in rule_ids
    assert RuleId.METHOD_REMOVED.value in rule_ids
    assert RuleId.REQUIRED_FIELD_ADDED.value in rule_ids
