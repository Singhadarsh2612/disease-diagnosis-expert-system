import { useState } from 'react';
import { submitFeedback } from '../../services/api.js';

export default function DiagnosisFeedback({ sessionId, finalDisease, deniedSymptoms = [] }) {
  const [sent, setSent] = useState(false);
  const [satisfied, setSatisfied] = useState(null);
  const [missedSymptoms, setMissedSymptoms] = useState('');
  const [comments, setComments] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState('');

  async function handleSubmit(e) {
    if (e) e.preventDefault();
    if (satisfied === null) {
      setErr('Please indicate whether this diagnosis was helpful (Yes or No).');
      return;
    }
    setSubmitting(true);
    setErr('');

    const missedList = missedSymptoms
      .split(',')
      .map((s) => s.trim().toLowerCase().replace(/\s+/g, '_'))
      .filter(Boolean);

    try {
      await submitFeedback({
        session_id: sessionId,
        satisfied: satisfied,
        final_disease: finalDisease,
        missed_symptoms: missedList,
        denied_symptoms: deniedSymptoms,
        comments: comments.trim(),
      });
      setSent(true);
    } catch (e) {
      setErr(e.message || 'Failed to submit feedback.');
    } finally {
      setSubmitting(false);
    }
  }

  if (sent) {
    return (
      <div className="feedback-section">
        <p style={{ color: 'var(--success)', fontWeight: 600 }}>
          ✓ Thank you for your feedback! Your response helps improve the system.
        </p>
      </div>
    );
  }

  return (
    <div className="feedback-section">
      <p className="section-title">Feedback on this Diagnosis</p>
      <p style={{ fontSize: '0.86rem', color: 'var(--neutral-600)', marginBottom: '0.5rem' }}>
        Was this diagnosis helpful and accurate?
      </p>
      <div className="feedback-buttons" style={{ marginBottom: '0.75rem' }}>
        <button
          type="button"
          className={`btn ${satisfied === true ? 'btn-primary' : 'btn-secondary'}`}
          disabled={submitting}
          onClick={() => {
            setSatisfied(true);
            setErr('');
          }}
        >
          👍 Yes, satisfied
        </button>
        <button
          type="button"
          className={`btn ${satisfied === false ? 'btn-danger' : 'btn-secondary'}`}
          disabled={submitting}
          onClick={() => {
            setSatisfied(false);
            setErr('');
          }}
        >
          👎 No, dissatisfied
        </button>
      </div>

      {satisfied !== null && (
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--neutral-600)', marginBottom: '0.2rem' }}>
              Were there any symptoms we missed? (comma-separated)
            </label>
            <input
              type="text"
              className="chat-input"
              style={{ width: '100%', fontSize: '0.85rem', padding: '0.5rem 0.75rem' }}
              placeholder="e.g. ear pain, loss of smell"
              value={missedSymptoms}
              onChange={(e) => setMissedSymptoms(e.target.value)}
              disabled={submitting}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--neutral-600)', marginBottom: '0.2rem' }}>
              Additional comments:
            </label>
            <textarea
              className="feedback-textarea"
              placeholder="Tell us what could be improved..."
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              disabled={submitting}
            />
          </div>

          {err && <p style={{ color: 'var(--emergency)', fontSize: '0.83rem' }}>{err}</p>}

          <button
            type="submit"
            className="btn btn-primary btn-sm"
            style={{ alignSelf: 'flex-start', marginTop: '0.25rem' }}
            disabled={submitting}
          >
            {submitting ? 'Submitting...' : 'Submit Feedback'}
          </button>
        </form>
      )}

      {err && satisfied === null && (
        <p style={{ color: 'var(--emergency)', fontSize: '0.83rem', marginTop: '0.4rem' }}>{err}</p>
      )}
    </div>
  );
}

