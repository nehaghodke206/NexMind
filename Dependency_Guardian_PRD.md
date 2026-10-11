# Product Requirements Document (PRD)

## Dependency Guardian
**A VS Code extension for detecting, explaining, and safely adapting external dependency changes**

| Field | Value |
|---|---|
| Document status | Revised MVP specification |
| Version | 1.1 |
| Date | 10 October 2026 |
| Product type | VS Code extension + local Python backend |
| Primary users | Application developers, platform engineers, QA engineers |
| MVP deployment | Local development environment |
| Primary dependency type | HTTP/JSON REST APIs |
| Demo environment | Fully simulated services and demo application |

---

## 1. Executive Summary

Dependency Guardian helps developers discover when an external service changes its observed behavior, understand which configured application workflows may be affected, and evaluate a comp-atibility repair before applying it.

The MVP pairs a VS Code extension with a local Python backend. The backend probes configured HTTP endpoints, stores known-good observations, compares later observations against those baselines, creates evidence-backed change reports, maps changes to explicitly configured workflows, and proposes narrowly scoped adapters. Repairs must be previewed, validated, and approved by the developer.

The product is designed around a safety principle:

> Detect and explain automatically; propose repairs cautiously; apply changes only after validation and explicit developer approval.

The MVP will demonstrate three simulated REST services and one notification tool represented by a local HTTP endpoint. It will focus on two repair paths—field rename compatibility and pagination adaptation—and one deliberately ambiguous payment-status change that must be blocked from automatic repair.

## 2. Problem Statement

Applications rely on external APIs and services whose behavior can change without a corresponding documented migration path. A response may remain valid JSON while a field is renamed, a pagination contract changes, error formats shift, rate limits increase, or a value's business meaning changes.

These changes can break application workflows or silently produce incorrect results. Developers must otherwise discover the change, trace dependencies, implement a compatibility layer, and run regression tests manually.

Dependency Guardian aims to shorten that investigation by connecting observed changes to configured workflows and tests, while making evidence and uncertainty visible.

## 3. Product Vision

Help software survive changes in systems it does not control.

Dependency Guardian should make dependency changes:

1. Observable through repeatable probes.
2. Comparable against a known-good baseline.
3. Understandable through evidence-backed explanations.
4. Traceable to configured workflows, files, and tests.
5. Repairable when a deterministic compatibility rule is safe enough.
6. Blocked for review when semantic equivalence cannot be established.

## 4. Goals and Non-Goals

### 4.1 MVP Goals

- Probe configured HTTP/JSON endpoints on demand.
- Create and preserve a known-good baseline.
- Detect structural and selected behavioral differences.
- Classify changes by impact and confidence.
- Map changes to workflows, files, and tests declared in configuration.
- Propose a field-rename adapter and a cursor-pagination adapter.
- Run contract and regression validation before a repair is eligible to be applied.
- Require explicit developer approval for every repair.
- Demonstrate an ambiguous semantic change that is flagged for human review.
- Present service status, changes, impact, repair proposals, and validation results in VS Code.
- Make the complete demo reproducible from a clean reset.

### 4.2 Non-Goals

The MVP will not:

- Monitor arbitrary APIs across the internet.
- Guarantee semantic equivalence between differently named fields or status values.
- Autonomously edit production systems or deploy code.
- Apply repairs without developer approval.
- Infer all code dependencies automatically.
- Replace production observability or API management platforms.
- Implement comprehensive SDK, webhook, or MCP protocol support.
- Guarantee that a passing test suite proves a repair is semantically correct.
- Send response bodies or credentials to an LLM by default.

## 5. Target Users and Core User Story

### Primary user
A developer maintaining an application that consumes external services.

### Secondary users
Technical leads, QA engineers, platform engineers, and reliability teams.

### Core user story
> As a developer, I want to know when a dependency's observed behavior changes, understand which configured workflows may be affected, and review a tested compatibility proposal without manually investigating the entire codebase.

