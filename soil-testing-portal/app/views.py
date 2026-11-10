import os
from flask import Blueprint, render_template, redirect, url_for, request
from app.auth import get_current_user

views_bp = Blueprint("views", __name__)


# ============================================================================
# PUBLIC PAGES (SOILFRONTEND)
# ============================================================================

@views_bp.route("/", methods=["GET"])
@views_bp.route("/index.html", methods=["GET"])
def index():
    """Renders the public portal landing page."""
    return render_template("index.html")


@views_bp.route("/soil-guide", methods=["GET"])
@views_bp.route("/soil-guide.html", methods=["GET"])
def soil_guide():
    """Renders the educational Soil Health & Testing Guide."""
    return render_template("soil_guide.html")


@views_bp.route("/contact", methods=["GET"])
@views_bp.route("/contact.html", methods=["GET"])
def contact():
    """Renders contact / support page."""
    return render_template("contact.html")


@views_bp.route("/claim", methods=["GET"])
@views_bp.route("/claim.html", methods=["GET"])
def claim_account():
    """Renders self-service account activation."""
    return render_template("claim.html")


@views_bp.route("/register", methods=["GET"])
@views_bp.route("/register.html", methods=["GET"])
def register():
    """Renders the farmer registration page."""
    from flask import session, g
    if request.args.get("new") or request.args.get("switch") or request.args.get("logged_out"):
        session.clear()
        g.current_user = None
        user = None
    else:
        user = get_current_user()

    if user and not (request.args.get("new") or request.args.get("stay")):
        if user["role"] == "admin":
            return redirect(url_for("views.admin_dashboard"))
        return redirect(url_for("views.farmer_dashboard"))
    return render_template("register.html")


@views_bp.route("/login", methods=["GET"])
@views_bp.route("/login.html", methods=["GET"])
def login():
    """Renders the login page with optional safe demo accounts panel."""
    from flask import current_app, session, g
    if request.args.get("logged_out") or request.args.get("switch") or request.args.get("reset"):
        session.clear()
        g.current_user = None
        user = None
    else:
        user = get_current_user()

    if user and not (request.args.get("stay") or request.args.get("switch") or request.args.get("logged_out")):
        if user["role"] == "admin":
            return redirect(url_for("views.admin_dashboard"))
        elif user["role"] == "operator":
            return redirect(url_for("views.operator_dashboard"))
        elif user["role"] == "field_worker":
            return redirect(url_for("views.field_worker_dashboard"))
        elif user["role"] == "lab_staff":
            return redirect(url_for("views.lab_dashboard"))
        elif user["role"] == "advisor":
            return redirect(url_for("views.advisor_dashboard"))
        return redirect(url_for("views.farmer_dashboard"))
    
    demo_mode = current_app.config.get("DEMO_MODE", False)
    demo_password = os.environ.get("DEMO_PASSWORD", "DemoUser@2026!") if demo_mode else ""
    return render_template("login.html", demo_mode=demo_mode, demo_password=demo_password)


@views_bp.route("/admin-login", methods=["GET"])
@views_bp.route("/admin-login.html", methods=["GET"])
def admin_login():
    """Renders dedicated coordinator / administrator login page."""
    from flask import session, g
    if request.args.get("logged_out") or request.args.get("switch") or request.args.get("reset"):
        session.clear()
        g.current_user = None
        user = None
    else:
        user = get_current_user()

    if user and user["role"] == "admin" and not (request.args.get("stay") or request.args.get("switch") or request.args.get("logged_out")):
        return redirect(url_for("views.admin_dashboard"))
    return render_template("admin-login.html")


# ============================================================================
# FARMER EXPERIENCE PAGES (SOILFRONTEND)
# ============================================================================

@views_bp.route("/dashboard.html", methods=["GET"])
@views_bp.route("/farmer", methods=["GET"])
def farmer_dashboard():
    """Renders the authenticated farmer dashboard."""
    user = get_current_user()
    if not user:
        return redirect(url_for("views.login"))
    role = str(user["role"] or "").lower()
    if "admin" in role or "coordinator" in role:
        return redirect(url_for("views.admin_dashboard"))
    elif "operator" in role:
        return redirect(url_for("views.operator_dashboard"))
    elif "field" in role:
        return redirect(url_for("views.field_worker_dashboard"))
    elif "lab" in role:
        return redirect(url_for("views.lab_dashboard"))
    elif "advisor" in role:
        return redirect(url_for("views.advisor_dashboard"))
    return render_template("farmer.html")


@views_bp.route("/book-appointment", methods=["GET"])
@views_bp.route("/book-appointment.html", methods=["GET"])
def book_appointment():
    """Renders the soil test booking page."""
    user = get_current_user()
    if not user:
        return redirect(url_for("views.login"))
    return render_template("book-appointment.html")


@views_bp.route("/appointments", methods=["GET"])
@views_bp.route("/appointments.html", methods=["GET"])
def appointments():
    """Renders farmer appointments listing."""
    user = get_current_user()
    if not user:
        return redirect(url_for("views.login"))
    return render_template("appointments.html")


@views_bp.route("/reports", methods=["GET"])
@views_bp.route("/reports.html", methods=["GET"])
def reports():
    """Renders farmer reports download page."""
    user = get_current_user()
    if not user:
        return redirect(url_for("views.login"))
    return render_template("reports.html")


@views_bp.route("/farmer/tracking", methods=["GET"])
def farmer_tracking():
    user = get_current_user()
    if not user:
        return redirect(url_for("views.login"))
    return render_template("farmer_tracking.html")


@views_bp.route("/farmer/plots", methods=["GET"])
def farmer_plots():
    user = get_current_user()
    if not user:
        return redirect(url_for("views.login"))
    return render_template("farmer_plots.html")


