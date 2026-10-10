#!/usr/bin/env bash
set -euo pipefail

# Dependency Guardian monorepo scaffold
# Run from the repo root: bash scripts/create-structure.sh
# Safe to rerun: it never overwrites existing files.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/" && pwd)"
cd "$ROOT"

echo "Scaffolding Dependency Guardian in: $ROOT"

dirs=(
  "apps/manager-web"
  "apps/vscode-extension"
  "services/backend/app"
  "services/backend/tests"
  "agents/detection"
  "agents/repair"
  "contracts/examples"
  "demo/simulated-apis"
  "demo/sample-project"
  "tests/integration"
  "docs"
  "scripts"
)

for dir in "${dirs[@]}"; do
  mkdir -p "$dir"
  # Only add .gitkeep when the directory has no other entries.
  if [[ -z "$(find "$dir" -mindepth 1 -maxdepth 1 ! -name .gitkeep -print -quit)" ]]; then
    touch "$dir/.gitkeep"
  fi
done

create_file() {
  local file="$1"
  local content="$2"
  if [[ ! -e "$file" ]]; then
    mkdir -p "$(dirname "$file")"
    printf '%s\n' "$content" > "$file"
    echo "Created: $file"
  else
    echo "Kept existing: $file"
  fi
}

create_file ".gitignore" '
# Environment / secrets
.env
.env.*
!.env.example
*.pem
*.key

# Python
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.venv/
venv/

# JavaScript / frontend
node_modules/
dist/
build/
coverage/
.vscode-test/

# Local data and logs
*.db
*.sqlite
*.sqlite3
*.log

# OS/editor
.DS_Store
Thumbs.db
.idea/
'

create_file ".env.example" '
APP_ENV=development
API_HOST=127.0.0.1
API_PORT=8000
DATABASE_URL=sqlite:///./dependency_guardian.db

# Set frontend API URL in the frontend framework-specific environment file.
# Example for Vite: VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
'

create_file "README.md" '
# Dependency Guardian

Detect breaking third-party API changes, track incidents, propose repairs,
validate changes, and support human review.

## Monorepo layout

- `apps/manager-web/` — manager dashboard; internal structure chosen by its owner
- `apps/vscode-extension/` — VS Code extension; internal structure chosen by its owner
- `services/backend/` — FastAPI backend; MVC/layered architecture chosen by backend owner
- `agents/detection/` — API change detection component
- `agents/repair/` — impact analysis and repair proposal component
- `contracts/` — shared API contract and example payloads
- `demo/` — simulated APIs and sample project
- `tests/integration/` — cross-component integration tests
- `docs/` — project-wide documentation
- `scripts/` — shared developer scripts

## Team rule

Top-level locations and cross-component contracts are shared. Each component owner may
choose their own internal folder structure, language conventions, and architecture.
Before changing an API field, status, or endpoint, update the contract and coordinate
with the other component owners.

## Getting started

Read `docs/architecture.md`, `docs/setup.md`, and `contracts/api-contract.md`.
Never commit `.env`, credentials, tokens, or private keys.
'

create_file "docs/architecture.md" '
# Architecture

## Components

- Manager web: incidents, assignments, reviews, and activity.
- VS Code extension: developer workflow, incident details, patch preview, and validation UI.
- FastAPI backend: shared API, lifecycle rules, and persistence.
- Detection agent: API observations, baseline comparison, classification, and evidence.
- Repair agent: impact analysis, candidate patches, risk evaluation, and validation helpers.

## Integration

The backend is the source of truth for shared persisted state. The agents submit findings,
proposals, and validation results through the agreed contract. The website and extension
read and update shared state through the backend API.

Approval is not application. Resolve an incident only after the patch is actually applied
and the agreed success criteria are confirmed.

## Internal architecture freedom

Each component may choose its own internal structure. The repository standardizes only
component locations, API contracts, configuration conventions, and run/test documentation.
'

create_file "docs/setup.md" '
# Development Setup

Each component owner must document prerequisites, installation, run, and test commands
in that component folder README.

## Backend starter

