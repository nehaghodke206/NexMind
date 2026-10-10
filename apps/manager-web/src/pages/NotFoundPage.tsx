import React from 'react';
import { Link } from 'react-router-dom';
import { EmptyState } from '../components/common/EmptyState';

export const NotFoundPage: React.FC = () => {
  return (
    <div style={{ padding: 'var(--space-2xl) 0' }}>
      <EmptyState
        title="404 - Page Not Found"
        description="The requested page could not be found. Please check the URL or return to the project dashboard."
      />
      <div style={{ textAlign: 'center', marginTop: 'var(--space-lg)' }}>
        <Link to="/" className="btn btn-primary">
          Return to Dashboard
        </Link>
      </div>
    </div>
  );
};
