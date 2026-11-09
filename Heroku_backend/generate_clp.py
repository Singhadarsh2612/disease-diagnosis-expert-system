#!/usr/bin/env python3
"""
generate_clp.py
Generates disease-symptoms.clp from knowledge_base.json.
Run: python generate_clp.py
This script is also called automatically by the Flask app on startup.
"""

import json
import os
import re
from datetime import datetime

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
KB_PATH = os.path.join(BACKEND_DIR, "data", "knowledge_base.json")
CLP_PATH = os.path.join(BACKEND_DIR, "data", "disease-symptoms.clp")


# Emergency rules (single source of truth; also read by the doctor-portal validator)
EMERGENCY_RULES = [
    {
        "name": "cardiac-emergency",
        "conditions": ["chest_pain", "shortness_of_breath", "increased_sweating"],
        "message": "Possible cardiac emergency (chest pain + breathlessness + sweating). Call emergency services immediately!"
    },
    {
        "name": "stroke-emergency",
        "conditions": ["facial_drooping", "arm_weakness", "slurred_speech"],
        "message": "Possible stroke (FAST: Face drooping, Arm weakness, Speech difficulty). Call emergency services immediately!"
    },
    {
        "name": "meningitis-emergency",
        "conditions": ["severe_headache", "stiff_neck", "fever"],
        "message": "Possible meningitis (severe headache + stiff neck + fever). Seek emergency care immediately!"
    },
    {
        "name": "anaphylaxis-emergency",
        "conditions": ["hives", "shortness_of_breath", "rapid_heartbeat"],
        "message": "Possible anaphylaxis (severe allergic reaction). Use epinephrine auto-injector and call emergency services!"
    },
    {
        "name": "gi-bleed-emergency",
        "conditions": ["vomiting_blood", "dark_stools"],
        "message": "Possible gastrointestinal bleeding (vomiting blood or black stools). Seek emergency care immediately!"
    },
    {
        "name": "appendicitis-emergency",
        "conditions": ["abdominal_pain", "fever", "rebound_tenderness"],
        "message": "Possible appendicitis. Seek emergency surgical evaluation immediately!"
    },
    {
        "name": "seizure-emergency",
        "conditions": ["seizures"],
        "message": "Seizure detected. Seek emergency care immediately if this is a new onset seizure!"
    },
    {
        "name": "low-consciousness-emergency",
        "conditions": ["confusion", "low_blood_pressure", "rapid_heartbeat"],
        "message": "Possible shock or severe systemic illness. Seek emergency care immediately!"
    }
]


