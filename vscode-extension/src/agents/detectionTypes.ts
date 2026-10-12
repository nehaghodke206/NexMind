import * as vscode from "vscode";

export type ExecutionState = "idle" | "running" | "succeeded" | "failed" | "canceled";

export interface ScanProgressEvent {
  type?: "progress";
  phase:
    | "starting"
    | "discovering_files"
    | "inspecting_dependencies"
    | "analyzing_source"
    | "checking_specifications"
    | "evaluating_tests"
    | "generating_reports"
    | "completed"
    | string;
  message: string;
  filesDiscovered?: number;
  filesProcessed?: number;
  totalFiles?: number;
  currentFile?: string;
  dependenciesCount?: number;
  integrationsCount?: number;
  endpointsCount?: number;
  discrepanciesCount?: number;
  coveragePercentage?: number;
  elapsedSeconds?: number;
  quietWarning?: boolean;
}

export interface CodebaseScanOptions {
  repositoryPath: string;
  outputDir?: string;
  mode?: "algorithmic" | "ai" | "hybrid";
  enrichOpenApi?: boolean;
  timeoutSeconds?: number;
  cancellationToken?: vscode.CancellationToken;
  onProgress?: (progress: ScanProgressEvent) => void;
  onLog?: (line: string) => void;
  syncBackend?: boolean;
  projectId?: string;
}

export interface ParameterDoc {
  name: string;
  in_location: string;
  param_type: string;
  required: boolean;
  default?: any;
  description?: string;
}

export interface ResponseDoc {
  status_code: number;
  description?: string;
  schema_name?: string;
  fields?: any[];
}

export interface EndpointDoc {
  http_method: string;
  route_path: string;
  summary?: string;
  description?: string;
  parameters: ParameterDoc[];
  responses: ResponseDoc[];
  auth_and_authz?: string;
  source_file?: string;
  line_number?: number;
  handler_function?: string;
  relevant_dependencies: string[];
  existing_tests: string[];
  discovery_method: "framework_ast" | "openapi_spec" | "hybrid" | string;
  confidence_level?: number;
}

export interface ImportLocation {
  file: string;
  line: number;
  statement: string;
}

export interface DependencyDoc {
  package_name: string;
  ecosystem: string;
  declared_constraint?: string;
  resolved_version?: string;
  is_direct: boolean;
  is_used: boolean;
  purpose?: string;
  import_locations: ImportLocation[];
  manifest_file?: string;
}

export interface ExternalIntegrationDoc {
  integration_type: string;
  service_name: string;
  target_url_or_host?: string;
  file_path: string;
  line_number: number;
  code_snippet: string;
  operations: string[];
}

export interface DiscrepancyDoc {
  discrepancy_type: "undocumented_endpoint" | "ghost_endpoint" | "parameter_mismatch" | "response_mismatch" | string;
  endpoint_path: string;
  method: string;
  description: string;
  code_evidence?: string;
  spec_evidence?: string;
  severity?: string;
  fingerprint?: string;
  message?: string;
  details?: string;
  type?: string;
  endpoint?: string;
  path?: string;
}

export interface TestCoverageSummary {
  total_endpoints: number;
  tested_endpoints: number;
  untested_endpoints: number;
  coverage_percentage: number;
  endpoint_coverage_map: Record<string, string[]>;
  integration_tests_found: string[];
}

export interface ScannerMetadata {
  scanner_name: string;
  scanner_version: string;
  scanned_path: string;
  scan_timestamp: string;
  languages_detected: string[];
  frameworks_detected: string[];
  total_files_scanned: number;
  openapi_specs_found: string[];
}

export interface RepositoryInventoryResult {
  metadata: ScannerMetadata;
  dependencies: DependencyDoc[];
  unused_dependencies: string[];
  integrations: ExternalIntegrationDoc[];
  endpoints: EndpointDoc[];
  discrepancies: DiscrepancyDoc[];
  test_coverage: TestCoverageSummary;
  ai_insights?: Record<string, any>;
  output_dir?: string;
  undocumented_endpoints?: any[];
  discovered_endpoints?: number;
}

