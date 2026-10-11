import React from 'react';

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Failed to load data',
  message,
  onRetry,
}) => {
  return (
    <div
      role="alert"
      className="card"
      style={{
        borderLeft: '4px solid #ef4444',
        padding: 'var(--space-xl)',
        backgroundColor: 'rgba(239, 68, 68, 0.05)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-md)' }}>
        <div
          style={{
            color: '#ef4444',
            fontSize: '1.25rem',
            lineHeight: 1,
            marginTop: '2px',
          }}
          aria-hidden="true"
        >
          ⚠
        </div>
        <div style={{ flex: 1 }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#fca5a5', marginBottom: 'var(--space-xs)' }}>
            {title}
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: onRetry ? 'var(--space-md)' : 0 }}>
            {message}
          </p>
          {onRetry && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onRetry}
              style={{ fontSize: '0.8125rem' }}
            >
              ↻ Try Again
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
