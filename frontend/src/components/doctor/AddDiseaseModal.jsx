import { useState } from 'react';
import { Modal, SymptomChipPicker, RemedyEditor } from './DoctorWidgets.jsx';

const EMPTY = {
  name: '', category: '', severity: 'mild', recommended_action: 'self-care',
  symptoms: [], description: '', next_steps: '', homeopathic_remedies: [], icd10: '',
};

const label = { display: 'block', fontWeight: 600, fontSize: '0.9rem', marginBottom: 4 };

export default function AddDiseaseModal({ meta, vocab, vocabMap, existingNames, onAdd, onClose, onAddNewSymptom }) {
  const [form, setForm] = useState({ ...EMPTY, category: meta.categories[0] || '' });
  const [errors, setErrors] = useState({});
  const set = (patch) => setForm((f) => ({ ...f, ...patch }));

  function submit() {
    const e = {};
    const name = form.name.trim();
    if (!name) e.name = 'Name is required';
    else if (existingNames.has(name.toLowerCase())) e.name = 'A disease with this name already exists';
    if (form.symptoms.length < 2) e.symptoms = 'Pick at least 2 symptoms';
    if (!form.category) e.category = 'Choose a category';
    setErrors(e);
    if (Object.keys(e).length) return;
    onAdd({ ...form, name, homeopathic_remedies: form.homeopathic_remedies.filter((r) => r.trim()) });
    onClose();
  }

  const err = (k) => errors[k] && <p style={{ color: 'var(--emergency)', fontSize: '0.85rem' }}>{errors[k]}</p>;

  return (
    <Modal title="➕ Add a disease" wide onClose={onClose}
      footer={<><button className="btn btn-secondary" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" onClick={submit}>Add to table</button></>}>
      <div style={{ display: 'grid', gap: '0.9rem' }}>
        <div><label style={label}>Disease name *</label>
          <input className="dp-input" autoFocus value={form.name} onChange={(e) => set({ name: e.target.value })} />{err('name')}</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem' }}>
          <div><label style={label}>Category</label>
            <select className="dp-input" value={form.category} onChange={(e) => set({ category: e.target.value })}>
              {meta.categories.map((c) => <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>)}</select>{err('category')}</div>
          <div><label style={label}>Severity</label>
            <select className="dp-input" value={form.severity} onChange={(e) => set({ severity: e.target.value })}>
              {meta.severities.map((c) => <option key={c} value={c}>{c}</option>)}</select></div>
          <div><label style={label}>What the patient should do</label>
            <select className="dp-input" value={form.recommended_action} onChange={(e) => set({ recommended_action: e.target.value })}>
              {meta.actions.map((c) => <option key={c} value={c}>{c.replace(/-/g, ' ')}</option>)}</select></div>
        </div>
        <div><label style={label}>Symptoms * (at least 2)</label>
          <SymptomChipPicker
            value={form.symptoms}
            vocab={vocab}
            vocabMap={vocabMap}
            onChange={(symptoms) => set({ symptoms })}
            onAddNew={onAddNewSymptom ? (initialName) => onAddNewSymptom((newSym) => set({ symptoms: [...form.symptoms, newSym.name] }), initialName) : undefined}
          />{err('symptoms')}</div>
        <div><label style={label}>Description</label>
          <textarea className="feedback-textarea" value={form.description} onChange={(e) => set({ description: e.target.value })} /></div>
        <div><label style={label}>Next steps for the patient</label>
          <textarea className="feedback-textarea" value={form.next_steps} onChange={(e) => set({ next_steps: e.target.value })} /></div>
        <div><label style={label}>Remedies <small className="text-muted">(complementary suggestions, not medical treatment)</small></label>
          <RemedyEditor value={form.homeopathic_remedies} onChange={(homeopathic_remedies) => set({ homeopathic_remedies })} /></div>
        <div style={{ maxWidth: 200 }}><label style={label}>ICD-10 code</label>
          <input className="dp-input" value={form.icd10} onChange={(e) => set({ icd10: e.target.value })} /></div>
      </div>
    </Modal>
  );
}

