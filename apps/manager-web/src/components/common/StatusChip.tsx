import React from 'react';
import { IncidentStatus, RepairStatus } from '../../api/types';

interface StatusChipProps {
  status: IncidentStatus | RepairStatus;
  type?: 'incident' | 'repair';
  className?: string;
}

export const StatusChip: React.FC<StatusChipProps> = ({ status, className = '' }) => {
  const formatLabel = (raw: string): string => {
    switch (raw) {
      case 'ready_for_review':
        return 'Ready for Review';
      case 'awaiting_review':
        return 'Awaiting Review';
      case 'repair_proposed':
        return 'Repair Proposed';
      case 'validation_failed':
        return 'Validation Failed';
      case 'validation_passed':
        return 'Validation Passed';
      case 'in_progress':
        return 'In Progress';
      default:
        return raw.charAt(0).toUpperCase() + raw.slice(1).replace(/_/g, ' ');
    }
  };

  const getStatusClass = (raw: string): string => {
    return `status-${raw}`;
  };

  return (
    <span className={`status-chip ${getStatusClass(status)} ${className}`}>
      {formatLabel(status)}
    </span>
  );
};
