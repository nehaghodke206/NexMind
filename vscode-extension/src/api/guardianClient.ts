/**
 * Client for communicating with the local Dependency Guardian backend (http://127.0.0.1:8765).
 */

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
  severity: "low" | "medium" | "high" | "blocked";
  evidence: Record<string, any>;
  status: string;
  created_at: string;
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

  constructor(baseUrl: string = "http://127.0.0.1:8765") {
    this.baseUrl = baseUrl;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });

    if (!res.ok) {
      let errorDetail = res.statusText;
      try {
        const errorJson = (await res.json()) as any;
        errorDetail = errorJson.detail || errorDetail;
      } catch {}
      throw new Error(`Guardian API error (${res.status}): ${errorDetail}`);
    }

    return (await res.json()) as T;
  }

  async getHealth(): Promise<{ status: string; product: string; version: string; workspace_root: string }> {
    return this.request("/api/health");
  }

  async initializeProject(): Promise<any> {
    return this.request("/api/projects/initialize", { method: "POST" });
  }

  async getServices(): Promise<DependencyService[]> {
    const data = await this.request<{ services: DependencyService[] }>("/api/services");
    return data.services;
  }

  async createBaseline(): Promise<any> {
    return this.request("/api/baselines", { method: "POST" });
  }

  async runScan(): Promise<{
    scan_id: string;
    status: string;
    services_checked: number;
    changes_detected: number;
    changes: ChangeItem[];
  }> {
    return this.request("/api/scans", { method: "POST" });
  }

  async getChanges(scanId?: string): Promise<ChangeItem[]> {
    const query = scanId ? `?scan_id=${encodeURIComponent(scanId)}` : "";
    const data = await this.request<{ changes: ChangeItem[] }>(`/api/changes${query}`);
    return data.changes;
  }

  async getChangeImpact(changeId: string): Promise<ImpactItem[]> {
    const data = await this.request<{ impacts: ImpactItem[] }>(`/api/changes/${changeId}/impact`);
    return data.impacts;
  }

  async createRepairProposal(changeId: string): Promise<RepairProposal> {
    return this.request(`/api/changes/${changeId}/repair-proposals`, { method: "POST" });
  }

  async getRepair(repairId: string): Promise<RepairProposal & { validations?: ValidationResult[] }> {
    return this.request(`/api/repairs/${repairId}`);
  }

  async validateRepair(repairId: string): Promise<ValidationResult> {
    return this.request(`/api/repairs/${repairId}/validate`, { method: "POST" });
  }

  async applyRepair(repairId: string): Promise<{ status: string; message: string; repair_id: string }> {
    return this.request(`/api/repairs/${repairId}/apply`, { method: "POST" });
  }

  async rejectRepair(repairId: string): Promise<{ status: string; repair_id: string }> {
    return this.request(`/api/repairs/${repairId}/reject`, { method: "POST" });
  }

  async rollbackRepair(repairId: string): Promise<{ status: string; message: string; repair_id: string }> {
    return this.request(`/api/repairs/${repairId}/rollback`, { method: "POST" });
  }

  async setScenario(scenario: string): Promise<any> {
    return this.request("/api/demo/set-scenario", {
      method: "POST",
      body: JSON.stringify({ scenario }),
    });
  }

  async resetDemo(): Promise<any> {
    return this.request("/api/demo/reset", { method: "POST" });
  }
}
