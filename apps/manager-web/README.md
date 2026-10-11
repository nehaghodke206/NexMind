# Manager Web

Owned by the manager-web teammate.

Choose and document the frontend framework and internal architecture here.
Required integration: configure the backend API base URL and follow `contracts/api-contract.md`.
Document install, run, build, and test commands before merging implementation.

---

## Overview

Manager Web is the incident management and human-in-the-loop review dashboard for **Dependency Guardian**. It provides visibility into breaking third-party API changes, impact diagnostics, candidate repair proposals, automated validation test results, registered contract baselines, active scanner probes, and reviewer approval workflows.

## Technology Stack & Architecture

- **Framework**: React 18 with TypeScript and Vite
- **Routing**: React Router DOM (v6)
- **Styling**: Enterprise software design system with warm beige background, crimson red primary brand accent, and minimalistic pastel severity/status chips (`src/styles/variables.css` and `src/styles/app.css`)
- **API Client**: Strongly typed contract-matching client (`src/api/client.ts` and `src/api/types.ts`) supporting live FastAPI backend integration with configurable environment switching and simulation fallback

## Directory Structure

```text
apps/manager-web/
├── .env                    # Configured environment variables (localhost / live mode)
├── .env.example            # Environment variable template
├── .eslintrc.cjs           # ESLint configuration
├── index.html              # Vite HTML entry point
├── package.json            # App scripts and dependencies
├── tsconfig.json           # TypeScript compiler configuration
├── tsconfig.node.json      # TypeScript Node compiler configuration
├── vite.config.ts          # Vite build configuration
├── NOTES.md                # Contract gaps and architectural decisions
├── README.md               # Project documentation
└── src/
    ├── api/
    │   ├── client.ts       # Typed API client calling real backend endpoints or mock simulation
    │   ├── mockData.ts     # Complete mock dataset based on contracts/examples/*.json & open-api.yaml
    │   └── types.ts        # TypeScript interfaces for API models and lifecycle states
    ├── components/
    │   ├── common/         # Shared accessible UI primitives (Badge, StatusChip, LoadingState, ErrorState, EmptyState)
    │   ├── layout/         # AppHeader (with live /health monitor), AppLayout, ThemeSlider
    │   └── incidents/      # EvidenceViewer, DiffViewer, RepairProposalCard, ApproveModal (with Reject support)
    ├── pages/
    │   ├── ProjectListPage.tsx     # Project observatory with KPI metrics (GET /projects/:id/summary)
    │   ├── IncidentListPage.tsx    # Filterable incident list with search and severity tabs
    │   ├── IncidentDetailPage.tsx  # Detailed evidence, raw observations, and repair approvals
    │   ├── DependenciesPage.tsx    # Monitored services & baseline contracts (GET /dependencies/:id/baselines)
    │   ├── ScansPage.tsx           # Active scanner runs and probe execution (GET/POST /projects/:id/scans)
    │   ├── ActivityFeedPage.tsx    # Chronological project audit log (GET /projects/:id/activity)
    │   └── NotFoundPage.tsx        # 404 fallback page
    ├── styles/             # CSS design tokens, palettes, and global styles
    ├── App.tsx             # Application routing and route guards
    ├── main.tsx            # React DOM root entry
    └── vite-env.d.ts       # Vite environment type declarations
```

## Environment Configuration

The environment file is located at:
`apps/manager-web/.env`

```env
# Backend API base URL (configurable for local dev or remote deployment server)
VITE_API_BASE_URL=http://localhost:8000/api/v1

# Set to false to fetch from real backend APIs, or true for static mock/demo data
VITE_USE_MOCK=false
```

To switch to a deployment server at any time, simply change `VITE_API_BASE_URL`:
```env
VITE_API_BASE_URL=https://api.your-deployment-domain.com/api/v1
```

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

## OpenAPI Features Implemented

1. **Backend Health Check**: `GET /health` polled automatically in `AppHeader` to show live connectivity status.
2. **Project Observatory & KPI Summaries**: `GET /projects`, `POST /projects`, and `GET /projects/{project_id}/summary`.
3. **Incident Radar & Telemetry**: `GET /projects/{project_id}/incidents`, `GET /incidents/{incident_id}`, and `GET /incidents/{incident_id}/observations`.
4. **Repair Approvals & Rejections**: `GET /incidents/{incident_id}/repair-proposals`, `GET /repair-proposals/{repair_id}/validation-runs`, `POST /repair-proposals/{repair_id}/approvals`, and `POST /repair-proposals/{repair_id}/rejection`.
5. **Contract Registry & Baselines**: `GET /projects/{project_id}/dependencies`, `POST /projects/{project_id}/dependencies`, and `GET /dependencies/{dependency_id}/baselines`.
6. **Active Drift Scanner**: `GET /projects/{project_id}/scans` and `POST /projects/{project_id}/scans` to trigger probe execution.
7. **Audit Activity Feed**: `GET /projects/{project_id}/activity`.

## Product & Lifecycle Rules

1. **Approval is Not Application**: Human review approval (`POST /repair-proposals/{id}/approvals`) registers review sign-off. The incident only transitions to `resolved` once the patch is applied and verified in the target environment by the developer or agent.
2. **Accessible Severity Indicators**: Severity levels (`critical`, `high`, `medium`, `low`) use distinctive textual and shape indicators in addition to high-contrast colors.
3. **Resilience & State Handling**: Every screen includes loading, empty, and actionable error states with Retry capabilities.
