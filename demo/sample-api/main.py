"""
Dependency Guardian Localhost Integration Demo API.

A minimal FastAPI application containing ONLY APIs that call the existing
Dependency Guardian backend running at http://localhost:<backend-port>.

Includes:
- Working localhost-backed integrations (health, projects listing, project details, creation).
- 3 Intentionally broken integrations:
    1. GET  /api/broken/invalid-path     -> calls nonexistent upstream path (404)
    2. POST /api/broken/method-mismatch  -> calls GET-only upstream health with POST (405)
    3. POST /api/broken/payload-mismatch -> calls upstream project creation with invalid payload (400)
"""
import os
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
import httpx

try:
    from .client import BackendIntegrationClient, BACKEND_URL
except (ImportError, ValueError):
    from client import BackendIntegrationClient, BACKEND_URL

# Request model for project creation
class CreateProjectRequest(BaseModel):
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Optional description")
    repository_url: Optional[str] = Field("https://github.com/demo/sample-repo", description="Repository URL")


# FastAPI App and Integration Client Initialization
"""Factory creating the minimal localhost-backed demo FastAPI app."""
app = FastAPI(
    title="Dependency Guardian Localhost Integration Demo",
    description="Minimal demo service calling Dependency Guardian backend at http://localhost:8000.",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

client = BackendIntegrationClient()

# =========================================================================
# Service Self Health Check
# =========================================================================

@app.get("/health", tags=["System"], summary="Demo service health check")
def self_health():
    return {
        "status": "ok",
        "service": "dependency-guardian-demo-api",
        "configured_backend_url": client.base_url,
    }

# =========================================================================
# Working Localhost-Backed Integrations
# =========================================================================

@app.get("/api/backend/health", tags=["Working Integrations"], summary="Verify upstream backend health")
def backend_health():
    """Working API 1: Queries upstream GET /api/v1/health."""
    try:
        data = client.get_health()
        return {
            "status": "connected",
            "backend_service": data.get("service", "dependency-guardian-backend"),
            "backend_version": data.get("version"),
            "upstream_url": f"{client.base_url}/api/v1/health",
            "raw_response": data,
        }
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Upstream Guardian backend unreachable at {client.base_url}: connection refused",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Upstream Guardian backend timed out at {client.base_url}",
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream returned HTTP {exc.response.status_code}: {exc.response.text}",
        )

@app.get("/api/backend/projects", tags=["Working Integrations"], summary="List projects from upstream backend")
def backend_projects():
    """Working API 2: Queries upstream GET /api/v1/projects."""
    try:
        data = client.list_projects()
        return {
            "status": "success",
            "upstream_url": f"{client.base_url}/api/v1/projects",
            "total": data.get("total", 0),
            "items": data.get("items", []),
        }
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Upstream Guardian backend unreachable at {client.base_url}",
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream error: {exc.response.text}",
        )

@app.post("/api/backend/projects", tags=["Working Integrations"], summary="Create a project on upstream backend", status_code=status.HTTP_201_CREATED)
def backend_create_project(req: CreateProjectRequest):
    """Working API 3: Posts valid ProjectCreate payload to upstream POST /api/v1/projects."""
    try:
        created = client.create_project(
            name=req.name,
            description=req.description,
            repo_url=req.repository_url,
        )
        return {
            "status": "created",
            "upstream_url": f"{client.base_url}/api/v1/projects",
            "project": created,
        }
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Upstream Guardian backend unreachable at {client.base_url}",
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream error creating project: {exc.response.text}",
        )

@app.get("/api/backend/projects/{project_id}", tags=["Working Integrations"], summary="Get project details from upstream backend")
def backend_get_project(project_id: str):
    """Working API 4: Queries upstream GET /api/v1/projects/{project_id}."""
    try:
        data = client.get_project(project_id)
        return {
            "status": "success",
            "upstream_url": f"{client.base_url}/api/v1/projects/{project_id}",
            "project": data,
        }
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Upstream Guardian backend unreachable at {client.base_url}",
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found on upstream backend",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream error: {exc.response.text}",
        )

@app.get("/api/backend/projects/{project_id}/dependencies", tags=["Working Integrations"], summary="List dependencies from upstream backend")
def backend_project_dependencies(project_id: str):
    """Working API 5: Queries upstream GET /api/v1/projects/{project_id}/dependencies."""
    try:
        data = client.get_project_dependencies(project_id)
        return {
            "status": "success",
            "upstream_url": f"{client.base_url}/api/v1/projects/{project_id}/dependencies",
            "dependencies": data,
        }
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Upstream Guardian backend unreachable at {client.base_url}",
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream error: {exc.response.text}",
        )

# =========================================================================
# Intentionally Broken Integrations (Simulating broken external contracts)
# =========================================================================

@app.get("/api/broken/invalid-path", tags=["Broken Integrations"], summary="Broken: Calls non-existent upstream path")
def broken_invalid_path():
    """
    Broken API 1 (Incorrect URL / Path):
    Calls upstream GET /api/v1/nonexistent-service which does not exist on the backend.
    The upstream backend returns HTTP 404 Not Found.
    This endpoint catches the upstream failure and returns HTTP 502 with diagnostic details.
    """
    resp = client.call_invalid_path()
    if resp.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "upstream_path_not_found",
                "target_url": f"{client.base_url}/api/v1/nonexistent-service",
                "upstream_status": 404,
                "message": "Configured upstream path '/api/v1/nonexistent-service' was not found on backend (404 Not Found).",
            },
        )
    return resp.json()

@app.post("/api/broken/method-mismatch", tags=["Broken Integrations"], summary="Broken: Calls upstream route with incorrect HTTP method")
def broken_method_mismatch():
    """
    Broken API 2 (Incorrect HTTP Method):
    Calls upstream POST /api/v1/health. The backend health endpoint only supports GET.
    The upstream backend returns HTTP 405 Method Not Allowed.
    This endpoint catches the upstream failure and returns HTTP 502 with diagnostic details.
    """
    resp = client.call_method_mismatch()
    if resp.status_code == 405:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "upstream_method_not_allowed",
                "target_url": f"{client.base_url}/api/v1/health",
                "method_used": "POST",
                "upstream_status": 405,
                "message": "Upstream endpoint does not support POST method (405 Method Not Allowed).",
            },
        )
    return resp.json()

@app.post("/api/broken/payload-mismatch", tags=["Broken Integrations"], summary="Broken: Sends invalid payload schema to upstream route")
def broken_payload_mismatch():
    """
    Broken API 3 (Incorrect Payload Schema):
    Calls upstream POST /api/v1/projects with a payload missing the mandatory 'name' attribute.
    The upstream backend Pydantic validator rejects the schema and returns HTTP 400 Bad Request.
    This endpoint catches the validation failure and returns HTTP 502 with diagnostic details.
    """
    resp = client.call_payload_mismatch()
    if resp.status_code in {400, 422}:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "upstream_payload_validation_failed",
                "target_url": f"{client.base_url}/api/v1/projects",
                "upstream_status": resp.status_code,
                "upstream_response": resp.json(),
                "message": "Upstream rejected invalid payload schema (required attribute 'name' missing).",
            },
        )
    return resp.json()


def create_app() -> FastAPI:
    """Factory returning the configured demo FastAPI app."""
    return app



if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("DEMO_API_PORT", "8080"))
    print(f"Starting Dependency Guardian Localhost Integration Demo on http://0.0.0.0:{port}...")
    print(f"Targeting backend at: {BACKEND_URL}")
    uvicorn.run("demo.sample_api.main:app", host="0.0.0.0", port=port, reload=True)
