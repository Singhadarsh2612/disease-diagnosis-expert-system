/** SelectedSymptomsBar — chips row showing chosen symptoms with remove button */
const fmt = (s) => s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

export default function SelectedSymptomsBar({ symptoms, onRemove }) {
  if (symptoms.length === 0) return null;
  return (
    <div className="selected-symptoms-wrap">
      <span className="selected-symptoms-label">Selected symptoms ({symptoms.length}):</span>
      {symptoms.map((s) => (
        <span key={s} className="chip">
          {fmt(s)}
          <button className="chip-remove" onClick={() => onRemove(s)} title="Remove">×</button>
        </span>
      ))}
    </div>
  );
}

