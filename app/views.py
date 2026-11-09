from flask import Blueprint, render_template, redirect, url_for, request
from app.auth import get_current_user

views_bp = Blueprint("views", __name__)


# ============================================================================
# PUBLIC PAGES
# ============================================================================

@views_bp.route("/", methods=["GET"])
def index():
    """Renders the public portal landing page."""
    return render_template("index.html")


@views_bp.route("/soil-guide", methods=["GET"])
def soil_guide():
    """
    Renders the educational Soil Health & Testing Guide.
    Accessible to all farmers, coordinators, and public visitors.
    """
    return render_template("soil_guide.html")


@views_bp.route("/contact", methods=["GET"])
def contact():
    """Renders the public & farmer Agricultural Support and Helpline center page."""
    return render_template("contact.html")


@views_bp.route("/claim", methods=["GET"])
def claim_account():
    """Renders the self-service account activation page for assisted farmers."""
    return render_template("claim.html")


@views_bp.route("/register", methods=["GET"])
def register():
    """
    Renders the farmer registration page.
    Redirects authenticated users to their corresponding dashboard.
    """
    user = get_current_user()
    if user:
        if user["role"] == "admin":
            return redirect(url_for("views.admin_dashboard"))
        return redirect(url_for("views.farmer_dashboard"))
    return render_template("register.html")


@views_bp.route("/login", methods=["GET"])
def login():
    """
    Renders the dual-entry login page (Farmer Login vs Staff / Admin Login).
    Redirects authenticated users to their corresponding dashboard.
    """
    user = get_current_user()
    if user:
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
    return render_template("login.html")


# ============================================================================
# FARMER EXPERIENCE PAGES
# ============================================================================

@views_bp.route("/farmer", methods=["GET"])
def farmer_dashboard():
    """
    Renders the authenticated farmer dashboard and booking interface.
    Redirects unauthenticated users to login, and admins to the admin dashboard.
    """
    user = get_current_user()
    if not user:
        return redirect(url_for("views.login"))
    if user["role"] != "farmer":
        return redirect(url_for("views.admin_dashboard"))
    return render_template("farmer.html")


@views_bp.route("/farmer/tracking", methods=["GET"])
def farmer_tracking():
    """Renders the live 13-stage soil sample tracking timeline."""
    user = get_current_user()
    if not user:
        return redirect(url_for("views.login"))
    return render_template("farmer_tracking.html")


@views_bp.route("/farmer/plots", methods=["GET"])
def farmer_plots():
    """Renders the farmer's agricultural land and plot registry."""
    user = get_current_user()
    if not user:
        return redirect(url_for("views.login"))
    return render_template("farmer_plots.html")


@views_bp.route("/farmer/crop-history", methods=["GET"])
def farmer_crop_history():
    """Renders season-by-season crop cultivation history with Paddy / Rice standardization."""
    user = get_current_user()
    if not user:
        return redirect(url_for("views.login"))
    return render_template("farmer_crop_history.html")


@views_bp.route("/farmer/farm-records", methods=["GET"])
def farmer_farm_records():
    """Renders harvest yield logging and sales records with transparent gross revenue calculations."""
    user = get_current_user()
    if not user:
        return redirect(url_for("views.login"))
    return render_template("farmer_farm_records.html")


@views_bp.route("/farmer/addresses", methods=["GET"])
def farmer_addresses():
    """Renders farmer postal delivery addresses management."""
    user = get_current_user()
    if not user:
        return redirect(url_for("views.login"))
    return render_template("farmer_addresses.html")


@views_bp.route("/farmer/expert-help", methods=["GET"])
def farmer_expert_help():
    """Renders the Ask an Agricultural Expert advisory consultation interface."""
    user = get_current_user()
    if not user:
        return redirect(url_for("views.login"))
    return render_template("farmer_expert.html")


# ============================================================================
# STAFF WORKFLOW PORTALS
# ============================================================================

@views_bp.route("/admin", methods=["GET"])
def admin_dashboard():
    """
    Renders the authenticated administrator queue and management dashboard.
    Redirects unauthenticated users to login, and farmers to the farmer dashboard.
    """
    user = get_current_user()
    if not user:
        return redirect(url_for("views.login"))
    if user["role"] != "admin":
        if user["role"] == "operator":
            return redirect(url_for("views.operator_dashboard"))
        elif user["role"] == "field_worker":
            return redirect(url_for("views.field_worker_dashboard"))
        elif user["role"] == "lab_staff":
            return redirect(url_for("views.lab_dashboard"))
        elif user["role"] == "advisor":
            return redirect(url_for("views.advisor_dashboard"))
        return redirect(url_for("views.farmer_dashboard"))
    return render_template("admin.html")


@views_bp.route("/admin/tracking", methods=["GET"])
def admin_tracking():
    """Renders the administrative 13-stage sample tracking pipeline overview."""
    user = get_current_user()
    if not user or user["role"] not in ("admin", "operator"):
        return redirect(url_for("views.login"))
    return render_template("admin_tracking.html")


@views_bp.route("/admin/dispatch", methods=["GET"])
def admin_dispatch():
    """Renders physical report print queue and Speed Post dispatch console."""
    user = get_current_user()
    if not user or user["role"] not in ("admin", "operator"):
        return redirect(url_for("views.login"))
    return render_template("admin_dispatch.html")


@views_bp.route("/operator", methods=["GET"])
def operator_dashboard():
    """Renders the call center operator assisted registration and booking portal."""
    user = get_current_user()
    if not user or user["role"] not in ("operator", "admin"):
        return redirect(url_for("views.login"))
    return render_template("operator.html")


@views_bp.route("/field-worker", methods=["GET"])
def field_worker_dashboard():
    """Renders the field technician sample collection and visit schedule portal."""
    user = get_current_user()
    if not user or user["role"] not in ("field_worker", "admin"):
        return redirect(url_for("views.login"))
    return render_template("field_worker.html")


@views_bp.route("/lab", methods=["GET"])
def lab_dashboard():
    """Renders the laboratory chemical testing and assay measurement workspace."""
    user = get_current_user()
    if not user or user["role"] not in ("lab_staff", "admin"):
        return redirect(url_for("views.login"))
    return render_template("lab_dashboard.html")


@views_bp.route("/advisor", methods=["GET"])
def advisor_dashboard():
    """Renders the agricultural scientist expert advisory response console."""
    user = get_current_user()
    if not user or user["role"] not in ("advisor", "admin"):
        return redirect(url_for("views.login"))
    return render_template("advisor_dashboard.html")
