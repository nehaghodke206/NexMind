import React, { useState } from 'react';
import { RepairProposal, ValidationRun } from '../../api/types';
import { StatusChip } from '../common/StatusChip';
import { DiffViewer } from './DiffViewer';
import { ApproveModal } from './ApproveModal';

interface RepairProposalCardProps {
  proposal: RepairProposal;
  validationRun: ValidationRun | null;
  onApprove: (comment: string) => Promise<void>;
  onReject?: (reason: string) => Promise<void>;
}

export const RepairProposalCard: React.FC<RepairProposalCardProps> = ({
  proposal,
  validationRun,
  onApprove,
  onReject,
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isApproving, setIsApproving] = useState(false);

  const diffContent = proposal.patch?.content || proposal.diff_preview || '';
  const validationPassed = validationRun?.status === 'passed' || validationRun?.result === 'passed';
  const isApproved = proposal.status === 'approved';
  const isApplied = proposal.status === 'applied';
  const isRejected = proposal.status === 'rejected';

  const handleConfirmApproval = async (comment: string) => {
    setIsApproving(true);
    try {
      await onApprove(comment);
    } finally {
      setIsApproving(false);
    }
  };

  const handleConfirmRejection = async (reason: string) => {
    if (!onReject) return;
    setIsApproving(true);
    try {
      await onReject(reason);
    } finally {
      setIsApproving(false);
    }
  };

  const getRiskStyle = (level?: string) => {
    switch (level) {
      case 'critical':
      case 'high':
        return {
          backgroundColor: 'var(--sev-critical-bg)',
          color: 'var(--sev-critical-text)',
          border: '1px solid var(--sev-critical-border)',
        };
      case 'medium':
        return {
          backgroundColor: 'var(--sev-high-bg)',
          color: 'var(--sev-high-text)',
          border: '1px solid var(--sev-high-border)',
        };
      case 'low':
      default:
        return {
          backgroundColor: 'var(--sev-low-bg)',
          color: 'var(--sev-low-text)',
          border: '1px solid var(--sev-low-border)',
        };
    }
  };

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-sm)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
          <h3 style={{ fontSize: '1.125rem', fontWeight: 700, letterSpacing: '-0.01em', margin: 0 }}>
            Automated Repair Proposal
          </h3>
          <StatusChip status={proposal.status} type="repair" />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
          {proposal.risk_level && (
            <span
              style={{
                fontSize: '0.75rem',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
                padding: '3px 10px',
                borderRadius: 'var(--radius-full)',
                ...getRiskStyle(proposal.risk_level),
              }}
            >
              RISK: {proposal.risk_level}
            </span>
          )}
        </div>
      </div>

      {/* Meta info */}
      <div style={{ fontSize: '0.875rem', display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)' }}>
        <p><strong>Rationale:</strong> {proposal.rationale}</p>
        {proposal.strategy && (
          <p style={{ color: 'var(--text-muted)' }}>
            <strong>Strategy:</strong>{' '}
            <code
              style={{
                color: 'var(--brand-primary)',
                backgroundColor: 'var(--bg-surface-elevated)',
                border: '1px solid var(--border-subtle)',
                padding: '2px 8px',
                borderRadius: 'var(--radius-sm)',
                fontFamily: 'var(--font-mono)',
              }}
            >
              {proposal.strategy}
            </code>
          </p>
        )}
      </div>

      {/* Unified Diff */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-xs)' }}>
          <h4 style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', margin: 0 }}>
            Unified Patch Diff
          </h4>
          <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-faint)' }}>
            unified_diff format
          </span>
        </div>
        <DiffViewer diffText={diffContent} />
      </div>

      {/* Validation Result Box */}
      <div
        style={{
          backgroundColor: 'var(--diff-bg)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          padding: 'var(--space-md)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-sm)' }}>
          <h4 style={{ fontSize: '0.875rem', fontWeight: 700, letterSpacing: '-0.01em', margin: 0 }}>
            Automated Validation Suite
          </h4>
          {validationRun && (
            <span
              style={{
                fontSize: '0.75rem',
                fontWeight: 700,
                letterSpacing: '0.04em',
                padding: '2px 10px',
                borderRadius: 'var(--radius-full)',
                backgroundColor: validationPassed ? 'var(--status-resolved-bg)' : 'var(--status-failed-bg)',
                color: validationPassed ? 'var(--status-resolved-text)' : 'var(--status-failed-text)',
                border: `1px solid ${validationPassed ? 'var(--status-resolved-border)' : 'var(--status-failed-border)'}`,
              }}
            >
              {validationPassed ? 'SUITE PASSED' : 'SUITE FAILED'}
            </span>
          )}
        </div>

        {validationRun ? (
          <div style={{ fontSize: '0.8125rem', display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)' }}>
            <div style={{ fontFamily: 'var(--font-mono)' }}>
              Tests:{' '}
              <span style={{ color: 'var(--text-main)', fontWeight: 700 }}>
                {validationRun.tests_passed ?? 0} passed
              </span>
              ,{' '}
              <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>
                {validationRun.tests_failed ?? 0} failed
              </span>{' '}
              (total: {validationRun.tests_total ?? 0})
            </div>
            {validationRun.summary && (
              <p style={{ color: 'var(--text-muted)' }}>{validationRun.summary}</p>
            )}
            {validationRun.output && (
              <pre
                style={{
                  marginTop: 'var(--space-xs)',
                  padding: 'var(--space-sm)',
                  backgroundColor: 'var(--bg-surface)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.75rem',
                  overflowX: 'auto',
                  maxHeight: '160px',
                  color: 'var(--text-main)',
                }}
              >
                {validationRun.output}
              </pre>
            )}
          </div>
        ) : (
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
            No validation run telemetry available for this proposal.
          </p>
        )}
      </div>

      {/* Action Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--space-md)', flexWrap: 'wrap', gap: 'var(--space-sm)' }}>
        <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
          {isApplied ? (
            <span style={{ color: 'var(--status-resolved-text)', fontWeight: 600 }}>Patch confirmed applied to repository</span>
          ) : isApproved ? (
            <span style={{ color: 'var(--brand-primary)', fontWeight: 600 }}>Review approved. Authorized for deployment.</span>
          ) : isRejected ? (
            <span style={{ color: 'var(--brand-primary)', fontWeight: 600 }}>Proposal rejected by human reviewer.</span>
          ) : !validationPassed ? (
            <span style={{ color: 'var(--text-muted)' }}>Automated tests must pass prior to approval</span>
          ) : (
            <span>Ready for human reviewer authorization</span>
          )}
        </div>

        {!isApproved && !isApplied && !isRejected && (
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setIsModalOpen(true)}
            disabled={!validationPassed}
            style={{ gap: '6px' }}
          >
            <span>Review & Approve Repair</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
        )}
      </div>

      <ApproveModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onConfirm={handleConfirmApproval}
        onReject={handleConfirmRejection}
        proposal={proposal}
        validationRun={validationRun}
        isApproving={isApproving}
      />
    </div>
  );
};
