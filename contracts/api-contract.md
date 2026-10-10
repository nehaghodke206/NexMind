
# API Contract (MVP)

Base path: `/api/v1`

## Initial endpoint plan

- `GET /health`
- `GET /api/v1/projects`
- `POST /api/v1/projects`
- `GET /api/v1/projects/{project_id}`
- `POST /api/v1/projects/{project_id}/dependencies`
- `GET /api/v1/projects/{project_id}/dependencies`
- `POST /api/v1/projects/{project_id}/incidents`
- `GET /api/v1/projects/{project_id}/incidents`
- `GET /api/v1/incidents/{incident_id}`
- `PATCH /api/v1/incidents/{incident_id}`
- `POST /api/v1/incidents/{incident_id}/repairs`
- `GET /api/v1/repairs/{repair_id}`
- `POST /api/v1/repairs/{repair_id}/validate`
- `POST /api/v1/repairs/{repair_id}/approve`
- `POST /api/v1/repairs/{repair_id}/apply-result`
- `GET /api/v1/projects/{project_id}/activity`

## Suggested incident fields

`dependency_id`, `title`, `description`, `severity`, `source`, `fingerprint`,
`evidence`, `affected_files`, and `affected_workflows`.

## Suggested lifecycle values

Incident: `detected`, `analyzing`, `repair_proposed`, `validating`,
`validation_failed`, `ready_for_review`, `approved`, `resolved`, `blocked`.

Repair proposal: `proposed`, `validating`, `validation_passed`, `validation_failed`,
`approved`, `rejected`, `applied`.

Treat this as the starting proposal: agree on fields, states, permissions, and error
formats as a team before implementing clients. Approval is not application.
Repeated detections should be deduplicated using a stable fingerprint.

