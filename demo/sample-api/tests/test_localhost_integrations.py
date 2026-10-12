"""
Automated tests for Dependency Guardian Localhost Integration Demo API.

Verifies:
1. Working integrations connecting to the local backend (http://localhost:8000).
2. The 3 intentionally broken external integrations:
   - Defect 1: Incorrect URL / Path (Upstream 404 -> HTTP 502)
   - Defect 2: Incorrect HTTP Method (Upstream 405 -> HTTP 502)
   - Defect 3: Incorrect Payload Schema (Upstream 400 -> HTTP 502)
"""
import pytest
from fastapi.testclient import TestClient

from demo.sample_api.main import create_app
from demo.sample_api.client import BackendIntegrationClient


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def backend_client():
    return BackendIntegrationClient()


# =============================================================================
# 1. System & Working Integrations Tests
# =============================================================================

def test_self_health(client):
    """Test demo service self-health check."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "dependency-guardian-demo-api"
    assert "configured_backend_url" in data


def test_working_backend_health(client):
    """Test working integration: GET /api/backend/health calls upstream GET /api/v1/health."""
    resp = client.get("/api/backend/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "connected"
    assert "backend_version" in data
    assert "/api/v1/health" in data["upstream_url"]


def test_working_backend_projects_list(client):
    """Test working integration: GET /api/backend/projects calls upstream GET /api/v1/projects."""
    resp = client.get("/api/backend/projects")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "total" in data
    assert isinstance(data["items"], list)
    assert data["total"] >= 1


def test_working_backend_create_and_get_project(client):
    """Test working integration: POST and GET /api/backend/projects."""
    # 1. Create project with valid schema
    create_resp = client.post(
        "/api/backend/projects",
        json={
            "name": "Integration Test Project",
            "description": "Automated test project for localhost demo",
            "repository_url": "https://github.com/demo/test-project",
        },
    )
    assert create_resp.status_code == 201
    create_data = create_resp.json()
    assert create_data["status"] == "created"
    project_id = create_data["project"]["id"]
    assert project_id is not None

    # 2. Get the created project details
    get_resp = client.get(f"/api/backend/projects/{project_id}")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["status"] == "success"
    assert get_data["project"]["id"] == project_id
    assert get_data["project"]["name"] == "Integration Test Project"


def test_working_backend_project_dependencies(client):
    """Test working integration: GET /api/backend/projects/{id}/dependencies."""
    # List projects to get an existing project ID
    list_resp = client.get("/api/backend/projects")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert len(items) > 0
    project_id = items[0]["id"]

    dep_resp = client.get(f"/api/backend/projects/{project_id}/dependencies")
    assert dep_resp.status_code == 200
    data = dep_resp.json()
    assert data["status"] == "success"
    assert isinstance(data["dependencies"], list)


# =============================================================================
# 2. Intentionally Broken Integrations Tests
# =============================================================================

def test_broken_api_1_invalid_path(client):
    """
    Broken API 1 (Incorrect URL / Path):
    Calling /api/broken/invalid-path triggers upstream GET /api/v1/nonexistent-service.
    Asserts HTTP 502 Bad Gateway with structured upstream 404 error diagnosis.
    """
    resp = client.get("/api/broken/invalid-path")
    assert resp.status_code == 502
    data = resp.json()
    assert "detail" in data
    detail = data["detail"]
    assert detail["error"] == "upstream_path_not_found"
    assert detail["upstream_status"] == 404
    assert "nonexistent-service" in detail["target_url"]


def test_broken_api_2_method_mismatch(client):
    """
    Broken API 2 (Incorrect HTTP Method):
    Calling /api/broken/method-mismatch triggers upstream POST /api/v1/health.
    Asserts HTTP 502 Bad Gateway with structured upstream 405 error diagnosis.
    """
    resp = client.post("/api/broken/method-mismatch")
    assert resp.status_code == 502
    data = resp.json()
    assert "detail" in data
    detail = data["detail"]
    assert detail["error"] == "upstream_method_not_allowed"
    assert detail["upstream_status"] == 405
    assert detail["method_used"] == "POST"
    assert "/api/v1/health" in detail["target_url"]


def test_broken_api_3_payload_mismatch(client):
    """
    Broken API 3 (Incorrect Payload Schema):
    Calling /api/broken/payload-mismatch triggers upstream POST /api/v1/projects with invalid payload.
    Asserts HTTP 502 Bad Gateway with structured upstream 400 validation error diagnosis.
    """
    resp = client.post("/api/broken/payload-mismatch")
    assert resp.status_code == 502
    data = resp.json()
    assert "detail" in data
    detail = data["detail"]
    assert detail["error"] == "upstream_payload_validation_failed"
    assert detail["upstream_status"] in {400, 422}
    assert "/api/v1/projects" in detail["target_url"]


# =============================================================================
# 3. Direct BackendIntegrationClient Tests
# =============================================================================

def test_direct_client_health(backend_client):
    """Direct client test for working health check."""
    data = backend_client.get_health()
    assert data["status"] == "ok"
    assert "version" in data


def test_direct_client_broken_calls(backend_client):
    """Direct client test verifying raw HTTP responses from broken endpoints."""
    # Broken 1: Path mismatch returns 404
    r1 = backend_client.call_invalid_path()
    assert r1.status_code == 404

    # Broken 2: Method mismatch returns 405
    r2 = backend_client.call_method_mismatch()
    assert r2.status_code == 405

    # Broken 3: Payload mismatch returns 400
    r3 = backend_client.call_payload_mismatch()
    assert r3.status_code in {400, 422}
