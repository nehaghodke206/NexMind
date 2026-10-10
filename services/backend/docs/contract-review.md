# Contract & Database Design Review

This document records the cross-check between the shared API contracts (`contracts/api-contract.md`, `docs/open-api.yaml`), the database design (`docs/database-design.mmd`), and the implementation requirements.

---

## 1. Identified Discrepancies & Resolutions

### Discrepancy 1: Primary Key Types (Integer vs. UUID)
- **Database Design (`database-design.mmd`)**:
  Declares all primary and foreign keys as integers (`int id PK`, `int project_id FK`, etc.).
- **OpenAPI Contract (`open-api.yaml`)**:
  Specifies string IDs formatted as UUIDs (`type: string, format: uuid`) for `ProjectId`, `DependencyId`, `BaselineId`, `ScanId`, `IncidentId`, `RepairId`, `UserId`, etc.
- **Contract Example (`contracts/examples/incident.json`)**:
  Uses string identifiers such as `"dep_demo_users"`.
- **Resolution**:
  Use UUID-compatible string keys (`String(36)` / `UUID`) with automated UUID v4 generation as default primary keys in database models and schemas. This guarantees full compatibility with OpenAPI schemas and client contracts while supporting isolated testing in SQLite and deployment in PostgreSQL.

---

### Discrepancy 2: Incident Status Enum Values
- **API Contract Outline (`contracts/api-contract.md`)**:
  Suggests incident states: `detected`, `analyzing`, `repair_proposed`, `validating`, `validation_failed`, `ready_for_review`, `approved`, `resolved`, `blocked`.
- **Authoritative OpenAPI Specification (`docs/open-api.yaml`)**:
  Defines `IncidentStatus` enum: `open`, `triaged`, `in_progress`, `awaiting_review`, `resolved`, `dismissed`.
- **Database Design (`database-design.mmd`)**:
  Declares `string status` without an explicit enum constraint.
- **Resolution**:
  Standardize on OpenAPI's authoritative `IncidentStatus` (`open`, `triaged`, `in_progress`, `awaiting_review`, `resolved`, `dismissed`). Provide graceful mapping/aliasing where appropriate if legacy status values are submitted.

---

### Discrepancy 3: Repair Proposal Lifecycle & Endpoints
- **API Contract Outline (`contracts/api-contract.md`)**:
  Proposes endpoints under `/incidents/{incident_id}/repairs`, `/repairs/{repair_id}`, `/repairs/{repair_id}/validate`, `/repairs/{repair_id}/approve`, `/repairs/{repair_id}/apply-result`. Status values: `proposed`, `validating`, `validation_passed`, `validation_failed`, `approved`, `rejected`, `applied`.
- **OpenAPI Specification (`docs/open-api.yaml`)**:
  Specifies `/incidents/{incident_id}/repair-proposals`, `/repair-proposals/{repair_id}`, `/repair-proposals/{repair_id}/validation-runs`, `/repair-proposals/{repair_id}/approvals`, `/repair-proposals/{repair_id}/rejection`, `/repair-proposals/{repair_id}/applications`. Status values: `proposed`, `validating`, `ready_for_review`, `approved`, `rejected`, `applied`, `failed`.
- **Resolution**:
  Implement the authoritative OpenAPI routes (`/repair-proposals/...`) and data models (`RepairStatus`), and provide route aliases for the shorter `/repairs/...` paths so both clients (`apps/manager-web`, `apps/vscode-extension`, and agents) function without broken routes.

---

### Discrepancy 4: Observations and Incident Evidence Storage
- **Database Design (`database-design.mmd`)**:
  Includes `REPOSITORY_NODES` and `REPOSITORY_EDGES` for AST/callgraph data, but does not include a dedicated `OBSERVATIONS` table.
- **OpenAPI Specification & Product Rules**:
  Explicitly requires `/scans/{scan_id}/observations`, `/incidents/{incident_id}/observations`, preserving evidence and linking observations to incidents.
- **Resolution**:
  Create an `observations` table (`id`, `scan_id`, `dependency_id`, `observation_type`, `endpoint`, `method`, `observed_at`, `payload_json`, `fingerprint`) and an `incident_observations` junction table to link incidents to preserved observations and evidence.

---

### Discrepancy 5: Approvals & Applications Persistence
- **Database Design (`database-design.mmd`)**:
  Repairs have inline `applied_at` and `applied_revision`, with no explicit approval or application audit tables.
- **OpenAPI Specification**:
  Defines distinct entities and endpoints: `POST .../approvals` (`RepairApproval`), `POST .../rejection`, and `POST .../applications` (`RepairApplication`).
- **Resolution**:
  Implement dedicated `repair_approvals` and `repair_applications` tables to preserve immutable audit trails of reviewer decisions and local extension application reports, while updating the proposal status accordingly.

---

### Discrepancy 6: Missing Referenced Document
- **Referenced File**: `docs/ANTIGRAVITY_BACKEND_PROMPT.md`
- **Status**: Missing from the repository.
- **Resolution**:
  Proceed using the authoritative instructions in `services/backend/AGENTS.md`, `docs/open-api.yaml`, `contracts/api-contract.md`, and `docs/database-design.mmd`.
