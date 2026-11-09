/** ConfidenceBar — shows a coloured bar for High/Moderate/Low */
export default function ConfidenceBar({ confidence, label }) {
  const pct = Math.round(confidence * 100);
  return (
    <div className="confidence-bar-wrap">
      <div className="confidence-bar-bg">
        <div
          className={`confidence-bar-fill bar-${label}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`confidence-label label-${label}`}>{label} {pct}%</span>
    </div>
  );
}

