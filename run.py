import os
import sys

# Ensure the app package is discoverable from this script's directory
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Start the Flask server with configurable debug mode
    debug_mode = os.environ.get("FLASK_DEBUG", "true").lower() in ("true", "1")
    if os.environ.get("FLASK_ENV") == "production":
        debug_mode = False

    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Soil Testing Portal backend on http://127.0.0.1:{port} (debug={debug_mode})")
    app.run(host="127.0.0.1", port=port, debug=debug_mode)

