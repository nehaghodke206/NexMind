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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xl)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-md)' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: 'var(--space-xs)' }}>
            Project Activity Feed
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9375rem' }}>
            Real-time chronological timeline of schema scans, detections, automated validations, and review actions.
          </p>
        </div>

        {projects.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
            <label htmlFor="activity-project-select" style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
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
                padding: 'var(--space-xs) var(--space-md)',
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
        <LoadingState message="Loading activity timeline..." />
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
            {activities.map((act) => (
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
                    borderRadius: '50%',
                    backgroundColor: 'var(--bg-app)',
                    border: '1px solid var(--border-strong)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.875rem',
                    flexShrink: 0,
                  }}
                  aria-hidden="true"
                >
                  {act.event_type.includes('detect')
                    ? '🔍'
                    : act.event_type.includes('repair')
                    ? '🛠'
                    : act.event_type.includes('validation')
                    ? '🧪'
                    : '📋'}
                </div>

                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '2px' }}>
                    <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-main)' }}>
                      {act.event_type.replace(/_/g, ' ').toUpperCase()}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-faint)' }}>
                      {new Date(act.created_at).toLocaleString()}
                    </span>
                  </div>
                  <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                    {act.message}
                  </p>
                  {act.actor_id && (
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-faint)', fontFamily: 'var(--font-mono)' }}>
                      Actor: {act.actor_id}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
