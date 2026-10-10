# Finding Contract Specification (v1.0.0)

## Overview
This specification defines the canonical schema for findings produced by the Dependency Guardian Detection Agent across all detection modes (`algorithmic`, `ai`, and `hybrid`).

## Schema Location
The authoritative JSON Schema is defined at [`contracts/finding-v1.json`](./finding-v1.json).

## Core Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes | Unique UUID for the specific finding occurrence. |
| `rule_id` | string | Yes | Deterministic rule identifier (e.g. `RULE-PATH-REMOVED`). |
| `fingerprint` | string | Yes | Stable collision-resistant identifier for deduplication across scans. |
| `compatibility` | string | Yes | `breaking`, `potentially_breaking`, `non_breaking`, or `unknown`. |
| `severity` | string | Yes | `critical`, `high`, `medium`, or `low`. Orthogonal to compatibility. |
| `path` | string | Yes | OpenAPI endpoint path (e.g. `/users/{id}`). |
| `method` | string or null | Yes | HTTP method in uppercase (`GET`, `POST`, etc.) or null if path-level. |
| `schema_location` | string | Yes | JSON pointer / locator of the change in the OpenAPI document. |
| `previous_value` | any | No | Value or schema chunk in the baseline specification. |
| `current_value` | any | No | Value or schema chunk in the current specification. |
| `message` | string | Yes | Clear explanation based directly on verified evidence. |
| `evidence` | object | Yes | Structured dictionary with details of the diff or missing construct. |
| `confidence` | number (0.0-1.0) | Yes | Deterministic checks yield `1.0`. AI reasoning may vary. |
| `source` | string | Yes | `algorithmic`, `ai`, or `hybrid`. |
| `review_required` | boolean | Yes | Whether human engineer triage is requested before automated repair. |
| `ai_reasoning` | string or null | No | Contextual reasoning or impact notes supplied by AI. |
| `created_at` | string (ISO-8601) | No | Timestamp of detection. |

---

## Compatibility vs. Severity

- **Compatibility** answers: *Does this break backward compatibility for existing callers conforming to the previous spec?*
  - `breaking`: Strictly backward-incompatible (e.g., removed endpoint, removed response field, newly required request parameter).
  - `potentially_breaking`: May break callers depending on runtime payloads (e.g., added request header without default, enum value removed from response).
  - `non_breaking`: Safe additive change (e.g., new optional request parameter, newly added response field, new optional path).
  - `unknown`: Semantic or unparsed changes requiring manual verification.
- **Severity** answers: *What is the operational urgency or blast radius?*
  - `critical`, `high`, `medium`, `low`.
  - Orthogonal: A non-breaking additive field is `low` severity; removing a deprecation header might be `medium`; deleting a primary authentication endpoint is `critical`.

---

## Stable Rule Identifiers

- `RULE-PATH-REMOVED`: Entire API path deleted.
- `RULE-METHOD-REMOVED`: HTTP operation removed from an existing path.
- `RULE-RESPONSE-FIELD-REMOVED`: Existing property removed from a success response schema.
- `RULE-REQUEST-FIELD-REMOVED`: Existing property removed from a request body schema.
- `RULE-FIELD-TYPE-CHANGED`: Property datatype changed incompatibly.
- `RULE-REQUIRED-PARAM-ADDED`: New parameter added with `required: true`.
- `RULE-REQUIRED-FIELD-ADDED`: New schema property added to `required` list in request body.
- `RULE-ENUM-VALUE-REMOVED`: Allowable enum value removed from response or request enum list changed.
- `RULE-STATUS-CODE-REMOVED`: Documented response status code removed.
- `RULE-FIELD-ADDED-OPTIONAL`: Additive non-breaking property introduced.

---

## Deduplication & Merge Policy (Hybrid Mode)

In `hybrid` mode:
1. Algorithmic findings provide the ground truth (`source="algorithmic"`, `confidence=1.0`).
2. AI may enrich findings matching the same `fingerprint` with `ai_reasoning`.
3. AI cannot convert a confirmed structural difference (`breaking`) into `non_breaking`.
4. If AI proposes novel findings not found by the deterministic engine:
   - They must be validated against `finding-v1.json`.
   - Their source is labeled `ai` and `confidence` is capped according to model self-assessment.
   - If evidence is missing, compatibility must be classified as `unknown` or `potentially_breaking` with `review_required=true`.

---

## Versioning Strategy

- Major versions (`v1`, `v2`) are path-isolated (e.g., `finding-v1.json`).
- Clients check the schema version header or property.
- Backward-compatible additions (optional fields) increment minor version without breaking existing consumers.
