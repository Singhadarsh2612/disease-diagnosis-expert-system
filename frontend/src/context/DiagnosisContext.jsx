import { createContext, useContext, useReducer, useEffect, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';

const DiagnosisContext = createContext(null);

const INITIAL = {
  sessionId: uuidv4(),
  selectedSymptoms: [],
  deniedSymptoms: [],
  possibleDiseases: [],
  remainingSymptoms: [],
  emergencyFlags: [],
  finalDiagnosis: null,
  messages: [],
  loading: false,
  error: null,
  stage: 'idle', // idle | selecting | diagnosing | done
};

const HISTORY_KEY = 'diagnosis_history';
const ACTIVE_SESSION_KEY = 'diagnosis_active_session';

function getInitialState() {
  try {
    const saved = localStorage.getItem(ACTIVE_SESSION_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      return {
        ...INITIAL,
        ...parsed,
        deniedSymptoms: Array.isArray(parsed.deniedSymptoms) ? parsed.deniedSymptoms : [],
        loading: false,
        error: null,
      };
    }
  } catch (e) {
    console.error('Failed to load active session from localStorage', e);
  }
  return { ...INITIAL, sessionId: uuidv4() };
}

function reducer(state, action) {
  switch (action.type) {
    case 'ADD_SYMPTOM': {
      if (state.selectedSymptoms.includes(action.payload)) return state;
      return {
        ...state,
        selectedSymptoms: [...state.selectedSymptoms, action.payload],
        deniedSymptoms: state.deniedSymptoms.filter((s) => s !== action.payload),
      };
    }
    case 'REMOVE_SYMPTOM':
      return { ...state, selectedSymptoms: state.selectedSymptoms.filter((s) => s !== action.payload) };
    case 'ADD_DENIED_SYMPTOM': {
      if (state.deniedSymptoms.includes(action.payload) || state.selectedSymptoms.includes(action.payload)) return state;
      return { ...state, deniedSymptoms: [...state.deniedSymptoms, action.payload] };
    }
    case 'REMOVE_DENIED_SYMPTOM':
      return { ...state, deniedSymptoms: state.deniedSymptoms.filter((s) => s !== action.payload) };
    case 'SET_DENIED_SYMPTOMS':
      return { ...state, deniedSymptoms: Array.isArray(action.payload) ? action.payload : [] };
    case 'SET_DIAGNOSIS_RESULT':
      return {
        ...state,
        possibleDiseases: action.payload.possible_diseases || [],
        remainingSymptoms: action.payload.remaining_symptoms || [],
        emergencyFlags: action.payload.emergency_flags || [],
        finalDiagnosis: action.payload.final_diagnosis || null,
        loading: false,
        error: null,
        stage: action.payload.final_diagnosis ? 'done' : 'diagnosing',
      };
    case 'SET_FINAL_DIAGNOSIS':
      return { ...state, finalDiagnosis: action.payload, stage: 'done' };
    case 'ADD_MESSAGE':
      return { ...state, messages: [...state.messages, action.payload] };
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload, loading: false };
    case 'RESET':
      try {
        localStorage.removeItem(ACTIVE_SESSION_KEY);
      } catch (e) {}
      return { ...INITIAL, sessionId: uuidv4() };
    default:
      return state;
  }
}

export function DiagnosisProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, null, getInitialState);

  // Persist active session state
  useEffect(() => {
    try {
      const toSave = {
        sessionId: state.sessionId,
        selectedSymptoms: state.selectedSymptoms,
        deniedSymptoms: state.deniedSymptoms,
        possibleDiseases: state.possibleDiseases,
        remainingSymptoms: state.remainingSymptoms,
        emergencyFlags: state.emergencyFlags,
        finalDiagnosis: state.finalDiagnosis,
        stage: state.stage,
      };
      localStorage.setItem(ACTIVE_SESSION_KEY, JSON.stringify(toSave));
    } catch (e) {
      console.error('Failed to save active session', e);
    }
  }, [
    state.sessionId,
    state.selectedSymptoms,
    state.deniedSymptoms,
    state.possibleDiseases,
    state.remainingSymptoms,
    state.emergencyFlags,
    state.finalDiagnosis,
    state.stage,
  ]);

  // Auto-save completed sessions to history
  useEffect(() => {
    if (state.stage === 'done' && state.finalDiagnosis) {
      const history = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
      const entry = {
        id: state.sessionId,
        timestamp: new Date().toISOString(),
        symptoms: state.selectedSymptoms,
        deniedSymptoms: state.deniedSymptoms,
        diagnosis: state.finalDiagnosis,
        emergencyFlags: state.emergencyFlags,
      };
      history.unshift(entry);
      localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 50)));
    }
  }, [state.stage]);

  return (
    <DiagnosisContext.Provider value={{ state, dispatch }}>
      {children}
    </DiagnosisContext.Provider>
  );
}

export function useDiagnosis() {
  const ctx = useContext(DiagnosisContext);
  if (!ctx) throw new Error('useDiagnosis must be used within DiagnosisProvider');
  return ctx;
}

export { HISTORY_KEY };
