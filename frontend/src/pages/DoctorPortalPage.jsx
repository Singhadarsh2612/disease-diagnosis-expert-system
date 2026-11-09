import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getDoctorKnowledge, getDoctorKnowledgeVersion, saveDoctorKnowledge, revertDoctorVersion,
  downloadDoctorCSV, clearDoctorToken,
} from '../services/api.js';
import {
  ConfirmDialog, TextEditorModal, Toast, SymptomChipPicker, RemedyEditor, Modal,
} from '../components/doctor/DoctorWidgets.jsx';
import AddDiseaseModal from '../components/doctor/AddDiseaseModal.jsx';
import VersionDrawer from '../components/doctor/VersionDrawer.jsx';
import CsvImportModal, { saveBlob } from '../components/doctor/CsvImportModal.jsx';
import AddSymptomModal from '../components/doctor/AddSymptomModal.jsx';
import ManageSymptomsDrawer from '../components/doctor/ManageSymptomsDrawer.jsx';

const FIELDS = ['name', 'category', 'severity', 'symptoms', 'description', 'recommended_action',
  'next_steps', 'homeopathic_remedies', 'icd10'];
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
let keyCounter = 0;
const newKey = () => `r${++keyCounter}`;
const withKey = (d, extra = {}) => ({ ...d, _key: newKey(), ...extra });
const pretty = (s) => String(s || '').replace(/[_-]/g, ' ');