### MVP use cases
- Detect a removed field and a possible replacement.
- Find configured workflows that reference the removed field.
- Propose a compatibility adapter and run regression tests.
- Detect a pagination contract change and propose an adapter.
- Detect a potentially semantic change and block automatic repair.
- Inspect a failed probe or failed validation without losing the last known-good baseline.

## 6. Product Scope and Prioritization

### P0 — Required for the demo
- VS Code extension scaffold and commands.
- Local FastAPI backend.
- `dependency-guardian.yml` configuration.
- Three simulated REST services: Users, Payments, Search.
- Notification tool simulated through a local HTTP endpoint.
- Manual probes and baseline creation.
- SQLite persistence for baselines, observations, scans, changes, and repair records.
- Structural diffing and selected behavior checks.
- Explicit workflow-to-dependency and workflow-to-file mapping.
- Change details and severity/confidence explanation.
- Field-rename adapter proposal.
- Human approval, validation, apply/reject, and rollback or restoration strategy.
- Cursor-pagination change detection and a bounded adapter proposal.
- Semantic uncertainty case that blocks repair.
- Reproducible demo scripts and automated tests.

### P1 — Include only after P0 works
- Periodic scans while the local backend is running.
- Richer response-header and rate-limit comparisons.
- Webview visualizations and status bar polish.
- Optional LLM-generated explanations or candidate mappings.
- Git diff preview for generated changes.

### Out of scope for the MVP
- Production traffic interception.
- Automatic repository-wide code search for arbitrary languages.
- Remote team dashboard.
- CI/CD and pull-request integrations.
- General-purpose SDK, webhook, and MCP protocol monitoring.

## 7. Product Principles

1. **Evidence before explanation:** every finding must include the observed baseline and current behavior.
2. **Deterministic first:** use code-based comparison rules for detection; use an LLM only as an optional assistant.
3. **No silent writes:** repairs are proposed, previewed, validated, and explicitly approved.
4. **Fail safely:** uncertain or failed validation blocks application.
5. **Preserve known-good state:** never overwrite the last known-good baseline merely because a scan observed a new response.
6. **Clear provenance:** distinguish observed facts, inferred mappings, and unverified hypotheses.
7. **Reproducible demo:** every scenario can be reset and replayed locally.

## 8. Proposed Architecture

```text
VS Code Extension (TypeScript)
  ├── Commands
  ├── Services / Changes Tree Views
  ├── Issue and Repair Webview
  └── Local backend client
             |
             | localhost HTTP API
             v
Local Python Backend (FastAPI)
  ├── Configuration loader and validator
  ├── Probe runner (HTTPX)
  ├── Normalizer and fingerprint builder
  ├── Baseline / observation store (SQLite)
  ├── Deterministic change detector
  ├── Workflow impact mapper
  ├── Repair planner
  ├── Validation runner (Pytest / configured command)
  └── Audit log
             |
             v
Simulated REST Services + Demo Application
  ├── Users API
  ├── Payments API
  ├── Search API
  └── Notification endpoint
```

### 8.1 Component responsibilities

**VS Code extension**
- Initiates scans and baseline creation.
- Displays services, changes, impact, proposals, and test results.
- Requests previews and explicit approval.
- Opens configured source files where possible.
- Never treats an LLM response as authorization to edit files.

**Local backend**
- Validates configuration and probe definitions.
- Executes bounded HTTP requests.
- Captures normalized observations.
- Computes diffs and rule-based severity.
- Maps findings using explicit configuration.
- Creates proposed repairs.
- Runs validation with timeouts and controlled working directories.
- Records actions and outcomes.

**Simulated services**
- Provide deterministic v1 and v2 modes.
- Expose a reset mechanism for repeatable demos.
- Never require real credentials or production data.

## 9. Supported Environment and Technology

### VS Code extension
- TypeScript
- VS Code Extension API
- Tree Views for structured lists
- Webview for detailed issue and repair review
- VS Code commands and notifications

### Backend
- Python 3.11 or later
- FastAPI
- Pydantic
- HTTPX
- SQLite
- Pytest
- JSON Schema or equivalent contract representation

