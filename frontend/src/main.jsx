import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App.jsx';
import { DiagnosisProvider } from './context/DiagnosisContext.jsx';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <DiagnosisProvider>
        <App />
      </DiagnosisProvider>
    </BrowserRouter>
  </React.StrictMode>
);

