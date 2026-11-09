import { useEffect, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { getDoctorToken, clearDoctorToken } from '../../services/api.js';

export default function Navbar() {
  const [loggedIn, setLoggedIn] = useState(!!getDoctorToken());
  const navigate = useNavigate();

  useEffect(() => {
    const sync = () => setLoggedIn(!!getDoctorToken());
    window.addEventListener('doctor-auth-changed', sync);
    return () => window.removeEventListener('doctor-auth-changed', sync);
  }, []);

  function logout() {
    clearDoctorToken();
    navigate('/doctor/login');
  }

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <NavLink to="/" className="navbar-brand">
          <div className="logo-icon">🩺</div>
          <span>DiagnosisAI</span>
        </NavLink>
        <div className="navbar-links">
          <NavLink to="/" end className={({ isActive }) => isActive ? 'active' : ''}>Home</NavLink>
          <NavLink to="/chat" className={({ isActive }) => isActive ? 'active' : ''}>Diagnose</NavLink>
          <NavLink to="/history" className={({ isActive }) => isActive ? 'active' : ''}>History</NavLink>
          {loggedIn ? (
            <>
              <NavLink to="/doctor" className={({ isActive }) => isActive ? 'active' : ''}>Doctor Portal</NavLink>
              <a href="#logout" onClick={(e) => { e.preventDefault(); logout(); }}>Logout</a>
            </>
          ) : (
            <NavLink to="/doctor/login" className={({ isActive }) => isActive ? 'active' : ''}>Doctor Login</NavLink>
          )}
        </div>
      </div>
    </nav>
  );
}