### Demo services and app
- FastAPI-based simulated services
- Separate local ports or one simulator with distinct routes
- Version flags for v1/v2 behavior
- Small demo client with contract and workflow tests

### Optional AI
- LLM API with structured output for explanations or candidate mappings
- Off by default
- No secrets or full response bodies sent without an explicit, informed opt-in
- All output treated as untrusted suggestions and checked by deterministic rules

### Suggested local ports
- Backend: `127.0.0.1:8765`
- Users API: `127.0.0.1:8001`
- Payments API: `127.0.0.1:8002`
- Search API: `127.0.0.1:8003`
- Notification endpoint: `127.0.0.1:8004`

Ports are configurable; these are defaults for the demo.

## 10. Configuration Contract

The project configuration is `dependency-guardian.yml`. The backend must validate it and provide actionable errors for invalid IDs, missing fields, malformed URLs, unsupported methods, duplicate identifiers, or invalid file paths.

Example:

```yaml
project:
  name: demo-shop
  validation_command: "pytest -q"

settings:
  request_timeout_seconds: 3
  scan_timeout_seconds: 10
  max_response_bytes: 1000000
  allow_private_network_targets: true
  llm_explanations_enabled: false

dependencies:
  - id: users-api
    name: Users API
    base_url: "http://127.0.0.1:8001"
    probes:
      - id: user-profile
        method: GET
        path: "/users/u_123"
        expected_contract: user_profile

  - id: payments-api
    name: Payments API
    base_url: "http://127.0.0.1:8002"
    probes:
      - id: payment-detail
        method: GET
        path: "/payments/p_123"
        expected_contract: payment

  - id: search-api
    name: Search API
    base_url: "http://127.0.0.1:8003"
    probes:
      - id: search-page-one
        method: GET
        path: "/search?page=1"
        expected_contract: search_results

workflows:
  - id: user-profile
    name: User Profile Page
    dependencies: [users-api]
    source_files: ["demo-app/src/services/user_service.py"]
    fields: ["name", "email"]
    tests: ["demo-app/tests/test_user_profile.py"]

  - id: payment-dashboard
    name: Payment Dashboard
    dependencies: [payments-api]
    source_files: ["demo-app/src/services/payment_service.py"]
    fields: ["status", "amount"]
    tests: ["demo-app/tests/test_payments.py"]

  - id: user-search
    name: User Search
    dependencies: [search-api]
    source_files: ["demo-app/src/services/search_service.py"]
    fields: ["items", "page", "next_page"]
    tests: ["demo-app/tests/test_search.py"]
```

Configuration is an explicit mapping for the MVP, not proof of automatic source-code discovery. File paths must be resolved within the configured workspace. Commands must not be executed from arbitrary directories.

## 11. Simulated Dependency Scenarios

### 11.1 Users API: field rename

**V1**
```json
{
  "id": "u_123",
  "name": "Alice",
  "email": "alice@example.com"
}
```

**V2**
```json
{
  "id": "u_123",
  "display_name": "Alice",
  "email": "alice@example.com"
}
```

Expected finding:
- `name` removed; `display_name` added.
- Same observed type and matching value in the fixture.
- Candidate mapping suggested with evidence.
- User Profile workflow marked as potentially affected.
- Adapter proposed, previewed, validated, and approved before application.

Important: matching values in one probe are evidence for a candidate mapping, not proof of universal semantic equivalence.

### 11.2 Search API: pagination change

**V1**
```json
{
  "items": [{"id": "u_123"}],
  "page": 1,
  "next_page": 2
}
```

**V2**
```json
{
  "results": [{"id": "u_123"}],
  "next_cursor": "cursor_demo_2"
}
```

Expected finding:
- Response collection and pagination contract changed.
- Affected search workflow identified.
- System proposes an adapter only if the simulator and tests define the intended pagination semantics.
- The MVP must not claim a generic cursor-to-page conversion is safe without knowing how the cursor is consumed and how the next page is fetched.

### 11.3 Payments API: semantic uncertainty

**V1**
```json
{
  "id": "p_123",
  "status": "paid",
  "amount": 100
}
```

