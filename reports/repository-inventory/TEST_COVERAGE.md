# Dependency Guardian — API Test Coverage Report

Comprehensive test coverage verification across discovered API routes and integrations.

## 1. Executive Coverage Metrics

| Metric | Value | Status |
|---|---|---|
| **Total Discovered Endpoints** | 27 | 100% of discovered routes |
| **Endpoints with Automated Tests** | 26 | Verified by test suite |
| **Endpoints with No Tests (Gaps)** | 1 | Need test implementation |
| **API Endpoint Test Coverage** | **96.3%** | 🟢 Good |
| **Integration Tests Found** | 6 | Integration/external tests |

---

## 2. Endpoint Test Coverage Matrix

| Method | Route Path | Source Location | Discovered Test(s) | Coverage State |
|---|---|---|---|:---:|
| `DELETE` | `/api/v1/products/{product_id}` | `contracts/openapi-v1.json:None` | • `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `generated-tests/test_candidate_regression_v2.py::test_regression_required_param_store_id_api_v1_products`<br>• `generated-tests/test_candidate_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`<br>*...and 4 more.* | ✅ Covered |
| `DELETE` | `/api/v1/users/{user_id}` | `contracts/openapi-v1.json:None` | • `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `generated-tests/test_candidate_regression_v2.py::test_regression_optional_param_search_supported`<br>• `generated-tests/test_approved_regression_v2.py::test_regression_optional_param_search_supported` | ✅ Covered |
| `GET` | `/api/backend/health` | `main.py:61` | • `tests/test_localhost_integrations.py::test_self_health`<br>• `tests/test_localhost_integrations.py::test_working_backend_health`<br>• `tests/test_localhost_integrations.py::test_direct_client_health`<br>*...and 5 more.* | ✅ Covered |
| `GET` | `/api/backend/projects` | `main.py:89` | • `tests/test_localhost_integrations.py::test_working_backend_projects_list`<br>• `tests/test_localhost_integrations.py::test_working_backend_create_and_get_project`<br>• `tests/test_localhost_integrations.py::test_working_backend_project_dependencies`<br>*...and 3 more.* | ✅ Covered |
| `GET` | `/api/backend/projects/{project_id}` | `main.py:136` | • `tests/test_localhost_integrations.py::test_working_backend_projects_list`<br>• `tests/test_localhost_integrations.py::test_working_backend_create_and_get_project`<br>• `tests/test_localhost_integrations.py::test_working_backend_project_dependencies`<br>*...and 3 more.* | ✅ Covered |
| `GET` | `/api/backend/projects/{project_id}/dependencies` | `main.py:162` | • `tests/test_localhost_integrations.py::test_working_backend_project_dependencies`<br>• `tests/test_contract_drift.py::test_openapi_contract_discovery_and_structure` | ✅ Covered |
| `GET` | `/api/broken/invalid-path` | `main.py:187` | • `tests/test_localhost_integrations.py::test_broken_api_1_invalid_path`<br>• `tests/test_contract_drift.py::test_openapi_contract_discovery_and_structure`<br>• `tests/test_contract_drift.py::test_defect_1_path_mismatch_drift` | ✅ Covered |
| `GET` | `/api/broken/method-mismatch` | `openapi.json:None` | • `tests/test_localhost_integrations.py::test_broken_api_2_method_mismatch`<br>• `tests/test_contract_drift.py::test_openapi_contract_discovery_and_structure`<br>• `tests/test_contract_drift.py::test_defect_2_method_mismatch_drift` | ✅ Covered |
| `GET` | `/api/v1/orders` | `contracts/openapi-v1.json:None` | • `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions` | ✅ Covered |
| `GET` | `/api/v1/orders/{order_id}` | `contracts/openapi-v1.json:None` | • `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions` | ✅ Covered |
| `GET` | `/api/v1/payments/{payment_id}` | `contracts/openapi-v1.json:None` | • `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `generated-tests/test_candidate_regression_v2.py::test_regression_enum_value_removed_api_v1_payments`<br>• `generated-tests/test_candidate_regression_v2.py::test_regression_required_request_field_api_v1_payments`<br>*...and 6 more.* | ✅ Covered |
| `GET` | `/api/v1/payments/{payment_id}/receipt` | `contracts/openapi-v1.json:None` | • `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `generated-tests/test_candidate_regression_v2.py::test_regression_path_removed_api_v1_payments__payment_id__receipt`<br>• `generated-tests/test_approved_regression_v2.py::test_regression_path_removed_api_v1_payments__payment_id__receipt` | ✅ Covered |
| `GET` | `/api/v1/products` | `contracts/openapi-v1.json:None` | • `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `generated-tests/test_candidate_regression_v2.py::test_regression_required_param_store_id_api_v1_products`<br>• `generated-tests/test_candidate_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`<br>*...and 4 more.* | ✅ Covered |
| `GET` | `/api/v1/products/{product_id}` | `contracts/openapi-v1.json:None` | • `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `generated-tests/test_candidate_regression_v2.py::test_regression_required_param_store_id_api_v1_products`<br>• `generated-tests/test_candidate_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`<br>*...and 4 more.* | ✅ Covered |
| `GET` | `/api/v1/users` | `contracts/openapi-v1.json:None` | • `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `generated-tests/test_candidate_regression_v2.py::test_regression_optional_param_search_supported`<br>• `generated-tests/test_approved_regression_v2.py::test_regression_optional_param_search_supported` | ✅ Covered |
| `GET` | `/api/v1/users/{user_id}` | `contracts/openapi-v1.json:None` | • `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `generated-tests/test_candidate_regression_v2.py::test_regression_optional_param_search_supported`<br>• `generated-tests/test_approved_regression_v2.py::test_regression_optional_param_search_supported` | ✅ Covered |
| `GET` | `/health` | `main.py:49` | • `tests/test_localhost_integrations.py::test_self_health`<br>• `tests/test_localhost_integrations.py::test_working_backend_health`<br>• `tests/test_localhost_integrations.py::test_broken_api_2_method_mismatch`<br>*...and 6 more.* | ✅ Covered |
| `PATCH` | `/api/v1/orders/{order_id}/status` | `contracts/openapi-v1.json:None` | *None* | ❌ **Coverage Gap** |
| `POST` | `/api/backend/projects` | `main.py:111` | • `tests/test_localhost_integrations.py::test_working_backend_projects_list`<br>• `tests/test_localhost_integrations.py::test_working_backend_create_and_get_project`<br>• `tests/test_localhost_integrations.py::test_working_backend_project_dependencies`<br>*...and 3 more.* | ✅ Covered |
| `POST` | `/api/broken/method-mismatch` | `main.py:208` | • `tests/test_localhost_integrations.py::test_broken_api_2_method_mismatch`<br>• `tests/test_contract_drift.py::test_openapi_contract_discovery_and_structure`<br>• `tests/test_contract_drift.py::test_defect_2_method_mismatch_drift` | ✅ Covered |
| `POST` | `/api/broken/payload-mismatch` | `main.py:230` | • `tests/test_localhost_integrations.py::test_broken_api_3_payload_mismatch`<br>• `tests/test_contract_drift.py::test_openapi_contract_discovery_and_structure`<br>• `tests/test_contract_drift.py::test_defect_3_payload_schema_mismatch_drift` | ✅ Covered |
| `POST` | `/api/v1/orders` | `contracts/openapi-v1.json:None` | • `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions` | ✅ Covered |
| `POST` | `/api/v1/payments` | `contracts/openapi-v1.json:None` | • `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `generated-tests/test_candidate_regression_v2.py::test_regression_enum_value_removed_api_v1_payments`<br>• `generated-tests/test_candidate_regression_v2.py::test_regression_required_request_field_api_v1_payments`<br>*...and 6 more.* | ✅ Covered |
| `POST` | `/api/v1/products` | `contracts/openapi-v1.json:None` | • `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `generated-tests/test_candidate_regression_v2.py::test_regression_required_param_store_id_api_v1_products`<br>• `generated-tests/test_candidate_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`<br>*...and 4 more.* | ✅ Covered |
| `POST` | `/api/v1/users` | `contracts/openapi-v1.json:None` | • `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `generated-tests/test_candidate_regression_v2.py::test_regression_optional_param_search_supported`<br>• `generated-tests/test_approved_regression_v2.py::test_regression_optional_param_search_supported` | ✅ Covered |
| `PUT` | `/api/v1/products/{product_id}` | `contracts/openapi-v1.json:None` | • `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `generated-tests/test_candidate_regression_v2.py::test_regression_required_param_store_id_api_v1_products`<br>• `generated-tests/test_candidate_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`<br>*...and 4 more.* | ✅ Covered |
| `PUT` | `/api/v1/users/{user_id}` | `contracts/openapi-v1.json:None` | • `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `generated-tests/test_candidate_regression_v2.py::test_regression_optional_param_search_supported`<br>• `generated-tests/test_approved_regression_v2.py::test_regression_optional_param_search_supported` | ✅ Covered |

---

## 3. Discovered Integration Tests

- 🧪 `tests/test_localhost_integrations.py::test_working_backend_health`
- 🧪 `tests/test_localhost_integrations.py::test_working_backend_projects_list`
- 🧪 `tests/test_localhost_integrations.py::test_working_backend_create_and_get_project`
- 🧪 `tests/test_localhost_integrations.py::test_working_backend_project_dependencies`
- 🧪 `tests/test_contract_drift.py::test_defect_1_path_mismatch_drift`
- 🧪 `tests/test_contract_drift.py::test_working_endpoints_unaffected`

---

## 4. Identified Test Gaps and Remediation Recommendations

The following endpoints currently lack automated test coverage:

- ⚠️ **`PATCH /api/v1/orders/{order_id}/status`** (contracts/openapi-v1.json) — Missing functional regression tests.

### Recommendations:
1. Generate automated regression tests using `dependency-guardian --generate-tests`.
2. Add positive tests asserting happy-path response status codes.
3. Add negative tests validating error cases and input validation rules.
