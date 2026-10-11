import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../api/client';
import { ActivityEvent, Project } from '../api/types';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';

export const ActivityFeedPage: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('proj_demo_shop');
  const [activities, setActivities] = useState<ActivityEvent[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [projList, acts] = await Promise.all([
        api.getProjects(),
        api.getActivity(selectedProjectId),
      ]);
      setProjects(projList);
      setActivities(acts);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load activity feed');
    } finally {
      setLoading(false);
    }
  }, [selectedProjectId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const getEventBadge = (type: string) => {
    if (type.includes('detect')) {
      return {
        label: 'Detection',
        color: 'var(--brand-primary)',
        border: 'var(--sev-critical-border)',
        bg: 'var(--sev-critical-bg)',
      };
    }
    if (type.includes('repair')) {
      return {
        label: 'Repair',
        color: 'var(--sev-high-text)',
        border: 'var(--sev-high-border)',
        bg: 'var(--sev-high-bg)',
      };
    }
    if (type.includes('validation')) {
      return {
        label: 'Validation',
        color: 'var(--status-review-text)',
        border: 'var(--status-review-border)',
        bg: 'var(--status-review-bg)',
      };
    }
    return {
      label: 'System',
      color: 'var(--text-muted)',
      border: 'var(--border-subtle)',
      bg: 'var(--bg-surface-elevated)',
    };
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xl)' }}>
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
              LIVE AUDIT LOG
            </span>
          </div>
          <h1 style={{ fontSize: '1.875rem', fontWeight: 700, marginBottom: 'var(--space-xs)', letterSpacing: '-0.02em' }}>
            Project Activity Feed
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9375rem' }}>
            Chronological audit stream of schema scans, detections, automated validations, and review actions (<code>GET /projects/:id/activity</code>).
          </p>
        </div>

        {projects.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
            <label htmlFor="activity-project-select" style={{ fontSize: '0.875rem', color: 'var(--text-muted)', fontWeight: 600 }}>
              Project:
            </label>
            <select
              id="activity-project-select"
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
              style={{
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-strong)',
                color: 'var(--text-main)',
                padding: '8px 14px',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem',
              }}
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {loading ? (
        <LoadingState message="Streaming activity events..." />
      ) : error ? (
        <ErrorState message={error} onRetry={loadData} />
      ) : activities.length === 0 ? (
        <EmptyState
          title="No Recent Activity"
          description="There are no recorded scan runs or incident events for this project yet."
        />
      ) : (
        <div className="card" style={{ padding: 'var(--space-xl)' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }}>
            {activities.map((act) => {
              const badge = getEventBadge(act.event_type);
              return (
                <div
                  key={act.id}
                  style={{
                    display: 'flex',
                    gap: 'var(--space-md)',
                    alignItems: 'flex-start',
                    borderBottom: '1px solid var(--border-subtle)',
                    paddingBottom: 'var(--space-md)',
                  }}
                >
                  <div
                    style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: 'var(--radius-md)',
                      backgroundColor: badge.bg,
                      border: `1px solid ${badge.border}`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                      color: badge.color,
                    }}
                    aria-hidden="true"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
                    </svg>
                  </div>

                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px', flexWrap: 'wrap', gap: '4px' }}>
                      <span
                        style={{
                          fontSize: '0.8125rem',
                          fontWeight: 700,
                          letterSpacing: '0.04em',
                          color: badge.color,
                          textTransform: 'uppercase',
                        }}
                      >
                        {act.event_type.replace(/_/g, ' ')}
                      </span>
                      <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-faint)' }}>
                        {new Date(act.created_at).toLocaleString()}
                      </span>
                    </div>
                    <p style={{ fontSize: '0.9375rem', color: 'var(--text-main)', marginBottom: '4px', lineHeight: 1.5 }}>
                      {act.message}
                    </p>
                    {act.actor_id && (
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-faint)', fontFamily: 'var(--font-mono)' }}>
                        Actor: <span style={{ color: 'var(--text-muted)' }}>{act.actor_id}</span>
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
