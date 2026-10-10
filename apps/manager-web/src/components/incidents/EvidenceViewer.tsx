import React from 'react';
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

  const removedFields = evidence?.removed_fields ?? [];
  const addedFields = evidence?.added_fields ?? [];
  const typeChanges = evidence?.type_changes ?? [];
  const hasPayloads = Boolean(evidence?.baseline || evidence?.observed);

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-sm)' }}>
        <h3 style={{ fontSize: '1.125rem', fontWeight: 600 }}>Detected Evidence & Impact</h3>
        {confidence !== undefined && confidence !== null && (
          <span
            style={{
              fontSize: '0.8125rem',
              color: isUncertain ? '#fef08a' : 'var(--text-muted)',
              backgroundColor: isUncertain ? 'rgba(234, 179, 8, 0.15)' : 'var(--bg-surface-elevated)',
              border: `1px solid ${isUncertain ? 'var(--sev-medium-border)' : 'var(--border-subtle)'}`,
              padding: '2px 8px',
              borderRadius: 'var(--radius-sm)',
            }}
          >
            Detection Confidence: {(confidence * 100).toFixed(0)}%
          </span>
        )}
      </div>

      {(isUncertain || isBlocked) && (
        <div className="alert-banner alert-warning" role="alert">
          <span aria-hidden="true">⚠</span>
          <div>
            <strong>Human Review Required: </strong>
            {isBlocked
              ? 'This incident is currently BLOCKED. Upstream service failure or manual intervention is required.'
              : 'Confidence is below 90%. Automated analysis requires careful human verification of API contracts.'}
          </div>
        </div>
      )}

      {evidence?.diff_summary ? (
        <p style={{ color: 'var(--text-main)', fontSize: '0.875rem' }}>
          {evidence.diff_summary}
        </p>
      ) : null}

      {/* Field changes tags */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 'var(--space-md)' }}>
        {removedFields.length > 0 ? (
          <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.08)', border: '1px solid var(--sev-critical-border)', borderRadius: 'var(--radius-md)', padding: 'var(--space-sm) var(--space-md)' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#fca5a5', textTransform: 'uppercase' }}>
              Removed Fields ({removedFields.length})
            </span>
            <ul style={{ listStyle: 'none', marginTop: 'var(--space-xs)' }}>
              {removedFields.map((f, i) => (
                <li key={i} style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8125rem', color: '#fca5a5' }}>
                  - {f}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {addedFields.length > 0 ? (
          <div style={{ backgroundColor: 'rgba(34, 197, 94, 0.08)', border: '1px solid #22c55e', borderRadius: 'var(--radius-md)', padding: 'var(--space-sm) var(--space-md)' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#86efac', textTransform: 'uppercase' }}>
              Added / Observed Fields ({addedFields.length})
            </span>
            <ul style={{ listStyle: 'none', marginTop: 'var(--space-xs)' }}>
              {addedFields.map((f, i) => (
                <li key={i} style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8125rem', color: '#86efac' }}>
                  + {f}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {typeChanges.length > 0 ? (
          <div style={{ backgroundColor: 'rgba(234, 179, 8, 0.08)', border: '1px solid #eab308', borderRadius: 'var(--radius-md)', padding: 'var(--space-sm) var(--space-md)' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#fde047', textTransform: 'uppercase' }}>
              Type / Semantic Changes
            </span>
            <ul style={{ listStyle: 'none', marginTop: 'var(--space-xs)' }}>
              {typeChanges.map((tc, i) => {
                const text = typeof tc === 'string' ? tc : `${tc.field}: ${tc.from} → ${tc.to}`;
                return (
                  <li key={i} style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8125rem', color: '#fde047' }}>
                    ~ {text}
                  </li>
                );
              })}
            </ul>
          </div>
        ) : null}
      </div>

      {/* Side-by-side Baseline vs Observed payloads */}
      {hasPayloads ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 'var(--space-md)' }}>
          <div>
            <h4 style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 'var(--space-xs)' }}>
              Baseline Contract Response
            </h4>
            <pre
              tabIndex={0}
              aria-label="Baseline Contract Payload"
              style={{
                backgroundColor: '#030712',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                padding: 'var(--space-md)',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.8125rem',
                color: '#cbd5e1',
                overflowX: 'auto',
                maxHeight: '260px',
              }}
            >
              {JSON.stringify(evidence?.baseline ?? {}, null, 2)}
            </pre>
          </div>

          <div>
            <h4 style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 'var(--space-xs)' }}>
              Observed Live Response
            </h4>
            <pre
              tabIndex={0}
              aria-label="Observed Live Payload"
              style={{
                backgroundColor: '#030712',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                padding: 'var(--space-md)',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.8125rem',
                color: '#fed7aa',
                overflowX: 'auto',
                maxHeight: '260px',
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
