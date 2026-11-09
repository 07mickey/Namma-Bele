import os
from flask import Flask, jsonify, render_template, request


def create_app(test_config=None):
    """
    Application factory for the Soil Testing Portal Flask backend.
    
    Creates and configures the Flask application instance.
    """
    app = Flask(__name__, instance_relative_config=True)

    demo_active = os.environ.get("DEMO_MODE") in ("1", "true", "True")
    default_db = os.path.join(app.instance_path, "demo_soil_testing.db") if demo_active else os.path.join(app.instance_path, "soil_testing.db")
    default_reports = os.path.join(app.instance_path, "demo_reports") if demo_active else os.path.join(app.instance_path, "reports")

    # Secure default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production"),
        DATABASE=os.environ.get("DATABASE", default_db),
        REPORT_FOLDER=os.environ.get("REPORT_FOLDER", default_reports),
        DEMO_MODE=demo_active,
        MAX_CONTENT_LENGTH=12 * 1024 * 1024,  # 12 MB limit (accounts for 10 MB PDF + multipart overhead)
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=(os.environ.get("FLASK_ENV") == "production" or os.environ.get("SESSION_COOKIE_SECURE") == "true"),
    )

    # Override configuration if provided (e.g. for testing)
    if test_config:
        app.config.update(test_config)

    # Ensure the instance directory exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # Register database teardown and CLI command
    from app import db
    db.init_app(app)

    # Register CSRF protection before_request hook
    from app.auth import verify_csrf_token, auth_bp, error_response
    app.before_request(verify_csrf_token)

    # Register authentication blueprint
    app.register_blueprint(auth_bp)

    # Register farmer appointments blueprint
    from app.appointments import appointments_bp
    app.register_blueprint(appointments_bp)

    # Register admin appointment management blueprint
    from app.admin import admin_bp, admin_farmers_bp
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_farmers_bp)

    # Register reports blueprint
    from app.reports import reports_bp
    app.register_blueprint(reports_bp)

    # Register operator blueprint
    from app.operator import operator_bp
    app.register_blueprint(operator_bp)

    # Register addresses blueprint
    from app.addresses import addresses_bp
    app.register_blueprint(addresses_bp)

    # Register tracking blueprint
    from app.tracking import tracking_bp
    app.register_blueprint(tracking_bp)

    # Register laboratory blueprint
    from app.lab import lab_bp
    app.register_blueprint(lab_bp)

    # Register farm & crop records blueprint
    from app.farm import farm_bp
    app.register_blueprint(farm_bp)

    # Register expert consultations blueprint
    from app.consultations import consultations_bp
    app.register_blueprint(consultations_bp)

    # Register physical dispatch blueprint
    from app.dispatch import dispatch_bp
    app.register_blueprint(dispatch_bp)

    # Register routes blueprint (health check)
    from app.routes import api_bp
    app.register_blueprint(api_bp)

    # Register frontend views blueprint
    from app.views import views_bp
    app.register_blueprint(views_bp)

    # Register error handler for oversized requests (MAX_CONTENT_LENGTH)
    @app.errorhandler(413)
    def request_entity_too_large(error):
        return error_response(
            code="PAYLOAD_TOO_LARGE",
            message="Request payload exceeds maximum permitted size.",
            status_code=413,
        )

    # Register error handler for 404 Not Found
    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/api/"):
            return error_response(
                code="NOT_FOUND",
                message="Resource not found.",
                status_code=404,
            )
        return render_template("404.html"), 404

    # Register test-only authorization routes when in TESTING mode
    if app.config.get("TESTING"):
        from app.auth import (
            login_required, admin_required, farmer_required,
            operator_required, field_worker_required, lab_staff_required, advisor_required, staff_required
        )

        @app.route("/api/test/login-only", methods=["GET"])
        @login_required
        def test_login_only():
            return jsonify({"status": "success", "message": "Accessible by any authenticated user"}), 200

        @app.route("/api/test/admin-only", methods=["GET"])
        @admin_required
        def test_admin_only():
            return jsonify({"status": "success", "message": "Accessible by admins only"}), 200

        @app.route("/api/test/farmer-only", methods=["GET"])
        @farmer_required
        def test_farmer_only():
            return jsonify({"status": "success", "message": "Accessible by farmers only"}), 200

        @app.route("/api/test/operator-only", methods=["GET"])
        @operator_required
        def test_operator_only():
            return jsonify({"status": "success", "message": "Accessible by operators and admins"}), 200

        @app.route("/api/test/field-worker-only", methods=["GET"])
        @field_worker_required
        def test_field_worker_only():
            return jsonify({"status": "success", "message": "Accessible by field workers and admins"}), 200

        @app.route("/api/test/lab-staff-only", methods=["GET"])
        @lab_staff_required
        def test_lab_staff_only():
            return jsonify({"status": "success", "message": "Accessible by lab staff and admins"}), 200

        @app.route("/api/test/advisor-only", methods=["GET"])
        @advisor_required
        def test_advisor_only():
            return jsonify({"status": "success", "message": "Accessible by advisors and admins"}), 200

        @app.route("/api/test/staff-only", methods=["GET"])
        @staff_required
        def test_staff_only():
            return jsonify({"status": "success", "message": "Accessible by any staff member"}), 200

    return app