**V2 scenario**
The field remains `status`, but a controlled simulator changes the meaning or allowed values so that the old interpretation is no longer valid.

Expected finding:
- Structural diff alone may not detect the issue.
- A known-value expectation, contract rule, or scenario-specific assertion must reveal the change.
- The system labels the meaning as uncertain and blocks automatic repair.
- It must not invent a replacement or silently map values.

### 11.4 Notification tool

For the MVP, expose a local HTTP endpoint with a stable tool-oriented request/response contract. This simulates a notification dependency but does **not** constitute full MCP protocol support. Full MCP transport and tool-schema monitoring are future work.

## 12. Functional Requirements

| ID | Requirement | Acceptance condition |
|---|---|---|
| FR-01 | Load configuration | Valid config loads; invalid config shows a useful error. |
| FR-02 | Register dependencies | Each dependency has a unique ID, URL, and one or more probes. |
| FR-03 | Run manual scan | Extension starts a scan and reports completion or failure. |
| FR-04 | Create baseline | Known-good probe observations are persisted and versioned. |
| FR-05 | Capture observations | Record method, path, status, selected headers, body, latency, timestamp, and normalized contract. |
| FR-06 | Fingerprint behavior | Create a deterministic normalized representation for supported response behavior. |
| FR-07 | Detect structural changes | Detect added/removed fields, type changes, nullability/requiredness changes, and status/error-shape changes. |
| FR-08 | Detect selected behavior changes | Detect configured pagination, rate-limit, and known-value expectation changes. |
| FR-09 | Classify findings | Show rule, severity, evidence, and uncertainty; do not rely on a confidence score alone. |
| FR-10 | Map impact | Show configured dependent workflows, files, fields, and tests. |
| FR-11 | Propose field adapter | Generate a non-applied proposal for the Users API field rename scenario. |
| FR-12 | Propose pagination adapter | Generate a scenario-specific proposal only where pagination semantics are defined. |
| FR-13 | Preview repair | Show a diff or adapter preview before any write. |
| FR-14 | Validate repair | Run configured checks with a timeout and capture output/exit code. |
| FR-15 | Require approval | Every file-changing repair requires an explicit developer action. |
| FR-16 | Block unsafe repair | Semantic uncertainty or failed validation prevents application. |
| FR-17 | Apply and restore | Apply only the approved validated patch; preserve original content for rollback. |
| FR-18 | Show status | Display service, scan, finding, repair, and validation states. |
| FR-19 | Record audit events | Record scan, baseline, proposal, validation, approval, application, rejection, and rollback. |
| FR-20 | Recover from errors | Probe/backend/test failures are surfaced without corrupting the baseline. |

## 13. Change Detection and Risk Model

### 13.1 Detection approach

Use deterministic comparison as the source of truth. Normalize only known-irrelevant differences, such as object-key ordering. Do not normalize away array ordering, missing fields, meaningful values, or timestamps unless a probe explicitly defines those as variable.

For each probe, store:
- Request definition (excluding secrets).
- Status code.
- Selected headers relevant to behavior.
- JSON structure and types.
- Required/nullable field expectations when known.
- Known-value assertions when configured.
- Pagination and error-response fingerprints when relevant.
- Latency as an observation, not a breaking-contract signal by itself.

### 13.2 Initial classification rules

| Observation | Default classification |
|---|---|
| New optional field | Informational / low risk |
| Removed configured required field | High risk |
| Type changes | High risk |
| Required field becomes nullable or disappears | High risk |
| Status code changes for a known probe | Medium or high, based on expectation |
| Error response shape changes | Medium risk |
| Pagination contract changes | High risk |
| Rate-limit response/header changes | Medium risk |
| Known-value assertion fails | High risk or semantic review |
| Possible rename candidate | Repair candidate; not proof |
| Business meaning is unclear | Human review; no automatic repair |

Severity is rule-based and should be shown separately from mapping confidence. Confidence must explain what evidence supports the mapping and what remains unknown.

### 13.3 Baseline lifecycle

