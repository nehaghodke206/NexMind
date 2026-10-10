# Dependency Guardian — Backend Agent Instructions

These instructions apply to the backend component in `services/backend/`. Keep changes scoped to this directory unless a shared contract discrepancy requires a proposed change.

## Before coding
1. Inspect the existing repository and preserve its current structure.
2. Read the shared API contract in `contracts/` and the actual database design in `docs/`.
3. Read `docs/ANTIGRAVITY_BACKEND_PROMPT.md` for the implementation plan.
4. Compare the API contract with the database design. If they conflict, document the discrepancy in `docs/contract-review.md` and explain the proposed resolution before changing shared contracts or implementing conflicting behavior.
5. Do not assume a database schema that is not present in the repository. If the database design is missing or ambiguous, state what is missing and ask for clarification or implement only unblocked foundation work.

## Scope and architecture
- Implement the backend only in `services/backend/`.
- Use Python 3.11+ and FastAPI.
- Use SQLAlchemy 2.x for persistence and Alembic for migrations.
- Use Pydantic v2 / `pydantic-settings` for request/response schemas and configuration.
- Use pytest and HTTPX for tests; Uvicorn for local development.
- Follow a modular, MVC-like layered architecture:
    - routers/controllers: HTTP routing, request parsing, response codes
    - services: business rules and workflow orchestration
    - repositories: database queries and persistence operations
    - models/entities: SQLAlchemy database models
    - schemas/DTOs: Pydantic request and response models
    - core: configuration, database session, exceptions, logging
- Prefer feature-based modules where practical. Keep routes thin and avoid putting business logic in ORM models or controllers.
- Add Alembic migrations for schema changes; do not rely on `create_all()` as the migration strategy.
- Keep dependencies explicit and documented in `requirements.txt` (or the existing dependency manager if already established).
- Add or update the backend README with setup, migration, run, and test instructions.

## Shared repository rules
- Treat `contracts/` and team-wide documentation as shared assets. Do not silently change API fields, endpoint paths, enum values, or error formats.
- If a contract change is needed, document the reason and coordinate it; keep clients and other components in mind.
- Do not edit teammates' code in `apps/`, `agents/`, or other components.
- Do not create or modify a root-level `AGENTS.md`.
- Never commit secrets. Keep local credentials in `.env`; provide safe placeholders in `.env.example`.
- Prefer PostgreSQL for shared deployment. If the supplied local setup explicitly uses SQLite for development, keep configuration environment-driven so PostgreSQL can be used without redesigning the app.

## Product invariants
- A baseline represents a known-good observation and must be versioned; never silently overwrite it.
- Preserve observations and evidence so an incident can be explained and reproduced.
- Deduplicate repeated detections using a stable fingerprint where appropriate.
- Keep repair proposals separate from validation results, approvals, and actual application results.
- Approval is not application. A repair must not be marked applied or an incident resolved merely because a proposal was approved.
- The backend must not reach into or edit a developer's laptop or repository directly. A local extension/agent applies a patch and reports the result to the backend.
- Require explicit human approval before a repair is treated as approved.
- Use clear lifecycle transitions and reject invalid transitions with useful error responses.

## Delivery discipline
- Build the smallest end-to-end vertical slice first: health check, project/dependency setup, baseline/scan observations, and incident creation with evidence.
- Add the repair proposal, validation, approval/rejection, and application-result lifecycle only after the first slice works.
- Write tests for business rules, API behavior, and important failure paths.
- Run the tests and report the actual result. Never claim tests passed, migrations succeeded, or an endpoint works unless you ran the relevant command and observed success.
- Keep changes focused. Do not build the AI agent, manager frontend, or VS Code extension as part of backend work.
- At completion, summarize files changed, commands run, test outcomes, known gaps, and the next recommended step.
