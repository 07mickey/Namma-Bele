import math
from flask import Blueprint, jsonify, request

from app.auth import admin_required, error_response
from app.db import get_db

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin/appointments")
admin_farmers_bp = Blueprint("admin_farmers", __name__, url_prefix="/api/admin/farmers")

# Supported appointment statuses
ALLOWED_STATUSES = ("Pending", "Approved", "Rejected", "Completed")

# Enforced state machine transitions
ALLOWED_TRANSITIONS = {
    "Pending": {"Approved", "Rejected"},
    "Approved": {"Completed"},
    "Rejected": set(),    # Terminal state
    "Completed": set(),   # Terminal state
}

# Pagination boundaries
DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100


# ============================================================================
# 1. ADMIN LIST APPOINTMENTS (GET /api/admin/appointments)
# ============================================================================

@admin_bp.route("", methods=["GET"])
@admin_required
def list_appointments():
    """
    Lists appointments across all farmers with pagination and optional status filter.
    - Requires authenticated admin role.
    - Supports ?status= filter ('Pending', 'Approved', 'Rejected', 'Completed').
    - Supports ?page= and ?per_page= bounded pagination.
    - Returns farmer details (name, phone) joined from users table.
    - Never exposes password hashes or security secrets.
    - Deterministic ordering: created_at DESC, id DESC.
    """
    db = get_db()

    # 1. Validate status filter
    status_filter = request.args.get("status")
    clean_status = None
    if status_filter is not None and status_filter.strip():
        clean_status = status_filter.strip()
        if clean_status not in ALLOWED_STATUSES:
            return error_response(
                code="VALIDATION_ERROR",
                message=f"Invalid status filter '{clean_status}'. Allowed values: {', '.join(ALLOWED_STATUSES)}.",
                status_code=400,
                details={"field": "status"},
            )

    # 2. Validate page parameter
    page_param = request.args.get("page", str(DEFAULT_PAGE))
    try:
        page = int(page_param)
        if page < 1:
            raise ValueError()
    except (ValueError, TypeError):
        return error_response(
            code="VALIDATION_ERROR",
            message="Page must be a positive integer greater than or equal to 1.",
            status_code=400,
            details={"field": "page"},
        )

    # 3. Validate per_page parameter
    per_page_param = request.args.get("per_page", str(DEFAULT_PER_PAGE))
    try:
        per_page = int(per_page_param)
        if per_page < 1 or per_page > MAX_PER_PAGE:
            raise ValueError()
    except (ValueError, TypeError):
        return error_response(
            code="VALIDATION_ERROR",
            message=f"per_page must be an integer between 1 and {MAX_PER_PAGE}.",
            status_code=400,
            details={"field": "per_page"},
        )

    # 4. Count total items for pagination
    if clean_status:
        count_cursor = db.execute(
            "SELECT COUNT(*) FROM appointments WHERE status = ?",
            (clean_status,),
        )
    else:
        count_cursor = db.execute("SELECT COUNT(*) FROM appointments")
    total_count = count_cursor.fetchone()[0]

    total_pages = math.ceil(total_count / per_page) if total_count > 0 else 1
    offset = (page - 1) * per_page

    # 5. Retrieve paginated records joined with users for farmer info
    if clean_status:
        rows = db.execute(
            """
            SELECT 
                a.id, a.farmer_id, u.name AS farmer_name, u.phone AS farmer_phone,
                a.land_details, a.address, a.preferred_date, a.preferred_time,
                a.notes, a.status, a.created_at, a.updated_at
            FROM appointments a
            JOIN users u ON a.farmer_id = u.id
            WHERE a.status = ?
            ORDER BY a.created_at DESC, a.id DESC
            LIMIT ? OFFSET ?
            """,
            (clean_status, per_page, offset),
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT 
                a.id, a.farmer_id, u.name AS farmer_name, u.phone AS farmer_phone,
                a.land_details, a.address, a.preferred_date, a.preferred_time,
                a.notes, a.status, a.created_at, a.updated_at
            FROM appointments a
            JOIN users u ON a.farmer_id = u.id
            ORDER BY a.created_at DESC, a.id DESC
            LIMIT ? OFFSET ?
            """,
            (per_page, offset),
        ).fetchall()

    appointment_list = [
        {
            "id": row["id"],
            "farmer_id": row["farmer_id"],
            "farmer_name": row["farmer_name"],
            "farmer_phone": row["farmer_phone"],
            "land_details": row["land_details"],
            "address": row["address"],
            "preferred_date": row["preferred_date"],
            "preferred_time": row["preferred_time"],
            "notes": row["notes"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]

    return jsonify({
        "status": "success",
        "appointments": appointment_list,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_count": total_count,
            "total_pages": total_pages,
        },
    }), 200


# ============================================================================
# 2. ADMIN VIEW ONE APPOINTMENT (GET /api/admin/appointments/<int:appointment_id>)
# ============================================================================

@admin_bp.route("/<int:appointment_id>", methods=["GET"])
@admin_required
def get_appointment(appointment_id):
    """
    Retrieves full details of a single appointment along with farmer information.
    - Requires authenticated admin role.
    - Returns HTTP 404 if the appointment does not exist.
    - Never exposes password hashes or security secrets.
    """
    db = get_db()
    row = db.execute(
        """
        SELECT 
            a.id, a.farmer_id, u.name AS farmer_name, u.phone AS farmer_phone,
            a.land_details, a.address, a.preferred_date, a.preferred_time,
            a.notes, a.status, a.created_at, a.updated_at
        FROM appointments a
        JOIN users u ON a.farmer_id = u.id
        WHERE a.id = ?
        """,
        (appointment_id,),
    ).fetchone()

    if row is None:
        return error_response(
            code="NOT_FOUND",
            message="Appointment not found.",
            status_code=404,
        )

    return jsonify({
        "status": "success",
        "appointment": {
            "id": row["id"],
            "farmer_id": row["farmer_id"],
            "farmer_name": row["farmer_name"],
            "farmer_phone": row["farmer_phone"],
            "land_details": row["land_details"],
            "address": row["address"],
            "preferred_date": row["preferred_date"],
            "preferred_time": row["preferred_time"],
            "notes": row["notes"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        },
    }), 200


# ============================================================================
# 3. ADMIN UPDATE APPOINTMENT STATUS (PATCH /api/admin/appointments/<int:appointment_id>/status)
# ============================================================================

@admin_bp.route("/<int:appointment_id>/status", methods=["PATCH"])
@admin_required
def update_appointment_status(appointment_id):
    """
    Updates the status of an appointment following strict state machine rules:
      Pending  -> Approved
      Pending  -> Rejected
      Approved -> Completed
    - Requires authenticated admin role and valid CSRF token.
    - Same-status request is handled as a successful no-op (updated_at preserved).
    - Invalid transition returns HTTP 409 Conflict.
    - Atomic conditional update avoids race conditions under concurrent updates.
    - Explicitly sets updated_at = CURRENT_TIMESTAMP upon real transition.
    """
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return error_response(
            code="MALFORMED_REQUEST",
            message="Request body must be a valid JSON object.",
            status_code=400,
        )

    # 1. Validate status field presence and format
    raw_status = data.get("status")
    if not raw_status or not isinstance(raw_status, str) or not raw_status.strip():
        return error_response(
            code="VALIDATION_ERROR",
            message="Status field is required and cannot be empty.",
            status_code=400,
            details={"field": "status"},
        )
    new_status = raw_status.strip()

    # 2. Check that status is among supported values
    if new_status not in ALLOWED_STATUSES:
        return error_response(
            code="VALIDATION_ERROR",
            message=f"Unsupported status value '{new_status}'. Allowed values: {', '.join(ALLOWED_STATUSES)}.",
            status_code=400,
            details={"field": "status"},
        )

    db = get_db()

    # 3. Fetch current appointment record
    row = db.execute(
        """
        SELECT 
            a.id, a.farmer_id, u.name AS farmer_name, u.phone AS farmer_phone,
            a.land_details, a.address, a.preferred_date, a.preferred_time,
            a.notes, a.status, a.created_at, a.updated_at
        FROM appointments a
        JOIN users u ON a.farmer_id = u.id
        WHERE a.id = ?
        """,
        (appointment_id,),
    ).fetchone()

    if row is None:
        return error_response(
            code="NOT_FOUND",
            message="Appointment not found.",
            status_code=404,
        )

    current_status = row["status"]

    # 4. Handle same-status as successful no-op (do not update updated_at)
    if new_status == current_status:
        return jsonify({
            "status": "success",
            "message": "Appointment status is already set to the requested value.",
            "appointment": {
                "id": row["id"],
                "farmer_id": row["farmer_id"],
                "farmer_name": row["farmer_name"],
                "farmer_phone": row["farmer_phone"],
                "land_details": row["land_details"],
                "address": row["address"],
                "preferred_date": row["preferred_date"],
                "preferred_time": row["preferred_time"],
                "notes": row["notes"],
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            },
        }), 200

    # 5. Enforce state machine transitions
    allowed_next_states = ALLOWED_TRANSITIONS.get(current_status, set())
    if new_status not in allowed_next_states:
        return error_response(
            code="CONFLICT",
            message=f"Invalid status transition from '{current_status}' to '{new_status}'.",
            status_code=409,
            details={
                "current_status": current_status,
                "requested_status": new_status,
                "allowed_transitions": sorted(list(allowed_next_states)),
            },
        )

    # 6. Execute atomic conditional update to guard against concurrent modifications
    with db:
        cursor = db.execute(
            """
            UPDATE appointments
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status = ?
            """,
            (new_status, appointment_id, current_status),
        )

    # 7. Check affected row count for concurrency collision
    if cursor.rowcount == 0:
        latest = db.execute("SELECT status FROM appointments WHERE id = ?", (appointment_id,)).fetchone()
        if latest is None:
            return error_response(
                code="NOT_FOUND",
                message="Appointment not found.",
                status_code=404,
            )
        return error_response(
            code="CONFLICT",
            message="Appointment status was modified concurrently by another process. Please reload and try again.",
            status_code=409,
            details={"current_status": latest["status"]},
        )

    # 8. Retrieve updated appointment record
    updated_row = db.execute(
        """
        SELECT 
            a.id, a.farmer_id, u.name AS farmer_name, u.phone AS farmer_phone,
            a.land_details, a.address, a.preferred_date, a.preferred_time,
            a.notes, a.status, a.created_at, a.updated_at
        FROM appointments a
        JOIN users u ON a.farmer_id = u.id
        WHERE a.id = ?
        """,
        (appointment_id,),
    ).fetchone()

    return jsonify({
        "status": "success",
        "message": f"Appointment status updated to '{new_status}'.",
        "appointment": {
            "id": updated_row["id"],
            "farmer_id": updated_row["farmer_id"],
            "farmer_name": updated_row["farmer_name"],
            "farmer_phone": updated_row["farmer_phone"],
            "land_details": updated_row["land_details"],
            "address": updated_row["address"],
            "preferred_date": updated_row["preferred_date"],
            "preferred_time": updated_row["preferred_time"],
            "notes": updated_row["notes"],
            "status": updated_row["status"],
            "created_at": updated_row["created_at"],
            "updated_at": updated_row["updated_at"],
        },
    }), 200


# ============================================================================
# REGISTERED FARMERS DIRECTORY
# ============================================================================

@admin_farmers_bp.route("", methods=["GET"])
@admin_required
def list_farmers():
    """
    Returns a list of all registered community farmers for administrative coordination.
    Powers the MANYA registered farmers directory view.
    """
    db = get_db()
    farmers = db.execute(
        """
        SELECT u.id, u.name, u.phone, u.created_at,
               COUNT(a.id) AS appointment_count
        FROM users u
        LEFT JOIN appointments a ON u.id = a.farmer_id
        WHERE u.role = 'farmer'
        GROUP BY u.id
        ORDER BY u.id DESC
        """
    ).fetchall()

    return jsonify({
        "status": "success",
        "data": {
            "farmers": [
                {
                    "id": f["id"],
                    "name": f["name"],
                    "phone": f["phone"],
                    "created_at": f["created_at"],
                    "appointment_count": f["appointment_count"]
                }
                for f in farmers
            ]
        }
    }), 200


