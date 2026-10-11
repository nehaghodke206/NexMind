import React, { useState } from 'react';
import { RepairProposal, ValidationRun } from '../../api/types';

interface ApproveModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (comment: string) => Promise<void>;
  onReject?: (reason: string) => Promise<void>;
  proposal: RepairProposal;
  validationRun: ValidationRun | null;
  isApproving: boolean;
}

export const ApproveModal: React.FC<ApproveModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  onReject,
  proposal,
  validationRun,
  isApproving,
}) => {
  const [comment, setComment] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [isRejectMode, setIsRejectMode] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const validationPassed = validationRun?.status === 'passed' || validationRun?.result === 'passed';
  const canApprove =
    validationPassed &&
    proposal.status !== 'approved' &&
    proposal.status !== 'applied';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      if (isRejectMode) {
        if (!rejectReason.trim()) {
          setError('Please provide a reason for rejecting this repair proposal.');
          return;
        }
        if (onReject) {
          await onReject(rejectReason.trim());
        }
      } else {
        if (!canApprove) return;
        await onConfirm(comment);
      }
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Action failed. Please try again.');
    }
  };

  return (
    <div
      className="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="approve-modal-title"
    >
      <div className="modal-content">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-md)' }}>
          <h2 id="approve-modal-title" style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>
            {isRejectMode ? 'Reject Repair Proposal' : 'Review & Approve Repair Proposal'}
          </h2>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              fontSize: '1.25rem',
              cursor: 'pointer',
              padding: '4px',
            }}
            aria-label="Close dialog"
          >
            ✕
          </button>
        </div>

        {/* Mode switcher pills */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: 'var(--space-md)' }}>
          <button
            type="button"
            onClick={() => { setIsRejectMode(false); setError(null); }}
            className={`btn ${!isRejectMode ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '0.75rem', padding: '4px 12px' }}
          >
            Approve Patch
          </button>
          <button
            type="button"
            onClick={() => { setIsRejectMode(true); setError(null); }}
            className={`btn ${isRejectMode ? 'btn-danger' : 'btn-secondary'}`}
            style={{ fontSize: '0.75rem', padding: '4px 12px' }}
          >
            Reject Proposal
          </button>
        </div>

        {!isRejectMode && (
          <>
            {/* Cardinal rule alert */}
            <div className="alert-banner alert-info" role="status">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="16" x2="12" y2="12"/>
                <line x1="12" y1="8" x2="12.01" y2="8"/>
              </svg>
              <div>
                <strong>Approval is not application:</strong> Approving this proposal authorizes the
                patch for deployment. The incident will move to <em>Approved</em>, but will not be marked
                <em>Resolved</em> until the repair is applied and verified in the environment.
              </div>
            </div>

            {/* Validation check */}
            {!validationPassed && (
              <div className="alert-banner alert-warning" role="alert">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                  <line x1="12" y1="9" x2="12" y2="13"/>
                  <line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
                <div>
                  <strong>Validation Gate Blocked:</strong> Automated tests have not passed for this repair
                  proposal (current status: <em>{validationRun?.status || 'No validation run'}</em>). Proposals
                  with failing or missing validation cannot be approved.
                </div>
              </div>
            )}
          </>
        )}

        <div style={{ margin: 'var(--space-md) 0', fontSize: '0.875rem', display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)', backgroundColor: 'var(--bg-surface-elevated)', padding: 'var(--space-md)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
          <div><strong>Strategy:</strong> {proposal.strategy || 'compatibility_adapter'}</div>
          <div><strong>Risk Level:</strong> {proposal.risk_level?.toUpperCase() || 'MEDIUM'}</div>
          <div><strong>Proposed By:</strong> {proposal.proposed_by || 'repair-agent'}</div>
          <div><strong>Rationale:</strong> {proposal.rationale}</div>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
          {isRejectMode ? (
            <div>
              <label
                htmlFor="reject-reason"
                style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: 'var(--space-xs)' }}
              >
                Rejection Reason (Required)
              </label>
              <textarea
                id="reject-reason"
                rows={3}
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Explain why this proposal is rejected (e.g., approach introduces regression, breaking change requires manual callsite update)..."
                required
                style={{
                  width: '100%',
                  padding: 'var(--space-sm)',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--bg-surface)',
                  border: '1px solid var(--border-strong)',
                  color: 'var(--text-main)',
                  fontFamily: 'inherit',
                  fontSize: '0.875rem',
                }}
              />
            </div>
          ) : (
            <div>
              <label
                htmlFor="review-comment"
                style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: 'var(--space-xs)' }}
              >
                Reviewer Notes / Feedback (Optional)
              </label>
              <textarea
                id="review-comment"
                rows={3}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="e.g., Reviewed against API v2 spec; patch is safe for rollout."
                style={{
                  width: '100%',
                  padding: 'var(--space-sm)',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--bg-surface)',
                  border: '1px solid var(--border-strong)',
                  color: 'var(--text-main)',
                  fontFamily: 'inherit',
                  fontSize: '0.875rem',
                }}
              />
            </div>
          )}

          {error && (
            <p style={{ color: 'var(--brand-primary)', fontSize: '0.8125rem' }} role="alert">
              {error}
            </p>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-md)', marginTop: 'var(--space-sm)' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              disabled={isApproving}
            >
              Cancel
            </button>
            {isRejectMode ? (
              <button
                type="submit"
                className="btn btn-danger"
                disabled={isApproving}
              >
                {isApproving ? 'Submitting...' : 'Reject Proposal'}
              </button>
            ) : (
              <button
                type="submit"
                className="btn btn-primary"
                disabled={!canApprove || isApproving}
              >
                {isApproving ? 'Submitting...' : 'Confirm & Approve Repair'}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
};
