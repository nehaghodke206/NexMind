import React, { useState } from 'react';
import { RepairProposal, ValidationRun } from '../../api/types';

interface ApproveModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (comment: string) => Promise<void>;
  proposal: RepairProposal;
  validationRun: ValidationRun | null;
  isApproving: boolean;
}

export const ApproveModal: React.FC<ApproveModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  proposal,
  validationRun,
  isApproving,
}) => {
  const [comment, setComment] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const validationPassed = validationRun?.status === 'passed' || validationRun?.result === 'passed';
  const canApprove =
    validationPassed &&
    proposal.status !== 'approved' &&
    proposal.status !== 'applied';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canApprove) return;
    setError(null);
    try {
      await onConfirm(comment);
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Approval failed. Please try again.');
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
        <h2 id="approve-modal-title" style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: 'var(--space-md)' }}>
          Review & Approve Repair Proposal
        </h2>

        {/* Cardinal rule alert */}
        <div className="alert-banner alert-info" role="status">
          <span aria-hidden="true">ℹ</span>
          <div>
            <strong>Approval is not application:</strong> Approving this proposal authorizes the
            patch for deployment. The incident will move to <em>Approved</em>, but will not be marked
            <em>Resolved</em> until the repair is applied and verified in the environment.
          </div>
        </div>

        {/* Validation check */}
        {!validationPassed && (
          <div className="alert-banner alert-warning" role="alert">
            <span aria-hidden="true">⚠</span>
            <div>
              <strong>Validation Gate Blocked:</strong> Automated tests have not passed for this repair
              proposal (current status: <em>{validationRun?.status || 'No validation run'}</em>). Proposals
              with failing or missing validation cannot be approved.
            </div>
          </div>
        )}

        <div style={{ margin: 'var(--space-md) 0', fontSize: '0.875rem', display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)' }}>
          <div><strong>Strategy:</strong> {proposal.strategy || 'Unspecified'}</div>
          <div><strong>Risk Level:</strong> {proposal.risk_level?.toUpperCase() || 'MEDIUM'}</div>
          <div><strong>Proposed By:</strong> {proposal.proposed_by || 'agent'}</div>
          <div><strong>Rationale:</strong> {proposal.rationale}</div>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
          <div>
            <label
              htmlFor="review-comment"
              style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 'var(--space-xs)' }}
            >
              Reviewer Notes / Feedback (optional)
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
                backgroundColor: 'var(--bg-app)',
                border: '1px solid var(--border-strong)',
                color: 'var(--text-main)',
                fontFamily: 'inherit',
                fontSize: '0.875rem',
              }}
            />
          </div>

          {error && (
            <p style={{ color: '#ef4444', fontSize: '0.8125rem' }} role="alert">
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
            <button
              type="submit"
              className="btn btn-primary"
              disabled={!canApprove || isApproving}
              style={{ backgroundColor: canApprove ? '#059669' : undefined }}
            >
              {isApproving ? 'Submitting...' : 'Confirm & Approve Repair'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