- A baseline is created only by an explicit developer action.
- A scan never silently replaces the last known-good baseline.
- A repaired dependency can be re-scanned and marked compatible, but baseline promotion requires an explicit action.
- Store baseline versions and timestamps so a developer can inspect or restore earlier versions.

## 14. Impact Analysis

For the MVP, impact analysis uses the explicit workflow mapping in the configuration file.

Each finding should identify:
- Dependency and probe.
- Changed fields or behavior.
- Configured workflows that reference the dependency or changed fields.
- Configured source files.
- Tests associated with those workflows.
- Evidence explaining the mapping.

The UI must describe these as **configured affected workflows/files**, not as guaranteed complete discovery of every source-code usage. Automated source-code indexing is outside the MVP unless time remains after core acceptance criteria pass.

## 15. Repair and Approval Workflow

Repair states:

`detected → proposed → previewed → validating → validation_passed → approved → applied`

Alternative terminal or blocked states:

`rejected`, `validation_failed`, `blocked_uncertain`, `apply_failed`, `rolled_back`.

Rules:
1. Detection does not automatically create a code change.
2. A repair proposal includes evidence, assumptions, target files, and a diff.
3. Validation runs against the proposed change in a controlled working copy or temporary patch.
4. A failed validation blocks application.
5. A passing test suite is necessary but not sufficient to establish semantic correctness.
6. The developer explicitly approves application after reviewing the diff and validation result.
7. Before applying, verify that target files have not changed since the preview was generated.
8. Preserve original contents and provide a rollback action.
9. If apply fails partway, restore changed files or report the partial state clearly.

## 16. Backend API Contract

Suggested local endpoints:

```text
GET    /api/health
POST   /api/projects/initialize
GET    /api/services
POST   /api/baselines
GET    /api/baselines
POST   /api/scans
GET    /api/scans/{scan_id}
GET    /api/changes
GET    /api/changes/{change_id}
GET    /api/changes/{change_id}/impact
POST   /api/changes/{change_id}/repair-proposals
GET    /api/repairs/{repair_id}
POST   /api/repairs/{repair_id}/validate
POST   /api/repairs/{repair_id}/apply
POST   /api/repairs/{repair_id}/reject
POST   /api/repairs/{repair_id}/rollback
```

API responses should use Pydantic models and consistent error shapes. Long-running scans and validation tasks should return an operation ID or clear state rather than leaving the extension waiting indefinitely.

Example scan result:

```json
{
  "scan_id": "scan_001",
  "status": "completed",
  "services_checked": 3,
  "changes_detected": 1,
  "started_at": "2026-10-10T12:00:00Z",
  "duration_ms": 640
}
```

## 17. Data Model

Persist at minimum:

**Dependency**
- `id`, `name`, `base_url`, `status`, `created_at`

**Probe**
- `id`, `dependency_id`, `method`, `path`, `expected_contract`

**Observation**
- `id`, `dependency_id`, `probe_id`, `scan_id`, `status_code`, `normalized_fingerprint`, `safe_response_snapshot`, `latency_ms`, `observed_at`

**Baseline**
- `id`, `dependency_id`, `probe_id`, `version`, `fingerprint`, `created_at`, `created_by_action`

**Change**
- `id`, `dependency_id`, `probe_id`, `type`, `severity`, `evidence`, `status`, `created_at`

**Impact**
- `change_id`, `workflow_id`, `source_file`, `test_file`, `reason`

**Repair proposal**
- `id`, `change_id`, `type`, `patch`, `evidence`, `assumptions`, `confidence`, `status`, `created_at`

**Validation run**
- `id`, `repair_id`, `command`, `exit_code`, `output_summary`, `started_at`, `duration_ms`, `status`

**Audit event**
- `id`, `actor_action`, `target_type`, `target_id`, `details`, `created_at`

Avoid storing secrets or unnecessary raw response data. Redact configured sensitive fields before persistence and logging.

## 18. VS Code UX Requirements

