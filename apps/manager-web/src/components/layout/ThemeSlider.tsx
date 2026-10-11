import React, { useEffect, useState } from 'react';

export type ThemeMode = 'beige' | 'linen' | 'espresso';

interface ThemeOption {
  id: ThemeMode;
  label: string;
}

const THEMES: ThemeOption[] = [
  { id: 'beige', label: 'Beige' },
  { id: 'linen', label: 'Linen' },
  { id: 'espresso', label: 'Espresso' },
];

export const ThemeSlider: React.FC = () => {
  const [theme, setTheme] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem('dg_theme') as ThemeMode;
    if (saved === 'beige' || saved === 'linen' || saved === 'espresso') {
      return saved;
    }
    return 'beige';
  });

  useEffect(() => {
    if (theme === 'beige') {
      document.documentElement.removeAttribute('data-theme');
    } else {
      document.documentElement.setAttribute('data-theme', theme);
    }
    localStorage.setItem('dg_theme', theme);
  }, [theme]);

  const activeIndex = THEMES.findIndex((t) => t.id === theme);

  return (
    <div
      className="liquid-track liquid-theme-track"
      role="radiogroup"
      aria-label="Enterprise Display Mode"
    >
      {/* Glider */}
      <div
        className="liquid-melt-glider"
        aria-hidden="true"
        style={{
          width: `calc((100% - 6px) / ${THEMES.length})`,
          transform: `translateX(${activeIndex * 100}%)`,
        }}
      >
        <div className="liquid-glider-specular" />
      </div>

      {THEMES.map((t) => {
        const isActive = t.id === theme;
        return (
          <button
            key={t.id}
            type="button"
            role="radio"
            aria-checked={isActive}
            onClick={() => setTheme(t.id)}
            className={`liquid-theme-btn ${isActive ? 'active' : ''}`}
            title={`Switch to ${t.label} palette`}
          >
            <span>{t.label}</span>
          </button>
        );
      })}
    </div>
  );
};