@views_bp.route("/farmer/crop-history", methods=["GET"])
def farmer_crop_history():
    user = get_current_user()
    if not user:
        return redirect(url_for("views.login"))
    return render_template("farmer_crop_history.html")


@views_bp.route("/farmer/farm-records", methods=["GET"])
def farmer_farm_records():
    user = get_current_user()
    if not user:
        return redirect(url_for("views.login"))
    return render_template("farmer_farm_records.html")


@views_bp.route("/farmer/addresses", methods=["GET"])
def farmer_addresses():
    user = get_current_user()
    if not user:
        return redirect(url_for("views.login"))
    return render_template("farmer_addresses.html")


@views_bp.route("/farmer/expert-help", methods=["GET"])
def farmer_expert_help():
    user = get_current_user()
    if not user:
        return redirect(url_for("views.login"))
    return render_template("farmer_expert.html")


# ============================================================================
# ADMIN & COORDINATOR PAGES (SOILFRONTEND)
# ============================================================================

@views_bp.route("/admin-dashboard.html", methods=["GET"])
@views_bp.route("/admin", methods=["GET"])
def admin_dashboard():
    """Renders the administrative dashboard."""
    user = get_current_user()
    if not user:
        return redirect(url_for("views.admin_login"))
    if user["role"] != "admin":
        if user["role"] == "farmer":
            return redirect(url_for("views.farmer_dashboard"))
        elif user["role"] == "operator":
            return redirect(url_for("views.operator_dashboard"))
        elif user["role"] == "field_worker":
            return redirect(url_for("views.field_worker_dashboard"))
        elif user["role"] == "lab_staff":
            return redirect(url_for("views.lab_dashboard"))
        elif user["role"] == "advisor":
            return redirect(url_for("views.advisor_dashboard"))
    return render_template("admin-dashboard.html")


@views_bp.route("/admin-appointments", methods=["GET"])
@views_bp.route("/admin-appointments.html", methods=["GET"])
def admin_appointments():
    """Renders admin appointments review table."""
    user = get_current_user()
    if not user or user["role"] != "admin":
        return redirect(url_for("views.admin_login"))
    return render_template("admin-appointments.html")


@views_bp.route("/admin-reports", methods=["GET"])
@views_bp.route("/admin-reports.html", methods=["GET"])
def admin_reports():
    """Renders admin report upload and management interface."""
    user = get_current_user()
    if not user or user["role"] != "admin":
        return redirect(url_for("views.admin_login"))
    return render_template("admin-reports.html")


@views_bp.route("/admin-farmers", methods=["GET"])
@views_bp.route("/admin-farmers.html", methods=["GET"])
def admin_farmers():
    """Renders admin farmer directory."""
    user = get_current_user()
    if not user or user["role"] != "admin":
        return redirect(url_for("views.admin_login"))
    return render_template("admin-farmers.html")


@views_bp.route("/admin/tracking", methods=["GET"])
def admin_tracking():
    user = get_current_user()
    if not user or user["role"] not in ("admin", "operator"):
        return redirect(url_for("views.admin_login"))
    return render_template("admin_tracking.html")


@views_bp.route("/admin/dispatch", methods=["GET"])
def admin_dispatch():
    user = get_current_user()
    if not user or user["role"] not in ("admin", "operator"):
        return redirect(url_for("views.admin_login"))
    return render_template("admin_dispatch.html")


# ============================================================================
# OTHER APPLICATION WORKFLOWS
# ============================================================================

@views_bp.route("/operator", methods=["GET"])
def operator_dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for("views.login"))
    if user["role"] not in ("operator", "admin"):
        if user["role"] == "farmer":
            return redirect(url_for("views.farmer_dashboard"))
        elif user["role"] == "field_worker":
            return redirect(url_for("views.field_worker_dashboard"))
        elif user["role"] == "lab_staff":
            return redirect(url_for("views.lab_dashboard"))
        elif user["role"] == "advisor":
            return redirect(url_for("views.advisor_dashboard"))
    return render_template("operator.html")


@views_bp.route("/field-worker", methods=["GET"])
def field_worker_dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for("views.login"))
    if user["role"] not in ("field_worker", "admin"):
        if user["role"] == "farmer":
            return redirect(url_for("views.farmer_dashboard"))
        elif user["role"] == "operator":
            return redirect(url_for("views.operator_dashboard"))
        elif user["role"] == "lab_staff":
            return redirect(url_for("views.lab_dashboard"))
        elif user["role"] == "advisor":
            return redirect(url_for("views.advisor_dashboard"))
    return render_template("field_worker.html")


@views_bp.route("/lab", methods=["GET"])
def lab_dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for("views.login"))
    if user["role"] not in ("lab_staff", "admin"):
        if user["role"] == "farmer":
            return redirect(url_for("views.farmer_dashboard"))
        elif user["role"] == "operator":
            return redirect(url_for("views.operator_dashboard"))
        elif user["role"] == "field_worker":
            return redirect(url_for("views.field_worker_dashboard"))
        elif user["role"] == "advisor":
            return redirect(url_for("views.advisor_dashboard"))
    return render_template("lab_dashboard.html")


@views_bp.route("/advisor", methods=["GET"])
def advisor_dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for("views.login"))
    if user["role"] not in ("advisor", "admin"):
        if user["role"] == "farmer":
            return redirect(url_for("views.farmer_dashboard"))
        elif user["role"] == "operator":
            return redirect(url_for("views.operator_dashboard"))
        elif user["role"] == "field_worker":
            return redirect(url_for("views.field_worker_dashboard"))
        elif user["role"] == "lab_staff":
            return redirect(url_for("views.lab_dashboard"))
    return render_template("advisor_dashboard.html")