### Commands
- Dependency Guardian: Initialize Project
- Dependency Guardian: Create Baseline
- Dependency Guardian: Scan Dependencies
- Dependency Guardian: View Detected Changes
- Dependency Guardian: Analyze Impact
- Dependency Guardian: Preview Repair
- Dependency Guardian: Run Validation
- Dependency Guardian: Apply Repair
- Dependency Guardian: Reject Repair
- Dependency Guardian: Roll Back Repair

### Sidebar
- Services
- Detected Changes
- Affected Workflows
- Repair Proposals
- Validation Results

### Finding details
Every finding screen should show:
- Dependency and endpoint.
- Baseline vs current observation.
- Change type and severity.
- Evidence and limitations.
- Affected configured workflows, files, and tests.
- Proposed repair and assumptions.
- Validation output.
- Available next actions.

### Repair controls
- Preview Fix
- Run Validation
- Apply Fix (enabled only after successful validation and review)
- Reject
- Roll Back (after a successful application)

### Status bar
Examples:
- Dependency Guardian: Healthy
- Dependency Guardian: Scanning
- Dependency Guardian: 1 issue
- Dependency Guardian: Review required

Webview messages must be validated by the extension host. The Webview must not directly execute shell commands or access arbitrary local files.

## 19. Security and Reliability Requirements

- Bind the backend to loopback (`127.0.0.1`) by default, not all network interfaces.
- Restrict probe targets according to project configuration and prevent accidental access to cloud metadata endpoints or unintended private hosts. Local simulated services are explicitly allowed.
- Apply request, response-size, and scan timeouts.
- Do not follow redirects to unapproved targets by default.
- Redact credentials and sensitive headers from logs and audit records.
- Treat response bodies, API descriptions, and LLM output as untrusted data.
- Never execute commands supplied by a remote service or an LLM.
- Allow only configured validation commands, run in the workspace with a timeout and visible output.
- Keep all file writes within the workspace and reject path traversal.
- Check file hashes or modification times before applying a previously previewed patch.
- Preserve last-known-good baselines.
- Make file-changing operations reversible.
- Do not send data to an external AI service unless the user has explicitly enabled that feature.

## 20. Non-Functional Requirements and Targets

These targets apply to the local demo environment and are not production-scale guarantees.

| Area | MVP target |
|---|---|
| Scan duration | Three local services complete a manual scan within 10 seconds under normal conditions |
| Change comparison | Compare the demo observations within 1 second, excluding network probe time |
| UI update | Show scan results within 2 seconds after backend completion |
| Reproducibility | Each scripted scenario can be reset and replayed |
| Failure handling | Backend/probe/test failure is visible and does not overwrite the baseline |
| Traceability | Each finding links to its observation and configured impact evidence |
| Safety | No file-changing repair without validation and explicit approval |
| Testability | Detection, state transitions, repair gating, and demo scenarios have automated tests |

## 21. Acceptance Criteria

The MVP is ready for judging when all of the following pass:

1. A developer initializes the project from VS Code.
2. Configuration is validated and invalid configuration produces a useful error.
3. A baseline can be created and remains unchanged by later scans.
4. A scan checks all three simulated REST services.
5. The Users API rename is detected with baseline/current evidence.
6. The configured User Profile workflow, file, and test are identified.
7. A field adapter is proposed and previewed.
8. Validation runs before application.
9. The approved adapter restores the User Profile demo test.
10. The Search API pagination change is detected and a bounded proposal is shown.
11. The Payments semantic-uncertainty scenario blocks automatic repair.
12. A failing validation prevents application.
13. A successful repair can be rolled back.
14. A backend or probe failure does not crash the extension or corrupt the baseline.
15. The full demo can be reset and replayed without manually editing code during the scenario.

## 22. Demo Plan

### Demo preparation
- Start the backend and simulated services.
- Reset service modes to v1.
- Run tests and confirm the demo app is healthy.
- Create the baseline.
- Ensure the extension shows all services as healthy.

