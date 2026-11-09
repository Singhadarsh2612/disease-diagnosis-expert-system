"""
fallback_engine.py — Pure Python diagnosis engine.
Produces the same JSON output as ClipsEngine.
Used when clipspy is not available.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class PythonFallbackEngine:
    """
    Pure-Python forward-chaining engine that replicates the CLIPS logic:
    - Assert symptom facts
    - Match disease-profiles
    - Compute candidates (matched/total)
    - Fire emergency rules
    - Assert confirmed-disease for high confidence
    """

    ENGINE_NAME = "python-fallback"

    # Emergency rules: list of (symptom_set, message)
    EMERGENCY_RULES = [
        (
            {"chest_pain", "shortness_of_breath", "increased_sweating"},
            "Possible cardiac emergency (chest pain + breathlessness + sweating). Call emergency services immediately!"
        ),
        (
            {"facial_drooping", "arm_weakness", "slurred_speech"},
            "Possible stroke (FAST: Face drooping, Arm weakness, Speech difficulty). Call emergency services immediately!"
        ),
        (
            {"severe_headache", "stiff_neck", "fever"},
            "Possible meningitis (severe headache + stiff neck + fever). Seek emergency care immediately!"
        ),
        (
            {"hives", "shortness_of_breath", "rapid_heartbeat"},
            "Possible anaphylaxis (severe allergic reaction). Use epinephrine auto-injector and call emergency services!"
        ),
        (
            {"vomiting_blood", "dark_stools"},
            "Possible gastrointestinal bleeding (vomiting blood or black stools). Seek emergency care immediately!"
        ),
        (
            {"abdominal_pain", "fever", "rebound_tenderness"},
            "Possible appendicitis. Seek emergency surgical evaluation immediately!"
        ),
        (
            {"seizures"},
            "Seizure detected. Seek emergency care immediately if this is a new onset seizure!"
        ),
        (
            {"confusion", "low_blood_pressure", "rapid_heartbeat"},
            "Possible shock or severe systemic illness. Seek emergency care immediately!"
        ),
    ]

    def __init__(self, disease_data: List[Dict[str, Any]]):
        self.disease_data = disease_data

    def run(self, selected_symptoms: List[str]) -> Dict[str, Any]:
        """
        Runs the diagnosis engine for a list of selected symptoms.
        Returns dict with:
          - candidates: list of {name, id, matched, total, category, severity}
          - confirmed: list of {name, id, confidence} (confidence >= 0.7)
          - emergencies: list of {message}
        """
        symptom_set = set(s.lower() for s in selected_symptoms)

        # Fire emergency rules
        emergencies = []
        seen_emergencies = set()
        for condition, message in self.EMERGENCY_RULES:
            if condition.issubset(symptom_set):
                if message not in seen_emergencies:
                    emergencies.append({"message": message})
                    seen_emergencies.add(message)

        # Compute candidates
        candidates = []
        confirmed = []
        for disease in self.disease_data:
            disease_symptoms = set(s.lower() for s in disease.get("symptoms", []))
            total = len(disease_symptoms)
            if total == 0:
                continue
            matched_syms = symptom_set & disease_symptoms
            matched = len(matched_syms)
            if matched > 0:
                candidate = {
                    "name": disease["name"],
                    "id": disease["id"],
                    "matched": matched,
                    "total": total,
                    "category": disease.get("category", "General"),
                    "severity": disease.get("severity", "mild"),
                }
                candidates.append(candidate)
                if matched / total >= 0.7:
                    confirmed.append({
                        "name": disease["name"],
                        "id": disease["id"],
                        "confidence": round(matched / total, 4),
                    })

        return {
            "candidates": candidates,
            "confirmed": confirmed,
            "emergencies": emergencies,
            "engine": self.ENGINE_NAME,
        }
