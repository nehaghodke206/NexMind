import React from 'react';
import { Outlet } from 'react-router-dom';
import { AppHeader } from './AppHeader';

export const AppLayout: React.FC = () => {
  return (
    <div className="app-shell">
      {/* Codexure Liquid Melt SVG Filter Definition (Gooey Fluid Physics) */}
      <svg
        className="liquid-svg-defs"
        aria-hidden="true"
        style={{ position: 'absolute', width: 0, height: 0, pointerEvents: 'none' }}
      >
        <defs>
          <filter id="liquid-melt">
            <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="blur" />
            <feColorMatrix
              in="blur"
              mode="matrix"
              values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 20 -10"
              result="goo"
            />
            <feComposite in="SourceGraphic" in2="goo" operator="atop" />
          </filter>
        </defs>
      </svg>

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
