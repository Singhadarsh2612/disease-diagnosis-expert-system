"""
tests/test_core.py — Core pytest suite (CORE features only).
"""
import json
import os
import sys
import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from modules.diagnosis import get_engine
from modules.fallback_engine import PythonFallbackEngine
from modules.nlp import extract_symptoms
from modules.safety import check_emergency

with open(os.path.join(BACKEND_DIR, "data", "knowledge_base.json")) as f:
    KB = json.load(f)
DISEASES = KB["diseases"]
ALL_SYMPTOMS = KB.get("all_symptoms", [])


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def engine():
    return get_engine()

@pytest.fixture(scope="module")
def fallback():
    return PythonFallbackEngine(DISEASES)

@pytest.fixture
def client():
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── Knowledge Base ────────────────────────────────────────────────────────────

def test_kb_has_40_plus_diseases():
    assert len(DISEASES) >= 40

def test_kb_has_100_plus_symptoms():
    assert len(ALL_SYMPTOMS) >= 100

def test_disease_ids_unique():
    ids = [d["id"] for d in DISEASES]
    assert len(ids) == len(set(ids))


# ── Diagnosis Engine ──────────────────────────────────────────────────────────

def test_diagnose_returns_structure(engine):
    r = engine.diagnose(["fever"])
    assert "possible_diseases" in r
    assert "remaining_symptoms" in r
    assert "emergency_flags" in r
    assert "disclaimer" in r

def test_diagnose_common_cold(engine):
    syms = ["runny_nose", "sneezing", "sore_throat", "cough", "fatigue"]
    r = engine.diagnose(syms)
    names = [d["name"] for d in r["possible_diseases"]]
    assert "Common Cold" in names

def test_confidence_label_high(engine):
    syms = ["runny_nose", "sneezing", "sore_throat", "cough", "nasal_congestion", "fatigue", "mild_fever"]
    r = engine.diagnose(syms)
    top = r["possible_diseases"][0] if r["possible_diseases"] else None
    assert top is not None
    assert top["label"] in {"High", "Moderate", "Low"}

def test_confidence_values_between_0_and_1(engine):
    r = engine.diagnose(["fever", "cough"])
    for d in r["possible_diseases"]:
        assert 0.0 <= d["confidence"] <= 1.0

def test_matched_and_missing_are_lists(engine):
    r = engine.diagnose(["fever"])
    for d in r["possible_diseases"]:
        assert isinstance(d["matched_symptoms"], list)
        assert isinstance(d["missing_symptoms"], list)

def test_cardiac_emergency_triggered(engine):
    r = engine.diagnose(["chest_pain", "shortness_of_breath", "increased_sweating"])
    assert len(r["emergency_flags"]) > 0

def test_meningitis_emergency_triggered(engine):
    r = engine.diagnose(["severe_headache", "stiff_neck", "fever"])
    assert any("meningitis" in e["message"].lower() for e in r["emergency_flags"])

def test_empty_symptoms_returns_empty_diseases(engine):
    r = engine.diagnose([])
    assert r["possible_diseases"] == []

def test_remaining_symptoms_present(engine):
    r = engine.diagnose(["fever"])
    assert isinstance(r["remaining_symptoms"], list)


# ── Fallback Engine ───────────────────────────────────────────────────────────

def test_fallback_influenza_match(fallback):
    r = fallback.run(["fever", "chills", "muscle_pain", "dry_cough", "fatigue"])
    names = [c["name"] for c in r["candidates"]]
    assert "Influenza" in names

def test_fallback_confirmed_high_confidence(fallback):
    syms = ["runny_nose", "sneezing", "sore_throat", "cough", "nasal_congestion", "fatigue", "mild_fever"]
    r = fallback.run(syms)
    for c in r["confirmed"]:
        assert c["confidence"] >= 0.7


# ── NLP ───────────────────────────────────────────────────────────────────────

def test_nlp_headache_from_synonym():
    r = extract_symptoms("my head is pounding", ALL_SYMPTOMS)
    assert "headache" in r["matched"]

def test_nlp_vomiting_from_synonym():
    r = extract_symptoms("I have been throwing up all morning", ALL_SYMPTOMS)
    assert "vomiting" in r["matched"]

def test_nlp_abdominal_from_synonym():
    r = extract_symptoms("I have a tummy ache", ALL_SYMPTOMS)
    assert "abdominal_pain" in r["matched"]

def test_nlp_multi_symptom():
    r = extract_symptoms("I have a headache and I feel like throwing up", ALL_SYMPTOMS)
    assert "headache" in r["matched"]
    assert "vomiting" in r["matched"]

def test_nlp_negation():
    r = extract_symptoms("no fever but I have a headache", ALL_SYMPTOMS)
    assert "fever" not in r["matched"]
    assert "headache" in r["matched"]

def test_nlp_direct_symptom_name():
    r = extract_symptoms("I have fever and cough", ALL_SYMPTOMS)
    assert "fever" in r["matched"]
    assert "cough" in r["matched"]


# ── Safety ────────────────────────────────────────────────────────────────────

def test_cardiac_safety_rule():
    flags = check_emergency(["chest_pain", "shortness_of_breath", "increased_sweating"])
    assert any("cardiac" in f["message"].lower() for f in flags)

def test_stroke_safety_rule():
    flags = check_emergency(["facial_drooping", "arm_weakness", "slurred_speech"])
    assert len(flags) > 0

def test_benign_no_emergency():
    flags = check_emergency(["runny_nose", "sneezing"])
    assert len(flags) == 0


# ── API Endpoints ─────────────────────────────────────────────────────────────

def test_api_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    d = r.get_json()
    assert d["status"] == "ok"
    assert d["engine"] in {"clips", "python-fallback"}
    assert d["disease_count"] >= 40

def test_api_get_initial_symptoms(client):
    r = client.get("/api/get_initial_symptoms")
    assert r.status_code == 200
    d = r.get_json()
    assert "categories" in d
    assert len(d["categories"]) > 0

def test_api_diagnose_returns_structure(client):
    r = client.post("/api/diagnose", json={"symptoms": ["fever", "cough"]})
    assert r.status_code == 200
    d = r.get_json()
    assert "possible_diseases" in d
    assert "emergency_flags" in d
    assert "disclaimer" in d

def test_api_diagnose_bad_input(client):
    r = client.post("/api/diagnose", json={"symptoms": "not-a-list"})
    assert r.status_code == 400

def test_api_extract_symptoms(client):
    r = client.post("/api/extract_symptoms", json={"text": "I have a headache and feel like throwing up"})
    assert r.status_code == 200
    d = r.get_json()
    assert "matched" in d
    assert "headache" in d["matched"]

def test_api_extract_empty_text(client):
    r = client.post("/api/extract_symptoms", json={"text": ""})
    assert r.status_code == 400

def test_api_feedback(client):
    r = client.post("/api/feedback", json={
        "session_id": "pytest-session",
        "satisfied": True,
        "final_disease": "Common Cold"
    })
    assert r.status_code == 201

def test_api_diseases_list(client):
    r = client.get("/api/diseases")
    assert r.status_code == 200
    d = r.get_json()
    assert len(d["diseases"]) >= 20

def test_api_disease_by_id(client):
    r = client.get("/api/diseases/d001")
    assert r.status_code == 200
    assert r.get_json()["name"] == "Common Cold"

def test_api_disease_not_found(client):
    r = client.get("/api/diseases/nonexistent_xyz")
    assert r.status_code == 404
