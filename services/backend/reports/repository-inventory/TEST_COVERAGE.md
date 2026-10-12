# Dependency Guardian — API Test Coverage Report

Comprehensive test coverage verification across discovered API routes and integrations.

## 1. Executive Coverage Metrics

| Metric | Value | Status |
|---|---|---|
| **Total Discovered Endpoints** | 51 | 100% of discovered routes |
| **Endpoints with Automated Tests** | 50 | Verified by test suite |
| **Endpoints with No Tests (Gaps)** | 1 | Need test implementation |
| **API Endpoint Test Coverage** | **98.0%** | 🟢 Good |
| **Integration Tests Found** | 4 | Integration/external tests |

---

## 2. Endpoint Test Coverage Matrix

| Method | Route Path | Source Location | Discovered Test(s) | Coverage State |
|---|---|---|---|:---:|
| `GET` | `/baselines/{baseline_id}` | `app/routers/baselines.py:158` | • `tests/test_baselines_scans_incidents.py::test_project_baselines_versioning_and_promotion`<br>• `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`<br>• `tests/test_invalid_transitions_and_errors.py::test_not_found_errors` | ✅ Covered |
| `GET` | `/dependencies/{dependency_id}` | `app/routers/dependencies.py:30` | • `tests/test_query_filters_and_pagination.py::test_incident_filters_and_pagination`<br>• `tests/test_query_filters_and_pagination.py::test_dependency_patch_update`<br>• `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`<br>*...and 9 more.* | ✅ Covered |
| `GET` | `/dependencies/{dependency_id}/baselines` | `app/routers/baselines.py:116` | • `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`<br>• `tests/test_invalid_transitions_and_errors.py::test_not_found_errors` | ✅ Covered |
| `GET` | `/health` | `app/routers/health.py:8` | • `tests/test_health.py::test_health_root`<br>• `tests/test_health.py::test_health_api_prefix` | ✅ Covered |
| `GET` | `/incidents/{incident_id}` | `app/routers/incidents.py:56` | • `tests/test_query_filters_and_pagination.py::test_incident_filters_and_pagination`<br>• `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`<br>• `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`<br>*...and 10 more.* | ✅ Covered |
| `GET` | `/incidents/{incident_id}/events` | `app/routers/incidents.py:109` | • `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence` | ✅ Covered |
| `GET` | `/incidents/{incident_id}/observations` | `app/routers/incidents.py:116` | • `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`<br>• `tests/test_first_vertical_slice.py::test_fingerprint_deduplication` | ✅ Covered |
| `GET` | `/incidents/{incident_id}/repair-proposals` | `app/routers/incidents.py:125` | • `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`<br>• `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`<br>• `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`<br>*...and 2 more.* | ✅ Covered |
| `GET` | `/incidents/{incident_id}/repairs` | `app/routers/incidents.py:125` | • `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`<br>• `tests/test_contract_examples.py::test_compatibility_with_shared_contract_examples` | ✅ Covered |
| `GET` | `/projects` | `app/routers/projects.py:21` | • `tests/test_query_filters_and_pagination.py::test_incident_filters_and_pagination`<br>• `tests/test_query_filters_and_pagination.py::test_dependency_patch_update`<br>• `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`<br>*...and 13 more.* | ✅ Covered |
| `GET` | `/projects/{project_id}` | `app/routers/projects.py:44` | • `tests/test_query_filters_and_pagination.py::test_incident_filters_and_pagination`<br>• `tests/test_query_filters_and_pagination.py::test_dependency_patch_update`<br>• `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`<br>*...and 13 more.* | ✅ Covered |
| `GET` | `/projects/{project_id}/activity` | `app/routers/projects.py:65` | • `tests/test_repairs_lifecycle.py::test_project_activity_and_dashboard_summary` | ✅ Covered |
| `GET` | `/projects/{project_id}/baselines` | `app/routers/baselines.py:27` | • `tests/test_baselines_scans_incidents.py::test_project_baselines_versioning_and_promotion`<br>• `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`<br>• `tests/test_invalid_transitions_and_errors.py::test_not_found_errors` | ✅ Covered |
| `GET` | `/projects/{project_id}/baselines/active` | `app/routers/baselines.py:57` | • `tests/test_baselines_scans_incidents.py::test_project_baselines_versioning_and_promotion` | ✅ Covered |
| `GET` | `/projects/{project_id}/baselines/compare` | `app/routers/baselines.py:70` | • `tests/test_baselines_scans_incidents.py::test_project_baselines_versioning_and_promotion` | ✅ Covered |
| `GET` | `/projects/{project_id}/baselines/{baseline_id}` | `app/routers/baselines.py:85` | • `tests/test_baselines_scans_incidents.py::test_project_baselines_versioning_and_promotion`<br>• `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`<br>• `tests/test_invalid_transitions_and_errors.py::test_not_found_errors` | ✅ Covered |
| `GET` | `/projects/{project_id}/dependencies` | `app/routers/dependencies.py:16` | • `tests/test_query_filters_and_pagination.py::test_incident_filters_and_pagination`<br>• `tests/test_query_filters_and_pagination.py::test_dependency_patch_update`<br>• `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`<br>*...and 9 more.* | ✅ Covered |
| `GET` | `/projects/{project_id}/incidents` | `app/routers/incidents.py:22` | • `tests/test_query_filters_and_pagination.py::test_incident_filters_and_pagination`<br>• `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`<br>• `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`<br>*...and 10 more.* | ✅ Covered |
| `GET` | `/projects/{project_id}/members` | `app/routers/projects.py:51` | • `tests/test_repairs_lifecycle.py::test_project_activity_and_dashboard_summary`<br>• `tests/test_invalid_transitions_and_errors.py::test_duplicate_project_member_error` | ✅ Covered |
| `GET` | `/projects/{project_id}/scans` | `app/routers/scans.py:22` | • `tests/test_baselines_scans_incidents.py::test_scan_ingest_idempotency`<br>• `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence`<br>• `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`<br>*...and 2 more.* | ✅ Covered |
| `GET` | `/projects/{project_id}/summary` | `app/routers/projects.py:82` | • `tests/test_repairs_lifecycle.py::test_project_activity_and_dashboard_summary`<br>• `tests/test_baselines_scans_incidents.py::test_project_baselines_versioning_and_promotion`<br>• `tests/test_baselines_scans_incidents.py::test_scan_ingest_idempotency`<br>*...and 3 more.* | ✅ Covered |
| `GET` | `/repair-proposals/{repair_id}` | `app/routers/repairs.py:23` | • `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`<br>• `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`<br>• `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`<br>*...and 2 more.* | ✅ Covered |
| `GET` | `/repair-proposals/{repair_id}/validation-runs` | `app/routers/repairs.py:31` | • `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end` | ✅ Covered |
| `GET` | `/repairs/{repair_id}` | `app/routers/repairs.py:23` | • `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`<br>• `tests/test_contract_examples.py::test_compatibility_with_shared_contract_examples` | ✅ Covered |
| `GET` | `/repairs/{repair_id}/validation-runs` | `app/routers/repairs.py:31` | • `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end` | ✅ Covered |
| `GET` | `/scans/{scan_id}` | `app/routers/scans.py:59` | • `tests/test_baselines_scans_incidents.py::test_scan_ingest_idempotency`<br>• `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence`<br>• `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`<br>*...and 2 more.* | ✅ Covered |
| `PATCH` | `/dependencies/{dependency_id}` | `app/routers/dependencies.py:37` | • `tests/test_query_filters_and_pagination.py::test_incident_filters_and_pagination`<br>• `tests/test_query_filters_and_pagination.py::test_dependency_patch_update`<br>• `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`<br>*...and 9 more.* | ✅ Covered |
| `PATCH` | `/incidents/{incident_id}` | `app/routers/incidents.py:63` | • `tests/test_query_filters_and_pagination.py::test_incident_filters_and_pagination`<br>• `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`<br>• `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`<br>*...and 10 more.* | ✅ Covered |
| `POST` | `/dependencies/{dependency_id}/baselines` | `app/routers/baselines.py:139` | • `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`<br>• `tests/test_invalid_transitions_and_errors.py::test_not_found_errors` | ✅ Covered |
| `POST` | `/incidents/{incident_id}/acknowledge` | `app/routers/incidents.py:70` | • `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence` | ✅ Covered |
| `POST` | `/incidents/{incident_id}/reopen` | `app/routers/incidents.py:96` | • `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence`<br>• `tests/test_invalid_transitions_and_errors.py::test_invalid_incident_lifecycle_transition` | ✅ Covered |
| `POST` | `/incidents/{incident_id}/repair-proposals` | `app/routers/incidents.py:133` | • `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`<br>• `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`<br>• `tests/test_invalid_transitions_and_errors.py::test_not_found_errors`<br>*...and 2 more.* | ✅ Covered |
| `POST` | `/incidents/{incident_id}/repairs` | `app/routers/incidents.py:133` | • `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`<br>• `tests/test_contract_examples.py::test_compatibility_with_shared_contract_examples` | ✅ Covered |
| `POST` | `/incidents/{incident_id}/resolve` | `app/routers/incidents.py:83` | • `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`<br>• `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`<br>• `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence`<br>*...and 1 more.* | ✅ Covered |
| `POST` | `/projects` | `app/routers/projects.py:37` | • `tests/test_query_filters_and_pagination.py::test_incident_filters_and_pagination`<br>• `tests/test_query_filters_and_pagination.py::test_dependency_patch_update`<br>• `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`<br>*...and 13 more.* | ✅ Covered |
| `POST` | `/projects/{project_id}/baselines` | `app/routers/baselines.py:44` | • `tests/test_baselines_scans_incidents.py::test_project_baselines_versioning_and_promotion`<br>• `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`<br>• `tests/test_invalid_transitions_and_errors.py::test_not_found_errors` | ✅ Covered |
| `POST` | `/projects/{project_id}/baselines/{baseline_id}/promote` | `app/routers/baselines.py:96` | • `tests/test_baselines_scans_incidents.py::test_project_baselines_versioning_and_promotion` | ✅ Covered |
| `POST` | `/projects/{project_id}/dependencies` | `app/routers/dependencies.py:23` | • `tests/test_query_filters_and_pagination.py::test_incident_filters_and_pagination`<br>• `tests/test_query_filters_and_pagination.py::test_dependency_patch_update`<br>• `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`<br>*...and 9 more.* | ✅ Covered |
| `POST` | `/projects/{project_id}/incidents` | `app/routers/incidents.py:49` | • `tests/test_query_filters_and_pagination.py::test_incident_filters_and_pagination`<br>• `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`<br>• `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`<br>*...and 10 more.* | ✅ Covered |
| `POST` | `/projects/{project_id}/members` | `app/routers/projects.py:58` | • `tests/test_repairs_lifecycle.py::test_project_activity_and_dashboard_summary`<br>• `tests/test_invalid_transitions_and_errors.py::test_duplicate_project_member_error` | ✅ Covered |
| `POST` | `/projects/{project_id}/scans` | `app/routers/scans.py:38` | • `tests/test_baselines_scans_incidents.py::test_scan_ingest_idempotency`<br>• `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence`<br>• `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`<br>*...and 2 more.* | ✅ Covered |
| `POST` | `/projects/{project_id}/scans/ingest` | `app/routers/scans.py:50` | • `tests/test_baselines_scans_incidents.py::test_scan_ingest_idempotency`<br>• `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence` | ✅ Covered |
| `POST` | `/repair-proposals/{repair_id}/applications` | `app/routers/repairs.py:62` | • `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`<br>• `tests/test_invalid_transitions_and_errors.py::test_cannot_apply_unapproved_repair` | ✅ Covered |
| `POST` | `/repair-proposals/{repair_id}/approvals` | `app/routers/repairs.py:47` | • `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`<br>• `tests/test_invalid_transitions_and_errors.py::test_cannot_reapprove_or_reject_already_decided_repair` | ✅ Covered |
| `POST` | `/repair-proposals/{repair_id}/rejection` | `app/routers/repairs.py:54` | • `tests/test_repairs_lifecycle.py::test_repair_rejection_flow`<br>• `tests/test_invalid_transitions_and_errors.py::test_cannot_reapprove_or_reject_already_decided_repair` | ✅ Covered |
| `POST` | `/repair-proposals/{repair_id}/validation-runs` | `app/routers/repairs.py:39` | • `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end` | ✅ Covered |
| `POST` | `/repairs/{repair_id}/apply-result` | `app/routers/repairs.py:62` | *None* | ❌ **Coverage Gap** |
| `POST` | `/repairs/{repair_id}/approve` | `app/routers/repairs.py:47` | • `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end` | ✅ Covered |
| `POST` | `/repairs/{repair_id}/validate` | `app/routers/repairs.py:39` | • `tests/test_contract_examples.py::test_compatibility_with_shared_contract_examples` | ✅ Covered |
| `POST` | `/scans/{scan_id}/complete` | `app/routers/scans.py:85` | • `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice` | ✅ Covered |
| `POST` | `/scans/{scan_id}/observations` | `app/routers/scans.py:72` | • `tests/test_first_vertical_slice.py::test_end_to_end_first_vertical_slice`<br>• `tests/test_first_vertical_slice.py::test_fingerprint_deduplication` | ✅ Covered |

---

## 3. Discovered Integration Tests

- 🧪 `tests/test_repairs_lifecycle.py::test_repair_lifecycle_end_to_end`
- 🧪 `tests/test_baselines_scans_incidents.py::test_project_baselines_versioning_and_promotion`
- 🧪 `tests/test_baselines_scans_incidents.py::test_scan_ingest_idempotency`
- 🧪 `tests/test_baselines_scans_incidents.py::test_incident_lifecycle_and_reopen_on_recurrence`

---

## 4. Identified Test Gaps and Remediation Recommendations

The following endpoints currently lack automated test coverage:

- ⚠️ **`POST /repairs/{repair_id}/apply-result`** (app/routers/repairs.py) — Missing functional regression tests.

### Recommendations:
1. Generate automated regression tests using `dependency-guardian --generate-tests`.
2. Add positive tests asserting happy-path response status codes.
3. Add negative tests validating error cases and input validation rules.
