export type DetectionMode = 'algorithmic' | 'ai' | 'hybrid';
export type Compatibility = 'breaking' | 'potentially_breaking' | 'non_breaking' | 'unknown';
export type Severity = 'critical' | 'high' | 'medium' | 'low';
export type DetectionSource = 'algorithmic' | 'ai' | 'hybrid';

export interface DetectionFinding {
  id: string;
  rule_id: string;
  fingerprint: string;
  compatibility: Compatibility;
  severity: Severity;
  path: string;
  method: string | null;
  schema_location: string;
  previous_value?: unknown;
  current_value?: unknown;
  message: string;
  evidence: Record<string, unknown>;
  confidence: number;
  source: DetectionSource;
  review_required: boolean;
  ai_reasoning?: string | null;
  created_at?: string;
}

export interface DiffSummary {
  total_findings: number;
  breaking_count: number;
  potentially_breaking_count: number;
  non_breaking_count: number;
  unknown_count: number;
  by_severity: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
}

export interface DetectionResult {
  success: boolean;
  mode: DetectionMode;
  findings: DetectionFinding[];
  summary: DiffSummary;
  ai_status?: string | null;
  ai_error?: string | null;
  fallback_triggered: boolean;
  execution_time_ms: number;
  timestamp: string;
}

export interface DetectionRunOptions {
  baselinePath: string;
  currentPath: string;
  mode?: DetectionMode;
  provider?: string;
  backendUrl?: string;
  projectId?: string;
  dependencyId?: string;
  timeoutSeconds?: number;
  cancellationToken?: import('vscode').CancellationToken;
}

