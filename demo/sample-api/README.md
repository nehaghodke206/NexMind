# Dependency Guardian — Minimal Localhost Integration Demo API

A minimal, focused FastAPI demo application containing **only APIs that call the existing Dependency Guardian backend at `http://localhost:<backend-port>`**. Unrelated demo functionality (such as mock e-commerce users, products, orders, and payments) has been removed.

When Dependency Guardian runs repository intelligence (`dependency-guardian scan-repo`), its Abstract Syntax Tree (AST) scanner discovers these outbound HTTP calls as external API integrations connecting to the local backend.

---

## 1. Architecture Overview

The demo consists of a lightweight service calling the live Dependency Guardian backend:

```
demo/sample-api/
├── client.py                       # BackendIntegrationClient issuing outbound httpx calls
├── main.py                         # FastAPI app exposing localhost-backed & broken endpoints
├── openapi.json                    # Canonical OpenAPI 3.1.0 contract specification
├── dependency-guardian.yml         # Probe definitions and authorized demo targets
├── run_demo.sh                     # Automated test & scanner demo runner
├── tests/
│   ├── conftest.py                 # Pytest configuration
│   ├── test_contract_drift.py      # Contract drift & defect verification tests
│   ├── test_detection_assertions.py # Algorithmic & orchestrator diff assertions
│   └── test_localhost_integrations.py # Pytest suite for working and broken endpoints
├── requirements.txt                # Demo requirements (fastapi, httpx, uvicorn, pytest)
└── README.md                       # This documentation
```

### Configuration Settings

| Environment Variable | Default Value | Description |
| :--- | :--- | :--- |
| `GUARDIAN_BACKEND_URL` | `http://localhost:8000` | Target URL of the running Dependency Guardian backend |
| `GUARDIAN_BACKEND_TIMEOUT` | `5.0` | HTTP request timeout in seconds |
| `DEMO_API_PORT` | `8080` | Local port on which this demo API listens |

---

## 2. API Endpoints Catalog

### A. Working Localhost-Backed Integrations

These endpoints make genuine requests to the running backend service and succeed with HTTP 200 / 201:

| Method & Route | Target Backend URL | Description | Expected Status |
| :--- | :--- | :--- | :--- |
| `GET /health` | *Internal* | Demo API self-health check | `200 OK` |
| `GET /api/backend/health` | `GET http://localhost:8000/api/v1/health` | Verifies live connectivity with upstream backend | `200 OK` |
| `GET /api/backend/projects` | `GET http://localhost:8000/api/v1/projects` | Lists registered projects from upstream database | `200 OK` |
| `POST /api/backend/projects` | `POST http://localhost:8000/api/v1/projects` | Creates a new project with valid schema | `201 Created` |
| `GET /api/backend/projects/{id}` | `GET http://localhost:8000/api/v1/projects/{id}` | Retrieves specific project details | `200 OK` |
| `GET /api/backend/projects/{id}/dependencies` | `GET http://localhost:8000/api/v1/projects/{id}/dependencies` | Queries dependencies of a project | `200 OK` |

---

### B. Intentionally Broken Integrations (Simulating Broken Contracts)

Three endpoints intentionally simulate broken third-party external integrations:

| Defect | Route & Method | Defect Mechanism | Upstream Behavior | Demo App Response |
| :--- | :--- | :--- | :--- | :--- |
| **1. Incorrect Path / URL** | `GET /api/broken/invalid-path` | Calls `/api/v1/nonexistent-service` which does not exist | Upstream returns `404 Not Found` | `502 Bad Gateway` with structured upstream 404 diagnosis |
| **2. Incorrect HTTP Method** | `POST /api/broken/method-mismatch` | Sends `POST` to backend `/api/v1/health` (which only supports `GET`) | Upstream returns `405 Method Not Allowed` | `502 Bad Gateway` with structured upstream 405 diagnosis |
| **3. Incorrect Payload Schema** | `POST /api/broken/payload-mismatch` | Sends payload missing mandatory `name` field to `POST /api/v1/projects` | Upstream Pydantic validator rejects schema with `400 Bad Request` | `502 Bad Gateway` with upstream schema error details |

---

## 3. How to Run the Demo

### Step 1: Ensure Upstream Backend is Running

Start the Dependency Guardian backend service (if not already running):

