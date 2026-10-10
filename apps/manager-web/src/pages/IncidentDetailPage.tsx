import React, { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import { Incident, RepairProposal, ValidationRun } from '../api/types';
import { SeverityBadge } from '../components/common/Badge';
import { StatusChip } from '../components/common/StatusChip';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EvidenceViewer } from '../components/incidents/EvidenceViewer';
import { RepairProposalCard } from '../components/incidents/RepairProposalCard';

export const IncidentDetailPage: React.FC = () => {
  const { incidentId } = useParams<{ incidentId: string }>();
  const [incident, setIncident] = useState<Incident | null>(null);
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
      const inc = await api.getIncident(incidentId);
      setIncident(inc);

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
    setActionSuccess('Repair proposal approved successfully. Ready for deployment by developer or agent.');
    // Reload data to reflect updated status
    await loadIncidentDetail();
  };

  if (loading) return <LoadingState message="Loading incident diagnosis & evidence..." />;
  if (error || !incident) {
    return (
      <ErrorState
        title="Incident Not Found"
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
          style={{ fontSize: '0.875rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
        >
          ← Back to Incident List
        </Link>
      </div>

      {actionSuccess && (
        <div className="alert-banner alert-info" role="status">
          <span aria-hidden="true">✓</span>
          <div style={{ flex: 1 }}>{actionSuccess}</div>
          <button
            type="button"
            onClick={() => setActionSuccess(null)}
            style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}
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

          <span style={{ fontSize: '0.8125rem', color: 'var(--text-faint)', fontFamily: 'var(--font-mono)' }}>
            ID: {incident.id}
          </span>
        </div>

        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 'var(--space-xs)' }}>
            {incident.title}
          </h1>
          {incident.description && (
            <p style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>
              {incident.description}
            </p>
          )}
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: 'var(--space-md)',
            paddingTop: 'var(--space-sm)',
            borderTop: '1px solid var(--border-subtle)',
            fontSize: '0.8125rem',
            color: 'var(--text-muted)',
          }}
        >
          <div>
            <strong>Dependency:</strong> <span style={{ color: 'var(--text-main)' }}>{incident.dependency_id}</span>
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
              <code style={{ color: '#93c5fd', fontSize: '0.75rem' }}>{incident.fingerprint}</code>
            </div>
          )}
        </div>
      </div>

      {/* Impacted Areas Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 'var(--space-lg)' }}>
        {/* Affected Files */}
        <div className="card">
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 'var(--space-sm)' }}>
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
                    backgroundColor: 'var(--bg-app)',
                    border: '1px solid var(--border-subtle)',
                    padding: 'var(--space-xs) var(--space-sm)',
                    borderRadius: 'var(--radius-sm)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.8125rem',
                    color: '#93c5fd',
                  }}
                >
                  📄 {file}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Affected Workflows */}
        <div className="card">
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 'var(--space-sm)' }}>
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
                    backgroundColor: 'var(--bg-surface-elevated)',
                    border: '1px solid var(--border-strong)',
                    padding: '4px 10px',
                    borderRadius: 'var(--radius-full)',
                    fontSize: '0.8125rem',
                    color: 'var(--text-main)',
                  }}
                >
                  ⚡ {wf}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

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
        />
      ) : (
        <div className="card" style={{ textAlign: 'center', padding: 'var(--space-xl)' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 'var(--space-xs)' }}>
            No Repair Proposal Generated Yet
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            The repair agent has not submitted candidate patches for this incident yet.
          </p>
        </div>
      )}
    </div>
  );
};
