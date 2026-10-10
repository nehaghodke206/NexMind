# Manager Web Notes & Decisions

## Contract Gaps and Inconsistencies

1. **Endpoint Paths Discrepancy**:
   - `contracts/api-contract.md` specifies `/api/v1/incidents/{incident_id}/repairs` and `/api/v1/repairs/{repair_id}/approve` (also `/validate`, `/apply-result`).
   - `docs/open-api.yaml` specifies `/incidents/{incident_id}/repair-proposals`, `/repair-proposals/{repair_id}`, `/repair-proposals/{repair_id}/approvals`, `/repair-proposals/{repair_id}/validation-runs`, and `/repair-proposals/{repair_id}/applications`.
   - *Resolution*: The typed API client supports both endpoint patterns through normalized adapter methods.

2. **Incident and Repair Lifecycle Statuses**:
   - `contracts/api-contract.md` lists granular agent statuses: `detected`, `analyzing`, `repair_proposed`, `validating`, `validation_failed`, `ready_for_review`, `approved`, `resolved`, `blocked`.
   - `docs/open-api.yaml` lists standard issue triage statuses: `open`, `triaged`, `in_progress`, `awaiting_review`, `resolved`, `dismissed`.
   - `RepairStatus` in `api-contract.md`: `proposed`, `validating`, `validation_passed`, `validation_failed`, `approved`, `rejected`, `applied`.
   - `RepairStatus` in `open-api.yaml`: `proposed`, `validating`, `ready_for_review`, `approved`, `rejected`, `applied`, `failed`.
   - *Resolution*: TypeScript union types accommodate both sets of status values so that mock payloads and backend responses are both valid and render correctly.

3. **Evidence & Patch Structure**:
   - `contracts/examples/incident.json` features a rich `evidence` object with `removed_fields`, `added_fields`, `type_changes`, `baseline`, and `observed`, plus `fingerprint` and `source`.
   - `docs/open-api.yaml` stores scan observations separately or in unstructured metadata.
   - `contracts/examples/repair-proposal.json` uses `patch: { format: "unified_diff", content: "..." }` and `risk_level: "medium"`, whereas `open-api.yaml` uses `diff_preview: string` and `strategy: enum`.
   - *Resolution*: UI components normalize these models so either format displays cleanly without crashes.

4. **Identifier Types**:
   - Contract examples use strings (`"dep_demo_users"`), `open-api.yaml` specifies UUID strings, and `database-design.mmd` specifies integer IDs.
   - *Resolution*: Identifier types are defined as `string` in TypeScript (strings or stringified numbers).

5. **Approval vs Application Rule**:
   - "Approval is not application." Human review approval marks the proposal as approved, but the incident remains open/awaiting application until the local agent or developer applies the change and reports application confirmation to the backend.
