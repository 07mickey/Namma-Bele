import os
import sys

# Ensure the app package is discoverable from this script's directory
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Default to DEMO_MODE=1 when testing locally unless explicitly disabled or in production
if os.environ.get("DEMO_MODE") is None and os.environ.get("FLASK_ENV") != "production":
    os.environ["DEMO_MODE"] = "1"

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Start the Flask server with configurable debug mode
    debug_mode = os.environ.get("FLASK_DEBUG", "true").lower() in ("true", "1")
    if os.environ.get("FLASK_ENV") == "production":
        debug_mode = False

    port_env = os.environ.get("PORT")
    if port_env:
        port = int(port_env)
    else:
        # Default to 5000 if free; if occupied (e.g. macOS AirPlay receiver), fall back to 5002
        import socket
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            test_sock.bind(("127.0.0.1", 5000))
            port = 5000
        except OSError:
            port = 5002
        finally:
            test_sock.close()

    print(f"Starting NAMMA BELE backend on http://127.0.0.1:{port} (debug={debug_mode}, demo={app.config.get('DEMO_MODE')})")
    app.run(host="127.0.0.1", port=port, debug=debug_mode)


