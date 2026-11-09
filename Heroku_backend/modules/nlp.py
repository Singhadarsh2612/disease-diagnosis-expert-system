"""
nlp.py — Offline NLP for symptom extraction from free text.
Core version: synonym lookup + basic negation, no external ML.
"""
import json
import logging
import os
import re
from typing import Dict, List

logger = logging.getLogger(__name__)

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNONYMS_PATH = os.path.join(BACKEND_DIR, "data", "synonyms.json")

# Words that negate the symptom that follows them
NEGATION_WORDS = ["no ", "not ", "without ", "don't have ", "doesn't have ", "never had ", "denies "]


class SymptomExtractor:
    """Wrapper class for symptom extraction."""
    @staticmethod
    def extract_symptoms(text: str, all_symptoms: List[str]) -> Dict[str, List[str]]:
        return extract_symptoms(text, all_symptoms)


def _load_synonyms() -> Dict[str, str]:
    """Build a flat phrase->canonical map from synonyms.json."""
    try:
        with open(SYNONYMS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        synonyms = data.get("synonyms", {})
    except Exception as e:
        logger.warning(f"[NLP] Could not load synonyms: {e}")
        synonyms = {}

    lookup: Dict[str, str] = {}
    for canonical, phrases in synonyms.items():
        # Map each phrase -> canonical
        for phrase in phrases:
            lookup[phrase.lower().strip()] = canonical
        # Also map the display form "back pain" -> "back_pain"
        lookup[canonical.replace("_", " ").lower()] = canonical
        # And the raw underscore form
        lookup[canonical.lower()] = canonical
    return lookup


_SYNONYM_LOOKUP: Dict[str, str] = {}
_LOOKUP_LOADED = False


def _get_lookup() -> Dict[str, str]:
    global _SYNONYM_LOOKUP, _LOOKUP_LOADED
    if not _LOOKUP_LOADED:
        _SYNONYM_LOOKUP = _load_synonyms()
        _LOOKUP_LOADED = True
    return _SYNONYM_LOOKUP


def reload_synonyms() -> Dict[str, str]:
    global _SYNONYM_LOOKUP, _LOOKUP_LOADED
    _SYNONYM_LOOKUP = _load_synonyms()
    _LOOKUP_LOADED = True
    return _SYNONYM_LOOKUP


def _is_negated(text: str, phrase: str) -> bool:
    """Return True if `phrase` appears right after a negation word in `text`."""
    for neg in NEGATION_WORDS:
        pattern = neg + phrase
        if pattern in text:
            return True
    return False


def extract_symptoms(text: str, all_symptoms: List[str]) -> Dict[str, List[str]]:
    """
    Extract canonical symptom names from free text.

    Strategy (in order):
    1. Build synonym lookup on first call.
    2. Scan n-grams (5→1 words) across the lowercased text.
    3. Check negation for each match.
    4. Also directly check if any canonical symptom display name appears.

    Returns {"matched": [...], "unrecognized": [...]}
    """
    if not text:
        return {"matched": [], "unrecognized": []}

    text_lower = text.lower()
    lookup = _get_lookup()

    matched = set()
    negated = set()

    # Split on sentence punctuation; process each chunk
    chunks = re.split(r"[,\.;!?]+", text_lower)
    for chunk in chunks:
        chunk = chunk.strip()
        words = chunk.split()
        i = 0
        while i < len(words):
            found = False
            # Try longest n-gram first (up to 5 words)
            for n in range(min(5, len(words) - i), 0, -1):
                phrase = " ".join(words[i : i + n])
                canonical = lookup.get(phrase)
                if canonical:
                    if _is_negated(text_lower, phrase):
                        negated.add(canonical)
                    else:
                        matched.add(canonical)
                    i += n
                    found = True
                    break
            if not found:
                i += 1

    # Also directly scan for canonical symptom names (underscore form and display form)
    for sym in all_symptoms:
        display = sym.replace("_", " ")
        for form in [sym, display]:
            if form in text_lower:
                if _is_negated(text_lower, form):
                    negated.add(sym)
                else:
                    matched.add(sym)

    # Remove negated symptoms
    matched -= negated

    # Collect unrecognized significant words (crude heuristic)
    known_phrases = set(lookup.keys())
    all_words = text_lower.split()
    stop = {"i", "a", "an", "the", "have", "has", "had", "been", "am", "is", "are",
            "my", "me", "and", "or", "but", "with", "no", "not", "feel", "feeling",
            "some", "very", "really", "quite", "bit", "little", "lot"}
    unrecognized = [
        w for w in all_words
        if w not in stop and len(w) > 3
        and w not in known_phrases
        and not any(w in s for s in matched)
    ]

    return {
        "matched": sorted(matched),
        "unrecognized": list(set(unrecognized))[:10],
    }
