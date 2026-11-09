import ConfidenceBar from './ConfidenceBar.jsx';

const fmt = (s) => s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

function severityBadge(s) {
  const cls = { mild: 'badge-mild', moderate: 'badge-moderate', severe: 'badge-severe' }[s] || 'badge-mild';
  return <span className={`badge ${cls}`}>{s}</span>;
}

export default function DiseaseCard({ disease, isTop }) {
  return (
    <div className={`disease-card${isTop ? ' top-match' : ''}`}>
      {isTop && (
        <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--primary)', marginBottom: '0.4rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          ⭐ Top Match
        </div>
      )}
      <div className="disease-name">{disease.name}</div>
      <div className="disease-meta">
        {severityBadge(disease.severity)}
        <span className="badge badge-category">{disease.category}</span>
        {disease.recommended_action && (
          <span className={`badge badge-action-${disease.recommended_action.toLowerCase().replace(/\s+/g, '-')}`}>
            {disease.recommended_action}
          </span>
        )}
      </div>
      <ConfidenceBar confidence={disease.confidence} label={disease.label} />
      {disease.denied_symptoms_hit?.length > 0 && (
        <p style={{ fontSize: '0.78rem', color: 'var(--neutral-500)', marginTop: '0.4rem', fontStyle: 'italic' }}>
          Lowered because you reported no: {disease.denied_symptoms_hit.map(fmt).join(', ')}
        </p>
      )}
      {disease.description && (
        <p style={{ fontSize: '0.83rem', color: 'var(--neutral-600)', marginTop: '0.5rem' }}>{disease.description}</p>
      )}
      {/* Matched / missing symptoms */}
      {disease.matched_symptoms?.length > 0 && (
        <div style={{ marginTop: '0.6rem' }}>
          {disease.matched_symptoms.map((s) => (
            <span key={s} className="symptom-chip-matched">✓ {fmt(s)}</span>
          ))}
          {disease.missing_symptoms?.slice(0, 4).map((s) => (
            <span key={s} className="symptom-chip-missing">{fmt(s)}</span>
          ))}
        </div>
      )}
    </div>
  );
}

