# Dependency Guardian

**Detect breaking third-party API changes, track incidents, propose repairs, validate changes, and support human review.**

---

## Executive Summary

Modern applications depend on external HTTP/JSON APIs whose behaviors often change without warning: fields get renamed, pagination contracts shift from page offsets to opaque cursors, and business status values evolve.

**Dependency Guardian** solves this through a core safety principle:
> *Detect and explain automatically; propose repairs cautiously; apply changes only after validation and explicit developer approval.*

---

## Monorepo Layout

- `apps/manager-web/` — Manager dashboard web interface (React + Vite)
- `vscode-extension/` (and `apps/vscode-extension/`) — VS Code extension for developers
- `services/backend/` & `backend/` — FastAPI backend services
- `agents/detection/` — API change detection agent
- `agents/repair/` — Impact analysis and repair proposal component
- `contracts/` — Shared API contracts and example payloads
- `demo/` & `demo-app/` — Simulated APIs, sample applications, and contract tests
- `simulators/` — Standalone simulated REST APIs (Users, Payments, Search, Notification)
- `tests/integration/` — Cross-component integration tests
- `scripts/` — Shared developer scripts, unified runners, and acceptance test suite
- `docs/` — Project-wide documentation and PRD

---

## Architecture

```text
VS Code Extension (TypeScript)
  ├── Activity Bar & Sidebar Views (Services, Changes, Workflows, Repairs)
  ├── Status Bar Indicator (Healthy, Issues Detected, Scanning)
  ├── Interactive Professional Webview Dashboard (Diff Viewer, Validation, Scenario Switcher)
  └── Local Backend Client (HTTP / JSON)
              │
              │ http://127.0.0.1:8765
              ▼
Local Python Backend (FastAPI + SQLite)
  ├── Configuration Loader & Validator (dependency-guardian.yml)
  ├── HTTP Probe Runner (bounded requests, timeouts, redactions)
  ├── Deterministic Normalizer & Fingerprint Generator
  ├── SQLite Persistence (baselines, observations, changes, repairs, audit)
  ├── Deterministic Change Detector (renames, pagination, semantic uncertainty)
  ├── Workflow Impact Mapper (explicit workflow, file, and test mapping)
  ├── Repair Planner (field rename adapters, cursor pagination adapters)
  ├── Validation Runner (pytest sandbox execution)
  └── Repair Applier & Rollback Engine (file hash checks & backups)
              │
              ▼
Simulated External REST Services
  ├── Users API (Port 8001)         -> Field rename scenario (name -> display_name)
  ├── Payments API (Port 8002)      -> Semantic uncertainty scenario (status: "processing_escrow")
  ├── Search API (Port 8003)        -> Cursor pagination change (items/page -> results/next_cursor)
  └── Notification Tool (Port 8004) -> Tool status probe
```

---

## Quick Start Guide

### 1. Requirements
- Python 3.10+
- Node.js 18+ and npm

### 2. Install Python Dependencies
```bash
pip install fastapi uvicorn pydantic httpx pyyaml pytest
```

### 3. Compile the VS Code Extension
```bash
npm run compile
```

### 4. Start the Unified Server Stack
Run the unified server stack (binds strictly to loopback `127.0.0.1`):
```bash
python scripts/run_all.py
```


### 5. Run the Automated Acceptance Test Suite
Verify all 15 acceptance criteria end-to-end:
```bash
python scripts/test_e2e.py
```

### 6. Run the Live Demo Walkthrough
```bash
python scripts/demo_runner.py
```

---

## Live Demo & Judging Sequence

### Scenario 1: Users API Field Rename
1. **Initial Baseline:** Start with all services on v1 baseline. Running a scan reports 0 changes.
2. **Introduce Drift:** Click **Users API: Field Rename** or send `POST /api/demo/set-scenario {"scenario": "users_v2"}`.
3. **Scan:** Dependency Guardian detects `field_rename_candidate` with exact baseline and current evidence (`Alice` == `Alice`).
4. **Impact Mapping:** Identifies `User Profile Page` workflow, target file `demo-app/src/services/user_service.py`, and test `demo-app/tests/test_user_profile.py`.
5. **Repair Proposal:** Generates unified diff adapter resolving `display_name` with fallback to `name`.
6. **Validation & Apply:** Running validation executes tests in a temporary sandbox. Once passed, developer approves and applies the patch.
7. **Recovery:** Affected workflow tests pass cleanly!

### Scenario 2: Search API Pagination Change
1. Switch simulator to **Search API: Cursor Pagination** (`POST /api/demo/set-scenario {"scenario": "search_v2"}`).
2. Dependency Guardian flags `pagination_contract_change` (High Severity).
3. Generates a bounded pagination adapter handling both legacy `items`/`page` and modern `results`/`next_cursor`.

### Scenario 3: Payments API Semantic Uncertainty (Safety Enforcement)
1. Switch Payments API to v2 (`status: "processing_escrow"`).
2. Dependency Guardian observes known-value assertion breach.
3. **Safety Block:** Automatically tags finding as `semantic_uncertainty`, flags severity as `BLOCKED`, and **strictly forbids automatic repair synthesis**.
4. Clearly explains why automated repair is prohibited to prevent corrupting financial business logic.

---

## Acceptance Criteria Matrix (15 / 15 Passed)

| # | PRD Acceptance Criterion | Verification Status |
|---|---|---|
| **AC 1** | Project initialization from VS Code / backend | Passed |
| **AC 2** | Configuration validated; invalid config yields actionable error | Passed |
| **AC 3** | Baseline created and preserved across future scans | Passed |
| **AC 4** | Scan checks all simulated REST services | Passed |
| **AC 5** | Users API rename detected with baseline/current evidence | Passed |
| **AC 6** | User Profile workflow, file, and test identified in impact analysis | Passed |
| **AC 7** | Field adapter proposed and diff previewed | Passed |
| **AC 8** | Validation runs before application | Passed |
| **AC 9** | Approved adapter restores User Profile demo test | Passed |
| **AC 10** | Search API pagination change detected & bounded proposal shown | Passed |
| **AC 11** | Payments semantic-uncertainty scenario blocks automatic repair | Passed |
| **AC 12** | Failing validation prevents application | Passed |
| **AC 13** | Successful repair can be rolled back | Passed |
| **AC 14** | Endpoint failure handled safely without corrupting baselines | Passed |
| **AC 15** | Full demo can be reset and replayed without manual code editing | Passed |