export type DetectionProvenance = "static_ast" | "contract_diff" | "live_probe" | "ai_inferred";

export interface ContractFinding {
  id: string;
  rule_id: string;
  compatibility: "breaking" | "potentially_breaking" | "non_breaking" | "unknown";
  severity: "critical" | "high" | "medium" | "low";
  path: string;
  method?: string | null;
  message: string;
  evidence: Record<string, any>;
  provenance?: DetectionProvenance;
  confidence?: number;
  recommended_action?: string | null;
  ai_reasoning?: string | null;
  impact?: Record<string, any>;
  fingerprint?: string;
}

export type ProbeStatus =
  | "reachable"
  | "auth_failure"
  | "client_error"
  | "server_failure"
  | "unreachable"
  | "contract_mismatch"
  | "security_blocked";

export interface LiveProbeResult {
  endpoint_id: string;
  service_name: string;
  url: string;
  method: string;
  status_code: number;
  status: ProbeStatus;
  latency_ms: number;
  error_message?: string | null;
  fingerprint: string;
  safe_headers?: Record<string, string>;
  structural_schema?: Record<string, any>;
  observed_at: string;
  findings?: ContractFinding[];
  provenance?: DetectionProvenance;
}

export interface LiveValidationReport {
  total_probes: number;
  reachable_count: number;
  auth_failure_count: number;
  client_error_count: number;
  server_failure_count: number;
  unreachable_count: number;
  contract_mismatch_count: number;
  security_blocked_count: number;
  duration_seconds: number;
  results: LiveProbeResult[];
  findings: ContractFinding[];
  config_source?: string | null;
  mode: "algorithmic" | "ai" | "hybrid" | string;
  ai_status?: string | null;
  ai_provider?: string | null;
  ai_model?: string | null;
  ai_error?: string | null;
  timestamp: string;
}

export interface LiveValidationOptions {
  configPath?: string;
  url?: string;
  method?: string;
  serviceName?: string;
  authEnvVar?: string;
  expectedStatus?: number;
  expectedFields?: string[];
  mode?: "algorithmic" | "ai" | "hybrid";
  timeoutSeconds?: number;
  concurrency?: number;
  maxRequests?: number;
  outputFile?: string;
  cancellationToken?: vscode.CancellationToken;
  onProgress?: (progress: ScanProgressEvent) => void;
  onLog?: (line: string) => void;
}

export interface FindingSummary {
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

export interface ContractDriftOptions {
  baselinePath?: string;
  currentPath?: string;
  mode?: "algorithmic" | "ai" | "hybrid";
  projectId?: string;
  dependencyId?: string;
  syncBackend?: boolean;
  proposeRepairs?: boolean;
  testCmd?: string;
  outputFile?: string;
  insightsOutputFile?: string;
  timeoutSeconds?: number;
  cancellationToken?: vscode.CancellationToken;
}

export interface ContractDriftResult {
  mode: string;
  execution_time_ms: number;
  success: boolean;
  findings: ContractFinding[];
  summary: FindingSummary;
  ai_provider?: string | null;
  ai_model?: string | null;
  ai_status?: string | null;
  ai_error?: string | null;
  ai_insights?: Record<string, any> | null;
  backend_sync?: {
    synced: boolean;
    scan_id?: string;
    observations_count?: number;
    incidents_created?: number;
    reason?: string;
  };
}

export interface DetectionStateEvent {
  capability: "codebase_scan" | "contract_drift" | "live_validation" | "unified_analysis";
  state: ExecutionState;
  error?: string;
  progress?: ScanProgressEvent;
  codebaseResult?: RepositoryInventoryResult;
  driftResult?: ContractDriftResult;
  liveValidationResult?: LiveValidationReport;
}
