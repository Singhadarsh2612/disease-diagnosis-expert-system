import { useState } from 'react';
import { Modal } from './DoctorWidgets.jsx';
import { addDoctorSymptom } from '../../services/api.js';

export default function AddSymptomModal({
  categories = [],
  initialName = '',
  editedBy = '',
  onSuccess,
  onSelectExisting,
  onClose,
}) {
  const [displayName, setDisplayName] = useState(initialName);
  const [category, setCategory] = useState(categories[0] || 'Common');
  const [synonymsText, setSynonymsText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [similarWarning, setSimilarWarning] = useState(null);

  async function submit(confirmNotDuplicate = false) {
    const cleanName = displayName.trim();
    if (!cleanName) {
      setError('Display name is required');
      return;
    }
    if (!/^[a-zA-Z0-9 -]{2,50}$/.test(cleanName)) {
      setError('Display name must be 2-50 characters with only letters, digits, spaces, and hyphens');
      return;
    }
    if (!editedBy.trim()) {
      setError('Please enter your name in the "Your name" top bar field before creating a symptom');
      return;
    }

    const cleanSynonyms = synonymsText
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    setBusy(true);
    setError('');
    try {
      const { data } = await addDoctorSymptom({
        display_name: cleanName,
        category,
        synonyms: cleanSynonyms,
        confirm_not_duplicate: confirmNotDuplicate,
        edited_by: editedBy.trim(),
      });
      if (onSuccess) onSuccess(data.symptom);
      onClose();
    } catch (e) {
      if (e.status === 409 && e.data?.error === 'similar_exists') {
        setSimilarWarning(e.data.similar || []);
      } else {
        setError(e.data?.error?.message || e.message);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      title="➕ Add New Symptom"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          {!similarWarning && (
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => submit(false)}
              disabled={busy || !displayName.trim()}
            >
              {busy ? 'Adding…' : 'Add Symptom'}
            </button>
          )}
        </>
      }
    >
      <div style={{ display: 'grid', gap: '1rem', padding: '0.25rem 0' }}>
        <div>
          <label style={{ display: 'block', fontWeight: 600, fontSize: '0.9rem', marginBottom: 4 }}>
            Display name *
          </label>
          <input
            className="dp-input"
            autoFocus
            placeholder="e.g. Loss of balance"
            value={displayName}
            onChange={(e) => {
              setDisplayName(e.target.value);
              setSimilarWarning(null);
            }}
          />
          <small className="text-muted" style={{ display: 'block', marginTop: 4 }}>
            Letters, digits, spaces, and hyphens only (e.g. Loss of balance → loss_of_balance).
          </small>
        </div>

        <div>
          <label style={{ display: 'block', fontWeight: 600, fontSize: '0.9rem', marginBottom: 4 }}>
            Category *
          </label>
          <select
            className="dp-input"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            {categories.map((c) => (
              <option key={c} value={c}>
                {c.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label style={{ display: 'block', fontWeight: 600, fontSize: '0.9rem', marginBottom: 4 }}>
            Synonyms (comma-separated, optional)
          </label>
          <input
            className="dp-input"
            placeholder="e.g. off balance, unsteady on feet, losing balance"
            value={synonymsText}
            onChange={(e) => setSynonymsText(e.target.value)}
          />
          <small className="text-muted" style={{ display: 'block', marginTop: 4 }}>
            Common phrases patients might use in chat.
          </small>
        </div>

        {error && (
          <div style={{ color: 'var(--emergency)', fontSize: '0.88rem', fontWeight: 600 }}>
            ⚠️ {error}
          </div>
        )}

        {similarWarning && (
          <div
            style={{
              background: '#fef3c7',
              border: '1.5px solid #f59e0b',
              borderRadius: 'var(--radius-sm)',
              padding: '0.9rem 1rem',
              color: '#92400e',
            }}
          >
            <div style={{ fontWeight: 700, marginBottom: '0.4rem', fontSize: '0.95rem' }}>
              ⚠️ Similar symptoms exist:
            </div>
            <p style={{ margin: '0 0 0.75rem', fontSize: '0.9rem' }}>
              Similar symptoms exist:{' '}
              <strong>{similarWarning.map((s) => s.display_name).join(', ')}</strong>. Is yours different?
            </p>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {similarWarning.map((s) => (
                <button
                  key={s.name}
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => {
                    if (onSelectExisting) onSelectExisting(s.name);
                    onClose();
                  }}
                  title={`Use existing symptom ${s.display_name}`}
                >
                  Use existing &ldquo;{s.display_name}&rdquo;
                </button>
              ))}
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => submit(true)}
                disabled={busy}
              >
                {busy ? 'Saving…' : 'No, add as new'}
              </button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}

