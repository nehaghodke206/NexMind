import React from 'react';
import { Severity } from '../../api/types';

interface BadgeProps {
  severity: Severity;
  className?: string;
}

export const SeverityBadge: React.FC<BadgeProps> = ({ severity, className = '' }) => {
  const labels: Record<Severity, { text: string }> = {
    critical: { text: 'Critical' },
    high: { text: 'High' },
    medium: { text: 'Medium' },
    low: { text: 'Low' },
  };

  const info = labels[severity] || { text: severity };

  return (
    <span
      className={`badge badge-${severity} ${className}`}
      aria-label={`Severity: ${info.text}`}
      role="status"
    >
      <span
        style={{
          display: 'inline-block',
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          backgroundColor: 'currentColor',
        }}
        aria-hidden="true"
      />
      <span>{info.text}</span>
    </span>
  );
};
