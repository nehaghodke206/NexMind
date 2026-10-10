import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { api } from '../../api/client';

export const AppHeader: React.FC = () => {
  const location = useLocation();
  const isMock = api.isMockMode();

  return (
    <header className="app-header">
      <div className="header-inner">
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xl)' }}>
          <Link to="/" className="header-brand">
            <span className="logo-badge">DG</span>
            <span>Dependency Guardian</span>
          </Link>

          <nav className="header-nav" aria-label="Main Navigation">
            <Link
              to="/projects"
              className={`nav-link ${location.pathname.startsWith('/projects') || location.pathname === '/' ? 'active' : ''}`}
            >
              Projects
            </Link>
            <Link
              to="/incidents"
              className={`nav-link ${location.pathname.startsWith('/incidents') ? 'active' : ''}`}
            >
              Incidents
            </Link>
            <Link
              to="/activity"
              className={`nav-link ${location.pathname.startsWith('/activity') ? 'active' : ''}`}
            >
              Activity Feed
            </Link>
          </nav>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
          <span
            style={{
              fontSize: '0.75rem',
              padding: '2px 8px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-strong)',
              backgroundColor: isMock ? 'rgba(99, 102, 241, 0.15)' : 'rgba(34, 197, 94, 0.15)',
              color: isMock ? '#a5b4fc' : '#86efac',
              fontWeight: 600,
            }}
          >
            {isMock ? '⚡ MOCK MODE' : '🔗 LIVE BACKEND'}
          </span>
        </div>
      </div>
    </header>
  );
};
