import React, { useState, useEffect, useRef } from 'react';
import { IncidentEvidence } from '../../api/types';

interface EvidenceViewerProps {
  evidence?: IncidentEvidence | null;
  confidence?: number | null;
  status: string;
}

export const EvidenceViewer: React.FC<EvidenceViewerProps> = ({
  evidence,
  confidence,
  status,
}) => {
  const isUncertain = confidence !== undefined && confidence !== null && confidence < 0.9;
  const isBlocked = status === 'blocked';

  const [compareMode, setCompareMode] = useState<'side-by-side' | 'slider'>('slider');
  const [sliderPosition, setSliderPosition] = useState(50);
  const [isAutoScanning, setIsAutoScanning] = useState(false);
  const scanDirectionRef = useRef<1 | -1>(1);

  // Auto-scan slider animation
  useEffect(() => {
    if (!isAutoScanning) return;

    const interval = setInterval(() => {
      setSliderPosition((prev) => {
        if (prev >= 85) scanDirectionRef.current = -1;
        if (prev <= 15) scanDirectionRef.current = 1;
        return prev + scanDirectionRef.current * 1.5;
      });
    }, 30);

    return () => clearInterval(interval);
  }, [isAutoScanning]);

  const removedFields = evidence?.removed_fields ?? [];
  const addedFields = evidence?.added_fields ?? [];
  const typeChanges = evidence?.type_changes ?? [];
  const hasPayloads = Boolean(evidence?.baseline || evidence?.observed);

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
      {/* Header with Comparison Controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-md)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
          <h3 style={{ fontSize: '1.125rem', fontWeight: 700, letterSpacing: '-0.01em', margin: 0 }}>
            Detected Evidence & Impact
          </h3>
          {confidence !== undefined && confidence !== null && (
            <span
              style={{
                fontSize: '0.75rem',
                fontWeight: 700,
                fontFamily: 'var(--font-mono)',
                color: isUncertain ? 'var(--sev-high-text)' : 'var(--brand-primary)',
                backgroundColor: isUncertain ? 'var(--sev-high-bg)' : 'var(--sev-critical-bg)',
                border: `1px solid ${isUncertain ? 'var(--sev-high-border)' : 'var(--sev-critical-border)'}`,
                padding: '2px 8px',
                borderRadius: 'var(--radius-full)',
              }}
            >
              CONFIDENCE: {(confidence * 100).toFixed(0)}%
            </span>
          )}
        </div>

        {/* View Mode Toggle */}
        {hasPayloads && (
          <div
            className="liquid-track"
            role="tablist"
            aria-label="Evidence Comparison Mode"
          >
            <div
              className="liquid-melt-glider"
              aria-hidden="true"
              style={{
                width: 'calc((100% - 6px) / 2)',
                transform: `translateX(${compareMode === 'slider' ? '100%' : '0%'})`,
              }}
            >
              <div className="liquid-glider-specular" />
            </div>
            <button
              type="button"
              role="tab"
              aria-selected={compareMode === 'side-by-side'}
              onClick={() => setCompareMode('side-by-side')}
              className={`liquid-tab-btn ${compareMode === 'side-by-side' ? 'active' : ''}`}
            >
              Side-by-Side
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={compareMode === 'slider'}
              onClick={() => setCompareMode('slider')}
              className={`liquid-tab-btn ${compareMode === 'slider' ? 'active' : ''}`}
            >
              Split Slider
            </button>
          </div>
        )}
      </div>

      {(isUncertain || isBlocked) && (
        <div className="alert-banner alert-warning" role="alert">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <div>
            <strong>Human Review Required: </strong>
            {isBlocked
              ? 'This incident is currently BLOCKED. Upstream service failure or manual intervention is required.'
              : 'Confidence score is below 90%. Automated analysis flags this change for required human verification.'}
          </div>
        </div>
      )}

      {evidence?.diff_summary ? (
        <p style={{ color: 'var(--text-main)', fontSize: '0.9375rem', lineHeight: 1.6, margin: 0 }}>
          {evidence.diff_summary}
        </p>
      ) : null}

      {/* Field changes tags */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 'var(--space-md)' }}>
        {removedFields.length > 0 ? (
          <div
            style={{
              backgroundColor: 'var(--sev-critical-bg)',
              border: '1px solid var(--sev-critical-border)',
              borderRadius: 'var(--radius-md)',
              padding: 'var(--space-sm) var(--space-md)',
            }}
          >
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--sev-critical-text)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Removed Contract Fields ({removedFields.length})
            </span>
            <ul style={{ listStyle: 'none', marginTop: 'var(--space-xs)' }}>
              {removedFields.map((f, i) => (
                <li key={i} style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8125rem', color: 'var(--sev-critical-text)', textDecoration: 'line-through' }}>
                  - {f}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {addedFields.length > 0 ? (
          <div
            style={{
              backgroundColor: 'var(--status-resolved-bg)',
              border: '1px solid var(--status-resolved-border)',
              borderRadius: 'var(--radius-md)',
              padding: 'var(--space-sm) var(--space-md)',
            }}
          >
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--status-resolved-text)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Observed / Added Fields ({addedFields.length})
            </span>
            <ul style={{ listStyle: 'none', marginTop: 'var(--space-xs)' }}>
              {addedFields.map((f, i) => (
                <li key={i} style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8125rem', color: 'var(--status-resolved-text)', fontWeight: 600 }}>
                  + {f}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {typeChanges.length > 0 ? (
          <div
            style={{
              backgroundColor: 'var(--sev-high-bg)',
              border: '1px solid var(--sev-high-border)',
              borderRadius: 'var(--radius-md)',
              padding: 'var(--space-sm) var(--space-md)',
            }}
          >
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--sev-high-text)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Type / Semantic Shifts ({typeChanges.length})
            </span>
            <ul style={{ listStyle: 'none', marginTop: 'var(--space-xs)' }}>
              {typeChanges.map((tc, i) => {
                const text = typeof tc === 'string' ? tc : `${tc.field}: ${tc.from} → ${tc.to}`;
                return (
                  <li key={i} style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8125rem', color: 'var(--sev-high-text)' }}>
                    ~ {text}
                  </li>
                );
              })}
            </ul>
          </div>
        ) : null}
      </div>

      {/* Comparison View: Split Slider vs Side-by-Side */}
      {hasPayloads && compareMode === 'slider' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
          {/* Slider Controls Bar */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              backgroundColor: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: '8px 14px',
              flexWrap: 'wrap',
              gap: 'var(--space-sm)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, minWidth: '220px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                BASELINE ({Math.round(sliderPosition)}%)
              </span>
              <input
                type="range"
                min="5"
                max="95"
                value={sliderPosition}
                onChange={(e) => {
                  setIsAutoScanning(false);
                  setSliderPosition(Number(e.target.value));
                }}
                aria-label="Before/After Diff Comparison Slider"
                style={{
                  flex: 1,
                  cursor: 'ew-resize',
                  height: '6px',
                }}
              />
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-main)', fontFamily: 'var(--font-mono)' }}>
                OBSERVED ({100 - Math.round(sliderPosition)}%)
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  setIsAutoScanning(false);
                  setSliderPosition(50);
                }}
                style={{ fontSize: '0.75rem', padding: '3px 8px' }}
              >
                50/50 Split
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setIsAutoScanning(!isAutoScanning)}
                style={{
                  fontSize: '0.75rem',
                  padding: '3px 10px',
                  backgroundColor: isAutoScanning ? 'var(--sev-critical-bg)' : undefined,
                  borderColor: isAutoScanning ? 'var(--brand-primary)' : undefined,
                  color: isAutoScanning ? 'var(--brand-primary)' : undefined,
                }}
              >
                {isAutoScanning ? 'Pause Scan' : 'Auto-Scan Animation'}
              </button>
            </div>
          </div>

          {/* Interactive Split Slider Surface */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: `${sliderPosition}% ${100 - sliderPosition}%`,
              gap: '2px',
              backgroundColor: 'var(--border-subtle)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              overflow: 'hidden',
              transition: isAutoScanning ? 'none' : 'grid-template-columns 0.15s ease',
            }}
          >
            {/* Left Payload (Baseline) */}
            <div style={{ backgroundColor: 'var(--diff-bg)', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
              <div
                style={{
                  padding: '6px 12px',
                  backgroundColor: 'var(--bg-surface-elevated)',
                  borderBottom: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <span style={{ fontSize: '0.6875rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                  BASELINE_CONTRACT
                </span>
                <span style={{ fontSize: '0.6875rem', color: 'var(--text-faint)' }}>STABLE</span>
              </div>
              <pre
                style={{
                  padding: 'var(--space-md)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.8125rem',
                  color: 'var(--text-muted)',
                  overflowX: 'auto',
                  maxHeight: '280px',
                  margin: 0,
                }}
              >
                {JSON.stringify(evidence?.baseline ?? {}, null, 2)}
              </pre>
            </div>

            {/* Right Payload (Observed) */}
            <div style={{ backgroundColor: 'var(--bg-surface)', overflow: 'hidden', display: 'flex', flexDirection: 'column', borderLeft: '2px solid var(--brand-primary)' }}>
              <div
                style={{
                  padding: '6px 12px',
                  backgroundColor: 'var(--bg-surface-elevated)',
                  borderBottom: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <span style={{ fontSize: '0.6875rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--brand-primary)' }}>
                  OBSERVED_DRIFT
                </span>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--brand-primary)' }} />
              </div>
              <pre
                style={{
                  padding: 'var(--space-md)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.8125rem',
                  color: 'var(--text-main)',
                  overflowX: 'auto',
                  maxHeight: '280px',
                  margin: 0,
                }}
              >
                {JSON.stringify(evidence?.observed ?? {}, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      ) : hasPayloads ? (
        /* Side-by-Side Mode */
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 'var(--space-md)' }}>
          <div
            style={{
              backgroundColor: 'var(--diff-bg)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '6px 12px',
                backgroundColor: 'var(--bg-surface-elevated)',
                borderBottom: '1px solid var(--border-subtle)',
              }}
            >
              <span style={{ fontSize: '0.6875rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', letterSpacing: '0.04em' }}>
                BASELINE_CONTRACT.json
              </span>
              <span style={{ fontSize: '0.6875rem', color: 'var(--text-faint)' }}>STABLE</span>
            </div>
            <pre
              tabIndex={0}
              aria-label="Baseline Contract Payload"
              style={{
                padding: 'var(--space-md)',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.8125rem',
                color: 'var(--text-muted)',
                overflowX: 'auto',
                maxHeight: '260px',
                margin: 0,
              }}
            >
              {JSON.stringify(evidence?.baseline ?? {}, null, 2)}
            </pre>
          </div>

          <div
            style={{
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-strong)',
              borderRadius: 'var(--radius-md)',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '6px 12px',
                backgroundColor: 'var(--bg-surface-elevated)',
                borderBottom: '1px solid var(--border-subtle)',
              }}
            >
              <span style={{ fontSize: '0.6875rem', fontFamily: 'var(--font-mono)', color: 'var(--brand-primary)', letterSpacing: '0.04em' }}>
                OBSERVED_RESPONSE.json
              </span>
              <span style={{ fontSize: '0.6875rem', color: 'var(--brand-primary)', fontWeight: 700 }}>DRIFT</span>
            </div>
            <pre
              tabIndex={0}
              aria-label="Observed Response Payload"
              style={{
                padding: 'var(--space-md)',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.8125rem',
                color: 'var(--text-main)',
                overflowX: 'auto',
                maxHeight: '260px',
                margin: 0,
              }}
            >
              {JSON.stringify(evidence?.observed ?? {}, null, 2)}
            </pre>
          </div>
        </div>
      ) : null}
    </div>
  );
};
