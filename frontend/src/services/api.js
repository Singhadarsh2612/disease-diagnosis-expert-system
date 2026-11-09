import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Doctor Portal token (sessionStorage) ─────────────────────────────────────
const TOKEN_KEY = 'doctor_token';
export const getDoctorToken = () => sessionStorage.getItem(TOKEN_KEY);
export const setDoctorToken = (t) => {
  sessionStorage.setItem(TOKEN_KEY, t);
  window.dispatchEvent(new Event('doctor-auth-changed'));
};
export const clearDoctorToken = () => {
  sessionStorage.removeItem(TOKEN_KEY);
  window.dispatchEvent(new Event('doctor-auth-changed'));
};

const isProtectedUrl = (url = '') =>
  (url.startsWith('/doctor') && url !== '/doctor/login') ||
  url.startsWith('/knowledge') ||
  (url.startsWith('/upload_csv') && !url.startsWith('/upload_csv/template'));

api.interceptors.request.use((config) => {
  const token = getDoctorToken();
  if (token && isProtectedUrl(config.url)) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err?.response?.status;
    if (status === 401 && isProtectedUrl(err?.config?.url)) {
      clearDoctorToken();
      if (!window.location.pathname.startsWith('/doctor/login')) {
        window.location.assign('/doctor/login?expired=1');
      }
    }
    const message =
      err?.response?.data?.error?.message ||
      err?.message ||
      'Network error – is the backend running?';
    const e = new Error(message);
    e.status = status;
    e.data = err?.response?.data;
    return Promise.reject(e);
  }
);

export const healthCheck = () => api.get('/health');
export const getInitialSymptoms = () => api.get('/get_initial_symptoms');
export const diagnose = (symptoms, denied_symptoms = []) => api.post('/diagnose', { symptoms, denied_symptoms });
export const extractSymptoms = (text) => api.post('/extract_symptoms', { text });
export const submitFeedback = (data) => api.post('/feedback', data);
export const getDiseases = (params) => api.get('/diseases', { params });
export const uploadCSV = (formData) =>
  api.post('/upload_csv', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
export const getCSVTemplate = () =>
  `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api'}/upload_csv/template`;

// ── Doctor Portal calls ──────────────────────────────────────────────────────
export const doctorLogin = (username, password) => api.post('/doctor/login', { username, password });
export const doctorVerify = () => api.get('/doctor/verify');
export const getDoctorKnowledge = () => api.get('/doctor/knowledge');
export const getDoctorKnowledgeVersion = () => api.get('/doctor/knowledge/version');
export const getDoctorChangelog = (limit) => api.get('/doctor/changelog', { params: limit ? { limit } : {} });
export const saveDoctorKnowledge = (diseases, edited_by, base_version) =>
  api.put('/doctor/knowledge', { diseases, edited_by, base_version }, { timeout: 30000 });
export const getDoctorVersions = () => api.get('/doctor/versions');
export const revertDoctorVersion = (version, edited_by) =>
  api.post('/doctor/knowledge/revert', { version, edited_by }, { timeout: 30000 });
export const addDoctorSymptom = (data) => api.post('/doctor/symptoms', data);
export const deleteDoctorSymptom = (name, edited_by) =>
  api.delete(`/doctor/symptoms/${encodeURIComponent(name)}`, { data: { edited_by } });
export const downloadDoctorCSV = () => api.get('/doctor/export_csv', { responseType: 'blob' });
export const downloadCSVTemplate = () => api.get('/upload_csv/template', { responseType: 'blob' });

export default api;
