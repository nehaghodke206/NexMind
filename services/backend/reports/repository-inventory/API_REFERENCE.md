# Dependency Guardian — API Reference Documentation

**Total Discovered Endpoints:** 51  
**Generated On:** `2026-10-11T20:50:57.743330+00:00`  

## Table of Contents

- [`GET /baselines/{baseline_id}`](#get-baselinesbaseline_id)
- [`GET /dependencies/{dependency_id}`](#get-dependenciesdependency_id)
- [`GET /dependencies/{dependency_id}/baselines`](#get-dependenciesdependency_idbaselines)
- [`GET /health`](#get-health)
- [`GET /incidents/{incident_id}`](#get-incidentsincident_id)
- [`GET /incidents/{incident_id}/events`](#get-incidentsincident_idevents)
- [`GET /incidents/{incident_id}/observations`](#get-incidentsincident_idobservations)
- [`GET /incidents/{incident_id}/repair-proposals`](#get-incidentsincident_idrepair-proposals)
- [`GET /incidents/{incident_id}/repairs`](#get-incidentsincident_idrepairs)
- [`GET /projects`](#get-projects)
- [`GET /projects/{project_id}`](#get-projectsproject_id)
- [`GET /projects/{project_id}/activity`](#get-projectsproject_idactivity)
- [`GET /projects/{project_id}/baselines`](#get-projectsproject_idbaselines)
- [`GET /projects/{project_id}/baselines/active`](#get-projectsproject_idbaselinesactive)
- [`GET /projects/{project_id}/baselines/compare`](#get-projectsproject_idbaselinescompare)
- [`GET /projects/{project_id}/baselines/{baseline_id}`](#get-projectsproject_idbaselinesbaseline_id)
- [`GET /projects/{project_id}/dependencies`](#get-projectsproject_iddependencies)
- [`GET /projects/{project_id}/incidents`](#get-projectsproject_idincidents)
- [`GET /projects/{project_id}/members`](#get-projectsproject_idmembers)
- [`GET /projects/{project_id}/scans`](#get-projectsproject_idscans)
- [`GET /projects/{project_id}/summary`](#get-projectsproject_idsummary)
- [`GET /repair-proposals/{repair_id}`](#get-repair-proposalsrepair_id)
- [`GET /repair-proposals/{repair_id}/validation-runs`](#get-repair-proposalsrepair_idvalidation-runs)
- [`GET /repairs/{repair_id}`](#get-repairsrepair_id)
- [`GET /repairs/{repair_id}/validation-runs`](#get-repairsrepair_idvalidation-runs)
- [`GET /scans/{scan_id}`](#get-scansscan_id)
- [`PATCH /dependencies/{dependency_id}`](#patch-dependenciesdependency_id)
- [`PATCH /incidents/{incident_id}`](#patch-incidentsincident_id)
- [`POST /dependencies/{dependency_id}/baselines`](#post-dependenciesdependency_idbaselines)
- [`POST /incidents/{incident_id}/acknowledge`](#post-incidentsincident_idacknowledge)
- [`POST /incidents/{incident_id}/reopen`](#post-incidentsincident_idreopen)
- [`POST /incidents/{incident_id}/repair-proposals`](#post-incidentsincident_idrepair-proposals)
- [`POST /incidents/{incident_id}/repairs`](#post-incidentsincident_idrepairs)
- [`POST /incidents/{incident_id}/resolve`](#post-incidentsincident_idresolve)
- [`POST /projects`](#post-projects)
- [`POST /projects/{project_id}/baselines`](#post-projectsproject_idbaselines)
- [`POST /projects/{project_id}/baselines/{baseline_id}/promote`](#post-projectsproject_idbaselinesbaseline_idpromote)
- [`POST /projects/{project_id}/dependencies`](#post-projectsproject_iddependencies)
- [`POST /projects/{project_id}/incidents`](#post-projectsproject_idincidents)
- [`POST /projects/{project_id}/members`](#post-projectsproject_idmembers)
- [`POST /projects/{project_id}/scans`](#post-projectsproject_idscans)
- [`POST /projects/{project_id}/scans/ingest`](#post-projectsproject_idscansingest)
- [`POST /repair-proposals/{repair_id}/applications`](#post-repair-proposalsrepair_idapplications)
- [`POST /repair-proposals/{repair_id}/approvals`](#post-repair-proposalsrepair_idapprovals)
- [`POST /repair-proposals/{repair_id}/rejection`](#post-repair-proposalsrepair_idrejection)
- [`POST /repair-proposals/{repair_id}/validation-runs`](#post-repair-proposalsrepair_idvalidation-runs)
- [`POST /repairs/{repair_id}/apply-result`](#post-repairsrepair_idapply-result)
- [`POST /repairs/{repair_id}/approve`](#post-repairsrepair_idapprove)
- [`POST /repairs/{repair_id}/validate`](#post-repairsrepair_idvalidate)
- [`POST /scans/{scan_id}/complete`](#post-scansscan_idcomplete)
- [`POST /scans/{scan_id}/observations`](#post-scansscan_idobservations)

---

### <a id="get-baselinesbaseline_id"></a>`GET /baselines/{baseline_id}`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/baselines.py:158)  
> **Handler:** `get_baseline` | **Source Location:** `app/routers/baselines.py:158`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `baseline_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`BaselineResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `dependency_id` | `str` | Yes | *(Not documented)* |
  | `version` | `int` | No | *(Not documented)* |
  | `contract` | `Dict[Any]` | Yes | *(Not documented)* |
  | `source` | `str` | Yes | *(Not documented)* |
  | `created_by` | `Optional[str]` | No | *(Not documented)* |
  | `created_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_baselines_scans_incidents.py::test_project_baselines_versioning_and_promotion`
- ✅ `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`

---

### <a id="get-dependenciesdependency_id"></a>`GET /dependencies/{dependency_id}`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/dependencies.py:30)  
> **Handler:** `get_dependency` | **Source Location:** `app/routers/dependencies.py:30`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `dependency_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`DependencyResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `project_id` | `str` | Yes | *(Not documented)* |
  | `name` | `str` | Yes | *(Not documented)* |
  | `kind` | `str` | Yes | *(Not documented)* |
  | `base_url` | `Optional[str]` | No | *(Not documented)* |
  | `version` | `Optional[str]` | No | *(Not documented)* |
  | `configuration` | `Dict[Any]` | No | *(Not documented)* |
  | `created_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_query_filters_and_pagination.py::test_incident_filters_and_pagination`
- ✅ `tests/test_query_filters_and_pagination.py::test_dependency_patch_update`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`
- ✅ `tests/test_repairs_lifecycle.py::test_project_activity_and_dashboard_summary`
- ✅ `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`
- ✅ `tests/test_first_vertical_slice.py::test_fingerprint_deduplication`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_apply_unapproved_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_reapprove_or_reject_already_decided_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_invalid_incident_lifecycle_transition`
- ✅ `tests/test_contract_examples.py::test_compatibility_with_shared_contract_examples`

---

### <a id="get-dependenciesdependency_idbaselines"></a>`GET /dependencies/{dependency_id}/baselines`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/baselines.py:116)  
> **Handler:** `list_baselines` | **Source Location:** `app/routers/baselines.py:116`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `dependency_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : Successful response (200)

#### Verified Test Coverage
- ✅ `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`

---

### <a id="get-health"></a>`GET /health`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/health.py:8)  
> **Handler:** `get_health` | **Source Location:** `app/routers/health.py:8`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔓 **Authentication & Authorization:** Public / None detected

#### Parameters
*No path, query, header, or cookie parameters required.*

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : Successful response (200)

#### Verified Test Coverage
- ✅ `tests/test_health.py::test_health_root`
- ✅ `tests/test_health.py::test_health_api_prefix`

---

### <a id="get-incidentsincident_id"></a>`GET /incidents/{incident_id}`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/incidents.py:56)  
> **Handler:** `get_incident` | **Source Location:** `app/routers/incidents.py:56`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `incident_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`IncidentResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `project_id` | `str` | Yes | *(Not documented)* |
  | `dependency_id` | `Optional[str]` | No | *(Not documented)* |
  | `title` | `str` | Yes | *(Not documented)* |
  | `description` | `Optional[str]` | No | *(Not documented)* |
  | `change_type` | `str` | Yes | *(Not documented)* |
  | `severity` | `str` | Yes | *(Not documented)* |
  | `status` | `str` | Yes | *(Not documented)* |
  | `provenance` | `str` | No | *(Not documented)* |
  | `confidence` | `Optional[float]` | No | *(Not documented)* |
  | `occurrence_count` | `int` | No | *(Not documented)* |
  | `fingerprint` | `Optional[str]` | No | *(Not documented)* |
  | `recommended_action` | `Optional[str]` | No | *(Not documented)* |
  | `resolution_notes` | `Optional[str]` | No | *(Not documented)* |
  | `review_notes` | `Optional[str]` | No | *(Not documented)* |
  | `assignee_id` | `Optional[str]` | No | *(Not documented)* |
  | `affected_workflows` | `List[str]` | No | *(Not documented)* |
  | `affected_files` | `List[str]` | No | *(Not documented)* |
  | `evidence_summary` | `Optional[str]` | No | *(Not documented)* |
  | `first_detected_at` | `datetime` | Yes | *(Not documented)* |
  | `last_observed_at` | `datetime` | Yes | *(Not documented)* |
  | `acknowledged_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `acknowledged_by` | `Optional[str]` | No | *(Not documented)* |
  | `resolved_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `reopened_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `created_at` | `datetime` | Yes | *(Not documented)* |
  | `updated_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_query_filters_and_pagination.py::test_incident_filters_and_pagination`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`
- ✅ `tests/test_repairs_lifecycle.py::test_project_activity_and_dashboard_summary`
- ✅ `tests/test_baselines_scans_incidents.py::test_scan_ingest_idempotency`
- ✅ `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence`
- ✅ `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`
- ✅ `tests/test_first_vertical_slice.py::test_fingerprint_deduplication`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_apply_unapproved_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_reapprove_or_reject_already_decided_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_invalid_incident_lifecycle_transition`
- ✅ `tests/test_contract_examples.py::test_compatibility_with_shared_contract_examples`

---

### <a id="get-incidentsincident_idevents"></a>`GET /incidents/{incident_id}/events`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/incidents.py:109)  
> **Handler:** `list_incident_events` | **Source Location:** `app/routers/incidents.py:109`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `incident_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : Successful response (200)

#### Verified Test Coverage
- ✅ `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence`

---

### <a id="get-incidentsincident_idobservations"></a>`GET /incidents/{incident_id}/observations`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/incidents.py:116)  
> **Handler:** `list_incident_observations` | **Source Location:** `app/routers/incidents.py:116`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `incident_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : Successful response (200)

#### Verified Test Coverage
- ✅ `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`
- ✅ `tests/test_first_vertical_slice.py::test_fingerprint_deduplication`

---

### <a id="get-incidentsincident_idrepair-proposals"></a>`GET /incidents/{incident_id}/repair-proposals`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/incidents.py:125)  
> **Handler:** `list_repair_proposals` | **Source Location:** `app/routers/incidents.py:125`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `incident_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : Successful response (200)

#### Verified Test Coverage
- ✅ `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_apply_unapproved_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_reapprove_or_reject_already_decided_repair`

---

### <a id="get-incidentsincident_idrepairs"></a>`GET /incidents/{incident_id}/repairs`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/incidents.py:125)  
> **Handler:** `list_repair_proposals` | **Source Location:** `app/routers/incidents.py:125`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `incident_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : Successful response (200)

#### Verified Test Coverage
- ✅ `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`
- ✅ `tests/test_contract_examples.py::test_compatibility_with_shared_contract_examples`

---

### <a id="get-projects"></a>`GET /projects`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/projects.py:21)  
> **Handler:** `list_projects` | **Source Location:** `app/routers/projects.py:21`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `page` | `query` | `int` | ✅ Yes | *None* | ge=1 | *(Not documented)* |
| `page_size` | `query` | `int` | ✅ Yes | *None* | ge=1, le=100 | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`ProjectListResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `items` | `List[ProjectResponse]` | Yes | *(Not documented)* |
  | `page` | `int` | Yes | *(Not documented)* |
  | `page_size` | `int` | Yes | *(Not documented)* |
  | `total` | `int` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_query_filters_and_pagination.py::test_incident_filters_and_pagination`
- ✅ `tests/test_query_filters_and_pagination.py::test_dependency_patch_update`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`
- ✅ `tests/test_repairs_lifecycle.py::test_project_activity_and_dashboard_summary`
- ✅ `tests/test_baselines_scans_incidents.py::test_project_baselines_versioning_and_promotion`
- ✅ `tests/test_baselines_scans_incidents.py::test_scan_ingest_idempotency`
- ✅ `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence`
- ✅ `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`
- ✅ `tests/test_first_vertical_slice.py::test_fingerprint_deduplication`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_apply_unapproved_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_reapprove_or_reject_already_decided_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_duplicate_project_member_error`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_invalid_incident_lifecycle_transition`
- ✅ `tests/test_contract_examples.py::test_compatibility_with_shared_contract_examples`

---

### <a id="get-projectsproject_id"></a>`GET /projects/{project_id}`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/projects.py:44)  
> **Handler:** `get_project` | **Source Location:** `app/routers/projects.py:44`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `project_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`ProjectResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `created_at` | `datetime` | Yes | *(Not documented)* |
  | `updated_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_query_filters_and_pagination.py::test_incident_filters_and_pagination`
- ✅ `tests/test_query_filters_and_pagination.py::test_dependency_patch_update`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`
- ✅ `tests/test_repairs_lifecycle.py::test_project_activity_and_dashboard_summary`
- ✅ `tests/test_baselines_scans_incidents.py::test_project_baselines_versioning_and_promotion`
- ✅ `tests/test_baselines_scans_incidents.py::test_scan_ingest_idempotency`
- ✅ `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence`
- ✅ `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`
- ✅ `tests/test_first_vertical_slice.py::test_fingerprint_deduplication`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_apply_unapproved_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_reapprove_or_reject_already_decided_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_duplicate_project_member_error`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_invalid_incident_lifecycle_transition`
- ✅ `tests/test_contract_examples.py::test_compatibility_with_shared_contract_examples`

---

### <a id="get-projectsproject_idactivity"></a>`GET /projects/{project_id}/activity`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/projects.py:65)  
> **Handler:** `list_activity` | **Source Location:** `app/routers/projects.py:65`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `project_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |
| `page` | `query` | `int` | ✅ Yes | *None* | ge=1 | *(Not documented)* |
| `page_size` | `query` | `int` | ✅ Yes | *None* | ge=1, le=100 | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`ActivityEventListResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `items` | `List[ActivityEventResponse]` | Yes | *(Not documented)* |
  | `page` | `int` | Yes | *(Not documented)* |
  | `page_size` | `int` | Yes | *(Not documented)* |
  | `total` | `int` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_repairs_lifecycle.py::test_project_activity_and_dashboard_summary`

---

### <a id="get-projectsproject_idbaselines"></a>`GET /projects/{project_id}/baselines`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/baselines.py:27)  
> **Handler:** `list_project_baselines` | **Source Location:** `app/routers/baselines.py:27`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `project_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`ProjectBaselineListResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `items` | `List[ProjectBaselineResponse]` | Yes | *(Not documented)* |
  | `total` | `int` | Yes | *(Not documented)* |
  | `active_baseline` | `Optional[ProjectBaselineResponse]` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_baselines_scans_incidents.py::test_project_baselines_versioning_and_promotion`
- ✅ `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`

---

### <a id="get-projectsproject_idbaselinesactive"></a>`GET /projects/{project_id}/baselines/active`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/baselines.py:57)  
> **Handler:** `get_active_project_baseline` | **Source Location:** `app/routers/baselines.py:57`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `project_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : Successful response (200)

#### Verified Test Coverage
- ✅ `tests/test_baselines_scans_incidents.py::test_project_baselines_versioning_and_promotion`

---

### <a id="get-projectsproject_idbaselinescompare"></a>`GET /projects/{project_id}/baselines/compare`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/baselines.py:70)  
> **Handler:** `compare_project_baselines` | **Source Location:** `app/routers/baselines.py:70`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `project_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |
| `base` | `query` | `str` | ✅ Yes | *None* | *None* | Base baseline ID or version number |
| `target` | `query` | `str` | ✅ Yes | *None* | *None* | Target baseline ID or version number |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`ProjectBaselineCompareResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `project_id` | `str` | Yes | *(Not documented)* |
  | `base_version` | `int` | Yes | *(Not documented)* |
  | `target_version` | `int` | Yes | *(Not documented)* |
  | `base_id` | `str` | Yes | *(Not documented)* |
  | `target_id` | `str` | Yes | *(Not documented)* |
  | `endpoints_added` | `List[Dict[Any]]` | No | *(Not documented)* |
  | `endpoints_removed` | `List[Dict[Any]]` | No | *(Not documented)* |
  | `endpoints_modified` | `List[Dict[Any]]` | No | *(Not documented)* |
  | `contract_diffs` | `Dict[Any]` | No | *(Not documented)* |
  | `summary` | `Dict[Any]` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_baselines_scans_incidents.py::test_project_baselines_versioning_and_promotion`

---

### <a id="get-projectsproject_idbaselinesbaseline_id"></a>`GET /projects/{project_id}/baselines/{baseline_id}`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/baselines.py:85)  
> **Handler:** `get_project_baseline` | **Source Location:** `app/routers/baselines.py:85`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `project_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |
| `baseline_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`ProjectBaselineResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `project_id` | `str` | Yes | *(Not documented)* |
  | `version` | `int` | No | *(Not documented)* |
  | `version_tag` | `Optional[str]` | No | *(Not documented)* |
  | `contracts` | `Dict[Any]` | No | *(Not documented)* |
  | `inventory` | `Dict[Any]` | No | *(Not documented)* |
  | `source_scan_id` | `Optional[str]` | No | *(Not documented)* |
  | `content_hash` | `Optional[str]` | No | *(Not documented)* |
  | `created_by` | `Optional[str]` | No | *(Not documented)* |
  | `is_active` | `bool` | Yes | *(Not documented)* |
  | `is_promoted` | `bool` | Yes | *(Not documented)* |
  | `promoted_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `promoted_by` | `Optional[str]` | No | *(Not documented)* |
  | `notes` | `Optional[str]` | No | *(Not documented)* |
  | `created_at` | `datetime` | Yes | *(Not documented)* |
  | `updated_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_baselines_scans_incidents.py::test_project_baselines_versioning_and_promotion`
- ✅ `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`

---

### <a id="get-projectsproject_iddependencies"></a>`GET /projects/{project_id}/dependencies`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/dependencies.py:16)  
> **Handler:** `list_dependencies` | **Source Location:** `app/routers/dependencies.py:16`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `project_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : Successful response (200)

#### Verified Test Coverage
- ✅ `tests/test_query_filters_and_pagination.py::test_incident_filters_and_pagination`
- ✅ `tests/test_query_filters_and_pagination.py::test_dependency_patch_update`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`
- ✅ `tests/test_repairs_lifecycle.py::test_project_activity_and_dashboard_summary`
- ✅ `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`
- ✅ `tests/test_first_vertical_slice.py::test_fingerprint_deduplication`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_apply_unapproved_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_reapprove_or_reject_already_decided_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_invalid_incident_lifecycle_transition`
- ✅ `tests/test_contract_examples.py::test_compatibility_with_shared_contract_examples`

---

### <a id="get-projectsproject_idincidents"></a>`GET /projects/{project_id}/incidents`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/incidents.py:22)  
> **Handler:** `list_incidents` | **Source Location:** `app/routers/incidents.py:22`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `project_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |
| `status` | `query` | `Optional[str]` | ✅ Yes | *None* | *None* | *(Not documented)* |
| `severity` | `query` | `Optional[str]` | ✅ Yes | *None* | *None* | *(Not documented)* |
| `assignee_id` | `query` | `Optional[str]` | ✅ Yes | *None* | *None* | *(Not documented)* |
| `page` | `query` | `int` | ✅ Yes | *None* | ge=1 | *(Not documented)* |
| `page_size` | `query` | `int` | ✅ Yes | *None* | ge=1, le=100 | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`IncidentListResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `items` | `List[IncidentResponse]` | Yes | *(Not documented)* |
  | `page` | `int` | Yes | *(Not documented)* |
  | `page_size` | `int` | Yes | *(Not documented)* |
  | `total` | `int` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_query_filters_and_pagination.py::test_incident_filters_and_pagination`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`
- ✅ `tests/test_repairs_lifecycle.py::test_project_activity_and_dashboard_summary`
- ✅ `tests/test_baselines_scans_incidents.py::test_scan_ingest_idempotency`
- ✅ `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence`
- ✅ `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`
- ✅ `tests/test_first_vertical_slice.py::test_fingerprint_deduplication`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_apply_unapproved_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_reapprove_or_reject_already_decided_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_invalid_incident_lifecycle_transition`
- ✅ `tests/test_contract_examples.py::test_compatibility_with_shared_contract_examples`

---

### <a id="get-projectsproject_idmembers"></a>`GET /projects/{project_id}/members`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/projects.py:51)  
> **Handler:** `list_members` | **Source Location:** `app/routers/projects.py:51`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `project_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : Successful response (200)

#### Verified Test Coverage
- ✅ `tests/test_repairs_lifecycle.py::test_project_activity_and_dashboard_summary`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_duplicate_project_member_error`

---

### <a id="get-projectsproject_idscans"></a>`GET /projects/{project_id}/scans`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/scans.py:22)  
> **Handler:** `list_scans` | **Source Location:** `app/routers/scans.py:22`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `project_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |
| `limit` | `query` | `int` | ✅ Yes | *None* | ge=1, le=200 | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : Successful response (200)

#### Verified Test Coverage
- ✅ `tests/test_baselines_scans_incidents.py::test_scan_ingest_idempotency`
- ✅ `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence`
- ✅ `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`
- ✅ `tests/test_first_vertical_slice.py::test_fingerprint_deduplication`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`

---

### <a id="get-projectsproject_idsummary"></a>`GET /projects/{project_id}/summary`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/projects.py:82)  
> **Handler:** `get_project_summary` | **Source Location:** `app/routers/projects.py:82`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `project_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`ProjectSummaryResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `project_id` | `str` | Yes | *(Not documented)* |
  | `dependency_count` | `int` | Yes | *(Not documented)* |
  | `open_incident_count` | `int` | Yes | *(Not documented)* |
  | `pending_review_count` | `int` | Yes | *(Not documented)* |
  | `validation_pass_count` | `int` | Yes | *(Not documented)* |
  | `validation_fail_count` | `int` | Yes | *(Not documented)* |
  | `last_scan_at` | `Optional[datetime]` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_repairs_lifecycle.py::test_project_activity_and_dashboard_summary`
- ✅ `tests/test_baselines_scans_incidents.py::test_project_baselines_versioning_and_promotion`
- ✅ `tests/test_baselines_scans_incidents.py::test_scan_ingest_idempotency`
- ✅ `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence`
- ✅ `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`
- ✅ `tests/test_contract_examples.py::test_compatibility_with_shared_contract_examples`

---

### <a id="get-repair-proposalsrepair_id"></a>`GET /repair-proposals/{repair_id}`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/repairs.py:23)  
> **Handler:** `get_repair_proposal` | **Source Location:** `app/routers/repairs.py:23`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `repair_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`RepairProposalResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `incident_id` | `str` | Yes | *(Not documented)* |
  | `status` | `str` | Yes | *(Not documented)* |
  | `rationale` | `str` | Yes | *(Not documented)* |
  | `strategy` | `str` | Yes | *(Not documented)* |
  | `diff_preview` | `Optional[str]` | No | *(Not documented)* |
  | `proposed_changes` | `Dict[Any]` | No | *(Not documented)* |
  | `confidence` | `Optional[float]` | No | *(Not documented)* |
  | `created_by` | `Optional[str]` | No | *(Not documented)* |
  | `created_at` | `datetime` | Yes | *(Not documented)* |
  | `updated_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_apply_unapproved_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_reapprove_or_reject_already_decided_repair`

---

### <a id="get-repair-proposalsrepair_idvalidation-runs"></a>`GET /repair-proposals/{repair_id}/validation-runs`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/repairs.py:31)  
> **Handler:** `list_validation_runs` | **Source Location:** `app/routers/repairs.py:31`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `repair_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : Successful response (200)

#### Verified Test Coverage
- ✅ `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`

---

### <a id="get-repairsrepair_id"></a>`GET /repairs/{repair_id}`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/repairs.py:23)  
> **Handler:** `get_repair_proposal` | **Source Location:** `app/routers/repairs.py:23`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `repair_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`RepairProposalResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `incident_id` | `str` | Yes | *(Not documented)* |
  | `status` | `str` | Yes | *(Not documented)* |
  | `rationale` | `str` | Yes | *(Not documented)* |
  | `strategy` | `str` | Yes | *(Not documented)* |
  | `diff_preview` | `Optional[str]` | No | *(Not documented)* |
  | `proposed_changes` | `Dict[Any]` | No | *(Not documented)* |
  | `confidence` | `Optional[float]` | No | *(Not documented)* |
  | `created_by` | `Optional[str]` | No | *(Not documented)* |
  | `created_at` | `datetime` | Yes | *(Not documented)* |
  | `updated_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`
- ✅ `tests/test_contract_examples.py::test_compatibility_with_shared_contract_examples`

---

### <a id="get-repairsrepair_idvalidation-runs"></a>`GET /repairs/{repair_id}/validation-runs`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/repairs.py:31)  
> **Handler:** `list_validation_runs` | **Source Location:** `app/routers/repairs.py:31`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `repair_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** : Successful response (200)

#### Verified Test Coverage
- ✅ `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`

---

### <a id="get-scansscan_id"></a>`GET /scans/{scan_id}`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/scans.py:59)  
> **Handler:** `get_scan` | **Source Location:** `app/routers/scans.py:59`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `scan_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`ScanRunResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `project_id` | `str` | Yes | *(Not documented)* |
  | `dependency_id` | `Optional[str]` | No | *(Not documented)* |
  | `initiated_by` | `Optional[str]` | No | *(Not documented)* |
  | `scan_type` | `str` | No | *(Not documented)* |
  | `detection_mode` | `Optional[str]` | No | *(Not documented)* |
  | `capabilities_executed` | `List[str]` | No | *(Not documented)* |
  | `status` | `str` | Yes | *(Not documented)* |
  | `duration_seconds` | `Optional[float]` | No | *(Not documented)* |
  | `summary_counts` | `Dict[Any]` | No | *(Not documented)* |
  | `summary` | `Optional[str]` | No | *(Not documented)* |
  | `error_message` | `Optional[str]` | No | *(Not documented)* |
  | `is_local` | `bool` | No | *(Not documented)* |
  | `sync_status` | `str` | No | *(Not documented)* |
  | `client_run_id` | `Optional[str]` | No | *(Not documented)* |
  | `started_at` | `datetime` | Yes | *(Not documented)* |
  | `completed_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `created_at` | `Optional[datetime]` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_baselines_scans_incidents.py::test_scan_ingest_idempotency`
- ✅ `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence`
- ✅ `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`
- ✅ `tests/test_first_vertical_slice.py::test_fingerprint_deduplication`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`

---

### <a id="patch-dependenciesdependency_id"></a>`PATCH /dependencies/{dependency_id}`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/dependencies.py:37)  
> **Handler:** `update_dependency` | **Source Location:** `app/routers/dependencies.py:37`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `dependency_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `DependencyUpdate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `name` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `kind` | `Optional[str]` | No | *None* | pattern=^(rest_api|sdk|package|mcp_tool|other)$ | *(Not documented)* |
| `base_url` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `version` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `configuration` | `Optional[Dict[Any]]` | No | *None* | *None* | *(Not documented)* |

#### Responses
- **HTTP 200** (`DependencyResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `project_id` | `str` | Yes | *(Not documented)* |
  | `name` | `str` | Yes | *(Not documented)* |
  | `kind` | `str` | Yes | *(Not documented)* |
  | `base_url` | `Optional[str]` | No | *(Not documented)* |
  | `version` | `Optional[str]` | No | *(Not documented)* |
  | `configuration` | `Dict[Any]` | No | *(Not documented)* |
  | `created_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_query_filters_and_pagination.py::test_incident_filters_and_pagination`
- ✅ `tests/test_query_filters_and_pagination.py::test_dependency_patch_update`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`
- ✅ `tests/test_repairs_lifecycle.py::test_project_activity_and_dashboard_summary`
- ✅ `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`
- ✅ `tests/test_first_vertical_slice.py::test_fingerprint_deduplication`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_apply_unapproved_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_reapprove_or_reject_already_decided_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_invalid_incident_lifecycle_transition`
- ✅ `tests/test_contract_examples.py::test_compatibility_with_shared_contract_examples`

---

### <a id="patch-incidentsincident_id"></a>`PATCH /incidents/{incident_id}`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/incidents.py:63)  
> **Handler:** `update_incident` | **Source Location:** `app/routers/incidents.py:63`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `incident_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `IncidentUpdate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `status` | `Optional[str]` | No | *None* | pattern=^(open|acknowledged|resolved|reopened|triaged|in_progress|awaiting_review|dismissed)$ | *(Not documented)* |
| `assignee_id` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `review_notes` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `resolution_notes` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `recommended_action` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `severity` | `Optional[str]` | No | *None* | pattern=^(low|medium|high|critical|blocked)$ | *(Not documented)* |

#### Responses
- **HTTP 200** (`IncidentResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `project_id` | `str` | Yes | *(Not documented)* |
  | `dependency_id` | `Optional[str]` | No | *(Not documented)* |
  | `title` | `str` | Yes | *(Not documented)* |
  | `description` | `Optional[str]` | No | *(Not documented)* |
  | `change_type` | `str` | Yes | *(Not documented)* |
  | `severity` | `str` | Yes | *(Not documented)* |
  | `status` | `str` | Yes | *(Not documented)* |
  | `provenance` | `str` | No | *(Not documented)* |
  | `confidence` | `Optional[float]` | No | *(Not documented)* |
  | `occurrence_count` | `int` | No | *(Not documented)* |
  | `fingerprint` | `Optional[str]` | No | *(Not documented)* |
  | `recommended_action` | `Optional[str]` | No | *(Not documented)* |
  | `resolution_notes` | `Optional[str]` | No | *(Not documented)* |
  | `review_notes` | `Optional[str]` | No | *(Not documented)* |
  | `assignee_id` | `Optional[str]` | No | *(Not documented)* |
  | `affected_workflows` | `List[str]` | No | *(Not documented)* |
  | `affected_files` | `List[str]` | No | *(Not documented)* |
  | `evidence_summary` | `Optional[str]` | No | *(Not documented)* |
  | `first_detected_at` | `datetime` | Yes | *(Not documented)* |
  | `last_observed_at` | `datetime` | Yes | *(Not documented)* |
  | `acknowledged_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `acknowledged_by` | `Optional[str]` | No | *(Not documented)* |
  | `resolved_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `reopened_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `created_at` | `datetime` | Yes | *(Not documented)* |
  | `updated_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_query_filters_and_pagination.py::test_incident_filters_and_pagination`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`
- ✅ `tests/test_repairs_lifecycle.py::test_project_activity_and_dashboard_summary`
- ✅ `tests/test_baselines_scans_incidents.py::test_scan_ingest_idempotency`
- ✅ `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence`
- ✅ `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`
- ✅ `tests/test_first_vertical_slice.py::test_fingerprint_deduplication`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_apply_unapproved_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_reapprove_or_reject_already_decided_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_invalid_incident_lifecycle_transition`
- ✅ `tests/test_contract_examples.py::test_compatibility_with_shared_contract_examples`

---

### <a id="post-dependenciesdependency_idbaselines"></a>`POST /dependencies/{dependency_id}/baselines`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/baselines.py:139)  
> **Handler:** `create_baseline` | **Source Location:** `app/routers/baselines.py:139`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `dependency_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `BaselineCreate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `contract` | `Dict[Any]` | ✅ Yes | *None* | *None* | *(Not documented)* |
| `source` | `str` | No | `manual` | pattern=^(manual|scan|imported)$ | *(Not documented)* |
| `created_by` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `notes` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |

#### Responses
- **HTTP 201** (`BaselineResponse`): Successful response (201)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `dependency_id` | `str` | Yes | *(Not documented)* |
  | `version` | `int` | No | *(Not documented)* |
  | `contract` | `Dict[Any]` | Yes | *(Not documented)* |
  | `source` | `str` | Yes | *(Not documented)* |
  | `created_by` | `Optional[str]` | No | *(Not documented)* |
  | `created_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`

---

### <a id="post-incidentsincident_idacknowledge"></a>`POST /incidents/{incident_id}/acknowledge`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/incidents.py:70)  
> **Handler:** `acknowledge_incident` | **Source Location:** `app/routers/incidents.py:70`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `incident_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |
| `payload` | `query` | `Optional[IncidentTransitionRequest]` | No | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`IncidentResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `project_id` | `str` | Yes | *(Not documented)* |
  | `dependency_id` | `Optional[str]` | No | *(Not documented)* |
  | `title` | `str` | Yes | *(Not documented)* |
  | `description` | `Optional[str]` | No | *(Not documented)* |
  | `change_type` | `str` | Yes | *(Not documented)* |
  | `severity` | `str` | Yes | *(Not documented)* |
  | `status` | `str` | Yes | *(Not documented)* |
  | `provenance` | `str` | No | *(Not documented)* |
  | `confidence` | `Optional[float]` | No | *(Not documented)* |
  | `occurrence_count` | `int` | No | *(Not documented)* |
  | `fingerprint` | `Optional[str]` | No | *(Not documented)* |
  | `recommended_action` | `Optional[str]` | No | *(Not documented)* |
  | `resolution_notes` | `Optional[str]` | No | *(Not documented)* |
  | `review_notes` | `Optional[str]` | No | *(Not documented)* |
  | `assignee_id` | `Optional[str]` | No | *(Not documented)* |
  | `affected_workflows` | `List[str]` | No | *(Not documented)* |
  | `affected_files` | `List[str]` | No | *(Not documented)* |
  | `evidence_summary` | `Optional[str]` | No | *(Not documented)* |
  | `first_detected_at` | `datetime` | Yes | *(Not documented)* |
  | `last_observed_at` | `datetime` | Yes | *(Not documented)* |
  | `acknowledged_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `acknowledged_by` | `Optional[str]` | No | *(Not documented)* |
  | `resolved_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `reopened_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `created_at` | `datetime` | Yes | *(Not documented)* |
  | `updated_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence`

---

### <a id="post-incidentsincident_idreopen"></a>`POST /incidents/{incident_id}/reopen`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/incidents.py:96)  
> **Handler:** `reopen_incident` | **Source Location:** `app/routers/incidents.py:96`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `incident_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |
| `payload` | `query` | `Optional[IncidentTransitionRequest]` | No | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`IncidentResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `project_id` | `str` | Yes | *(Not documented)* |
  | `dependency_id` | `Optional[str]` | No | *(Not documented)* |
  | `title` | `str` | Yes | *(Not documented)* |
  | `description` | `Optional[str]` | No | *(Not documented)* |
  | `change_type` | `str` | Yes | *(Not documented)* |
  | `severity` | `str` | Yes | *(Not documented)* |
  | `status` | `str` | Yes | *(Not documented)* |
  | `provenance` | `str` | No | *(Not documented)* |
  | `confidence` | `Optional[float]` | No | *(Not documented)* |
  | `occurrence_count` | `int` | No | *(Not documented)* |
  | `fingerprint` | `Optional[str]` | No | *(Not documented)* |
  | `recommended_action` | `Optional[str]` | No | *(Not documented)* |
  | `resolution_notes` | `Optional[str]` | No | *(Not documented)* |
  | `review_notes` | `Optional[str]` | No | *(Not documented)* |
  | `assignee_id` | `Optional[str]` | No | *(Not documented)* |
  | `affected_workflows` | `List[str]` | No | *(Not documented)* |
  | `affected_files` | `List[str]` | No | *(Not documented)* |
  | `evidence_summary` | `Optional[str]` | No | *(Not documented)* |
  | `first_detected_at` | `datetime` | Yes | *(Not documented)* |
  | `last_observed_at` | `datetime` | Yes | *(Not documented)* |
  | `acknowledged_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `acknowledged_by` | `Optional[str]` | No | *(Not documented)* |
  | `resolved_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `reopened_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `created_at` | `datetime` | Yes | *(Not documented)* |
  | `updated_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_invalid_incident_lifecycle_transition`

---

### <a id="post-incidentsincident_idrepair-proposals"></a>`POST /incidents/{incident_id}/repair-proposals`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/incidents.py:133)  
> **Handler:** `create_repair_proposal` | **Source Location:** `app/routers/incidents.py:133`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `incident_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `RepairProposalCreate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `rationale` | `str` | No | *None* | min_length=1 | *(Not documented)* |
| `strategy` | `str` | No | `compatibility_adapter` | pattern=^(compatibility_adapter|callsite_update|pagination_adapter|manual_review|other)$ | *(Not documented)* |
| `diff_preview` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `proposed_changes` | `Optional[Dict[Any]]` | No | *None* | *None* | *(Not documented)* |
| `confidence` | `Optional[float]` | No | *None* | ge=0.0, le=1.0 | *(Not documented)* |
| `created_by` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `patch` | `Optional[Dict[Any]]` | No | *None* | *None* | *(Not documented)* |

#### Responses
- **HTTP 201** (`RepairProposalResponse`): Successful response (201)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `incident_id` | `str` | Yes | *(Not documented)* |
  | `status` | `str` | Yes | *(Not documented)* |
  | `rationale` | `str` | Yes | *(Not documented)* |
  | `strategy` | `str` | Yes | *(Not documented)* |
  | `diff_preview` | `Optional[str]` | No | *(Not documented)* |
  | `proposed_changes` | `Dict[Any]` | No | *(Not documented)* |
  | `confidence` | `Optional[float]` | No | *(Not documented)* |
  | `created_by` | `Optional[str]` | No | *(Not documented)* |
  | `created_at` | `datetime` | Yes | *(Not documented)* |
  | `updated_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_apply_unapproved_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_reapprove_or_reject_already_decided_repair`

---

### <a id="post-incidentsincident_idrepairs"></a>`POST /incidents/{incident_id}/repairs`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/incidents.py:133)  
> **Handler:** `create_repair_proposal` | **Source Location:** `app/routers/incidents.py:133`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `incident_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `RepairProposalCreate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `rationale` | `str` | No | *None* | min_length=1 | *(Not documented)* |
| `strategy` | `str` | No | `compatibility_adapter` | pattern=^(compatibility_adapter|callsite_update|pagination_adapter|manual_review|other)$ | *(Not documented)* |
| `diff_preview` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `proposed_changes` | `Optional[Dict[Any]]` | No | *None* | *None* | *(Not documented)* |
| `confidence` | `Optional[float]` | No | *None* | ge=0.0, le=1.0 | *(Not documented)* |
| `created_by` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `patch` | `Optional[Dict[Any]]` | No | *None* | *None* | *(Not documented)* |

#### Responses
- **HTTP 201** (`RepairProposalResponse`): Successful response (201)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `incident_id` | `str` | Yes | *(Not documented)* |
  | `status` | `str` | Yes | *(Not documented)* |
  | `rationale` | `str` | Yes | *(Not documented)* |
  | `strategy` | `str` | Yes | *(Not documented)* |
  | `diff_preview` | `Optional[str]` | No | *(Not documented)* |
  | `proposed_changes` | `Dict[Any]` | No | *(Not documented)* |
  | `confidence` | `Optional[float]` | No | *(Not documented)* |
  | `created_by` | `Optional[str]` | No | *(Not documented)* |
  | `created_at` | `datetime` | Yes | *(Not documented)* |
  | `updated_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`
- ✅ `tests/test_contract_examples.py::test_compatibility_with_shared_contract_examples`

---

### <a id="post-incidentsincident_idresolve"></a>`POST /incidents/{incident_id}/resolve`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/incidents.py:83)  
> **Handler:** `resolve_incident` | **Source Location:** `app/routers/incidents.py:83`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `incident_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |
| `payload` | `query` | `Optional[IncidentTransitionRequest]` | No | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`IncidentResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `project_id` | `str` | Yes | *(Not documented)* |
  | `dependency_id` | `Optional[str]` | No | *(Not documented)* |
  | `title` | `str` | Yes | *(Not documented)* |
  | `description` | `Optional[str]` | No | *(Not documented)* |
  | `change_type` | `str` | Yes | *(Not documented)* |
  | `severity` | `str` | Yes | *(Not documented)* |
  | `status` | `str` | Yes | *(Not documented)* |
  | `provenance` | `str` | No | *(Not documented)* |
  | `confidence` | `Optional[float]` | No | *(Not documented)* |
  | `occurrence_count` | `int` | No | *(Not documented)* |
  | `fingerprint` | `Optional[str]` | No | *(Not documented)* |
  | `recommended_action` | `Optional[str]` | No | *(Not documented)* |
  | `resolution_notes` | `Optional[str]` | No | *(Not documented)* |
  | `review_notes` | `Optional[str]` | No | *(Not documented)* |
  | `assignee_id` | `Optional[str]` | No | *(Not documented)* |
  | `affected_workflows` | `List[str]` | No | *(Not documented)* |
  | `affected_files` | `List[str]` | No | *(Not documented)* |
  | `evidence_summary` | `Optional[str]` | No | *(Not documented)* |
  | `first_detected_at` | `datetime` | Yes | *(Not documented)* |
  | `last_observed_at` | `datetime` | Yes | *(Not documented)* |
  | `acknowledged_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `acknowledged_by` | `Optional[str]` | No | *(Not documented)* |
  | `resolved_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `reopened_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `created_at` | `datetime` | Yes | *(Not documented)* |
  | `updated_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`
- ✅ `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_invalid_incident_lifecycle_transition`

---

### <a id="post-projects"></a>`POST /projects`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/projects.py:37)  
> **Handler:** `create_project` | **Source Location:** `app/routers/projects.py:37`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
*No path, query, header, or cookie parameters required.*

#### Request Body
**Content-Type:** `application/json` | **Schema:** `ProjectCreate` (Required)

*Request body schema defines no specific properties.*

#### Responses
- **HTTP 201** (`ProjectResponse`): Successful response (201)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `created_at` | `datetime` | Yes | *(Not documented)* |
  | `updated_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_query_filters_and_pagination.py::test_incident_filters_and_pagination`
- ✅ `tests/test_query_filters_and_pagination.py::test_dependency_patch_update`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`
- ✅ `tests/test_repairs_lifecycle.py::test_project_activity_and_dashboard_summary`
- ✅ `tests/test_baselines_scans_incidents.py::test_project_baselines_versioning_and_promotion`
- ✅ `tests/test_baselines_scans_incidents.py::test_scan_ingest_idempotency`
- ✅ `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence`
- ✅ `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`
- ✅ `tests/test_first_vertical_slice.py::test_fingerprint_deduplication`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_apply_unapproved_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_reapprove_or_reject_already_decided_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_duplicate_project_member_error`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_invalid_incident_lifecycle_transition`
- ✅ `tests/test_contract_examples.py::test_compatibility_with_shared_contract_examples`

---

### <a id="post-projectsproject_idbaselines"></a>`POST /projects/{project_id}/baselines`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/baselines.py:44)  
> **Handler:** `create_project_baseline` | **Source Location:** `app/routers/baselines.py:44`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `project_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `ProjectBaselineCreate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `contracts` | `Dict[Any]` | No | *None* | *None* | *(Not documented)* |
| `inventory` | `Dict[Any]` | No | *None* | *None* | *(Not documented)* |
| `version_tag` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `source_scan_id` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `notes` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `created_by` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `is_promoted` | `bool` | No | `False` | *None* | *(Not documented)* |

#### Responses
- **HTTP 201** (`ProjectBaselineResponse`): Successful response (201)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `project_id` | `str` | Yes | *(Not documented)* |
  | `version` | `int` | No | *(Not documented)* |
  | `version_tag` | `Optional[str]` | No | *(Not documented)* |
  | `contracts` | `Dict[Any]` | No | *(Not documented)* |
  | `inventory` | `Dict[Any]` | No | *(Not documented)* |
  | `source_scan_id` | `Optional[str]` | No | *(Not documented)* |
  | `content_hash` | `Optional[str]` | No | *(Not documented)* |
  | `created_by` | `Optional[str]` | No | *(Not documented)* |
  | `is_active` | `bool` | Yes | *(Not documented)* |
  | `is_promoted` | `bool` | Yes | *(Not documented)* |
  | `promoted_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `promoted_by` | `Optional[str]` | No | *(Not documented)* |
  | `notes` | `Optional[str]` | No | *(Not documented)* |
  | `created_at` | `datetime` | Yes | *(Not documented)* |
  | `updated_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_baselines_scans_incidents.py::test_project_baselines_versioning_and_promotion`
- ✅ `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`

---

### <a id="post-projectsproject_idbaselinesbaseline_idpromote"></a>`POST /projects/{project_id}/baselines/{baseline_id}/promote`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/baselines.py:96)  
> **Handler:** `promote_project_baseline` | **Source Location:** `app/routers/baselines.py:96`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `project_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |
| `baseline_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |
| `promoted_by` | `query` | `Optional[str]` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
*No request body expected.*

#### Responses
- **HTTP 200** (`ProjectBaselineResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `project_id` | `str` | Yes | *(Not documented)* |
  | `version` | `int` | No | *(Not documented)* |
  | `version_tag` | `Optional[str]` | No | *(Not documented)* |
  | `contracts` | `Dict[Any]` | No | *(Not documented)* |
  | `inventory` | `Dict[Any]` | No | *(Not documented)* |
  | `source_scan_id` | `Optional[str]` | No | *(Not documented)* |
  | `content_hash` | `Optional[str]` | No | *(Not documented)* |
  | `created_by` | `Optional[str]` | No | *(Not documented)* |
  | `is_active` | `bool` | Yes | *(Not documented)* |
  | `is_promoted` | `bool` | Yes | *(Not documented)* |
  | `promoted_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `promoted_by` | `Optional[str]` | No | *(Not documented)* |
  | `notes` | `Optional[str]` | No | *(Not documented)* |
  | `created_at` | `datetime` | Yes | *(Not documented)* |
  | `updated_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_baselines_scans_incidents.py::test_project_baselines_versioning_and_promotion`

---

### <a id="post-projectsproject_iddependencies"></a>`POST /projects/{project_id}/dependencies`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/dependencies.py:23)  
> **Handler:** `create_dependency` | **Source Location:** `app/routers/dependencies.py:23`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `project_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `DependencyCreate` (Required)

*Request body schema defines no specific properties.*

#### Responses
- **HTTP 201** (`DependencyResponse`): Successful response (201)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `project_id` | `str` | Yes | *(Not documented)* |
  | `name` | `str` | Yes | *(Not documented)* |
  | `kind` | `str` | Yes | *(Not documented)* |
  | `base_url` | `Optional[str]` | No | *(Not documented)* |
  | `version` | `Optional[str]` | No | *(Not documented)* |
  | `configuration` | `Dict[Any]` | No | *(Not documented)* |
  | `created_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_query_filters_and_pagination.py::test_incident_filters_and_pagination`
- ✅ `tests/test_query_filters_and_pagination.py::test_dependency_patch_update`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`
- ✅ `tests/test_repairs_lifecycle.py::test_project_activity_and_dashboard_summary`
- ✅ `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`
- ✅ `tests/test_first_vertical_slice.py::test_fingerprint_deduplication`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_apply_unapproved_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_reapprove_or_reject_already_decided_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_invalid_incident_lifecycle_transition`
- ✅ `tests/test_contract_examples.py::test_compatibility_with_shared_contract_examples`

---

### <a id="post-projectsproject_idincidents"></a>`POST /projects/{project_id}/incidents`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/incidents.py:49)  
> **Handler:** `create_incident` | **Source Location:** `app/routers/incidents.py:49`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `project_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `IncidentCreate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `dependency_id` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `title` | `str` | No | *None* | min_length=1 | *(Not documented)* |
| `description` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `change_type` | `str` | No | `unknown` | *None* | *(Not documented)* |
| `severity` | `str` | No | `medium` | pattern=^(low|medium|high|critical|blocked)$ | *(Not documented)* |
| `provenance` | `Optional[str]` | No | `contract_diff` | *None* | *(Not documented)* |
| `confidence` | `Optional[float]` | No | *None* | ge=0.0, le=1.0 | *(Not documented)* |
| `fingerprint` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `recommended_action` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `observation_ids` | `Optional[List[str]]` | No | *None* | *None* | *(Not documented)* |
| `affected_workflows` | `Optional[List[str]]` | No | *None* | *None* | *(Not documented)* |
| `affected_files` | `Optional[List[str]]` | No | *None* | *None* | *(Not documented)* |
| `evidence` | `Optional[Dict[Any]]` | No | *None* | *None* | *(Not documented)* |

#### Responses
- **HTTP 201** (`IncidentResponse`): Successful response (201)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `project_id` | `str` | Yes | *(Not documented)* |
  | `dependency_id` | `Optional[str]` | No | *(Not documented)* |
  | `title` | `str` | Yes | *(Not documented)* |
  | `description` | `Optional[str]` | No | *(Not documented)* |
  | `change_type` | `str` | Yes | *(Not documented)* |
  | `severity` | `str` | Yes | *(Not documented)* |
  | `status` | `str` | Yes | *(Not documented)* |
  | `provenance` | `str` | No | *(Not documented)* |
  | `confidence` | `Optional[float]` | No | *(Not documented)* |
  | `occurrence_count` | `int` | No | *(Not documented)* |
  | `fingerprint` | `Optional[str]` | No | *(Not documented)* |
  | `recommended_action` | `Optional[str]` | No | *(Not documented)* |
  | `resolution_notes` | `Optional[str]` | No | *(Not documented)* |
  | `review_notes` | `Optional[str]` | No | *(Not documented)* |
  | `assignee_id` | `Optional[str]` | No | *(Not documented)* |
  | `affected_workflows` | `List[str]` | No | *(Not documented)* |
  | `affected_files` | `List[str]` | No | *(Not documented)* |
  | `evidence_summary` | `Optional[str]` | No | *(Not documented)* |
  | `first_detected_at` | `datetime` | Yes | *(Not documented)* |
  | `last_observed_at` | `datetime` | Yes | *(Not documented)* |
  | `acknowledged_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `acknowledged_by` | `Optional[str]` | No | *(Not documented)* |
  | `resolved_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `reopened_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `created_at` | `datetime` | Yes | *(Not documented)* |
  | `updated_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_query_filters_and_pagination.py::test_incident_filters_and_pagination`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`
- ✅ `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`
- ✅ `tests/test_repairs_lifecycle.py::test_project_activity_and_dashboard_summary`
- ✅ `tests/test_baselines_scans_incidents.py::test_scan_ingest_idempotency`
- ✅ `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence`
- ✅ `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`
- ✅ `tests/test_first_vertical_slice.py::test_fingerprint_deduplication`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_apply_unapproved_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_reapprove_or_reject_already_decided_repair`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_invalid_incident_lifecycle_transition`
- ✅ `tests/test_contract_examples.py::test_compatibility_with_shared_contract_examples`

---

### <a id="post-projectsproject_idmembers"></a>`POST /projects/{project_id}/members`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/projects.py:58)  
> **Handler:** `add_member` | **Source Location:** `app/routers/projects.py:58`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `project_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `ProjectMemberCreate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `user_id` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |
| `role` | `str` | No | `developer` | pattern=^(owner|admin|developer|reviewer)$ | *(Not documented)* |
| `display_name` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `email` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |

#### Responses
- **HTTP 201** (`ProjectMemberResponse`): Successful response (201)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `project_id` | `str` | Yes | *(Not documented)* |
  | `user_id` | `str` | Yes | *(Not documented)* |
  | `role` | `str` | Yes | *(Not documented)* |
  | `display_name` | `Optional[str]` | No | *(Not documented)* |
  | `email` | `Optional[str]` | No | *(Not documented)* |
  | `joined_at` | `datetime` | Yes | *(Not documented)* |

#### Error Cases & Side Effects
**Side Effects:**
- `database_write` on `Database`: Persists changes or updates entity in database transaction

#### Verified Test Coverage
- ✅ `tests/test_repairs_lifecycle.py::test_project_activity_and_dashboard_summary`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_duplicate_project_member_error`

---

### <a id="post-projectsproject_idscans"></a>`POST /projects/{project_id}/scans`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/scans.py:38)  
> **Handler:** `start_scan` | **Source Location:** `app/routers/scans.py:38`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `project_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `ScanCreate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `dependency_id` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `initiated_by` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `scan_type` | `str` | No | `full` | pattern=^(full|targeted|codebase|contract_drift|live_probe)$ | *(Not documented)* |
| `detection_mode` | `Optional[str]` | No | `algorithmic` | pattern=^(algorithmic|hybrid|ai)$ | *(Not documented)* |
| `trigger_type` | `Optional[str]` | No | `manual` | *None* | *(Not documented)* |

#### Responses
- **HTTP 200** (`ScanRunResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `project_id` | `str` | Yes | *(Not documented)* |
  | `dependency_id` | `Optional[str]` | No | *(Not documented)* |
  | `initiated_by` | `Optional[str]` | No | *(Not documented)* |
  | `scan_type` | `str` | No | *(Not documented)* |
  | `detection_mode` | `Optional[str]` | No | *(Not documented)* |
  | `capabilities_executed` | `List[str]` | No | *(Not documented)* |
  | `status` | `str` | Yes | *(Not documented)* |
  | `duration_seconds` | `Optional[float]` | No | *(Not documented)* |
  | `summary_counts` | `Dict[Any]` | No | *(Not documented)* |
  | `summary` | `Optional[str]` | No | *(Not documented)* |
  | `error_message` | `Optional[str]` | No | *(Not documented)* |
  | `is_local` | `bool` | No | *(Not documented)* |
  | `sync_status` | `str` | No | *(Not documented)* |
  | `client_run_id` | `Optional[str]` | No | *(Not documented)* |
  | `started_at` | `datetime` | Yes | *(Not documented)* |
  | `completed_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `created_at` | `Optional[datetime]` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_baselines_scans_incidents.py::test_scan_ingest_idempotency`
- ✅ `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence`
- ✅ `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`
- ✅ `tests/test_first_vertical_slice.py::test_fingerprint_deduplication`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`

---

### <a id="post-projectsproject_idscansingest"></a>`POST /projects/{project_id}/scans/ingest`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/scans.py:50)  
> **Handler:** `ingest_scan` | **Source Location:** `app/routers/scans.py:50`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `project_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `ScanIngestRequest` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `client_run_id` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `scan_type` | `str` | No | `full` | *None* | *(Not documented)* |
| `detection_mode` | `str` | No | `algorithmic` | pattern=^(algorithmic|hybrid|ai)$ | *(Not documented)* |
| `capabilities_executed` | `List[str]` | No | *None* | *None* | *(Not documented)* |
| `duration_seconds` | `Optional[float]` | No | *None* | *None* | *(Not documented)* |
| `summary_counts` | `Dict[Any]` | No | *None* | *None* | *(Not documented)* |
| `findings` | `List[Dict[Any]]` | No | *None* | *None* | *(Not documented)* |
| `inventory` | `Optional[Dict[Any]]` | No | *None* | *None* | *(Not documented)* |
| `status` | `str` | No | `succeeded` | pattern=^(succeeded|partial|failed|canceled)$ | *(Not documented)* |
| `error_message` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `scanner_version` | `Optional[str]` | No | `0.2.0` | *None* | *(Not documented)* |
| `repository_revision` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `initiated_by` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `started_at` | `Optional[datetime]` | No | *None* | *None* | *(Not documented)* |
| `completed_at` | `Optional[datetime]` | No | *None* | *None* | *(Not documented)* |

#### Responses
- **HTTP 201** (`ScanRunResponse`): Successful response (201)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `project_id` | `str` | Yes | *(Not documented)* |
  | `dependency_id` | `Optional[str]` | No | *(Not documented)* |
  | `initiated_by` | `Optional[str]` | No | *(Not documented)* |
  | `scan_type` | `str` | No | *(Not documented)* |
  | `detection_mode` | `Optional[str]` | No | *(Not documented)* |
  | `capabilities_executed` | `List[str]` | No | *(Not documented)* |
  | `status` | `str` | Yes | *(Not documented)* |
  | `duration_seconds` | `Optional[float]` | No | *(Not documented)* |
  | `summary_counts` | `Dict[Any]` | No | *(Not documented)* |
  | `summary` | `Optional[str]` | No | *(Not documented)* |
  | `error_message` | `Optional[str]` | No | *(Not documented)* |
  | `is_local` | `bool` | No | *(Not documented)* |
  | `sync_status` | `str` | No | *(Not documented)* |
  | `client_run_id` | `Optional[str]` | No | *(Not documented)* |
  | `started_at` | `datetime` | Yes | *(Not documented)* |
  | `completed_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `created_at` | `Optional[datetime]` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_baselines_scans_incidents.py::test_scan_ingest_idempotency`
- ✅ `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence`

---

### <a id="post-repair-proposalsrepair_idapplications"></a>`POST /repair-proposals/{repair_id}/applications`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/repairs.py:62)  
> **Handler:** `record_repair_application` | **Source Location:** `app/routers/repairs.py:62`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `repair_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `RepairApplicationCreate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `agent_id` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `status` | `str` | No | *None* | pattern=^(applied|failed|cancelled)$ | *(Not documented)* |
| `workspace_reference` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `message` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |

#### Responses
- **HTTP 201** (`RepairApplicationResponse`): Successful response (201)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `repair_id` | `str` | Yes | *(Not documented)* |
  | `agent_id` | `Optional[str]` | No | *(Not documented)* |
  | `status` | `str` | Yes | *(Not documented)* |
  | `workspace_reference` | `Optional[str]` | No | *(Not documented)* |
  | `message` | `Optional[str]` | No | *(Not documented)* |
  | `reported_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_apply_unapproved_repair`

---

### <a id="post-repair-proposalsrepair_idapprovals"></a>`POST /repair-proposals/{repair_id}/approvals`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/repairs.py:47)  
> **Handler:** `approve_repair` | **Source Location:** `app/routers/repairs.py:47`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `repair_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `RepairApprovalCreate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `reviewer_id` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |
| `decision` | `str` | No | `approved` | pattern=^(approved)$ | *(Not documented)* |
| `comment` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |

#### Responses
- **HTTP 201** (`RepairApprovalResponse`): Successful response (201)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `repair_id` | `str` | Yes | *(Not documented)* |
  | `reviewer_id` | `str` | Yes | *(Not documented)* |
  | `decision` | `str` | Yes | *(Not documented)* |
  | `comment` | `Optional[str]` | No | *(Not documented)* |
  | `decided_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_reapprove_or_reject_already_decided_repair`

---

### <a id="post-repair-proposalsrepair_idrejection"></a>`POST /repair-proposals/{repair_id}/rejection`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/repairs.py:54)  
> **Handler:** `reject_repair` | **Source Location:** `app/routers/repairs.py:54`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `repair_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `RepairRejectionCreate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `reviewer_id` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |
| `reason` | `str` | No | *None* | min_length=1 | *(Not documented)* |

#### Responses
- **HTTP 200** (`RepairProposalResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `incident_id` | `str` | Yes | *(Not documented)* |
  | `status` | `str` | Yes | *(Not documented)* |
  | `rationale` | `str` | Yes | *(Not documented)* |
  | `strategy` | `str` | Yes | *(Not documented)* |
  | `diff_preview` | `Optional[str]` | No | *(Not documented)* |
  | `proposed_changes` | `Dict[Any]` | No | *(Not documented)* |
  | `confidence` | `Optional[float]` | No | *(Not documented)* |
  | `created_by` | `Optional[str]` | No | *(Not documented)* |
  | `created_at` | `datetime` | Yes | *(Not documented)* |
  | `updated_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`
- ✅ `tests/test_invalid_transitions_and_errors.py::test_cannot_reapprove_or_reject_already_decided_repair`

---

### <a id="post-repair-proposalsrepair_idvalidation-runs"></a>`POST /repair-proposals/{repair_id}/validation-runs`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/repairs.py:39)  
> **Handler:** `create_validation_run` | **Source Location:** `app/routers/repairs.py:39`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `repair_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `ValidationRunCreate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `status` | `Optional[str]` | No | `passed` | pattern=^(queued|running|passed|failed|blocked|error)$ | *(Not documented)* |
| `test_command` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `output` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `details` | `Optional[Dict[Any]]` | No | *None* | *None* | *(Not documented)* |
| `started_at` | `Optional[datetime]` | No | *None* | *None* | *(Not documented)* |
| `completed_at` | `Optional[datetime]` | No | *None* | *None* | *(Not documented)* |
| `result` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `summary` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |

#### Responses
- **HTTP 201** (`ValidationRunResponse`): Successful response (201)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `repair_id` | `str` | Yes | *(Not documented)* |
  | `status` | `str` | Yes | *(Not documented)* |
  | `test_command` | `Optional[str]` | No | *(Not documented)* |
  | `output` | `Optional[str]` | No | *(Not documented)* |
  | `details` | `Dict[Any]` | No | *(Not documented)* |
  | `started_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `completed_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `created_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`

---

### <a id="post-repairsrepair_idapply-result"></a>`POST /repairs/{repair_id}/apply-result`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/repairs.py:62)  
> **Handler:** `record_repair_application` | **Source Location:** `app/routers/repairs.py:62`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `repair_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `RepairApplicationCreate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `agent_id` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `status` | `str` | No | *None* | pattern=^(applied|failed|cancelled)$ | *(Not documented)* |
| `workspace_reference` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `message` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |

#### Responses
- **HTTP 201** (`RepairApplicationResponse`): Successful response (201)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `repair_id` | `str` | Yes | *(Not documented)* |
  | `agent_id` | `Optional[str]` | No | *(Not documented)* |
  | `status` | `str` | Yes | *(Not documented)* |
  | `workspace_reference` | `Optional[str]` | No | *(Not documented)* |
  | `message` | `Optional[str]` | No | *(Not documented)* |
  | `reported_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ⚠️ *No automated tests found covering this route (Coverage Gap).*

---

### <a id="post-repairsrepair_idapprove"></a>`POST /repairs/{repair_id}/approve`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/repairs.py:47)  
> **Handler:** `approve_repair` | **Source Location:** `app/routers/repairs.py:47`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `repair_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `RepairApprovalCreate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `reviewer_id` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |
| `decision` | `str` | No | `approved` | pattern=^(approved)$ | *(Not documented)* |
| `comment` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |

#### Responses
- **HTTP 201** (`RepairApprovalResponse`): Successful response (201)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `repair_id` | `str` | Yes | *(Not documented)* |
  | `reviewer_id` | `str` | Yes | *(Not documented)* |
  | `decision` | `str` | Yes | *(Not documented)* |
  | `comment` | `Optional[str]` | No | *(Not documented)* |
  | `decided_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`

---

### <a id="post-repairsrepair_idvalidate"></a>`POST /repairs/{repair_id}/validate`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/repairs.py:39)  
> **Handler:** `create_validation_run` | **Source Location:** `app/routers/repairs.py:39`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `repair_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `ValidationRunCreate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `status` | `Optional[str]` | No | `passed` | pattern=^(queued|running|passed|failed|blocked|error)$ | *(Not documented)* |
| `test_command` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `output` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `details` | `Optional[Dict[Any]]` | No | *None* | *None* | *(Not documented)* |
| `started_at` | `Optional[datetime]` | No | *None* | *None* | *(Not documented)* |
| `completed_at` | `Optional[datetime]` | No | *None* | *None* | *(Not documented)* |
| `result` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `summary` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |

#### Responses
- **HTTP 201** (`ValidationRunResponse`): Successful response (201)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `repair_id` | `str` | Yes | *(Not documented)* |
  | `status` | `str` | Yes | *(Not documented)* |
  | `test_command` | `Optional[str]` | No | *(Not documented)* |
  | `output` | `Optional[str]` | No | *(Not documented)* |
  | `details` | `Dict[Any]` | No | *(Not documented)* |
  | `started_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `completed_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `created_at` | `datetime` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_contract_examples.py::test_compatibility_with_shared_contract_examples`

---

### <a id="post-scansscan_idcomplete"></a>`POST /scans/{scan_id}/complete`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/scans.py:85)  
> **Handler:** `complete_scan` | **Source Location:** `app/routers/scans.py:85`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `scan_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `ScanCompleteRequest` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `status` | `str` | No | *None* | pattern=^(succeeded|partial|failed|canceled|completed)$ | *(Not documented)* |
| `summary` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `error_message` | `Optional[str]` | No | *None* | *None* | *(Not documented)* |
| `duration_seconds` | `Optional[float]` | No | *None* | *None* | *(Not documented)* |
| `summary_counts` | `Optional[Dict[Any]]` | No | *None* | *None* | *(Not documented)* |

#### Responses
- **HTTP 200** (`ScanRunResponse`): Successful response (200)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `id` | `str` | Yes | *(Not documented)* |
  | `project_id` | `str` | Yes | *(Not documented)* |
  | `dependency_id` | `Optional[str]` | No | *(Not documented)* |
  | `initiated_by` | `Optional[str]` | No | *(Not documented)* |
  | `scan_type` | `str` | No | *(Not documented)* |
  | `detection_mode` | `Optional[str]` | No | *(Not documented)* |
  | `capabilities_executed` | `List[str]` | No | *(Not documented)* |
  | `status` | `str` | Yes | *(Not documented)* |
  | `duration_seconds` | `Optional[float]` | No | *(Not documented)* |
  | `summary_counts` | `Dict[Any]` | No | *(Not documented)* |
  | `summary` | `Optional[str]` | No | *(Not documented)* |
  | `error_message` | `Optional[str]` | No | *(Not documented)* |
  | `is_local` | `bool` | No | *(Not documented)* |
  | `sync_status` | `str` | No | *(Not documented)* |
  | `client_run_id` | `Optional[str]` | No | *(Not documented)* |
  | `started_at` | `datetime` | Yes | *(Not documented)* |
  | `completed_at` | `Optional[datetime]` | No | *(Not documented)* |
  | `created_at` | `Optional[datetime]` | No | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`

---

### <a id="post-scansscan_idobservations"></a>`POST /scans/{scan_id}/observations`


> [!NOTE]
> **Discovery Method:** `framework_ast` | **Evidence:** source_ast:fastapi_router (app/routers/scans.py:72)  
> **Handler:** `submit_observations` | **Source Location:** `app/routers/scans.py:72`  
> **Confidence Level:** `100%` | **Inferred:** `No`

🔒 **Authentication & Authorization:** Security: Depends(get_db)

#### Parameters
| Name | Location | Type | Required | Default | Constraints | Description |
|---|---|---|:---:|---|---|---|
| `scan_id` | `path` | `str` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Request Body
**Content-Type:** `application/json` | **Schema:** `ObservationBatchCreate` (Required)

| Field | Type | Required | Default | Constraints | Description |
|---|---|:---:|---|---|---|
| `observations` | `List[ObservationCreate]` | ✅ Yes | *None* | *None* | *(Not documented)* |

#### Responses
- **HTTP 201** (`ObservationBatchResponse`): Successful response (201)
  | Response Field | Type | Required | Description |
  |---|---|:---:|---|
  | `accepted_count` | `int` | Yes | *(Not documented)* |
  | `observation_ids` | `List[str]` | Yes | *(Not documented)* |

#### Verified Test Coverage
- ✅ `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`
- ✅ `tests/test_first_vertical_slice.py::test_fingerprint_deduplication`

---
