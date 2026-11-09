# AI Disease Diagnosis Expert System

An AI-powered expert system for preliminary disease diagnosis. Uses a CLIPS knowledge base (with a pure-Python fallback) in a Flask backend, and a React + Vite frontend.

> ⚠️ **Medical Disclaimer:** This tool is for educational/demonstration purposes only. It is NOT a substitute for professional medical advice.

---

## Quick Start

### 1 — Backend (Flask)

```bash
cd Heroku_backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Backend runs at **http://localhost:5001** (or 5000 if AirPlay Receiver is disabled)

### 2 — Frontend (React + Vite)

Open a **second terminal**:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:5173** — open this in your browser.

---

## Running Tests

```bash
cd Heroku_backend
source venv/bin/activate
pytest tests/ -v
```

All 124 tests should pass across `test_core.py`, `test_diagnosis.py`, and `test_doctor.py`.

---

## Doctor Portal

A medical staff portal for viewing and editing the disease knowledge base in an intuitive, spreadsheet-style table. Any saved changes atomically write `knowledge_base.json`, backup the prior version, rebuild `disease-symptoms.clp`, and dynamically reload the live CLIPS inference engine **without restarting the server**.

### Doctor Credentials (.env)

Configure staff credentials in `Heroku_backend/.env`:

```env
DOCTOR_USERNAME=doctor
DOCTOR_PASSWORD=change-me-123
SECRET_KEY=your-long-random-secret-key-here
```

### Accessing the Doctor Portal

1. Start both servers (see Quick Start above).
2. Open **http://localhost:5173** and click **Doctor Login** in the navigation bar (or visit **http://localhost:5173/doctor/login** directly).
3. Log in with the demo credentials:
   - **Username:** `doctor`
   - **Password:** `change-me-123`

### Demo Steps

1. **Browse & Filter:** Use the top search bar to filter by disease name or symptom, or filter by category dropdown.
2. **Inline Editing:** Click any cell to edit:
   - Text fields (Name, Description, Next steps, ICD-10): click to edit inline or open the multiline editor.
   - Category, Severity, Action: change via coloured dropdown badges.
   - Symptoms: remove chips or type in the autocomplete picker to add valid symptoms from the known vocabulary.
   - Remedies: add or remove complementary care suggestions.
3. **Add Disease:** Click `➕ Add disease` to open the modal, fill in required fields with at least 2 symptoms, and see the new row highlighted at the top.
4. **Duplicate or Delete:** Use row actions to clone an existing disease or remove one (with confirmation).
5. **Save Changes:** Notice the yellow unsaved changes banner. Click `💾 Save changes` and confirm. The backend validates all rows (checking for unique names, allowed values, known symptoms, and emergency rule safety), creates a versioned backup in `data/kb_versions/`, rebuilds `disease-symptoms.clp`, and reloads the CLIPS engine in-memory.
6. **Instant Verification:** Switch to the patient **Diagnose** page (`/chat`), enter symptoms of your newly added/edited disease, and confirm that the expert system diagnoses it immediately with zero downtime.
7. **Version History & Revert:** Click `🕘 Version history` to view timestamped backups and restore any prior version with one click.
8. **CSV Export / Import:** Click `⬇️ Download CSV` for a clean export, or `⬆️ Upload CSV` to bulk update diseases.

---

## API Endpoints

### Patient Endpoints (Public)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check, active engine, disease/symptom counts |
| GET | `/api/get_initial_symptoms` | All symptoms grouped by category |
| POST | `/api/diagnose` | `{"symptoms": [...]}` → ranked diseases, follow-ups |
| POST | `/api/extract_symptoms` | `{"text": "..."}` → matched canonical symptoms |
| POST | `/api/feedback` | Submit diagnosis feedback |
| GET | `/api/diseases` | List diseases (paginated) |
| GET | `/api/diseases/:id` | Single disease details |
| GET | `/api/upload_csv/template` | Download CSV template |

### Doctor Portal Endpoints (Protected with Bearer Token)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/doctor/login` | Log in with credentials (5 failed attempts/5 min rate limited) |
| GET | `/api/doctor/verify` | Verify token validity and session status |
| GET | `/api/doctor/knowledge` | Full disease table, dropdown choices, vocabulary |
| PUT | `/api/doctor/knowledge` | Validate and atomic save full disease catalog |
| GET | `/api/doctor/versions` | List the last 20 knowledge base backups |
| POST | `/api/doctor/knowledge/revert` | Revert to a specific backup version file |
| GET | `/api/doctor/export_csv` | Export knowledge base as clean CSV |
| POST | `/api/upload_csv` | Bulk import / merge CSV into knowledge base |
| POST/PUT/DEL | `/api/knowledge/*` | Granular disease/symptom manipulation |

---

## Knowledge Base

- **45 diseases** across 10+ categories
- **172 symptoms** in 8 categories
- CLIPS rules with emergency/safety triggers
- Pure-Python fallback engine (no `clipspy` required)

---

## Project Structure

```
disease-diagnosis-expert-system/
├── Heroku_backend/
│   ├── app.py                  # Flask app entry point
│   ├── modules/
│   │   ├── routes.py           # API endpoints
│   │   ├── diagnosis.py        # Engine orchestration
│   │   ├── fallback_engine.py  # Pure-Python CLIPS fallback
│   │   ├── clips_engine.py     # CLIPS integration (optional)
│   │   ├── nlp.py              # Free-text symptom extraction
│   │   ├── safety.py           # Emergency condition rules
│   │   ├── csv_processor.py    # CSV import/export
│   │   └── models.py           # Data models
│   ├── data/
│   │   ├── knowledge_base.json # 45 diseases + 172 symptoms
│   │   ├── disease-symptoms.clp # Generated CLIPS rules
│   │   └── synonyms.json       # Symptom synonyms for NLP
│   └── tests/
│       └── test_core.py        # 33 pytest tests
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── main.jsx
    │   ├── pages/
    │   │   ├── HomePage.jsx
    │   │   ├── ChatPage.jsx    # Main diagnosis UI
    │   │   └── HistoryPage.jsx
    │   ├── components/
    │   │   ├── common/         # Navbar, Footer, DisclaimerBanner
    │   │   ├── symptoms/       # SymptomSelector, SelectedSymptomsBar
    │   │   └── diagnosis/      # DiseaseCard, FinalDiagnosisCard, DiagnosisFeedback
    │   ├── context/DiagnosisContext.jsx
    │   └── services/api.js
    └── index.html
```

