"""
Backend API Client for Dependency Guardian Localhost Integration Demo.

This module executes outbound HTTP calls to the running Dependency Guardian
backend service at http://localhost:<port>.

Dependency Guardian's repository scanner identifies these httpx calls
as external HTTP service dependencies and maps their integration endpoints.
"""
import os
from typing import Any, Dict, Optional
import httpx

# Upstream Guardian Backend connection configuration
DEFAULT_BACKEND_URL = "http://localhost:8000"
BACKEND_URL = os.environ.get("GUARDIAN_BACKEND_URL", DEFAULT_BACKEND_URL).rstrip("/")
BACKEND_TIMEOUT = float(os.environ.get("GUARDIAN_BACKEND_TIMEOUT", "5.0"))


class BackendIntegrationClient:
    """Outbound HTTP client calling the local Dependency Guardian backend."""

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        self.base_url = (base_url or BACKEND_URL).rstrip("/")
        self.timeout = timeout or BACKEND_TIMEOUT

    # =========================================================================
    # Working Endpoints (Genuine localhost-backed integrations)
    # =========================================================================

    def get_health(self) -> Dict[str, Any]:
        """
        Working Integration 1: Health Check
        Calls GET http://localhost:8000/api/v1/health.
        Returns HTTP 200 OK with upstream version and service status.
        """
        if self.base_url == DEFAULT_BACKEND_URL:
            resp = httpx.get("http://localhost:8000/api/v1/health", timeout=self.timeout)
        else:
            resp = httpx.get(f"{self.base_url}/api/v1/health", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def list_projects(self) -> Dict[str, Any]:
        """
        Working Integration 2: Project Listing
        Calls GET http://localhost:8000/api/v1/projects.
        Returns HTTP 200 OK with list of registered projects.
        """
        if self.base_url == DEFAULT_BACKEND_URL:
            resp = httpx.get("http://localhost:8000/api/v1/projects", timeout=self.timeout)
        else:
            resp = httpx.get(f"{self.base_url}/api/v1/projects", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def create_project(self, name: str, description: Optional[str] = None, repo_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Working Integration 3: Create Project
        Calls POST http://localhost:8000/api/v1/projects with a valid payload.
        Returns HTTP 201 Created with the new project record.
        """
        payload = {
            "name": name,
            "description": description or f"Demo project created by sample-api",
            "repository_url": repo_url or "https://github.com/demo/sample-repo",
        }
        if self.base_url == DEFAULT_BACKEND_URL:
            resp = httpx.post("http://localhost:8000/api/v1/projects", json=payload, timeout=self.timeout)
        else:
            resp = httpx.post(f"{self.base_url}/api/v1/projects", json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def get_project(self, project_id: str) -> Dict[str, Any]:
        """
        Working Integration 4: Project Details
        Calls GET http://localhost:8000/api/v1/projects/{project_id}.
        Returns HTTP 200 OK with project metadata.
        """
        if self.base_url == DEFAULT_BACKEND_URL:
            resp = httpx.get(f"http://localhost:8000/api/v1/projects/{project_id}", timeout=self.timeout)
        else:
            resp = httpx.get(f"{self.base_url}/api/v1/projects/{project_id}", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def get_project_dependencies(self, project_id: str) -> Dict[str, Any]:
        """
        Working Integration 5: Project Dependencies
        Calls GET http://localhost:8000/api/v1/projects/{project_id}/dependencies.
        Returns HTTP 200 OK with registered dependencies.
        """
        if self.base_url == DEFAULT_BACKEND_URL:
            resp = httpx.get(f"http://localhost:8000/api/v1/projects/{project_id}/dependencies", timeout=self.timeout)
        else:
            resp = httpx.get(f"{self.base_url}/api/v1/projects/{project_id}/dependencies", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    # =========================================================================
    # Intentionally Broken Endpoints (Simulating broken external integrations)
    # =========================================================================

    def call_invalid_path(self) -> httpx.Response:
        """
        Broken Integration 1: Incorrect URL / Path
        Calls GET http://localhost:8000/api/v1/nonexistent-service.
        The upstream backend returns HTTP 404 Not Found because this route does not exist.
        """
        if self.base_url == DEFAULT_BACKEND_URL:
            return httpx.get("http://localhost:8000/api/v1/nonexistent-service", timeout=self.timeout)
        return httpx.get(f"{self.base_url}/api/v1/nonexistent-service", timeout=self.timeout)

    def call_method_mismatch(self) -> httpx.Response:
        """
        Broken Integration 2: Incorrect HTTP Method
        Calls POST http://localhost:8000/api/v1/health.
        The upstream backend's health check only permits GET.
        Sending POST causes upstream to return HTTP 405 Method Not Allowed.
        """
        if self.base_url == DEFAULT_BACKEND_URL:
            return httpx.post("http://localhost:8000/api/v1/health", timeout=self.timeout)
        return httpx.post(f"{self.base_url}/api/v1/health", timeout=self.timeout)

    def call_payload_mismatch(self) -> httpx.Response:
        """
        Broken Integration 3: Incorrect Payload Schema
        Calls POST http://localhost:8000/api/v1/projects with invalid payload missing 'name'.
        The upstream backend expects a valid ProjectCreate schema requiring 'name'.
        Sending wrong attributes causes upstream to reject the request with HTTP 400 Bad Request.
        """
        payload = {"unsupported_key": "bad_data", "invalid_numeric": 9999}
        if self.base_url == DEFAULT_BACKEND_URL:
            return httpx.post("http://localhost:8000/api/v1/projects", json=payload, timeout=self.timeout)
        return httpx.post(f"{self.base_url}/api/v1/projects", json=payload, timeout=self.timeout)
