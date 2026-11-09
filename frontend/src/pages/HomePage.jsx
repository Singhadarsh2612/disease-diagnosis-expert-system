import { Link } from 'react-router-dom';

const STEPS = [
  { icon: '🔍', title: 'Describe Symptoms', desc: 'Select from categories, search by name, or type in plain language.' },
  { icon: '🧠', title: 'AI Analysis', desc: 'Expert system rules match symptoms to 40+ diseases with confidence scores.' },
  { icon: '📋', title: 'Ranked Results', desc: 'See ranked possible conditions, follow-up questions, and recommended actions.' },
  { icon: '🏥', title: 'Next Steps', desc: 'Get guidance on when to self-care, see a doctor, or seek emergency help.' },
];

const FEATURES = [
  '45+ diseases in knowledge base',
  '170+ symptoms tracked',
  'Emergency condition alerts',
  'Free-text symptom input',
  'Diagnosis history saved locally',
  'Homeopathic remedy suggestions',
];

export default function HomePage() {
  return (
    <>
      {/* Hero */}
      <section className="hero">
        <div className="hero-inner">
          <h1>
            AI-Powered <span>Disease Diagnosis</span> Expert System
          </h1>
          <p>
            Describe your symptoms and let our expert system — powered by a CLIPS knowledge base — help
            you understand possible conditions and what to do next.
          </p>
          <div className="hero-badges">
            {FEATURES.map((f) => (
              <span key={f} className="hero-badge">{f}</span>
            ))}
          </div>
          <Link to="/chat" className="btn btn-primary btn-lg">
            Start Diagnosis →
          </Link>
        </div>
      </section>

      {/* How it works */}
      <section className="how-it-works">
        <h2>How It Works</h2>
        <p className="subtitle">Four simple steps to preliminary diagnosis</p>
        <div className="steps">
          {STEPS.map((s, i) => (
            <div key={i} className="step-card">
              <div className="step-icon">{s.icon}</div>
              <h3>{s.title}</h3>
              <p>{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <div style={{ textAlign: 'center', padding: '2rem 1.5rem 4rem' }}>
        <Link to="/chat" className="btn btn-primary btn-lg">
          Try It Now — Free &amp; Private
        </Link>
        <p style={{ marginTop: '0.75rem', color: 'var(--neutral-500)', fontSize: '0.85rem' }}>
          No account needed · Data stays in your browser
        </p>
      </div>
    </>
  );
}

