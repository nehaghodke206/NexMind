/**
 * Client for communicating with the Dependency Guardian backend service.
 */

import { getGuardianConfig, normalizeBackendUrl } from "../config";

export interface DependencyProbe {
  id: string;
  method: string;
  path: string;
  expected_contract?: string;
  known_values?: Record<string, any>;
}

export interface DependencyService {
  id: string;
  name: string;
  base_url: string;
  probes: DependencyProbe[];
}

export interface ChangeItem {
  id: string;
  scan_id: string;
  dependency_id: string;
  probe_id: string;
  change_type: string;
  severity: "low" | "medium" | "high" | "blocked" | "critical";
  evidence: Record<string, any>;
  status: string;
  created_at: string;
  affected_files?: string[];
  affected_workflows?: string[];
  provenance?: string;
  confidence?: number;
  fingerprint?: string;
  occurrence_count?: number;
  recommended_action?: string;
  review_notes?: string;
  resolution_notes?: string;
  reopened_at?: string;
}

export interface ProjectBaseline {
  id: string;
  project_id: string;
  version_number: number;
  version?: number;
  version_tag: string;
  description?: string;
  contracts: Record<string, any>;
  inventory: Record<string, any>;
  source_scan_id?: string;
  content_hash?: string;
  created_by?: string;
  is_active: boolean;
  is_promoted: boolean;
  promoted_at?: string;
  promoted_by?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectBaselineListResponse {
  items: ProjectBaseline[];
  total: number;
  active_baseline?: ProjectBaseline | null;
}

export interface ProjectBaselineCompareResponse {
  project_id: string;
  base_version: number;
  target_version: number;
  base_id: string;
  target_id: string;
  endpoints_added: any[];
  endpoints_removed: any[];
  endpoints_modified: any[];
  contract_diffs: Record<string, any>;
  summary: Record<string, any>;
}

export interface ScanRun {
  id: string;
  project_id: string;
  dependency_id?: string;
  initiated_by?: string;
  scan_type: string;
  detection_mode?: string;
  capabilities_executed: string[];
  status: string;
  duration_seconds?: number;
  summary_counts: Record<string, any>;
  summary?: string;
  error_message?: string;
  is_local: boolean;
  sync_status: string;
  client_run_id?: string;
  started_at: string;
  completed_at?: string;
  created_at?: string;
}

export interface ScanIngestPayload {
  client_run_id?: string;
  scan_type?: string;
  detection_mode?: string;
  capabilities_executed?: string[];
  duration_seconds?: number;
  summary_counts?: Record<string, any>;
  findings?: any[];
  inventory?: any;
  status?: string;
  error_message?: string;
  scanner_version?: string;
  repository_revision?: string;
  initiated_by?: string;
  started_at?: string;
  completed_at?: string;
}

export interface IncidentEvent {
  id: string;
  incident_id: string;
  event_type: string;
  actor_id?: string;
  from_status?: string;
  to_status?: string;
  message: string;
  metadata_json?: Record<string, any>;
  created_at: string;
}

export interface BackendIncident {
  id: string;
  project_id: string;
  dependency_id: string;
  title: string;
  description: string;
  change_type: string;
  severity: "low" | "medium" | "high" | "critical" | "blocked";
  status: "open" | "acknowledged" | "resolved" | "reopened";
  provenance: string;
  confidence?: number;
  fingerprint: string;
  occurrence_count: number;
  recommended_action?: string;
  review_notes?: string;
  resolution_notes?: string;
  affected_workflows?: string[];
  affected_files?: string[];
  first_detected_at?: string;
  last_observed_at?: string;
  acknowledged_at?: string;
  acknowledged_by?: string;
  resolved_at?: string;
  reopened_at?: string;
  last_scan_id?: string;
  evidence_summary?: string;
  created_at: string;
  updated_at: string;
}

export interface ImpactItem {
  id?: string;
  workflow_id: string;
  workflow_name: string;
  source_files: string[];
  tests: string[];
  affected_fields: string[];
  reason: string;
}

export interface RepairProposal {
  id: string;
  change_id: string;
  repair_type: string;
  target_file: string;
  original_code_snippet: string;
  proposed_code_snippet: string;
  diff: string;
  evidence: Record<string, any>;
  assumptions: string[];
  confidence: number;
  status: string;
  created_at: string;
  error_message?: string;
  likely_root_cause?: string;
  affected_symbols?: string[];
  rationale?: string;
  risks?: string[];
  alternatives_considered?: string[];
  line_ranges?: string[];
  suggested_validation_command?: string;
  proposed_changes?: Record<string, any>;
  patch_hash?: string;
  client_repair_id?: string;
  repair_id?: string;
}

export interface ValidationResult {
  id: string;
  repair_id: string;
  command: string;
  exit_code: number;
  output_summary: string;
  duration_ms: number;
  status: "passed" | "failed";
  started_at: string;
}

export class GuardianClient {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    this.baseUrl = normalizeBackendUrl(baseUrl || getGuardianConfig().backendUrl);
  }

