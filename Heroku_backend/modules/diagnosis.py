"""
diagnosis.py — Core diagnostic logic and engine interface.

DiagnosisEngine is the interface. At startup, try ClipsEngine;
fall back to PythonFallbackEngine if clips is unavailable.
"""
import json
import logging
import math
import os
import shutil
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from .models import DiagnosisResult, Disease

logger = logging.getLogger(__name__)

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_PATH = os.path.join(BACKEND_DIR, "data", "knowledge_base.json")
CLP_PATH = os.path.join(BACKEND_DIR, "data", "disease-symptoms.clp")
KB_VERSIONS_DIR = os.path.join(BACKEND_DIR, "data", "kb_versions")
CHANGE_LOG_PATH = os.path.join(BACKEND_DIR, "data", "change_log.json")
SYNONYMS_PATH = os.path.join(BACKEND_DIR, "data", "synonyms.json")
DISCLAIMER = (
    "⚠️ MEDICAL DISCLAIMER: This tool provides preliminary guidance only "
    "and is NOT a substitute for professional medical advice, diagnosis, or treatment. "
    "Always consult a qualified healthcare professional."
)


def _confidence_label(confidence: float) -> str:
    if confidence >= 0.7:
        return "High"
    elif confidence >= 0.4:
        return "Moderate"
    return "Low"


