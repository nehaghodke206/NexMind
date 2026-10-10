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
  created_at: string;
  updated_at: string;
}

export interface Dependency {
  id: string;
  project_id: string;
  name: string;
  kind?: string;
  base_url?: string | null;
  version?: string | null;
  created_at: string;
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
