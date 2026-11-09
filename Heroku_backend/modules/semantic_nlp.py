"""
semantic_nlp.py — Semantic symptom extraction using a local embedding model.
Uses fastembed with BAAI/bge-small-en-v1.5 and cached vectors.
Falls back to dictionary-only extraction if the model cannot be loaded.
"""
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

logger = logging.getLogger(__name__)

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BACKEND_DIR, "models")
KB_PATH = os.path.join(BACKEND_DIR, "data", "knowledge_base.json")
SYNONYMS_PATH = os.path.join(BACKEND_DIR, "data", "synonyms.json")
CACHE_FILE = os.path.join(MODELS_DIR, "semantic_index.npz")

NEGATION_WORDS = ["no ", "not ", "without ", "don't have ", "doesn't have ", "never had ", "denies "]

STOP_WORDS = {
    "i", "a", "an", "the", "have", "has", "had", "been", "am", "is", "are",
    "was", "were", "my", "me", "and", "or", "but", "with", "feel", "feeling",
    "feels", "like", "some", "very", "really", "quite", "bit", "little", "lot",
    "also", "just", "so", "to", "in", "of", "for", "on", "at", "it", "that",
    "this", "do", "does", "did", "be", "im", "got", "bad", "slight", "mild", "severe"
}


def _is_negated(text: str, phrase: str) -> bool:
    """Return True if `phrase` appears right after a negation expression in `text`."""
    text_lower = text.lower()
    phrase_clean = phrase.lower().strip().replace("_", " ")
    if not phrase_clean:
        return False
    # Pattern 1: Negation trigger followed optionally by filler words, then the phrase
    neg_pattern = rf"\b(no|not|without|never|denies|denied|don't have|doesn't have|didn't have|do not have|does not have|did not have|haven't had|free of)\b(?:\s+(?:a|an|the|any|much|signs? of))?\s+{re.escape(phrase_clean)}\b"
    if re.search(neg_pattern, text_lower):
        return True
    # Pattern 2: Conjunction negation: 'no fever or headache' -> headache is also negated
    conj_pattern = rf"\b(no|not|without|never|denies|denied|don't have|doesn't have|didn't have|do not have|does not have|did not have)\b(?:\s+(?:a|an|the|any|much|signs? of))?\s+\w+(?:\s+\w+)?\s+(?:or|nor)\s+{re.escape(phrase_clean)}\b"
    if re.search(conj_pattern, text_lower):
        return True
    return False


