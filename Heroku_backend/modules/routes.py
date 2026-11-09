"""
routes.py — Flask REST API endpoints (CORE features only).
"""
import json
import logging
import os
import time
import uuid
from datetime import datetime

from flask import Blueprint, Response, jsonify, request

from .csv_processor import generate_csv_template, parse_csv
from .diagnosis import get_engine
from .doctor_auth import require_doctor
from .semantic_nlp import extract_symptoms, get_nlp_mode

logger = logging.getLogger(__name__)

api = Blueprint("api", __name__, url_prefix="/api")

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEEDBACK_PATH = os.path.join(BACKEND_DIR, "data", "feedback.json")

MAX_SYMPTOMS = 50
MAX_TEXT_LENGTH = 2000

DISCLAIMER = (
    "⚠️ MEDICAL DISCLAIMER: This tool provides preliminary guidance only and is "
    "NOT a substitute for professional medical advice, diagnosis, or treatment. "
    "Always consult a qualified healthcare professional."
)


# ── helpers ──────────────────────────────────────────────────────────────────

def err(code: str, message: str, status: int = 400):
    return jsonify({"error": {"code": code, "message": message}}), status


def _load_feedback() -> list:
    if os.path.exists(FEEDBACK_PATH):
        try:
            with open(FEEDBACK_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _save_feedback(data: list):
    tmp = FEEDBACK_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, FEEDBACK_PATH)


# ── GET /api/health ───────────────────────────────────────────────────────────

