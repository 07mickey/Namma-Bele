"""
Compatibility API Blueprint for Soilfrontend.
Bridges frontend requests directly to existing authoritative backend services.
"""
from flask import Blueprint, jsonify, request, g, session, send_file, current_app
from app.auth import get_current_user, error_response
from app.db import get_db

compat_bp = Blueprint("compat", __name__)


# ----------------------------------------------------------------------------
# 1. FARMER REGISTRATION ALIAS: POST /api/farmer/register -> auth.register
# ----------------------------------------------------------------------------
@compat_bp.route("/api/farmer/register", methods=["POST"])
def farmer_register():
    from app.auth import register
    return register()


# ----------------------------------------------------------------------------
# 2. FARMER LOGIN ALIAS: POST /api/farmer/login -> auth.login
# ----------------------------------------------------------------------------
@compat_bp.route("/api/farmer/login", methods=["POST"])
def farmer_login():
    from app.auth import login
    # Call core login logic
    res = login()
    # If successful login, ensure return structure has token/farmer fields expected by soilfrontend
    if isinstance(res, tuple):
        response_obj, status_code = res
    else:
        response_obj, status_code = res, 200

    if status_code == 200:
        json_data = response_obj.get_json() if hasattr(response_obj, "get_json") else {}
        user = json_data.get("user") or {}
        # Return standardized structure
        return jsonify({
            "status": "success",
            "message": "Login successful.",
            "data": {
                "token": session.get("csrf_token", "session-active"),
                "farmer": {
                    "id": user.get("id"),
                    "name": user.get("name"),
                    "phone": user.get("phone"),
                    "role": user.get("role", "farmer")
                }
            },
            "user": user,
            "csrf_token": session.get("csrf_token")
        }), 200
    return res


# ----------------------------------------------------------------------------
# 3. ADMIN LOGIN ALIAS: POST /api/admin/login -> auth.login
# ----------------------------------------------------------------------------
@compat_bp.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return error_response(
            code="VALIDATION_ERROR",
            message="Username and password are required.",
            status_code=400
        )

    # Allow admin login by username OR phone
    db = get_db()
    from app.auth import normalize_phone
    from werkzeug.security import check_password_hash
    clean_phone = normalize_phone(username)
    user = db.execute(
        "SELECT id, name, phone, password_hash, role, account_status FROM users WHERE phone = ? OR name = ?",
        (clean_phone or username, username)
    ).fetchone()

    if user is None or not check_password_hash(user["password_hash"], password):
        return error_response(
            code="INVALID_CREDENTIALS",
            message="Invalid credentials.",
            status_code=401
        )

    if user["role"] != "admin":
        return error_response(
            code="FORBIDDEN",
            message="Access denied: Admin credentials required.",
            status_code=403
        )

    # Set session
    from app.auth import generate_csrf_token
    session.clear()
    session["user_id"] = user["id"]
    session["role"] = user["role"]
    session["name"] = user["name"]
    session["phone"] = user["phone"]
    csrf_token = generate_csrf_token()

    return jsonify({
        "status": "success",
        "message": "Admin login successful.",
        "data": {
            "token": csrf_token,
            "admin": {
                "id": user["id"],
                "username": user["name"],
                "role": "Chief Agricultural Coordinator"
            }
        },
        "user": {
            "id": user["id"],
            "name": user["name"],
            "role": user["role"]
        },
        "csrf_token": csrf_token
    }), 200


# ----------------------------------------------------------------------------
# 4. FARMER APPOINTMENTS ALIAS: GET /api/farmer/appointments -> appointments.list_appointments
# ----------------------------------------------------------------------------
@compat_bp.route("/api/farmer/appointments", methods=["GET"])
def farmer_appointments():
    from app.appointments import list_appointments
    res = list_appointments()
    # In case user requested data format
    if isinstance(res, tuple):
        resp, code = res
    else:
        resp, code = res, 200

    if code == 200:
        json_data = resp.get_json() if hasattr(resp, "get_json") else {}
        apts = json_data.get("appointments") or []
        return jsonify({
            "status": "success",
            "data": {
                "appointments": apts
            },
            "appointments": apts
        }), 200
    return res


