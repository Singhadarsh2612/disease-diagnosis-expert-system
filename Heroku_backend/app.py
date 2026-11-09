"""
app.py — Flask application entry point.
"""
import logging
import os
import sys

from flask import Flask
from flask_cors import CORS

# Ensure we can import from the Heroku_backend directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging before anything else
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("[App] .env loaded")
except ImportError:
    logger.warning("[App] python-dotenv not installed; skipping .env load")


def create_app() -> Flask:
    app = Flask(__name__)

    # Config
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload limit
    app.config["JSON_SORT_KEYS"] = False

    # CORS
    cors_origins = os.environ.get("CORS_ORIGINS", "*")
    CORS(app, resources={r"/api/*": {"origins": cors_origins}},
         allow_headers=["Content-Type", "Authorization"])

    # Generate CLP from knowledge_base.json
    try:
        from generate_clp import generate_clp
        generate_clp()
        logger.info("[App] CLIPS knowledge base generated.")
    except Exception as e:
        logger.error(f"[App] CLP generation failed: {e}")

    # Init diagnosis engine (eager to catch startup errors)
    try:
        from modules.diagnosis import get_engine
        engine = get_engine()
        logger.info(
            f"[App] Diagnosis engine ready: {engine.engine_name} | "
            f"Diseases: {engine.disease_count} | Symptoms: {engine.symptom_count}"
        )
    except Exception as e:
        logger.critical(f"[App] Failed to initialize diagnosis engine: {e}", exc_info=True)
        raise

    # Register blueprint
    from modules.routes import api
    app.register_blueprint(api)
    from modules.doctor import doctor
    app.register_blueprint(doctor)

    # Root redirect info
    @app.route("/")
    def index():
        from flask import jsonify
        return jsonify({
            "app": "AI Disease Diagnosis Expert System",
            "version": "1.0.0",
            "api_docs": "/api/health",
            "status": "running",
        })

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    logger.info(f"[App] Starting Flask on port {port}, debug={debug}")
    app.run(host="0.0.0.0", port=port, debug=debug)
