# Dependency Guardian — API Reference Documentation

**Total Discovered Endpoints:** 27  
**Generated On:** `2026-10-12T04:43:41.002458+00:00`  

## Table of Contents

- [`DELETE /api/v1/products/{product_id}`](#delete-apiv1productsproduct_id)
- [`DELETE /api/v1/users/{user_id}`](#delete-apiv1usersuser_id)
- [`GET /api/backend/health`](#get-apibackendhealth)
- [`GET /api/backend/projects`](#get-apibackendprojects)
- [`GET /api/backend/projects/{project_id}`](#get-apibackendprojectsproject_id)
- [`GET /api/backend/projects/{project_id}/dependencies`](#get-apibackendprojectsproject_iddependencies)
- [`GET /api/broken/invalid-path`](#get-apibrokeninvalid-path)
- [`GET /api/broken/method-mismatch`](#get-apibrokenmethod-mismatch)
- [`GET /api/v1/orders`](#get-apiv1orders)
- [`GET /api/v1/orders/{order_id}`](#get-apiv1ordersorder_id)
- [`GET /api/v1/payments/{payment_id}`](#get-apiv1paymentspayment_id)
- [`GET /api/v1/payments/{payment_id}/receipt`](#get-apiv1paymentspayment_idreceipt)
- [`GET /api/v1/products`](#get-apiv1products)
- [`GET /api/v1/products/{product_id}`](#get-apiv1productsproduct_id)
- [`GET /api/v1/users`](#get-apiv1users)
- [`GET /api/v1/users/{user_id}`](#get-apiv1usersuser_id)
- [`GET /health`](#get-health)
- [`PATCH /api/v1/orders/{order_id}/status`](#patch-apiv1ordersorder_idstatus)
- [`POST /api/backend/projects`](#post-apibackendprojects)
- [`POST /api/broken/method-mismatch`](#post-apibrokenmethod-mismatch)
- [`POST /api/broken/payload-mismatch`](#post-apibrokenpayload-mismatch)
- [`POST /api/v1/orders`](#post-apiv1orders)
- [`POST /api/v1/payments`](#post-apiv1payments)
- [`POST /api/v1/products`](#post-apiv1products)
- [`POST /api/v1/users`](#post-apiv1users)
- [`PUT /api/v1/products/{product_id}`](#put-apiv1productsproduct_id)
- [`PUT /api/v1/users/{user_id}`](#put-apiv1usersuser_id)

---

### <a id="delete-apiv1productsproduct_id"></a>`DELETE /api/v1/products/{product_id}`

**Summary:** Delete product  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `contracts/openapi-v1.json:None`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `product_id` | `path` | `integer` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 204** : Successful Response
- **HTTP 422** (`HTTPValidationError`): Validation Error
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `detail` | `array` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_response_field_stock_removed`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_response_field_stock_removed`

---

### <a id="delete-apiv1usersuser_id"></a>`DELETE /api/v1/users/{user_id}`

**Summary:** Delete user  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `contracts/openapi-v1.json:None`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `user_id` | `path` | `integer` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 204** : Successful Response
- **HTTP 422** (`HTTPValidationError`): Validation Error
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `detail` | `array` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_optional_param_search_supported`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_optional_param_search_supported`

---

### <a id="get-apibackendhealth"></a>`GET /api/backend/health`

**Summary:** Verify upstream backend health  
**Description:** Working API 1: Queries upstream GET /api/v1/health on Dependency Guardian backend.  

> [!NOTE]
> **Discovery Method:** `hybrid` | **Evidence:** hybrid_source_and_openapi (main.py:61 & openapi.json)  
> **Handler:** `backend_health` | **Source Location:** `main.py:61`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
*No path, query, header, or cookie parameters required.*

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : Upstream backend is reachable and healthy
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `status` | `string` | Yes | *(Not documented)* |
  | `backend_service` | `string` | Yes | *(Not documented)* |
  | `backend_version` | `string` | No | *(Not documented)* |
  | `upstream_url` | `string` | Yes | *(Not documented)* |
  | `raw_response` | `object` | No | *(Not documented)* |
- **HTTP 502** : Upstream backend unreachable or gateway error

#### Error Cases & Side Effects
**Error Cases:**
- `HTTP 400`: Validation or business logic exception
- `HTTP 400`: Validation or business logic exception
- `HTTP 400`: Validation or business logic exception

#### Verified Test Coverage
- ✅ `tests/test_localhost_integrations.py::test_self_health`
- ✅ `tests/test_localhost_integrations.py::test_working_backend_health`
- ✅ `tests/test_localhost_integrations.py::test_direct_client_health`
- ✅ `tests/test_contract_drift.py::test_openapi_contract_discovery_and_structure`
- ✅ `tests/test_contract_drift.py::test_defect_1_path_mismatch_drift`
- ✅ `tests/test_contract_drift.py::test_defect_2_method_mismatch_drift`
- ✅ `tests/test_contract_drift.py::test_working_endpoints_unaffected`
- ✅ `tests/test_contract_drift.py::test_algorithmic_detector_drift_rules`

---

### <a id="get-apibackendprojects"></a>`GET /api/backend/projects`

**Summary:** List projects from upstream backend  
**Description:** Working API 2: Queries upstream GET /api/v1/projects from Dependency Guardian backend.  

> [!NOTE]
> **Discovery Method:** `hybrid` | **Evidence:** hybrid_source_and_openapi (main.py:89 & openapi.json)  
> **Handler:** `backend_projects` | **Source Location:** `main.py:89`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
*No path, query, header, or cookie parameters required.*

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : Project listing retrieved successfully
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `status` | `string` | Yes | *(Not documented)* |
  | `upstream_url` | `string` | Yes | *(Not documented)* |
  | `total` | `integer` | Yes | *(Not documented)* |
  | `items` | `array` | Yes | *(Not documented)* |

#### Error Cases & Side Effects
**Error Cases:**
- `HTTP 400`: Validation or business logic exception
- `HTTP 400`: Validation or business logic exception

#### Verified Test Coverage
- ✅ `tests/test_localhost_integrations.py::test_working_backend_projects_list`
- ✅ `tests/test_localhost_integrations.py::test_working_backend_create_and_get_project`
- ✅ `tests/test_localhost_integrations.py::test_working_backend_project_dependencies`
- ✅ `tests/test_contract_drift.py::test_openapi_contract_discovery_and_structure`
- ✅ `tests/test_contract_drift.py::test_working_endpoints_unaffected`
- ✅ `tests/test_contract_drift.py::test_algorithmic_detector_drift_rules`

---

### <a id="get-apibackendprojectsproject_id"></a>`GET /api/backend/projects/{project_id}`

**Summary:** Get project details from upstream backend  
**Description:** Working API 4: Queries upstream GET /api/v1/projects/{project_id}.  

> [!NOTE]
> **Discovery Method:** `hybrid` | **Evidence:** hybrid_source_and_openapi (main.py:136 & openapi.json)  
> **Handler:** `backend_get_project` | **Source Location:** `main.py:136`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `project_id` | `path` | `string` | ✅ Yes | *None* | *None* | Unique project identifier |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : Project details retrieved successfully
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `status` | `string` | Yes | *(Not documented)* |
  | `upstream_url` | `string` | Yes | *(Not documented)* |
  | `project` | `string` | Yes | *(Not documented)* |
- **HTTP 404** : Project not found on upstream backend

#### Error Cases & Side Effects
**Error Cases:**
- `HTTP 400`: Validation or business logic exception
- `HTTP 400`: Validation or business logic exception
- `HTTP 400`: Validation or business logic exception

#### Verified Test Coverage
- ✅ `tests/test_localhost_integrations.py::test_working_backend_projects_list`
- ✅ `tests/test_localhost_integrations.py::test_working_backend_create_and_get_project`
- ✅ `tests/test_localhost_integrations.py::test_working_backend_project_dependencies`
- ✅ `tests/test_contract_drift.py::test_openapi_contract_discovery_and_structure`
- ✅ `tests/test_contract_drift.py::test_working_endpoints_unaffected`
- ✅ `tests/test_contract_drift.py::test_algorithmic_detector_drift_rules`

---

### <a id="get-apibackendprojectsproject_iddependencies"></a>`GET /api/backend/projects/{project_id}/dependencies`

**Summary:** List dependencies from upstream backend  
**Description:** Working API 5: Queries upstream GET /api/v1/projects/{project_id}/dependencies.  

> [!NOTE]
> **Discovery Method:** `hybrid` | **Evidence:** hybrid_source_and_openapi (main.py:162 & openapi.json)  
> **Handler:** `backend_project_dependencies` | **Source Location:** `main.py:162`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `project_id` | `path` | `string` | ✅ Yes | *None* | *None* | Unique project identifier |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : Project dependencies retrieved successfully
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `status` | `string` | Yes | *(Not documented)* |
  | `upstream_url` | `string` | Yes | *(Not documented)* |
  | `dependencies` | `array` | Yes | *(Not documented)* |

#### Error Cases & Side Effects
**Error Cases:**
- `HTTP 400`: Validation or business logic exception
- `HTTP 400`: Validation or business logic exception

#### Verified Test Coverage
- ✅ `tests/test_localhost_integrations.py::test_working_backend_project_dependencies`
- ✅ `tests/test_contract_drift.py::test_openapi_contract_discovery_and_structure`

---

### <a id="get-apibrokeninvalid-path"></a>`GET /api/broken/invalid-path`

**Summary:** Integration route with intentional path mismatch  
**Description:** Expected contract specifies valid upstream health integration. Intentional mismatch: client calls nonexistent route /api/v1/nonexistent-service resulting in 404/502.  

> [!NOTE]
> **Discovery Method:** `hybrid` | **Evidence:** hybrid_source_and_openapi (main.py:187 & openapi.json)  
> **Handler:** `broken_invalid_path` | **Source Location:** `main.py:187`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
*No path, query, header, or cookie parameters required.*

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : Expected successful response
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `status` | `string` | No | *(Not documented)* |
- **HTTP 502** : Upstream route not found (404 forwarded as 502 Bad Gateway)

#### Error Cases & Side Effects
**Error Cases:**
- `HTTP 400`: Validation or business logic exception

#### Verified Test Coverage
- ✅ `tests/test_localhost_integrations.py::test_broken_api_1_invalid_path`
- ✅ `tests/test_contract_drift.py::test_openapi_contract_discovery_and_structure`
- ✅ `tests/test_contract_drift.py::test_defect_1_path_mismatch_drift`

---

### <a id="get-apibrokenmethod-mismatch"></a>`GET /api/broken/method-mismatch`

**Summary:** Health status probe integration with method mismatch  
**Description:** Expected contract specifies HTTP method GET for health verification. Intentional mismatch: client integration and endpoint use POST causing 405 Method Not Allowed.  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (openapi.json)  
> **Handler:** *N/A* | **Source Location:** `openapi.json:None`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
*No path, query, header, or cookie parameters required.*

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : Expected successful health check response
- **HTTP 502** : Upstream method not allowed (405 forwarded as 502 Bad Gateway)

#### Verified Test Coverage
- ✅ `tests/test_localhost_integrations.py::test_broken_api_2_method_mismatch`
- ✅ `tests/test_contract_drift.py::test_openapi_contract_discovery_and_structure`
- ✅ `tests/test_contract_drift.py::test_defect_2_method_mismatch_drift`

---

### <a id="get-apiv1orders"></a>`GET /api/v1/orders`

**Summary:** List orders  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `contracts/openapi-v1.json:None`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `status` | `query` | `string` | No | *None* | *None* | Filter by order status |
| `user_id` | `query` | `string` | No | *None* | *None* | Filter by user ID |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`OrderListResponse`): Successful Response
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `items` | `array` | Yes | *(Not documented)* |
  | `total` | `integer` | Yes | *(Not documented)* |
- **HTTP 422** (`HTTPValidationError`): Validation Error
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `detail` | `array` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`

---

### <a id="get-apiv1ordersorder_id"></a>`GET /api/v1/orders/{order_id}`

**Summary:** Get order by ID  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `contracts/openapi-v1.json:None`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `order_id` | `path` | `integer` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`OrderResponse`): Successful Response
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `integer` | Yes | *(Not documented)* |
  | `user_id` | `integer` | Yes | *(Not documented)* |
  | `status` | `string` | Yes | *(Not documented)* |
  | `items` | `array` | Yes | *(Not documented)* |
  | `total_amount` | `number` | Yes | *(Not documented)* |
  | `created_at` | `string` | Yes | *(Not documented)* |
- **HTTP 422** (`HTTPValidationError`): Validation Error
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `detail` | `array` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`

---

### <a id="get-apiv1paymentspayment_id"></a>`GET /api/v1/payments/{payment_id}`

**Summary:** Get payment status  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `contracts/openapi-v1.json:None`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `payment_id` | `path` | `integer` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`PaymentResponse`): Successful Response
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `integer` | Yes | *(Not documented)* |
  | `order_id` | `integer` | Yes | *(Not documented)* |
  | `amount` | `number` | Yes | *(Not documented)* |
  | `payment_method` | `string` | Yes | *(Not documented)* |
  | `status` | `string` | Yes | *(Not documented)* |
  | `transaction_id` | `string` | Yes | *(Not documented)* |
  | `created_at` | `string` | Yes | *(Not documented)* |
- **HTTP 422** (`HTTPValidationError`): Validation Error
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `detail` | `array` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_enum_value_removed_api_v1_payments`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_required_request_field_api_v1_payments`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_field_type_amount_changed`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_path_removed_api_v1_payments__payment_id__receipt`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_enum_value_removed_api_v1_payments`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_required_request_field_api_v1_payments`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_field_type_amount_changed`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_path_removed_api_v1_payments__payment_id__receipt`

---

### <a id="get-apiv1paymentspayment_idreceipt"></a>`GET /api/v1/payments/{payment_id}/receipt`

**Summary:** Get payment receipt  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `contracts/openapi-v1.json:None`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `payment_id` | `path` | `integer` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`PaymentReceiptResponse`): Successful Response
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `receipt_id` | `string` | Yes | *(Not documented)* |
  | `payment_id` | `integer` | Yes | *(Not documented)* |
  | `amount` | `number` | Yes | *(Not documented)* |
  | `issued_at` | `string` | Yes | *(Not documented)* |
- **HTTP 422** (`HTTPValidationError`): Validation Error
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `detail` | `array` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_path_removed_api_v1_payments__payment_id__receipt`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_path_removed_api_v1_payments__payment_id__receipt`

---

### <a id="get-apiv1products"></a>`GET /api/v1/products`

**Summary:** List products  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `contracts/openapi-v1.json:None`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `category` | `query` | `string` | No | *None* | *None* | Filter by product category |
| `min_price` | `query` | `string` | No | *None* | *None* | Minimum price filter |
| `limit` | `query` | `integer` | No | `20` | minimum=1, maximum=100 | Page limit |
| `offset` | `query` | `integer` | No | `0` | minimum=0 | Page offset |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`ProductListResponse`): Successful Response
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `items` | `array` | Yes | *(Not documented)* |
  | `total` | `integer` | Yes | *(Not documented)* |
- **HTTP 422** (`HTTPValidationError`): Validation Error
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `detail` | `array` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_response_field_stock_removed`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_response_field_stock_removed`

---

### <a id="get-apiv1productsproduct_id"></a>`GET /api/v1/products/{product_id}`

**Summary:** Get product by ID  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `contracts/openapi-v1.json:None`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `product_id` | `path` | `integer` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`ProductResponse`): Successful Response
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `name` | `string` | Yes | *(Not documented)* |
  | `description` | `string` | No | *(Not documented)* |
  | `price` | `number` | Yes | Price in USD |
  | `category` | `string` | No | *(Not documented)* |
  | `id` | `integer` | Yes | Unique product identifier |
  | `stock` | `integer` | No | *(Not documented)* |
- **HTTP 422** (`HTTPValidationError`): Validation Error
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `detail` | `array` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_response_field_stock_removed`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_response_field_stock_removed`

---

### <a id="get-apiv1users"></a>`GET /api/v1/users`

**Summary:** List users  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `contracts/openapi-v1.json:None`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `role` | `query` | `string` | No | *None* | *None* | Filter by user role |
| `limit` | `query` | `integer` | No | `10` | minimum=1, maximum=100 | Page limit |
| `offset` | `query` | `integer` | No | `0` | minimum=0 | Page offset |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`UserListResponse`): Successful Response
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `items` | `array` | Yes | *(Not documented)* |
  | `total` | `integer` | Yes | *(Not documented)* |
- **HTTP 422** (`HTTPValidationError`): Validation Error
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `detail` | `array` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_optional_param_search_supported`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_optional_param_search_supported`

---

### <a id="get-apiv1usersuser_id"></a>`GET /api/v1/users/{user_id}`

**Summary:** Get user by ID  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `contracts/openapi-v1.json:None`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `user_id` | `path` | `integer` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`UserResponse`): Successful Response
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `username` | `string` | Yes | Unique username |
  | `email` | `string` | Yes | User email address |
  | `role` | `string` | No | Account permission role |
  | `id` | `integer` | Yes | Unique integer ID |
  | `is_active` | `boolean` | No | Account active status |
- **HTTP 422** (`HTTPValidationError`): Validation Error
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `detail` | `array` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_optional_param_search_supported`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_optional_param_search_supported`

---

### <a id="get-health"></a>`GET /health`

**Summary:** Service health check  

> [!NOTE]
> **Discovery Method:** `hybrid` | **Evidence:** hybrid_source_and_openapi (main.py:49 & contracts/openapi-v1.json)  
> **Handler:** `self_health` | **Source Location:** `main.py:49`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
*No path, query, header, or cookie parameters required.*

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : Successful Response

#### Verified Test Coverage
- ✅ `tests/test_localhost_integrations.py::test_self_health`
- ✅ `tests/test_localhost_integrations.py::test_working_backend_health`
- ✅ `tests/test_localhost_integrations.py::test_broken_api_2_method_mismatch`
- ✅ `tests/test_localhost_integrations.py::test_direct_client_health`
- ✅ `tests/test_contract_drift.py::test_openapi_contract_discovery_and_structure`
- ✅ `tests/test_contract_drift.py::test_defect_1_path_mismatch_drift`
- ✅ `tests/test_contract_drift.py::test_defect_2_method_mismatch_drift`
- ✅ `tests/test_contract_drift.py::test_working_endpoints_unaffected`
- ✅ `tests/test_contract_drift.py::test_algorithmic_detector_drift_rules`

---

### <a id="patch-apiv1ordersorder_idstatus"></a>`PATCH /api/v1/orders/{order_id}/status`

**Summary:** Update order status  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `contracts/openapi-v1.json:None`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `order_id` | `path` | `integer` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `OrderUpdateStatus` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `status` | `string` | ✅ Yes | *None* | *None* | Target status |

#### Responses
- **HTTP 200** (`OrderResponse`): Successful Response
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `integer` | Yes | *(Not documented)* |
  | `user_id` | `integer` | Yes | *(Not documented)* |
  | `status` | `string` | Yes | *(Not documented)* |
  | `items` | `array` | Yes | *(Not documented)* |
  | `total_amount` | `number` | Yes | *(Not documented)* |
  | `created_at` | `string` | Yes | *(Not documented)* |
- **HTTP 422** (`HTTPValidationError`): Validation Error
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `detail` | `array` | No | *(Not documented)* |

#### Verified Test Coverage
- ⚠️ *No automated tests found covering this route (Coverage Gap).*

---

### <a id="post-apibackendprojects"></a>`POST /api/backend/projects`

**Summary:** Create a project on upstream backend  
**Description:** Working API 3: Posts valid ProjectCreate payload to upstream POST /api/v1/projects.  

> [!NOTE]
> **Discovery Method:** `hybrid` | **Evidence:** hybrid_source_and_openapi (main.py:111 & openapi.json)  
> **Handler:** `backend_create_project` | **Source Location:** `main.py:111`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
*No path, query, header, or cookie parameters required.*

#### Request Body
**Content-Type:** `application/json` | **Schema:** `CreateProjectRequest` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `name` | `string` | ✅ Yes | *None* | *None* | Project name |
| `description` | `string` | No | *None* | *None* | Optional description |
| `repository_url` | `string` | No | `https://github.com/demo/sample-repo` | *None* | Repository URL |

#### Responses
- **HTTP 201** : Project created successfully
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `status` | `string` | Yes | *(Not documented)* |
  | `upstream_url` | `string` | Yes | *(Not documented)* |
  | `project` | `string` | Yes | *(Not documented)* |
- **HTTP 502** : Upstream error creating project

#### Error Cases & Side Effects
**Error Cases:**
- `HTTP 400`: Validation or business logic exception
- `HTTP 400`: Validation or business logic exception

#### Verified Test Coverage
- ✅ `tests/test_localhost_integrations.py::test_working_backend_projects_list`
- ✅ `tests/test_localhost_integrations.py::test_working_backend_create_and_get_project`
- ✅ `tests/test_localhost_integrations.py::test_working_backend_project_dependencies`
- ✅ `tests/test_contract_drift.py::test_openapi_contract_discovery_and_structure`
- ✅ `tests/test_contract_drift.py::test_working_endpoints_unaffected`
- ✅ `tests/test_contract_drift.py::test_algorithmic_detector_drift_rules`

---

### <a id="post-apibrokenmethod-mismatch"></a>`POST /api/broken/method-mismatch`

**Summary:** Broken API 2 (Incorrect HTTP Method):
Calls upstream POST /api/v1/health. The backend health endpoint only supports GET.
The upstream backend returns HTTP 405 Method Not Allowed.
This endpoint catches the upstream failure and returns HTTP 502 with diagnostic details.  

> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (main.py:208)  
> **Handler:** `broken_method_mismatch` | **Source Location:** `main.py:208`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
*No path, query, header, or cookie parameters required.*

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : Successful response (200)

#### Error Cases & Side Effects
**Error Cases:**
- `HTTP 400`: Validation or business logic exception

#### Verified Test Coverage
- ✅ `tests/test_localhost_integrations.py::test_broken_api_2_method_mismatch`
- ✅ `tests/test_contract_drift.py::test_openapi_contract_discovery_and_structure`
- ✅ `tests/test_contract_drift.py::test_defect_2_method_mismatch_drift`

---

### <a id="post-apibrokenpayload-mismatch"></a>`POST /api/broken/payload-mismatch`

**Summary:** Project creation integration with schema drift  
**Description:** Expected contract requires CreateProjectRequest with mandatory field 'name'. Intentional mismatch: client sends invalid keys without 'name', causing 400 Bad Request.  

> [!NOTE]
> **Discovery Method:** `hybrid` | **Evidence:** hybrid_source_and_openapi (main.py:230 & openapi.json)  
> **Handler:** `broken_payload_mismatch` | **Source Location:** `main.py:230`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
*No path, query, header, or cookie parameters required.*

#### Request Body
**Content-Type:** `application/json` | **Schema:** `CreateProjectRequest` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `name` | `string` | ✅ Yes | *None* | *None* | Project name |
| `description` | `string` | No | *None* | *None* | Optional description |
| `repository_url` | `string` | No | `https://github.com/demo/sample-repo` | *None* | Repository URL |

#### Responses
- **HTTP 201** : Project created successfully
- **HTTP 502** : Upstream payload validation failed (400 forwarded as 502 Bad Gateway)

#### Error Cases & Side Effects
**Error Cases:**
- `HTTP 400`: Validation or business logic exception

#### Verified Test Coverage
- ✅ `tests/test_localhost_integrations.py::test_broken_api_3_payload_mismatch`
- ✅ `tests/test_contract_drift.py::test_openapi_contract_discovery_and_structure`
- ✅ `tests/test_contract_drift.py::test_defect_3_payload_schema_mismatch_drift`

---

### <a id="post-apiv1orders"></a>`POST /api/v1/orders`

**Summary:** Create order  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `contracts/openapi-v1.json:None`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
*No path, query, header, or cookie parameters required.*

#### Request Body
**Content-Type:** `application/json` | **Schema:** `OrderCreate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `user_id` | `integer` | ✅ Yes | *None* | *None* | *(Not documented)* |
| `items` | `array` | ✅ Yes | *None* | *None* | *(Not documented)* |
| `notes` | `string` | No | *None* | *None* | Optional customer notes |

#### Responses
- **HTTP 201** (`OrderResponse`): Successful Response
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `integer` | Yes | *(Not documented)* |
  | `user_id` | `integer` | Yes | *(Not documented)* |
  | `status` | `string` | Yes | *(Not documented)* |
  | `items` | `array` | Yes | *(Not documented)* |
  | `total_amount` | `number` | Yes | *(Not documented)* |
  | `created_at` | `string` | Yes | *(Not documented)* |
- **HTTP 422** (`HTTPValidationError`): Validation Error
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `detail` | `array` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`

---

### <a id="post-apiv1payments"></a>`POST /api/v1/payments`

**Summary:** Process payment  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `contracts/openapi-v1.json:None`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
*No path, query, header, or cookie parameters required.*

#### Request Body
**Content-Type:** `application/json` | **Schema:** `PaymentCreate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `order_id` | `integer` | ✅ Yes | *None* | *None* | *(Not documented)* |
| `amount` | `number` | ✅ Yes | *None* | *None* | *(Not documented)* |
| `payment_method` | `string` | No | `credit_card` | *None* | *(Not documented)* |

#### Responses
- **HTTP 201** (`PaymentResponse`): Successful Response
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `integer` | Yes | *(Not documented)* |
  | `order_id` | `integer` | Yes | *(Not documented)* |
  | `amount` | `number` | Yes | *(Not documented)* |
  | `payment_method` | `string` | Yes | *(Not documented)* |
  | `status` | `string` | Yes | *(Not documented)* |
  | `transaction_id` | `string` | Yes | *(Not documented)* |
  | `created_at` | `string` | Yes | *(Not documented)* |
- **HTTP 422** (`HTTPValidationError`): Validation Error
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `detail` | `array` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_enum_value_removed_api_v1_payments`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_required_request_field_api_v1_payments`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_field_type_amount_changed`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_path_removed_api_v1_payments__payment_id__receipt`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_enum_value_removed_api_v1_payments`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_required_request_field_api_v1_payments`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_field_type_amount_changed`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_path_removed_api_v1_payments__payment_id__receipt`

---

### <a id="post-apiv1products"></a>`POST /api/v1/products`

**Summary:** Create product  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `contracts/openapi-v1.json:None`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
*No path, query, header, or cookie parameters required.*

#### Request Body
**Content-Type:** `application/json` | **Schema:** `ProductCreate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `name` | `string` | ✅ Yes | *None* | minLength=2, maxLength=100 | *(Not documented)* |
| `description` | `string` | No | *None* | *None* | *(Not documented)* |
| `price` | `number` | ✅ Yes | *None* | *None* | Price in USD |
| `category` | `string` | No | `electronics` | *None* | *(Not documented)* |
| `stock` | `integer` | No | `0` | minimum=0.0 | *(Not documented)* |

#### Responses
- **HTTP 201** (`ProductResponse`): Successful Response
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `name` | `string` | Yes | *(Not documented)* |
  | `description` | `string` | No | *(Not documented)* |
  | `price` | `number` | Yes | Price in USD |
  | `category` | `string` | No | *(Not documented)* |
  | `id` | `integer` | Yes | Unique product identifier |
  | `stock` | `integer` | No | *(Not documented)* |
- **HTTP 422** (`HTTPValidationError`): Validation Error
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `detail` | `array` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_response_field_stock_removed`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_response_field_stock_removed`

---

### <a id="post-apiv1users"></a>`POST /api/v1/users`

**Summary:** Create user  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `contracts/openapi-v1.json:None`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
*No path, query, header, or cookie parameters required.*

#### Request Body
**Content-Type:** `application/json` | **Schema:** `UserCreate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `username` | `string` | ✅ Yes | *None* | minLength=3, maxLength=50 | Unique username |
| `email` | `string` | ✅ Yes | *None* | *None* | User email address |
| `role` | `string` | No | `member` | *None* | Account permission role |

#### Responses
- **HTTP 201** (`UserResponse`): Successful Response
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `username` | `string` | Yes | Unique username |
  | `email` | `string` | Yes | User email address |
  | `role` | `string` | No | Account permission role |
  | `id` | `integer` | Yes | Unique integer ID |
  | `is_active` | `boolean` | No | Account active status |
- **HTTP 422** (`HTTPValidationError`): Validation Error
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `detail` | `array` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_optional_param_search_supported`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_optional_param_search_supported`

---

### <a id="put-apiv1productsproduct_id"></a>`PUT /api/v1/products/{product_id}`

**Summary:** Update product  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `contracts/openapi-v1.json:None`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `product_id` | `path` | `integer` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `ProductUpdate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `name` | `string` | No | *None* | *None* | *(Not documented)* |
| `description` | `string` | No | *None* | *None* | *(Not documented)* |
| `price` | `string` | No | *None* | *None* | *(Not documented)* |
| `category` | `string` | No | *None* | *None* | *(Not documented)* |
| `stock` | `string` | No | *None* | *None* | *(Not documented)* |

#### Responses
- **HTTP 200** (`ProductResponse`): Successful Response
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `name` | `string` | Yes | *(Not documented)* |
  | `description` | `string` | No | *(Not documented)* |
  | `price` | `number` | Yes | Price in USD |
  | `category` | `string` | No | *(Not documented)* |
  | `id` | `integer` | Yes | Unique product identifier |
  | `stock` | `integer` | No | *(Not documented)* |
- **HTTP 422** (`HTTPValidationError`): Validation Error
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `detail` | `array` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_response_field_stock_removed`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_response_field_stock_removed`

---

### <a id="put-apiv1usersuser_id"></a>`PUT /api/v1/users/{user_id}`

**Summary:** Update user  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `contracts/openapi-v1.json:None`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `user_id` | `path` | `integer` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `UserUpdate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `username` | `string` | No | *None* | *None* | *(Not documented)* |
| `email` | `string` | No | *None* | *None* | *(Not documented)* |
| `role` | `string` | No | *None* | *None* | *(Not documented)* |
| `is_active` | `string` | No | *None* | *None* | *(Not documented)* |

#### Responses
- **HTTP 200** (`UserResponse`): Successful Response
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `username` | `string` | Yes | Unique username |
  | `email` | `string` | Yes | User email address |
  | `role` | `string` | No | Account permission role |
  | `id` | `integer` | Yes | Unique integer ID |
  | `is_active` | `boolean` | No | Account active status |
- **HTTP 422** (`HTTPValidationError`): Validation Error
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `detail` | `array` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `generated-tests/test_candidate_regression_v2.py::test_regression_optional_param_search_supported`
- ✅ `generated-tests/test_approved_regression_v2.py::test_regression_optional_param_search_supported`

---
