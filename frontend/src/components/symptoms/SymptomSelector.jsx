import { useState, useMemo } from 'react';

const fmt = (s) =>
  String(s ?? '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

// Accepts either a plain string or a {name, display_name} object
const getName = (s) => (typeof s === 'string' ? s : s?.name ?? '');
const getLabel = (s) =>
  typeof s === 'string' ? fmt(s) : s?.display_name ?? fmt(s?.name);

export default function SymptomSelector({ categories, selectedSymptoms, onToggle }) {
  const [activeCategory, setActiveCategory] = useState('All');
  const [search, setSearch] = useState('');

  const catNames = useMemo(() => ['All', ...Object.keys(categories || {})], [categories]);

  const visibleSymptoms = useMemo(() => {
    let syms = [];
    if (activeCategory === 'All') {
      syms = Object.values(categories || {}).flat();
    } else {
      syms = (categories || {})[activeCategory] || [];
    }
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      syms = syms.filter(
        (s) =>
          getName(s).toLowerCase().includes(q) ||
          getLabel(s).toLowerCase().includes(q)
      );
    }
    return syms;
  }, [categories, activeCategory, search]);

  return (
    <div className="card">
      <div className="card-header">🔍 Select Symptoms</div>
      {/* Search */}
      <div style={{ padding: '0.75rem 1rem 0' }}>
        <input
          className="symptom-search"
          placeholder="Search symptoms…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      {/* Category tabs */}
      <div className="category-tabs">
        {catNames.map((cat) => (
          <button
            key={cat}
            className={`category-tab${activeCategory === cat ? ' active' : ''}`}
            onClick={() => setActiveCategory(cat)}
          >
            {cat}
          </button>
        ))}
      </div>
      {/* Symptom grid */}
      <div className="symptom-grid">
        {visibleSymptoms.length === 0 && (
          <p style={{ gridColumn: '1/-1', fontSize: '0.85rem', color: 'var(--neutral-400)' }}>
            No symptoms found.
          </p>
        )}
        {visibleSymptoms.map((sym) => {
          const name = getName(sym);
          const selected = selectedSymptoms.includes(name);
          return (
            <button
              key={name}
              className={`symptom-item${selected ? ' selected' : ''}`}
              onClick={() => onToggle(name)}
            >
              {selected ? '✓ ' : ''}{getLabel(sym)}
            </button>
          );
        })}
      </div>
    </div>
  );
}