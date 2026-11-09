import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { doctorLogin, setDoctorToken } from '../services/api.js';

export default function DoctorLoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const expired = params.get('expired') === '1';

  async function submit(e) {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      const res = await doctorLogin(username.trim(), password);
      setDoctorToken(res.data.token);
      navigate('/doctor', { replace: true });
    } catch (err) {
      setError(err.status === 401 ? 'Wrong username or password.' : err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ maxWidth: 420, margin: '3rem auto', padding: '0 1rem' }}>
      <div className="card">
        <div className="card-header">🔐 Doctor Login</div>
        <form className="card-body" onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
          {expired && (
            <div className="emergency-banner" style={{ margin: 0 }}>
              <p>Session expired. Please log in again.</p>
            </div>
          )}
          <label style={{ fontWeight: 600, fontSize: '0.9rem' }}>
            Username
            <input className="chat-input" style={{ width: '100%', marginTop: 4 }} autoFocus autoComplete="username"
              value={username} onChange={(e) => setUsername(e.target.value)} required />
          </label>
          <label style={{ fontWeight: 600, fontSize: '0.9rem' }}>
            Password
            <input className="chat-input" style={{ width: '100%', marginTop: 4 }} type="password" autoComplete="current-password"
              value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
          {error && <p style={{ color: 'var(--emergency)', fontSize: '0.88rem' }}>{error}</p>}
          <button className="btn btn-primary btn-lg" type="submit" disabled={busy || !username || !password}>
            {busy ? 'Signing in…' : 'Login'}
          </button>
          <p className="text-muted">For authorised medical staff only.</p>
          <Link to="/" style={{ fontSize: '0.88rem', color: 'var(--primary-dark)' }}>← Back to patient site</Link>
        </form>
      </div>
    </div>
  );
}

