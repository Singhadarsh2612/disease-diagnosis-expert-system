import { useState, useEffect, useRef } from 'react';
import { useDiagnosis } from '../context/DiagnosisContext.jsx';
import { getInitialSymptoms, diagnose, extractSymptoms } from '../services/api.js';

import SymptomSelector from '../components/symptoms/SymptomSelector.jsx';
import SelectedSymptomsBar from '../components/symptoms/SelectedSymptomsBar.jsx';
import DiseaseCard from '../components/diagnosis/DiseaseCard.jsx';
import FinalDiagnosisCard from '../components/diagnosis/FinalDiagnosisCard.jsx';

const fmt = (s) => s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

export default function ChatPage() {
  const { state, dispatch } = useDiagnosis();
  const { sessionId, selectedSymptoms, deniedSymptoms = [], possibleDiseases, remainingSymptoms,
          emergencyFlags, finalDiagnosis, loading, error, stage } = state;

  const [categories, setCategories] = useState({});
  const [catLoading, setCatLoading] = useState(true);
  const [freeText, setFreeText] = useState('');
  const [extracting, setExtracting] = useState(false);
  const [extractError, setExtractError] = useState('');
  const [showAll, setShowAll] = useState(false);

  // Load symptom categories on mount
  useEffect(() => {
    getInitialSymptoms()
      .then((res) => setCategories(res.data.categories || {}))
      .catch(() => setCategories({}))
      .finally(() => setCatLoading(false));
  }, []);

  // Auto-diagnose when selected or denied symptoms change (debounced)
  const debounceRef = useRef(null);
  useEffect(() => {
    if (selectedSymptoms.length === 0) return;
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      dispatch({ type: 'SET_LOADING', payload: true });
      try {
        const res = await diagnose(selectedSymptoms, deniedSymptoms);
        dispatch({ type: 'SET_DIAGNOSIS_RESULT', payload: res.data });
        // If we get a final_diagnosis from backend with high confidence, mark done
        if (res.data.final_diagnosis) {
          dispatch({ type: 'SET_FINAL_DIAGNOSIS', payload: res.data.final_diagnosis });
        }
      } catch (e) {
        dispatch({ type: 'SET_ERROR', payload: e.message });
      }
    }, 600);
    return () => clearTimeout(debounceRef.current);
  }, [selectedSymptoms, deniedSymptoms]);

  function toggleSymptom(sym) {
    if (selectedSymptoms.includes(sym)) {
      dispatch({ type: 'REMOVE_SYMPTOM', payload: sym });
    } else {
      dispatch({ type: 'ADD_SYMPTOM', payload: sym });
    }
  }

  async function handleExtract() {
    if (!freeText.trim()) return;
    setExtracting(true);
    setExtractError('');
    try {
      const res = await extractSymptoms(freeText.trim());
      const matched = res.data.matched || [];
      if (matched.length === 0) {
        setExtractError('No known symptoms found. Try selecting from the list below.');
      } else {
        matched.forEach((s) => dispatch({ type: 'ADD_SYMPTOM', payload: s }));
        setFreeText('');
      }
    } catch (e) {
      setExtractError(e.message);
    } finally {
      setExtracting(false);
    }
  }

  function handleFinalize() {
    if (possibleDiseases.length > 0) {
      dispatch({ type: 'SET_FINAL_DIAGNOSIS', payload: possibleDiseases[0] });
    }
  }

  function handleReset() {
    setShowAll(false);
    setFreeText('');
    setExtractError('');
    dispatch({ type: 'RESET' });
  }

  const displayedDiseases = showAll ? possibleDiseases : possibleDiseases.slice(0, 5);

  return (
    <div className="chat-page">
      {/* ── Left: main panel ── */}
      <div className="chat-main">

        {/* Emergency banner */}
        {emergencyFlags.length > 0 && (
          <div className="emergency-banner">
            <h4>🚨 Emergency Alert</h4>
            {emergencyFlags.map((f, i) => (
              <p key={i}>{f.message}</p>
            ))}
          </div>
        )}

        {/* Final diagnosis card */}
        {stage === 'done' && finalDiagnosis && (
          <FinalDiagnosisCard
            diagnosis={finalDiagnosis}
            sessionId={sessionId}
            emergencyFlags={emergencyFlags}
            onReset={handleReset}
            deniedSymptoms={deniedSymptoms}
          />
        )}

        {/* Free-text input */}
        {stage !== 'done' && (
          <div className="card">
            <div className="card-header">💬 Describe in Your Own Words</div>
            <div className="card-body">
              <div className="chat-input-row">
                <input
                  className="chat-input"
                  placeholder='e.g. "I have a headache and feel like throwing up"'
                  value={freeText}
                  onChange={(e) => setFreeText(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleExtract()}
                  disabled={extracting}
                />
                <button className="btn btn-primary" onClick={handleExtract} disabled={extracting || !freeText.trim()}>
                  {extracting ? <span className="spinner" /> : 'Extract'}
                </button>
              </div>
              {extractError && <p style={{ color: 'var(--emergency)', fontSize: '0.83rem', marginTop: '0.5rem' }}>{extractError}</p>}
              <p style={{ fontSize: '0.78rem', color: 'var(--neutral-400)', marginTop: '0.4rem' }}>
                Or select directly from the symptom list below.
              </p>
            </div>
          </div>
        )}

        {/* Selected symptoms bar */}
        {selectedSymptoms.length > 0 && (
          <SelectedSymptomsBar symptoms={selectedSymptoms} onRemove={(s) => dispatch({ type: 'REMOVE_SYMPTOM', payload: s })} />
        )}

        {/* Ruled out symptoms bar */}
        {deniedSymptoms.length > 0 && (
          <div className="selected-symptoms-wrap" style={{ marginTop: '0.4rem' }}>
            <span className="selected-symptoms-label" style={{ color: 'var(--neutral-500)' }}>Ruled out ({deniedSymptoms.length}):</span>
            {deniedSymptoms.map((s) => (
              <span key={s} className="chip" style={{ background: '#f3f4f6', color: '#4b5563', borderColor: '#d1d5db' }}>
                Not: {fmt(s)}
                <button
                  className="chip-remove"
                  onClick={() => dispatch({ type: 'REMOVE_DENIED_SYMPTOM', payload: s })}
                  title="Remove"
                  style={{ color: '#6b7280' }}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}

        {/* Symptom selector */}
        {stage !== 'done' && (
          catLoading
            ? <div className="card card-body" style={{ color: 'var(--neutral-400)' }}>Loading symptoms…</div>
            : <SymptomSelector categories={categories} selectedSymptoms={selectedSymptoms} onToggle={toggleSymptom} />
        )}

        {/* Error */}
        {error && (
          <div className="emergency-banner">
            <h4>⚠️ Error</h4>
            <p>{error}</p>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem', color: 'var(--neutral-500)', fontSize: '0.88rem' }}>
            <div className="spinner spinner-dark" />Analysing symptoms…
          </div>
        )}

        {/* Ranked diseases */}
        {stage === 'diagnosing' && possibleDiseases.length > 0 && (
          <div>
            <div className="flex justify-between items-center" style={{ marginBottom: '0.75rem' }}>
              <p className="section-title">Possible Conditions ({possibleDiseases.length})</p>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                {possibleDiseases.length > 5 && (
                  <button className="btn btn-ghost btn-sm" onClick={() => setShowAll(!showAll)}>
                    {showAll ? 'Show less' : `Show all ${possibleDiseases.length}`}
                  </button>
                )}
                <button className="btn btn-primary btn-sm" onClick={handleFinalize}>
                  Finalise →
                </button>
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {displayedDiseases.map((d, i) => (
                <DiseaseCard key={d.id} disease={d} isTop={i === 0} />
              ))}
            </div>
          </div>
        )}

        {stage === 'diagnosing' && possibleDiseases.length === 0 && !loading && (
          <div className="empty-state">
            <div className="empty-icon">🤔</div>
            <h3>No matching conditions</h3>
            <p>Try adding more symptoms or describing your condition differently.</p>
          </div>
        )}

        {/* Reset */}
        {stage !== 'idle' && stage !== 'done' && (
          <button className="btn btn-secondary btn-sm" style={{ alignSelf: 'flex-start', marginTop: '0.5rem' }} onClick={handleReset}>
            ↺ Reset
          </button>
        )}
      </div>

      {/* ── Right: sidebar ── */}
      <div className="chat-sidebar">
        {/* Follow-up questions */}
        {remainingSymptoms.length > 0 && stage === 'diagnosing' && (
          <div className="card">
            <div className="card-header">❓ Follow-up Questions</div>
            <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
              <p style={{ fontSize: '0.8rem', color: 'var(--neutral-500)', marginBottom: '0.2rem' }}>
                Do you also experience any of the following?
              </p>
              {remainingSymptoms
                .filter((sym) => !deniedSymptoms.includes(sym.name) && !selectedSymptoms.includes(sym.name))
                .slice(0, 8)
                .map((sym) => (
                  <div
                    key={sym.name}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '0.45rem 0.65rem',
                      background: 'var(--neutral-100)',
                      borderRadius: 'var(--radius-sm)',
                      gap: '0.5rem',
                    }}
                  >
                    <span style={{ fontSize: '0.83rem', fontWeight: 500 }}>{fmt(sym.name)}?</span>
                    <div style={{ display: 'flex', gap: '0.35rem', flexShrink: 0 }}>
                      <button
                        className="btn btn-primary btn-sm"
                        style={{ padding: '0.2rem 0.55rem', fontSize: '0.75rem' }}
                        onClick={() => toggleSymptom(sym.name)}
                      >
                        Yes
                      </button>
                      <button
                        className="btn btn-secondary btn-sm"
                        style={{ padding: '0.2rem 0.55rem', fontSize: '0.75rem' }}
                        onClick={() => dispatch({ type: 'ADD_DENIED_SYMPTOM', payload: sym.name })}
                      >
                        No
                      </button>
                    </div>
                  </div>
                ))}
              {remainingSymptoms.filter(
                (sym) => !deniedSymptoms.includes(sym.name) && !selectedSymptoms.includes(sym.name)
              ).length === 0 && (
                <p style={{ fontSize: '0.8rem', color: 'var(--neutral-400)' }}>
                  All current follow-up questions answered.
                </p>
              )}
            </div>
          </div>
        )}

        {/* Quick stats */}
        <div className="card">
          <div className="card-header">📊 Session</div>
          <div className="card-body" style={{ fontSize: '0.85rem', color: 'var(--neutral-600)' }}>
            <p><strong>{selectedSymptoms.length}</strong> symptoms selected</p>
            <p style={{ marginTop: '0.3rem' }}><strong>{possibleDiseases.length}</strong> possible conditions</p>
            {possibleDiseases[0] && (
              <p style={{ marginTop: '0.3rem' }}>
                Top: <strong>{possibleDiseases[0].name}</strong> ({Math.round(possibleDiseases[0].confidence * 100)}%)
              </p>
            )}
          </div>
        </div>

        {/* Tips */}
        <div className="card">
          <div className="card-header">💡 Tips</div>
          <div className="card-body" style={{ fontSize: '0.83rem', color: 'var(--neutral-600)', lineHeight: '1.6' }}>
            <p>• Add more symptoms for better accuracy.</p>
            <p>• Use free-text to describe in plain language.</p>
            <p>• Click <em>Finalise</em> when ready for a full report.</p>
            <p>• This is NOT a medical diagnosis — always see a doctor.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

