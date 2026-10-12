# Dependency Guardian — Repository Dependency Report

**Scanned Repository Path:** `/home/last-hope/Dnyaneshwar/HackWave/demo`  
**Scan Timestamp:** `2026-10-11T19:21:15.989294+00:00`  
**Scanner Engine:** `Dependency Guardian Repository Intelligence v0.2.0`  

## 1. Executive Summary

| Metric | Count | Note |
|---|---|---|
| **Total Declared Dependencies** | 6 | Discovered across manifests and lockfiles |
| **Active Dependencies in Code** | 3 | Imported or required in source code |
| **Declared but Unused Packages** | 3 | Potential cleanup candidates |
| **Internal Modules** | 26 | Local architectural modules |
| **External Integrations** | 0 | Databases, queues, HTTP clients, SDKs |

---

## 2. External Dependencies Inventory

All discovered third-party libraries, version constraints, resolved lockfile versions, purposes, and usage sites:

| Package Name | Ecosystem | Declared Constraint | Resolved Version | Used in Code | Purpose | Documentation URL | Vulnerabilities |
|---|---|---|---|:---:|---|---|---|
| **fastapi** | python | `>=0.110.0` | *Unresolved* | ✅ Yes | High-performance asynchronous web framework for building APIs | [Docs](https://fastapi.tiangolo.com/) | None verified |
| **pydantic** | python | `>=2.7.0` | *Unresolved* | ✅ Yes | Data validation and settings management using Python type annotations | [Docs](https://docs.pydantic.dev/) | None verified |
| **pytest** | python | `>=8.0.0` | *Unresolved* | ✅ Yes | Testing framework supporting unit, functional, and integration tests | [Docs](https://docs.pytest.org/) | None verified |
| **httpx** | python | `>=0.27.0` | *Unresolved* | ⚠️ No | Next-generation HTTP client with async support and HTTP/2 | [Docs](https://www.python-httpx.org/) | None verified |
| **pyyaml** | python | `>=6.0` | *Unresolved* | ⚠️ No | YAML parser and emitter for Python | [Docs](https://pyyaml.org/) | None verified |
| **uvicorn** | python | `>=0.28.0` | *Unresolved* | ⚠️ No | Lightning-fast ASGI web server implementation for Python | [Docs](https://www.uvicorn.org/) | None verified |

### Dependency Usage Sites (Top Imported Packages)

#### `fastapi` (22 import sites)
- `sample-api/versions/v1/app/main.py:2`: `from fastapi import FastAPI`
- `sample-api/versions/v1/app/api/payments.py:2`: `from fastapi import APIRouter, Depends, status`
- `sample-api/versions/v1/app/api/users.py:3`: `from fastapi import APIRouter, Depends, Query`
- `sample-api/versions/v1/app/api/products.py:3`: `from fastapi import APIRouter, Depends, Query`
- `sample-api/versions/v1/app/api/orders.py:3`: `from fastapi import APIRouter, Depends, Query`
- *...and 17 more locations.*

#### `pydantic` (10 import sites)
- `sample-api/versions/v1/app/schemas/product.py:3`: `from pydantic import BaseModel, ConfigDict, Field`
- `sample-api/versions/v1/app/schemas/payment.py:2`: `from pydantic import BaseModel, ConfigDict, Field`
- `sample-api/versions/v1/app/schemas/order.py:3`: `from pydantic import BaseModel, ConfigDict, Field`
- `sample-api/versions/v1/app/schemas/user.py:3`: `from pydantic import BaseModel, ConfigDict, Field`
- `sample-api/versions/v1/app/core/config.py:2`: `from pydantic import BaseModel`
- *...and 5 more locations.*

#### `pytest` (5 import sites)
- `sample-api/tests/test_v1_api.py:2`: `import pytest`
- `sample-api/tests/test_detection_assertions.py:7`: `import pytest`
- `sample-api/tests/test_v2_api.py:2`: `import pytest`
- `sample-api/generated-tests/test_candidate_regression_v2.py:6`: `import pytest`
- `sample-api/generated-tests/test_approved_regression_v2.py:6`: `import pytest`

---

## 3. Declared but Unused Dependencies

> [!NOTE]
> The following packages are declared in dependency manifests but were not found imported or required anywhere in the scanned source code. Consider removing them to reduce attack surface and build times.

- ⚠️ **httpx** — Declared in manifest but has 0 import references
- ⚠️ **pyyaml** — Declared in manifest but has 0 import references
- ⚠️ **uvicorn** — Declared in manifest but has 0 import references

---

## 4. Internal Module Architecture

Local packages and modules detected within the repository:

- `config`
- `conftest`
- `generate_contracts`
- `main`
- `order`
- `order_repository`
- `order_service`
- `orders`
- `payment`
- `payment_repository`
- `payment_service`
- `payments`
- `product`
- `product_repository`
- `product_service`
- `products`
- `sample-api`
- `test_approved_regression_v2`
- `test_candidate_regression_v2`
- `test_detection_assertions`
- `test_v1_api`
- `test_v2_api`
- `user`
- `user_repository`
- `user_service`
- `users`

---

## 5. External Services and Integrations

> [!IMPORTANT]
> All external service interfaces, outbound HTTP calls, database clients, SDKs, and message brokers are inventoried below.
> **Secret Safety Verification:** All credential strings, tokens, and passwords have been strictly sanitized and redacted.

| Integration Type | Service Name | Target / Host | File Location | Detected Operations | Redacted Secrets |
|---|---|---|---|---|:---:|
| *None* | No external integrations detected | - | - | - | 0 |

---

## 6. Scanner Limitations and Skipped Files

✅ All discoverable source files and manifests were successfully parsed.
