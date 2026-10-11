import {
  Project,
  Dependency,
  Incident,
  RepairProposal,
  ValidationRun,
  ActivityEvent,
} from './types';

export const mockProjects: Project[] = [
  {
    id: 'proj_demo_shop',
    name: 'E-Commerce Storefront',
    description: 'Main customer-facing web application and checkout flows',
    repository_url: 'https://github.com/org/storefront',
    created_at: '2026-09-01T10:00:00Z',
    updated_at: '2026-10-10T12:00:00Z',
  },
  {
    id: 'proj_analytics_core',
    name: 'Analytics Pipeline',
    description: 'Event collection and business intelligence ingestion services',
    repository_url: 'https://github.com/org/analytics',
    created_at: '2026-09-15T08:30:00Z',
    updated_at: '2026-10-08T16:20:00Z',
  },
];

export const mockDependencies: Dependency[] = [
  {
    id: 'dep_demo_users',
    project_id: 'proj_demo_shop',
    name: 'Users API',
    kind: 'rest_api',
    base_url: 'https://api.users.internal/v1',
    version: '1.4.0',
    created_at: '2026-09-01T10:05:00Z',
  },
  {
    id: 'dep_payments_gateway',
    project_id: 'proj_demo_shop',
    name: 'Payments Gateway',
    kind: 'rest_api',
    base_url: 'https://api.stripe-mock.internal/v2',
    version: '2026-03-01',
    created_at: '2026-09-01T10:10:00Z',
  },
  {
    id: 'dep_inventory_v2',
    project_id: 'proj_demo_shop',
    name: 'Warehouse Inventory API',
    kind: 'rest_api',
    base_url: 'https://inventory.logistics.internal/api',
    version: '2.1.0',
    created_at: '2026-09-05T14:20:00Z',
  },
];