### Live sequence
1. **Baseline:** show the three dependencies and healthy workflows.
2. **Introduce change:** switch Users API from `name` to `display_name`.
3. **Scan:** show the removed/added field and evidence.
4. **Impact:** open the User Profile workflow and its configured file/test.
5. **Repair:** preview the adapter, run validation, and apply after approval.
6. **Recovery:** show the workflow passing again.
7. **Second change:** switch Search API to cursor pagination and show the detected contract change and bounded proposal.
8. **Safety case:** change payment-status semantics and show that automatic repair is blocked.
9. **Close:** summarize changes detected, workflows recovered, and uncertain repairs safely blocked.

### Suggested closing statement
“Dependency Guardian does more than tell you an API changed. It connects observed behavior to the workflows you configured, proposes a tested compatibility path, and stops when it cannot establish that a repair is safe.”

## 23. Development Plan

Build in dependency order. Do not build a polished Webview before the end-to-end backend pipeline works.

### Phase 1 — Skeleton and demo harness
- Create repository and folders.
- Create simulated service version switches and reset script.
- Create demo application and baseline tests.
- Create extension scaffold and FastAPI health endpoint.

**Exit condition:** all services and demo tests run locally from documented commands.

### Phase 2 — Observation and baselines
- Implement configuration validation.
- Implement HTTP probes and bounded response capture.
- Normalize supported JSON responses.
- Store observations and versioned baselines in SQLite.

**Exit condition:** create baseline, scan again, and inspect persisted observations.

### Phase 3 — Detection and impact
- Implement deterministic structural diffing.
- Add known pagination and status/error behavior rules.
- Add severity and evidence output.
- Map findings to configured workflows, files, and tests.

**Exit condition:** scripted Users and Search changes produce expected findings and impacts.

### Phase 4 — Repair safety
- Implement field adapter proposal.
- Implement bounded pagination proposal.
- Add preview, validation, approval, apply, reject, and rollback states.
- Add file-safety checks and audit events.

**Exit condition:** a valid repair passes, an invalid repair is blocked, and rollback restores original behavior.

### Phase 5 — VS Code workflow
- Add commands and sidebar Tree Views.
- Connect extension to backend.
- Display findings, impact, and validation output.
- Add repair preview and approval actions.

**Exit condition:** complete core flow works without requiring terminal interaction except initial startup.

### Phase 6 — Polish and rehearsal
- Add payment semantic-uncertainty scenario.
- Add reset/demo script.
- Improve errors and loading states.
- Run automated acceptance tests.
- Rehearse a two-minute demo and prepare architecture visuals.

**Exit condition:** all acceptance criteria pass from a clean reset.

## 24. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| False positives | Deterministic rules, normalization, and visible evidence |
| False field-rename inference | Treat rename as a candidate; require tests and approval |
| Cursor mapping is underspecified | Define exact simulator semantics and tests before proposing a repair |
| Semantic change cannot be inferred from shape | Add explicit known-value assertions; label remaining uncertainty |
| LLM hallucination | Keep detection deterministic and validate every suggestion |
| Scope overwhelms team | Finish Users end-to-end before adding optional integrations |
| Unsafe local probing | Loopback defaults, target restrictions, timeouts, and response-size limits |
| Patch applies to stale files | Verify file state before application and preserve rollback data |
| Demo failure | Reset scripts, fixed fixtures, automated smoke tests, and a backup recording |

## 25. Future Roadmap

### Post-MVP
- OpenAPI contract comparison.
- GitHub pull request comments and CI checks.
- Source-code indexing for supported languages.
- Webhook payload monitoring.
- Full MCP protocol and tool-schema support.
- SDK-specific adapters.
- Team-shared dependency graph.
- Runtime trace-based impact discovery.
- Canary validation and controlled rollback.
- Historical change analytics.

## 26. Final MVP Definition

Dependency Guardian MVP is complete when a developer can open the demo project in VS Code, create a baseline for simulated external services, detect an undocumented behavior change, inspect evidence and configured impact, preview a compatibility proposal, validate it, explicitly approve the change, and see the affected workflow pass again.

The product must also demonstrate safe restraint: when a semantic change cannot be established as equivalent, or validation fails, the system blocks automatic application and asks for human review.
