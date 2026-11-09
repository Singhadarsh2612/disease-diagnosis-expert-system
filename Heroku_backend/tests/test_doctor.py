"""
tests/test_doctor.py — Doctor Portal: auth, protection, validation, save/revert, CSV export.
All knowledge-base writes go to a temporary copy; the real data/ folder is never touched.
"""
import json
import os
import shutil
import sys

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from modules import diagnosis, doctor_auth, nlp  # noqa: E402
from modules.csv_processor import diseases_to_csv, parse_csv  # noqa: E402

CREDS = {"username": "doctor", "password": "change-me-123"}


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Fresh DiagnosisEngine working on a temp copy of the knowledge base."""
    data = tmp_path / "data"
    (data / "kb_versions").mkdir(parents=True)
    kb_path = data / "knowledge_base.json"
    shutil.copy(os.path.join(BACKEND_DIR, "data", "knowledge_base.json"), kb_path)
    syn_path = data / "synonyms.json"
    if os.path.exists(os.path.join(BACKEND_DIR, "data", "synonyms.json")):
        shutil.copy(os.path.join(BACKEND_DIR, "data", "synonyms.json"), syn_path)
    monkeypatch.setattr(diagnosis, "KB_PATH", str(kb_path))
    monkeypatch.setattr(diagnosis, "CLP_PATH", str(data / "disease-symptoms.clp"))
    monkeypatch.setattr(diagnosis, "KB_VERSIONS_DIR", str(data / "kb_versions"))
    monkeypatch.setattr(diagnosis, "CHANGE_LOG_PATH", str(data / "change_log.json"))
    monkeypatch.setattr(diagnosis, "SYNONYMS_PATH", str(syn_path))
    monkeypatch.setattr(nlp, "SYNONYMS_PATH", str(syn_path))
    nlp.reload_synonyms()
    import generate_clp
    generate_clp.generate_clp(str(kb_path), str(data / "disease-symptoms.clp"))
    monkeypatch.setenv("DOCTOR_USERNAME", "doctor")
    monkeypatch.setenv("DOCTOR_PASSWORD", "change-me-123")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setattr(diagnosis, "_engine_instance", diagnosis.DiagnosisEngine())
    doctor_auth.reset_rate_limits()
    yield data
    doctor_auth.reset_rate_limits()


@pytest.fixture
def client(sandbox):
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    # create_app() ran get_engine() -> uses the sandbox singleton set above
    with app.test_client() as c:
        yield c


@pytest.fixture
def auth(client):
    r = client.post("/api/doctor/login", json=CREDS)
    assert r.status_code == 200
    return {"Authorization": "Bearer " + r.get_json()["token"]}


def _table(client, auth):
    return client.get("/api/doctor/knowledge", headers=auth).get_json()


def _save(client, auth, diseases, edited_by="Dr Test", base_version=None):
    if base_version is None:
        base_version = _table(client, auth)["version"]
    return client.put("/api/doctor/knowledge",
                      json={"diseases": diseases, "edited_by": edited_by, "base_version": base_version},
                      headers=auth)


def _new_disease(**over):
    d = {"name": "Test Fever Syndrome", "category": "Respiratory", "severity": "mild",
         "symptoms": ["fever", "cough"], "description": "Test", "recommended_action": "self-care",
         "next_steps": "Rest", "homeopathic_remedies": ["Rest"], "icd10": "X00"}
    d.update(over)
    return d


# ── Login ─────────────────────────────────────────────────────────────────────

def test_login_success_returns_token(client):
    r = client.post("/api/doctor/login", json=CREDS)
    assert r.status_code == 200 and r.get_json()["token"]


def test_login_wrong_password_is_generic_401(client):
    r = client.post("/api/doctor/login", json={"username": "doctor", "password": "nope"})
    r2 = client.post("/api/doctor/login", json={"username": "nobody", "password": "nope"})
    assert r.status_code == r2.status_code == 401
    assert r.get_json() == r2.get_json()          # same message for both


def test_login_rate_limited_after_5_failures(client):
    for _ in range(5):
        assert client.post("/api/doctor/login", json={"username": "x", "password": "y"}).status_code == 401
    assert client.post("/api/doctor/login", json={"username": "x", "password": "y"}).status_code == 429
    # even the right password is blocked while limited
    assert client.post("/api/doctor/login", json=CREDS).status_code == 429


def test_verify_valid_missing_bad_and_expired(client, auth, monkeypatch):
    assert client.get("/api/doctor/verify", headers=auth).status_code == 200
    assert client.get("/api/doctor/verify").status_code == 401
    assert client.get("/api/doctor/verify", headers={"Authorization": "Bearer junk"}).status_code == 401
    monkeypatch.setattr(doctor_auth, "TOKEN_MAX_AGE", -1)
    assert client.get("/api/doctor/verify", headers=auth).status_code == 401


# ── Protection ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("method,url", [
    ("get", "/api/doctor/knowledge"), ("put", "/api/doctor/knowledge"),
    ("get", "/api/doctor/versions"), ("post", "/api/doctor/knowledge/revert"),
    ("get", "/api/doctor/export_csv"), ("post", "/api/doctor/symptoms"),
    ("delete", "/api/doctor/symptoms/fever"),
    ("post", "/api/knowledge/disease"), ("put", "/api/knowledge/disease/d001"),
    ("delete", "/api/knowledge/disease/d001"), ("post", "/api/knowledge/symptom"),
    ("delete", "/api/knowledge/symptom/fever"), ("post", "/api/upload_csv"),
])
def test_modifying_endpoints_require_token(client, method, url):
    assert getattr(client, method)(url, json={}).status_code == 401


def test_patient_endpoints_stay_public(client):
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/get_initial_symptoms").status_code == 200
    assert client.post("/api/diagnose", json={"symptoms": ["fever"]}).status_code == 200
    assert client.post("/api/extract_symptoms", json={"text": "fever"}).status_code == 200


# ── Table data + validation ───────────────────────────────────────────────────

def test_get_knowledge_has_dropdown_values(client, auth):
    d = _table(client, auth)
    assert len(d["diseases"]) >= 40 and d["version"]
    assert d["severities"] == ["mild", "moderate", "severe"]
    assert set(d["actions"]) == {"self-care", "consult-doctor", "emergency"}
    assert "Respiratory" in d["categories"]
    assert all({"name", "display_name", "category"} <= set(s) for s in d["symptoms"])
    assert "increased_sweating" in {s["name"] for s in d["symptoms"]}


def test_validation_collects_all_errors(client, auth):
    rows = _table(client, auth)["diseases"]
    rows.append(_new_disease(name="Bad One", category="Nope", severity="huge", symptoms=["sweating"]))
    rows.append(_new_disease(name="common cold"))                      # duplicate (case-insensitive)
    r = _save(client, auth, rows)
    assert r.status_code == 400
    errs = r.get_json()["errors"]
    fields = {(e["row"], e["field"]) for e in errs}
    n = len(rows)
    assert (n - 1, "category") in fields and (n - 1, "severity") in fields
    assert (n - 1, "symptoms") in fields and (n, "name") in fields
    sweat = next(e for e in errs if e["row"] == n - 1 and e["field"] == "symptoms" and "known symptom" in e["message"])
    assert "increased_sweating" in sweat["message"]            # closest-match suggestion


def test_validation_needs_two_symptoms(client, auth):
    rows = _table(client, auth)["diseases"] + [_new_disease(symptoms=["fever"])]
    r = _save(client, auth, rows)
    assert r.status_code == 400
    assert any("at least 2" in e["message"] for e in r.get_json()["errors"])


def test_emergency_symptom_removal_is_blocked(client, auth):
    rows = _table(client, auth)["diseases"]
    for d in rows:
        d["symptoms"] = [s for s in d["symptoms"] if s != "rebound_tenderness"]
    r = _save(client, auth, rows)
    assert r.status_code == 400
    msgs = " ".join(e["message"] for e in r.get_json()["errors"])
    assert "appendicitis-emergency" in msgs


# ── Version conflict & edited_by ─────────────────────────────────────────────

def test_missing_or_blank_or_long_edited_by_is_400(client, auth):
    rows = _table(client, auth)["diseases"]
    v = _table(client, auth)["version"]
    # missing
    assert client.put("/api/doctor/knowledge", json={"diseases": rows, "base_version": v}, headers=auth).status_code == 400
    # blank
    assert client.put("/api/doctor/knowledge", json={"diseases": rows, "base_version": v, "edited_by": "   "}, headers=auth).status_code == 400
    # >60 chars
    assert client.put("/api/doctor/knowledge", json={"diseases": rows, "base_version": v, "edited_by": "A" * 61}, headers=auth).status_code == 400


def test_version_conflict_returns_409(client, auth):
    rows = _table(client, auth)["diseases"]
    r = client.put("/api/doctor/knowledge",
                   json={"diseases": rows, "edited_by": "Dr Someone", "base_version": "0.0.0"},
                   headers=auth)
    assert r.status_code == 409
    body = r.get_json()
    assert body["error"] == "conflict"
    assert "current_version" in body and "last_edited_by" in body and "last_saved_at" in body


def test_knowledge_version_endpoint(client, auth):
    r = client.get("/api/doctor/knowledge/version", headers=auth)
    assert r.status_code == 200
    d = r.get_json()
    assert "version" in d and "last_edited_by" in d and "last_saved_at" in d


# ── Save / diagnose / backup / revert ─────────────────────────────────────────

def test_save_creates_backup_rebuilds_clp_and_engine_sees_it(client, auth, sandbox):
    rows = _table(client, auth)["diseases"]
    before_version = _table(client, auth)["version"]
    rows.insert(0, _new_disease(name="Zorblax Syndrome", symptoms=["fever", "bad_breath"]))
    r = _save(client, auth, rows, edited_by="Dr Test")
    assert r.status_code == 200, r.get_json()
    out = r.get_json()
    assert out["status"] == "ok" and out["disease_count"] == len(rows) and out["version"] != before_version
    assert len(list((sandbox / "kb_versions").glob("knowledge_base_*.json"))) == 1
    assert "Zorblax Syndrome" in (sandbox / "disease-symptoms.clp").read_text()
    saved = json.loads((sandbox / "knowledge_base.json").read_text())
    assert saved["_meta"]["last_edited_by"] == "Dr Test"
    zid = next(d["id"] for d in saved["diseases"] if d["name"] == "Zorblax Syndrome")
    assert zid.startswith("d") and zid not in {d["id"] for d in saved["diseases"] if d["name"] != "Zorblax Syndrome"}
    # check disease-level metadata
    z_disease = next(d for d in saved["diseases"] if d["id"] == zid)
    assert z_disease["last_edited_by"] == "Dr Test" and z_disease.get("last_edited_at")
    # no restart: the live engine already diagnoses with the new disease
    diag = client.post("/api/diagnose", json={"symptoms": ["fever", "bad_breath"]}).get_json()
    assert "Zorblax Syndrome" in [x["name"] for x in diag["possible_diseases"]]
    assert client.get("/api/health").get_json()["disease_count"] == len(rows)


def test_changelog_records_diffs_and_revert(client, auth, sandbox):
    rows = _table(client, auth)["diseases"]
    # Edit the first disease's description and add a symptom
    d0 = dict(rows[0])
    d0["description"] = "Updated test description"
    d0["symptoms"] = list(d0["symptoms"]) + ["chills"] if "chills" not in d0["symptoms"] else d0["symptoms"]
    rows[0] = d0
    # Add a new disease
    rows.append(_new_disease(name="Diff Test Disease", symptoms=["fever", "cough"]))
    # Delete the last existing disease
    del rows[1]

    r = _save(client, auth, rows, edited_by="Dr Diff")
    assert r.status_code == 200

    # Changelog verification
    cl_resp = client.get("/api/doctor/changelog", headers=auth)
    assert cl_resp.status_code == 200
    changelog = cl_resp.get_json()["changelog"]
    assert len(changelog) >= 1
    latest = changelog[0]
    assert latest["edited_by"] == "Dr Diff"
    types = {c["type"] for c in latest["changes"]}
    assert "added" in types and "edited" in types and "deleted" in types

    # Revert verification
    versions = client.get("/api/doctor/versions", headers=auth).get_json()["versions"]
    assert len(versions) >= 1
    rev_resp = client.post("/api/doctor/knowledge/revert",
                           json={"version": versions[0]["filename"], "edited_by": "Dr Revert"},
                           headers=auth)
    assert rev_resp.status_code == 200

    cl_resp2 = client.get("/api/doctor/changelog", headers=auth)
    latest2 = cl_resp2.get_json()["changelog"][0]
    assert latest2["edited_by"] == "Dr Revert"
    assert latest2["changes"][0]["type"] == "reverted"


def test_failed_rebuild_restores_backup(client, auth, sandbox, monkeypatch):
    import generate_clp
    original = (sandbox / "knowledge_base.json").read_text()
    rows = _table(client, auth)["diseases"] + [_new_disease(name="Will Not Save")]
    real = generate_clp.generate_clp
    calls = {"n": 0}

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        return real(*a, **k)

    monkeypatch.setattr(generate_clp, "generate_clp", flaky)
    r = _save(client, auth, rows)
    assert r.status_code == 500
    assert json.loads((sandbox / "knowledge_base.json").read_text()) == json.loads(original)
    diag = client.post("/api/diagnose", json={"symptoms": ["fever", "cough"]})
    assert diag.status_code == 200
    assert "Will Not Save" not in (sandbox / "disease-symptoms.clp").read_text()


def test_versions_and_revert(client, auth, sandbox):
    rows = _table(client, auth)["diseases"]
    rows.append(_new_disease(name="Temporary Disease", symptoms=["fever", "bad_breath"]))
    assert _save(client, auth, rows, edited_by="A").status_code == 200
    versions = client.get("/api/doctor/versions", headers=auth).get_json()["versions"]
    assert len(versions) == 1 and versions[0]["filename"].endswith(".json")
    r = client.post("/api/doctor/knowledge/revert", json={"version": versions[0]["filename"]}, headers=auth)
    assert r.status_code == 200
    names = [d["name"] for d in _table(client, auth)["diseases"]]
    assert "Temporary Disease" not in names and len(names) == len(rows) - 1
    assert "Temporary Disease" not in (sandbox / "disease-symptoms.clp").read_text()
    assert client.post("/api/doctor/knowledge/revert", json={"version": "../../etc/passwd"}, headers=auth).status_code == 404


# ── CSV export / import ───────────────────────────────────────────────────────

def test_export_csv_round_trips_through_import(client, auth):
    original = _table(client, auth)["diseases"]
    r = client.get("/api/doctor/export_csv", headers=auth)
    assert r.status_code == 200 and r.mimetype == "text/csv"
    text = r.get_data(as_text=True)
    assert text.splitlines()[0].split(",")[:3] == ["id", "name", "category"]
    report = parse_csv(text, original)
    assert report["errors"] == [] and len(report["updated"]) == len(original) and report["added"] == []
    keys = ["id", "name", "category", "severity", "symptoms", "description",
            "recommended_action", "next_steps", "homeopathic_remedies", "icd10"]
    for a, b in zip(original, report["new_diseases"]):
        assert {k: a[k] for k in keys} == {k: b[k] for k in keys}


def test_upload_csv_with_token_works(client, auth):
    from io import BytesIO
    text = diseases_to_csv(_table(client, auth)["diseases"])
    r = client.post("/api/upload_csv", headers=auth, content_type="multipart/form-data",
                    data={"file": (BytesIO(text.encode()), "kb.csv")})
    assert r.status_code == 200 and r.get_json()["errors"] == []


# ── Symptom Management Endpoints ──────────────────────────────────────────────

def test_add_symptom_duplicate_and_similarity(client, auth, sandbox):
    # 1. Similarity check detects existing symptom
    # "Dizziness" exists; sending "Dizzy feeling" should trigger similar_exists
    r = client.post("/api/doctor/symptoms", json={
        "display_name": "Dizzy spells",
        "category": "Common",
        "synonyms": ["feeling dizzy"],
        "edited_by": "Dr S",
    }, headers=auth)
    assert r.status_code == 409
    body = r.get_json()
    assert body["error"] == "similar_exists"
    assert any("dizziness" in s["name"].lower() for s in body["similar"])

    # 2. Resending with confirm_not_duplicate: True succeeds
    r2 = client.post("/api/doctor/symptoms", json={
        "display_name": "Dizzy spells",
        "category": "Common",
        "synonyms": ["feeling dizzy"],
        "confirm_not_duplicate": True,
        "edited_by": "Dr S",
    }, headers=auth)
    assert r2.status_code == 201
    symptom_info = r2.get_json()["symptom"]
    assert symptom_info["name"] == "dizzy_spells"

    # 3. Exactly identical machine name returns 409 conflict
    r3 = client.post("/api/doctor/symptoms", json={
        "display_name": "Dizzy spells",
        "category": "Common",
        "confirm_not_duplicate": True,
        "edited_by": "Dr S",
    }, headers=auth)
    assert r3.status_code == 409
    assert r3.get_json()["error"] == "conflict"

    # 4. Appears in vocabulary and category
    t = _table(client, auth)
    names = [s["name"] for s in t["symptoms"]]
    assert "dizzy_spells" in names

    # 5. Appears in synonyms.json
    syn_file = json.loads((sandbox / "synonyms.json").read_text())
    assert "dizzy_spells" in syn_file["synonyms"]
    assert "feeling dizzy" in syn_file["synonyms"]["dizzy_spells"]


def test_delete_symptom_used_vs_unused(client, auth, sandbox):
    # 1. Deleting a symptom in an emergency rule returns 409
    r_em = client.delete("/api/doctor/symptoms/chest_pain", headers=auth)
    assert r_em.status_code == 409
    assert r_em.get_json()["error"] == "symptom_in_use"

    # 2. Deleting a symptom used by a disease returns 409 with used_by list
    r_dis = client.delete("/api/doctor/symptoms/itching", headers=auth)
    assert r_dis.status_code == 409
    body = r_dis.get_json()
    assert body["error"] == "symptom_in_use"
    assert len(body["used_by"]) > 0

    # 3. Create an unused symptom, then delete it
    r_add = client.post("/api/doctor/symptoms", json={
        "display_name": "Temporary Itch",
        "category": "Skin",
        "confirm_not_duplicate": True,
        "edited_by": "Dr S",
    }, headers=auth)
    assert r_add.status_code == 201
    assert "temporary_itch" in [s["name"] for s in _table(client, auth)["symptoms"]]

    r_del = client.delete("/api/doctor/symptoms/temporary_itch", headers=auth)
    assert r_del.status_code == 200
    assert "temporary_itch" not in [s["name"] for s in _table(client, auth)["symptoms"]]
    syn_file = json.loads((sandbox / "synonyms.json").read_text())
    assert "temporary_itch" not in syn_file["synonyms"]


def test_new_symptom_assigned_to_disease_and_diagnosed(client, auth, sandbox):
    # 1. Add "Loss of balance"
    r_sym = client.post("/api/doctor/symptoms", json={
        "display_name": "Loss of balance",
        "category": "Neurological",
        "synonyms": ["off balance", "unsteady on feet"],
        "confirm_not_duplicate": True,
        "edited_by": "Dr Balance",
    }, headers=auth)
    assert r_sym.status_code == 201

    # 2. Assign to a new disease
    rows = _table(client, auth)["diseases"]
    new_d = _new_disease(name="Equilibrium Disorder", category="Neurological",
                         symptoms=["loss_of_balance", "dizziness"])
    rows.append(new_d)
    r_save = _save(client, auth, rows, edited_by="Dr Balance")
    assert r_save.status_code == 200

    # 3. NLP extraction recognizes synonym "I feel off balance"
    nlp_res = client.post("/api/extract_symptoms", json={"text": "I feel off balance and dizzy"}).get_json()
    assert "loss_of_balance" in nlp_res["matched"]

    # 4. Diagnose with the new symptom works immediately without restart
    diag = client.post("/api/diagnose", json={"symptoms": ["loss_of_balance", "dizziness"]}).get_json()
    disease_names = [d["name"] for d in diag["possible_diseases"]]
    assert "Equilibrium Disorder" in disease_names