export const mockIncidents: Incident[] = [
  {
    id: 'inc_users_field_renamed',
    project_id: 'proj_demo_shop',
    dependency_id: 'dep_demo_users',
    title: 'Users API response field renamed',
    description: 'Expected field name was not found; display_name was observed.',
    severity: 'high',
    status: 'ready_for_review',
    source: 'detection-agent',
    fingerprint: 'users-api:name-to-display_name',
    confidence: 0.96,
    assignee_id: 'user_alex_manager',
    review_notes: 'Patch proposal verified against staging response samples.',
    evidence: {
      removed_fields: ['name'],
      added_fields: ['display_name'],
      type_changes: [],
      baseline: { name: 'Ada Lovelace' },
      observed: { display_name: 'Ada Lovelace' },
      diff_summary: 'Field "name" replaced with "display_name" in user profile response.',
    },
    affected_files: ['src/users/client.ts'],
    affected_workflows: ['user profile display', 'account settings dropdown'],
    created_at: '2026-10-10T14:23:10Z',
    updated_at: '2026-10-10T14:45:00Z',
    first_detected_at: '2026-10-10T14:23:10Z',
    last_observed_at: '2026-10-10T14:23:10Z',
  },
  {
    id: 'inc_inventory_pagination',
    project_id: 'proj_demo_shop',
    dependency_id: 'dep_inventory_v2',
    title: 'Warehouse API pagination keys changed from offset to cursor',
    description: 'Query parameter offset is deprecated; cursor-based pagination is now enforced.',
    severity: 'medium',
    status: 'validation_failed',
    source: 'detection-agent',
    fingerprint: 'inventory:offset-to-cursor',
    confidence: 0.88,
    assignee_id: null,
    review_notes: null,
    evidence: {
      removed_fields: ['offset', 'limit'],
      added_fields: ['cursor', 'page_size'],
      type_changes: [],
      baseline: { offset: 0, limit: 50 },
      observed: { cursor: 'eyJpZCI6MTB9', page_size: 50 },
      diff_summary: 'Offset parameters replaced with opaque cursor token.',
    },
    affected_files: ['src/inventory/stockFetcher.ts'],
    affected_workflows: ['catalog page inventory sync'],
    created_at: '2026-10-10T11:15:00Z',
    updated_at: '2026-10-10T13:30:00Z',
    first_detected_at: '2026-10-10T11:15:00Z',
    last_observed_at: '2026-10-10T11:15:00Z',
  },
  {
    id: 'inc_payments_auth_scheme',
    project_id: 'proj_demo_shop',
    dependency_id: 'dep_payments_gateway',
    title: 'Payments API Authorization header format change',
    description: 'HTTP 401 Unauthorized encountered during checkout webhook execution.',
    severity: 'critical',
    status: 'analyzing',
    source: 'detection-agent',
    fingerprint: 'payments:auth-scheme-migration',
    confidence: 0.99,
    assignee_id: 'user_dev_lead',
    review_notes: null,
    evidence: {
      removed_fields: ['Authorization: Bearer <token>'],
      added_fields: ['X-Api-Key: <key>'],
      type_changes: [],
      baseline: { auth_header: 'Bearer sec_live_123' },
      observed: { auth_header_required: 'X-Api-Key ak_live_123' },
      diff_summary: 'Gateway requires X-Api-Key header instead of Authorization Bearer header.',
    },
    affected_files: ['src/payments/stripeClient.ts', 'src/checkout/process.ts'],
    affected_workflows: ['credit card checkout', 'subscription renewal'],
    created_at: '2026-10-10T16:00:00Z',
    updated_at: '2026-10-10T16:10:00Z',
    first_detected_at: '2026-10-10T16:00:00Z',
    last_observed_at: '2026-10-10T16:05:00Z',
  },
  {
    id: 'inc_auth_service_blocked',
    project_id: 'proj_demo_shop',
    dependency_id: 'dep_demo_users',
    title: 'OAuth endpoint /oauth/token returned 502 Bad Gateway repeatedly',
    description: 'Third-party authentication provider unreachable; human intervention required.',
    severity: 'critical',
    status: 'blocked',
    source: 'detection-agent',
    fingerprint: 'auth:upstream-502-failure',
    confidence: 1.0,
    assignee_id: null,
    review_notes: 'Blocked by upstream provider outage. Incident logged with vendor support.',
    evidence: {
      removed_fields: [],
      added_fields: [],
      type_changes: [],
      baseline: { status: 200, response: 'ok' },
      observed: { status: 502, error: 'Bad Gateway' },
      diff_summary: 'Upstream server unreachable.',
    },
    affected_files: ['src/auth/provider.ts'],
    affected_workflows: ['single sign-on', 'token refresh'],
    created_at: '2026-10-09T09:00:00Z',
    updated_at: '2026-10-10T08:00:00Z',
    first_detected_at: '2026-10-09T09:00:00Z',
    last_observed_at: '2026-10-10T08:00:00Z',
  },
  {
    id: 'inc_analytics_timestamp',
    project_id: 'proj_demo_shop',
    dependency_id: 'dep_demo_users',
    title: 'Timestamp format shifted from Unix epoch integer to ISO-8601 string',
    description: 'Event timestamp returned as ISO string instead of millisecond integer.',
    severity: 'low',
    status: 'resolved',
    source: 'detection-agent',
    fingerprint: 'analytics:timestamp-iso',
    confidence: 0.92,
    assignee_id: 'user_alex_manager',
    review_notes: 'Patch applied in release v2.4.1. Verification suite passed.',
    evidence: {
      removed_fields: [],
      added_fields: [],
      type_changes: ['timestamp: int -> ISO8601 string'],
      baseline: { ts: 1712345678 },
      observed: { ts: '2026-10-05T12:00:00Z' },
      diff_summary: 'Field ts changed from integer to ISO string format.',
    },
    affected_files: ['src/telemetry/events.ts'],
    affected_workflows: ['user click tracking'],
    created_at: '2026-10-05T10:00:00Z',
    updated_at: '2026-10-06T15:20:00Z',
    first_detected_at: '2026-10-05T10:00:00Z',
    last_observed_at: '2026-10-05T10:00:00Z',
    resolved_at: '2026-10-06T15:20:00Z',
  },
];

