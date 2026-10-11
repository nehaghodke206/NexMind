import {
  Project,
  ProjectCreate,
  ProjectSummary,
  Dependency,
  DependencyCreate,
  Baseline,
  ScanRun,
  Observation,
  Incident,
  IncidentFilterOptions,
  RepairProposal,
  ValidationRun,
  RepairApproval,
  ActivityEvent,
  HealthStatus,
} from './types';
import {
  mockProjects,
  mockDependencies,
  mockIncidents,
  mockRepairProposals,
  mockValidationRuns,
  mockActivity,
  mockProjectSummaries,
  mockBaselines,
  mockScans,
  mockObservations,
} from './mockData';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
const IS_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

// In-memory state for mock mode session updates
const inMemoryProjects = [...mockProjects];
const inMemoryDependencies = [...mockDependencies];
const inMemoryIncidents = [...mockIncidents];
const inMemoryProposals = { ...mockRepairProposals };
const inMemoryScans = [...mockScans];

async function delay(ms = 200): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });

    if (!res.ok) {
      let errMsg = `HTTP ${res.status}: ${res.statusText}`;
      try {
        const errJson = await res.json();
        if (errJson.detail) errMsg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
        else if (errJson.message) errMsg = errJson.message;
      } catch {
        // use default statusText
      }
      throw new Error(`API error at ${path}: ${errMsg}`);
    }

    return await res.json();
  } catch (err: unknown) {
    if (err instanceof TypeError && err.message.includes('fetch')) {
      throw new Error(
        `Unable to reach backend at ${BASE_URL}. Ensure the backend service is running, or switch VITE_USE_MOCK=true in .env.`
      );
    }
    throw err;
  }
}

