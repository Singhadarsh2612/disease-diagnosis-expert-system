import { useEffect, useMemo, useRef, useState } from 'react';

/* ── Modal / confirm / text editor / toast ─────────────────────────────── */

export function Modal({ title, onClose, children, footer, wide }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);
  return (
    <div className="dp-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="dp-modal card" style={{ maxWidth: wide ? 760 : 520 }} role="dialog" aria-modal="true">
        <div className="card-header" style={{ justifyContent: 'space-between' }}>
          <span>{title}</span>
          <button className="btn btn-ghost btn-sm" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="card-body dp-modal-body">{children}</div>
        {footer && <div className="dp-modal-footer">{footer}</div>}
      </div>
    </div>
  );
}

export function ConfirmDialog({ title, children, confirmLabel = 'Confirm', danger, busy, onConfirm, onCancel }) {
  return (
    <Modal
      title={title}
      onClose={onCancel}
      footer={
        <>
          <button className="btn btn-secondary" onClick={onCancel} disabled={busy}>Cancel</button>
          <button className={`btn ${danger ? 'btn-danger' : 'btn-primary'}`} onClick={onConfirm} disabled={busy}>
            {busy ? 'Working…' : confirmLabel}
          </button>
        </>
      }
    >
      {children}
    </Modal>
  );
}

export function TextEditorModal({ title, value, onSave, onClose }) {
  const [text, setText] = useState(value || '');
  return (
    <Modal
      title={title}
      onClose={onClose}
      wide
      footer={
        <>
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={() => { onSave(text); onClose(); }}>Done</button>
        </>
      }
    >
      <textarea className="feedback-textarea" style={{ minHeight: 220, fontSize: '1rem' }} autoFocus
        value={text} onChange={(e) => setText(e.target.value)} />
    </Modal>
  );
}

export function Toast({ toast, onClose }) {
  useEffect(() => {
    if (!toast) return undefined;
    const t = setTimeout(onClose, toast.type === 'error' ? 8000 : 5000);
    return () => clearTimeout(t);
  }, [toast, onClose]);
  if (!toast) return null;
  return (
    <div className={`dp-toast dp-toast-${toast.type || 'success'}`} role="status" onClick={onClose}>
      {toast.type === 'error' ? '⚠️ ' : '✓ '}{toast.message}
    </div>
  );
}

/* ── Symptom chip picker (autocomplete from the real vocabulary only) ──── */

export function SymptomChipPicker({ value, vocab, vocabMap, onChange, onAddNew }) {
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(false);
  const boxRef = useRef(null);

  const suggestions = useMemo(() => {
    const term = q.trim().toLowerCase().replace(/_/g, ' ');
    if (!term) return [];
    const have = new Set(value);
    return vocab
      .filter((s) => !have.has(s.name) && (s.display_name.toLowerCase().includes(term) || s.name.replace(/_/g, ' ').includes(term)))
      .slice(0, 8);
  }, [q, vocab, value]);

  const add = (name) => { onChange([...value, name]); setQ(''); };

  return (
    <div className="dp-chips" ref={boxRef}>
      <div className="dp-chip-count">{value.length} symptom{value.length === 1 ? '' : 's'}</div>
      <div className="dp-chip-list">
        {value.map((name) => {
          const known = vocabMap[name];
          return (
            <span key={name} className={`chip${known ? '' : ' dp-chip-bad'}`} title={known ? name : 'Not a known symptom'}>
              {known ? known.display_name : name}
              <button type="button" className="chip-remove" aria-label={`Remove ${name}`}
                onClick={() => onChange(value.filter((s) => s !== name))}>×</button>
            </span>
          );
        })}
      </div>
      <div style={{ position: 'relative' }}>
        <input
          className="dp-input" placeholder="+ add symptom (type to search)" value={q}
          onChange={(e) => { setQ(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 200)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') { e.preventDefault(); if (suggestions[0]) add(suggestions[0].name); }
            if (e.key === 'Escape') setOpen(false);
          }}
        />
        {open && (
          <ul className="dp-suggest">
            {suggestions.map((s) => (
              <li key={s.name} onMouseDown={(e) => { e.preventDefault(); add(s.name); }}>
                {s.display_name} <small>{s.category}</small>
              </li>
            ))}
            {suggestions.length === 0 && q.trim() && (
              <li className="dp-suggest-empty">No matching symptom</li>
            )}
            {onAddNew && (
              <li
                onMouseDown={(e) => {
                  e.preventDefault();
                  setOpen(false);
                  onAddNew(q.trim());
                }}
                style={{
                  color: 'var(--primary)',
                  fontWeight: 600,
                  borderTop: '1px solid var(--neutral-200)',
                  background: 'var(--neutral-50)',
                }}
              >
                ➕ Add new symptom...
              </li>
            )}
          </ul>
        )}
      </div>
    </div>
  );
}

/* ── Remedies list editor ──────────────────────────────────────────────── */

export function RemedyEditor({ value, onChange }) {
  const lines = value || [];
  return (
    <div>
      {lines.map((line, i) => (
        <div key={i} style={{ display: 'flex', gap: 4, marginBottom: 4 }}>
          <input className="dp-input" value={line} placeholder="Remedy"
            onChange={(e) => onChange(lines.map((l, j) => (j === i ? e.target.value : l)))} />
          <button type="button" className="btn btn-ghost btn-sm" aria-label="Remove remedy"
            onClick={() => onChange(lines.filter((_, j) => j !== i))}>✕</button>
        </div>
      ))}
      <button type="button" className="btn btn-ghost btn-sm" onClick={() => onChange([...lines, ''])}>+ Add line</button>
    </div>
  );
}