def sanitize_name(name: str) -> str:
    """Convert a name to a valid CLIPS symbol (no spaces, no special chars)."""
    name = name.lower()
    name = re.sub(r"[^a-z0-9_\-]", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")


def generate_clp(kb_path: str = KB_PATH, clp_path: str = CLP_PATH) -> str:
    """Generate a .clp file from the knowledge base JSON. Returns path to generated file."""
    with open(kb_path, "r", encoding="utf-8") as f:
        kb = json.load(f)

    diseases = kb.get("diseases", [])
    lines = []

    # Header
    lines.append("; ===========================================================")
    lines.append("; disease-symptoms.clp")
    lines.append(f"; Auto-generated from knowledge_base.json on {datetime.now().isoformat()}")
    lines.append("; DO NOT EDIT DIRECTLY — edit knowledge_base.json and re-run generate_clp.py")
    lines.append("; This is for academic demonstration only.")
    lines.append("; ===========================================================")
    lines.append("")

    # -----------------------------------------------
    # Deftemplates
    # -----------------------------------------------
    lines.append("; --- Core templates ---")
    lines.append("")
    lines.append("(deftemplate symptom")
    lines.append('  "A symptom reported by the user"')
    lines.append("  (slot name (type SYMBOL)))")
    lines.append("")
    lines.append("(deftemplate disease-profile")
    lines.append('  "A disease entry from the knowledge base"')
    lines.append("  (slot id (type SYMBOL))")
    lines.append("  (slot name (type STRING))")
    lines.append("  (slot category (type SYMBOL))")
    lines.append("  (slot severity (type SYMBOL))")
    lines.append("  (multislot symptoms))")
    lines.append("")
    lines.append("(deftemplate candidate")
    lines.append('  "A candidate disease with match counts"')
    lines.append("  (slot name (type STRING))")
    lines.append("  (slot id (type SYMBOL))")
    lines.append("  (slot matched (type INTEGER) (default 0))")
    lines.append("  (slot total (type INTEGER) (default 0))")
    lines.append("  (slot category (type SYMBOL))")
    lines.append("  (slot severity (type SYMBOL)))")
    lines.append("")
    lines.append("(deftemplate confirmed-disease")
    lines.append('  "A disease that has high confidence"')
    lines.append("  (slot name (type STRING))")
    lines.append("  (slot id (type SYMBOL))")
    lines.append("  (slot confidence (type FLOAT)))")
    lines.append("")
    lines.append("(deftemplate emergency")
    lines.append('  "An emergency condition detected"')
    lines.append("  (slot message (type STRING))")
    lines.append("  (slot priority (type INTEGER) (default 100)))")
    lines.append("")
    lines.append("(deftemplate diagnosis-complete")
    lines.append('  "Signal that diagnosis is done"')
    lines.append("  (slot status (type SYMBOL)))")
    lines.append("")

    # -----------------------------------------------
    # Disease-profile facts (deffacts)
    # -----------------------------------------------
    lines.append("; --- Disease knowledge base facts ---")
    lines.append("")
    lines.append("(deffacts disease-knowledge")
    lines.append('  "All diseases in the knowledge base"')
    for disease in diseases:
        did = sanitize_name(disease["id"])
        dname = disease["name"].replace('"', "'")
        cat = sanitize_name(disease.get("category", "general"))
        sev = sanitize_name(disease.get("severity", "mild"))
        symptoms = " ".join(sanitize_name(s) for s in disease.get("symptoms", []))
        lines.append(f"  (disease-profile")
        lines.append(f"    (id {did})")
        lines.append(f'    (name "{dname}")')
        lines.append(f"    (category {cat})")
        lines.append(f"    (severity {sev})")
        lines.append(f"    (symptoms {symptoms}))") 
    lines.append(")")
    lines.append("")

    # -----------------------------------------------
    # Safety / Emergency rules (high salience)
    # -----------------------------------------------
    lines.append("; --- Emergency / Safety Rules (salience 1000) ---")
    lines.append("")

    emergency_rules = EMERGENCY_RULES

    for rule in emergency_rules:
        rname = rule["name"]
        conds = "\n  ".join(f"(symptom (name {c}))" for c in rule["conditions"])
        msg = rule["message"].replace('"', "'")
        lines.append(f"(defrule detect-{rname}")
        lines.append(f'  "Emergency: {rname}"')
        lines.append(f"  (declare (salience 1000))")
        lines.append(f"  {conds}")
        lines.append(f"  =>")
        lines.append(f'  (assert (emergency (message "{msg}"))))')
        lines.append("")

    # -----------------------------------------------
    # General matching rule
    # -----------------------------------------------
    lines.append("; --- General Matching Rule ---")
    lines.append("")
    lines.append("(defrule compute-candidates")
    lines.append('  "For each disease-profile, count how many asserted symptoms it contains"')
    lines.append("  (declare (salience 10))")
    lines.append("  (disease-profile (id ?id) (name ?n) (symptoms $?syms) (category ?cat) (severity ?sev))")
    lines.append("  =>")
    lines.append("  (bind ?matched 0)")
    lines.append("  (bind ?total (length$ ?syms))")
    lines.append("  (progn$ (?s ?syms)")
    lines.append("    (if (any-factp ((?f symptom)) (eq ?f:name ?s))")
    lines.append("      then (bind ?matched (+ ?matched 1))))")
    lines.append("  (if (> ?matched 0)")
    lines.append("    then (assert (candidate (name ?n) (id ?id) (matched ?matched) (total ?total) (category ?cat) (severity ?sev)))))")
    lines.append("")

    # -----------------------------------------------
    # Confidence threshold rule
    # -----------------------------------------------
    lines.append("(defrule confirm-high-confidence")
    lines.append('  "Assert confirmed-disease for high confidence matches (>= 70%)"')
    lines.append("  (declare (salience 5))")
    lines.append("  ?c <- (candidate (name ?n) (id ?id) (matched ?m) (total ?t))")
    lines.append("  (test (>= (/ ?m ?t) 0.7))")
    lines.append("  =>")
    lines.append("  (assert (confirmed-disease (name ?n) (id ?id) (confidence (/ ?m ?t)))))")
    lines.append("")

    lines.append("(defrule mark-complete")
    lines.append('  "Signal diagnosis computation is complete"')
    lines.append("  (declare (salience -100))")
    lines.append("  =>")
    lines.append("  (assert (diagnosis-complete (status done))))")
    lines.append("")

    # Footer
    lines.append("; End of generated CLIPS knowledge base")

    clp_content = "\n".join(lines)
    with open(clp_path, "w", encoding="utf-8") as f:
        f.write(clp_content)

    print(f"[generate_clp] Generated {len(diseases)} diseases -> {clp_path}")
    return clp_path


if __name__ == "__main__":
    generate_clp()
    print("Done.")
