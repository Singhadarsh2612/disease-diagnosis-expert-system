import { useState } from 'react';
import { uploadCSV, downloadCSVTemplate } from '../../services/api.js';
import { Modal } from './DoctorWidgets.jsx';

export function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function CsvImportModal({ hasUnsaved, onImported, onClose }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState([]);
  const [rowCount, setRowCount] = useState(0);
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);

  async function pick(f) {
    setReport(null); setError('');
    if (!f) return;
    if (!f.name.toLowerCase().endsWith('.csv')) { setError('Please choose a .csv file.'); return; }
    setFile(f);
    const lines = (await f.text()).split(/\r?\n/).filter((l) => l.trim());
    setRowCount(Math.max(0, lines.length - 1));
    setPreview(lines.slice(0, 4));
  }

  async function upload() {
    setBusy(true); setError('');
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await uploadCSV(fd);
      setReport(res.data);
      if ((res.data.added?.length || 0) + (res.data.updated?.length || 0) > 0) await onImported(res.data);
    } catch (e) {
      setError(e.message);
    } finally { setBusy(false); }
  }

  async function template() {
    try { const r = await downloadCSVTemplate(); saveBlob(r.data, 'disease_import_template.csv'); }
    catch (e) { setError(e.message); }
  }

  return (
    <Modal title="⬆️ Upload CSV" wide onClose={onClose}
      footer={<><button className="btn btn-secondary" onClick={onClose}>Close</button>
        <button className="btn btn-primary" disabled={!file || busy || hasUnsaved} onClick={upload}>{busy ? 'Importing…' : 'Import'}</button></>}>
      {hasUnsaved && (
        <div className="emergency-banner" style={{ marginTop: 0 }}>
          <p>You have unsaved changes. Save or discard them first, because an import reloads the table.</p>
        </div>
      )}
      <p className="text-muted" style={{ marginBottom: 8 }}>
        Diseases with the same name are updated; new names are added. Importing changes the live knowledge base straight away.{' '}
        <a href="#template" onClick={(e) => { e.preventDefault(); template(); }} style={{ color: 'var(--primary-dark)' }}>Download template</a>
      </p>
      <label className={`dp-drop${drag ? ' dp-drop-active' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files[0]); }}>
        <input type="file" accept=".csv" style={{ display: 'none' }} onChange={(e) => pick(e.target.files[0])} />
        {file ? <strong>{file.name}</strong> : 'Drop a .csv file here, or click to choose'}
      </label>
      {file && (
        <div style={{ marginTop: 10 }}>
          <p className="section-title">Preview ({rowCount} row{rowCount === 1 ? '' : 's'})</p>
          <pre className="dp-preview">{preview.join('\n')}</pre>
        </div>
      )}
      {error && <p style={{ color: 'var(--emergency)', marginTop: 8 }}>{error}</p>}
      {report && (
        <div style={{ marginTop: 12 }}>
          <p className="section-title">Import report</p>
          <p style={{ color: 'var(--success)', fontWeight: 600 }}>{report.summary}</p>
          {report.errors?.length > 0 && (
            <ul style={{ paddingLeft: '1.2rem', color: 'var(--emergency)', fontSize: '0.9rem' }}>
              {report.errors.map((e, i) => <li key={i}>Row {e.row}: {e.message}</li>)}
            </ul>
          )}
        </div>
      )}
    </Modal>
  );
}

