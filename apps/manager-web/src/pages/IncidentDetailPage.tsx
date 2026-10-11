import React, { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import { Incident, RepairProposal, ValidationRun, Observation } from '../api/types';
import { SeverityBadge } from '../components/common/Badge';
import { StatusChip } from '../components/common/StatusChip';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EvidenceViewer } from '../components/incidents/EvidenceViewer';
import { RepairProposalCard } from '../components/incidents/RepairProposalCard';

export const IncidentDetailPage: React.FC = () => {
  const { incidentId } = useParams<{ incidentId: string }>();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [repairProposal, setRepairProposal] = useState<RepairProposal | null>(null);
  const [validationRun, setValidationRun] = useState<ValidationRun | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const loadIncidentDetail = useCallback(async () => {
    if (!incidentId) return;
    setLoading(true);
    setError(null);
    try {
      const [inc, obsList] = await Promise.all([
        api.getIncident(incidentId),
        api.getIncidentObservations(incidentId),
      ]);
      setIncident(inc);
      setObservations(obsList);

      // Attempt loading repair proposal
      const proposal = await api.getRepairProposal(incidentId);
      setRepairProposal(proposal);

      if (proposal) {
        const valRun = await api.getValidationRun(proposal.id);
        setValidationRun(valRun);
      } else {
        setValidationRun(null);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load incident detail');
    } finally {
      setLoading(false);
    }
  }, [incidentId]);

  useEffect(() => {
    loadIncidentDetail();
  }, [loadIncidentDetail]);

  const handleApproveRepair = async (comment: string) => {
    if (!repairProposal) return;
    await api.approveRepairProposal(repairProposal.id, comment);
    setActionSuccess('Repair proposal approved successfully. Authorized for deployment by developer or agent.');
    await loadIncidentDetail();
  };

  const handleRejectRepair = async (reason: string) => {
    if (!repairProposal) return;
    await api.rejectRepairProposal(repairProposal.id, reason);
    setActionSuccess('Repair proposal rejected with reviewer feedback.');
    await loadIncidentDetail();
  };

  if (loading) return <LoadingState message="Scanning incident telemetry & evidence graph..." />;
  if (error || !incident) {
    return (
      <ErrorState
        title="Incident Record Not Found"
        message={error || `Could not retrieve incident details for ${incidentId}.`}
        onRetry={loadIncidentDetail}
      />
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xl)' }}>
      {/* Breadcrumb Navigation */}
      <div>
        <Link
          to={`/projects/${incident.project_id}/incidents`}
          style={{
            fontSize: '0.875rem',
            fontWeight: 600,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            color: 'var(--brand-primary)',
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          <span>Back to Incident Radar</span>
        </Link>
      </div>

      {actionSuccess && (
        <div className="alert-banner alert-info" role="status">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          <div style={{ flex: 1, fontWeight: 500 }}>{actionSuccess}</div>
          <button
            type="button"
            onClick={() => setActionSuccess(null)}
            style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '1rem' }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Incident Header Card */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-sm)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
            <SeverityBadge severity={incident.severity} />
            <StatusChip status={incident.status} />
          </div>

          <span
            style={{
              fontSize: '0.75rem',
              color: 'var(--text-faint)',
              fontFamily: 'var(--font-mono)',
              backgroundColor: 'var(--bg-surface-elevated)',
              padding: '2px 8px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            ID: {incident.id}
          </span>
        </div>

        <div>
          <h1 style={{ fontSize: '1.625rem', fontWeight: 700, marginBottom: 'var(--space-xs)', letterSpacing: '-0.02em' }}>
            {incident.title}
          </h1>
          {incident.description && (
            <p style={{ color: 'var(--text-muted)', fontSize: '1rem', lineHeight: 1.6 }}>
              {incident.description}
            </p>
          )}
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: 'var(--space-md)',
            paddingTop: 'var(--space-md)',
            borderTop: '1px solid var(--border-subtle)',
            fontSize: '0.8125rem',
            color: 'var(--text-muted)',
          }}
        >
          <div>
            <strong>Dependency:</strong> <span style={{ color: 'var(--text-main)', fontFamily: 'var(--font-mono)' }}>{incident.dependency_id}</span>
          </div>
          <div>
            <strong>Source Agent:</strong> <span style={{ color: 'var(--text-main)' }}>{incident.source || 'detection-agent'}</span>
          </div>
          <div>
            <strong>Detected At:</strong>{' '}
            <span style={{ color: 'var(--text-main)' }}>
              {new Date(incident.created_at).toLocaleString()}
            </span>
          </div>
          {incident.fingerprint && (
            <div>
              <strong>Fingerprint:</strong>{' '}
              <code style={{ color: 'var(--brand-primary)', backgroundColor: 'var(--bg-surface-elevated)', padding: '1px 6px', borderRadius: '4px', fontSize: '0.75rem' }}>
                {incident.fingerprint}
              </code>
            </div>
          )}
        </div>
      </div>

      {/* Impacted Areas Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 'var(--space-lg)' }}>
        {/* Affected Files */}
        <div className="card">
          <h3 style={{ fontSize: '1rem', fontWeight: 700, letterSpacing: '-0.01em', marginBottom: 'var(--space-sm)' }}>
            Affected Repository Files ({incident.affected_files.length})
          </h3>
          {incident.affected_files.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>No affected files identified.</p>
          ) : (
            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)' }}>
              {incident.affected_files.map((file, idx) => (
                <li
                  key={idx}
                  style={{
                    backgroundColor: 'var(--bg-surface-elevated)',
                    border: '1px solid var(--border-subtle)',
                    padding: '6px 12px',
                    borderRadius: 'var(--radius-sm)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.8125rem',
                    color: 'var(--text-main)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                  }}
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
                    <polyline points="13 2 13 9 20 9"/>
                  </svg>
                  <span>{file}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Affected Workflows */}
        <div className="card">
          <h3 style={{ fontSize: '1rem', fontWeight: 700, letterSpacing: '-0.01em', marginBottom: 'var(--space-sm)' }}>
            Impacted User Workflows ({incident.affected_workflows.length})
          </h3>
          {incident.affected_workflows.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>No impacted workflows specified.</p>
          ) : (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-xs)' }}>
              {incident.affected_workflows.map((wf, idx) => (
                <span
                  key={idx}
                  style={{
                    backgroundColor: 'var(--status-review-bg)',
                    border: '1px solid var(--status-review-border)',
                    padding: '4px 10px',
                    borderRadius: 'var(--radius-full)',
                    fontSize: '0.8125rem',
                    fontWeight: 600,
                    color: 'var(--status-review-text)',
                  }}
                >
                  {wf}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Raw Scanner Observations (GET /incidents/:id/observations) */}
      {observations.length > 0 && (
        <div className="card">
          <h3 style={{ fontSize: '1rem', fontWeight: 700, letterSpacing: '-0.01em', marginBottom: 'var(--space-sm)' }}>
            Scanner Observations (API: <code>GET /incidents/:id/observations</code>)
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
            {observations.map((obs) => (
              <div
                key={obs.id}
                style={{
                  backgroundColor: 'var(--diff-bg)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  padding: 'var(--space-md)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ fontWeight: 700, fontSize: '0.875rem' }}>
                    Type: <code style={{ color: 'var(--brand-primary)' }}>{obs.observation_type}</code> ({obs.method || 'GET'} {obs.endpoint || ''})
                  </span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {new Date(obs.observed_at).toLocaleString()}
                  </span>
                </div>
                <pre
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.75rem',
                    backgroundColor: 'var(--bg-surface)',
                    padding: '8px',
                    borderRadius: '4px',
                    border: '1px solid var(--border-subtle)',
                    overflowX: 'auto',
                    margin: 0,
                  }}
                >
                  {JSON.stringify(obs.payload, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Evidence Inspector */}
      <EvidenceViewer
        evidence={incident.evidence}
        confidence={incident.confidence}
        status={incident.status}
      />

      {/* Repair Proposal Section */}
      {repairProposal ? (
        <RepairProposalCard
          proposal={repairProposal}
          validationRun={validationRun}
          onApprove={handleApproveRepair}
          onReject={handleRejectRepair}
        />
      ) : (
        <div className="card" style={{ textAlign: 'center', padding: 'var(--space-xl)' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 'var(--space-xs)' }}>
            No Repair Proposal Generated Yet
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            The automated repair agent has not submitted candidate patches for this incident yet.
          </p>
        </div>
      )}
    </div>
  );
};
