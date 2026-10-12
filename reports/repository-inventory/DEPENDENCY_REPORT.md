# Dependency Guardian — Repository Dependency Report

**Scanned Repository Path:** `/home/last-hope/Dnyaneshwar/HackWave/demo/sample-api`  
**Scan Timestamp:** `2026-10-12T04:51:26.082097+00:00`  
**Scanner Engine:** `Dependency Guardian Repository Intelligence v0.2.0`  

## 1. Executive Summary

| Metric | Count | Note |
|---|---|---|
| **Total Declared Dependencies** | 6 | Discovered across manifests and lockfiles |
| **Active Dependencies in Code** | 5 | Imported or required in source code |
| **Declared but Unused Packages** | 1 | Potential cleanup candidates |
| **Internal Modules** | 14 | Local architectural modules |
| **External Integrations** | 16 | Databases, queues, HTTP clients, SDKs |

---

## 2. External Dependencies Inventory

All discovered third-party libraries, version constraints, resolved lockfile versions, purposes, and usage sites:

| Package Name | Ecosystem | Declared Constraint | Resolved Version | Used in Code | Purpose | Documentation URL | Vulnerabilities |
|---|---|---|---|:---:|---|---|---|
| **fastapi** | python | `>=0.110.0` | *Unresolved* | ✅ Yes | High-performance asynchronous web framework for building APIs | [Docs](https://fastapi.tiangolo.com/) | None verified |
| **httpx** | python | `>=0.27.0` | *Unresolved* | ✅ Yes | Next-generation HTTP client with async support and HTTP/2 | [Docs](https://www.python-httpx.org/) | None verified |
| **pydantic** | python | `>=2.7.0` | *Unresolved* | ✅ Yes | Data validation and settings management using Python type annotations | [Docs](https://docs.pydantic.dev/) | None verified |
| **pytest** | python | `>=8.0.0` | *Unresolved* | ✅ Yes | Testing framework supporting unit, functional, and integration tests | [Docs](https://docs.pytest.org/) | None verified |
| **uvicorn** | python | `>=0.28.0` | *Unresolved* | ✅ Yes | Lightning-fast ASGI web server implementation for Python | [Docs](https://www.uvicorn.org/) | None verified |
| **pyyaml** | python | `>=6.0` | *Unresolved* | ⚠️ No | YAML parser and emitter for Python | [Docs](https://pyyaml.org/) | None verified |

### Dependency Usage Sites (Top Imported Packages)

#### `fastapi` (5 import sites)
- `main.py:16`: `from fastapi import FastAPI, HTTPException, status`
- `tests/test_localhost_integrations.py:12`: `from fastapi.testclient import TestClient`
- `tests/test_contract_drift.py:16`: `from fastapi.testclient import TestClient`
- `generated-tests/test_candidate_regression_v2.py:7`: `from fastapi.testclient import TestClient`
- `generated-tests/test_approved_regression_v2.py:7`: `from fastapi.testclient import TestClient`

#### `pytest` (5 import sites)
- `tests/test_localhost_integrations.py:11`: `import pytest`
- `tests/test_detection_assertions.py:7`: `import pytest`
- `tests/test_contract_drift.py:15`: `import pytest`
- `generated-tests/test_candidate_regression_v2.py:6`: `import pytest`
- `generated-tests/test_approved_regression_v2.py:6`: `import pytest`

#### `pydantic` (3 import sites)
- `main.py:17`: `from pydantic import BaseModel, Field`
- `versions/v1/app/core/config.py:4`: `from pydantic import BaseModel`
- `versions/v2/app/core/config.py:4`: `from pydantic import BaseModel`

#### `httpx` (2 import sites)
- `client.py:12`: `import httpx`
- `main.py:18`: `import httpx`

#### `uvicorn` (1 import sites)
- `main.py:259`: `import uvicorn`

---

## 3. Declared but Unused Dependencies

> [!NOTE]
> The following packages are declared in dependency manifests but were not found imported or required anywhere in the scanned source code. Consider removing them to reduce attack surface and build times.

- ⚠️ **pyyaml** — Declared in manifest but has 0 import references

---

## 4. Internal Module Architecture

Local packages and modules detected within the repository:

- `client`
- `config`
- `conftest`
- `generate_contracts`
- `generated-tests`
- `main`
- `scripts`
- `test_approved_regression_v2`
- `test_candidate_regression_v2`
- `test_contract_drift`
- `test_detection_assertions`
- `test_localhost_integrations`
- `tests`
- `versions`

---

## 5. External Services and Integrations

> [!IMPORTANT]
> All external service interfaces, outbound HTTP calls, database clients, SDKs, and message brokers are inventoried below.
> **Secret Safety Verification:** All credential strings, tokens, and passwords have been strictly sanitized and redacted.

| Integration Type | Service Name | Target / Host | File Location | Detected Operations | Redacted Secrets |
|---|---|---|---|---|:---:|
| **HTTP_SERVICE** | External HTTP Service | `{var}/api/v1/nonexistent-service` | `client.py:113` | `GET` | 0 (Safe) |
| **HTTP_SERVICE** | External HTTP Service | `{var}/api/v1/health` | `client.py:124` | `POST` | 0 (Safe) |
| **HTTP_SERVICE** | External HTTP Service | `{var}/api/v1/projects` | `client.py:136` | `POST` | 0 (Safe) |
| **HTTP_SERVICE** | External Service (localhost) | `http://localhost:8000/api/v1/health` | `client.py:38` | `GET` | 0 (Safe) |
| **HTTP_SERVICE** | External HTTP Service | `{var}/api/v1/health` | `client.py:40` | `GET` | 0 (Safe) |
| **HTTP_SERVICE** | External Service (localhost) | `http://localhost:8000/api/v1/projects` | `client.py:51` | `GET` | 0 (Safe) |
| **HTTP_SERVICE** | External HTTP Service | `{var}/api/v1/projects` | `client.py:53` | `GET` | 0 (Safe) |
| **HTTP_SERVICE** | External Service (localhost) | `http://localhost:8000/api/v1/projects` | `client.py:69` | `POST` | 0 (Safe) |
| **HTTP_SERVICE** | External HTTP Service | `{var}/api/v1/projects` | `client.py:71` | `POST` | 0 (Safe) |
| **HTTP_SERVICE** | External Service (localhost) | `http://localhost:8000/api/v1/projects/{project_id}` | `client.py:82` | `GET` | 0 (Safe) |
| **HTTP_SERVICE** | External HTTP Service | `{var}/api/v1/projects/{project_id}` | `client.py:84` | `GET` | 0 (Safe) |
| **HTTP_SERVICE** | External Service (localhost) | `http://localhost:8000/api/v1/projects/{project_id}/dependencies` | `client.py:95` | `GET` | 0 (Safe) |
| **HTTP_SERVICE** | External HTTP Service | `{var}/api/v1/projects/{project_id}/dependencies` | `client.py:97` | `GET` | 0 (Safe) |
| **HTTP_SERVICE** | External Service (localhost) | `http://localhost:8000/api/v1/nonexistent-service` | `client.py:112` | `GET` | 0 (Safe) |
| **HTTP_SERVICE** | External Service (localhost) | `http://localhost:8000/api/v1/health` | `client.py:123` | `POST` | 0 (Safe) |
| **HTTP_SERVICE** | External Service (localhost) | `http://localhost:8000/api/v1/projects` | `client.py:135` | `POST` | 0 (Safe) |

---

## 6. Scanner Limitations and Skipped Files

✅ All discoverable source files and manifests were successfully parsed.
