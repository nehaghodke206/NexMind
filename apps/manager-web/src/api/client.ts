import {
  Project,
  Dependency,
  Incident,
  IncidentFilterOptions,
  RepairProposal,
  ValidationRun,
  RepairApproval,
  ActivityEvent,
} from './types';
import {
  mockProjects,
  mockDependencies,
  mockIncidents,
  mockRepairProposals,
  mockValidationRuns,
  mockActivity,
} from './mockData';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';
const IS_MOCK = import.meta.env.VITE_USE_MOCK !== 'false';

// In-memory state for mock mode session updates
const inMemoryIncidents = [...mockIncidents];
const inMemoryProposals = { ...mockRepairProposals };

async function delay(ms = 250): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export const api = {
  isMockMode(): boolean {
    return IS_MOCK;
  },

  getBaseUrl(): string {
    return BASE_URL;
  },

  async getProjects(): Promise<Project[]> {
    if (IS_MOCK) {
      await delay();
      return [...mockProjects];
    }
    const res = await fetch(`${BASE_URL}/projects`);
    if (!res.ok) {
      throw new Error(`Failed to fetch projects (HTTP ${res.status}: ${res.statusText})`);
    }
    const data = await res.json();
    return Array.isArray(data) ? data : data.items || [];
  },

  async getProject(projectId: string): Promise<Project> {
    if (IS_MOCK) {
      await delay();
      const proj = mockProjects.find((p) => p.id === projectId);
      if (!proj) throw new Error(`Project not found: ${projectId}`);
      return { ...proj };
    }
    const res = await fetch(`${BASE_URL}/projects/${projectId}`);
    if (!res.ok) {
      throw new Error(`Failed to fetch project ${projectId} (HTTP ${res.status}: ${res.statusText})`);
    }
    return res.json();
  },

  async getDependencies(projectId: string): Promise<Dependency[]> {
    if (IS_MOCK) {
      await delay();
      return mockDependencies.filter((d) => d.project_id === projectId);
    }
    const res = await fetch(`${BASE_URL}/projects/${projectId}/dependencies`);
    if (!res.ok) {
      throw new Error(`Failed to fetch dependencies (HTTP ${res.status}: ${res.statusText})`);
    }
    const data = await res.json();
    return Array.isArray(data) ? data : data.items || [];
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

    const res = await fetch(`${BASE_URL}/projects/${projectId}/incidents${queryString}`);
    if (!res.ok) {
      throw new Error(`Failed to fetch incidents (HTTP ${res.status}: ${res.statusText})`);
    }
    const data = await res.json();
    return Array.isArray(data) ? data : data.items || [];
  },

  async getIncident(incidentId: string): Promise<Incident> {
    if (IS_MOCK) {
      await delay();
      const inc = inMemoryIncidents.find((i) => i.id === incidentId);
      if (!inc) throw new Error(`Incident not found: ${incidentId}`);
      return { ...inc };
    }
    const res = await fetch(`${BASE_URL}/incidents/${incidentId}`);
    if (!res.ok) {
      throw new Error(`Failed to fetch incident ${incidentId} (HTTP ${res.status}: ${res.statusText})`);
    }
    return res.json();
  },

  async getRepairProposal(incidentId: string): Promise<RepairProposal | null> {
    if (IS_MOCK) {
      await delay();
      const proposal = inMemoryProposals[incidentId];
      return proposal ? { ...proposal } : null;
    }
    const res = await fetch(`${BASE_URL}/incidents/${incidentId}/repair-proposals`);
    if (res.status === 404) return null;
    if (!res.ok) {
      throw new Error(`Failed to fetch repair proposals (HTTP ${res.status}: ${res.statusText})`);
    }
    const data = await res.json();
    if (Array.isArray(data)) return data[0] || null;
    return data.items ? data.items[0] || null : data;
  },

  async getValidationRun(repairId: string): Promise<ValidationRun | null> {
    if (IS_MOCK) {
      await delay();
      const run = mockValidationRuns[repairId];
      return run ? { ...run } : null;
    }
    const res = await fetch(`${BASE_URL}/repair-proposals/${repairId}/validation-runs`);
    if (res.status === 404) return null;
    if (!res.ok) {
      throw new Error(`Failed to fetch validation runs (HTTP ${res.status}: ${res.statusText})`);
    }
    const data = await res.json();
    if (Array.isArray(data)) return data[0] || null;
    return data.items ? data.items[0] || null : data;
  },

  async approveRepairProposal(repairId: string, comment?: string): Promise<RepairApproval> {
    if (IS_MOCK) {
      await delay(400);
      // In-memory transition: repair proposal status moves to approved
      // Cardinal Product Rule: Approval is NOT Application.
      // The incident remains in its current workflow or 'approved' state, NOT 'resolved'.
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

    const res = await fetch(`${BASE_URL}/repair-proposals/${repairId}/approvals`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        reviewer_id: 'user_alex_manager',
        decision: 'approved',
        comment: comment || '',
      }),
    });
    if (!res.ok) {
      throw new Error(`Failed to approve repair proposal (HTTP ${res.status}: ${res.statusText})`);
    }
    return res.json();
  },

  async getActivity(projectId: string): Promise<ActivityEvent[]> {
    if (IS_MOCK) {
      await delay();
      return mockActivity.filter((a) => a.project_id === projectId);
    }
    const res = await fetch(`${BASE_URL}/projects/${projectId}/activity`);
    if (!res.ok) {
      throw new Error(`Failed to fetch activity (HTTP ${res.status}: ${res.statusText})`);
    }
    const data = await res.json();
    return Array.isArray(data) ? data : data.items || [];
  },
};
