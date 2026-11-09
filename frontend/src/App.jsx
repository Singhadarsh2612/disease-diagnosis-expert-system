import { Routes, Route } from 'react-router-dom';
import Navbar from './components/common/Navbar.jsx';
import Footer from './components/common/Footer.jsx';
import DisclaimerBanner from './components/common/DisclaimerBanner.jsx';
import HomePage from './pages/HomePage.jsx';
import ChatPage from './pages/ChatPage.jsx';
import HistoryPage from './pages/HistoryPage.jsx';
import DoctorLoginPage from './pages/DoctorLoginPage.jsx';
import DoctorPortalPage from './pages/DoctorPortalPage.jsx';
import ProtectedRoute from './components/doctor/ProtectedRoute.jsx';

export default function App() {
  return (
    <div className="app-layout">
      <Navbar />
      <DisclaimerBanner />
      <main className="page-content">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/doctor/login" element={<DoctorLoginPage />} />
          <Route path="/doctor" element={<ProtectedRoute><DoctorPortalPage /></ProtectedRoute>} />
        </Routes>
      </main>
      <Footer />
    </div>
  );
}

