# Dependency Guardian — API Test Coverage Report

Comprehensive test coverage verification across discovered API routes and integrations.

## 1. Executive Coverage Metrics

| Metric | Value | Status |
|---|---|---|
| **Total Discovered Endpoints** | 35 | 100% of discovered routes |
| **Endpoints with Automated Tests** | 35 | Verified by test suite |
| **Endpoints with No Tests (Gaps)** | 0 | Need test implementation |
| **API Endpoint Test Coverage** | **100.0%** | 🟢 Good |
| **Integration Tests Found** | 0 | Integration/external tests |

---

## 2. Endpoint Test Coverage Matrix

| Method | Route Path | Source Location | Discovered Test(s) | Coverage State |
|---|---|---|---|:---:|
| `DELETE` | `/api/v1/products/{product_id}` | `sample-api/contracts/openapi-v1.json:None` | • `sample-api/tests/test_v1_api.py::test_v1_products_crud_and_filtering`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_products_breaking_and_non_breaking_changes`<br>*...and 6 more.* | ✅ Covered |
| `DELETE` | `/api/v1/users/{user_id}` | `sample-api/contracts/openapi-v1.json:None` | • `sample-api/tests/test_v1_api.py::test_v1_users_crud_and_validation`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_users_with_search_and_notes`<br>*...and 2 more.* | ✅ Covered |
| `DELETE` | `/products/{product_id}` | `sample-api/versions/v1/app/api/products.py:53` | • `sample-api/tests/test_v1_api.py::test_v1_products_crud_and_filtering`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_products_breaking_and_non_breaking_changes`<br>*...and 6 more.* | ✅ Covered |
| `DELETE` | `/users/{user_id}` | `sample-api/versions/v2/app/api/users.py:54` | • `sample-api/tests/test_v1_api.py::test_v1_users_crud_and_validation`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_users_with_search_and_notes`<br>*...and 2 more.* | ✅ Covered |
| `GET` | `/api/v1/orders` | `sample-api/contracts/openapi-v1.json:None` | • `sample-api/tests/test_v1_api.py::test_v1_orders_and_validation`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_orders_with_discount` | ✅ Covered |
| `GET` | `/api/v1/orders/{order_id}` | `sample-api/contracts/openapi-v1.json:None` | • `sample-api/tests/test_v1_api.py::test_v1_orders_and_validation`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_orders_with_discount` | ✅ Covered |
| `GET` | `/api/v1/payments/{payment_id}` | `sample-api/contracts/openapi-v1.json:None` | • `sample-api/tests/test_v1_api.py::test_v1_payments_flow`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_payments_breaking_changes`<br>*...and 8 more.* | ✅ Covered |
| `GET` | `/api/v1/payments/{payment_id}/receipt` | `sample-api/contracts/openapi-v1.json:None` | • `sample-api/tests/test_v1_api.py::test_v1_payments_flow`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_payments_breaking_changes`<br>*...and 2 more.* | ✅ Covered |
| `GET` | `/api/v1/products` | `sample-api/contracts/openapi-v1.json:None` | • `sample-api/tests/test_v1_api.py::test_v1_products_crud_and_filtering`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_products_breaking_and_non_breaking_changes`<br>*...and 6 more.* | ✅ Covered |
| `GET` | `/api/v1/products/{product_id}` | `sample-api/contracts/openapi-v1.json:None` | • `sample-api/tests/test_v1_api.py::test_v1_products_crud_and_filtering`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_products_breaking_and_non_breaking_changes`<br>*...and 6 more.* | ✅ Covered |
| `GET` | `/api/v1/users` | `sample-api/contracts/openapi-v1.json:None` | • `sample-api/tests/test_v1_api.py::test_v1_users_crud_and_validation`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_users_with_search_and_notes`<br>*...and 2 more.* | ✅ Covered |
| `GET` | `/api/v1/users/{user_id}` | `sample-api/contracts/openapi-v1.json:None` | • `sample-api/tests/test_v1_api.py::test_v1_users_crud_and_validation`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_users_with_search_and_notes`<br>*...and 2 more.* | ✅ Covered |
| `GET` | `/health` | `sample-api/contracts/openapi-v1.json:None` | • `sample-api/tests/test_v1_api.py::test_v1_health`<br>• `sample-api/tests/test_v2_api.py::test_v2_health` | ✅ Covered |
| `GET` | `/orders` | `sample-api/versions/v2/app/api/orders.py:17` | • `sample-api/tests/test_v1_api.py::test_v1_orders_and_validation`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_orders_with_discount` | ✅ Covered |
| `GET` | `/orders/{order_id}` | `sample-api/versions/v2/app/api/orders.py:34` | • `sample-api/tests/test_v1_api.py::test_v1_orders_and_validation`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_orders_with_discount` | ✅ Covered |
| `GET` | `/payments/{payment_id}` | `sample-api/versions/v2/app/api/payments.py:24` | • `sample-api/tests/test_v1_api.py::test_v1_payments_flow`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_payments_breaking_changes`<br>*...and 8 more.* | ✅ Covered |
| `GET` | `/payments/{payment_id}/receipt` | `sample-api/versions/v1/app/api/payments.py:32` | • `sample-api/tests/test_v1_api.py::test_v1_payments_flow`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_payments_breaking_changes`<br>*...and 2 more.* | ✅ Covered |
| `GET` | `/products` | `sample-api/versions/v2/app/api/products.py:17` | • `sample-api/tests/test_v1_api.py::test_v1_products_crud_and_filtering`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_products_breaking_and_non_breaking_changes`<br>*...and 6 more.* | ✅ Covered |
| `GET` | `/products/{product_id}` | `sample-api/versions/v2/app/api/products.py:39` | • `sample-api/tests/test_v1_api.py::test_v1_products_crud_and_filtering`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_products_breaking_and_non_breaking_changes`<br>*...and 6 more.* | ✅ Covered |
| `GET` | `/users` | `sample-api/versions/v2/app/api/users.py:17` | • `sample-api/tests/test_v1_api.py::test_v1_users_crud_and_validation`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_users_with_search_and_notes`<br>*...and 2 more.* | ✅ Covered |
| `GET` | `/users/{user_id}` | `sample-api/versions/v2/app/api/users.py:37` | • `sample-api/tests/test_v1_api.py::test_v1_users_crud_and_validation`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_users_with_search_and_notes`<br>*...and 2 more.* | ✅ Covered |
| `PATCH` | `/api/v1/orders/{order_id}/status` | `sample-api/contracts/openapi-v1.json:None` | • `sample-api/tests/test_v1_api.py::test_v1_orders_and_validation`<br>• `sample-api/tests/test_v2_api.py::test_v2_orders_with_discount` | ✅ Covered |
| `PATCH` | `/orders/{order_id}/status` | `sample-api/versions/v2/app/api/orders.py:42` | • `sample-api/tests/test_v1_api.py::test_v1_orders_and_validation`<br>• `sample-api/tests/test_v2_api.py::test_v2_orders_with_discount` | ✅ Covered |
| `POST` | `/api/v1/orders` | `sample-api/contracts/openapi-v1.json:None` | • `sample-api/tests/test_v1_api.py::test_v1_orders_and_validation`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_orders_with_discount` | ✅ Covered |
| `POST` | `/api/v1/payments` | `sample-api/contracts/openapi-v1.json:None` | • `sample-api/tests/test_v1_api.py::test_v1_payments_flow`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_payments_breaking_changes`<br>*...and 8 more.* | ✅ Covered |
| `POST` | `/api/v1/products` | `sample-api/contracts/openapi-v1.json:None` | • `sample-api/tests/test_v1_api.py::test_v1_products_crud_and_filtering`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_products_breaking_and_non_breaking_changes`<br>*...and 6 more.* | ✅ Covered |
| `POST` | `/api/v1/users` | `sample-api/contracts/openapi-v1.json:None` | • `sample-api/tests/test_v1_api.py::test_v1_users_crud_and_validation`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_users_with_search_and_notes`<br>*...and 2 more.* | ✅ Covered |
| `POST` | `/orders` | `sample-api/versions/v2/app/api/orders.py:26` | • `sample-api/tests/test_v1_api.py::test_v1_orders_and_validation`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_orders_with_discount` | ✅ Covered |
| `POST` | `/payments` | `sample-api/versions/v2/app/api/payments.py:16` | • `sample-api/tests/test_v1_api.py::test_v1_payments_flow`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_payments_breaking_changes`<br>*...and 8 more.* | ✅ Covered |
| `POST` | `/products` | `sample-api/versions/v2/app/api/products.py:30` | • `sample-api/tests/test_v1_api.py::test_v1_products_crud_and_filtering`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_products_breaking_and_non_breaking_changes`<br>*...and 6 more.* | ✅ Covered |
| `POST` | `/users` | `sample-api/versions/v2/app/api/users.py:29` | • `sample-api/tests/test_v1_api.py::test_v1_users_crud_and_validation`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_users_with_search_and_notes`<br>*...and 2 more.* | ✅ Covered |
| `PUT` | `/api/v1/products/{product_id}` | `sample-api/contracts/openapi-v1.json:None` | • `sample-api/tests/test_v1_api.py::test_v1_products_crud_and_filtering`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_products_breaking_and_non_breaking_changes`<br>*...and 6 more.* | ✅ Covered |
| `PUT` | `/api/v1/users/{user_id}` | `sample-api/contracts/openapi-v1.json:None` | • `sample-api/tests/test_v1_api.py::test_v1_users_crud_and_validation`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_users_with_search_and_notes`<br>*...and 2 more.* | ✅ Covered |
| `PUT` | `/products/{product_id}` | `sample-api/versions/v2/app/api/products.py:47` | • `sample-api/tests/test_v1_api.py::test_v1_products_crud_and_filtering`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_products_breaking_and_non_breaking_changes`<br>*...and 6 more.* | ✅ Covered |
| `PUT` | `/users/{user_id}` | `sample-api/versions/v2/app/api/users.py:45` | • `sample-api/tests/test_v1_api.py::test_v1_users_crud_and_validation`<br>• `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`<br>• `sample-api/tests/test_v2_api.py::test_v2_users_with_search_and_notes`<br>*...and 2 more.* | ✅ Covered |

---

## 3. Discovered Integration Tests

*No dedicated external integration tests detected.*

---

## 4. Identified Test Gaps and Remediation Recommendations

🎉 **Outstanding! All discovered API endpoints have automated test coverage.**
