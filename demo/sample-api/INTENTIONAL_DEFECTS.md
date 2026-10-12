# Dependency Guardian — Demo App Intentional Defects Ground Truth

This document serves as the developer-only ground truth catalog for the intentional API contract drifts and integration defects introduced into `demo/sample-api` (specifically `versions/v2`).

> **Notice:** This document is an offline developer reference fixture. It is isolated from production API endpoints and runtime responses.

---

## Defect Catalog Summary

| Defect ID | Category | Endpoint / Symbol | Affected Source File | Root Cause |
| :--- | :--- | :--- | :--- | :--- |
| **DEFECT-A** | Response Schema Drift | `GET /api/v1/products` & `verify_product_stock_fulfillment` | `versions/v2/app/services/order_service.py` | `stock` removed from response schema; calling consumer accesses `product["stock"]` |
| **DEFECT-B** | Request Contract Mismatch | `GET /api/v1/products` & `fetch_store_inventory` | `versions/v2/app/services/product_service.py` | `store_id` query parameter made mandatory; calling client sends only `category` |
| **DEFECT-C** | Broken External Integration | `GET /api/v1/integrations/backend-telemetry` | `versions/v2/app/api/integrations.py` | Calls non-existent `/api/v1/partner-telemetry` on external Guardian backend (HTTP 404 -> 502) |
| **DEFECT-D** | Incorrect Error Handling | `GET /api/v1/integrations/upstream-sync` | `versions/v2/app/api/integrations.py` | Fails to catch `httpx.TimeoutException`, causing unhandled 500 crashes on slow upstream |
| **DEFECT-E** | Missing / Stale Contract | `GET /api/v1/integrations/internal-diagnostics` & `/api/v1/discounts/validate` | `versions/v2/app/api/integrations.py` & `contracts/openapi-v2.json` | Undocumented code route (`internal-diagnostics`) + Ghost contract route (`discounts/validate`) |

---

## Detailed Defect Specifications

### 1. DEFECT-A: Response Schema Drift (`stock` Removed)
- **Defect ID**: `DEFECT-A`
- **Category**: A (Response schema drift)
- **Affected File**: `demo/sample-api/versions/v2/app/services/order_service.py`
- **Affected Endpoint / Consumer**: `verify_product_stock_fulfillment(product: dict, quantity: int = 1)` & `create_order`
- **Expected Contract**: Baseline OpenAPI v1 `ProductResponse` contains `stock: integer`.
- **Actual Behavior**: In v2, `stock` was removed from `ProductResponse` schema (`RULE-RESPONSE-FIELD-REMOVED`). Consumer in `order_service.py` accessing `product["stock"]` raises `KeyError: 'stock'` or fails when evaluating catalog items.
- **Reproduction Command**:
  ```python
  from demo.sample_api.versions.v2.app.services.order_service import verify_product_stock_fulfillment
  verify_product_stock_fulfillment({"id": 1, "name": "Headphones", "price": 199.99})
  # Raises KeyError: 'stock'
  ```
- **Expected Detector Finding**:
  - Rule: `RULE-RESPONSE-FIELD-REMOVED`
  - Location: `paths./api/v1/products.responses.200.content.application/json.schema.properties.items.properties.stock`
  - Evidence: `{"removed_property": "stock"}`
- **Expected Repair Outcome**:
  - Repair Agent injects safe dictionary access fallback:
    `product.get("stock", 0) >= quantity`
- **Validation Command**:
  ```bash
  pytest demo/sample-api/tests/test_defect_scenarios.py -k "test_defect_a"
  ```

---

### 2. DEFECT-B: Request Contract Mismatch (Missing Required `store_id`)
- **Defect ID**: `DEFECT-B`
- **Category**: B (Request contract mismatch)
- **Affected File**: `demo/sample-api/versions/v2/app/services/product_service.py`
- **Affected Endpoint / Client**: `fetch_store_inventory(client, category: str = "electronics")` calling `GET /api/v1/products`
- **Expected Contract**: In v2, `GET /api/v1/products` requires query parameter `store_id: string`.
- **Actual Behavior**: `fetch_store_inventory` dispatches request with `params={"category": category}`, omitting `store_id`. Endpoint returns `HTTP 422 Unprocessable Entity` (`Field required: store_id`).
- **Reproduction Command**:
  ```python
  from fastapi.testclient import TestClient
  from demo.sample_api.versions.v2.app.main import create_app
  from demo.sample_api.versions.v2.app.services.product_service import fetch_store_inventory

  with TestClient(create_app()) as client:
      resp = fetch_store_inventory(client)
      assert resp.status_code == 422
  ```
- **Expected Detector Finding**:
  - Rule: `RULE-REQUIRED-PARAM-ADDED`
  - Location: `paths./api/v1/products.get.parameters`
  - Evidence: `{"parameter_name": "store_id"}`
- **Expected Repair Outcome**:
  - Repair Agent updates params dictionary with required parameter:
    `params={"category": category, "store_id": "default"}`