# ----------------------------------------------------------------------------
# 5. FARMER REPORTS ALIAS: GET /api/farmer/reports
# ----------------------------------------------------------------------------
@compat_bp.route("/api/farmer/reports", methods=["GET"])
def farmer_reports():
    user = get_current_user()
    if not user:
        return error_response(
            code="UNAUTHORIZED",
            message="Authentication required.",
            status_code=401
        )
    if user["role"] != "farmer":
        return error_response(
            code="FORBIDDEN",
            message="Access restricted to farmers.",
            status_code=403
        )

    db = get_db()
    rows = db.execute(
        """
        SELECT 
            r.id, r.appointment_id, r.original_filename, r.file_size_bytes,
            r.checksum_sha256, r.uploaded_at,
            a.land_details, a.address, a.preferred_date
        FROM reports r
        JOIN appointments a ON r.appointment_id = a.id
        WHERE a.farmer_id = ?
        ORDER BY r.uploaded_at DESC, r.id DESC
        """,
        (user["id"],)
    ).fetchall()

    reports_list = [
        {
            "id": row["id"],
            "appointment_id": row["appointment_id"],
            "land_details": row["land_details"],
            "report_date": row["uploaded_at"][:10] if row["uploaded_at"] else "",
            "file_name": row["original_filename"],
            "file_size_bytes": row["file_size_bytes"],
            "remarks": "Official Soil Health Certificate verified by Taluk Agricultural Testing Laboratory."
        }
        for row in rows
    ]

    return jsonify({
        "status": "success",
        "data": {
            "reports": reports_list
        },
        "reports": reports_list
    }), 200


# ----------------------------------------------------------------------------
# 6. FARMER REPORT DOWNLOAD BY REPORT ID: GET /api/reports/<int:report_id>/download
# ----------------------------------------------------------------------------
@compat_bp.route("/api/reports/<int:report_id>/download", methods=["GET"])
def download_by_report_id(report_id):
    user = get_current_user()
    if not user:
        return error_response(
            code="UNAUTHORIZED",
            message="Authentication required.",
            status_code=401
        )

    db = get_db()
    row = db.execute(
        """
        SELECT r.id, r.appointment_id, r.file_path, r.original_filename, a.farmer_id
        FROM reports r
        JOIN appointments a ON r.appointment_id = a.id
        WHERE r.id = ?
        """,
        (report_id,)
    ).fetchone()

    if row is None:
        return error_response(
            code="NOT_FOUND",
            message="Report not found.",
            status_code=404
        )

    # Verify authorization: must be admin OR owner farmer
    if user["role"] != "admin" and row["farmer_id"] != user["id"]:
        return error_response(
            code="FORBIDDEN",
            message="You do not have permission to access this report.",
            status_code=403
        )

    from app.reports import send_report_file
    return send_report_file(row["file_path"], row["original_filename"])


# ----------------------------------------------------------------------------
# 7. ADMIN REPORT UPLOAD COMPATIBILITY: POST /api/admin/reports/upload
# ----------------------------------------------------------------------------
@compat_bp.route("/api/admin/reports/upload", methods=["POST"])
def admin_upload_report_compat():
    user = get_current_user()
    if not user:
        return error_response(
            code="UNAUTHORIZED",
            message="Authentication required.",
            status_code=401
        )
    if user["role"] != "admin":
        return error_response(
            code="FORBIDDEN",
            message="Admin role required.",
            status_code=403
        )

    # Read appointment_id from multipart form data
    raw_appointment_id = request.form.get("appointment_id")
    if not raw_appointment_id:
        return error_response(
            code="VALIDATION_ERROR",
            message="appointment_id is required.",
            status_code=400,
            details={"field": "appointment_id"}
        )

    try:
        appointment_id = int(raw_appointment_id)
    except ValueError:
        return error_response(
            code="VALIDATION_ERROR",
            message="appointment_id must be a valid integer.",
            status_code=400,
            details={"field": "appointment_id"}
        )

    from app.reports import upload_report
    return upload_report(appointment_id)


# ----------------------------------------------------------------------------
# 8. ADMIN REPORTS LIST COMPATIBILITY: GET /api/admin/reports
# ----------------------------------------------------------------------------
@compat_bp.route("/api/admin/reports", methods=["GET"])
def admin_list_reports_compat():
    user = get_current_user()
    if not user:
        return error_response(
            code="UNAUTHORIZED",
            message="Authentication required.",
            status_code=401
        )
    if user["role"] != "admin":
        return error_response(
            code="FORBIDDEN",
            message="Admin role required.",
            status_code=403
        )

    db = get_db()
    rows = db.execute(
        """
        SELECT 
            r.id, r.appointment_id, r.original_filename, r.file_size_bytes,
            r.checksum_sha256, r.uploaded_at,
            a.land_details, a.address, a.preferred_date,
            u.name AS farmer_name, u.phone AS farmer_phone
        FROM reports r
        JOIN appointments a ON r.appointment_id = a.id
        JOIN users u ON a.farmer_id = u.id
        ORDER BY r.uploaded_at DESC, r.id DESC
        """
    ).fetchall()

    reports_list = [
        {
            "id": row["id"],
            "appointment_id": row["appointment_id"],
            "farmer_name": row["farmer_name"],
            "farmer_phone": row["farmer_phone"],
            "land_details": row["land_details"],
            "report_date": row["uploaded_at"][:10] if row["uploaded_at"] else "",
            "file_name": row["original_filename"],
            "file_size_bytes": row["file_size_bytes"],
            "remarks": "Official Verified Report"
        }
        for row in rows
    ]

    return jsonify({
        "status": "success",
        "data": {
            "reports": reports_list
        },
        "reports": reports_list
    }), 200