  public setBaseUrl(url: string) {
    this.baseUrl = normalizeBackendUrl(url);
  }

  public getBaseUrl(): string {
    return this.baseUrl;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
    // Support root paths like /health or /api/health
    const url = endpoint.startsWith("http")
      ? endpoint
      : `${this.baseUrl}${cleanEndpoint}`;

    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...(options.headers || {}),
      },
    });

    if (!res.ok) {
      let errorDetail = res.statusText;
      try {
        const errorJson = (await res.json()) as any;
        errorDetail = errorJson.message || errorJson.detail || errorDetail;
      } catch {}
      throw new Error(`Backend API error (${res.status}): ${errorDetail}`);
    }

    return (await res.json()) as T;
  }

  async getHealth(): Promise<{ status: string; product: string; version: string; workspace_root: string }> {
    // Try both root /health and /api/v1/health
    const candidates = [
      `${this.baseUrl}/health`,
      this.baseUrl.replace(/\/api\/v1\/?$/, "/health"),
      `${this.baseUrl.replace(/\/api\/v1\/?$/, "")}/api/health`,
    ];

    let lastError: any = null;
    for (const url of candidates) {
      try {
        const res = await fetch(url, { headers: { Accept: "application/json" } });
        if (res.ok) {
          const data = (await res.json()) as any;
          return {
            status: data.status || "ok",
            product: data.product || "Dependency Guardian",
            version: data.version || "0.1.0",
            workspace_root: data.workspace_root || "",
          };
        }
      } catch (err) {
        lastError = err;
      }
    }

    throw lastError || new Error("Backend service is unreachable.");
  }

  async getProjects(): Promise<any[]> {
    try {
      const data = await this.request<any>("/projects");
      return Array.isArray(data) ? data : data.items || [];
    } catch {
      return [];
    }
  }

  async initializeProject(name: string = "Default Project"): Promise<any> {
    try {
      const projects = await this.getProjects();
      if (projects.length > 0) {
        return { project_id: projects[0].id, dependencies_count: 1 };
      }
      const created = await this.request<any>("/projects", {
        method: "POST",
        body: JSON.stringify({ name }),
      });
      return { project_id: created.id, dependencies_count: 0 };
    } catch (err: any) {
      // Fallback for prototype server if present
      try {
        return await this.request<any>("/api/projects/initialize", { method: "POST" });
      } catch {
        throw err;
      }
    }
  }

  async createProject(name: string, description?: string): Promise<any> {
    return this.request<any>("/projects", {
      method: "POST",
      body: JSON.stringify({ name, description: description || "Project registered via VS Code" }),
    });
  }

  async getProjectDependencies(projectId: string): Promise<any[]> {
    try {
      const data = await this.request<any>(`/projects/${projectId}/dependencies`);
      return Array.isArray(data) ? data : data.items || [];
    } catch {
      return [];
    }
  }

  async createDependency(
    projectId: string,
    dependency: { name: string; kind?: string; base_url?: string; version?: string; configuration?: Record<string, any> }
  ): Promise<any> {
    return this.request<any>(`/projects/${projectId}/dependencies`, {
      method: "POST",
      body: JSON.stringify({
        name: dependency.name,
        kind: dependency.kind || "rest_api",
        base_url: dependency.base_url || null,
        version: dependency.version || null,
        configuration: dependency.configuration || {},
      }),
    });
  }

  async getServices(): Promise<DependencyService[]> {
    try {
      const projects = await this.getProjects();
      if (projects.length === 0) {
        return [];
      }
      const projectId = projects[0].id;
      const deps = await this.request<any[]>(`/projects/${projectId}/dependencies`);
      return (deps || []).map((d: any) => ({
        id: d.id,
        name: d.name,
        base_url: d.base_url || d.target_url || "http://localhost",
        probes: (d.probes || []).map((p: any) => ({
          id: p.id || p.path,
          method: p.method || "GET",
          path: p.path || "/",
          expected_contract: p.expected_contract,
        })),
      }));
    } catch {
      // Prototype fallback
      try {
        const data = await this.request<{ services: DependencyService[] }>("/services");
        return data.services || [];
      } catch {
        return [];
      }
    }
  }

  async createBaseline(
    projectId?: string,
    data?: {
      version_tag?: string;
      description?: string;
      contracts?: Record<string, any>;
      inventory?: Record<string, any>;
      notes?: string;
    }
  ): Promise<ProjectBaseline> {
    const config = getGuardianConfig();
    let targetProjectId = projectId || config.projectId;
    if (!targetProjectId) {
      const projects = await this.getProjects();
      if (projects && projects.length > 0) {
        targetProjectId = projects[0].id;
      }
    }

    if (targetProjectId) {
      return this.createProjectBaseline(targetProjectId, {
        version_tag: data?.version_tag || `v${Date.now()}`,
        description: data?.description || "Captured baseline snapshot from VS Code Extension",
        contracts: data?.contracts || {},
        inventory: data?.inventory || {},
        notes: data?.notes,
      });
    }

    // Top-level baseline endpoint fallback
    return this.request<ProjectBaseline>("/baselines", {
      method: "POST",
      body: JSON.stringify({
        version_tag: data?.version_tag || `v${Date.now()}`,
        description: data?.description || "Captured baseline snapshot from VS Code Extension",
        contracts: data?.contracts || {},
        inventory: data?.inventory || {},
        notes: data?.notes,
      }),
    });
  }

  async runScan(): Promise<{
    scan_id: string;
    status: string;
    services_checked: number;
    changes_detected: number;
    changes: ChangeItem[];
  }> {
    // Queries changes directly
    const changes = await this.getChanges();
    return {
      scan_id: `scan_${Date.now()}`,
      status: "completed",
      services_checked: (await this.getServices()).length || 1,
      changes_detected: changes.length,
      changes,
    };
  }

  async getChanges(scanId?: string): Promise<ChangeItem[]> {
    try {
      // Try real backend incidents
      const projects = await this.getProjects();
      let incidents: any[] = [];

      if (projects.length > 0) {
        const pId = projects[0].id;
        const incResp = await this.request<any>(`/projects/${pId}/incidents`);
        incidents = Array.isArray(incResp) ? incResp : incResp.items || [];
      } else {
        const incResp = await this.request<any>("/incidents");
        incidents = Array.isArray(incResp) ? incResp : incResp.items || [];
      }

      return incidents.map((inc: any) => ({
        id: inc.id,
        scan_id: inc.scan_id || inc.last_scan_id || "",
        dependency_id: inc.dependency_id || inc.title || "dependency",
        probe_id: inc.fingerprint || inc.id,
        change_type: inc.source || inc.change_type || inc.title || "contract_drift",
        severity: (inc.severity || "high").toLowerCase(),
        evidence: inc.evidence || (inc.metadata_json && inc.metadata_json.evidence) || {},
        status: inc.status || "open",
        created_at: inc.created_at || new Date().toISOString(),
        affected_files: inc.affected_files || [],
        affected_workflows: inc.affected_workflows || [],
        provenance: inc.provenance || "detector",
        confidence: inc.confidence,
        fingerprint: inc.fingerprint,
        occurrence_count: inc.occurrence_count || 1,
        recommended_action: inc.recommended_action,
        review_notes: inc.review_notes,
        resolution_notes: inc.resolution_notes,
        reopened_at: inc.reopened_at,
      }));
    } catch {
      // Prototype fallback
      try {
        const query = scanId ? `?scan_id=${encodeURIComponent(scanId)}` : "";
        const data = await this.request<{ changes: ChangeItem[] }>(`/changes${query}`);
        return data.changes || [];
      } catch {
        return [];
      }
    }
  }

  async getChangeImpact(changeId: string): Promise<ImpactItem[]> {
    try {
      const inc = await this.request<any>(`/incidents/${changeId}`);
      const files: string[] = inc.affected_files || [];
      const workflows: string[] = inc.affected_workflows || [];
      const ev = inc.evidence || {};

      const fields: string[] = [];
      if (ev.removed_property) fields.push(ev.removed_property);
      if (ev.renamed_from) fields.push(ev.renamed_from);
      if (ev.renamed_to) fields.push(ev.renamed_to);
      if (ev.field) fields.push(ev.field);

      return [
        {
          workflow_id: `wf_${changeId}`,
          workflow_name: workflows[0] || inc.title || "API Integration Workflow",
          source_files: files,
          tests: [],
          affected_fields: fields,
          reason: inc.description || "Contract drift detected on upstream dependency.",
        },
      ];
    } catch {
      // Prototype fallback
      try {
        const data = await this.request<{ impacts: ImpactItem[] }>(`/changes/${changeId}/impact`);
        return data.impacts || [];
      } catch {
        return [];
      }
    }
  }

  async getRepairProposals(changeId: string): Promise<RepairProposal[]> {
    try {
      const proposals = await this.request<any[]>(`/incidents/${changeId}/repair-proposals`);
      return (proposals || []).map((p: any) => this.mapRepairProposal(p));
    } catch {
      return [];
    }
  }

  async createRepairProposal(changeId: string): Promise<RepairProposal> {
    try {
      // Check existing proposals first
      const existing = await this.getRepairProposals(changeId);
      if (existing.length > 0) {
        return existing[0];
      }
      const data = await this.request<any>(`/incidents/${changeId}/repair-proposals`, {
        method: "POST",
        body: JSON.stringify({
          strategy: "compatibility_adapter",
          rationale: "Automated backwards-compatible repair proposal.",
          proposed_changes: {},
        }),
      });
      return this.mapRepairProposal(data);
    } catch (err: any) {
      // Prototype fallback
      try {
        const data = await this.request<any>(`/changes/${changeId}/repair-proposals`, { method: "POST" });
        return this.mapRepairProposal(data);
      } catch {
        throw err;
      }
    }
  }

  async getRepair(repairId: string): Promise<RepairProposal & { validations?: ValidationResult[] }> {
    try {
      const proposalData = await this.request<any>(`/repair-proposals/${repairId}`);
      const mapped = this.mapRepairProposal(proposalData);

      let validations: ValidationResult[] = [];
      try {
        const runs = await this.request<any[]>(`/repair-proposals/${repairId}/validation-runs`);
        validations = (runs || []).map((r: any) => ({
          id: r.id,
          repair_id: repairId,
          command: r.test_command || "pytest sandbox",
          exit_code: r.status === "passed" ? 0 : 1,
          output_summary: r.output_summary || r.test_output || "",
          duration_ms: Math.round((r.duration_seconds || 0) * 1000),
          status: r.status === "passed" ? "passed" : "failed",
          started_at: r.created_at || new Date().toISOString(),
        }));
      } catch {}

      return {
        ...mapped,
        validations,
      };
    } catch {
      // Prototype fallback
      return this.request(`/repairs/${repairId}`);
    }
  }

  async validateRepair(repairId: string): Promise<ValidationResult> {
    try {
      const runs = await this.request<any[]>(`/repair-proposals/${repairId}/validation-runs`);
      if (runs && runs.length > 0) {
        const latest = runs[runs.length - 1];
        return {
          id: latest.id,
          repair_id: repairId,
          command: latest.test_command || "sandbox validation",
          exit_code: latest.status === "passed" ? 0 : 1,
          output_summary: latest.output || latest.details?.test_output || `Validation status: ${latest.status}`,
          duration_ms: Math.round(latest.details?.validation_time_ms || 150),
          status: latest.status,
          started_at: latest.started_at || latest.created_at || new Date().toISOString(),
        };
      }
      return this.request(`/repairs/${repairId}/validate`, { method: "POST" });
    } catch {
      // Prototype fallback
      return this.request(`/repairs/${repairId}/validate`, { method: "POST" });
    }
  }

  async approveRepair(repairId: string, reviewerId: string = "vscode-developer", comment?: string): Promise<any> {
    try {
      return await this.request(`/repair-proposals/${repairId}/approvals`, {
        method: "POST",
        body: JSON.stringify({
          reviewer_id: reviewerId,
          decision: "approved",
          comment: comment || "Explicitly approved via Dependency Guardian VS Code Extension.",
        }),
      });
    } catch {
      // Prototype fallback
      return this.request(`/repairs/${repairId}/approve`, { method: "POST" });
    }
  }

  async applyRepair(
    repairId: string,
    agentId: string = "vscode-developer",
    status: string = "applied",
    workspaceReference?: string,
    message?: string
  ): Promise<{ status: string; message: string; repair_id: string }> {
    try {
      const res = await this.request<any>(`/repair-proposals/${repairId}/applications`, {
        method: "POST",
        body: JSON.stringify({
          agent_id: agentId,
          status: status,
          workspace_reference: workspaceReference || "",
          message: message || "Repair successfully applied to workspace after patch integrity verification.",
        }),
      });
      return {
        status: res.status || status,
        message: res.message || "Repair successfully recorded as applied on backend.",
        repair_id: repairId,
      };
    } catch {
      // Prototype fallback
      return this.request(`/repairs/${repairId}/apply`, { method: "POST" });
    }
  }

  async rejectRepair(
    repairId: string,
    reviewerId: string = "vscode-developer",
    reason: string = "Rejected via VS Code Extension."
  ): Promise<{ status: string; repair_id: string }> {
    try {
      await this.request(`/repair-proposals/${repairId}/rejection`, {
        method: "POST",
        body: JSON.stringify({
          reviewer_id: reviewerId,
          reason: reason || "Rejected via VS Code Extension.",
        }),
      });
      return { status: "rejected", repair_id: repairId };
    } catch {
      return this.request(`/repairs/${repairId}/reject`, {
        method: "POST",
        body: JSON.stringify({
          reviewer_id: reviewerId,
          reason: reason || "Rejected via VS Code Extension.",
        }),
      });
    }
  }

  async rollbackRepair(repairId: string): Promise<{ status: string; message: string; repair_id: string }> {
    try {
      const res = await this.request<any>(`/repair-proposals/${repairId}/rollback`, { method: "POST" });
      return {
        status: res.status || "rolled_back",
        message: res.message || "Repair successfully rolled back on backend.",
        repair_id: repairId,
      };
    } catch {
      return this.request(`/repairs/${repairId}/rollback`, { method: "POST" });
    }
  }

  async setScenario(scenario: string): Promise<any> {
    return this.request("/demo/set-scenario", {
      method: "POST",
      body: JSON.stringify({ scenario }),
    });
  }

  async resetDemo(): Promise<any> {
    return this.request("/demo/reset", { method: "POST" });
  }

  // =========================================================================
  // Project Baselines API
  // =========================================================================

  async getProjectBaselines(projectId: string): Promise<ProjectBaselineListResponse> {
    try {
      const res = await this.request<any>(`/projects/${projectId}/baselines`);
      return {
        items: res.items || [],
        total: res.total !== undefined ? res.total : (res.items || []).length,
        active_baseline: res.active_baseline || null,
      };
    } catch {
      return { items: [], total: 0, active_baseline: null };
    }
  }

  async getActiveProjectBaseline(projectId: string): Promise<ProjectBaseline | null> {
    try {
      const res = await this.request<ProjectBaseline | null>(`/projects/${projectId}/baselines/active`);
      return res || null;
    } catch {
      return null;
    }
  }

  async createProjectBaseline(
    projectId: string,
    data: {
      version_tag?: string;
      description?: string;
      contracts?: Record<string, any>;
      inventory?: Record<string, any>;
      source_scan_id?: string;
      notes?: string;
      metadata_json?: Record<string, any>;
    }
  ): Promise<ProjectBaseline> {
    return this.request<ProjectBaseline>(`/projects/${projectId}/baselines`, {
      method: "POST",
      body: JSON.stringify({
        version_tag: data.version_tag || `v${Date.now()}`,
        description: data.description || "Created via VS Code Extension",
        contracts: data.contracts || {},
        inventory: data.inventory || {},
        source_scan_id: data.source_scan_id,
        notes: data.notes,
        metadata_json: data.metadata_json || {},
      }),
    });
  }

  async promoteProjectBaseline(
    projectId: string,
    baselineId: string,
    actorId?: string
  ): Promise<ProjectBaseline> {
    const q = actorId ? `?promoted_by=${encodeURIComponent(actorId)}` : "";
    return this.request<ProjectBaseline>(`/projects/${projectId}/baselines/${baselineId}/promote${q}`, {
      method: "POST",
    });
  }

  async compareProjectBaselines(
    projectId: string,
    base: string,
    target: string
  ): Promise<ProjectBaselineCompareResponse> {
    return this.request<ProjectBaselineCompareResponse>(
      `/projects/${projectId}/baselines/compare?base=${encodeURIComponent(base)}&target=${encodeURIComponent(target)}`
    );
  }

  // =========================================================================
  // Persistent Scan History & Ingestion API
  // =========================================================================

  async ingestScanRun(projectId: string, payload: ScanIngestPayload): Promise<ScanRun> {
    return this.request<ScanRun>(`/projects/${projectId}/scans/ingest`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async listProjectScans(projectId: string, limit: number = 20): Promise<ScanRun[]> {
    try {
      const res = await this.request<any>(`/projects/${projectId}/scans?limit=${limit}`);
      return Array.isArray(res) ? res : res.items || [];
    } catch {
      return [];
    }
  }

  // =========================================================================
  // Incident Management & Lifecycle API
  // =========================================================================

  async acknowledgeIncident(
    incidentId: string,
    notes?: string,
    actorId?: string
  ): Promise<BackendIncident> {
    return this.request<BackendIncident>(`/incidents/${incidentId}/acknowledge`, {
      method: "POST",
      body: JSON.stringify({
        actor_id: actorId || "vscode-developer",
        notes: notes || "Acknowledged via VS Code Extension",
      }),
    });
  }

  async resolveIncident(
    incidentId: string,
    notes?: string,
    actorId?: string
  ): Promise<BackendIncident> {
    return this.request<BackendIncident>(`/incidents/${incidentId}/resolve`, {
      method: "POST",
      body: JSON.stringify({
        actor_id: actorId || "vscode-developer",
        notes: notes || "Resolved via VS Code Extension",
      }),
    });
  }

  async reopenIncident(
    incidentId: string,
    notes?: string,
    actorId?: string
  ): Promise<BackendIncident> {
    return this.request<BackendIncident>(`/incidents/${incidentId}/reopen`, {
      method: "POST",
      body: JSON.stringify({
        actor_id: actorId || "vscode-developer",
        notes: notes || "Reopened via VS Code Extension",
      }),
    });
  }

  async getIncidentEvents(incidentId: string): Promise<IncidentEvent[]> {
    try {
      const res = await this.request<IncidentEvent[]>(`/incidents/${incidentId}/events`);
      return Array.isArray(res) ? res : [];
    } catch {
      return [];
    }
  }

  async listProjectIncidents(
    projectId: string,
    status?: string
  ): Promise<{ items: BackendIncident[]; total: number }> {
    try {
      const q = status ? `?status=${encodeURIComponent(status)}` : "";
      const res = await this.request<any>(`/projects/${projectId}/incidents${q}`);
      return {
        items: Array.isArray(res) ? res : res.items || [],
        total: res.total !== undefined ? res.total : (res.items || []).length,
      };
    } catch {
      return { items: [], total: 0 };
    }
  }

  private mapRepairProposal(p: any): RepairProposal {
    const changes = p.proposed_changes || {};
    return {
      id: p.id,
      change_id: p.incident_id || p.change_id || "",
      repair_type: p.strategy || changes.engine_strategy || "compatibility_adapter",
      target_file: changes.target_file || p.target_file || "",
      original_code_snippet: "",
      proposed_code_snippet: changes.proposed_content || "",
      diff: p.diff_preview || p.patch?.content || p.diff || "",
      evidence: changes,
      assumptions: changes.assumptions || p.assumptions || [],
      confidence: p.confidence !== undefined ? p.confidence : 0.95,
      status: p.status || "proposed",
      created_at: p.created_at || new Date().toISOString(),
      likely_root_cause: changes.likely_root_cause || p.likely_root_cause,
      affected_symbols: changes.affected_symbols || p.affected_symbols || [],
      rationale: p.rationale || changes.rationale,
      risks: changes.risks || p.risks || [],
      alternatives_considered: changes.alternatives_considered || p.alternatives_considered || [],
      line_ranges: changes.line_ranges || p.line_ranges || [],
      suggested_validation_command: changes.suggested_validation_command || p.suggested_validation_command,
      proposed_changes: changes,
      patch_hash: p.patch_hash,
      client_repair_id: changes.client_repair_id || changes.repair_id,
      repair_id: changes.repair_id || p.id,
    };
  }
}