- **Validation Command**:
  ```bash
  pytest demo/sample-api/tests/test_defect_scenarios.py -k "test_defect_b"
  ```

---

### 3. DEFECT-C: Broken External Integration (Invalid Route on Third-Party Backend)
- **Defect ID**: `DEFECT-C`
- **Category**: C (Broken internal / external integration)
- **Affected File**: `demo/sample-api/versions/v2/app/api/integrations.py` & `demo/sample-api/versions/v2/app/core/backend_client.py`
- **Affected Endpoint**: `GET /api/v1/integrations/backend-telemetry`
- **Expected Contract**: Upstream third-party Guardian Backend service (`GUARDIAN_BACKEND_URL`) exposes `/api/v1/health` and `/api/v1/projects`.
- **Actual Behavior**: `backend_client.get_upstream_telemetry_broken()` queries non-existent upstream route `/api/v1/partner-telemetry`. The upstream backend returns `HTTP 404 Not Found`. Demo app catches `HTTPStatusError` and maps to `HTTP 502 Bad Gateway` reporting the missing upstream endpoint.
- **Reproduction Command**:
  ```bash
  curl -i http://localhost:8080/api/v1/integrations/backend-telemetry
  # Returns: HTTP 502 Bad Gateway with details:
  # {"detail": {"error": "upstream_route_missing", "upstream_status": 404, "upstream_url": "http://127.0.0.1:8000/api/v1/partner-telemetry"}}
  ```
- **Expected Detector Finding**:
  - AST Scanner identifies outbound HTTP dependency to Guardian Backend.
  - Live API probe returns 502 / upstream contract mismatch.
- **Expected Repair Outcome**:
  - Point the telemetry integration route to valid backend endpoint `/api/v1/health` (or `/api/v1/projects`).
- **Validation Command**:
  ```bash
  pytest demo/sample-api/tests/test_defect_scenarios.py -k "test_defect_c"
  ```

---

### 4. DEFECT-D: Incorrect Error Handling (Unhandled Timeout Crash)
- **Defect ID**: `DEFECT-D`
- **Category**: D (Incorrect error handling)
- **Affected File**: `demo/sample-api/versions/v2/app/api/integrations.py`
- **Affected Endpoint**: `GET /api/v1/integrations/upstream-sync`
- **Expected Behavior**: When upstream service is slow or times out, endpoint must catch `httpx.TimeoutException` and return structured `HTTP 504 Gateway Timeout`.
- **Actual Behavior**: Endpoint invokes `backend_client.sync_upstream_unhandled_timeout` without `try...except httpx.TimeoutException`. When upstream latency exceeds threshold or `timeout_override` is provided, an unhandled `httpx.ReadTimeout` exception crashes the request as HTTP 500.
- **Reproduction Command**:
  ```python
  from fastapi.testclient import TestClient
  from demo.sample_api.versions.v2.app.main import create_app

  with TestClient(create_app()) as client:
      # Overriding timeout to 0.00001s triggers unhandled ReadTimeout
      client.get("/api/v1/integrations/upstream-sync?timeout_override=0.00001")
  ```
- **Expected Detector Finding**:
  - AST Endpoint Scanner identifies unhandled exception path in external HTTP route.
- **Expected Repair Outcome**:
  - Enclose upstream call in `try...except (httpx.TimeoutException, httpx.RequestError)` returning HTTP 504 with JSON detail.
- **Validation Command**:
  ```bash
  pytest demo/sample-api/tests/test_defect_scenarios.py -k "test_defect_d"
  ```

---

### 5. DEFECT-E: Missing or Stale Contract (Discrepancy Drift)
- **Defect ID**: `DEFECT-E`
- **Category**: E (Missing or stale contract)
- **Affected Files**: `demo/sample-api/versions/v2/app/api/integrations.py` and `demo/sample-api/contracts/openapi-v2.json`
- **Affected Endpoints**:
  1. `GET /api/v1/integrations/internal-diagnostics` (implemented in code with `include_in_schema=False`).
  2. `GET /api/v1/discounts/validate` (declared in `openapi-v2.json` but has no matching handler in code).
- **Expected Behavior**: Clean parity between OpenAPI documentation and code implementation.
- **Actual Behavior**:
  - `internal-diagnostics` is an implemented route missing from OpenAPI (`undocumented_endpoint`).
  - `discounts/validate` is a contract route missing from application code (`ghost_endpoint`).
- **Reproduction Command**:
  ```bash
  dependency-guardian scan-repo demo/sample-api/versions/v2/app --format json | jq '.discrepancies'
  ```
- **Expected Detector Finding**:
  - `discrepancy_type: "undocumented_endpoint"` for `/api/v1/integrations/internal-diagnostics`.
  - `discrepancy_type: "ghost_endpoint"` for `/api/v1/discounts/validate`.
- **Expected Repair Outcome**:
  - Synchronize OpenAPI specification with codebase using `generate_contracts.py` or implement missing route.
- **Validation Command**:
  ```bash
  pytest demo/sample-api/tests/test_defect_scenarios.py -k "test_defect_e"
  ```
