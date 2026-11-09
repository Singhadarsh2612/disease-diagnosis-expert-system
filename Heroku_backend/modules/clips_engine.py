"""
clips_engine.py — Wrapper around clipspy for CLIPS-based inference.
Falls back gracefully if clipspy is not available.
"""
import logging
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    import clips  # clipspy
    CLIPS_AVAILABLE = True
except ImportError:
    CLIPS_AVAILABLE = False
    logger.warning(
        "[ClipsEngine] clipspy not found. CLIPS engine disabled. "
        "Using PythonFallbackEngine instead. "
        "Install with: pip install clipspy"
    )


class ClipsEngine:
    """
    Wraps clipspy to run the CLIPS forward-chaining rules.
    Creates a fresh CLIPS environment per request (stateless).
    """

    ENGINE_NAME = "clips"

    def __init__(self, clp_path: str):
        if not CLIPS_AVAILABLE:
            raise ImportError("clipspy is not installed")
        if not os.path.exists(clp_path):
            raise FileNotFoundError(f"CLIPS rule file not found: {clp_path}")
        self.clp_path = clp_path

    @classmethod
    def is_available(cls) -> bool:
        return CLIPS_AVAILABLE

    def run(self, selected_symptoms: List[str]) -> Dict[str, Any]:
        """
        Creates a fresh CLIPS environment, loads the .clp file,
        asserts symptom facts, runs the inference, and collects results.
        Returns same structure as PythonFallbackEngine.run()
        """
        if not CLIPS_AVAILABLE:
            raise RuntimeError("clipspy is not installed")

        env = clips.Environment()
        try:
            # Load the CLIPS rules/facts
            env.load(self.clp_path)

            # Reset to load deffacts
            env.reset()

            # Assert user symptoms
            symptom_template = env.find_template("symptom")
            for sym in selected_symptoms:
                fact = symptom_template.assert_fact(name=clips.Symbol(sym.lower()))

            # Run the inference engine
            env.run()

            # Collect results
            candidates = []
            confirmed = []
            emergencies = []

            for fact in env.facts():
                template_name = fact.template.name if fact.template else None

                if template_name == "candidate":
                    try:
                        candidates.append({
                            "name": str(fact["name"]),
                            "id": str(fact["id"]),
                            "matched": int(fact["matched"]),
                            "total": int(fact["total"]),
                            "category": str(fact["category"]),
                            "severity": str(fact["severity"]),
                        })
                    except Exception as e:
                        logger.warning(f"[ClipsEngine] Error reading candidate fact: {e}")

                elif template_name == "confirmed-disease":
                    try:
                        confirmed.append({
                            "name": str(fact["name"]),
                            "id": str(fact["id"]),
                            "confidence": float(fact["confidence"]),
                        })
                    except Exception as e:
                        logger.warning(f"[ClipsEngine] Error reading confirmed fact: {e}")

                elif template_name == "emergency":
                    try:
                        emergencies.append({"message": str(fact["message"])})
                    except Exception as e:
                        logger.warning(f"[ClipsEngine] Error reading emergency fact: {e}")

            return {
                "candidates": candidates,
                "confirmed": confirmed,
                "emergencies": emergencies,
                "engine": self.ENGINE_NAME,
            }

        except Exception as e:
            logger.error(f"[ClipsEngine] Error during inference: {e}", exc_info=True)
            raise
        finally:
            # Ensure environment is cleaned up
            try:
                env.clear()
            except Exception:
                pass
