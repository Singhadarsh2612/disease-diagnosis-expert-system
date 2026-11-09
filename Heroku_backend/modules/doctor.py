"""
doctor.py — Doctor Portal endpoints (shared login + knowledge-base table).
"""
import difflib
import json
import logging
import os
import re

from flask import Blueprint, Response, jsonify, request

from generate_clp import EMERGENCY_RULES
from .csv_processor import VALID_ACTIONS, VALID_SEVERITIES, diseases_to_csv
from .diagnosis import get_engine
from . import diagnosis

from .doctor_auth import (
    check_credentials, clear_failures, create_token, is_rate_limited,
    record_failure, require_doctor, _client_ip, TOKEN_MAX_AGE,
)

logger = logging.getLogger(__name__)

doctor = Blueprint("doctor", __name__, url_prefix="/api/doctor")


def err(code: str, message: str, status: int = 400):
    return jsonify({"error": {"code": code, "message": message}}), status


# ── Auth ──────────────────────────────────────────────────────────────────────

@doctor.route("/login", methods=["POST"])
def login():
    ip = _client_ip()
    if is_rate_limited(ip):
        return err("TOO_MANY_ATTEMPTS", "Too many failed attempts. Try again in a few minutes.", 429)

    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")
    if not isinstance(username, str) or not isinstance(password, str):
        record_failure(ip)
        return err("UNAUTHORIZED", "Invalid username or password.", 401)

    if check_credentials(username, password):
        clear_failures(ip)
        return jsonify({"token": create_token(), "expires_in": TOKEN_MAX_AGE})

    record_failure(ip)
    return err("UNAUTHORIZED", "Invalid username or password.", 401)


@doctor.route("/verify", methods=["GET"])
@require_doctor
def verify():
    return jsonify({"status": "ok"})


# ── Knowledge-base helpers ────────────────────────────────────────────────────

SEVERITY_ORDER = ["mild", "moderate", "severe"]
ACTION_ORDER = ["self-care", "consult-doctor", "emergency"]
MAX_ROWS = 500


def _vocabulary(kb: dict):
    """Return (ordered list of symptom dicts, {name: category}). Union of flat list + categories."""
    cat_of = {}
    for cat, syms in kb.get("symptom_categories", {}).items():
        for sym in syms:
            cat_of.setdefault(sym, cat)
    names = []
    for sym in list(kb.get("all_symptoms", [])) + list(cat_of.keys()):
        if sym not in names:
            names.append(sym)
    names.sort()

    usage_count = {n: 0 for n in names}
    for d in kb.get("diseases", []):
        for s in d.get("symptoms", []):
            if s in usage_count:
                usage_count[s] += 1

    emergency_symptoms = {cond for rule in EMERGENCY_RULES for cond in rule.get("conditions", [])}

    vocab = [{
        "name": n,
        "display_name": n.replace("_", " ").title(),
        "category": cat_of.get(n, "Other"),
        "used_count": usage_count.get(n, 0),
        "is_emergency": n in emergency_symptoms,
    } for n in names]
    return vocab, cat_of


def _suggest(symptom: str, vocab_names: list):
    """Closest known symptom name (substring match first, then fuzzy)."""
    s = symptom.strip().lower().replace(" ", "_")
    if not s:
        return None
    subs = [v for v in vocab_names if s in v or v in s]
    if subs:
        return min(subs, key=lambda v: abs(len(v) - len(s)))
    m = difflib.get_close_matches(s, vocab_names, n=1, cutoff=0.6)
    return m[0] if m else None


def _next_id(used_ids: set) -> str:
    nums = [int(m.group(1)) for i in used_ids if (m := re.fullmatch(r"d(\d+)", i))]
    n = max(nums, default=0) + 1
    while f"d{n:03d}" in used_ids:
        n += 1
    return f"d{n:03d}"


