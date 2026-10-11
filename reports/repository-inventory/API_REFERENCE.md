# Dependency Guardian — API Reference Documentation

**Total Discovered Endpoints:** 6  
**Generated On:** `2026-10-11T07:54:40.667589+00:00`  

## Table of Contents

- [`GET /api/v1/health`](#get-apiv1health)
- [`GET /api/v1/legacy-analytics`](#get-apiv1legacy-analytics)
- [`GET /api/v1/users`](#get-apiv1users)
- [`GET /api/v1/users/{user_id}`](#get-apiv1usersuser_id)
- [`POST /api/v1/orders`](#post-apiv1orders)
- [`POST /api/v1/users`](#post-apiv1users)

---

### <a id="get-apiv1health"></a>`GET /api/v1/health`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_regex:express_app (web/server.js:11)  
> **Handler:** `anonymous_handler` | **Source Location:** `web/server.js:11`  
> **Confidence Level:** `95%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
*No path, query, header, or cookie parameters required.*

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : OK response

#### Verified Test Coverage
- ⚠️ *No automated tests found covering this route (Coverage Gap).*

---

### <a id="get-apiv1legacy-analytics"></a>`GET /api/v1/legacy-analytics`

**Summary:** Legacy analytics summary (Ghost Endpoint)  
**Description:** Deprecated endpoint documented in spec but no longer implemented in code.  

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
- **HTTP 200** : Analytics summary

#### Verified Test Coverage
- ⚠️ *No automated tests found covering this route (Coverage Gap).*

---

### <a id="get-apiv1users"></a>`GET /api/v1/users`

**Summary:** List all active users  
**Description:** Retrieve paginated list of registered users.  

> [!NOTE]
> **Discovery Method:** `hybrid` | **Evidence:** hybrid_source_and_openapi (app/main.py:45 & openapi.json)  
> **Handler:** `list_users` | **Source Location:** `app/main.py:45`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `limit` | `query` | `integer` | No | `10` | minimum=1, maximum=100 | Maximum number of items to return |
| `role` | `query` | `string` | No | *None* | *None* | Filter users by role |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : Successfully retrieved users list

#### Verified Test Coverage
- ✅ `tests/test_api.py::test_list_users`
- ✅ `tests/test_api.py::test_create_user`

---

### <a id="get-apiv1usersuser_id"></a>`GET /api/v1/users/{user_id}`

**Summary:** Fetch single user by unique identifier.  

> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/main.py:88)  
> **Handler:** `get_user_by_id` | **Source Location:** `app/main.py:88`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `user_id` | `path` | `int` | ✅ Yes | *None* | *None* | Target user identifier |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`UserResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `int` | No | Unique user ID |
  | `username` | `str` | No | User name |
  | `email` | `str` | No | Email address |
  | `created_at` | `str` | No | Account creation timestamp |

#### Error Cases & Side Effects
**Error Cases:**
- `HTTP 404`: User not found

#### Verified Test Coverage
- ✅ `tests/test_api.py::test_create_user`

---

### <a id="post-apiv1orders"></a>`POST /api/v1/orders`

**Summary:** Undocumented route implemented in source code but missing from OpenAPI spec.  

> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/main.py:103)  
> **Handler:** `create_order` | **Source Location:** `app/main.py:103`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
*No path, query, header, or cookie parameters required.*

#### Request Body
**Content-Type:** `application/json` | **Schema:** `OrderCreate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `item_name` | `str` | No | *None* | min_length=1 | Item identifier |
| `amount` | `float` | No | *None* | gt=0 | Order total in USD |

#### Responses
- **HTTP 201** : Successful response (201)

#### Error Cases & Side Effects
**Side Effects:**
- `database_write` on `Database`: Persists changes or updates entity in database transaction
- `database_write` on `Database`: Persists changes or updates entity in database transaction

#### Verified Test Coverage
- ⚠️ *No automated tests found covering this route (Coverage Gap).*

---

### <a id="post-apiv1users"></a>`POST /api/v1/users`

**Summary:** Register a new user  
**Description:** Create a new user record in the database.  

> [!NOTE]
> **Discovery Method:** `hybrid` | **Evidence:** hybrid_source_and_openapi (app/main.py:54 & openapi.json)  
> **Handler:** `create_user` | **Source Location:** `app/main.py:54`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_current_user)

#### Parameters
*No path, query, header, or cookie parameters required.*

#### Request Body
**Content-Type:** `application/json` | **Schema:** `UserCreate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `username` | `string` | ✅ Yes | *None* | minLength=3, maxLength=50 | Unique username |
| `email` | `string` | ✅ Yes | *None* | *None* | User primary email address |
| `age` | `integer` | No | *None* | minimum=18, maximum=120 | User age in years |
| `status` | `string` | No | `pending` | *None* | Account status |

#### Responses
- **HTTP 201** (`UserResponse`): User created successfully
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `integer` | Yes | Unique user ID |
  | `username` | `string` | Yes | User name |
  | `email` | `string` | Yes | Email address |
  | `created_at` | `string` | Yes | Account creation timestamp |

#### Error Cases & Side Effects
**Error Cases:**
- `HTTP 400`: Username already taken
**Side Effects:**
- `database_write` on `Database`: Persists changes or updates entity in database transaction
- `database_write` on `Database`: Persists changes or updates entity in database transaction
- `external_http` on `External Service`: Dispatches outbound call: httpx.post
- `message_publish` on `Message Queue`: Publishes asynchronous event or task

#### Verified Test Coverage
- ✅ `tests/test_api.py::test_create_user`

---
