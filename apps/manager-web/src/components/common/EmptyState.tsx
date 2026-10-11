import React from 'react';

interface EmptyStateProps {
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  actionText,
  onAction,
}) => {
  return (
    <div
      className="card"
      style={{
        textAlign: 'center',
        padding: 'var(--space-2xl) var(--space-xl)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          width: '48px',
          height: '48px',
          borderRadius: '50%',
          backgroundColor: 'var(--bg-surface-elevated)',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-muted)',
          marginBottom: 'var(--space-md)',
        }}
        aria-hidden="true"
      >
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="8" y1="12" x2="16" y2="12"/>
        </svg>
      </div>
      <h3 style={{ fontSize: '1.125rem', fontWeight: 700, marginBottom: 'var(--space-xs)', color: 'var(--text-main)' }}>
        {title}
      </h3>
      <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', maxWidth: '440px', marginBottom: actionText ? 'var(--space-lg)' : 0, lineHeight: 1.5 }}>
        {description}
      </p>
      {actionText && onAction && (
        <button type="button" className="btn btn-secondary" onClick={onAction}>
          {actionText}
        </button>
      )}
    </div>
  );
};
