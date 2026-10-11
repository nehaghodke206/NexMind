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
          backgroundColor: 'var(--bg-surface-hover)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-muted)',
          fontSize: '1.25rem',
          marginBottom: 'var(--space-md)',
        }}
        aria-hidden="true"
      >
        ∅
      </div>
      <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: 'var(--space-xs)' }}>
        {title}
      </h3>
      <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', maxWidth: '420px', marginBottom: actionText ? 'var(--space-lg)' : 0 }}>
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