```bash
cd services/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Verify backend health:
```bash
curl http://localhost:8000/api/v1/health
# {"status":"ok","version":"1.1.0"}
```

### Step 2: Start the Demo API

In a new terminal:

```bash
cd demo/sample-api
python3 main.py
```

*Or using uvicorn:*
```bash
uvicorn demo.sample_api.main:app --host 0.0.0.0 --port 8080 --reload
```

The interactive OpenAPI documentation will be available at:
`http://localhost:8080/docs`

---

## 4. Reproducing Each Endpoint via cURL

### A. Testing Working Endpoints

#### 1. Check Demo Service Health
```bash
curl -i http://localhost:8080/health
```

#### 2. Query Upstream Backend Health
```bash
curl -i http://localhost:8080/api/backend/health
```
**Response (HTTP 200):**
```json
{
  "status": "connected",
  "backend_service": "dependency-guardian-backend",
  "backend_version": "1.1.0",
  "upstream_url": "http://localhost:8000/api/v1/health",
  "raw_response": {
    "status": "ok",
    "version": "1.1.0"
  }
}
```

#### 3. List Projects from Upstream Backend
```bash
curl -i http://localhost:8080/api/backend/projects
```

#### 4. Create a Project on Upstream Backend
```bash
curl -i -X POST http://localhost:8080/api/backend/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Demo Evaluation Service",
    "description": "Integration test created from demo-api",
    "repository_url": "https://github.com/demo/eval-repo"
  }'
```

---

### B. Reproducing Intentionally Broken Endpoints

#### Broken API 1: Incorrect URL / Path (Upstream 404)
Calls non-existent route `/api/v1/nonexistent-service` on the backend:

```bash
curl -i http://localhost:8080/api/broken/invalid-path
```
**Response (HTTP 502 Bad Gateway):**
```json
{
  "detail": {
    "error": "upstream_path_not_found",
    "target_url": "http://localhost:8000/api/v1/nonexistent-service",
    "upstream_status": 404,
    "message": "Configured upstream path '/api/v1/nonexistent-service' was not found on backend (404 Not Found)."
  }
}
```

#### Broken API 2: Incorrect HTTP Method (Upstream 405)
Sends a `POST` request to `/api/v1/health` (which only supports `GET`):

```bash
curl -i -X POST http://localhost:8080/api/broken/method-mismatch
```
**Response (HTTP 502 Bad Gateway):**
```json
{
  "detail": {
    "error": "upstream_method_not_allowed",
    "target_url": "http://localhost:8000/api/v1/health",
    "method_used": "POST",
    "upstream_status": 405,
    "message": "Upstream endpoint does not support POST method (405 Method Not Allowed)."
  }
}
```

#### Broken API 3: Incorrect Payload Schema (Upstream 400)
Sends an invalid payload missing the required `name` attribute to `POST /api/v1/projects`:

```bash
curl -i -X POST http://localhost:8080/api/broken/payload-mismatch
```
**Response (HTTP 502 Bad Gateway):**
```json
{
  "detail": {
    "error": "upstream_payload_validation_failed",
    "target_url": "http://localhost:8000/api/v1/projects",
    "upstream_status": 400,
    "upstream_response": {
      "error": "bad_request",
      "message": "Invalid request payload",
      "details": {
        "errors": [
          {
            "type": "missing",
            "loc": ["body", "name"],
            "msg": "Field required",
            "input": {"unsupported_key": "bad_data", "invalid_numeric": 9999}
          }
        ]
      }
    },
    "message": "Upstream rejected invalid payload schema (required attribute 'name' missing)."
  }
}
```

---

## 5. API Contract & Contract Drift Testing

The demo app includes an explicit OpenAPI 3.1.0 contract specification at `demo/sample-api/openapi.json`. Dependency Guardian automatically discovers and loads this contract during repository intelligence scans (`scan-repo`) and live probe validation (`validate-api`).

### The 3 Intentional Contract Mismatches