export const mockRepairProposals: Record<string, RepairProposal> = {
  inc_users_field_renamed: {
    id: 'rep_users_field_renamed',
    incident_id: 'inc_users_field_renamed',
    status: 'ready_for_review',
    rationale: 'Update the consumer mapping to use display_name.',
    strategy: 'compatibility_adapter',
    risk_level: 'medium',
    confidence: 0.94,
    proposed_by: 'repair-agent',
    patch: {
      format: 'unified_diff',
      content: `--- a/src/users/client.ts
+++ b/src/users/client.ts
@@ -10,6 +10,6 @@ export interface User {
 }
 
 export function mapUserResponse(raw: any): User {
-  return { name: raw.name, email: raw.email };
+  return { name: raw.display_name ?? raw.name, email: raw.email };
 }`,
    },
    diff_preview: `--- a/src/users/client.ts
+++ b/src/users/client.ts
@@ -10,6 +10,6 @@ export interface User {
 }
 
 export function mapUserResponse(raw: any): User {
-  return { name: raw.name, email: raw.email };
+  return { name: raw.display_name ?? raw.name, email: raw.email };
 }`,
    created_at: '2026-10-10T14:30:00Z',
  },
  inc_inventory_pagination: {
    id: 'rep_inventory_pagination',
    incident_id: 'inc_inventory_pagination',
    status: 'validation_failed',
    rationale: 'Switch query parameters from offset/limit to cursor/page_size.',
    strategy: 'callsite_update',
    risk_level: 'high',
    confidence: 0.75,
    proposed_by: 'repair-agent',
    patch: {
      format: 'unified_diff',
      content: `--- a/src/inventory/stockFetcher.ts
+++ b/src/inventory/stockFetcher.ts
@@ -25,4 +25,4 @@ export async function fetchStock(token: string) {
-  return api.get('/inventory', { params: { offset: 0, limit: 50 } });
+  return api.get('/inventory', { params: { cursor: token, page_size: 50 } });
 }`,
    },
    diff_preview: `--- a/src/inventory/stockFetcher.ts
+++ b/src/inventory/stockFetcher.ts
@@ -25,4 +25,4 @@ export async function fetchStock(token: string) {
-  return api.get('/inventory', { params: { offset: 0, limit: 50 } });
+  return api.get('/inventory', { params: { cursor: token, page_size: 50 } });
 }`,
    created_at: '2026-10-10T12:00:00Z',
  },
};

export const mockValidationRuns: Record<string, ValidationRun> = {
  rep_users_field_renamed: {
    id: 'val_users_field_renamed',
    repair_id: 'rep_users_field_renamed',
    status: 'passed',
    result: 'passed',
    tests_total: 3,
    tests_passed: 3,
    tests_failed: 0,
    summary: 'All 3 user profile unit and integration tests passed.',
    test_command: 'npm test -- --grep "user client mapping"',
    output: `PASS src/users/client.test.ts
  ✓ maps legacy name field properly (14ms)
  ✓ maps new display_name field properly (8ms)
  ✓ gracefully falls back when both exist (6ms)

Test Suites: 1 passed, 1 total
Tests:       3 passed, 3 total`,
    started_at: '2026-10-10T14:31:00Z',
    completed_at: '2026-10-10T14:31:45Z',
    created_at: '2026-10-10T14:31:00Z',
  },
  rep_inventory_pagination: {
    id: 'val_inventory_pagination',
    repair_id: 'rep_inventory_pagination',
    status: 'failed',
    result: 'failed',
    tests_total: 3,
    tests_passed: 2,
    tests_failed: 1,
    summary: 'One test still expects the old field.',
    test_command: 'npm test -- --grep "inventory fetcher"',
    output: `FAIL src/inventory/stockFetcher.test.ts
  ✓ validates cursor parameter encoding (12ms)
  ✓ rejects null cursor payload (9ms)
  ✕ verifies legacy pagination fallback (24ms)

  AssertionError: expected params to include "offset"
    at Object.<anonymous> (src/inventory/stockFetcher.test.ts:44:18)

Test Suites: 1 failed, 1 total
Tests:       1 failed, 2 passed, 3 total`,
    started_at: '2026-10-10T12:05:00Z',
    completed_at: '2026-10-10T12:05:30Z',
    created_at: '2026-10-10T12:05:00Z',
  },
};

export const mockActivity: ActivityEvent[] = [
  {
    id: 'act_10',
    project_id: 'proj_demo_shop',
    actor_id: 'agent_detection',
    event_type: 'incident_detected',
    message: 'Detected breaking schema rename in Users API: name -> display_name',
    entity_type: 'incident',
    entity_id: 'inc_users_field_renamed',
    created_at: '2026-10-10T14:23:10Z',
  },
  {
    id: 'act_11',
    project_id: 'proj_demo_shop',
    actor_id: 'agent_repair',
    event_type: 'repair_proposed',
    message: 'Generated candidate patch with compatibility_adapter strategy',
    entity_type: 'repair_proposal',
    entity_id: 'rep_users_field_renamed',
    created_at: '2026-10-10T14:30:00Z',
  },
  {
    id: 'act_12',
    project_id: 'proj_demo_shop',
    actor_id: 'agent_validator',
    event_type: 'validation_completed',
    message: 'Automated test suite passed (3/3 tests passed)',
    entity_type: 'validation_run',
    entity_id: 'val_users_field_renamed',
    created_at: '2026-10-10T14:31:45Z',
  },
  {
    id: 'act_13',
    project_id: 'proj_demo_shop',
    actor_id: 'agent_detection',
    event_type: 'incident_detected',
    message: 'Detected breaking change in Payments Gateway Authorization header',
    entity_type: 'incident',
    entity_id: 'inc_payments_auth_scheme',
    created_at: '2026-10-10T16:00:00Z',
  },
];
