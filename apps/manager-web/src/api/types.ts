export type Severity = 'low' | 'medium' | 'high' | 'critical';

export type IncidentStatus =
  | 'detected'
  | 'analyzing'
  | 'repair_proposed'
  | 'validating'
  | 'validation_failed'
  | 'ready_for_review'
  | 'approved'
  | 'resolved'
  | 'blocked'
  | 'open'
  | 'triaged'
  | 'in_progress'
  | 'awaiting_review'
  | 'dismissed';

export type RepairStatus =
  | 'proposed'
  | 'validating'
  | 'validation_passed'
  | 'validation_failed'
  | 'ready_for_review'
  | 'approved'
  | 'rejected'
  | 'applied'
  | 'failed';

export type ValidationStatus =
  | 'queued'
  | 'running'
  | 'passed'
  | 'failed'
  | 'blocked'
  | 'error';

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export interface HealthStatus {
  status: string;
}

export interface ProjectSummary {
  project_id: string;
  dependency_count: number;
  open_incident_count: number;
  pending_review_count: number;
  validation_pass_count: number;
  validation_fail_count: number;
  last_scan_at?: string | null;
}

export interface IncidentEvidence {
  removed_fields?: string[];
  added_fields?: string[];
  type_changes?: Array<{ field: string; from: string; to: string } | string>;
  baseline?: Record<string, unknown> | unknown;
  observed?: Record<string, unknown> | unknown;
  diff_summary?: string;
}

export interface Incident {
  id: string;
  project_id: string;
  dependency_id: string;
  title: string;
  description?: string | null;
  change_type?: string;
  severity: Severity;
  status: IncidentStatus;
  source?: string;
  fingerprint?: string;
  confidence?: number | null;
  assignee_id?: string | null;
  review_notes?: string | null;
  evidence?: IncidentEvidence | null;
  affected_files: string[];
  affected_workflows: string[];
  created_at: string;
  updated_at: string;
  first_detected_at?: string;
  last_observed_at?: string;
  resolved_at?: string | null;
}

export interface PatchPayload {
  format: 'unified_diff' | string;
  content: string;
}

export interface RepairProposal {
  id: string;
  incident_id: string;
  status: RepairStatus;
  rationale: string;
  strategy?: string;
  diff_preview?: string;
  patch?: PatchPayload;
  proposed_changes?: Record<string, unknown>;
  risk_level?: RiskLevel;
  confidence?: number | null;
  proposed_by?: string;
  created_by?: string | null;
  created_at: string;
  updated_at?: string;
}

export interface ValidationDetails {
  tests_total?: number;
  tests_passed?: number;
  tests_failed?: number;
  summary?: string;
  [key: string]: unknown;
}

export interface ValidationRun {
  id: string;
  repair_id: string;
  status: ValidationStatus;
  result?: 'passed' | 'failed' | string;
  test_command?: string | null;
  output?: string | null;
  summary?: string;
  tests_total?: number;
  tests_passed?: number;
  tests_failed?: number;
  details?: ValidationDetails | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
}

export interface RepairApproval {
  id: string;
  repair_id: string;
  reviewer_id: string;
  decision: 'approved' | 'rejected';
  comment?: string | null;
  decided_at: string;
}

export interface Project {
  id: string;
  name: string;
  description?: string | null;
  repository_url?: string | null;
  default_branch?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  description?: string;
  repository_url?: string;
  default_branch?: string;
}

export interface Dependency {
  id: string;
  project_id: string;
  name: string;
  kind?: string;
  base_url?: string | null;
  version?: string | null;
  configuration?: Record<string, unknown>;
  created_at: string;
}

export interface DependencyCreate {
  name: string;
  kind: 'rest_api' | 'sdk' | 'package' | 'mcp_tool' | 'other';
  base_url?: string;
}

export interface Baseline {
  id: string;
  dependency_id: string;
  version: number;
  contract: Record<string, unknown>;
  source?: 'manual' | 'scan' | 'imported';
  created_by?: string | null;
  created_at: string;
}

export interface ScanRun {
  id: string;
  project_id: string;
  dependency_id?: string | null;
  initiated_by?: string | null;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  summary?: string | null;
  error_message?: string | null;
  started_at: string;
  completed_at?: string | null;
}

export interface Observation {
  id: string;
  scan_id: string;
  dependency_id: string;
  observation_type: 'response_shape' | 'status_code' | 'latency' | 'pagination' | 'tool_schema' | 'semantic_change' | 'other';
  endpoint?: string | null;
  method?: string | null;
  observed_at: string;
  payload: Record<string, unknown>;
  fingerprint?: string | null;
}

export interface ProjectMember {
  id: string;
  project_id: string;
  user_id: string;
  display_name: string;
  email: string;
  role: 'owner' | 'maintainer' | 'developer' | 'viewer';
  joined_at: string;
}

export interface ActivityEvent {
  id: string;
  project_id: string;
  actor_id?: string | null;
  event_type: string;
  message: string;
  entity_type?: string;
  entity_id?: string;
  created_at: string;
}

export interface IncidentFilterOptions {
  severity?: Severity;
  status?: IncidentStatus;
  dependency_id?: string;
  search?: string;
}