| Defect | Route & Integration | Expected Contract | Actual Implementation | Scan Finding & Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **1. Path Mismatch** | `GET /api/broken/invalid-path` | Valid upstream endpoint returning `200 OK` | `client.py` calls non-existent path `/api/v1/nonexistent-service`, upstream returns `404`, demo returns `502` | `RULE-API-SERVER-FAILURE` with `upstream_status: 404`, `target_url: http://localhost:8000/api/v1/nonexistent-service` |
| **2. HTTP Method Mismatch** | `POST /api/broken/method-mismatch` | `openapi.json` expects `GET /api/broken/method-mismatch` | `main.py` defines `POST`, `client.py` sends `POST` to `GET`-only `/api/v1/health` (upstream `405`) | AST reconciliation detects `ghost_endpoint` for `GET` & `undocumented_endpoint` for `POST`. Live call returns `502` with `method_used: POST`, `upstream_status: 405`. |
| **3. Request Payload Mismatch** | `POST /api/broken/payload-mismatch` | `CreateProjectRequest` requiring `name: string` | `client.py` sends `{"unsupported_key": "bad_data", "invalid_numeric": 9999}` omitting required `name` | Upstream Pydantic validator returns `400/422`, demo returns `502` with structured missing field evidence. |

---

## 6. How to Scan for Drift and Identify Intentional Defects

### Step A: Repository AST & Contract Reconciliation Scan

Run the repository intelligence scanner on `demo/sample-api`:

```bash
python3 -m dependency_guardian.cli scan-repo demo/sample-api --format summary
```

**What Dependency Guardian Detects:**
- Discovers `openapi.json` automatically and parses declared routes and schemas.
- AST scans Python source files (`main.py`, `client.py`) to discover implemented routes and outbound integrations.
- Identifies **hybrid matches** for working endpoints and flags contract drift discrepancies:
  - `ghost_endpoint`: `GET /api/broken/method-mismatch` is documented in `openapi.json` but missing in code AST.
  - `undocumented_endpoint`: `POST /api/broken/method-mismatch` is implemented in `main.py` but missing in `openapi.json`.
- Maps external HTTP calls to `http://localhost:8000` in `reports/repository-inventory/INTEGRATION_MAP.md`.

### Step B: Safe Live External API Contract Validation

Run live probe validation against configured demo targets in `dependency-guardian.yml`:

```bash
python3 -m dependency_guardian.cli validate-api demo/sample-api/dependency-guardian.yml --format summary
```

**What Dependency Guardian Detects:**
- Probes authorized localhost targets (`http://localhost:8080`, `http://localhost:8000`).
- Validates that working endpoints return `200 OK` with required response schema fields.
- Reports `server_failure` on `http://localhost:8080/api/broken/invalid-path` with rule:
  - `[HIGH] RULE-API-SERVER-FAILURE`: Upstream service returned `502` due to non-existent route `/api/v1/nonexistent-service` (404 Not Found).

### Step C: Algorithmic Specification Diff

To compare baseline vs. drifted OpenAPI specifications:

```bash
python3 -m dependency_guardian.cli demo/sample-api/contracts/openapi-v1.json demo/sample-api/contracts/openapi-v2.json --format summary
```

---

## 7. Automated Testing

Run the full automated test suite covering working integrations, contract drift detection, and algorithmic assertions:

```bash
PYTHONPATH="agents/detection:demo/sample-api:." pytest demo/sample-api/tests -v
```

All 20 tests pass:
- `tests/test_contract_drift.py` (6 tests):
  - `test_openapi_contract_discovery_and_structure`: Verifies `openapi.json` discovery and schema validity.
  - `test_defect_1_path_mismatch_drift`: Verifies Defect 1 (path mismatch, upstream 404 -> demo 502 with evidence).
  - `test_defect_2_method_mismatch_drift`: Verifies Defect 2 (method mismatch, upstream 405 -> demo 502 + AST discrepancy).
  - `test_defect_3_payload_schema_mismatch_drift`: Verifies Defect 3 (payload schema mismatch, upstream 400 -> demo 502 with evidence).
  - `test_working_endpoints_unaffected`: Verifies all working integrations remain healthy (200/201).
  - `test_algorithmic_detector_drift_rules`: Verifies algorithmic detection rules for breaking spec changes.
- `tests/test_localhost_integrations.py` (10 tests): Verifies direct localhost integration and client calls.
- `tests/test_detection_assertions.py` (4 tests): Verifies orchestrator modes and algorithmic diff assertions.

---

## 8. One-Command Demo Runner

To execute the test suite, contract reconciliation scan, and live validation probe in a single command:

```bash
./demo/sample-api/run_demo.sh
```