function timeAgo(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  const now = new Date();
  const diffSec = Math.floor((now - date) / 1000);
  if (diffSec < 60) return 'just now';
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}h ago`;
  const diffDay = Math.floor(diffHour / 24);
  if (diffDay < 30) return `${diffDay}d ago`;
  return date.toLocaleDateString();
}

/* ── One table row ─────────────────────────────────────────────────────── */

const Row = memo(function Row({ row, orig, meta, vocab, vocabMap, errors, onChange, onEditText, onDuplicate, onDelete, onAddNewSymptom }) {
  const isNew = !orig;
  const changed = (f) => isNew || !same(row[f], orig[f]);
  const cls = (f) => (changed(f) ? 'dp-changed' : '');
  const rowChanged = isNew || FIELDS.some((f) => changed(f));
  const set = (patch) => onChange(row._key, patch);

  const textCell = (field, title) => (
    <td className={cls(field)} onClick={() => onEditText(row._key, field, title)} title="Click to edit" style={{ cursor: 'pointer' }}>
      <div className="dp-longtext">{row[field] || <span className="text-muted">— click to add —</span>}</div>
    </td>
  );

  return (
    <tr id={`row-${row._key}`} className={`${rowChanged ? 'dp-row-changed' : ''}${isNew ? ' dp-row-new' : ''}${errors ? ' dp-row-error' : ''}`}>
      <td className={cls('name')}>
        {isNew && <span className="badge badge-category" style={{ marginBottom: 4, display: 'inline-block' }}>NEW</span>}
        <input className="dp-input dp-name" value={row.name} placeholder="Disease name" onChange={(e) => set({ name: e.target.value })} />
        {row.last_edited_by && (
          <div className="text-muted" style={{ fontSize: '0.74rem', marginTop: '3px', lineHeight: '1.2' }}>
            last edited by {row.last_edited_by}{row.last_edited_at ? `, ${timeAgo(row.last_edited_at)}` : ''}
          </div>
        )}
        {errors && <ul className="dp-row-errors">{errors.map((m, i) => <li key={i}>{m}</li>)}</ul>}
      </td>
      <td className={cls('category')}>
        <select className="dp-input" value={row.category} onChange={(e) => set({ category: e.target.value })}>
          {!meta.categories.includes(row.category) && <option value={row.category}>{row.category || '—'}</option>}
          {meta.categories.map((c) => <option key={c} value={c}>{pretty(c)}</option>)}
        </select>
      </td>
      <td className={cls('severity')}>
        <select className={`dp-input dp-badge-select badge-${row.severity}`} value={row.severity} onChange={(e) => set({ severity: e.target.value })}>
          {meta.severities.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </td>
      <td className={cls('symptoms')} style={{ minWidth: 300 }}>
        <SymptomChipPicker
          value={row.symptoms}
          vocab={vocab}
          vocabMap={vocabMap}
          onChange={(symptoms) => set({ symptoms })}
          onAddNew={(initialName) => onAddNewSymptom(row._key, initialName)}
        />
      </td>
      {textCell('description', `Description — ${row.name || 'new disease'}`)}
      <td className={cls('recommended_action')}>
        <select className={`dp-input dp-badge-select badge-action-${row.recommended_action}`} value={row.recommended_action}
          onChange={(e) => set({ recommended_action: e.target.value })}>
          {meta.actions.map((c) => <option key={c} value={c}>{pretty(c)}</option>)}
        </select>
      </td>
      {textCell('next_steps', `Next steps — ${row.name || 'new disease'}`)}
      <td className={cls('homeopathic_remedies')} style={{ minWidth: 220 }}>
        <RemedyEditor value={row.homeopathic_remedies} onChange={(homeopathic_remedies) => set({ homeopathic_remedies })} />
      </td>
      <td className={cls('icd10')}>
        <input className="dp-input" style={{ width: 80 }} value={row.icd10 || ''} onChange={(e) => set({ icd10: e.target.value })} />
      </td>
      <td className="dp-actions-cell">
        <button className="btn btn-secondary btn-sm" onClick={() => onDuplicate(row._key)} title="Duplicate this row">⧉ Duplicate</button>
        <button className="btn btn-ghost btn-sm" style={{ color: 'var(--emergency)' }} onClick={() => onDelete(row._key)} title="Delete this row">🗑 Delete</button>
      </td>
    </tr>
  );
});

/* ── Page ──────────────────────────────────────────────────────────────── */

export default function DoctorPortalPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [meta, setMeta] = useState(null);                 // categories, severities, actions, version…
  const [vocab, setVocab] = useState([]);
  const [rows, setRows] = useState([]);
  const [originals, setOriginals] = useState({});         // id -> original disease
  const [deletedIds, setDeletedIds] = useState([]);       // ids of original rows removed
  const [search, setSearch] = useState('');
  const [catFilter, setCatFilter] = useState('');
  const [sortDir, setSortDir] = useState('none');         // 'none' | 'asc' | 'desc'
  const [pinnedKeys, setPinnedKeys] = useState(new Set());
  const [toast, setToast] = useState(null);
  const [textEdit, setTextEdit] = useState(null);         // {key, field, title}
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [showVersions, setShowVersions] = useState(false);
  const [showCsv, setShowCsv] = useState(false);
  const [confirmSave, setConfirmSave] = useState(false);
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  const [doctorName, setDoctorName] = useState(() => sessionStorage.getItem('doctor_name') || '');
  const [saving, setSaving] = useState(false);
  const [saveErrors, setSaveErrors] = useState(null);     // {list: [...], byKey: {key: [msgs]}}
  const [remoteUpdate, setRemoteUpdate] = useState(null);
  const [conflictModal, setConflictModal] = useState(null);
  const [addSymptomTarget, setAddSymptomTarget] = useState(null);
  const [showManageSymptoms, setShowManageSymptoms] = useState(false);
  const wrapRef = useRef(null);

  const vocabMap = useMemo(() => Object.fromEntries(vocab.map((s) => [s.name, s])), [vocab]);

  const load = useCallback(async () => {
    setLoading(true); setLoadError('');
    try {
      const { data } = await getDoctorKnowledge();
      setMeta({ categories: data.categories, severities: data.severities, actions: data.actions,
        version: data.version, last_edited_by: data.last_edited_by, saved_at: data.saved_at });
      setVocab(data.symptoms);
      setRows(data.diseases.map((d) => withKey(d)));
      setOriginals(Object.fromEntries(data.diseases.map((d) => [d.id, d])));
      setDeletedIds([]); setSaveErrors(null); setRemoteUpdate(null);
    } catch (e) {
      setLoadError(e.message);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  /* 30-second version polling */
  useEffect(() => {
    if (!meta?.version) return undefined;
    const interval = setInterval(async () => {
      try {
        const { data } = await getDoctorKnowledgeVersion();
        if (data.version && meta.version && data.version !== meta.version) {
          setRemoteUpdate(data);
        }
      } catch (err) {
        // quiet catch
      }
    }, 30000);
    return () => clearInterval(interval);
  }, [meta?.version]);

  /* unsaved-change tracking */
  const changedKeys = useMemo(() => new Set(rows
    .filter((r) => { const o = originals[r.id]; return !o || FIELDS.some((f) => !same(r[f], o[f])); })
    .map((r) => r._key)), [rows, originals]);
  const unsavedCount = changedKeys.size + deletedIds.length;
  const hasUnsaved = unsavedCount > 0;

  useEffect(() => {
    if (!hasUnsaved) return undefined;
    const h = (e) => { e.preventDefault(); e.returnValue = ''; };
    window.addEventListener('beforeunload', h);
    return () => window.removeEventListener('beforeunload', h);
  }, [hasUnsaved]);

  /* row actions (stable callbacks so memo rows don't all re-render) */
  const updateRow = useCallback((key, patch) => setRows((rs) => rs.map((r) => (r._key === key ? { ...r, ...patch } : r))), []);
  const duplicateRow = useCallback((key) => setRows((rs) => {
    const i = rs.findIndex((r) => r._key === key);
    if (i < 0) return rs;
    const { id, ...rest } = rs[i];
    const copy = withKey({ ...rest, id: '', name: `${rs[i].name} (copy)`, symptoms: [...rs[i].symptoms],
      homeopathic_remedies: [...(rs[i].homeopathic_remedies || [])] });
    return [...rs.slice(0, i + 1), copy, ...rs.slice(i + 1)];
  }), []);
  const askDelete = useCallback((key) => setConfirmDelete(key), []);
  const openTextEdit = useCallback((key, field, title) => setTextEdit({ key, field, title }), []);

  function doDelete() {
    const row = rows.find((r) => r._key === confirmDelete);
    if (row && originals[row.id]) setDeletedIds((ids) => [...ids, row.id]);
    setRows((rs) => rs.filter((r) => r._key !== confirmDelete));
    setConfirmDelete(null);
  }

  function addDisease(d) {
    const newRow = withKey({ ...d, id: '' });
    setPinnedKeys((prev) => new Set(prev).add(newRow._key));
    setRows((rs) => [newRow, ...rs]);
    setSearch(''); setCatFilter('');
    setTimeout(() => wrapRef.current?.scrollTo({ top: 0, behavior: 'smooth' }), 50);
  }

  const cycleSort = useCallback(() => {
    setPinnedKeys(new Set());
    setSortDir((cur) => {
      if (cur === 'none') return 'asc';
      if (cur === 'asc') return 'desc';
      return 'none';
    });
  }, []);

  /* filtering & sorting */
  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    const filtered = rows.filter((r) => {
      if (catFilter && r.category !== catFilter) return false;
      if (!q) return true;
      return r.name.toLowerCase().includes(q) || r.symptoms.some((s) =>
        s.includes(q.replace(/ /g, '_')) || (vocabMap[s]?.display_name || '').toLowerCase().includes(q));
    });
    if (sortDir === 'none') return filtered;

    const pinned = filtered.filter((r) => pinnedKeys.has(r._key));
    const unpinned = filtered.filter((r) => !pinnedKeys.has(r._key));

    unpinned.sort((a, b) => {
      const cmp = (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' });
      return sortDir === 'asc' ? cmp : -cmp;
    });

    return [...pinned, ...unpinned];
  }, [rows, search, catFilter, vocabMap, sortDir, pinnedKeys]);

  /* save */
  async function doSave() {
    const cleanName = doctorName.trim();
    if (!cleanName) {
      setToast({ type: 'error', message: 'Please enter your name in the "Your name" field before saving.' });
      return;
    }
    setSaving(true);
    sessionStorage.setItem('doctor_name', cleanName);
    const payload = rows.map((r) => {
      const out = {};
      FIELDS.forEach((f) => { out[f] = r[f]; });
      if (originals[r.id]) out.id = r.id;
      return out;
    });
    try {
      const { data } = await saveDoctorKnowledge(payload, cleanName, meta.version);
      setConfirmSave(false);
      setToast({ type: 'success', message: `Saved. Knowledge base is now version ${data.version} (${data.disease_count} diseases). The diagnosis engine is updated.` });
      await load();
    } catch (e) {
      setConfirmSave(false);
      if (e.status === 409 || e.data?.error === 'conflict') {
        setConflictModal(e.data);
        return;
      }
      const errs = e.data?.errors;
      if (errs) {
        const byKey = {}; const list = [];
        errs.forEach((er) => {
          const key = er.row > 0 ? rows[er.row - 1]?._key : null;
          const where = er.row > 0 ? `Row ${er.row}${rows[er.row - 1]?.name ? ` (${rows[er.row - 1].name})` : ''}, ${pretty(er.field)}` : 'Whole table';
          list.push(`${where}: ${er.message}`);
          if (key) (byKey[key] = byKey[key] || []).push(`${pretty(er.field)}: ${er.message}`);
        });
        setSaveErrors({ list, byKey });
        setSearch(''); setCatFilter('');
        setTimeout(() => {
          const first = Object.keys(byKey)[0];
          if (first) document.getElementById(`row-${first}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 100);
      } else {
        setToast({ type: 'error', message: e.message });
      }
    } finally { setSaving(false); }
  }

  async function restoreVersion(filename) {
    const cleanName = doctorName.trim() || 'Doctor';
    const { data } = await revertDoctorVersion(filename, cleanName);
    await load();
    setToast({ type: 'success', message: `Restored. Knowledge base is now version ${data.version}.` });
  }

  async function downloadCsv() {
    try { const r = await downloadDoctorCSV(); saveBlob(r.data, 'knowledge_base.csv'); }
    catch (e) { setToast({ type: 'error', message: e.message }); }
  }

  function logout() { clearDoctorToken(); navigate('/doctor/login'); }

  /* ── render ── */
  if (loading && !meta) return <div className="empty-state"><div className="spinner spinner-dark" style={{ margin: '0 auto 1rem' }} />Loading the knowledge base…</div>;
  if (loadError && !meta) {
    return (
      <div className="empty-state">
        <div className="empty-icon">⚠️</div><h3>Could not load the knowledge base</h3><p>{loadError}</p>
        <button className="btn btn-primary mt-2" onClick={load}>Try again</button>
      </div>
    );
  }

  const textRow = textEdit && rows.find((r) => r._key === textEdit.key);
  const delRow = confirmDelete && rows.find((r) => r._key === confirmDelete);
  const existingNames = new Set(rows.map((r) => r.name.trim().toLowerCase()));

  return (
    <div className="dp-page">
      <div className="dp-topbar">
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700 }}>Doctor Portal — Disease Knowledge Base</h2>
          <p className="text-muted" style={{ fontSize: '0.95rem' }}>
            {rows.length} diseases · version {meta.version}{meta.last_edited_by ? ` · last edited by ${meta.last_edited_by}` : ''}
          </p>
        </div>
        <div className="dp-buttons" style={{ alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <label style={{ fontSize: '0.85rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.3rem', whiteSpace: 'nowrap' }}>
              <span>Your name:</span>
              <input
                type="text"
                className="dp-input"
                style={{ width: 140, padding: '0.45rem 0.6rem' }}
                placeholder="Dr. Name"
                value={doctorName}
                onChange={(e) => {
                  setDoctorName(e.target.value);
                  sessionStorage.setItem('doctor_name', e.target.value);
                }}
              />
            </label>
          </div>
          <button
            className="btn btn-primary"
            disabled={!hasUnsaved || saving}
            onClick={() => {
              if (!doctorName.trim()) {
                setToast({ type: 'error', message: 'Please enter your name in the "Your name" field before saving.' });
                return;
              }
              setConfirmSave(true);
            }}
          >
            💾 Save changes
          </button>
          <button className="btn btn-secondary" onClick={() => setShowAdd(true)}>➕ Add disease</button>
          <button className="btn btn-secondary" onClick={() => setShowManageSymptoms(true)}>🩺 Manage symptoms</button>
          <button className="btn btn-secondary" onClick={downloadCsv}>⬇️ Download CSV</button>
          <button className="btn btn-secondary" onClick={() => setShowCsv(true)}>⬆️ Upload CSV</button>
          <button className="btn btn-secondary" onClick={() => setShowVersions(true)}>🕘 Version history</button>
          <button className="btn btn-ghost" onClick={logout}>Logout</button>
        </div>
      </div>

      {remoteUpdate && (
        <div className="dp-banner" style={{ background: '#eff6ff', borderColor: '#3b82f6', color: '#1e40af' }}>
          <span>
            ℹ️ New changes saved by <strong>{remoteUpdate.last_edited_by || 'another doctor'}</strong> (v{remoteUpdate.version}). Refresh to see them.
          </span>
          <button className="btn btn-secondary btn-sm" onClick={() => { setRemoteUpdate(null); load(); }}>
            Refresh
          </button>
        </div>
      )}

      {hasUnsaved && (
        <div className="dp-banner">
          <span>✏️ You have <strong>{unsavedCount}</strong> unsaved change{unsavedCount === 1 ? '' : 's'}. Patients will not see them until you save.</span>
          <button className="btn btn-secondary btn-sm" onClick={() => setConfirmDiscard(true)}>Discard changes</button>
        </div>
      )}

      {saveErrors && (
        <div className="emergency-banner" style={{ margin: '0 0 0.75rem' }}>
          <h4>⚠️ Nothing was saved — please fix these {saveErrors.list.length} problem{saveErrors.list.length === 1 ? '' : 's'}:</h4>
          <ul style={{ paddingLeft: '1.2rem', color: '#991b1b', fontSize: '0.95rem' }}>
            {saveErrors.list.map((m, i) => <li key={i}>{m}</li>)}
          </ul>
        </div>
      )}

      <div className="dp-filters">
        <input className="dp-input" style={{ maxWidth: 360 }} placeholder="🔍 Search by disease or symptom…" value={search} onChange={(e) => setSearch(e.target.value)} />
        <button
          type="button"
          className="btn btn-secondary"
          style={{ whiteSpace: 'nowrap' }}
          onClick={cycleSort}
          title="Click to cycle sorting: A-Z, Z-A, original order"
        >
          Sort A-Z {sortDir === 'asc' ? '↑' : sortDir === 'desc' ? '↓' : ''}
        </button>
        <select className="dp-input" style={{ maxWidth: 220 }} value={catFilter} onChange={(e) => setCatFilter(e.target.value)}>
          <option value="">All categories</option>
          {meta.categories.map((c) => <option key={c} value={c}>{pretty(c)}</option>)}
        </select>
        <span className="text-muted">Showing {visible.length} of {rows.length}</span>
      </div>

      <div className="dp-table-wrap" ref={wrapRef}>
        <table className="dp-table">
          <thead>
            <tr>
              <th
                style={{ minWidth: 200, cursor: 'pointer', userSelect: 'none' }}
                onClick={cycleSort}
                title="Click to sort by disease name (cycles A-Z, Z-A, original order)"
              >
                Name {sortDir === 'asc' ? '↑' : sortDir === 'desc' ? '↓' : ''}
              </th>
              <th>Category</th><th>Severity</th><th>Symptoms</th>
              <th style={{ minWidth: 240 }}>Description</th><th>What the patient should do</th><th style={{ minWidth: 220 }}>Next steps</th>
              <th title="Complementary suggestions, not medical treatment">Remedies <small>(complementary, non-clinical)</small></th>
              <th>ICD-10</th><th>Row actions</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((r) => (
              <Row key={r._key} row={r} orig={originals[r.id]} meta={meta} vocab={vocab} vocabMap={vocabMap}
                errors={saveErrors?.byKey[r._key]} onChange={updateRow} onEditText={openTextEdit}
                onDuplicate={duplicateRow} onDelete={askDelete}
                onAddNewSymptom={(rowKey, initialName) => setAddSymptomTarget({ rowKey, initialName })} />
            ))}
            {visible.length === 0 && (
              <tr><td colSpan={10}><div className="empty-state" style={{ padding: '2rem' }}>
                {rows.length === 0 ? 'The table is empty. Click “Add disease” to start.' : 'No diseases match your search.'}
              </div></td></tr>
            )}
          </tbody>
        </table>
      </div>

      {textEdit && textRow && (
        <TextEditorModal title={textEdit.title} value={textRow[textEdit.field]}
          onSave={(v) => updateRow(textEdit.key, { [textEdit.field]: v })} onClose={() => setTextEdit(null)} />
      )}

      {confirmDelete && delRow && (
        <ConfirmDialog title="Delete this disease?" danger confirmLabel="Delete" onConfirm={doDelete} onCancel={() => setConfirmDelete(null)}>
          <p>Remove <strong>{delRow.name || 'this new row'}</strong> from the table? It is only removed for patients when you click Save changes.</p>
        </ConfirmDialog>
      )}

      {confirmDiscard && (
        <ConfirmDialog title="Discard all changes?" danger confirmLabel="Discard" onConfirm={() => { setConfirmDiscard(false); load(); }} onCancel={() => setConfirmDiscard(false)}>
          <p>All {unsavedCount} unsaved change{unsavedCount === 1 ? '' : 's'} will be lost and the table reloaded from the saved version.</p>
        </ConfirmDialog>
      )}

      {confirmSave && (
        <ConfirmDialog title="Save changes?" confirmLabel="Yes, save" busy={saving} onConfirm={doSave} onCancel={() => setConfirmSave(false)}>
          <p><strong>This updates the diagnosis engine for all patients.</strong> A backup of the current version is kept so you can restore it.</p>
          <label style={{ display: 'block', marginTop: 12, fontWeight: 600, fontSize: '0.9rem' }}>
            Saving as
            <input
              className="dp-input"
              style={{ marginTop: 4 }}
              placeholder="Your name"
              value={doctorName}
              onChange={(e) => {
                setDoctorName(e.target.value);
                sessionStorage.setItem('doctor_name', e.target.value);
              }}
            />
          </label>
        </ConfirmDialog>
      )}

      {conflictModal && (
        <Modal title="Version Conflict" onClose={() => setConflictModal(null)}>
          <div style={{ padding: '1.25rem' }}>
            <p style={{ marginBottom: '1rem', color: '#b91c1c', fontWeight: 600, fontSize: '1rem' }}>
              ⚠️ {conflictModal.last_edited_by || 'Another doctor'} saved changes{' '}
              {conflictModal.last_saved_at ? `at ${new Date(conflictModal.last_saved_at).toLocaleTimeString()}` : ''} (version {conflictModal.current_version}).
            </p>
            <p style={{ marginBottom: '1rem', color: 'var(--neutral-700)' }}>
              Please reload the table to see the latest changes before saving.
            </p>
            <p style={{ color: 'var(--emergency)', fontSize: '0.9rem', marginBottom: '1.5rem', background: 'var(--emergency-bg)', padding: '0.6rem 0.8rem', borderRadius: 'var(--radius-sm)' }}>
              Warning: Reloading will discard your unsaved edits. You can click &ldquo;Copy my changes&rdquo; to copy your modified rows to the clipboard first.
            </p>
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  const changedRows = rows.filter((r) => changedKeys.has(r._key));
                  navigator.clipboard.writeText(JSON.stringify(changedRows, null, 2));
                  setToast({ type: 'success', message: 'Copied your modified rows to clipboard!' });
                }}
              >
                📋 Copy my changes
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  setConflictModal(null);
                  setRemoteUpdate(null);
                  load();
                }}
              >
                🔄 Reload table
              </button>
            </div>
          </div>
        </Modal>
      )}

      {showAdd && (
        <AddDiseaseModal
          meta={meta}
          vocab={vocab}
          vocabMap={vocabMap}
          existingNames={existingNames}
          onAdd={addDisease}
          onClose={() => setShowAdd(false)}
          onAddNewSymptom={(appendCb, initialName) => setAddSymptomTarget({ appendCb, initialName })}
        />
      )}
      {showVersions && <VersionDrawer hasUnsaved={hasUnsaved} onRestore={restoreVersion} onClose={() => setShowVersions(false)} />}
      {showCsv && <CsvImportModal hasUnsaved={hasUnsaved} onImported={async (rep) => { await load(); setToast({ type: 'success', message: rep.summary }); }} onClose={() => setShowCsv(false)} />}

      {addSymptomTarget && (
        <AddSymptomModal
          categories={meta.categories}
          initialName={addSymptomTarget.initialName || ''}
          editedBy={doctorName}
          onSuccess={async (newSym) => {
            await load();
            if (addSymptomTarget.rowKey) {
              const targetRow = rows.find((r) => r._key === addSymptomTarget.rowKey);
              if (targetRow && !targetRow.symptoms.includes(newSym.name)) {
                updateRow(addSymptomTarget.rowKey, { symptoms: [...targetRow.symptoms, newSym.name] });
              }
            } else if (addSymptomTarget.appendCb) {
              addSymptomTarget.appendCb(newSym);
            }
            setToast({ type: 'success', message: `Symptom "${newSym.display_name}" created and added.` });
          }}
          onSelectExisting={(existingName) => {
            if (addSymptomTarget.rowKey) {
              const targetRow = rows.find((r) => r._key === addSymptomTarget.rowKey);
              if (targetRow && !targetRow.symptoms.includes(existingName)) {
                updateRow(addSymptomTarget.rowKey, { symptoms: [...targetRow.symptoms, existingName] });
              }
            } else if (addSymptomTarget.appendCb) {
              addSymptomTarget.appendCb({ name: existingName });
            }
          }}
          onClose={() => setAddSymptomTarget(null)}
        />
      )}

      {showManageSymptoms && (
        <ManageSymptomsDrawer
          vocab={vocab}
          categories={meta.categories}
          editedBy={doctorName}
          onDeleted={async (sym) => {
            await load();
            setToast({ type: 'success', message: `Symptom "${sym.display_name}" deleted.` });
          }}
          onClose={() => setShowManageSymptoms(false)}
        />
      )}

      <Toast toast={toast} onClose={() => setToast(null)} />
    </div>
  );
}