class DiagnosisEngine:
    """
    Unified diagnosis engine. Wraps ClipsEngine or PythonFallbackEngine.
    Single instance, thread-safe KB reload.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._kb: Dict[str, Any] = {}
        self._diseases: List[Dict[str, Any]] = []
        self._symptom_weights: Dict[str, float] = {}
        self._engine_name: str = "python-fallback"
        self._engine = None
        self._kb_version: str = ""

        # Load KB and generate CLP
        self._load_kb()
        self._init_engine()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _load_kb(self):
        """Load knowledge_base.json and compute symptom weights."""
        with open(KB_PATH, "r", encoding="utf-8") as f:
            self._kb = json.load(f)
        self._diseases = self._kb.get("diseases", [])
        self._kb_version = self._kb.get("_meta", {}).get("version", "unknown")
        self._compute_symptom_weights()
        logger.info(f"[DiagnosisEngine] KB loaded: {len(self._diseases)} diseases.")

    def _compute_symptom_weights(self):
        """
        Inverse frequency weighting: rarer symptoms across the KB get higher weight.
        weight(s) = log(N / df(s) + 1)
        """
        N = len(self._diseases)
        freq: Dict[str, int] = {}
        for d in self._diseases:
            for s in d.get("symptoms", []):
                freq[s] = freq.get(s, 0) + 1
        self._symptom_weights = {
            s: math.log(N / (df + 1) + 1)
            for s, df in freq.items()
        }

    def _init_engine(self):
        """Try ClipsEngine; fall back to PythonFallbackEngine."""
        from .clips_engine import ClipsEngine, CLIPS_AVAILABLE
        from .fallback_engine import PythonFallbackEngine

        if CLIPS_AVAILABLE:
            try:
                self._engine = ClipsEngine(CLP_PATH)
                self._engine_name = "clips"
                logger.info("[DiagnosisEngine] Using CLIPS engine.")
                return
            except Exception as e:
                logger.warning(f"[DiagnosisEngine] CLIPS init failed: {e}. Using fallback.")

        self._engine = PythonFallbackEngine(self._diseases)
        self._engine_name = "python-fallback"
        logger.warning("[DiagnosisEngine] Using Python fallback engine.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def engine_name(self) -> str:
        return self._engine_name

    @property
    def kb_version(self) -> str:
        return self._kb_version

    @property
    def disease_count(self) -> int:
        return len(self._diseases)

    @property
    def symptom_count(self) -> int:
        return len(self._kb.get("all_symptoms", []))

    def get_all_symptoms_by_category(self) -> Dict[str, List[str]]:
        return self._kb.get("symptom_categories", {})

    def get_all_diseases(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [d for d in self._diseases]

    def get_disease_by_id(self, disease_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for d in self._diseases:
                if d["id"] == disease_id:
                    return d
        return None

    def diagnose(self, selected_symptoms: List[str], denied_symptoms: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Main diagnosis function.
        Returns full response dict compatible with /api/diagnose.
        """
        if denied_symptoms is None:
            denied_symptoms = []

        selected_clean = [str(s).strip().lower() for s in selected_symptoms if s]
        selected_set = set(selected_clean)

        known_symptoms = set(self._kb.get("all_symptoms", [])) | set(self._symptom_weights.keys())
        cleaned_denied = []
        for s in denied_symptoms:
            s_norm = str(s).strip().lower()
            if s_norm and s_norm in known_symptoms and s_norm not in selected_set and s_norm not in cleaned_denied:
                cleaned_denied.append(s_norm)
            if len(cleaned_denied) >= 50:
                break

        if not selected_clean:
            return {
                "possible_diseases": [],
                "remaining_symptoms": [],
                "final_diagnosis": None,
                "emergency_flags": [],
                "disclaimer": DISCLAIMER,
                "next_steps": "Please select or describe your symptoms to begin.",
                "engine": self._engine_name,
                "denied_symptoms": cleaned_denied,
            }

        with self._lock:
            engine_result = self._engine.run(selected_clean)
            candidates_raw = engine_result.get("candidates", [])
            emergencies = engine_result.get("emergencies", [])

            # Build detailed diagnosis results with weighted confidence
            possible_diseases = self._calculate_disease_matches(selected_clean, candidates_raw, cleaned_denied)

            # Sort by weighted confidence descending
            possible_diseases.sort(key=lambda x: x["confidence"], reverse=True)

            # Remaining symptoms (ranked by info gain)
            remaining = self._filter_remaining_symptoms(selected_clean, possible_diseases, cleaned_denied)

            # Final diagnosis (if strong single candidate or user finished)
            final_diagnosis = None
            if possible_diseases:
                top = possible_diseases[0]
                if top["confidence"] >= 0.7:
                    disease_full = self.get_disease_by_id(top["id"])
                    if disease_full:
                        final_diagnosis = {**top}
                        final_diagnosis["description"] = disease_full.get("description", "")
                        final_diagnosis["next_steps"] = disease_full.get("next_steps", "")
                        final_diagnosis["homeopathic_remedies"] = disease_full.get("homeopathic_remedies", [])
                        final_diagnosis["remedies_disclaimer"] = disease_full.get("remedies_disclaimer", "")

            # Next steps text
            next_steps = self._build_next_steps(possible_diseases, emergencies)

            return {
                "possible_diseases": possible_diseases,
                "remaining_symptoms": remaining,
                "final_diagnosis": final_diagnosis,
                "emergency_flags": emergencies,
                "disclaimer": DISCLAIMER,
                "next_steps": next_steps,
                "engine": self._engine_name,
                "denied_symptoms": cleaned_denied,
            }

    def _calculate_disease_matches(
        self, selected_symptoms: List[str], candidates_raw: List[Dict], denied_symptoms: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Build detailed match results with weighted confidence scores.
        """
        symptom_set = set(s.lower() for s in selected_symptoms)
        results = []

        # Build a lookup for full disease data
        disease_lookup = {d["id"]: d for d in self._diseases}

        for cand in candidates_raw:
            did = cand["id"]
            disease = disease_lookup.get(did)
            if not disease:
                continue

            disease_symptoms = set(s.lower() for s in disease.get("symptoms", []))
            matched = symptom_set & disease_symptoms
            missing = disease_symptoms - symptom_set
            total = len(disease_symptoms)

            # Weighted confidence: sum of weights of matched / sum of weights of all disease symptoms
            w_matched = sum(self._symptom_weights.get(s, 1.0) for s in matched)
            w_total = sum(self._symptom_weights.get(s, 1.0) for s in disease_symptoms)
            confidence = w_matched / w_total if w_total > 0 else 0.0

            denied_hits = [s for s in (denied_symptoms or []) if s in disease_symptoms]
            denied_weight = sum(self._symptom_weights.get(s, 1.0) for s in denied_hits)
            penalty = min(0.4, denied_weight / w_total) if w_total > 0 else 0.0
            adjusted_confidence = confidence * (1.0 - penalty)

            results.append({
                "name": disease["name"],
                "id": disease["id"],
                "category": disease.get("category", ""),
                "severity": disease.get("severity", "mild"),
                "confidence": round(adjusted_confidence, 4),
                "label": _confidence_label(adjusted_confidence),
                "matched_symptoms": sorted(matched),
                "missing_symptoms": sorted(missing),
                "denied_symptoms_hit": sorted(denied_hits),
                "total_symptoms": total,
                "description": disease.get("description", ""),
                "recommended_action": disease.get("recommended_action", ""),
                "next_steps": disease.get("next_steps", ""),
                "homeopathic_remedies": disease.get("homeopathic_remedies", []),
                "remedies_disclaimer": disease.get("remedies_disclaimer", ""),
            })

        return results

    def _filter_remaining_symptoms(
        self, selected_symptoms: List[str], possible_diseases: List[Dict], denied_symptoms: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Return remaining (unselected and not denied) symptoms that appear in still-possible diseases,
        ranked by information gain (how well they split the candidate set).
        """
        if not possible_diseases:
            # Return all symptoms grouped
            return []

        selected_set = set(s.lower() for s in selected_symptoms)
        denied_set = set(s.lower() for s in (denied_symptoms or []))
        exclude_set = selected_set | denied_set
        # Only consider diseases with confidence > 0
        candidate_count = len(possible_diseases)

        # Gather all symptoms from possible diseases
        symptom_freq: Dict[str, int] = {}
        for d in possible_diseases:
            for s in d.get("matched_symptoms", []) + d.get("missing_symptoms", []):
                if s not in exclude_set:
                    symptom_freq[s] = symptom_freq.get(s, 0) + 1

        # Information gain approximation: symptom that splits candidates ~50/50
        # Score = -|freq/N - 0.5| (closer to 0.5 = better split)
        ranked = []
        for sym, freq in symptom_freq.items():
            ratio = freq / candidate_count
            info_gain = 1.0 - abs(ratio - 0.5) * 2  # 1.0 = perfect split, 0.0 = useless
            ranked.append({
                "name": sym,
                "display_name": sym.replace("_", " ").title(),
                "frequency": freq,
                "info_gain": round(info_gain, 4),
            })

        ranked.sort(key=lambda x: x["info_gain"], reverse=True)
        return ranked[:15]  # Top 15 follow-up suggestions

    def _build_next_steps(self, possible_diseases: List[Dict], emergencies: List[Dict]) -> str:
        if emergencies:
            return "🚨 EMERGENCY: " + emergencies[0]["message"]
        if not possible_diseases:
            return "No matching conditions found. Please describe more symptoms or consult a doctor."
        top = possible_diseases[0]
        if top["label"] == "High":
            return f"Top match: {top['name']}. {top.get('next_steps', 'Consult a healthcare professional.')}"
        elif top["label"] == "Moderate":
            return "Moderate confidence match. Please add more symptoms for a better diagnosis, or consult a doctor."
        return "Low confidence. Please describe more symptoms or consult a healthcare professional."

    # ------------------------------------------------------------------
    # Knowledge Base management
    # ------------------------------------------------------------------

    def reload_disease_symptoms(self):
        """Thread-safe KB reload. Backs up and regenerates CLP."""
        with self._lock:
            self._backup_kb()
            self._load_kb()
            self._regenerate_clp()
            # Update engine data
            from .fallback_engine import PythonFallbackEngine
            from .clips_engine import ClipsEngine, CLIPS_AVAILABLE
            if self._engine_name == "python-fallback":
                self._engine = PythonFallbackEngine(self._diseases)
            elif CLIPS_AVAILABLE:
                try:
                    self._engine = ClipsEngine(CLP_PATH)
                except Exception as e:
                    logger.warning(f"[DiagnosisEngine] CLIPS reload failed: {e}")
                    self._engine = PythonFallbackEngine(self._diseases)
                    self._engine_name = "python-fallback"
        logger.info("[DiagnosisEngine] KB reloaded successfully.")

    def _backup_kb(self):
        """Write a versioned backup to data/kb_versions/."""
        os.makedirs(KB_VERSIONS_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(KB_VERSIONS_DIR, f"knowledge_base_{ts}.json")
        n = 2
        while os.path.exists(backup_path):      # never overwrite an earlier backup made in the same second
            backup_path = os.path.join(KB_VERSIONS_DIR, f"knowledge_base_{ts}_{n}.json")
            n += 1
        shutil.copy2(KB_PATH, backup_path)
        if os.path.exists(SYNONYMS_PATH):
            syn_backup = backup_path.replace("knowledge_base_", "synonyms_")
            shutil.copy2(SYNONYMS_PATH, syn_backup)
        logger.info(f"[DiagnosisEngine] KB backed up to {backup_path}")
        return backup_path

    def _regenerate_clp(self, strict: bool = False):
        """Regenerate the CLIPS file from the updated KB. strict=True re-raises errors."""
        try:
            import sys
            sys.path.insert(0, BACKEND_DIR)
            from generate_clp import generate_clp
            generate_clp(KB_PATH, CLP_PATH)
        except Exception as e:
            logger.error(f"[DiagnosisEngine] CLP regeneration failed: {e}")
            if strict:
                raise

    def _write_kb_atomic(self, new_kb: Dict):
        """Atomic KB write: write to temp, then rename."""
        tmp_path = KB_PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(new_kb, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, KB_PATH)

    def _write_synonyms_atomic(self, syn_data: Dict):
        """Atomic synonyms write: write to temp, then rename."""
        tmp_path = SYNONYMS_PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(syn_data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, SYNONYMS_PATH)

    def add_disease(self, disease_data: Dict) -> Tuple[bool, str]:
        """Add a new disease to the KB."""
        with self._lock:
            # Validation
            required = ["id", "name", "category", "severity", "symptoms", "description", "recommended_action"]
            for field in required:
                if field not in disease_data:
                    return False, f"Missing required field: {field}"

            existing_ids = {d["id"] for d in self._diseases}
            if disease_data["id"] in existing_ids:
                return False, f"Disease with id '{disease_data['id']}' already exists"

            self._backup_kb()
            self._kb["diseases"].append(disease_data)
            self._kb["_meta"]["disease_count"] = len(self._kb["diseases"])
            self._write_kb_atomic(self._kb)
            self._load_kb()
            self._regenerate_clp()
            self._update_fallback_engine()
            return True, "Disease added successfully"

    def update_disease(self, disease_id: str, updates: Dict) -> Tuple[bool, str]:
        """Update an existing disease."""
        with self._lock:
            for i, d in enumerate(self._kb["diseases"]):
                if d["id"] == disease_id:
                    self._backup_kb()
                    self._kb["diseases"][i].update(updates)
                    self._write_kb_atomic(self._kb)
                    self._load_kb()
                    self._regenerate_clp()
                    self._update_fallback_engine()
                    return True, "Disease updated successfully"
            return False, f"Disease '{disease_id}' not found"

    def delete_disease(self, disease_id: str) -> Tuple[bool, str]:
        """Delete a disease from the KB."""
        with self._lock:
            original = len(self._kb["diseases"])
            self._kb["diseases"] = [d for d in self._kb["diseases"] if d["id"] != disease_id]
            if len(self._kb["diseases"]) == original:
                return False, f"Disease '{disease_id}' not found"
            self._backup_kb()
            self._kb["_meta"]["disease_count"] = len(self._kb["diseases"])
            self._write_kb_atomic(self._kb)
            self._load_kb()
            self._regenerate_clp()
            self._update_fallback_engine()
            return True, "Disease deleted successfully"

    def add_symptom(self, symptom_name: str, category: str) -> Tuple[bool, str]:
        """Add a new symptom to the KB."""
        with self._lock:
            all_symptoms = self._kb.get("all_symptoms", [])
            if symptom_name in all_symptoms:
                return False, f"Symptom '{symptom_name}' already exists"
            self._backup_kb()
            self._kb.setdefault("all_symptoms", []).append(symptom_name)
            cats = self._kb.setdefault("symptom_categories", {})
            cats.setdefault(category, []).append(symptom_name)
            self._write_kb_atomic(self._kb)
            self._load_kb()
            return True, "Symptom added successfully"

    def delete_symptom(self, symptom_name: str) -> Tuple[bool, str]:
        """Delete a symptom and cascade-update all diseases that reference it."""
        with self._lock:
            all_symptoms = self._kb.get("all_symptoms", [])
            if symptom_name not in all_symptoms:
                return False, f"Symptom '{symptom_name}' not found"
            self._backup_kb()
            self._kb["all_symptoms"] = [s for s in all_symptoms if s != symptom_name]
            for cat in self._kb.get("symptom_categories", {}).values():
                if symptom_name in cat:
                    cat.remove(symptom_name)
            for disease in self._kb["diseases"]:
                if symptom_name in disease.get("symptoms", []):
                    disease["symptoms"].remove(symptom_name)
            self._write_kb_atomic(self._kb)
            self._load_kb()
            self._regenerate_clp()
            self._update_fallback_engine()
            return True, f"Symptom '{symptom_name}' deleted and cascaded"

    def get_kb_versions(self) -> List[Dict[str, str]]:
        """List all KB backup versions."""
        os.makedirs(KB_VERSIONS_DIR, exist_ok=True)
        files = sorted(os.listdir(KB_VERSIONS_DIR), reverse=True)
        versions = []
        for f in files:
            if f.endswith(".json"):
                path = os.path.join(KB_VERSIONS_DIR, f)
                size = os.path.getsize(path)
                versions.append({
                    "filename": f,
                    "path": path,
                    "size_bytes": size,
                    "created": f.replace("knowledge_base_", "").replace(".json", ""),
                })
        return versions

    # ------------------------------------------------------------------
    # Doctor Portal: whole-table save / revert (reuses the helpers above)
    # ------------------------------------------------------------------

    def _smoke_test(self):
        """Run one diagnosis through the live engine; raises if the rules are broken."""
        if self._engine_name == "clips":
            from .clips_engine import ClipsEngine
            ClipsEngine(CLP_PATH).run(["fever"])
        else:
            self._engine.run(["fever"])

    def _rebuild_everything(self):
        """KB file already written -> reload data, rebuild CLP, refresh engines, smoke test."""
        self._load_kb()
        self._regenerate_clp(strict=True)
        self._update_fallback_engine()
        self._smoke_test()

    def _load_changelog(self) -> List[Dict[str, Any]]:
        if not os.path.isfile(CHANGE_LOG_PATH):
            return []
        try:
            with open(CHANGE_LOG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"[DiagnosisEngine] Could not load change_log.json: {e}")
            return []

    def _append_changelog(self, entry: Dict[str, Any]):
        try:
            entries = self._load_changelog()
            entries.append(entry)
            entries = entries[-200:]
            tmp_path = CHANGE_LOG_PATH + ".tmp"
            os.makedirs(os.path.dirname(CHANGE_LOG_PATH), exist_ok=True)
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, CHANGE_LOG_PATH)
        except Exception as e:
            logger.error(f"[DiagnosisEngine] Failed to append to change_log.json: {e}", exc_info=True)

    def get_changelog(self, limit: int = 200) -> List[Dict[str, Any]]:
        with self._lock:
            entries = self._load_changelog()
            return list(reversed(entries))[:limit]

    def _diff_and_tag_diseases(
        self, old_diseases: List[Dict], new_diseases: List[Dict], edited_by: str, saved_at: str
    ) -> Tuple[List[Dict], List[Dict[str, Any]]]:
        old_by_id = {d["id"]: d for d in old_diseases if "id" in d}
        new_ids = set()
        changes: List[Dict[str, Any]] = []
        tagged_new: List[Dict[str, Any]] = []

        for d in new_diseases:
            d_copy = dict(d)
            did = d_copy.get("id")
            if did:
                new_ids.add(did)
            old_d = old_by_id.get(did) if did else None

            if not old_d:
                d_copy["last_edited_by"] = edited_by
                d_copy["last_edited_at"] = saved_at
                changes.append({
                    "type": "added",
                    "disease": d_copy.get("name", "Unknown"),
                    "details": f"Added disease with {len(d_copy.get('symptoms', []))} symptoms",
                })
            else:
                field_diffs = []
                for field in ["name", "category", "severity", "recommended_action", "description", "next_steps", "icd10"]:
                    old_val = (old_d.get(field) or "").strip() if isinstance(old_d.get(field), str) else old_d.get(field, "")
                    new_val = (d_copy.get(field) or "").strip() if isinstance(d_copy.get(field), str) else d_copy.get(field, "")
                    if old_val != new_val:
                        field_diffs.append(f"{field}: '{old_val}' → '{new_val}'")

                old_syms = set(old_d.get("symptoms", []))
                new_syms = set(d_copy.get("symptoms", []))
                added_syms = new_syms - old_syms
                removed_syms = old_syms - new_syms
                if added_syms:
                    field_diffs.append(f"symptoms added: {', '.join(sorted(added_syms))}")
                if removed_syms:
                    field_diffs.append(f"symptoms removed: {', '.join(sorted(removed_syms))}")

                old_rem = [r.strip() for r in old_d.get("homeopathic_remedies", []) if isinstance(r, str)]
                new_rem = [r.strip() for r in d_copy.get("homeopathic_remedies", []) if isinstance(r, str)]
                if old_rem != new_rem:
                    field_diffs.append("homeopathic remedies updated")

                if field_diffs:
                    d_copy["last_edited_by"] = edited_by
                    d_copy["last_edited_at"] = saved_at
                    changes.append({
                        "type": "edited",
                        "disease": d_copy.get("name", old_d.get("name", "Unknown")),
                        "details": "; ".join(field_diffs),
                    })
                else:
                    if "last_edited_by" in old_d and "last_edited_by" not in d_copy:
                        d_copy["last_edited_by"] = old_d["last_edited_by"]
                    if "last_edited_at" in old_d and "last_edited_at" not in d_copy:
                        d_copy["last_edited_at"] = old_d["last_edited_at"]

            tagged_new.append(d_copy)

        for old_id, old_d in old_by_id.items():
            if old_id not in new_ids:
                changes.append({
                    "type": "deleted",
                    "disease": old_d.get("name", old_id),
                    "details": "Disease removed",
                })

        return tagged_new, changes

    def replace_all_diseases(self, diseases: List[Dict], edited_by: str = "") -> Dict[str, Any]:
        """
        Save a full edited disease list. Backs up first; if anything fails after the
        file is written, the backup is restored and the error re-raised.
        """
        with self._lock:
            backup_path = self._backup_kb()
            try:
                saved_at = datetime.now().isoformat(timespec="seconds")
                clean_editor = (edited_by or "").strip()[:80]
                tagged_diseases, changes = self._diff_and_tag_diseases(
                    self._diseases, diseases, clean_editor, saved_at
                )
                new_kb = json.loads(json.dumps(self._kb))        # deep copy
                new_kb["diseases"] = tagged_diseases
                meta = new_kb.setdefault("_meta", {})
                meta["disease_count"] = len(tagged_diseases)
                meta["version"] = self._next_version(meta.get("version", "1.0.0"))
                meta["last_edited_by"] = clean_editor
                meta["saved_at"] = saved_at
                self._write_kb_atomic(new_kb)
                self._rebuild_everything()
                self._append_changelog({
                    "version": meta["version"],
                    "saved_at": saved_at,
                    "edited_by": clean_editor,
                    "backup_file": os.path.basename(backup_path),
                    "changes": changes,
                })
            except Exception:
                logger.error("[DiagnosisEngine] Save failed; restoring backup", exc_info=True)
                self._restore_file(backup_path)
                raise
            m = self._kb["_meta"]
            return {"version": m["version"], "disease_count": len(self._diseases),
                    "saved_at": m["saved_at"], "backup": os.path.basename(backup_path)}

    def revert_to_version(self, filename: str, edited_by: str = "Doctor") -> Dict[str, Any]:
        """Restore a backup from data/kb_versions (current state is backed up first)."""
        safe = os.path.basename(filename)
        src = os.path.join(KB_VERSIONS_DIR, safe)
        if safe != filename or not safe.endswith(".json") or not os.path.isfile(src):
            raise FileNotFoundError(f"Version '{filename}' not found")
        with self._lock:
            backup_path = self._backup_kb()
            try:
                shutil.copy2(src, KB_PATH + ".tmp")
                os.replace(KB_PATH + ".tmp", KB_PATH)
                self._rebuild_everything()
            except Exception:
                logger.error("[DiagnosisEngine] Revert failed; restoring previous KB", exc_info=True)
                self._restore_file(backup_path)
                raise
            m = self._kb.get("_meta", {})
            restored_version = m.get("version", "")
            saved_at = datetime.now().isoformat(timespec="seconds")
            clean_editor = (edited_by or "Doctor").strip()[:80]
            self._append_changelog({
                "version": restored_version,
                "saved_at": saved_at,
                "edited_by": clean_editor,
                "backup_file": safe,
                "changes": [{
                    "type": "reverted",
                    "disease": "All",
                    "details": f"Restored version {restored_version} from {safe}"
                }]
            })
            return {"version": restored_version, "disease_count": len(self._diseases),
                    "restored_from": safe}

    def _restore_file(self, backup_path: str):
        """Put a backup back as the live KB and rebuild everything (best effort)."""
        shutil.copy2(backup_path, KB_PATH + ".tmp")
        os.replace(KB_PATH + ".tmp", KB_PATH)
        syn_backup = backup_path.replace("knowledge_base_", "synonyms_")
        if os.path.exists(syn_backup) and os.path.exists(SYNONYMS_PATH):
            shutil.copy2(syn_backup, SYNONYMS_PATH + ".tmp")
            os.replace(SYNONYMS_PATH + ".tmp", SYNONYMS_PATH)
        try:
            self._load_kb()
            self._regenerate_clp()
            self._update_fallback_engine()
            from . import nlp
            nlp.reload_synonyms()
        except Exception:
            logger.error("[DiagnosisEngine] Restore rebuild failed", exc_info=True)

    def add_symptom_full(
        self, machine_name: str, display_name: str, category: str,
        synonyms: List[str], edited_by: str
    ) -> Dict[str, Any]:
        with self._lock:
            backup_path = self._backup_kb()
            try:
                new_kb = json.loads(json.dumps(self._kb))
                all_symptoms = new_kb.setdefault("all_symptoms", [])
                if machine_name not in all_symptoms:
                    all_symptoms.append(machine_name)
                    all_symptoms.sort()
                cats = new_kb.setdefault("symptom_categories", {})
                cat_list = cats.setdefault(category, [])
                if machine_name not in cat_list:
                    cat_list.append(machine_name)
                    cat_list.sort()

                meta = new_kb.setdefault("_meta", {})
                meta["symptom_count"] = len(all_symptoms)
                saved_at = datetime.now().isoformat(timespec="seconds")
                clean_editor = (edited_by or "").strip()[:80]
                meta["last_edited_by"] = clean_editor
                meta["saved_at"] = saved_at
                meta["version"] = self._next_version(meta.get("version", "1.0.0"))

                syn_data = {}
                if os.path.exists(SYNONYMS_PATH):
                    try:
                        with open(SYNONYMS_PATH, "r", encoding="utf-8") as f:
                            syn_data = json.load(f)
                    except Exception:
                        syn_data = {}
                syn_dict = syn_data.setdefault("synonyms", {})
                existing_phrases = syn_dict.get(machine_name, [])
                new_phrases = set(existing_phrases)
                new_phrases.add(display_name.lower().strip())
                for s in synonyms:
                    if isinstance(s, str) and s.strip():
                        new_phrases.add(s.lower().strip())
                syn_dict[machine_name] = sorted(new_phrases)

                self._write_kb_atomic(new_kb)
                self._write_synonyms_atomic(syn_data)
                self._rebuild_everything()

                from . import nlp
                nlp.reload_synonyms()

                self._append_changelog({
                    "version": meta["version"],
                    "saved_at": saved_at,
                    "edited_by": clean_editor,
                    "backup_file": os.path.basename(backup_path),
                    "changes": [{
                        "type": "symptom_added",
                        "disease": display_name,
                        "details": f"Added symptom '{machine_name}' in category '{category}'"
                    }]
                })
            except Exception:
                logger.error("[DiagnosisEngine] add_symptom_full failed; restoring backup", exc_info=True)
                self._restore_file(backup_path)
                raise

            return {
                "name": machine_name,
                "display_name": display_name,
                "category": category,
                "version": self._kb.get("_meta", {}).get("version", "")
            }

    def delete_symptom_full(self, machine_name: str, edited_by: str = "Doctor") -> Dict[str, Any]:
        with self._lock:
            backup_path = self._backup_kb()
            try:
                new_kb = json.loads(json.dumps(self._kb))
                all_symptoms = new_kb.get("all_symptoms", [])
                if machine_name in all_symptoms:
                    all_symptoms.remove(machine_name)
                for cat_list in new_kb.get("symptom_categories", {}).values():
                    if machine_name in cat_list:
                        cat_list.remove(machine_name)

                meta = new_kb.setdefault("_meta", {})
                meta["symptom_count"] = len(all_symptoms)
                saved_at = datetime.now().isoformat(timespec="seconds")
                clean_editor = (edited_by or "Doctor").strip()[:80]
                meta["last_edited_by"] = clean_editor
                meta["saved_at"] = saved_at
                meta["version"] = self._next_version(meta.get("version", "1.0.0"))

                syn_data = {}
                if os.path.exists(SYNONYMS_PATH):
                    try:
                        with open(SYNONYMS_PATH, "r", encoding="utf-8") as f:
                            syn_data = json.load(f)
                    except Exception:
                        syn_data = {}
                syn_dict = syn_data.get("synonyms", {})
                if machine_name in syn_dict:
                    del syn_dict[machine_name]

                self._write_kb_atomic(new_kb)
                self._write_synonyms_atomic(syn_data)
                self._rebuild_everything()

                from . import nlp
                nlp.reload_synonyms()

                self._append_changelog({
                    "version": meta["version"],
                    "saved_at": saved_at,
                    "edited_by": clean_editor,
                    "backup_file": os.path.basename(backup_path),
                    "changes": [{
                        "type": "symptom_deleted",
                        "disease": machine_name,
                        "details": f"Deleted symptom '{machine_name}'"
                    }]
                })
            except Exception:
                logger.error("[DiagnosisEngine] delete_symptom_full failed; restoring backup", exc_info=True)
                self._restore_file(backup_path)
                raise

            return {
                "name": machine_name,
                "version": self._kb.get("_meta", {}).get("version", "")
            }

    @staticmethod
    def _next_version(v: str) -> str:
        parts = str(v).split(".")
        try:
            parts[-1] = str(int(parts[-1]) + 1)
            return ".".join(parts)
        except ValueError:
            return "1.0.1"

    def list_versions(self, limit: int = 20) -> List[Dict[str, Any]]:
        os.makedirs(KB_VERSIONS_DIR, exist_ok=True)
        files = sorted((f for f in os.listdir(KB_VERSIONS_DIR) if f.startswith("knowledge_base_") and f.endswith(".json")),
                       key=lambda f: os.path.getmtime(os.path.join(KB_VERSIONS_DIR, f)), reverse=True)[:limit]
        out = []
        for f in files:
            path = os.path.join(KB_VERSIONS_DIR, f)
            meta, count = {}, None
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    kb = json.load(fh)
                meta = kb.get("_meta", {})
                count = len(kb.get("diseases", []))
            except Exception:
                pass
            ts = f.replace("knowledge_base_", "").replace(".json", "")[:15]
            try:
                ts = datetime.strptime(ts, "%Y%m%d_%H%M%S").isoformat(timespec="seconds")
            except ValueError:
                pass
            out.append({"filename": f, "backed_up_at": ts, "version": meta.get("version", ""),
                        "edited_by": meta.get("last_edited_by", ""), "disease_count": count})
        return out

    def _update_fallback_engine(self):
        if self._engine_name == "python-fallback":
            from .fallback_engine import PythonFallbackEngine
            self._engine = PythonFallbackEngine(self._diseases)


# Singleton instance
_engine_instance: Optional[DiagnosisEngine] = None
_engine_lock = threading.Lock()


def get_engine() -> DiagnosisEngine:
    global _engine_instance
    if _engine_instance is None:
        with _engine_lock:
            if _engine_instance is None:
                _engine_instance = DiagnosisEngine()
    return _engine_instance
