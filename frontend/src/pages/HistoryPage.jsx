import { useState, useEffect } from 'react';
import { HISTORY_KEY } from '../context/DiagnosisContext.jsx';
import { Link } from 'react-router-dom';

const fmt = (s) => s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function HistoryPage() {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    const stored = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
    setHistory(stored);
  }, []);

  function deleteEntry(id) {
    const updated = history.filter((item) => item.id !== id);
    setHistory(updated);
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
    } catch (e) {
      console.error(e);
    }
  }

  function clearAllData() {
    if (window.confirm('Are you sure you want to clear all diagnosis history and active session data?')) {
      try {
        localStorage.removeItem(HISTORY_KEY);
        localStorage.removeItem('diagnosis_active_session');
      } catch (e) {
        console.error(e);
      }
      setHistory([]);
    }
  }

  if (history.length === 0) {
    return (
      <div className="history-page">
        <h2 style={{ marginBottom: '1.5rem', fontSize: '1.4rem', fontWeight: 700 }}>Diagnosis History</h2>
        <div className="empty-state">
          <div className="empty-icon">📋</div>
          <h3>No history yet</h3>
          <p>Completed diagnoses will appear here automatically.</p>
          <Link to="/chat" className="btn btn-primary" style={{ marginTop: '1rem' }}>Start a Diagnosis</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="history-page">
      <div className="flex justify-between items-center" style={{ marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700 }}>Diagnosis History ({history.length})</h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--neutral-500)' }}>Locally saved on this device</p>
        </div>
        <button className="btn btn-danger btn-sm" onClick={clearAllData}>
          🗑️ Clear All Data
        </button>
      </div>

      {history.map((entry) => (
        <div key={entry.id} className="history-entry" style={{ position: 'relative' }}>
          <div className="flex justify-between items-center">
            <div className="history-meta">{formatDate(entry.timestamp)}</div>
            <button
              className="btn btn-ghost btn-sm"
              style={{ color: 'var(--neutral-400)', padding: '0.2rem 0.5rem', fontSize: '0.8rem' }}
              onClick={() => deleteEntry(entry.id)}
              title="Delete this entry"
            >
              ✕ Delete
            </button>
          </div>

          {entry.diagnosis && (
            <div style={{ fontWeight: 700, fontSize: '1.05rem', marginBottom: '0.4rem', color: 'var(--neutral-800)' }}>
              🩺 {entry.diagnosis.name}
              {' '}
              <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--primary-dark)' }}>
                ({Math.round((entry.diagnosis.confidence || 0) * 100)}% match)
              </span>
            </div>
          )}

          {entry.symptoms?.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem', margin: '0.5rem 0' }}>
              {entry.symptoms.map((s) => (
                <span key={s} className="chip" style={{ fontSize: '0.75rem' }}>✓ {fmt(s)}</span>
              ))}
            </div>
          )}

          {entry.deniedSymptoms?.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem', margin: '0.3rem 0' }}>
              {entry.deniedSymptoms.map((s) => (
                <span key={s} className="chip" style={{ fontSize: '0.75rem', background: '#f3f4f6', color: '#4b5563', borderColor: '#d1d5db' }}>
                  Not: {fmt(s)}
                </span>
              ))}
            </div>
          )}

          {entry.emergencyFlags?.length > 0 && (
            <div style={{ color: 'var(--emergency)', fontSize: '0.83rem', fontWeight: 600, marginTop: '0.3rem' }}>
              🚨 Emergency alert was recorded for this session
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

