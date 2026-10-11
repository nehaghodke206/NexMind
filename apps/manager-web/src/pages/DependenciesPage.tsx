import React, { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api/client';
import { Dependency, Baseline, Project, DependencyCreate } from '../api/types';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';

export const DependenciesPage: React.FC = () => {
  const { projectId: routeProjectId } = useParams<{ projectId?: string }>();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>(routeProjectId || 'proj_demo_shop');
  const [dependencies, setDependencies] = useState<Dependency[]>([]);
  const [selectedDep, setSelectedDep] = useState<Dependency | null>(null);
  const [baselines, setBaselines] = useState<Baseline[]>([]);

  const [loading, setLoading] = useState(true);
  const [loadingBaselines, setLoadingBaselines] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // New dependency modal
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newKind, setNewKind] = useState<'rest_api' | 'sdk' | 'package' | 'mcp_tool' | 'other'>('rest_api');
  const [newBaseUrl, setNewBaseUrl] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadDependencies = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [projList, deps] = await Promise.all([
        api.getProjects(),
        api.getDependencies(selectedProjectId),
      ]);
      setProjects(projList);
      setDependencies(deps);
      if (deps.length > 0 && !selectedDep) {
        setSelectedDep(deps[0]);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load dependencies');
    } finally {
      setLoading(false);
    }
  }, [selectedProjectId, selectedDep]);

  useEffect(() => {
    loadDependencies();
  }, [loadDependencies]);

  const loadBaselines = useCallback(async (depId: string) => {
    setLoadingBaselines(true);
    try {
      const data = await api.getDependencyBaselines(depId);
      setBaselines(data);
    } catch {
      setBaselines([]);
    } finally {
      setLoadingBaselines(false);
    }
  }, []);

  useEffect(() => {
    if (selectedDep) {
      loadBaselines(selectedDep.id);
    }
  }, [selectedDep, loadBaselines]);

  const handleCreateDependency = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setIsSubmitting(true);
    try {
      const payload: DependencyCreate = {
        name: newName.trim(),
        kind: newKind,
        base_url: newBaseUrl.trim() || undefined,
      };
      const created = await api.createDependency(selectedProjectId, payload);
      setDependencies((prev) => [...prev, created]);
      setSelectedDep(created);
      setIsAddModalOpen(false);
      setNewName('');
      setNewBaseUrl('');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to register dependency');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xl)' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-md)' }}>
        <div>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', marginBottom: 'var(--space-xs)' }}>
            <span
              style={{
                fontSize: '0.6875rem',
                fontWeight: 700,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                color: 'var(--brand-primary)',
                padding: '2px 8px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--sev-critical-bg)',
                border: '1px solid var(--sev-critical-border)',
              }}
            >
              SCHEMA CONTRACT REGISTRY
            </span>
          </div>
          <h1 style={{ fontSize: '1.875rem', fontWeight: 700, marginBottom: 'var(--space-xs)', letterSpacing: '-0.02em' }}>
            Monitored Dependencies & Baselines
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9375rem' }}>
            Registered external service contracts, baseline snapshots, and drift validation targets.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
          {projects.length > 0 && (
            <select
              value={selectedProjectId}
              onChange={(e) => {
                setSelectedProjectId(e.target.value);
                setSelectedDep(null);
              }}
              style={{
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-strong)',
                color: 'var(--text-main)',
                padding: '8px 14px',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem',
                cursor: 'pointer',
              }}
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          )}

          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setIsAddModalOpen(true)}
            style={{ gap: '6px' }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            <span>Register Dependency</span>
          </button>
        </div>
      </div>

      {loading ? (
        <LoadingState message="Loading registered dependency catalog..." />
      ) : error ? (
        <ErrorState message={error} onRetry={loadDependencies} />
      ) : dependencies.length === 0 ? (
        <EmptyState
          title="No Monitored Dependencies"
          description="This project currently has no registered dependencies or API endpoints tracked for schema drift."
          actionText="Register First Dependency"
          onAction={() => setIsAddModalOpen(true)}
        />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 380px) 1fr', gap: 'var(--space-xl)', alignItems: 'start' }}>
          {/* Dependency List Sidebar */}
          <div className="card" style={{ padding: 'var(--space-md)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <h2 style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', padding: '4px 8px' }}>
              Tracked Services ({dependencies.length})
            </h2>

            {dependencies.map((dep) => {
              const isSelected = selectedDep?.id === dep.id;
              return (
                <button
                  key={dep.id}
                  type="button"
                  onClick={() => setSelectedDep(dep)}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px',
                    textAlign: 'left',
                    padding: 'var(--space-md)',
                    borderRadius: 'var(--radius-md)',
                    backgroundColor: isSelected ? 'var(--bg-surface-elevated)' : 'transparent',
                    border: `1px solid ${isSelected ? 'var(--brand-primary)' : 'var(--border-subtle)'}`,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                    <span style={{ fontWeight: 700, color: 'var(--text-main)', fontSize: '0.9375rem' }}>
                      {dep.name}
                    </span>
                    <span
                      style={{
                        fontSize: '0.6875rem',
                        textTransform: 'uppercase',
                        padding: '2px 6px',
                        borderRadius: 'var(--radius-sm)',
                        backgroundColor: 'var(--bg-app)',
                        color: 'var(--text-muted)',
                        border: '1px solid var(--border-subtle)',
                        fontWeight: 600,
                      }}
                    >
                      {dep.kind || 'rest_api'}
                    </span>
                  </div>

                  {dep.base_url && (
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-faint)', fontFamily: 'var(--font-mono)' }}>
                      {dep.base_url}
                    </span>
                  )}
                  {dep.version && (
                    <span style={{ fontSize: '0.75rem', color: 'var(--brand-secondary)' }}>
                      v{dep.version}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Selected Dependency Baselines */}
          {selectedDep ? (
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-xs)' }}>
                  <h2 style={{ fontSize: '1.375rem', fontWeight: 700 }}>{selectedDep.name}</h2>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    ID: {selectedDep.id}
                  </span>
                </div>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                  Target: <code style={{ color: 'var(--brand-primary)', fontFamily: 'var(--font-mono)' }}>{selectedDep.base_url || 'Internal Mock API'}</code>
                </p>
              </div>

              <div>
                <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: 'var(--space-sm)' }}>
                  Captured Baseline Versions (API: <code>GET /dependencies/:id/baselines</code>)
                </h3>

                {loadingBaselines ? (
                  <LoadingState message="Fetching schema snapshots..." />
                ) : baselines.length === 0 ? (
                  <div style={{ padding: 'var(--space-lg)', textAlign: 'center', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                      No schema baselines captured yet. Baselines are recorded during scanner discovery runs or manually imported.
                    </p>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
                    {baselines.map((b) => (
                      <div
                        key={b.id}
                        style={{
                          backgroundColor: 'var(--diff-bg)',
                          border: '1px solid var(--border-subtle)',
                          borderRadius: 'var(--radius-md)',
                          padding: 'var(--space-md)',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-sm)' }}>
                          <span style={{ fontWeight: 700, fontSize: '0.875rem', color: 'var(--text-main)' }}>
                            Baseline Version #{b.version} ({b.source || 'scan'})
                          </span>
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                            {new Date(b.created_at).toLocaleString()}
                          </span>
                        </div>
                        <pre
                          style={{
                            fontFamily: 'var(--font-mono)',
                            fontSize: '0.8125rem',
                            color: 'var(--text-main)',
                            overflowX: 'auto',
                            padding: 'var(--space-sm)',
                            backgroundColor: 'var(--bg-surface)',
                            borderRadius: 'var(--radius-sm)',
                            border: '1px solid var(--border-subtle)',
                          }}
                        >
                          {JSON.stringify(b.contract, null, 2)}
                        </pre>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="card" style={{ padding: 'var(--space-2xl)', textAlign: 'center' }}>
              <p style={{ color: 'var(--text-muted)' }}>Select a dependency to view its contract baseline telemetry.</p>
            </div>
          )}
        </div>
      )}

      {/* Add Dependency Modal */}
      {isAddModalOpen && (
        <div className="modal-overlay" role="dialog" aria-modal="true">
          <div className="modal-content">
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: 'var(--space-md)' }}>
              Register Monitored Dependency
            </h2>
            <form onSubmit={handleCreateDependency} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, marginBottom: '4px' }}>
                  Service Name *
                </label>
                <input
                  type="text"
                  required
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g., Stripe Payments API, Twilio SMS Service"
                  style={{ width: '100%' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, marginBottom: '4px' }}>
                  Dependency Kind
                </label>
                <select
                  value={newKind}
                  onChange={(e) => setNewKind(e.target.value as DependencyCreate['kind'])}
                  style={{ width: '100%' }}
                >
                  <option value="rest_api">REST API</option>
                  <option value="sdk">SDK Client</option>
                  <option value="package">Package / Module</option>
                  <option value="mcp_tool">MCP Tool Schema</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, marginBottom: '4px' }}>
                  Base URL / Target Endpoint
                </label>
                <input
                  type="url"
                  value={newBaseUrl}
                  onChange={(e) => setNewBaseUrl(e.target.value)}
                  placeholder="https://api.external-service.com/v1"
                  style={{ width: '100%' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-sm)', marginTop: 'var(--space-sm)' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setIsAddModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isSubmitting || !newName.trim()}
                >
                  {isSubmitting ? 'Registering...' : 'Save & Track'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
