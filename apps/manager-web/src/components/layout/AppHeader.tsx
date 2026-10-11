import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { api } from '../../api/client';
import { ThemeSlider } from './ThemeSlider';

export const AppHeader: React.FC = () => {
  const location = useLocation();
  const isMock = api.isMockMode();
  const baseUrl = api.getBaseUrl();
  const [healthStatus, setHealthStatus] = useState<string>('checking...');

  useEffect(() => {
    let isMounted = true;
    const check = async () => {
      try {
        const res = await api.checkHealth();
        if (isMounted) setHealthStatus(res.status);
      } catch {
        if (isMounted) setHealthStatus('offline');
      }
    };
    check();
    const interval = setInterval(check, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const getNavIndex = (pathname: string): number => {
    if (pathname.includes('/scans')) return 3;
    if (pathname.includes('/dependencies')) return 2;
    if (pathname.includes('/incidents')) return 1;
    if (pathname.includes('/activity')) return 4;
    return 0; // default to Projects
  };
  const activeIndex = getNavIndex(location.pathname);

  const isBackendHealthy = healthStatus.includes('healthy') || healthStatus.includes('ok');

  return (
    <header className="app-header">
      <div className="header-inner">
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-lg)' }}>
          <Link to="/" className="header-brand" aria-label="Dependency Guardian Home">
            <span className="logo-badge">DG</span>
            <span className="brand-title">Dependency Guardian</span>
          </Link>

          {/* Enterprise Navigation Bar */}
          <nav className="liquid-nav-bar" aria-label="Main Navigation">
            <div
              className="liquid-melt-glider"
              aria-hidden="true"
              style={{
                width: 'calc((100% - 6px) / 5)',
                transform: `translateX(${activeIndex * 100}%)`,
              }}
            >
              <div className="liquid-glider-specular" />
            </div>

            <Link
              to="/projects"
              className={`liquid-nav-link ${activeIndex === 0 ? 'active' : ''}`}
            >
              <svg className="liquid-nav-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
              </svg>
              <span>Projects</span>
            </Link>

            <Link
              to="/incidents"
              className={`liquid-nav-link ${activeIndex === 1 ? 'active' : ''}`}
            >
              <svg className="liquid-nav-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
              <span>Incidents</span>
            </Link>

            <Link
              to="/dependencies"
              className={`liquid-nav-link ${activeIndex === 2 ? 'active' : ''}`}
            >
              <svg className="liquid-nav-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
                <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
                <line x1="6" y1="6" x2="6.01" y2="6"/>
                <line x1="6" y1="18" x2="6.01" y2="18"/>
              </svg>
              <span>Contracts</span>
            </Link>

            <Link
              to="/scans"
              className={`liquid-nav-link ${activeIndex === 3 ? 'active' : ''}`}
            >
              <svg className="liquid-nav-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="10"/>
                <line x1="2" y1="12" x2="22" y2="12"/>
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
              </svg>
              <span>Probes</span>
            </Link>

            <Link
              to="/activity"
              className={`liquid-nav-link ${activeIndex === 4 ? 'active' : ''}`}
            >
              <svg className="liquid-nav-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
              </svg>
              <span>Activity</span>
            </Link>
          </nav>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
          <ThemeSlider />

          {/* Backend Connection & Health Status Indicator */}
          <div
            title={`Backend: ${baseUrl} (${isMock ? 'Mock Simulation Mode' : 'Live Mode'})`}
            style={{
              fontSize: '0.75rem',
              letterSpacing: '0.04em',
              padding: '4px 10px',
              borderRadius: 'var(--radius-full)',
              border: '1px solid var(--border-strong)',
              backgroundColor: 'var(--bg-surface-elevated)',
              color: 'var(--text-main)',
              fontWeight: 600,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                backgroundColor: isMock
                  ? 'var(--brand-accent)'
                  : isBackendHealthy
                  ? '#16a34a'
                  : 'var(--brand-primary)',
                boxShadow: isMock
                  ? '0 0 6px var(--brand-primary-glow)'
                  : isBackendHealthy
                  ? '0 0 6px rgba(22, 163, 74, 0.5)'
                  : '0 0 6px rgba(153, 27, 27, 0.5)',
              }}
              aria-hidden="true"
            />
            <span>
              {isMock
                ? 'MOCK MODE'
                : isBackendHealthy
                ? 'BACKEND CONNECTED'
                : `OFFLINE (${healthStatus})`}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
