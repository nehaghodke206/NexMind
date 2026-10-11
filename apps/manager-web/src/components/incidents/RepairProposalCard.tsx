import React, { useState } from 'react';
import { RepairProposal, ValidationRun } from '../../api/types';
import { StatusChip } from '../common/StatusChip';
import { DiffViewer } from './DiffViewer';
import { ApproveModal } from './ApproveModal';

interface RepairProposalCardProps {
  proposal: RepairProposal;
  validationRun: ValidationRun | null;
  onApprove: (comment: string) => Promise<void>;
}

export const RepairProposalCard: React.FC<RepairProposalCardProps> = ({
  proposal,
  validationRun,
  onApprove,
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isApproving, setIsApproving] = useState(false);

  const diffContent = proposal.patch?.content || proposal.diff_preview || '';
  const validationPassed = validationRun?.status === 'passed' || validationRun?.result === 'passed';
  const isApproved = proposal.status === 'approved';
  const isApplied = proposal.status === 'applied';

  const handleConfirmApproval = async (comment: string) => {
    setIsApproving(true);
    try {
      await onApprove(comment);
    } finally {
      setIsApproving(false);
    }
  };

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-sm)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
          <h3 style={{ fontSize: '1.125rem', fontWeight: 600 }}>Repair Proposal</h3>
          <StatusChip status={proposal.status} type="repair" />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
          {proposal.risk_level && (
            <span
              style={{
                fontSize: '0.75rem',
                fontWeight: 700,
                textTransform: 'uppercase',
                padding: '2px 8px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor:
                  proposal.risk_level === 'high'
                    ? 'rgba(239, 68, 68, 0.15)'
                    : proposal.risk_level === 'medium'
                    ? 'rgba(234, 179, 8, 0.15)'
                    : 'rgba(34, 197, 94, 0.15)',
                color:
                  proposal.risk_level === 'high'
                    ? '#fca5a5'
                    : proposal.risk_level === 'medium'
                    ? '#fef08a'
                    : '#86efac',
                border: `1px solid ${
                  proposal.risk_level === 'high'
                    ? 'var(--sev-critical-border)'
                    : proposal.risk_level === 'medium'
                    ? 'var(--sev-medium-border)'
                    : '#22c55e'
                }`,
              }}
            >
              Risk: {proposal.risk_level}
            </span>
          )}
        </div>
      </div>

      {/* Meta info */}
      <div style={{ fontSize: '0.875rem', display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)' }}>
        <p><strong>Rationale:</strong> {proposal.rationale}</p>
        {proposal.strategy && (
          <p style={{ color: 'var(--text-muted)' }}>
            <strong>Strategy:</strong> <code style={{ color: '#93c5fd' }}>{proposal.strategy}</code>
          </p>
        )}
      </div>

      {/* Unified Diff */}
      <div>
        <h4 style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 'var(--space-xs)' }}>
          Candidate Patch Diff
        </h4>
        <DiffViewer diffText={diffContent} />
      </div>

      {/* Validation Result Box */}
      <div
        style={{
          backgroundColor: 'var(--bg-app)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          padding: 'var(--space-md)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-sm)' }}>
          <h4 style={{ fontSize: '0.875rem', fontWeight: 600 }}>Automated Validation Run</h4>
          {validationRun && (
            <span
              style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                padding: '2px 8px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: validationPassed ? 'rgba(34, 197, 94, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                color: validationPassed ? '#86efac' : '#fca5a5',
              }}
            >
              {validationPassed ? '✓ PASSED' : '✕ FAILED'}
            </span>
          )}
        </div>

        {validationRun ? (
          <div style={{ fontSize: '0.8125rem', display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)' }}>
            <div>
              Tests: <strong>{validationRun.tests_passed ?? 0} passed</strong>,{' '}
              <strong>{validationRun.tests_failed ?? 0} failed</strong> (total: {validationRun.tests_total ?? 0})
            </div>
            {validationRun.summary && (
              <p style={{ color: 'var(--text-muted)' }}>{validationRun.summary}</p>
            )}
            {validationRun.output && (
              <pre
                style={{
                  marginTop: 'var(--space-xs)',
                  padding: 'var(--space-sm)',
                  backgroundColor: '#030712',
                  borderRadius: 'var(--radius-sm)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.75rem',
                  overflowX: 'auto',
                  maxHeight: '160px',
                  color: '#94a3b8',
                }}
              >
                {validationRun.output}
              </pre>
            )}
          </div>
        ) : (
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
            No validation run results available for this proposal.
          </p>
        )}
      </div>

      {/* Action Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--space-md)' }}>
        <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
          {isApplied ? (
            <span style={{ color: '#86efac', fontWeight: 600 }}>✓ Patch applied to repository</span>
          ) : isApproved ? (
            <span style={{ color: '#93c5fd', fontWeight: 600 }}>✓ Review approved. Ready for application.</span>
          ) : !validationPassed ? (
            <span style={{ color: '#fca5a5' }}>⚠ Tests must pass before approving</span>
          ) : (
            <span>Ready for manager review sign-off</span>
          )}
        </div>

        {!isApproved && !isApplied && (
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setIsModalOpen(true)}
            disabled={!validationPassed}
            style={{ backgroundColor: validationPassed ? '#059669' : undefined }}
          >
            Review & Approve Repair...
          </button>
        )}
      </div>

      <ApproveModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onConfirm={handleConfirmApproval}
        proposal={proposal}
        validationRun={validationRun}
        isApproving={isApproving}
      />
    </div>
  );
};
