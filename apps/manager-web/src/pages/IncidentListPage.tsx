import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import { Incident, Severity, IncidentStatus, Dependency, Project } from '../api/types';
import { SeverityBadge } from '../components/common/Badge';
import { StatusChip } from '../components/common/StatusChip';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';

const SEVERITY_TABS: Array<{ id: Severity | 'all'; label: string }> = [
  { id: 'all', label: 'All' },
  { id: 'critical', label: 'Critical' },
  { id: 'high', label: 'High' },
  { id: 'medium', label: 'Medium' },
  { id: 'low', label: 'Low' },
];

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

  const activeSeverityIndex = SEVERITY_TABS.findIndex((tab) => tab.id === severityFilter);

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
              ACTIVE DRIFT RADAR
            </span>
          </div>
          <h1 style={{ fontSize: '1.875rem', fontWeight: 700, marginBottom: 'var(--space-xs)', letterSpacing: '-0.02em' }}>
            Detected Incidents
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9375rem' }}>
            Review breaking third-party API changes, impact diagnostics, and automated repairs.
          </p>
        </div>

        {/* Project Context Selector */}
        {projects.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
            <label htmlFor="project-select" style={{ fontSize: '0.875rem', color: 'var(--text-muted)', fontWeight: 600 }}>
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
                padding: '8px 14px',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem',
                fontFamily: 'inherit',
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

      {/* Filter Card */}
      <div
        className="card"
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-md)',
          padding: 'var(--space-lg)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-sm)' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Filter By Severity Level
          </span>

          {/* Severity Filter Tabs */}
          <div
            className="liquid-track liquid-severity-track"
            role="tablist"
            aria-label="Severity Filter Slider"
          >
            <div
              className="liquid-melt-glider"
              aria-hidden="true"
              style={{
                width: `calc((100% - 6px) / ${SEVERITY_TABS.length})`,
                transform: `translateX(${activeSeverityIndex * 100}%)`,
              }}
            >
              <div className="liquid-glider-specular" />
            </div>

            {SEVERITY_TABS.map((tab) => {
              const isActive = tab.id === severityFilter;
              return (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  onClick={() => setSeverityFilter(tab.id)}
                  className={`liquid-tab-btn ${isActive ? 'active' : ''}`}
                >
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Query & Dropdown Filters */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: 'var(--space-md)',
            borderTop: '1px solid var(--border-subtle)',
            paddingTop: 'var(--space-md)',
          }}
        >
          <div>
            <label htmlFor="search-input" style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '6px' }}>
              Search Keyword / File
            </label>
            <input
              id="search-input"
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search title, file, fingerprint..."
              style={{
                width: '100%',
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-strong)',
                color: 'var(--text-main)',
                padding: '8px 12px',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem',
                fontFamily: 'inherit',
              }}
            />
          </div>

          <div>
            <label htmlFor="status-select" style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '6px' }}>
              Filter by Status
            </label>
            <select
              id="status-select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as IncidentStatus | 'all')}
              style={{
                width: '100%',
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-strong)',
                color: 'var(--text-main)',
                padding: '8px 12px',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem',
                fontFamily: 'inherit',
                cursor: 'pointer',
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
            <label htmlFor="dependency-select" style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '6px' }}>
              Filter by Dependency
            </label>
            <select
              id="dependency-select"
              value={dependencyFilter}
              onChange={(e) => setDependencyFilter(e.target.value)}
              style={{
                width: '100%',
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-strong)',
                color: 'var(--text-main)',
                padding: '8px 12px',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem',
                fontFamily: 'inherit',
                cursor: 'pointer',
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
      </div>

      {/* Content States */}
      {loading ? (
        <LoadingState message="Scanning incident radar..." />
      ) : error ? (
        <ErrorState message={error} onRetry={loadData} />
      ) : filteredIncidents.length === 0 ? (
        <EmptyState
          title="No Incidents Match Filters"
          description="All dependencies are healthy under the selected filter criteria. Clear filters to see full history."
          actionText="Reset Filters"
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
                <th scope="col" style={{ width: '130px' }}>Severity</th>
                <th scope="col">Incident Title</th>
                <th scope="col" style={{ width: '160px' }}>Status</th>
                <th scope="col" style={{ width: '190px' }}>Affected Target</th>
                <th scope="col" style={{ width: '130px' }}>Detected</th>
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
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                      <Link
                        to={`/incidents/${inc.id}`}
                        style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '0.9375rem' }}
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
                            color: 'var(--brand-primary)',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          <span style={{ opacity: 0.6 }}>fp:</span> {inc.fingerprint}
                        </span>
                      )}
                    </div>
                  </td>
                  <td>
                    <StatusChip status={inc.status} />
                  </td>
                  <td>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {inc.affected_files.length} file{inc.affected_files.length === 1 ? '' : 's'}
                      </span>
                      {inc.affected_files[0] && (
                        <code style={{ fontSize: '0.75rem', color: 'var(--brand-secondary)', fontFamily: 'var(--font-mono)' }}>
                          {inc.affected_files[0]}
                        </code>
                      )}
                    </div>
                  </td>
                  <td>
                    <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      {new Date(inc.created_at).toLocaleDateString()}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <Link
                      to={`/incidents/${inc.id}`}
                      className="btn btn-secondary"
                      style={{ fontSize: '0.8125rem', padding: '6px 12px', gap: '4px' }}
                    >
                      <span>Inspect</span>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <polyline points="9 18 15 12 9 6"/>
                      </svg>
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
