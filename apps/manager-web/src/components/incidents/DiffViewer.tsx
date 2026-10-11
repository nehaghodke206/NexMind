import React from 'react';

interface DiffViewerProps {
  diffText: string;
}

export const DiffViewer: React.FC<DiffViewerProps> = ({ diffText }) => {
  if (!diffText || !diffText.trim()) {
    return (
      <div
        className="diff-container"
        style={{ padding: 'var(--space-md)', color: 'var(--text-muted)' }}
      >
        No patch diff content provided.
      </div>
    );
  }

  const lines = diffText.split('\n');

  return (
    <div
      className="diff-container"
      tabIndex={0}
      aria-label="Unified Diff Preview"
      role="region"
    >
      {lines.map((line, index) => {
        let lineClass = '';
        if (line.startsWith('+') && !line.startsWith('+++')) {
          lineClass = 'diff-line-add';
        } else if (line.startsWith('-') && !line.startsWith('---')) {
          lineClass = 'diff-line-del';
        } else if (line.startsWith('@@')) {
          lineClass = 'diff-line-hunk';
        } else if (line.startsWith('---') || line.startsWith('+++')) {
          lineClass = 'diff-line-meta';
        }

        return (
          <div key={index} className={`diff-line ${lineClass}`}>
            <span
              style={{
                userSelect: 'none',
                width: '32px',
                textAlign: 'right',
                marginRight: 'var(--space-md)',
                color: 'var(--text-faint)',
                opacity: 0.5,
              }}
            >
              {index + 1}
            </span>
            <span style={{ flex: 1 }}>{line || ' '}</span>
          </div>
        );
      })}
    </div>
  );
};
