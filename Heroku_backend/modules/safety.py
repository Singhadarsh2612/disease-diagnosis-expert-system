"""
safety.py — Critical condition rules and disclaimer management.
Emergency rules are defined here for use by the frontend safety layer.
"""
from typing import List, Dict

DISCLAIMER_SHORT = (
    "⚠️ Not a substitute for professional medical advice."
)

DISCLAIMER_FULL = (
    "⚠️ MEDICAL DISCLAIMER: This tool is for academic demonstration purposes only. "
    "It provides preliminary, informational guidance and is NOT a substitute for "
    "professional medical advice, diagnosis, or treatment. Always consult a qualified "
    "healthcare professional for medical concerns. In case of emergency, call emergency "
    "services (112/911) immediately."
)

# Emergency rules for display in the frontend
EMERGENCY_RULES = [
    {
        "id": "cardiac",
        "trigger_symptoms": ["chest_pain", "shortness_of_breath", "increased_sweating"],
        "message": "⚠️ EMERGENCY: These symptoms may indicate a cardiac event. Call emergency services (112/911) IMMEDIATELY.",
        "severity": "critical",
    },
    {
        "id": "stroke",
        "trigger_symptoms": ["facial_drooping", "arm_weakness", "slurred_speech"],
        "message": "⚠️ EMERGENCY: FAST signs of stroke detected. Call emergency services (112/911) IMMEDIATELY.",
        "severity": "critical",
    },
    {
        "id": "meningitis",
        "trigger_symptoms": ["severe_headache", "stiff_neck", "fever"],
        "message": "⚠️ EMERGENCY: Possible meningitis. Seek emergency care IMMEDIATELY.",
        "severity": "critical",
    },
    {
        "id": "anaphylaxis",
        "trigger_symptoms": ["hives", "shortness_of_breath", "rapid_heartbeat"],
        "message": "⚠️ EMERGENCY: Signs of anaphylaxis. Use epinephrine (EpiPen) and call emergency services NOW.",
        "severity": "critical",
    },
    {
        "id": "gi_bleed",
        "trigger_symptoms": ["vomiting_blood", "dark_stools"],
        "message": "⚠️ EMERGENCY: GI bleeding suspected. Seek emergency care IMMEDIATELY.",
        "severity": "critical",
    },
]


def check_emergency(selected_symptoms: List[str]) -> List[Dict]:
    """Check symptoms against emergency rules. Returns triggered rules."""
    selected_set = set(s.lower() for s in selected_symptoms)
    triggered = []
    for rule in EMERGENCY_RULES:
        if set(rule["trigger_symptoms"]).issubset(selected_set):
            triggered.append({
                "id": rule["id"],
                "message": rule["message"],
                "severity": rule["severity"],
            })
    return triggered


def get_safety_disclaimer(recommended_action: str) -> str:
    """Return an appropriate disclaimer based on recommended action."""
    if recommended_action == "emergency":
        return "🚨 This condition may require emergency care. Please call emergency services immediately."
    elif recommended_action == "consult-doctor":
        return "🏥 Please consult a healthcare professional for proper evaluation and treatment."
    else:
        return "💊 For self-care conditions, monitor symptoms. Seek care if symptoms worsen."