def validate_and_clean(diseases, kb: dict):
    """
    Validate a full edited disease list. Returns (cleaned_list, errors).
    errors = [{row, field, message}]  (row is 1-based, 0 = whole table)
    """
    errors = []

    def add(row, field, msg):
        errors.append({"row": row, "field": field, "message": msg})

    if not isinstance(diseases, list):
        return [], [{"row": 0, "field": "diseases", "message": "diseases must be a list"}]
    if len(diseases) > MAX_ROWS:
        return [], [{"row": 0, "field": "diseases", "message": f"Too many rows (max {MAX_ROWS})"}]

    vocab, _ = _vocabulary(kb)
    vocab_names = [v["name"] for v in vocab]
    vocab_set = set(vocab_names)
    categories = list(kb.get("symptom_categories", {}).keys())
    old_by_id = {d["id"]: d for d in kb.get("diseases", [])}

    cleaned, seen_names, used_ids = [], {}, set()

    for idx, raw in enumerate(diseases, start=1):
        if not isinstance(raw, dict):
            add(idx, "row", "Row is not a valid disease")
            continue

        def text(field, required=False):
            v = raw.get(field, "")
            if v is None:
                v = ""
            if not isinstance(v, str):
                add(idx, field, f"{field.replace('_', ' ').capitalize()} must be text")
                return ""
            v = v.strip()
            if required and not v:
                add(idx, field, f"{field.replace('_', ' ').capitalize()} is required")
            return v

        name = text("name", required=True)
        if name:
            key = name.lower()
            if key in seen_names:
                add(idx, "name", f"'{name}' is already used in row {seen_names[key]} (names must be unique)")
            else:
                seen_names[key] = idx

        category = text("category", required=True)
        if category and category not in categories:
            add(idx, "category", f"'{category}' is not an allowed category")
        severity = text("severity", required=True).lower()
        if severity and severity not in VALID_SEVERITIES:
            add(idx, "severity", f"'{severity}' is not allowed (use mild, moderate or severe)")
        action = text("recommended_action", required=True).lower()
        if action and action not in VALID_ACTIONS:
            add(idx, "recommended_action", f"'{action}' is not allowed (use self-care, consult-doctor or emergency)")

        syms_raw = raw.get("symptoms", [])
        symptoms = []
        if not isinstance(syms_raw, list):
            add(idx, "symptoms", "Symptoms must be a list")
        else:
            for sym in syms_raw:
                if not isinstance(sym, str) or not sym.strip():
                    add(idx, "symptoms", "Empty symptom entry")
                    continue
                sym = sym.strip()
                if sym in symptoms:
                    continue
                if sym not in vocab_set:
                    hint = _suggest(sym, vocab_names)
                    msg = f"'{sym}' is not a known symptom"
                    if hint:
                        msg += f", did you mean '{hint}'?"
                    add(idx, "symptoms", msg)
                symptoms.append(sym)
            if len(symptoms) < 2:
                add(idx, "symptoms", "Each disease needs at least 2 symptoms")

        remedies_raw = raw.get("homeopathic_remedies", [])
        remedies = []
        if not isinstance(remedies_raw, list) or not all(isinstance(r, str) for r in remedies_raw):
            add(idx, "homeopathic_remedies", "Remedies must be a list of text lines")
        else:
            remedies = [r.strip() for r in remedies_raw if r.strip()]

        did = raw.get("id") if isinstance(raw.get("id"), str) else ""
        did = did.strip()
        if did and did in used_ids:
            add(idx, "id", f"Duplicate id '{did}'")
        if did:
            used_ids.add(did)

        base = dict(old_by_id.get(did, {})) if did else {}
        base.update({
            "id": did, "name": name, "category": category, "severity": severity,
            "symptoms": symptoms, "description": text("description"),
            "recommended_action": action, "next_steps": text("next_steps"),
            "homeopathic_remedies": remedies, "icd10": text("icd10"),
        })
        base.setdefault("remedies_disclaimer", "Traditional suggestions only — not a substitute for medical care.")
        if raw.get("last_edited_by"):
            base["last_edited_by"] = raw["last_edited_by"]
        if raw.get("last_edited_at"):
            base["last_edited_at"] = raw["last_edited_at"]
        cleaned.append(base)

    # assign ids to new rows
    all_ids = set(used_ids) | set(old_by_id.keys())
    for d in cleaned:
        if not d["id"]:
            d["id"] = _next_id(all_ids)
            all_ids.add(d["id"])

    # emergency-rule protection: symptoms used by a rule must stay in use by some disease
    old_used = {s for d in kb.get("diseases", []) for s in d.get("symptoms", [])}
    new_used = {s for d in cleaned for s in d["symptoms"]}
    for rule in EMERGENCY_RULES:
        for cond in rule["conditions"]:
            if cond not in vocab_set:
                add(0, "symptoms", f"Emergency rule '{rule['name']}' needs symptom '{cond}', which is not in the symptom list")
            elif cond in old_used and cond not in new_used:
                add(0, "symptoms",
                    f"Saving would remove the symptom '{cond}' from every disease, but the emergency rule "
                    f"'{rule['name']}' depends on it. Keep it in at least one disease.")
    return cleaned, errors


# ── Table endpoints (all protected) ───────────────────────────────────────────

