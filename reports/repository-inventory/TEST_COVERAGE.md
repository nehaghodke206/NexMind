# Dependency Guardian — API Test Coverage Report

Comprehensive test coverage verification across discovered API routes and integrations.

## 1. Executive Coverage Metrics

| Metric | Value | Status |
|---|---|---|
| **Total Discovered Endpoints** | 6 | 100% of discovered routes |
| **Endpoints with Automated Tests** | 3 | Verified by test suite |
| **Endpoints with No Tests (Gaps)** | 3 | Need test implementation |
| **API Endpoint Test Coverage** | **50.0%** | 🟡 Needs Improvement |
| **Integration Tests Found** | 0 | Integration/external tests |

---

## 2. Endpoint Test Coverage Matrix

| Method | Route Path | Source Location | Discovered Test(s) | Coverage State |
|---|---|---|---|:---:|
| `GET` | `/api/v1/health` | `web/server.js:11` | *None* | ❌ **Coverage Gap** |
| `GET` | `/api/v1/legacy-analytics` | `openapi.json:None` | *None* | ❌ **Coverage Gap** |
| `GET` | `/api/v1/users` | `app/main.py:45` | • `tests/test_api.py::test_list_users`<br>• `tests/test_api.py::test_create_user` | ✅ Covered |
| `GET` | `/api/v1/users/{user_id}` | `app/main.py:88` | • `tests/test_api.py::test_create_user` | ✅ Covered |
| `POST` | `/api/v1/orders` | `app/main.py:103` | *None* | ❌ **Coverage Gap** |
| `POST` | `/api/v1/users` | `app/main.py:54` | • `tests/test_api.py::test_create_user` | ✅ Covered |

---

## 3. Discovered Integration Tests

*No dedicated external integration tests detected.*

---

## 4. Identified Test Gaps and Remediation Recommendations

The following endpoints currently lack automated test coverage:

- ⚠️ **`GET /api/v1/health`** (web/server.js) — Missing functional regression tests.
- ⚠️ **`GET /api/v1/legacy-analytics`** (openapi.json) — Missing functional regression tests.
- ⚠️ **`POST /api/v1/orders`** (app/main.py) — Missing functional regression tests.

### Recommendations:
1. Generate automated regression tests using `dependency-guardian --generate-tests`.
2. Add positive tests asserting happy-path response status codes.
3. Add negative tests validating error cases and input validation rules.
