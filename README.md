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

## Deploy to Render

The repository includes a ready-to-use [`render.yaml`](render.yaml) Blueprint configuration for 1-click deployment on [Render](https://render.com).

### Option A — 1-Click Render Blueprint (Recommended)

1. Log in to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** at the top right and select **Blueprint**.
3. Connect your GitHub repository: `Singhadarsh2612/disease-diagnosis-expert-system`.
4. Render will parse `render.yaml` and configure two services automatically:
   - **`disease-diagnosis-backend`** (Python Web Service running Flask + Gunicorn on Python 3.11 — also serves `frontend/dist` directly as a unified full-stack app).
   - **`disease-diagnosis-frontend`** (Static Site serving the compiled Vite React SPA — 100% free and unlimited on Render CDN).
5. Click **Apply**.
6. Render builds both services and automatically wires `VITE_API_BASE_URL` (`property: url`) from the backend to the frontend.
7. Once deployment finishes (usually 3–5 minutes for the backend Python/ONNX wheels), open the live app URL!

> **Note:** In production builds (`frontend/.env.production`), `VITE_API_BASE_URL` defaults to `/api` (relative path), while local development (`frontend/.env.development`) points to `http://localhost:5001/api`.

### Option B — Manual Deployment

If you prefer to configure services manually in Render:

#### 1. Backend (Web Service)
- **Service Type:** Web Service
- **Root Directory:** `Heroku_backend`
- **Runtime:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app --workers=2 --timeout=120 --bind=0.0.0.0:$PORT`
- **Plan:** Free
- **Environment Variables:**
  - `PYTHON_VERSION`: `3.11.9`
  - `CORS_ORIGINS`: `*`
  - `DOCTOR_USERNAME`: `doctor`
  - `DOCTOR_PASSWORD`: `<choose_a_password>`
  - `SECRET_KEY`: `<generate_random_key>`

#### 2. Frontend (Static Site)
- **Service Type:** Static Site
- **Root Directory:** `frontend`
- **Build Command:** `npm install && npm run build`
- **Publish Directory:** `dist`
- **Redirects/Rewrites:**
  - Route: `/*`
  - Destination: `/index.html`
  - Action: `Rewrite`
- **Environment Variables:**
  - `VITE_API_BASE_URL`: `https://<your-backend-service-name>.onrender.com`

---

## Running Tests

```bash
cd Heroku_backend
source venv/bin/activate
pytest tests/ -v
```

All 143 tests should pass across `test_core.py`, `test_diagnosis.py`, and `test_doctor.py`.

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
9. **Symptom Vocabulary Management:** Use `+ Add new symptom...` inside any symptom chip picker (with duplicate/similarity detection and automatic synonym registration), or open **Manage symptoms** to inspect symptom usage and delete unused symptoms.

---

## Semantic Symptom Extraction

The expert system features local semantic symptom extraction for free-text patient descriptions:
- **Embedding Model:** `fastembed` (ONNX runtime) with model `BAAI/bge-small-en-v1.5` (384-dimensional dense vectors).
- **Local & Offline:** Downloaded model files and precomputed vector indexes are stored under `Heroku_backend/models/`. After initial download, it operates entirely offline without external API calls.
- **Similarity Thresholds:**
  - **Semantic (Fastembed):** Matches $\ge 0.75$, Suggestions $0.55 \le \text{score} < 0.75$, Unrecognized $< 0.55$.
  - **TF-IDF Fallback:** Matches $\ge 0.60$, Suggestions $0.40 \le \text{score} < 0.60$, Unrecognized $< 0.40$.
- **Automatic Index Invalidation:** Cache timestamps are checked against `knowledge_base.json` and `synonyms.json`; any knowledge update automatically rebuilds the vector index.
- **Resilience:** If model files are missing or fastembed fails to load, the system logs a warning, falls back to dictionary-only extraction, and reports `"nlp": "dictionary"` in `/api/health` without crashing.

---

## API Endpoints

### Patient Endpoints (Public)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check, active engine, NLP mode, disease/symptom counts |
| GET | `/api/get_initial_symptoms` | All symptoms grouped by category |
| POST | `/api/diagnose` | `{"symptoms": [...], "denied_symptoms": [...]}` → ranked diseases, follow-ups |
| POST | `/api/extract_symptoms` | `{"text": "..."}` → matched canonical symptoms, suggestions, method |
| POST | `/api/feedback` | Submit diagnosis feedback (includes `denied_symptoms`) |
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
| GET | `/api/doctor/knowledge/version` | Current knowledge base version metadata |
| GET | `/api/doctor/changelog` | Knowledge base edit and symptom change log |
| GET | `/api/doctor/versions` | List the last 20 knowledge base backups |
| POST | `/api/doctor/knowledge/revert` | Revert to a specific backup version file |
| GET | `/api/doctor/export_csv` | Export knowledge base as clean CSV |
| POST | `/api/doctor/symptoms` | Add a new symptom with duplicate checking & synonym mapping |
| DELETE | `/api/doctor/symptoms/:name` | Delete an unused symptom (refuses if used by disease/emergency rule) |
| POST | `/api/upload_csv` | Bulk import / merge CSV into knowledge base |

---

## Knowledge Base

- **46 diseases** across 10+ categories
- **172 symptoms** in 10 categories
- CLIPS rules with emergency/safety triggers
- Pure-Python fallback engine (no `clipspy` required)

---

## Project Structure

```
disease-diagnosis-expert-system/
├── render.yaml                     # Render Blueprint (Web Service + Static Site)
├── Heroku_backend/
│   ├── app.py                      # Flask app entry point (also serves frontend/dist)
│   ├── generate_clp.py             # Generates CLIPS rules from knowledge_base.json
│   ├── modules/
│   │   ├── routes.py               # Public patient API endpoints
│   │   ├── doctor.py               # Doctor portal API endpoints
│   │   ├── doctor_auth.py          # Token authentication & rate limiting
│   │   ├── diagnosis.py            # Engine orchestration & denied-symptom penalties
│   │   ├── fallback_engine.py      # Pure-Python CLIPS fallback
│   │   ├── clips_engine.py         # CLIPS integration (optional)
│   │   ├── nlp.py                  # Dictionary & n-gram symptom extraction
│   │   ├── semantic_nlp.py         # Fastembed semantic symptom extraction & caching
│   │   ├── safety.py               # Emergency condition rules
│   │   ├── csv_processor.py        # CSV import/export
│   │   └── models.py               # Data models
│   ├── data/
│   │   ├── knowledge_base.json     # Diseases, categories, and symptom vocabulary
│   │   ├── disease-symptoms.clp    # Generated CLIPS rules
│   │   └── synonyms.json           # Symptom synonyms for NLP
│   ├── models/                     # Cached fastembed ONNX model & vector index
│   └── tests/
│       ├── test_core.py            # Core endpoints & safety tests
│       ├── test_diagnosis.py       # Diagnosis, denied symptoms & semantic NLP tests
│       └── test_doctor.py          # Doctor portal & symptom management tests
└── frontend/
    ├── .env.development            # Points to http://localhost:5001/api for local dev
    ├── .env.production             # Uses relative /api for production builds
    ├── src/
    │   ├── App.jsx
    │   ├── main.jsx
    │   ├── pages/
    │   │   ├── HomePage.jsx
    │   │   ├── ChatPage.jsx        # Main diagnosis UI (selector, NLP, follow-ups)
    │   │   ├── HistoryPage.jsx
    │   │   ├── DoctorLoginPage.jsx
    │   │   └── DoctorPortalPage.jsx
    │   ├── components/
    │   │   ├── common/             # Navbar, Footer, DisclaimerBanner
    │   │   ├── symptoms/           # SymptomSelector, SelectedSymptomsBar
    │   │   ├── diagnosis/          # DiseaseCard, FinalDiagnosisCard, DiagnosisFeedback
    │   │   └── doctor/             # Knowledge table, Symptom/CSV/History modals
    │   ├── context/DiagnosisContext.jsx
    │   └── services/api.js
    └── index.html
```

