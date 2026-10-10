
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

