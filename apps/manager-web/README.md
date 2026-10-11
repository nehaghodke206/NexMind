# Manager Web

Owned by the manager-web teammate.

Choose and document the frontend framework and internal architecture here.
Required integration: configure the backend API base URL and follow `contracts/api-contract.md`.
Document install, run, build, and test commands before merging implementation.

---

## Overview

Manager Web is the incident management and human-in-the-loop review dashboard for **Dependency Guardian**. It provides visibility into breaking third-party API changes, impact diagnostics, candidate repair proposals, automated validation test results, and reviewer approval workflows.

## Technology Stack & Architecture

- **Framework**: React 18 with TypeScript and Vite
- **Routing**: React Router DOM (v6)
- **Styling**: Semantic, high-contrast, accessible CSS with custom design tokens (`src/styles/variables.css` and `src/styles/app.css`)
- **API Client**: Strongly typed contract-matching client (`src/api/client.ts` and `src/api/types.ts`) supporting both mock mode and live FastAPI backend integration

## Directory Structure

```text
apps/manager-web/
├── .env.example              # Environment variable template
├── .eslintrc.cjs             # ESLint configuration
├── index.html                # Vite HTML entry point
├── package.json              # App scripts and dependencies
├── tsconfig.json             # TypeScript compiler configuration
├── vite.config.ts            # Vite build configuration
├── NOTES.md                  # Contract gaps and architectural decisions
├── README.md                 # Project documentation
└── src/
    ├── api/
    │   ├── client.ts         # Typed API client with mock and live fetch adapters
    │   ├── mockData.ts       # Mock dataset based on contracts/examples/*.json
    │   └── types.ts          # TypeScript interfaces for API models and lifecycle states
    ├── components/
    │   ├── common/           # Shared accessible UI primitives (Badge, Chip, States)
    │   ├── layout/           # AppHeader, AppLayout
    │   └── incidents/        # EvidenceViewer, DiffViewer, RepairProposalCard, ApproveModal
    ├── pages/                # ProjectListPage, IncidentListPage, IncidentDetailPage, ActivityFeedPage
    ├── styles/               # CSS variables and application stylesheets
    ├── App.tsx               # App routing and layout shell
    └── main.tsx              # React DOM entry point
```

## Environment Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000/api/v1` | URL for the Dependency Guardian FastAPI backend |
| `VITE_USE_MOCK` | `true` | When `true`, uses mock data modeled from `contracts/examples/` |

## Commands

All commands must be executed from inside `apps/manager-web/`:

### Install Dependencies
```bash
npm install
```

### Start Development Server
```bash
npm run dev
```
Starts the local dev server at `http://localhost:5173`.

### Build for Production
```bash
npm run build
```
Typechecks with `tsc` and bundles assets with Vite into `dist/`.

### Run Linter
```bash
npm run lint
```
Runs ESLint across all TypeScript and React source files with zero allowed warnings.

## Product & Lifecycle Rules

1. **Approval is Not Application**: Human review approval (`POST /repair-proposals/{id}/approvals`) registers review sign-off. The incident only transitions to `resolved` once the patch is applied and verified in the target environment by the developer or agent.
2. **Accessible Severity Indicators**: Severity levels (`critical`, `high`, `medium`, `low`) use distinctive textual and shape indicators in addition to high-contrast colors.
3. **Resilience & State Handling**: Every screen includes loading, empty, and actionable error states with Retry capabilities.