class SemanticSymptomExtractor:
    def __init__(
        self,
        models_dir: str = MODELS_DIR,
        kb_path: str = KB_PATH,
        synonyms_path: str = SYNONYMS_PATH,
    ):
        self.models_dir = models_dir
        self.kb_path = kb_path
        self.synonyms_path = synonyms_path
        self.mode = "dictionary"
        self.model = None

        self.index_phrases: List[str] = []
        self.index_symptoms: List[str] = []
        self.index_display_names: List[str] = []
        self.index_vectors: Optional[np.ndarray] = None

        self._init_model()

    def _init_model(self):
        """Try loading fastembed with bge-small-en-v1.5 from models_dir."""
        try:
            from fastembed import TextEmbedding

            os.makedirs(self.models_dir, exist_ok=True)
            self.model = TextEmbedding(
                model_name="BAAI/bge-small-en-v1.5",
                cache_dir=self.models_dir,
            )
            self.mode = "semantic"
            self._load_or_build_index()
            logger.info("[SemanticNLP] Successfully initialized fastembed (bge-small-en-v1.5).")
        except Exception as e:
            logger.warning(f"[SemanticNLP] Failed to load embedding model ({e}). Falling back to dictionary-only.")
            self.model = None
            self.mode = "dictionary"

    def _get_mtimes(self) -> Tuple[float, float]:
        kb_mtime = os.path.getmtime(self.kb_path) if os.path.exists(self.kb_path) else 0.0
        syn_mtime = os.path.getmtime(self.synonyms_path) if os.path.exists(self.synonyms_path) else 0.0
        return kb_mtime, syn_mtime

    def _load_or_build_index(self):
        """Load cached index if fresh, otherwise rebuild and save."""
        kb_mtime, syn_mtime = self._get_mtimes()
        self._cached_kb_mtime = kb_mtime
        self._cached_syn_mtime = syn_mtime

        cache_path = os.path.join(self.models_dir, "semantic_index.npz")
        if os.path.exists(cache_path):
            try:
                data = np.load(cache_path, allow_pickle=True)
                cached_kb = float(data.get("kb_mtime", 0.0))
                cached_syn = float(data.get("syn_mtime", 0.0))
                if abs(cached_kb - kb_mtime) < 1e-4 and abs(cached_syn - syn_mtime) < 1e-4:
                    self.index_vectors = data["vectors"]
                    self.index_phrases = [str(x) for x in data["phrases"]]
                    self.index_symptoms = [str(x) for x in data["symptoms"]]
                    self.index_display_names = [str(x) for x in data["display_names"]]
                    logger.info(f"[SemanticNLP] Loaded {len(self.index_phrases)} cached vectors.")
                    return
            except Exception as e:
                logger.warning(f"[SemanticNLP] Cache read error ({e}), rebuilding index.")

        self.rebuild_index()

    def _check_freshness(self):
        """Rebuild or reload index if KB or synonyms changed on disk."""
        if self.mode != "semantic" or self.model is None:
            return
        kb_mtime, syn_mtime = self._get_mtimes()
        cached_kb = getattr(self, "_cached_kb_mtime", 0.0)
        cached_syn = getattr(self, "_cached_syn_mtime", 0.0)
        if abs(cached_kb - kb_mtime) >= 1e-4 or abs(cached_syn - syn_mtime) >= 1e-4:
            logger.info("[SemanticNLP] Knowledge base or synonyms updated; refreshing index.")
            self._load_or_build_index()

    def rebuild_index(self):
        """Extract all display names, machine names, and synonyms, then compute embeddings."""
        if self.model is None:
            return

        all_symptoms: List[str] = []
        if os.path.exists(self.kb_path):
            try:
                with open(self.kb_path, "r", encoding="utf-8") as f:
                    kb = json.load(f)
                all_symptoms = kb.get("all_symptoms", [])
            except Exception as e:
                logger.error(f"[SemanticNLP] Could not read KB: {e}")

        synonyms_map: Dict[str, List[str]] = {}
        if os.path.exists(self.synonyms_path):
            try:
                with open(self.synonyms_path, "r", encoding="utf-8") as f:
                    syn_data = json.load(f)
                synonyms_map = syn_data.get("synonyms", {})
            except Exception as e:
                logger.error(f"[SemanticNLP] Could not read synonyms: {e}")

        entries: Dict[str, Tuple[str, str]] = {}

        # 1. From all_symptoms
        for s in all_symptoms:
            s_clean = s.strip().lower()
            disp = s_clean.replace("_", " ").title()
            entries[s_clean] = (s_clean, disp)
            entries[s_clean.replace("_", " ")] = (s_clean, disp)

        # 2. From synonyms.json
        for canonical, phrases in synonyms_map.items():
            canonical_clean = canonical.strip().lower()
            disp = canonical_clean.replace("_", " ").title()
            entries[canonical_clean] = (canonical_clean, disp)
            entries[canonical_clean.replace("_", " ")] = (canonical_clean, disp)
            for p in phrases:
                p_clean = p.strip().lower()
                if p_clean:
                    entries[p_clean] = (canonical_clean, disp)

        phrases = list(entries.keys())
        symptoms = [entries[p][0] for p in phrases]
        display_names = [entries[p][1] for p in phrases]

        # Compute embeddings
        raw_vecs = list(self.model.embed(phrases))
        vectors = np.array(raw_vecs, dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        vectors = vectors / norms

        self.index_phrases = phrases
        self.index_symptoms = symptoms
        self.index_display_names = display_names
        self.index_vectors = vectors

        # Save cache atomically
        kb_mtime, syn_mtime = self._get_mtimes()
        cache_path = os.path.join(self.models_dir, "semantic_index.npz")
        tmp_path = os.path.join(self.models_dir, "semantic_index_tmp.npz")
        try:
            np.savez_compressed(
                tmp_path,
                vectors=vectors,
                phrases=np.array(phrases, dtype=object),
                symptoms=np.array(symptoms, dtype=object),
                display_names=np.array(display_names, dtype=object),
                kb_mtime=np.array(kb_mtime),
                syn_mtime=np.array(syn_mtime),
            )
            os.replace(tmp_path, cache_path)
            logger.info(f"[SemanticNLP] Built and cached {len(phrases)} vector index entries.")
        except Exception as e:
            logger.warning(f"[SemanticNLP] Could not write vector cache: {e}")
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def _extract_dictionary_pass(self, text: str, all_symptoms: List[str]) -> Tuple[Set[str], Set[str], str]:
        """
        Run dictionary pass and return (matched_symptoms, negated_symptoms, remaining_masked_text).
        Longest matching synonym phrases are matched and masked from text first.
        """
        from .nlp import _get_lookup

        text_lower = text.lower()
        lookup = _get_lookup()
        matched = set()
        negated = set()
        consumed = list(text_lower)

        # Sort lookup phrases by length descending
        sorted_phrases = sorted(lookup.keys(), key=lambda x: (len(x.split()), len(x)), reverse=True)

        for phrase in sorted_phrases:
            if phrase in text_lower:
                pattern = re.compile(r"\b" + re.escape(phrase) + r"\b")
                for m in pattern.finditer(text_lower):
                    canonical = lookup[phrase]
                    if _is_negated(text_lower, phrase):
                        negated.add(canonical)
                    else:
                        matched.add(canonical)

                    # Mask matched span
                    for j in range(m.start(), m.end()):
                        consumed[j] = " "

                    # Also mask negation prefix if present
                    for neg in NEGATION_WORDS:
                        pre_start = max(0, m.start() - len(neg))
                        if text_lower[pre_start:m.start()] == neg:
                            for j in range(pre_start, m.start()):
                                consumed[j] = " "

        # Also check canonical symptom names
        for sym in all_symptoms:
            display = sym.replace("_", " ")
            for form in [sym, display]:
                if form in text_lower:
                    pattern = re.compile(r"\b" + re.escape(form) + r"\b")
                    for m in pattern.finditer(text_lower):
                        if _is_negated(text_lower, form):
                            negated.add(sym)
                        else:
                            matched.add(sym)
                        for j in range(m.start(), m.end()):
                            consumed[j] = " "
                        for neg in NEGATION_WORDS:
                            pre_start = max(0, m.start() - len(neg))
                            if text_lower[pre_start:m.start()] == neg:
                                for j in range(pre_start, m.start()):
                                    consumed[j] = " "

        matched -= negated
        remaining_text = "".join(consumed)
        return matched, negated, remaining_text

    def extract_candidate_phrases(self, remaining_text: str) -> List[str]:
        """Generate 1-4 word candidate phrase windows from remaining text after removing stop words."""
        chunks = re.split(r"[,\.;!?]+", remaining_text)
        candidates = []

        for chunk in chunks:
            tokens = [w.strip("'\"") for w in re.findall(r"\b[\w']+\b", chunk)]
            filtered = [w for w in tokens if w not in STOP_WORDS]
            if not filtered:
                continue

            # 1 to 4 word windows
            for n in range(min(4, len(filtered)), 0, -1):
                for i in range(len(filtered) - n + 1):
                    p = " ".join(filtered[i : i + n]).strip()
                    if len(p) >= 2 and p not in candidates:
                        candidates.append(p)

            # Also full chunk trimmed of stop words if >= 2 words
            if len(tokens) >= 2:
                s = 0
                while s < len(tokens) and tokens[s] in STOP_WORDS:
                    s += 1
                e = len(tokens)
                while e > s and tokens[e - 1] in STOP_WORDS:
                    e -= 1
                if e - s >= 2:
                    p = " ".join(tokens[s:e]).strip()
                    if len(p) >= 2 and p not in candidates:
                        candidates.append(p)

        return sorted(candidates, key=lambda x: (len(x.split()), len(x)), reverse=True)

    def extract_symptoms(self, text: str, all_symptoms: List[str]) -> Dict[str, Any]:
        """
        Extract symptoms from free text:
        1. Run existing dictionary & n-gram pass.
        2. For remaining text: generate candidate phrases, embed and match by cosine similarity.
        Thresholds:
          >= 0.75: accepted as matched
          0.55 .. 0.75: suggestions
          < 0.55: unrecognized
        """
        if not text or not text.strip():
            return {
                "matched": [],
                "unrecognized": [],
                "suggestions": [],
                "method": "dictionary",
            }

        self._check_freshness()

        dict_matched, dict_negated, remaining_text = self._extract_dictionary_pass(text, all_symptoms)

        # If semantic model unavailable, return dictionary-only
        if self.mode != "semantic" or self.model is None or self.index_vectors is None or len(self.index_vectors) == 0:
            from .nlp import extract_symptoms as dict_extract
            fallback_res = dict_extract(text, all_symptoms)
            return {
                "matched": fallback_res["matched"],
                "unrecognized": fallback_res["unrecognized"],
                "suggestions": [],
                "method": "dictionary",
            }

        text_lower = text.lower()
        candidates = self.extract_candidate_phrases(remaining_text)

        semantic_matched = set()
        suggestions_by_symptom: Dict[str, Dict[str, Any]] = {}
        unrecognized_words: Set[str] = set()
        covered_tokens: Set[str] = set()

        threshold_match = 0.75
        threshold_sug = 0.55

        if candidates:
            try:
                cand_vecs = np.array(list(self.model.embed(candidates)), dtype=np.float32)
                norms = np.linalg.norm(cand_vecs, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                cand_vecs = cand_vecs / norms

                sims = np.dot(cand_vecs, self.index_vectors.T)

                # Pass 1: Semantic matches (score >= 0.75)
                for cand, row in zip(candidates, sims):
                    cand_tokens = set(cand.split())
                    if cand_tokens.issubset(covered_tokens):
                        continue

                    best_idx = int(np.argmax(row))
                    score = float(row[best_idx])
                    symptom = self.index_symptoms[best_idx]
                    display_name = self.index_display_names[best_idx]

                    # Negation check
                    is_neg = (
                        _is_negated(text_lower, cand)
                        or _is_negated(text_lower, symptom)
                        or _is_negated(text_lower, symptom.replace("_", " "))
                    )
                    if is_neg:
                        dict_negated.add(symptom)
                        continue

                    if symptom in dict_negated:
                        continue

                    if score >= threshold_match:
                        semantic_matched.add(symptom)
                        covered_tokens.update(cand_tokens)

                # Pass 2: Suggestions (0.55 <= score < 0.75)
                for cand, row in zip(candidates, sims):
                    cand_tokens = set(cand.split())
                    if cand_tokens.issubset(covered_tokens):
                        continue

                    best_idx = int(np.argmax(row))
                    score = float(row[best_idx])
                    symptom = self.index_symptoms[best_idx]
                    display_name = self.index_display_names[best_idx]

                    is_neg = (
                        _is_negated(text_lower, cand)
                        or _is_negated(text_lower, symptom)
                        or _is_negated(text_lower, symptom.replace("_", " "))
                    )
                    if is_neg:
                        dict_negated.add(symptom)
                        continue

                    if symptom in dict_negated:
                        continue

                    if threshold_sug <= score < threshold_match:
                        if symptom not in dict_matched and symptom not in semantic_matched:
                            existing = suggestions_by_symptom.get(symptom)
                            if not existing or score > existing["score"]:
                                suggestions_by_symptom[symptom] = {
                                    "phrase": cand,
                                    "symptom": symptom,
                                    "display_name": display_name,
                                    "score": round(score, 3),
                                }
                            covered_tokens.update(cand_tokens)
                    elif score < threshold_sug:
                        for w in cand.split():
                            if w not in STOP_WORDS and len(w) > 3:
                                unrecognized_words.add(w)
            except Exception as e:
                logger.warning(f"[SemanticNLP] Error during semantic embedding/matching: {e}")

        # Remove symptoms that ended up in matched from suggestions
        all_matched = (dict_matched | semantic_matched) - dict_negated
        for s in all_matched:
            suggestions_by_symptom.pop(s, None)

        suggestions = sorted(suggestions_by_symptom.values(), key=lambda x: x["score"], reverse=True)

        # Collect unrecognized words from remaining text not covered by any match or suggestion
        for w in re.findall(r"\b[\w']+\b", remaining_text):
            if w not in STOP_WORDS and len(w) > 3:
                if not any(w in s for s in all_matched) and not any(w in sug["phrase"] for sug in suggestions):
                    unrecognized_words.add(w)

        # Determine method
        has_dict = len(dict_matched) > 0
        has_sem = len(semantic_matched) > 0 or len(suggestions) > 0
        if has_dict and has_sem:
            method = "hybrid"
        elif has_sem:
            method = "semantic"
        else:
            method = "dictionary"

        return {
            "matched": sorted(all_matched),
            "unrecognized": sorted(unrecognized_words)[:10],
            "suggestions": suggestions[:5],
            "method": method,
        }


# Singleton instance
_EXTRACTOR: Optional[SemanticSymptomExtractor] = None


def get_semantic_extractor() -> SemanticSymptomExtractor:
    global _EXTRACTOR
    if _EXTRACTOR is None:
        _EXTRACTOR = SemanticSymptomExtractor()
    return _EXTRACTOR


def get_nlp_mode() -> str:
    extractor = get_semantic_extractor()
    return extractor.mode


def extract_symptoms(text: str, all_symptoms: List[str]) -> Dict[str, Any]:
    extractor = get_semantic_extractor()
    return extractor.extract_symptoms(text, all_symptoms)
