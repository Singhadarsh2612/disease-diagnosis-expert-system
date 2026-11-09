"""
csv_processor.py — CSV import and validation for the knowledge base.
Expected columns: disease, category, severity, symptoms (semicolon-separated),
description, recommended_action, remedies (semicolon-separated, optional)
"""
import csv
import io
import json
import logging
import os
import re
from typing import Dict, List, Tuple, Any

logger = logging.getLogger(__name__)

VALID_SEVERITIES = {"mild", "moderate", "severe"}
VALID_ACTIONS = {"self-care", "consult-doctor", "emergency"}
VALID_CATEGORIES = {
    "Common", "Respiratory", "Digestive", "Neurological", "Cardiovascular",
    "Skin", "Musculoskeletal", "Urinary", "Eye_ENT", "General_Systemic",
}
# Export uses friendlier column names; map them onto the import names.
COLUMN_ALIASES = {"name": "disease", "homeopathic_remedies": "remedies"}
REQUIRED_COLUMNS = {"disease", "category", "severity", "symptoms", "description", "recommended_action"}


def _sanitize_id(name: str) -> str:
    """Create a slug-style ID from a disease name."""
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return "csv_" + name.strip("_")


def _sanitize_symptom(s: str) -> str:
    """Normalize symptom string to snake_case."""
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def parse_csv(
    csv_content: str,
    existing_diseases: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Parse CSV content and merge into the existing disease list.

    Returns:
        {
          "added": [...],
          "updated": [...],
          "skipped": [...],
          "errors": [{"row": N, "message": "..."}],
          "new_diseases": [...]  # merged list for saving
        }
    """
    report = {
        "added": [],
        "updated": [],
        "skipped": [],
        "errors": [],
        "new_diseases": [d.copy() for d in existing_diseases],
    }

    existing_names = {d["name"].lower(): i for i, d in enumerate(report["new_diseases"])}

    try:
        reader = csv.DictReader(io.StringIO(csv_content.strip()))
    except Exception as e:
        report["errors"].append({"row": 0, "message": f"CSV parse error: {e}"})
        return report

    # Check headers
    if not reader.fieldnames:
        report["errors"].append({"row": 0, "message": "CSV has no headers"})
        return report

    headers = {COLUMN_ALIASES.get(h.strip().lower(), h.strip().lower()) for h in reader.fieldnames}
    missing = REQUIRED_COLUMNS - headers
    if missing:
        report["errors"].append({"row": 0, "message": f"Missing required columns: {missing}"})
        return report

    for row_num, row in enumerate(reader, start=2):
        try:
            row = {COLUMN_ALIASES.get(k.strip().lower(), k.strip().lower()): (v or "").strip() for k, v in row.items() if k}

            name = row.get("disease", "").strip()
            if not name:
                report["errors"].append({"row": row_num, "message": "Empty disease name"})
                continue

            category = row.get("category", "General_Systemic").strip()
            if category not in VALID_CATEGORIES:
                category = "General_Systemic"

            severity = row.get("severity", "mild").strip().lower()
            if severity not in VALID_SEVERITIES:
                report["errors"].append({
                    "row": row_num,
                    "message": f"Invalid severity '{severity}'. Must be: {VALID_SEVERITIES}"
                })
                continue

            recommended_action = row.get("recommended_action", "consult-doctor").strip().lower()
            if recommended_action not in VALID_ACTIONS:
                report["errors"].append({
                    "row": row_num,
                    "message": f"Invalid recommended_action '{recommended_action}'. Must be: {VALID_ACTIONS}"
                })
                continue

            symptoms_raw = row.get("symptoms", "")
            symptoms = [_sanitize_symptom(s) for s in symptoms_raw.split(";") if s.strip()]
            if not symptoms:
                report["errors"].append({"row": row_num, "message": f"No symptoms listed for '{name}'"})
                continue

            description = row.get("description", f"Imported disease: {name}")
            remedies_raw = row.get("remedies", "")
            remedies = [r.strip() for r in remedies_raw.split(";") if r.strip()]

            disease_entry = {
                "id": _sanitize_id(name),
                "name": name,
                "category": category,
                "severity": severity,
                "symptoms": symptoms,
                "description": description,
                "recommended_action": recommended_action,
                "next_steps": row.get("next_steps", "Consult a healthcare professional."),
                "homeopathic_remedies": remedies,
                "remedies_disclaimer": "Traditional suggestions only — not a substitute for medical care.",
                "icd10": row.get("icd10", ""),
            }

            name_lower = name.lower()
            csv_id = _sanitize_symptom(row.get("id", "")) if row.get("id") else ""
            if csv_id and csv_id not in {d["id"] for d in report["new_diseases"]}:
                disease_entry["id"] = csv_id          # honour an id column (export round-trip)
            if name_lower in existing_names:
                idx = existing_names[name_lower]
                disease_entry["id"] = report["new_diseases"][idx]["id"]   # never change an existing id
                if not row.get("remedies") and "remedies" not in row:
                    disease_entry["homeopathic_remedies"] = report["new_diseases"][idx].get("homeopathic_remedies", [])
                report["new_diseases"][idx].update(disease_entry)
                report["updated"].append(name)
            else:
                report["new_diseases"].append(disease_entry)
                existing_names[name_lower] = len(report["new_diseases"]) - 1
                report["added"].append(name)

        except Exception as e:
            report["errors"].append({"row": row_num, "message": str(e)})

    return report


def generate_csv_template() -> str:
    """Generate a CSV template string for download."""
    headers = [
        "disease", "category", "severity", "symptoms", "description",
        "recommended_action", "next_steps", "remedies", "icd10"
    ]
    example = [
        "Example Disease", "Respiratory", "mild",
        "fever;cough;fatigue",
        "An example disease for demonstration",
        "consult-doctor",
        "Rest and see a doctor if symptoms persist",
        "Rest;Hydration",
        "J99"
    ]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerow(example)
    return output.getvalue()


EXPORT_HEADERS = [
    "id", "name", "category", "severity", "symptoms", "description",
    "recommended_action", "next_steps", "homeopathic_remedies", "icd10",
]


def diseases_to_csv(diseases: List[Dict[str, Any]]) -> str:
    """Export diseases as CSV. Re-importable by parse_csv (see column aliases there)."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(EXPORT_HEADERS)
    for d in diseases:
        writer.writerow([
            d.get("id", ""), d.get("name", ""), d.get("category", ""), d.get("severity", ""),
            ";".join(d.get("symptoms", [])), d.get("description", ""),
            d.get("recommended_action", ""), d.get("next_steps", ""),
            ";".join(d.get("homeopathic_remedies", [])), d.get("icd10", ""),
        ])
    return output.getvalue()
