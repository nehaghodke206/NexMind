
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

