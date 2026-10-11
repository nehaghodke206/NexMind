import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import { Incident, Severity, IncidentStatus, Dependency, Project } from '../api/types';
import { SeverityBadge } from '../components/common/Badge';
import { StatusChip } from '../components/common/StatusChip';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';

export const IncidentListPage: React.FC = () => {
  const { projectId: routeProjectId } = useParams<{ projectId?: string }>();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>(routeProjectId || 'proj_demo_shop');
  const [dependencies, setDependencies] = useState<Dependency[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [severityFilter, setSeverityFilter] = useState<Severity | 'all'>('all');
  const [statusFilter, setStatusFilter] = useState<IncidentStatus | 'all'>('all');
  const [dependencyFilter, setDependencyFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Sync route param with state
  useEffect(() => {
    if (routeProjectId) {
      setSelectedProjectId(routeProjectId);
    }
  }, [routeProjectId]);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [projList, deps, incs] = await Promise.all([
        api.getProjects(),
        api.getDependencies(selectedProjectId),
        api.getIncidents(selectedProjectId),
      ]);
      setProjects(projList);
      setDependencies(deps);
      setIncidents(incs);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch incident data');
    } finally {
      setLoading(false);
    }
  }, [selectedProjectId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const filteredIncidents = useMemo(() => {
    return incidents.filter((inc) => {
      if (severityFilter !== 'all' && inc.severity !== severityFilter) return false;
      if (statusFilter !== 'all' && inc.status !== statusFilter) return false;
      if (dependencyFilter !== 'all' && inc.dependency_id !== dependencyFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchTitle = inc.title.toLowerCase().includes(q);
        const matchDesc = inc.description?.toLowerCase().includes(q);
        const matchFp = inc.fingerprint?.toLowerCase().includes(q);
        const matchFile = inc.affected_files.some((f) => f.toLowerCase().includes(q));
        if (!matchTitle && !matchDesc && !matchFp && !matchFile) return false;
      }
      return true;
    });
  }, [incidents, severityFilter, statusFilter, dependencyFilter, searchQuery]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xl)' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-md)' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: 'var(--space-xs)' }}>
            Detected Incidents
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9375rem' }}>
            Review breaking third-party API changes, impact diagnostics, and automated repairs.
          </p>
        </div>

        {/* Project Context Selector */}
        {projects.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
            <label htmlFor="project-select" style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
              Project:
            </label>
            <select
              id="project-select"
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

      {/* Filter Toolbar */}
      <div
        className="card"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 'var(--space-md)',
          padding: 'var(--space-md)',
        }}
      >
        <div>
          <label htmlFor="search-input" style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
            Search Keyword / File
          </label>
          <input
            id="search-input"
            type="search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by title, file, fingerprint..."
            style={{
              width: '100%',
              backgroundColor: 'var(--bg-app)',
              border: '1px solid var(--border-strong)',
              color: 'var(--text-main)',
              padding: '6px 10px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.875rem',
            }}
          />
        </div>

        <div>
          <label htmlFor="severity-select" style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
            Filter by Severity
          </label>
          <select
            id="severity-select"
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value as Severity | 'all')}
            style={{
              width: '100%',
              backgroundColor: 'var(--bg-app)',
              border: '1px solid var(--border-strong)',
              color: 'var(--text-main)',
              padding: '6px 10px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.875rem',
            }}
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>

        <div>
          <label htmlFor="status-select" style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
            Filter by Status
          </label>
          <select
            id="status-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as IncidentStatus | 'all')}
            style={{
              width: '100%',
              backgroundColor: 'var(--bg-app)',
              border: '1px solid var(--border-strong)',
              color: 'var(--text-main)',
              padding: '6px 10px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.875rem',
            }}
          >
            <option value="all">All Statuses</option>
            <option value="ready_for_review">Ready for Review</option>
            <option value="analyzing">Analyzing</option>
            <option value="repair_proposed">Repair Proposed</option>
            <option value="validation_failed">Validation Failed</option>
            <option value="approved">Approved</option>
            <option value="resolved">Resolved</option>
            <option value="blocked">Blocked</option>
          </select>
        </div>

        <div>
          <label htmlFor="dependency-select" style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
            Filter by Dependency
          </label>
          <select
            id="dependency-select"
            value={dependencyFilter}
            onChange={(e) => setDependencyFilter(e.target.value)}
            style={{
              width: '100%',
              backgroundColor: 'var(--bg-app)',
              border: '1px solid var(--border-strong)',
              color: 'var(--text-main)',
              padding: '6px 10px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.875rem',
            }}
          >
            <option value="all">All Dependencies</option>
            {dependencies.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Content States */}
      {loading ? (
        <LoadingState message="Loading incidents..." />
      ) : error ? (
        <ErrorState message={error} onRetry={loadData} />
      ) : filteredIncidents.length === 0 ? (
        <EmptyState
          title="No Matching Incidents"
          description="No incidents match the active filters or search terms. Try clearing filters to see all events."
          actionText="Clear Filters"
          onAction={() => {
            setSeverityFilter('all');
            setStatusFilter('all');
            setDependencyFilter('all');
            setSearchQuery('');
          }}
        />
      ) : (
        <div className="table-wrapper">
          <table className="data-table" aria-label="Incident List">
            <thead>
              <tr>
                <th scope="col" style={{ width: '120px' }}>Severity</th>
                <th scope="col">Incident Title</th>
                <th scope="col" style={{ width: '150px' }}>Status</th>
                <th scope="col" style={{ width: '180px' }}>Affected Files</th>
                <th scope="col" style={{ width: '140px' }}>Detected</th>
                <th scope="col" style={{ width: '120px', textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredIncidents.map((inc) => (
                <tr key={inc.id}>
                  <td>
                    <SeverityBadge severity={inc.severity} />
                  </td>
                  <td>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                      <Link
                        to={`/incidents/${inc.id}`}
                        style={{ fontWeight: 600, color: 'var(--text-main)', textDecoration: 'none' }}
                      >
                        {inc.title}
                      </Link>
                      {inc.description && (
                        <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                          {inc.description}
                        </span>
                      )}
                      {inc.fingerprint && (
                        <span
                          style={{
                            fontSize: '0.75rem',
                            fontFamily: 'var(--font-mono)',
                            color: 'var(--text-faint)',
                          }}
                        >
                          fingerprint: {inc.fingerprint}
                        </span>
                      )}
                    </div>
                  </td>
                  <td>
                    <StatusChip status={inc.status} />
                  </td>
                  <td>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                      <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                        {inc.affected_files.length} file{inc.affected_files.length === 1 ? '' : 's'}
                      </span>
                      {inc.affected_files[0] && (
                        <code style={{ fontSize: '0.75rem', color: '#93c5fd' }}>
                          {inc.affected_files[0]}
                        </code>
                      )}
                    </div>
                  </td>
                  <td>
                    <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                      {new Date(inc.created_at).toLocaleDateString()}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <Link
                      to={`/incidents/${inc.id}`}
                      className="btn btn-secondary"
                      style={{ fontSize: '0.8125rem', padding: '4px 10px' }}
                    >
                      Inspect →
                    </Link>
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
