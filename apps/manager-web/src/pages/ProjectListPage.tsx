import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { Project, ProjectSummary, ProjectCreate } from '../api/types';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';

export const ProjectListPage: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [summaries, setSummaries] = useState<Record<string, ProjectSummary>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create Project modal state
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newRepoUrl, setNewRepoUrl] = useState('');
  const [newDefaultBranch, setNewDefaultBranch] = useState('main');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadProjects = async () => {
    setLoading(true);
    setError(null);
    try {
      const projList = await api.getProjects();
      setProjects(projList);

      // Load project summaries from GET /projects/:id/summary
      const sumMap: Record<string, ProjectSummary> = {};
      await Promise.all(
        projList.map(async (p) => {
          try {
            const summary = await api.getProjectSummary(p.id);
            sumMap[p.id] = summary;
          } catch {
            // fallback if summary endpoint is unavailable
          }
        })
      );
      setSummaries(sumMap);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load projects');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setIsSubmitting(true);
    try {
      const payload: ProjectCreate = {
        name: newName.trim(),
        description: newDesc.trim() || undefined,
        repository_url: newRepoUrl.trim() || undefined,
        default_branch: newDefaultBranch.trim() || 'main',
      };
      const created = await api.createProject(payload);
      setProjects((prev) => [created, ...prev]);
      setIsCreateModalOpen(false);
      setNewName('');
      setNewDesc('');
      setNewRepoUrl('');
      setNewDefaultBranch('main');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to create project');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) return <LoadingState message="Connecting to project registry..." />;
  if (error) return <ErrorState message={error} onRetry={loadProjects} />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xl)' }}>
      {/* Header */}
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
              PROJECT OBSERVATORY
            </span>
          </div>
          <h1 style={{ fontSize: '1.875rem', fontWeight: 700, marginBottom: 'var(--space-xs)', letterSpacing: '-0.02em' }}>
            Monitored Projects
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9375rem' }}>
            Real-time API schema drift surveillance, anomaly detection, and automated repair pipelines.
          </p>
        </div>

        {/* Minimal Theme-Matching Create Project Button */}
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => setIsCreateModalOpen(true)}
          style={{
            gap: '8px',
            padding: '8px 16px',
            fontSize: '0.875rem',
            boxShadow: 'var(--shadow-sm)',
          }}
          aria-label="Create a new monitored project"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          <span>Create New Project</span>
        </button>
      </div>

      {projects.length === 0 ? (
        <EmptyState
          title="No Monitored Projects"
          description="There are currently no active projects configured for dependency guardian monitoring."
          actionText="Create New Project"
          onAction={() => setIsCreateModalOpen(true)}
        />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: 'var(--space-lg)' }}>
          {projects.map((p) => {
            const summary = summaries[p.id];
            return (
              <div key={p.id} className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: 'var(--space-md)' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-sm)' }}>
                    <h2 style={{ fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.01em', margin: 0 }}>{p.name}</h2>
                    <span
                      style={{
                        fontSize: '0.75rem',
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--text-muted)',
                        backgroundColor: 'var(--bg-surface-elevated)',
                        border: '1px solid var(--border-subtle)',
                        padding: '2px 6px',
                        borderRadius: 'var(--radius-sm)',
                      }}
                    >
                      {p.id}
                    </span>
                  </div>

                  <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: 'var(--space-md)' }}>
                    {p.description || 'No description provided.'}
                  </p>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: 'var(--space-md)', fontSize: '0.8125rem' }}>
                    {p.repository_url && (
                      <p style={{ color: 'var(--text-faint)', margin: 0 }}>
                        Repository: <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{p.repository_url}</span>
                      </p>
                    )}
                    {p.default_branch && (
                      <p style={{ color: 'var(--text-faint)', margin: 0 }}>
                        Branch: <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--brand-secondary)' }}>{p.default_branch}</span>
                      </p>
                    )}
                  </div>

                  {/* Summary Metrics */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--space-sm)', margin: 'var(--space-md) 0' }}>
                    <div
                      style={{
                        backgroundColor: 'var(--bg-surface-elevated)',
                        border: '1px solid var(--border-subtle)',
                        padding: 'var(--space-sm)',
                        borderRadius: 'var(--radius-md)',
                        textAlign: 'center',
                      }}
                    >
                      <div style={{ fontSize: '1.375rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-main)' }}>
                        {summary?.open_incident_count ?? '-'}
                      </div>
                      <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                        Incidents
                      </div>
                    </div>

                    <div
                      style={{
                        backgroundColor: 'var(--sev-high-bg)',
                        border: '1px solid var(--sev-high-border)',
                        padding: 'var(--space-sm)',
                        borderRadius: 'var(--radius-md)',
                        textAlign: 'center',
                      }}
                    >
                      <div style={{ fontSize: '1.375rem', fontWeight: 700, color: 'var(--sev-high-text)', fontFamily: 'var(--font-mono)' }}>
                        {summary?.pending_review_count ?? '-'}
                      </div>
                      <div style={{ fontSize: '0.6875rem', color: 'var(--sev-high-text)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                        In Review
                      </div>
                    </div>

                    <div
                      style={{
                        backgroundColor: 'var(--status-review-bg)',
                        border: '1px solid var(--status-review-border)',
                        padding: 'var(--space-sm)',
                        borderRadius: 'var(--radius-md)',
                        textAlign: 'center',
                      }}
                    >
                      <div style={{ fontSize: '1.375rem', fontWeight: 700, color: 'var(--status-review-text)', fontFamily: 'var(--font-mono)' }}>
                        {summary?.dependency_count ?? '-'}
                      </div>
                      <div style={{ fontSize: '0.6875rem', color: 'var(--status-review-text)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                        Services
                      </div>
                    </div>
                  </div>
                </div>

                {/* Action Links */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--space-md)' }}>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <Link
                      to={`/projects/${p.id}/incidents`}
                      className="btn btn-primary"
                      style={{ flex: 1, textAlign: 'center', fontSize: '0.8125rem' }}
                    >
                      Incidents
                    </Link>
                    <Link
                      to={`/projects/${p.id}/dependencies`}
                      className="btn btn-secondary"
                      style={{ flex: 1, textAlign: 'center', fontSize: '0.8125rem' }}
                    >
                      Dependencies
                    </Link>
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <Link
                      to={`/projects/${p.id}/scans`}
                      className="btn btn-secondary"
                      style={{ flex: 1, textAlign: 'center', fontSize: '0.8125rem' }}
                    >
                      Scans & Probes
                    </Link>
                    <Link
                      to={`/projects/${p.id}/activity`}
                      className="btn btn-secondary"
                      style={{ flex: 1, textAlign: 'center', fontSize: '0.8125rem' }}
                    >
                      Activity Feed
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create New Project Modal */}
      {isCreateModalOpen && (
        <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="create-project-title">
          <div className="modal-content">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-md)' }}>
              <h2 id="create-project-title" style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>
                Create New Project
              </h2>
              <button
                type="button"
                onClick={() => setIsCreateModalOpen(false)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-muted)',
                  fontSize: '1.25rem',
                  cursor: 'pointer',
                  padding: '4px',
                }}
                aria-label="Close dialog"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateProject} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
              <div>
                <label htmlFor="project-name-input" style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, marginBottom: '4px', color: 'var(--text-main)' }}>
                  Project Name *
                </label>
                <input
                  id="project-name-input"
                  type="text"
                  required
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g., Checkout Microservice"
                  style={{
                    width: '100%',
                    backgroundColor: 'var(--bg-surface)',
                    border: '1px solid var(--border-strong)',
                    color: 'var(--text-main)',
                  }}
                />
              </div>

              <div>
                <label htmlFor="project-desc-input" style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, marginBottom: '4px', color: 'var(--text-main)' }}>
                  Description
                </label>
                <textarea
                  id="project-desc-input"
                  rows={2}
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="Service role, business domain, and team ownership"
                  style={{
                    width: '100%',
                    backgroundColor: 'var(--bg-surface)',
                    border: '1px solid var(--border-strong)',
                    color: 'var(--text-main)',
                  }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 'var(--space-md)' }}>
                <div>
                  <label htmlFor="project-repo-input" style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, marginBottom: '4px', color: 'var(--text-main)' }}>
                    Repository URL
                  </label>
                  <input
                    id="project-repo-input"
                    type="url"
                    value={newRepoUrl}
                    onChange={(e) => setNewRepoUrl(e.target.value)}
                    placeholder="https://github.com/org/repo"
                    style={{
                      width: '100%',
                      backgroundColor: 'var(--bg-surface)',
                      border: '1px solid var(--border-strong)',
                      color: 'var(--text-main)',
                    }}
                  />
                </div>

                <div>
                  <label htmlFor="project-branch-input" style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, marginBottom: '4px', color: 'var(--text-main)' }}>
                    Default Branch
                  </label>
                  <input
                    id="project-branch-input"
                    type="text"
                    value={newDefaultBranch}
                    onChange={(e) => setNewDefaultBranch(e.target.value)}
                    placeholder="main"
                    style={{
                      width: '100%',
                      backgroundColor: 'var(--bg-surface)',
                      border: '1px solid var(--border-strong)',
                      color: 'var(--text-main)',
                    }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-sm)', marginTop: 'var(--space-sm)' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setIsCreateModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isSubmitting || !newName.trim()}
                >
                  {isSubmitting ? 'Creating...' : 'Create Project'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