@api.route("/health", methods=["GET"])
def health():
    engine = get_engine()
    return jsonify({
        "status": "ok",
        "engine": engine.engine_name,
        "kb_version": engine.kb_version,
        "disease_count": engine.disease_count,
        "symptom_count": engine.symptom_count,
        "nlp": get_nlp_mode(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })


# ── GET /api/get_initial_symptoms ─────────────────────────────────────────────

@api.route("/get_initial_symptoms", methods=["GET"])
def get_initial_symptoms():
    engine = get_engine()
    categories = engine.get_all_symptoms_by_category()
    result = {
        cat: [{"name": s, "display_name": s.replace("_", " ").title()} for s in syms]
        for cat, syms in categories.items()
    }
    return jsonify({"categories": result, "engine": engine.engine_name})


# ── GET /api/symptoms ─────────────────────────────────────────────────────────

@api.route("/symptoms", methods=["GET"])
def get_symptoms():
    engine = get_engine()
    category = request.args.get("category", "").strip()
    query = request.args.get("q", "").strip().lower()
    page = max(1, int(request.args.get("page", 1)))
    page_size = min(int(request.args.get("page_size", 50)), 200)

    all_syms = []
    for cat, syms in engine.get_all_symptoms_by_category().items():
        if category and cat.lower() != category.lower():
            continue
        for s in syms:
            all_syms.append({"name": s, "display_name": s.replace("_", " ").title(), "category": cat})

    if query:
        all_syms = [s for s in all_syms if query in s["name"] or query in s["display_name"].lower()]

    total = len(all_syms)
    start = (page - 1) * page_size
    return jsonify({
        "symptoms": all_syms[start : start + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


# ── POST /api/diagnose ────────────────────────────────────────────────────────

@api.route("/diagnose", methods=["POST"])
def diagnose():
    data = request.get_json(silent=True) or {}
    symptoms = data.get("symptoms", [])
    denied_symptoms = data.get("denied_symptoms", [])

    if not isinstance(symptoms, list):
        return err("INVALID_INPUT", "symptoms must be a list")
    if not isinstance(denied_symptoms, list):
        return err("INVALID_INPUT", "denied_symptoms must be a list")
    if len(symptoms) > MAX_SYMPTOMS:
        return err("TOO_MANY_SYMPTOMS", f"Max {MAX_SYMPTOMS} symptoms")
    if len(denied_symptoms) > MAX_SYMPTOMS:
        return err("TOO_MANY_SYMPTOMS", f"Max {MAX_SYMPTOMS} denied symptoms")

    symptoms = [str(s).strip().lower() for s in symptoms if s]
    denied_symptoms = [str(s).strip().lower() for s in denied_symptoms if s]

    t0 = time.time()
    result = get_engine().diagnose(symptoms, denied_symptoms)
    result["response_time_ms"] = round((time.time() - t0) * 1000, 1)
    return jsonify(result)


# ── POST /api/extract_symptoms ────────────────────────────────────────────────

@api.route("/extract_symptoms", methods=["POST"])
def extract_symptoms_endpoint():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()

    if not text:
        return err("EMPTY_TEXT", "text field is required")
    if len(text) > MAX_TEXT_LENGTH:
        return err("TEXT_TOO_LONG", f"Max {MAX_TEXT_LENGTH} characters")

    engine = get_engine()
    all_syms = list(engine._kb.get("all_symptoms", []))
    result = extract_symptoms(text, all_syms)
    return jsonify({
        "matched": result["matched"],
        "unrecognized": result["unrecognized"],
        "suggestions": result.get("suggestions", []),
        "method": result.get("method", "dictionary"),
    })


# ── GET /api/diseases ─────────────────────────────────────────────────────────

@api.route("/diseases", methods=["GET"])
def get_diseases():
    engine = get_engine()
    q = request.args.get("q", "").strip().lower()
    category = request.args.get("category", "").strip()
    page = max(1, int(request.args.get("page", 1)))
    page_size = min(int(request.args.get("page_size", 20)), 100)

    diseases = engine.get_all_diseases()
    if q:
        diseases = [d for d in diseases if q in d["name"].lower()]
    if category:
        diseases = [d for d in diseases if d.get("category", "").lower() == category.lower()]

    total = len(diseases)
    start = (page - 1) * page_size
    return jsonify({
        "diseases": diseases[start : start + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@api.route("/diseases/<disease_id>", methods=["GET"])
def get_disease(disease_id):
    d = get_engine().get_disease_by_id(disease_id)
    if not d:
        return err("NOT_FOUND", f"Disease '{disease_id}' not found", 404)
    return jsonify(d)


# ── POST /api/knowledge/disease ───────────────────────────────────────────────

@api.route("/knowledge/disease", methods=["POST"])
@require_doctor
def add_disease():
    data = request.get_json(silent=True) or {}
    ok, msg = get_engine().add_disease(data)
    if ok:
        return jsonify({"status": "ok", "message": msg}), 201
    return err("VALIDATION_ERROR", msg)


@api.route("/knowledge/disease/<disease_id>", methods=["PUT"])
@require_doctor
def update_disease(disease_id):
    data = request.get_json(silent=True) or {}
    ok, msg = get_engine().update_disease(disease_id, data)
    return jsonify({"status": "ok", "message": msg}) if ok else err("NOT_FOUND", msg, 404)


@api.route("/knowledge/disease/<disease_id>", methods=["DELETE"])
@require_doctor
def delete_disease(disease_id):
    ok, msg = get_engine().delete_disease(disease_id)
    return jsonify({"status": "ok", "message": msg}) if ok else err("NOT_FOUND", msg, 404)


@api.route("/knowledge/symptom", methods=["POST"])
@require_doctor
def add_symptom():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip().lower().replace(" ", "_")
    category = data.get("category", "General_Systemic").strip()
    if not name:
        return err("INVALID_INPUT", "name is required")
    ok, msg = get_engine().add_symptom(name, category)
    return (jsonify({"status": "ok", "message": msg}), 201) if ok else err("CONFLICT", msg, 409)


@api.route("/knowledge/symptom/<symptom_name>", methods=["DELETE"])
@require_doctor
def delete_symptom(symptom_name):
    ok, msg = get_engine().delete_symptom(symptom_name)
    return jsonify({"status": "ok", "message": msg}) if ok else err("NOT_FOUND", msg, 404)


# ── POST /api/upload_csv ──────────────────────────────────────────────────────

@api.route("/upload_csv", methods=["POST"])
@require_doctor
def upload_csv():
    if "file" not in request.files:
        return err("NO_FILE", "Upload a file with key 'file'")
    file = request.files["file"]
    if not file.filename.lower().endswith(".csv"):
        return err("INVALID_FILE", "Only .csv files accepted")
    try:
        content = file.read().decode("utf-8")
    except Exception as e:
        return err("READ_ERROR", str(e))

    engine = get_engine()
    report = parse_csv(content, engine.get_all_diseases())
    new_diseases = report.pop("new_diseases")

    if report["added"] or report["updated"]:
        try:
            engine._backup_kb()
            engine._kb["diseases"] = new_diseases
            engine._kb["_meta"]["disease_count"] = len(new_diseases)
            engine._write_kb_atomic(engine._kb)
            engine._load_kb()
            engine._regenerate_clp()
            engine._update_fallback_engine()
        except Exception as e:
            return err("SAVE_ERROR", str(e), 500)

    return jsonify({
        "status": "ok" if not report["errors"] else "partial",
        "added": report["added"],
        "updated": report["updated"],
        "skipped": report["skipped"],
        "errors": report["errors"],
        "summary": f"Added: {len(report['added'])}, Updated: {len(report['updated'])}, Errors: {len(report['errors'])}",
    })


@api.route("/upload_csv/template", methods=["GET"])
def csv_template():
    return Response(
        generate_csv_template(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=disease_import_template.csv"},
    )


# ── POST /api/feedback ────────────────────────────────────────────────────────

@api.route("/feedback", methods=["POST"])
def submit_feedback():
    data = request.get_json(silent=True) or {}
    if data.get("satisfied") is None:
        return err("INVALID_INPUT", "satisfied (bool) is required")
    entry = {
        "session_id": data.get("session_id", str(uuid.uuid4())),
        "satisfied": bool(data["satisfied"]),
        "final_disease": data.get("final_disease", ""),
        "missed_symptoms": data.get("missed_symptoms", []),
        "denied_symptoms": data.get("denied_symptoms", []) if isinstance(data.get("denied_symptoms"), list) else [],
        "comments": str(data.get("comments", ""))[:500],
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    feedback_list = _load_feedback()
    feedback_list.append(entry)
    _save_feedback(feedback_list)
    return jsonify({"status": "ok", "message": "Feedback recorded. Thank you!"}), 201


# ── root ──────────────────────────────────────────────────────────────────────

@api.route("/", methods=["GET"])
def api_root():
    return jsonify({"message": "AI Disease Diagnosis Expert System API", "health": "/api/health"})
