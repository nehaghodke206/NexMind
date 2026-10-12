# Dependency Guardian — API Reference Documentation

**Total Discovered Endpoints:** 35  
**Generated On:** `2026-10-11T19:21:15.989294+00:00`  

## Table of Contents

- [`DELETE /api/v1/products/{product_id}`](#delete-apiv1productsproduct_id)
- [`DELETE /api/v1/users/{user_id}`](#delete-apiv1usersuser_id)
- [`DELETE /products/{product_id}`](#delete-productsproduct_id)
- [`DELETE /users/{user_id}`](#delete-usersuser_id)
- [`GET /api/v1/orders`](#get-apiv1orders)
- [`GET /api/v1/orders/{order_id}`](#get-apiv1ordersorder_id)
- [`GET /api/v1/payments/{payment_id}`](#get-apiv1paymentspayment_id)
- [`GET /api/v1/payments/{payment_id}/receipt`](#get-apiv1paymentspayment_idreceipt)
- [`GET /api/v1/products`](#get-apiv1products)
- [`GET /api/v1/products/{product_id}`](#get-apiv1productsproduct_id)
- [`GET /api/v1/users`](#get-apiv1users)
- [`GET /api/v1/users/{user_id}`](#get-apiv1usersuser_id)
- [`GET /health`](#get-health)
- [`GET /orders`](#get-orders)
- [`GET /orders/{order_id}`](#get-ordersorder_id)
- [`GET /payments/{payment_id}`](#get-paymentspayment_id)
- [`GET /payments/{payment_id}/receipt`](#get-paymentspayment_idreceipt)
- [`GET /products`](#get-products)
- [`GET /products/{product_id}`](#get-productsproduct_id)
- [`GET /users`](#get-users)
- [`GET /users/{user_id}`](#get-usersuser_id)
- [`PATCH /api/v1/orders/{order_id}/status`](#patch-apiv1ordersorder_idstatus)
- [`PATCH /orders/{order_id}/status`](#patch-ordersorder_idstatus)
- [`POST /api/v1/orders`](#post-apiv1orders)
- [`POST /api/v1/payments`](#post-apiv1payments)
- [`POST /api/v1/products`](#post-apiv1products)
- [`POST /api/v1/users`](#post-apiv1users)
- [`POST /orders`](#post-orders)
- [`POST /payments`](#post-payments)
- [`POST /products`](#post-products)
- [`POST /users`](#post-users)
- [`PUT /api/v1/products/{product_id}`](#put-apiv1productsproduct_id)
- [`PUT /api/v1/users/{user_id}`](#put-apiv1usersuser_id)
- [`PUT /products/{product_id}`](#put-productsproduct_id)
- [`PUT /users/{user_id}`](#put-usersuser_id)

---

### <a id="delete-apiv1productsproduct_id"></a>`DELETE /api/v1/products/{product_id}`

**Summary:** Delete product  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (sample-api/contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `sample-api/contracts/openapi-v1.json:None`  
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
- ✅ `sample-api/tests/test_v1_api.py::test_v1_products_crud_and_filtering`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_products_breaking_and_non_breaking_changes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_response_field_stock_removed`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_response_field_stock_removed`

---

### <a id="delete-apiv1usersuser_id"></a>`DELETE /api/v1/users/{user_id}`

**Summary:** Delete user  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (sample-api/contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `sample-api/contracts/openapi-v1.json:None`  
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
- ✅ `sample-api/tests/test_v1_api.py::test_v1_users_crud_and_validation`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_users_with_search_and_notes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_optional_param_search_supported`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_optional_param_search_supported`

---

### <a id="delete-productsproduct_id"></a>`DELETE /products/{product_id}`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (sample-api/versions/v1/app/api/products.py:53)  
> **Handler:** `delete_product` | **Source Location:** `sample-api/versions/v1/app/api/products.py:53`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_product_service)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `product_id` | `path` | `int` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : Successful response (200)

#### Verified Test Coverage
- ✅ `sample-api/tests/test_v1_api.py::test_v1_products_crud_and_filtering`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_products_breaking_and_non_breaking_changes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_response_field_stock_removed`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_response_field_stock_removed`

---

### <a id="delete-usersuser_id"></a>`DELETE /users/{user_id}`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (sample-api/versions/v2/app/api/users.py:54)  
> **Handler:** `delete_user` | **Source Location:** `sample-api/versions/v2/app/api/users.py:54`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_user_service)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `user_id` | `path` | `int` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : Successful response (200)

#### Verified Test Coverage
- ✅ `sample-api/tests/test_v1_api.py::test_v1_users_crud_and_validation`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_users_with_search_and_notes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_optional_param_search_supported`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_optional_param_search_supported`

---

### <a id="get-apiv1orders"></a>`GET /api/v1/orders`

**Summary:** List orders  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (sample-api/contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `sample-api/contracts/openapi-v1.json:None`  
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
- ✅ `sample-api/tests/test_v1_api.py::test_v1_orders_and_validation`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_orders_with_discount`

---

### <a id="get-apiv1ordersorder_id"></a>`GET /api/v1/orders/{order_id}`

**Summary:** Get order by ID  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (sample-api/contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `sample-api/contracts/openapi-v1.json:None`  
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
- ✅ `sample-api/tests/test_v1_api.py::test_v1_orders_and_validation`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_orders_with_discount`

---

### <a id="get-apiv1paymentspayment_id"></a>`GET /api/v1/payments/{payment_id}`

**Summary:** Get payment status  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (sample-api/contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `sample-api/contracts/openapi-v1.json:None`  
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
- ✅ `sample-api/tests/test_v1_api.py::test_v1_payments_flow`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_payments_breaking_changes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_enum_value_removed_api_v1_payments`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_required_request_field_api_v1_payments`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_field_type_amount_changed`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_path_removed_api_v1_payments__payment_id__receipt`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_enum_value_removed_api_v1_payments`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_required_request_field_api_v1_payments`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_field_type_amount_changed`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_path_removed_api_v1_payments__payment_id__receipt`

---

### <a id="get-apiv1paymentspayment_idreceipt"></a>`GET /api/v1/payments/{payment_id}/receipt`

**Summary:** Get payment receipt  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (sample-api/contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `sample-api/contracts/openapi-v1.json:None`  
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
- ✅ `sample-api/tests/test_v1_api.py::test_v1_payments_flow`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_payments_breaking_changes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_path_removed_api_v1_payments__payment_id__receipt`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_path_removed_api_v1_payments__payment_id__receipt`

---

### <a id="get-apiv1products"></a>`GET /api/v1/products`

**Summary:** List products  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (sample-api/contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `sample-api/contracts/openapi-v1.json:None`  
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
- ✅ `sample-api/tests/test_v1_api.py::test_v1_products_crud_and_filtering`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_products_breaking_and_non_breaking_changes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_response_field_stock_removed`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_response_field_stock_removed`

---

### <a id="get-apiv1productsproduct_id"></a>`GET /api/v1/products/{product_id}`

**Summary:** Get product by ID  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (sample-api/contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `sample-api/contracts/openapi-v1.json:None`  
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
- ✅ `sample-api/tests/test_v1_api.py::test_v1_products_crud_and_filtering`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_products_breaking_and_non_breaking_changes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_response_field_stock_removed`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_response_field_stock_removed`

---

### <a id="get-apiv1users"></a>`GET /api/v1/users`

**Summary:** List users  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (sample-api/contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `sample-api/contracts/openapi-v1.json:None`  
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
- ✅ `sample-api/tests/test_v1_api.py::test_v1_users_crud_and_validation`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_users_with_search_and_notes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_optional_param_search_supported`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_optional_param_search_supported`

---

### <a id="get-apiv1usersuser_id"></a>`GET /api/v1/users/{user_id}`

**Summary:** Get user by ID  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (sample-api/contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `sample-api/contracts/openapi-v1.json:None`  
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
- ✅ `sample-api/tests/test_v1_api.py::test_v1_users_crud_and_validation`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_users_with_search_and_notes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_optional_param_search_supported`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_optional_param_search_supported`

---

### <a id="get-health"></a>`GET /health`

**Summary:** Service health check  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (sample-api/contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `sample-api/contracts/openapi-v1.json:None`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
*No path, query, header, or cookie parameters required.*

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : Successful Response

#### Verified Test Coverage
- ✅ `sample-api/tests/test_v1_api.py::test_v1_health`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_health`

---

### <a id="get-orders"></a>`GET /orders`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (sample-api/versions/v2/app/api/orders.py:17)  
> **Handler:** `list_orders` | **Source Location:** `sample-api/versions/v2/app/api/orders.py:17`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_order_service)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `status_filter` | `query` | `Optional[OrderStatus]` | ✅ Yes | *None* | *None* | Filter by order status |
| `user_id` | `query` | `Optional[int]` | ✅ Yes | *None* | *None* | Filter by user ID |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`OrderListResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `items` | `List[OrderResponse]` | Yes | *(Not documented)* |
  | `total` | `int` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `sample-api/tests/test_v1_api.py::test_v1_orders_and_validation`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_orders_with_discount`

---

### <a id="get-ordersorder_id"></a>`GET /orders/{order_id}`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (sample-api/versions/v2/app/api/orders.py:34)  
> **Handler:** `get_order` | **Source Location:** `sample-api/versions/v2/app/api/orders.py:34`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_order_service)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `order_id` | `path` | `int` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`OrderResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `int` | Yes | *(Not documented)* |
  | `user_id` | `int` | Yes | *(Not documented)* |
  | `status` | `OrderStatus` | Yes | *(Not documented)* |
  | `items` | `List[OrderItemResponse]` | Yes | *(Not documented)* |
  | `total_amount` | `float` | Yes | *(Not documented)* |
  | `created_at` | `str` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `sample-api/tests/test_v1_api.py::test_v1_orders_and_validation`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_orders_with_discount`

---

### <a id="get-paymentspayment_id"></a>`GET /payments/{payment_id}`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (sample-api/versions/v2/app/api/payments.py:24)  
> **Handler:** `get_payment` | **Source Location:** `sample-api/versions/v2/app/api/payments.py:24`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_payment_service)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `payment_id` | `path` | `int` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`PaymentResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `int` | Yes | *(Not documented)* |
  | `order_id` | `int` | Yes | *(Not documented)* |
  | `amount` | `float` | Yes | *(Not documented)* |
  | `payment_method` | `PaymentMethod` | Yes | *(Not documented)* |
  | `status` | `PaymentStatus` | Yes | *(Not documented)* |
  | `transaction_id` | `str` | Yes | *(Not documented)* |
  | `created_at` | `str` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `sample-api/tests/test_v1_api.py::test_v1_payments_flow`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_payments_breaking_changes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_enum_value_removed_api_v1_payments`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_required_request_field_api_v1_payments`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_field_type_amount_changed`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_path_removed_api_v1_payments__payment_id__receipt`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_enum_value_removed_api_v1_payments`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_required_request_field_api_v1_payments`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_field_type_amount_changed`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_path_removed_api_v1_payments__payment_id__receipt`

---

### <a id="get-paymentspayment_idreceipt"></a>`GET /payments/{payment_id}/receipt`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (sample-api/versions/v1/app/api/payments.py:32)  
> **Handler:** `get_payment_receipt` | **Source Location:** `sample-api/versions/v1/app/api/payments.py:32`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_payment_service)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `payment_id` | `path` | `int` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`PaymentReceiptResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `receipt_id` | `str` | Yes | *(Not documented)* |
  | `payment_id` | `int` | Yes | *(Not documented)* |
  | `amount` | `float` | Yes | *(Not documented)* |
  | `issued_at` | `str` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `sample-api/tests/test_v1_api.py::test_v1_payments_flow`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_payments_breaking_changes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_path_removed_api_v1_payments__payment_id__receipt`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_path_removed_api_v1_payments__payment_id__receipt`

---

### <a id="get-products"></a>`GET /products`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (sample-api/versions/v2/app/api/products.py:17)  
> **Handler:** `list_products` | **Source Location:** `sample-api/versions/v2/app/api/products.py:17`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_product_service)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `store_id` | `query` | `str` | ✅ Yes | *None* | *None* | Store location identifier required for multi-store inventory |
| `category` | `query` | `Optional[ProductCategory]` | ✅ Yes | *None* | *None* | Filter by product category |
| `min_price` | `query` | `Optional[float]` | ✅ Yes | *None* | ge=0 | Minimum price filter |
| `limit` | `query` | `int` | ✅ Yes | *None* | ge=1, le=100 | Page limit |
| `offset` | `query` | `int` | ✅ Yes | *None* | ge=0 | Page offset |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`ProductListResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `items` | `List[ProductResponse]` | Yes | *(Not documented)* |
  | `total` | `int` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `sample-api/tests/test_v1_api.py::test_v1_products_crud_and_filtering`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_products_breaking_and_non_breaking_changes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_response_field_stock_removed`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_response_field_stock_removed`

---

### <a id="get-productsproduct_id"></a>`GET /products/{product_id}`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (sample-api/versions/v2/app/api/products.py:39)  
> **Handler:** `get_product` | **Source Location:** `sample-api/versions/v2/app/api/products.py:39`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_product_service)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `product_id` | `path` | `int` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`ProductResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `int` | No | Unique product identifier |
  | `stock` | `int` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `sample-api/tests/test_v1_api.py::test_v1_products_crud_and_filtering`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_products_breaking_and_non_breaking_changes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_response_field_stock_removed`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_response_field_stock_removed`

---

### <a id="get-users"></a>`GET /users`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (sample-api/versions/v2/app/api/users.py:17)  
> **Handler:** `list_users` | **Source Location:** `sample-api/versions/v2/app/api/users.py:17`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_user_service)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `role` | `query` | `Optional[UserRole]` | ✅ Yes | *None* | *None* | Filter by user role |
| `search` | `query` | `Optional[str]` | ✅ Yes | *None* | *None* | Search by username or email |
| `limit` | `query` | `int` | ✅ Yes | *None* | ge=1, le=100 | Page limit |
| `offset` | `query` | `int` | ✅ Yes | *None* | ge=0 | Page offset |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`UserListResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `items` | `List[UserResponse]` | Yes | *(Not documented)* |
  | `total` | `int` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `sample-api/tests/test_v1_api.py::test_v1_users_crud_and_validation`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_users_with_search_and_notes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_optional_param_search_supported`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_optional_param_search_supported`

---

### <a id="get-usersuser_id"></a>`GET /users/{user_id}`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (sample-api/versions/v2/app/api/users.py:37)  
> **Handler:** `get_user` | **Source Location:** `sample-api/versions/v2/app/api/users.py:37`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_user_service)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `user_id` | `path` | `int` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`UserResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `int` | No | Unique integer ID |
  | `is_active` | `bool` | No | Account active status |

#### Verified Test Coverage
- ✅ `sample-api/tests/test_v1_api.py::test_v1_users_crud_and_validation`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_users_with_search_and_notes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_optional_param_search_supported`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_optional_param_search_supported`

---

### <a id="patch-apiv1ordersorder_idstatus"></a>`PATCH /api/v1/orders/{order_id}/status`

**Summary:** Update order status  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (sample-api/contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `sample-api/contracts/openapi-v1.json:None`  
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
- ✅ `sample-api/tests/test_v1_api.py::test_v1_orders_and_validation`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_orders_with_discount`

---

### <a id="patch-ordersorder_idstatus"></a>`PATCH /orders/{order_id}/status`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (sample-api/versions/v2/app/api/orders.py:42)  
> **Handler:** `update_order_status` | **Source Location:** `sample-api/versions/v2/app/api/orders.py:42`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_order_service)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `order_id` | `path` | `int` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `OrderUpdateStatus` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `status` | `OrderStatus` | No | *None* | *None* | Target status |

#### Responses
- **HTTP 200** (`OrderResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `int` | Yes | *(Not documented)* |
  | `user_id` | `int` | Yes | *(Not documented)* |
  | `status` | `OrderStatus` | Yes | *(Not documented)* |
  | `items` | `List[OrderItemResponse]` | Yes | *(Not documented)* |
  | `total_amount` | `float` | Yes | *(Not documented)* |
  | `created_at` | `str` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `sample-api/tests/test_v1_api.py::test_v1_orders_and_validation`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_orders_with_discount`

---

### <a id="post-apiv1orders"></a>`POST /api/v1/orders`

**Summary:** Create order  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (sample-api/contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `sample-api/contracts/openapi-v1.json:None`  
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
- ✅ `sample-api/tests/test_v1_api.py::test_v1_orders_and_validation`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_orders_with_discount`

---

### <a id="post-apiv1payments"></a>`POST /api/v1/payments`

**Summary:** Process payment  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (sample-api/contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `sample-api/contracts/openapi-v1.json:None`  
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
- ✅ `sample-api/tests/test_v1_api.py::test_v1_payments_flow`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_payments_breaking_changes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_enum_value_removed_api_v1_payments`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_required_request_field_api_v1_payments`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_field_type_amount_changed`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_path_removed_api_v1_payments__payment_id__receipt`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_enum_value_removed_api_v1_payments`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_required_request_field_api_v1_payments`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_field_type_amount_changed`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_path_removed_api_v1_payments__payment_id__receipt`

---

### <a id="post-apiv1products"></a>`POST /api/v1/products`

**Summary:** Create product  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (sample-api/contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `sample-api/contracts/openapi-v1.json:None`  
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
- ✅ `sample-api/tests/test_v1_api.py::test_v1_products_crud_and_filtering`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_products_breaking_and_non_breaking_changes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_response_field_stock_removed`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_response_field_stock_removed`

---

### <a id="post-apiv1users"></a>`POST /api/v1/users`

**Summary:** Create user  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (sample-api/contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `sample-api/contracts/openapi-v1.json:None`  
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
- ✅ `sample-api/tests/test_v1_api.py::test_v1_users_crud_and_validation`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_users_with_search_and_notes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_optional_param_search_supported`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_optional_param_search_supported`

---

### <a id="post-orders"></a>`POST /orders`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (sample-api/versions/v2/app/api/orders.py:26)  
> **Handler:** `create_order` | **Source Location:** `sample-api/versions/v2/app/api/orders.py:26`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_order_service)

#### Parameters
*No path, query, header, or cookie parameters required.*

#### Request Body
**Content-Type:** `application/json` | **Schema:** `OrderCreate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `user_id` | `int` | No | *None* | gt=0 | *(Not documented)* |
| `items` | `List[OrderItemCreate]` | No | *None* | min_length=1 | *(Not documented)* |
| `notes` | `Optional[str]` | No | *None* | *None* | Optional customer notes |

#### Responses
- **HTTP 201** (`OrderResponse`): Successful response (201)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `int` | Yes | *(Not documented)* |
  | `user_id` | `int` | Yes | *(Not documented)* |
  | `status` | `OrderStatus` | Yes | *(Not documented)* |
  | `items` | `List[OrderItemResponse]` | Yes | *(Not documented)* |
  | `total_amount` | `float` | Yes | *(Not documented)* |
  | `created_at` | `str` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `sample-api/tests/test_v1_api.py::test_v1_orders_and_validation`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_orders_with_discount`

---

### <a id="post-payments"></a>`POST /payments`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (sample-api/versions/v2/app/api/payments.py:16)  
> **Handler:** `process_payment` | **Source Location:** `sample-api/versions/v2/app/api/payments.py:16`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_payment_service)

#### Parameters
*No path, query, header, or cookie parameters required.*

#### Request Body
**Content-Type:** `application/json` | **Schema:** `PaymentCreate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `order_id` | `int` | No | *None* | gt=0 | *(Not documented)* |
| `amount` | `float` | No | *None* | gt=0 | *(Not documented)* |
| `payment_method` | `PaymentMethod` | No | *None* | *None* | *(Not documented)* |

#### Responses
- **HTTP 201** (`PaymentResponse`): Successful response (201)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `int` | Yes | *(Not documented)* |
  | `order_id` | `int` | Yes | *(Not documented)* |
  | `amount` | `float` | Yes | *(Not documented)* |
  | `payment_method` | `PaymentMethod` | Yes | *(Not documented)* |
  | `status` | `PaymentStatus` | Yes | *(Not documented)* |
  | `transaction_id` | `str` | Yes | *(Not documented)* |
  | `created_at` | `str` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `sample-api/tests/test_v1_api.py::test_v1_payments_flow`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_payments_breaking_changes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_enum_value_removed_api_v1_payments`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_required_request_field_api_v1_payments`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_field_type_amount_changed`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_path_removed_api_v1_payments__payment_id__receipt`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_enum_value_removed_api_v1_payments`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_required_request_field_api_v1_payments`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_field_type_amount_changed`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_path_removed_api_v1_payments__payment_id__receipt`

---

### <a id="post-products"></a>`POST /products`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (sample-api/versions/v2/app/api/products.py:30)  
> **Handler:** `create_product` | **Source Location:** `sample-api/versions/v2/app/api/products.py:30`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_product_service)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `store_id` | `query` | `str` | ✅ Yes | *None* | *None* | Store ID for initial product placement |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `ProductCreate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `stock` | `int` | No | `0` | ge=0 | *(Not documented)* |

#### Responses
- **HTTP 201** (`ProductResponse`): Successful response (201)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `int` | No | Unique product identifier |
  | `stock` | `int` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `sample-api/tests/test_v1_api.py::test_v1_products_crud_and_filtering`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_products_breaking_and_non_breaking_changes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_response_field_stock_removed`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_response_field_stock_removed`

---

### <a id="post-users"></a>`POST /users`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (sample-api/versions/v2/app/api/users.py:29)  
> **Handler:** `create_user` | **Source Location:** `sample-api/versions/v2/app/api/users.py:29`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_user_service)

#### Parameters
*No path, query, header, or cookie parameters required.*

#### Request Body
**Content-Type:** `application/json` | **Schema:** `UserCreate` (Required)

*Request body schema defines no specific properties.*

#### Responses
- **HTTP 201** (`UserResponse`): Successful response (201)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `int` | No | Unique integer ID |
  | `is_active` | `bool` | No | Account active status |

#### Verified Test Coverage
- ✅ `sample-api/tests/test_v1_api.py::test_v1_users_crud_and_validation`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_users_with_search_and_notes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_optional_param_search_supported`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_optional_param_search_supported`

---

### <a id="put-apiv1productsproduct_id"></a>`PUT /api/v1/products/{product_id}`

**Summary:** Update product  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (sample-api/contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `sample-api/contracts/openapi-v1.json:None`  
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
- ✅ `sample-api/tests/test_v1_api.py::test_v1_products_crud_and_filtering`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_products_breaking_and_non_breaking_changes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_response_field_stock_removed`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_response_field_stock_removed`

---

### <a id="put-apiv1usersuser_id"></a>`PUT /api/v1/users/{user_id}`

**Summary:** Update user  

> [!NOTE]
> **Discovery Method:** `openapi_spec` | **Evidence:** openapi_specification (sample-api/contracts/openapi-v1.json)  
> **Handler:** *N/A* | **Source Location:** `sample-api/contracts/openapi-v1.json:None`  
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
- ✅ `sample-api/tests/test_v1_api.py::test_v1_users_crud_and_validation`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_users_with_search_and_notes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_optional_param_search_supported`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_optional_param_search_supported`

---

### <a id="put-productsproduct_id"></a>`PUT /products/{product_id}`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (sample-api/versions/v2/app/api/products.py:47)  
> **Handler:** `update_product` | **Source Location:** `sample-api/versions/v2/app/api/products.py:47`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_product_service)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `product_id` | `path` | `int` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `ProductUpdate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `name` | `Optional[str]` | No | *None* | min_length=2, max_length=100 | *(Not documented)* |
| `description` | `Optional[str]` | No | *None* | max_length=500 | *(Not documented)* |
| `price` | `Optional[float]` | No | *None* | gt=0 | *(Not documented)* |
| `category` | `Optional[ProductCategory]` | No | *None* | *None* | *(Not documented)* |
| `stock` | `Optional[int]` | No | *None* | ge=0 | *(Not documented)* |

#### Responses
- **HTTP 200** (`ProductResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `int` | No | Unique product identifier |
  | `stock` | `int` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `sample-api/tests/test_v1_api.py::test_v1_products_crud_and_filtering`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_products_breaking_and_non_breaking_changes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_response_field_stock_removed`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_required_param_store_id_api_v1_products`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_method_removed_delete_api_v1_products__product_id`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_response_field_stock_removed`

---

### <a id="put-usersuser_id"></a>`PUT /users/{user_id}`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (sample-api/versions/v2/app/api/users.py:45)  
> **Handler:** `update_user` | **Source Location:** `sample-api/versions/v2/app/api/users.py:45`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_user_service)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `user_id` | `path` | `int` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `UserUpdate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `username` | `Optional[str]` | No | *None* | min_length=3, max_length=50 | *(Not documented)* |
| `email` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `role` | `Optional[UserRole]` | No | *None* | *None* | *(Not documented)* |
| `is_active` | `Optional[bool]` | No | *None* | *None* | *(Not documented)* |

#### Responses
- **HTTP 200** (`UserResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `int` | No | Unique integer ID |
  | `is_active` | `bool` | No | Account active status |

#### Verified Test Coverage
- ✅ `sample-api/tests/test_v1_api.py::test_v1_users_crud_and_validation`
- ✅ `sample-api/tests/test_detection_assertions.py::test_algorithmic_comparison_assertions`
- ✅ `sample-api/tests/test_v2_api.py::test_v2_users_with_search_and_notes`
- ✅ `sample-api/generated-tests/test_candidate_regression_v2.py::test_regression_optional_param_search_supported`
- ✅ `sample-api/generated-tests/test_approved_regression_v2.py::test_regression_optional_param_search_supported`

---
