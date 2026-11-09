"""
models.py - Data classes for the disease diagnosis system.
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Symptom:
    name: str
    category: str = "General_Systemic"
    display_name: str = ""

    def __post_init__(self):
        if not self.display_name:
            self.display_name = self.name.replace("_", " ").title()


@dataclass
class Disease:
    id: str
    name: str
    category: str
    severity: str
    symptoms: List[str]
    description: str
    recommended_action: str
    next_steps: str = ""
    homeopathic_remedies: List[str] = field(default_factory=list)
    remedies_disclaimer: str = "Traditional suggestions only — not a substitute for medical care."
    icd10: str = ""

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "severity": self.severity,
            "symptoms": self.symptoms,
            "description": self.description,
            "recommended_action": self.recommended_action,
            "next_steps": self.next_steps,
            "homeopathic_remedies": self.homeopathic_remedies,
            "remedies_disclaimer": self.remedies_disclaimer,
            "icd10": self.icd10,
        }


@dataclass
class DiagnosisResult:
    name: str
    id: str
    category: str
    severity: str
    confidence: float
    label: str  # High / Moderate / Low
    matched_symptoms: List[str]
    missing_symptoms: List[str]
    total_symptoms: int
    description: str = ""
    recommended_action: str = ""
    next_steps: str = ""
    homeopathic_remedies: List[str] = field(default_factory=list)
    remedies_disclaimer: str = ""

    def to_dict(self):
        return {
            "name": self.name,
            "id": self.id,
            "category": self.category,
            "severity": self.severity,
            "confidence": round(self.confidence, 4),
            "label": self.label,
            "matched_symptoms": self.matched_symptoms,
            "missing_symptoms": self.missing_symptoms,
            "total_symptoms": self.total_symptoms,
            "description": self.description,
            "recommended_action": self.recommended_action,
            "next_steps": self.next_steps,
            "homeopathic_remedies": self.homeopathic_remedies,
            "remedies_disclaimer": self.remedies_disclaimer,
        }


@dataclass
class Feedback:
    session_id: str
    satisfied: bool
    final_disease: str = ""
    missed_symptoms: List[str] = field(default_factory=list)
    comments: str = ""
    timestamp: str = ""
