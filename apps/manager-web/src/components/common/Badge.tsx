import React from 'react';
import { Severity } from '../../api/types';

interface BadgeProps {
  severity: Severity;
  className?: string;
}

export const SeverityBadge: React.FC<BadgeProps> = ({ severity, className = '' }) => {
  const labels: Record<Severity, { text: string; indicator: string }> = {
    critical: { text: 'Critical', indicator: '●' },
    high: { text: 'High', indicator: '▲' },
    medium: { text: 'Medium', indicator: '■' },
    low: { text: 'Low', indicator: '○' },
  };

  const info = labels[severity] || { text: severity, indicator: '•' };

  return (
    <span
      className={`badge badge-${severity} ${className}`}
      aria-label={`Severity: ${info.text}`}
      role="status"
    >
      <span aria-hidden="true" style={{ fontSize: '0.65rem' }}>{info.indicator}</span>
      <span>{info.text}</span>
    </span>
  );
};
