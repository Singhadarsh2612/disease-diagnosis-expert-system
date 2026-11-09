import { useEffect, useState } from 'react';
import { getDoctorChangelog } from '../../services/api.js';
import { ConfirmDialog } from './DoctorWidgets.jsx';

const TYPE_STYLES = {
  added: { bg: '#dcfce7', color: '#166534', label: '+ Added' },
  edited: { bg: '#dbeafe', color: '#1e40af', label: '✎ Edited' },
  deleted: { bg: '#fee2e2', color: '#991b1b', label: '— Deleted' },
  reverted: { bg: '#f3e8ff', color: '#6b21a8', label: '↺ Restored' },
};

export default function VersionDrawer({ hasUnsaved, onRestore, onClose }) {
  const [changelog, setChangelog] = useState(null);
  const [error, setError] = useState('');
  const [pick, setPick] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getDoctorChangelog()
      .then((r) => setChangelog(r.data.changelog || []))
      .catch((e) => setError(e.message));
  }, []);

  async function restore() {
    if (!pick?.backup_file) return;
    setBusy(true);
    try {
      await onRestore(pick.backup_file);
      setPick(null);
      onClose();
    } catch (e) {
      setError(e.message);
      setPick(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="dp-overlay dp-overlay-right" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <aside className="dp-drawer" style={{ width: 480 }}>
        <div className="card-header" style={{ justifyContent: 'space-between' }}>
          <span>🕘 Version History & Change Log</span>
          <button className="btn btn-ghost btn-sm" onClick={onClose}>✕</button>
        </div>
        <div className="card-body" style={{ overflowY: 'auto' }}>
          <p className="text-muted" style={{ marginBottom: '0.75rem' }}>
            Every save is recorded with detailed changes and a restorable backup.
          </p>
          {error && <p style={{ color: 'var(--emergency)' }}>{error}</p>}
          {!changelog && !error && <p className="text-muted">Loading change log…</p>}
          {changelog && changelog.length === 0 && (
            <p className="text-muted">No change log entries yet. Save a change to create one.</p>
          )}
          {changelog && changelog.map((entry, idx) => (
            <div key={idx} className="history-entry" style={{ padding: '0.85rem', marginBottom: '0.75rem', border: '1px solid var(--neutral-200)', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>
                  Version {entry.version || '?'}
                </span>
                <span className="text-muted" style={{ fontSize: '0.8rem' }}>
                  {entry.saved_at ? new Date(entry.saved_at).toLocaleString() : ''}
                </span>
              </div>
              <div className="text-muted" style={{ fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                Saved by <strong>{entry.edited_by || 'Doctor'}</strong>
              </div>

              {entry.changes && entry.changes.length > 0 && (
                <div style={{ margin: '0.5rem 0', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {entry.changes.map((c, cIdx) => {
                    const style = TYPE_STYLES[c.type] || { bg: 'var(--neutral-100)', color: 'var(--neutral-700)', label: c.type };
                    return (
                      <div key={cIdx} style={{ fontSize: '0.84rem', lineHeight: '1.3' }}>
                        <span
                          style={{
                            background: style.bg,
                            color: style.color,
                            fontWeight: 600,
                            padding: '1px 6px',
                            borderRadius: '4px',
                            marginRight: '6px',
                            fontSize: '0.75rem',
                          }}
                        >
                          {style.label}
                        </span>
                        <strong>{c.disease}</strong>
                        {c.details && (
                          <span className="text-muted" style={{ fontSize: '0.82rem', marginLeft: '4px' }}>
                            ({c.details})
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {entry.backup_file && (
                <button
                  className="btn btn-secondary btn-sm mt-1"
                  onClick={() => setPick(entry)}
                  title={`Restore backup from ${entry.backup_file}`}
                >
                  ↺ Restore this version
                </button>
              )}
            </div>
          ))}
        </div>
      </aside>
      {pick && (
        <ConfirmDialog
          title={`Restore version ${pick.version}?`}
          confirmLabel="Restore"
          busy={busy}
          onConfirm={restore}
          onCancel={() => setPick(null)}
        >
          <p>
            This replaces the active knowledge base with <strong>version {pick.version}</strong> saved by{' '}
            <strong>{pick.edited_by || 'Doctor'}</strong> ({pick.saved_at ? new Date(pick.saved_at).toLocaleString() : ''}) and updates the diagnosis engine.
          </p>
          {hasUnsaved && (
            <p style={{ color: 'var(--emergency)', marginTop: 8, fontWeight: 600 }}>
              ⚠️ Your unsaved changes in the table will be lost.
            </p>
          )}
        </ConfirmDialog>
      )}
    </div>
  );
}
