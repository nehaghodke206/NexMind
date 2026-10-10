import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { Project, Incident } from '../api/types';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';

export const ProjectListPage: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [incidentCounts, setIncidentCounts] = useState<Record<string, { total: number; critical: number; review: number }>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadProjects = async () => {
    setLoading(true);
    setError(null);
    try {
      const projList = await api.getProjects();
      setProjects(projList);

      // Load summary incident counts for each project
      const counts: Record<string, { total: number; critical: number; review: number }> = {};
      for (const p of projList) {
        try {
          const incs: Incident[] = await api.getIncidents(p.id);
          counts[p.id] = {
            total: incs.length,
            critical: incs.filter((i) => i.severity === 'critical' || i.severity === 'high').length,
            review: incs.filter((i) => i.status === 'ready_for_review').length,
          };
        } catch {
          counts[p.id] = { total: 0, critical: 0, review: 0 };
        }
      }
      setIncidentCounts(counts);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load projects');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  if (loading) return <LoadingState message="Loading monitored projects..." />;
  if (error) return <ErrorState message={error} onRetry={loadProjects} />;
  if (projects.length === 0) {
    return (
      <EmptyState
        title="No Monitored Projects"
        description="There are currently no active projects configured for dependency guardian monitoring."
      />
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xl)' }}>
      <div>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: 'var(--space-xs)' }}>
          Monitored Projects
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9375rem' }}>
          Select a project to review detected API schema drifts, active incidents, and automated repair proposals.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: 'var(--space-lg)' }}>
        {projects.map((p) => {
          const stats = incidentCounts[p.id] || { total: 0, critical: 0, review: 0 };
          return (
            <div key={p.id} className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-sm)' }}>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>{p.name}</h2>
                  <span
                    style={{
                      fontSize: '0.75rem',
                      fontFamily: 'var(--font-mono)',
                      color: 'var(--text-faint)',
                    }}
                  >
                    {p.id}
                  </span>
                </div>

                <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: 'var(--space-md)' }}>
                  {p.description || 'No description provided.'}
                </p>

                {p.repository_url && (
                  <p style={{ fontSize: '0.8125rem', color: 'var(--text-faint)', marginBottom: 'var(--space-md)' }}>
                    Repository: <span style={{ fontFamily: 'var(--font-mono)' }}>{p.repository_url}</span>
                  </p>
                )}

                {/* Metric indicators */}
                <div style={{ display: 'flex', gap: 'var(--space-sm)', margin: 'var(--space-md) 0', flexWrap: 'wrap' }}>
                  <div
                    style={{
                      flex: 1,
                      minWidth: '90px',
                      backgroundColor: 'var(--bg-app)',
                      padding: 'var(--space-sm)',
                      borderRadius: 'var(--radius-sm)',
                      textAlign: 'center',
                    }}
                  >
                    <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{stats.total}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Incidents</div>
                  </div>

                  <div
                    style={{
                      flex: 1,
                      minWidth: '90px',
                      backgroundColor: 'rgba(239, 68, 68, 0.1)',
                      border: '1px solid rgba(239, 68, 68, 0.2)',
                      padding: 'var(--space-sm)',
                      borderRadius: 'var(--radius-sm)',
                      textAlign: 'center',
                    }}
                  >
                    <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fca5a5' }}>
                      {stats.critical}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#fca5a5' }}>High/Crit</div>
                  </div>

                  <div
                    style={{
                      flex: 1,
                      minWidth: '90px',
                      backgroundColor: 'rgba(20, 184, 166, 0.1)',
                      border: '1px solid rgba(20, 184, 166, 0.2)',
                      padding: 'var(--space-sm)',
                      borderRadius: 'var(--radius-sm)',
                      textAlign: 'center',
                    }}
                  >
                    <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#99f6e4' }}>
                      {stats.review}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#99f6e4' }}>Review Ready</div>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 'var(--space-sm)', marginTop: 'var(--space-md)' }}>
                <Link
                  to={`/projects/${p.id}/incidents`}
                  className="btn btn-primary"
                  style={{ flex: 1, textAlign: 'center' }}
                >
                  View Incidents
                </Link>
                <Link
                  to={`/projects/${p.id}/activity`}
                  className="btn btn-secondary"
                  style={{ textAlign: 'center' }}
                >
                  Activity
                </Link>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
