import React, { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api/client';
import { ScanRun, Project, Dependency } from '../api/types';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';

export const ScansPage: React.FC = () => {
  const { projectId: routeProjectId } = useParams<{ projectId?: string }>();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>(routeProjectId || 'proj_demo_shop');
  const [dependencies, setDependencies] = useState<Dependency[]>([]);
  const [scans, setScans] = useState<ScanRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Trigger scan state
  const [selectedDepId, setSelectedDepId] = useState<string>('all');
  const [isTriggering, setIsTriggering] = useState(false);
  const [triggerSuccess, setTriggerSuccess] = useState<string | null>(null);

  const loadScans = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [projList, deps, scanList] = await Promise.all([
        api.getProjects(),
        api.getDependencies(selectedProjectId),
        api.getScans(selectedProjectId),
      ]);
      setProjects(projList);
      setDependencies(deps);
      setScans(scanList);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load scanner history');
    } finally {
      setLoading(false);
    }
  }, [selectedProjectId]);

  useEffect(() => {
    loadScans();
  }, [loadScans]);

  const handleTriggerScan = async () => {
    setIsTriggering(true);
    setTriggerSuccess(null);
    try {
      const depArg = selectedDepId === 'all' ? undefined : selectedDepId;
      const newScan = await api.triggerScan(selectedProjectId, depArg);
      setScans((prev) => [newScan, ...prev]);
      setTriggerSuccess(`Scan #${newScan.id} launched successfully. Analyzing response shape drift.`);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to launch scan');
    } finally {
      setIsTriggering(false);
    }
  };

  const getStatusChip = (status: string) => {
    switch (status) {
      case 'completed':
        return <span className="status-chip status-resolved">COMPLETED</span>;
      case 'running':
        return <span className="status-chip status-analyzing">RUNNING</span>;
      case 'failed':
        return <span className="status-chip status-failed">FAILED</span>;
      case 'queued':
      default:
        return <span className="status-chip status-open">{status.toUpperCase()}</span>;
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
              ACTIVE DRIFT SCANNER
            </span>
          </div>
          <h1 style={{ fontSize: '1.875rem', fontWeight: 700, marginBottom: 'var(--space-xs)', letterSpacing: '-0.02em' }}>
            Scanner Runs & Probes
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9375rem' }}>
            Continuous contract observation probes and automated schema drift discovery runs (<code>GET/POST /projects/:id/scans</code>).
          </p>
        </div>

        {/* Project Context Selector */}
        {projects.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
            <label htmlFor="project-select-scan" style={{ fontSize: '0.875rem', color: 'var(--text-muted)', fontWeight: 600 }}>
              Project:
            </label>
            <select
              id="project-select-scan"
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
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
          </div>
        )}
      </div>

      {/* Trigger Probe Control Card */}
      <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-md)', padding: 'var(--space-lg)' }}>
        <div>
          <h2 style={{ fontSize: '1.125rem', fontWeight: 700, marginBottom: '4px' }}>
            Trigger Active Discovery Probe
          </h2>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
            Execute real-time API contract sampling to discover response changes or broken schemas.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', flexWrap: 'wrap' }}>
          <select
            value={selectedDepId}
            onChange={(e) => setSelectedDepId(e.target.value)}
            style={{ minWidth: '180px' }}
          >
            <option value="all">All Dependencies</option>
            {dependencies.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>

          <button
            type="button"
            className="btn btn-primary"
            onClick={handleTriggerScan}
            disabled={isTriggering}
            style={{ gap: '6px' }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            <span>{isTriggering ? 'Launching Probe...' : 'Execute Probe Scan'}</span>
          </button>
        </div>
      </div>

      {triggerSuccess && (
        <div className="alert-banner alert-info" role="status">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          <div>{triggerSuccess}</div>
        </div>
      )}

      {/* Scan History Table */}
      {loading ? (
        <LoadingState message="Retrieving probe telemetry..." />
      ) : error ? (
        <ErrorState message={error} onRetry={loadScans} />
      ) : scans.length === 0 ? (
        <EmptyState
          title="No Past Scan Runs"
          description="No automated discovery or probe runs have been recorded for this project yet."
          actionText="Execute First Probe"
          onAction={handleTriggerScan}
        />
      ) : (
        <div className="table-wrapper">
          <table className="data-table" aria-label="Scanner Runs">
            <thead>
              <tr>
                <th scope="col" style={{ width: '130px' }}>Status</th>
                <th scope="col" style={{ width: '150px' }}>Scan ID</th>
                <th scope="col">Observation Summary</th>
                <th scope="col" style={{ width: '140px' }}>Initiated By</th>
                <th scope="col" style={{ width: '180px' }}>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {scans.map((s) => (
                <tr key={s.id}>
                  <td>{getStatusChip(s.status)}</td>
                  <td>
                    <code style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8125rem', color: 'var(--brand-primary)' }}>
                      {s.id}
                    </code>
                  </td>
                  <td>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                      <span style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '0.875rem' }}>
                        {s.summary || 'Routine drift verification probe complete.'}
                      </span>
                      {s.error_message && (
                        <span style={{ fontSize: '0.75rem', color: 'var(--brand-primary)' }}>
                          Error: {s.error_message}
                        </span>
                      )}
                    </div>
                  </td>
                  <td>
                    <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                      {s.initiated_by || 'system'}
                    </span>
                  </td>
                  <td>
                    <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      {new Date(s.started_at).toLocaleString()}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