@doctor.route("/knowledge", methods=["GET"])
@require_doctor
def get_knowledge():
    engine = get_engine()
    kb = engine._kb
    vocab, _ = _vocabulary(kb)
    return jsonify({
        "diseases": engine.get_all_diseases(),
        "categories": list(kb.get("symptom_categories", {}).keys()),
        "severities": SEVERITY_ORDER,
        "actions": ACTION_ORDER,
        "symptoms": vocab,
        "version": kb.get("_meta", {}).get("version", ""),
        "last_edited_by": kb.get("_meta", {}).get("last_edited_by", ""),
        "saved_at": kb.get("_meta", {}).get("saved_at", ""),
    })


@doctor.route("/knowledge/version", methods=["GET"])
@require_doctor
def get_knowledge_version():
    meta = get_engine()._kb.get("_meta", {})
    return jsonify({
        "version": meta.get("version", ""),
        "last_edited_by": meta.get("last_edited_by", ""),
        "last_saved_at": meta.get("saved_at", ""),
    })


@doctor.route("/changelog", methods=["GET"])
@require_doctor
def get_changelog():
    limit = request.args.get("limit", 200, type=int)
    return jsonify({"changelog": get_engine().get_changelog(limit=limit)})


@doctor.route("/knowledge", methods=["PUT"])
@require_doctor
def save_knowledge():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or "diseases" not in data:
        return err("INVALID_INPUT", "Send {diseases: [...]}")

    edited_by = data.get("edited_by")
    if not isinstance(edited_by, str) or not edited_by.strip() or len(edited_by.strip()) > 60:
        return err("INVALID_INPUT", "edited_by is required (non-empty string, max 60 chars)", 400)
    edited_by = edited_by.strip()

    engine = get_engine()
    current_version = engine._kb.get("_meta", {}).get("version", "")
    base_version = data.get("base_version")
    if base_version is None or str(base_version) != current_version:
        meta = engine._kb.get("_meta", {})
        return jsonify({
            "error": "conflict",
            "current_version": current_version,
            "last_edited_by": meta.get("last_edited_by", ""),
            "last_saved_at": meta.get("saved_at", ""),
        }), 409

    cleaned, errors = validate_and_clean(data["diseases"], engine._kb)
    if errors:
        return jsonify({"errors": errors}), 400

    try:
        result = engine.replace_all_diseases(cleaned, edited_by)
    except Exception as e:
        logger.error("[Doctor] Save failed", exc_info=True)
        return err("SAVE_FAILED", f"Could not apply the changes; the previous version was restored. ({e})", 500)
    return jsonify({"status": "ok", **result})


@doctor.route("/versions", methods=["GET"])
@require_doctor
def versions():
    return jsonify({"versions": get_engine().list_versions(20)})


@doctor.route("/knowledge/revert", methods=["POST"])
@require_doctor
def revert():
    data = request.get_json(silent=True) or {}
    version = data.get("version", "")
    if not isinstance(version, str) or not version:
        return err("INVALID_INPUT", "version (backup filename) is required")
    edited_by = data.get("edited_by", "Doctor")
    if not isinstance(edited_by, str) or not edited_by.strip():
        edited_by = "Doctor"
    try:
        result = get_engine().revert_to_version(version, edited_by=edited_by.strip()[:60])
    except FileNotFoundError as e:
        return err("NOT_FOUND", str(e), 404)
    except Exception as e:
        logger.error("[Doctor] Revert failed", exc_info=True)
        return err("REVERT_FAILED", f"Could not restore that version; the current one was kept. ({e})", 500)
    return jsonify({"status": "ok", **result})


@doctor.route("/export_csv", methods=["GET"])
@require_doctor
def export_csv():
    return Response(
        diseases_to_csv(get_engine().get_all_diseases()),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=knowledge_base.csv"},
    )


# ── Symptom management ────────────────────────────────────────────────────────