From `services/backend/`:

```bash
python -m venv .venv
```

Activate the environment:

Linux/macOS:
```bash
source .venv/bin/activate
```

Windows PowerShell:
```powershell
.venv\Scripts\Activate.ps1
```

Install and run:
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Health check: http://127.0.0.1:8000/health
API docs: http://127.0.0.1:8000/docs
'

create_file "docs/deployment.md" '
# Deployment Notes

This is one Git repository, not necessarily one deployed service.

- Deploy `apps/manager-web/` as a frontend.
- Run `services/backend/` as a FastAPI web service.
- Use persistent database storage; PostgreSQL is a good choice for a shared hosted deployment.
- Package `apps/vscode-extension/` as a VSIX.
- Run agents locally or as hosted workers depending on repository and test access needs.
- Configure CORS and environment-specific API URLs.
- Keep secrets in the hosting provider secret manager or environment settings.
'

create_file "contracts/api-contract.md" '
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
'

create_file "contracts/examples/incident.json" '
{
  "dependency_id": "dep_demo_users",
  "title": "Users API response field renamed",
  "description": "Expected field name was not found; display_name was observed.",
  "severity": "high",
  "source": "detection-agent",
  "fingerprint": "users-api:name-to-display_name",
  "evidence": {
    "removed_fields": ["name"],
    "added_fields": ["display_name"],
    "type_changes": [],
    "baseline": {"name": "Ada Lovelace"},
    "observed": {"display_name": "Ada Lovelace"}
  },
  "affected_files": ["src/users/client.ts"],
  "affected_workflows": ["user profile display"]
}
'

create_file "contracts/examples/repair-proposal.json" '
{
  "proposed_by": "repair-agent",
  "rationale": "Update the consumer mapping to use display_name.",
  "patch": {
    "format": "unified_diff",
    "content": ""
  },
  "risk_level": "medium"
}
'

create_file "contracts/examples/validation-result.json" '
{
  "result": "failed",
  "tests_total": 3,
  "tests_passed": 2,
  "tests_failed": 1,
  "summary": "One test still expects the old field."
}
'

create_file "services/backend/requirements.txt" '
fastapi
uvicorn[standard]
sqlalchemy
pydantic-settings
'

create_file "services/backend/app/main.py" '
from fastapi import FastAPI

app = FastAPI(
    title="Dependency Guardian API",
    version="0.1.0",
)

@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
'

create_file "services/backend/README.md" '
# Backend

Backend owner chooses and documents the internal MVC/layered structure here.

Starter stack: FastAPI, SQLAlchemy, and Pydantic Settings.

From this directory:
```bash
python -m venv .venv
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Health: http://127.0.0.1:8000/health
API docs: http://127.0.0.1:8000/docs
'

create_file "apps/manager-web/README.md" '
# Manager Web

Owned by the manager-web teammate.

Choose and document the frontend framework and internal architecture here.
Required integration: configure the backend API base URL and follow `contracts/api-contract.md`.
Document install, run, build, and test commands before merging implementation.
'

create_file "apps/vscode-extension/README.md" '
# VS Code Extension

Owned by the VS Code extension teammate.

Choose the internal extension structure following the VS Code tooling conventions.
Required integration: configurable backend URL, shared API contract, and an actionable
error state when the backend is unavailable.
Document install, run, package, and test commands before merging implementation.
'

create_file "agents/detection/README.md" '
# Detection Agent

Owned by the detection teammate.

Choose the internal architecture that best supports API probes, baseline management,
response comparison, change classification, evidence capture, and incident submission.

Do not silently overwrite a known-good baseline. Document setup, run, and test commands.
'

create_file "agents/repair/README.md" '
# Repair Agent

Owned by the repair teammate.

Choose the internal architecture that best supports impact analysis, candidate patch
generation, risk evaluation, and validation helpers.

Prefer deterministic checks and send uncertain semantic changes for human review.
Document setup, run, and test commands.
'

echo
echo "Scaffold ready."
echo "Review it with: git status"
echo "Then commit and push the shared structure."
