"""
NAMMA BELE (ನಮ್ಮ ಬೆಳೆ) — Root Application Entrypoint for Vercel & Production WSGI

Exports the Flask application instance as `app` by delegating to the
canonical application factory in `soil-testing-portal`.
"""
import os
import sys

# Ensure soil-testing-portal is on the Python module search path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PORTAL_DIR = os.path.join(CURRENT_DIR, "soil-testing-portal")

if PORTAL_DIR not in sys.path:
    sys.path.insert(0, PORTAL_DIR)

# Default to DEMO_MODE=1 when testing locally unless explicitly disabled or in production
if os.environ.get("DEMO_MODE") is None and os.environ.get("FLASK_ENV") != "production":
    os.environ["DEMO_MODE"] = "1"

from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() in ("true", "1")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
