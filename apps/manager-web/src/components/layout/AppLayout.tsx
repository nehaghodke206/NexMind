import React from 'react';
import { Outlet } from 'react-router-dom';
import { AppHeader } from './AppHeader';

export const AppLayout: React.FC = () => {
  return (
    <div className="app-shell">
      <AppHeader />
      <main className="app-main">
        <Outlet />
      </main>
      <footer
        style={{
          borderTop: '1px solid var(--border-subtle)',
          padding: 'var(--space-md) var(--space-xl)',
          textAlign: 'center',
          color: 'var(--text-faint)',
          fontSize: '0.75rem',
        }}
      >
        Dependency Guardian &bull; Manager Web Dashboard &bull; Human-in-the-loop Review System
      </footer>
    </div>
  );
};
