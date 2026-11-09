import { useMemo, useState } from 'react';
import { deleteDoctorSymptom } from '../../services/api.js';
import { ConfirmDialog } from './DoctorWidgets.jsx';

export default function ManageSymptomsDrawer({
  vocab = [],
  categories = [],
  editedBy = '',
  onDeleted,
  onClose,
}) {
  const [search, setSearch] = useState('');
  const [catFilter, setCatFilter] = useState('');
  const [pick, setPick] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return vocab.filter((s) => {
      if (catFilter && s.category !== catFilter) return false;
      if (!q) return true;
      return (
        s.display_name.toLowerCase().includes(q) ||
        s.name.toLowerCase().includes(q)
      );
    });
  }, [vocab, search, catFilter]);

  const grouped = useMemo(() => {
    const groups = {};
    for (const s of filtered) {
      const c = s.category || 'Other';
      if (!groups[c]) groups[c] = [];
      groups[c].push(s);
    }
    return groups;
  }, [filtered]);

  async function doDelete() {
    if (!pick) return;
    setBusy(true);
    setError('');
    try {
      await deleteDoctorSymptom(pick.name, editedBy.trim() || 'Doctor');
      setPick(null);
      if (onDeleted) onDeleted(pick);
    } catch (e) {
      setError(e.data?.error?.message || e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="dp-overlay dp-overlay-right"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <aside className="dp-drawer" style={{ width: 500 }}>
        <div className="card-header" style={{ justifyContent: 'space-between' }}>
          <span>🩺 Manage Symptoms ({vocab.length})</span>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="card-body" style={{ overflowY: 'auto' }}>
          <p className="text-muted" style={{ marginBottom: '0.75rem', fontSize: '0.88rem' }}>
            Browse and manage all symptoms in the vocabulary. Unused symptoms can be safely deleted.
          </p>

          {error && (
            <div style={{ color: 'var(--emergency)', marginBottom: '0.75rem', fontWeight: 600 }}>
              ⚠️ {error}
            </div>
          )}

          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <input
              className="dp-input"
              placeholder="🔍 Search symptoms…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <select
              className="dp-input"
              style={{ maxWidth: 150 }}
              value={catFilter}
              onChange={(e) => setCatFilter(e.target.value)}
            >
              <option value="">All</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </div>

          {Object.keys(grouped).length === 0 ? (
            <p className="text-muted" style={{ textAlign: 'center', padding: '2rem 0' }}>
              No symptoms match your search.
            </p>
          ) : (
            Object.entries(grouped).map(([category, syms]) => (
              <div key={category} style={{ marginBottom: '1.25rem' }}>
                <div
                  style={{
                    fontSize: '0.8rem',
                    fontWeight: 700,
                    color: 'var(--neutral-600)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                    borderBottom: '1px solid var(--neutral-200)',
                    paddingBottom: '4px',
                    marginBottom: '6px',
                  }}
                >
                  {category} ({syms.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {syms.map((s) => {
                    const isUsed = (s.used_count || 0) > 0;
                    const isEmergency = Boolean(s.is_emergency);
                    const canDelete = !isUsed && !isEmergency;

                    let tooltip = '';
                    if (isEmergency) tooltip = 'Required by emergency safety rules';
                    else if (isUsed) tooltip = `Used by ${s.used_count} disease(s)`;
                    else tooltip = 'Unused symptom — safe to delete';

                    return (
                      <div
                        key={s.name}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '0.35rem 0.5rem',
                          borderRadius: 'var(--radius-sm)',
                          background: 'var(--neutral-50)',
                          fontSize: '0.9rem',
                        }}
                      >
                        <div style={{ minWidth: 0, flex: 1, marginRight: '0.5rem' }}>
                          <span style={{ fontWeight: 600 }}>{s.display_name}</span>{' '}
                          <code style={{ fontSize: '0.78rem', color: 'var(--neutral-500)' }}>
                            ({s.name})
                          </code>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          {isEmergency ? (
                            <span
                              className="badge"
                              title={tooltip}
                              style={{ background: '#fee2e2', color: '#991b1b', fontSize: '0.75rem' }}
                            >
                              Emergency rule
                            </span>
                          ) : isUsed ? (
                            <span
                              className="badge badge-category"
                              title={tooltip}
                              style={{ fontSize: '0.75rem' }}
                            >
                              used by {s.used_count} disease{s.used_count === 1 ? '' : 's'}
                            </span>
                          ) : (
                            <span
                              className="badge"
                              title={tooltip}
                              style={{ background: '#f1f5f9', color: '#475569', fontSize: '0.75rem' }}
                            >
                              Unused
                            </span>
                          )}

                          <button
                            type="button"
                            className="btn btn-ghost btn-sm"
                            disabled={!canDelete}
                            title={tooltip}
                            style={{
                              color: canDelete ? 'var(--emergency)' : 'var(--neutral-400)',
                              opacity: canDelete ? 1 : 0.4,
                              padding: '2px 6px',
                            }}
                            onClick={() => setPick(s)}
                          >
                            🗑 Delete
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>
      </aside>

      {pick && (
        <ConfirmDialog
          title={`Delete symptom "${pick.display_name}"?`}
          danger
          confirmLabel="Delete"
          busy={busy}
          onConfirm={doDelete}
          onCancel={() => setPick(null)}
        >
          <p>
            Remove <strong>{pick.display_name}</strong> (<code>{pick.name}</code>) from the symptom vocabulary
            and synonym dictionary?
          </p>
          <p className="text-muted" style={{ fontSize: '0.85rem', marginTop: 8 }}>
            This symptom is not currently used by any diseases or emergency safety rules.
          </p>
        </ConfirmDialog>
      )}
    </div>
  );
}

