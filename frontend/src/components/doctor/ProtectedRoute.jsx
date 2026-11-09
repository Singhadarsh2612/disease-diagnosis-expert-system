import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { getDoctorToken, clearDoctorToken, doctorVerify } from '../../services/api.js';

/** Guards /doctor: needs a token in sessionStorage AND GET /api/doctor/verify must succeed. */
export default function ProtectedRoute({ children }) {
  const [status, setStatus] = useState(getDoctorToken() ? 'checking' : 'no');

  useEffect(() => {
    if (!getDoctorToken()) { setStatus('no'); return; }
    let cancelled = false;
    doctorVerify()
      .then(() => !cancelled && setStatus('yes'))
      .catch((e) => {
        if (cancelled) return;
        if (e.status === 401) { clearDoctorToken(); setStatus('no'); }
        else setStatus('error');
      });
    return () => { cancelled = true; };
  }, []);

  if (status === 'checking') {
    return <div className="empty-state"><div className="spinner spinner-dark" style={{ margin: '0 auto 1rem' }} />Checking your login…</div>;
  }
  if (status === 'error') {
    return (
      <div className="empty-state">
        <div className="empty-icon">⚠️</div>
        <h3>Cannot reach the server</h3>
        <p>Make sure the backend is running, then refresh this page.</p>
      </div>
    );
  }
  if (status === 'no') return <Navigate to="/doctor/login" replace />;
  return children;
}