export const api = {
  isMockMode(): boolean {
    return IS_MOCK;
  },

  getBaseUrl(): string {
    return BASE_URL;
  },

  async checkHealth(): Promise<HealthStatus> {
    if (IS_MOCK) {
      await delay(100);
      return { status: 'healthy (simulation)' };
    }
    const healthUrl = BASE_URL.replace(/\/api\/v1\/?$/, '') + '/health';
    try {
      const res = await fetch(healthUrl);
      if (res.ok) return await res.json();
      return { status: `degraded (${res.status})` };
    } catch {
      return { status: 'offline' };
    }
  },

  async getProjects(): Promise<Project[]> {
    if (IS_MOCK) {
      await delay();
      return [...inMemoryProjects];
    }
    const data = await request<Project[] | { items: Project[] }>('/projects');
    return Array.isArray(data) ? data : data.items || [];
  },

  async createProject(payload: ProjectCreate): Promise<Project> {
    if (IS_MOCK) {
      await delay();
      const newProj: Project = {
        id: `proj_${Date.now()}`,
        name: payload.name,
        description: payload.description || null,
        repository_url: payload.repository_url || null,
        default_branch: payload.default_branch || 'main',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      inMemoryProjects.unshift(newProj);
      return newProj;
    }
    return request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async getProject(projectId: string): Promise<Project> {
    if (IS_MOCK) {
      await delay();
      const proj = inMemoryProjects.find((p) => p.id === projectId);
      if (!proj) throw new Error(`Project not found: ${projectId}`);
      return { ...proj };
    }
    return request<Project>(`/projects/${projectId}`);
  },

  async getProjectSummary(projectId: string): Promise<ProjectSummary> {
    if (IS_MOCK) {
      await delay();
      const summary = mockProjectSummaries[projectId] || {
        project_id: projectId,
        dependency_count: inMemoryDependencies.filter((d) => d.project_id === projectId).length,
        open_incident_count: inMemoryIncidents.filter((i) => i.project_id === projectId).length,
        pending_review_count: 1,
        validation_pass_count: 2,
        validation_fail_count: 0,
        last_scan_at: new Date().toISOString(),
      };
      return { ...summary };
    }
    return request<ProjectSummary>(`/projects/${projectId}/summary`);
  },

  async getDependencies(projectId: string): Promise<Dependency[]> {
    if (IS_MOCK) {
      await delay();
      return inMemoryDependencies.filter((d) => d.project_id === projectId);
    }
    const data = await request<Dependency[] | { items: Dependency[] }>(`/projects/${projectId}/dependencies`);
    return Array.isArray(data) ? data : data.items || [];
  },

  async createDependency(projectId: string, payload: DependencyCreate): Promise<Dependency> {
    if (IS_MOCK) {
      await delay();
      const newDep: Dependency = {
        id: `dep_${Date.now()}`,
        project_id: projectId,
        name: payload.name,
        kind: payload.kind,
        base_url: payload.base_url || null,
        version: '1.0.0',
        created_at: new Date().toISOString(),
      };
      inMemoryDependencies.push(newDep);
      return newDep;
    }
    return request<Dependency>(`/projects/${projectId}/dependencies`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async getDependencyBaselines(dependencyId: string): Promise<Baseline[]> {
    if (IS_MOCK) {
      await delay();
      return mockBaselines[dependencyId] || [];
    }
    const data = await request<Baseline[] | { items: Baseline[] }>(`/dependencies/${dependencyId}/baselines`);
    return Array.isArray(data) ? data : data.items || [];
  },

  async getScans(projectId: string): Promise<ScanRun[]> {
    if (IS_MOCK) {
      await delay();
      return inMemoryScans.filter((s) => s.project_id === projectId);
    }
    const data = await request<ScanRun[] | { items: ScanRun[] }>(`/projects/${projectId}/scans`);
    return Array.isArray(data) ? data : data.items || [];
  },

  async triggerScan(projectId: string, dependencyId?: string): Promise<ScanRun> {
    if (IS_MOCK) {
      await delay(400);
      const newScan: ScanRun = {
        id: `scan_${Date.now()}`,
        project_id: projectId,
        dependency_id: dependencyId || null,
        initiated_by: 'user_manager',
        status: 'running',
        summary: 'Active probe scan checking response contracts against registered baselines.',
        started_at: new Date().toISOString(),
      };
      inMemoryScans.unshift(newScan);
      return newScan;
    }
    return request<ScanRun>(`/projects/${projectId}/scans`, {
      method: 'POST',
      body: JSON.stringify({ dependency_id: dependencyId }),
    });
  },

  async getIncidents(projectId: string, filters?: IncidentFilterOptions): Promise<Incident[]> {
    if (IS_MOCK) {
      await delay();
      let list = inMemoryIncidents.filter((inc) => inc.project_id === projectId);

      if (filters?.severity) {
        list = list.filter((inc) => inc.severity === filters.severity);
      }
      if (filters?.status) {
        list = list.filter((inc) => inc.status === filters.status);
      }
      if (filters?.dependency_id) {
        list = list.filter((inc) => inc.dependency_id === filters.dependency_id);
      }
      if (filters?.search) {
        const q = filters.search.toLowerCase();
        list = list.filter(
          (inc) =>
            inc.title.toLowerCase().includes(q) ||
            (inc.description && inc.description.toLowerCase().includes(q)) ||
            (inc.fingerprint && inc.fingerprint.toLowerCase().includes(q)) ||
            inc.affected_files.some((f) => f.toLowerCase().includes(q))
        );
      }

      return list.map((item) => ({ ...item }));
    }

    const query = new URLSearchParams();
    if (filters?.severity) query.set('severity', filters.severity);
    if (filters?.status) query.set('status', filters.status);
    if (filters?.dependency_id) query.set('dependency_id', filters.dependency_id);
    const queryString = query.toString() ? `?${query.toString()}` : '';

    const data = await request<Incident[] | { items: Incident[] }>(`/projects/${projectId}/incidents${queryString}`);
    return Array.isArray(data) ? data : data.items || [];
  },

  async getIncident(incidentId: string): Promise<Incident> {
    if (IS_MOCK) {
      await delay();
      const inc = inMemoryIncidents.find((i) => i.id === incidentId);
      if (!inc) throw new Error(`Incident not found: ${incidentId}`);
      return { ...inc };
    }
    return request<Incident>(`/incidents/${incidentId}`);
  },

  async getIncidentObservations(incidentId: string): Promise<Observation[]> {
    if (IS_MOCK) {
      await delay();
      return mockObservations[incidentId] || [];
    }
    try {
      const data = await request<Observation[] | { items: Observation[] }>(`/incidents/${incidentId}/observations`);
      return Array.isArray(data) ? data : data.items || [];
    } catch {
      return [];
    }
  },

  async getRepairProposal(incidentId: string): Promise<RepairProposal | null> {
    if (IS_MOCK) {
      await delay();
      const proposal = inMemoryProposals[incidentId];
      return proposal ? { ...proposal } : null;
    }
    try {
      const data = await request<RepairProposal[] | { items: RepairProposal[] }>(
        `/incidents/${incidentId}/repair-proposals`
      );
      if (Array.isArray(data)) return data[0] || null;
      return data.items ? data.items[0] || null : (data as unknown as RepairProposal);
    } catch {
      return null;
    }
  },

  async getValidationRun(repairId: string): Promise<ValidationRun | null> {
    if (IS_MOCK) {
      await delay();
      const run = mockValidationRuns[repairId];
      return run ? { ...run } : null;
    }
    try {
      const data = await request<ValidationRun[] | { items: ValidationRun[] }>(
        `/repair-proposals/${repairId}/validation-runs`
      );
      if (Array.isArray(data)) return data[0] || null;
      return data.items ? data.items[0] || null : (data as unknown as ValidationRun);
    } catch {
      return null;
    }
  },

  async approveRepairProposal(repairId: string, comment?: string): Promise<RepairApproval> {
    if (IS_MOCK) {
      await delay(300);
      for (const key of Object.keys(inMemoryProposals)) {
        if (inMemoryProposals[key].id === repairId) {
          inMemoryProposals[key] = {
            ...inMemoryProposals[key],
            status: 'approved',
          };
          const incIndex = inMemoryIncidents.findIndex((i) => i.id === inMemoryProposals[key].incident_id);
          if (incIndex >= 0) {
            inMemoryIncidents[incIndex] = {
              ...inMemoryIncidents[incIndex],
              status: 'approved',
              review_notes: comment ? `Approved with comment: ${comment}` : 'Approved by human reviewer.',
            };
          }
          break;
        }
      }

      return {
        id: `appr_${Date.now()}`,
        repair_id: repairId,
        reviewer_id: 'user_alex_manager',
        decision: 'approved',
        comment: comment || null,
        decided_at: new Date().toISOString(),
      };
    }

    return request<RepairApproval>(`/repair-proposals/${repairId}/approvals`, {
      method: 'POST',
      body: JSON.stringify({
        reviewer_id: 'user_alex_manager',
        decision: 'approved',
        comment: comment || '',
      }),
    });
  },

  async rejectRepairProposal(repairId: string, reason: string): Promise<{ status: string }> {
    if (IS_MOCK) {
      await delay(300);
      for (const key of Object.keys(inMemoryProposals)) {
        if (inMemoryProposals[key].id === repairId) {
          inMemoryProposals[key] = {
            ...inMemoryProposals[key],
            status: 'rejected',
          };
          break;
        }
      }
      return { status: 'rejected' };
    }
    return request<{ status: string }>(`/repair-proposals/${repairId}/rejection`, {
      method: 'POST',
      body: JSON.stringify({
        reviewer_id: 'user_alex_manager',
        reason,
      }),
    });
  },

  async getActivity(projectId: string): Promise<ActivityEvent[]> {
    if (IS_MOCK) {
      await delay();
      return mockActivity.filter((a) => a.project_id === projectId);
    }
    const data = await request<ActivityEvent[] | { items: ActivityEvent[] }>(`/projects/${projectId}/activity`);
    return Array.isArray(data) ? data : data.items || [];
  },
};
