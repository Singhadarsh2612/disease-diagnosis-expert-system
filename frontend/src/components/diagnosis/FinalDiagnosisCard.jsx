import ConfidenceBar from './ConfidenceBar.jsx';
import DiagnosisFeedback from './DiagnosisFeedback.jsx';

const fmt = (s) => s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

export default function FinalDiagnosisCard({ diagnosis, sessionId, emergencyFlags = [], onReset, deniedSymptoms = [] }) {
  if (!diagnosis) return null;

  const isEmergency =
    emergencyFlags.length > 0 ||
    diagnosis.recommended_action === 'emergency' ||
    diagnosis.severity === 'severe';

  return (
    <div className="final-diagnosis-card">
      {/* Emergency banner if applicable */}
      {isEmergency && (
        <div className="emergency-banner" style={{ margin: 0, borderRadius: 0, borderLeft: 'none', borderRight: 'none', borderTop: 'none' }}>
          <h4>🚨 URGENT MEDICAL ATTENTION RECOMMENDED</h4>
          {emergencyFlags.length > 0 ? (
            emergencyFlags.map((f, i) => <p key={i}>{f.message}</p>)
          ) : (
            <p>This condition has high severity or requires immediate emergency care. Please contact emergency services (911/112) or go to the nearest emergency department.</p>
          )}
        </div>
      )}

      <div className="final-diagnosis-header">
        <h2>🩺 {diagnosis.name}</h2>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap', marginTop: '0.25rem' }}>
          <span>{diagnosis.category}</span>
          <span>•</span>
          <span style={{ textTransform: 'capitalize' }}>{diagnosis.severity} Severity</span>
          {diagnosis.recommended_action && (
            <span
              className={`badge badge-action-${diagnosis.recommended_action.toLowerCase().replace(/\s+/g, '-')}`}
              style={{ background: 'rgba(255, 255, 255, 0.25)', color: 'white', border: '1px solid rgba(255, 255, 255, 0.4)' }}
            >
              Action: {diagnosis.recommended_action}
            </span>
          )}
        </div>
        <div style={{ marginTop: '0.75rem' }}>
          <ConfidenceBar confidence={diagnosis.confidence} label={diagnosis.label} />
        </div>
      </div>

      <div className="final-diagnosis-body">
        {diagnosis.recommended_action && (
          <div style={{ marginBottom: '1rem', padding: '0.75rem 1rem', background: 'var(--neutral-100)', borderRadius: 'var(--radius-sm)' }}>
            <p className="section-title" style={{ marginBottom: '0.2rem' }}>Recommended Action</p>
            <p style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--neutral-800)' }}>
              {diagnosis.recommended_action === 'self-care' && 'Self-care at home. Monitor for worsening symptoms.'}
              {diagnosis.recommended_action === 'consult-doctor' && 'Consult a licensed healthcare professional for examination and treatment.'}
              {diagnosis.recommended_action === 'emergency' && 'Seek immediate emergency medical attention.'}
              {!['self-care', 'consult-doctor', 'emergency'].includes(diagnosis.recommended_action) && diagnosis.recommended_action}
            </p>
          </div>
        )}

        {diagnosis.description && (
          <div style={{ marginBottom: '1rem' }}>
            <p className="section-title">About this condition</p>
            <p style={{ fontSize: '0.9rem' }}>{diagnosis.description}</p>
          </div>
        )}

        {diagnosis.next_steps && (
          <div style={{ marginBottom: '1rem' }}>
            <p className="section-title">Recommended Next Steps</p>
            <p style={{ fontSize: '0.9rem', color: 'var(--primary-dark)', fontWeight: 500 }}>{diagnosis.next_steps}</p>
          </div>
        )}

        {/* Matched symptoms */}
        {diagnosis.matched_symptoms?.length > 0 && (
          <div style={{ marginBottom: '1rem' }}>
            <p className="section-title">Your matching symptoms ({diagnosis.matched_symptoms.length})</p>
            <div>
              {diagnosis.matched_symptoms.map((s) => (
                <span key={s} className="symptom-chip-matched">✓ {fmt(s)}</span>
              ))}
            </div>
          </div>
        )}

        {/* Missing / unselected symptoms */}
        {diagnosis.missing_symptoms?.length > 0 && (
          <div style={{ marginBottom: '1rem' }}>
            <p className="section-title">Common symptoms of this condition not reported ({diagnosis.missing_symptoms.length})</p>
            <div>
              {diagnosis.missing_symptoms.map((s) => (
                <span key={s} className="symptom-chip-missing">✕ {fmt(s)}</span>
              ))}
            </div>
          </div>
        )}

        {diagnosis.homeopathic_remedies?.length > 0 && (
          <div style={{ marginBottom: '1rem' }}>
            <p className="section-title">Supportive / Homeopathic Remedies</p>
            <ul style={{ paddingLeft: '1.25rem', fontSize: '0.88rem', color: 'var(--neutral-700)' }}>
              {diagnosis.homeopathic_remedies.map((r, i) => <li key={i}>{r}</li>)}
            </ul>
            {diagnosis.remedies_disclaimer && (
              <p style={{ fontSize: '0.78rem', color: 'var(--neutral-400)', marginTop: '0.4rem' }}>{diagnosis.remedies_disclaimer}</p>
            )}
          </div>
        )}

        {/* Disclaimer */}
        <div style={{ margin: '1.25rem 0', padding: '0.75rem', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 'var(--radius-sm)', fontSize: '0.8rem', color: '#92400e' }}>
          ⚠️ <strong>Medical Disclaimer:</strong> This expert system diagnosis is for academic demonstration only and is not a substitute for clinical advice. Always consult a certified physician.
        </div>

        <DiagnosisFeedback sessionId={sessionId} finalDisease={diagnosis.name} deniedSymptoms={deniedSymptoms} />

        <hr className="divider" />
        <button className="btn btn-secondary btn-sm" onClick={onReset}>
          ↺ Start Over
        </button>
      </div>
    </div>
  );
}