@doctor.route("/symptoms", methods=["POST"])
@require_doctor
def add_symptom():
    data = request.get_json(silent=True) or {}
    display_name = data.get("display_name", "")
    category = data.get("category", "")
    synonyms = data.get("synonyms", [])
    confirm_not_duplicate = bool(data.get("confirm_not_duplicate", False))
    edited_by = data.get("edited_by", "")

    if not isinstance(display_name, str):
        return err("INVALID_INPUT", "display_name must be text", 400)
    display_name = display_name.strip()
    if not re.fullmatch(r"[a-zA-Z0-9 -]{2,50}", display_name):
        return err("INVALID_INPUT", "display_name must be 2-50 characters with only letters, digits, spaces and hyphens", 400)

    engine = get_engine()
    categories = list(engine._kb.get("symptom_categories", {}).keys())
    if not isinstance(category, str) or category not in categories:
        return err("INVALID_INPUT", f"category must be one of: {', '.join(categories)}", 400)

    if not isinstance(edited_by, str) or not edited_by.strip() or len(edited_by.strip()) > 60:
        return err("INVALID_INPUT", "edited_by is required (non-empty string, max 60 chars)", 400)
    edited_by = edited_by.strip()

    if not isinstance(synonyms, list) or not all(isinstance(s, str) for s in synonyms):
        return err("INVALID_INPUT", "synonyms must be a list of text phrases", 400)

    m_name = re.sub(r"[\s\-]+", "_", display_name.lower())
    m_name = re.sub(r"[^a-z0-9_]", "", m_name).strip("_")
    if not m_name:
        return err("INVALID_INPUT", "Could not generate valid machine name from display_name", 400)

    vocab, _ = _vocabulary(engine._kb)
    vocab_map = {v["name"]: v for v in vocab}
    if m_name in vocab_map:
        return jsonify({"error": "conflict", "message": f"Symptom '{m_name}' already exists"}), 409

    syn_data = {}
    syn_path = diagnosis.SYNONYMS_PATH
    if os.path.exists(syn_path):
        try:
            with open(syn_path, "r", encoding="utf-8") as f:
                syn_data = json.load(f)
        except Exception:
            syn_data = {}
    syn_dict = syn_data.get("synonyms", {})

    clean_synonyms = [s.strip().lower() for s in synonyms if s.strip()]
    candidates = [display_name.lower(), m_name] + clean_synonyms

    similar = {}
    for v in vocab:
        existing_name = v["name"].lower()
        existing_display = v["display_name"].lower()
        existing_syns = [p.lower() for p in syn_dict.get(v["name"], [])]
        targets = [existing_name, existing_display] + existing_syns

        match_found = False
        for c in candidates:
            if not c:
                continue
            for t in targets:
                if not t:
                    continue
                ratio = difflib.SequenceMatcher(None, c, t).ratio()
                if ratio >= 0.8:
                    match_found = True
                    break
                if len(c) >= 3 and len(t) >= 3 and (c in t or t in c):
                    match_found = True
                    break
            if match_found:
                break

        if match_found:
            similar[v["name"]] = {"name": v["name"], "display_name": v["display_name"]}

    if similar and not confirm_not_duplicate:
        return jsonify({
            "error": "similar_exists",
            "message": "Similar symptoms exist",
            "similar": list(similar.values())
        }), 409

    try:
        res = engine.add_symptom_full(
            machine_name=m_name,
            display_name=display_name,
            category=category,
            synonyms=clean_synonyms,
            edited_by=edited_by,
        )
    except Exception as e:
        logger.error(f"[Doctor] Add symptom failed: {e}", exc_info=True)
        return err("ADD_FAILED", f"Could not add symptom; the previous version was restored. ({e})", 500)

    return jsonify({
        "status": "ok",
        "symptom": {
            "name": m_name,
            "display_name": display_name,
            "category": category,
        },
        "version": res.get("version", ""),
    }), 201


@doctor.route("/symptoms/<name>", methods=["DELETE"])
@require_doctor
def delete_symptom(name):
    name = (name or "").strip().lower()
    engine = get_engine()
    vocab, _ = _vocabulary(engine._kb)
    vocab_map = {v["name"]: v for v in vocab}
    if name not in vocab_map:
        return err("NOT_FOUND", f"Symptom '{name}' not found", 404)

    emergency_rules_using = [
        rule["name"] for rule in EMERGENCY_RULES if name in rule.get("conditions", [])
    ]
    if emergency_rules_using:
        return jsonify({
            "error": "symptom_in_use",
            "message": f"Cannot delete '{name}': required by emergency rule(s): {', '.join(emergency_rules_using)}",
            "emergency_rules": emergency_rules_using,
        }), 409

    diseases_using = [
        {"id": d.get("id"), "name": d.get("name")}
        for d in engine.get_all_diseases()
        if name in d.get("symptoms", [])
    ]
    if diseases_using:
        return jsonify({
            "error": "symptom_in_use",
            "message": f"Cannot delete '{name}': used by {len(diseases_using)} disease(s)",
            "used_by": diseases_using,
        }), 409

    data = request.get_json(silent=True) or {}
    edited_by = data.get("edited_by", "Doctor")
    if not isinstance(edited_by, str) or not edited_by.strip():
        edited_by = "Doctor"

    try:
        res = engine.delete_symptom_full(name, edited_by=edited_by.strip()[:60])
    except Exception as e:
        logger.error(f"[Doctor] Delete symptom failed: {e}", exc_info=True)
        return err("DELETE_FAILED", f"Could not delete symptom; the previous version was restored. ({e})", 500)

    return jsonify({
        "status": "ok",
        "deleted": name,
        "version": res.get("version", ""),
    }), 200
