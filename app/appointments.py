import re
from datetime import date, datetime
from zoneinfo import ZoneInfo
from flask import Blueprint, g, jsonify, request

from app.auth import farmer_required, error_response
from app.db import get_db
from app.services.tracking_service import get_or_create_soil_sample, record_sample_event

appointments_bp = Blueprint("appointments", __name__, url_prefix="/api/appointments")

# Valid time slots as per project specification and SQLite CHECK constraint
ALLOWED_TIME_SLOTS = ("09:00-12:00", "14:00-17:00")

# Sensible maximum field lengths
MAX_LAND_DETAILS_LEN = 500
MAX_ADDRESS_LEN = 500
MAX_NOTES_LEN = 1000

DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ============================================================================
# 1. CREATE APPOINTMENT (POST /api/appointments)
# ============================================================================

@appointments_bp.route("", methods=["POST"])
@farmer_required
def create_appointment():
    """
    Creates a new soil testing appointment for the authenticated farmer.
    - Status is always initialized to 'Pending'.
    - Farmer ID is strictly taken from the authenticated session (never client input).
    - Client-supplied 'status' or 'farmer_id' fields are completely ignored.
    - Validates presence, formatting, date reality, and time slot choices.
    """
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return error_response(
            code="MALFORMED_REQUEST",
            message="Request body must be a valid JSON object.",
            status_code=400,
        )

    # 1. Validate land_details
    land_details = data.get("land_details")
    if not land_details or not isinstance(land_details, str) or not land_details.strip():
        return error_response(
            code="VALIDATION_ERROR",
            message="Land details are required and cannot be empty.",
            status_code=400,
            details={"field": "land_details"},
        )
    clean_land_details = land_details.strip()
    if len(clean_land_details) > MAX_LAND_DETAILS_LEN:
        return error_response(
            code="VALIDATION_ERROR",
            message=f"Land details cannot exceed {MAX_LAND_DETAILS_LEN} characters.",
            status_code=400,
            details={"field": "land_details"},
        )

    # 2. Validate address
    address = data.get("address")
    if not address or not isinstance(address, str) or not address.strip():
        return error_response(
            code="VALIDATION_ERROR",
            message="Address is required and cannot be empty.",
            status_code=400,
            details={"field": "address"},
        )
    clean_address = address.strip()
    if len(clean_address) > MAX_ADDRESS_LEN:
        return error_response(
            code="VALIDATION_ERROR",
            message=f"Address cannot exceed {MAX_ADDRESS_LEN} characters.",
            status_code=400,
            details={"field": "address"},
        )

    # 3. Validate preferred_date
    preferred_date = data.get("preferred_date")
    if not preferred_date or not isinstance(preferred_date, str) or not DATE_REGEX.match(preferred_date.strip()):
        return error_response(
            code="VALIDATION_ERROR",
            message="Preferred date is required and must use exact YYYY-MM-DD format.",
            status_code=400,
            details={"field": "preferred_date"},
        )
    clean_date_str = preferred_date.strip()

    try:
        parsed_date = datetime.strptime(clean_date_str, "%Y-%m-%d").date()
    except ValueError:
        return error_response(
            code="VALIDATION_ERROR",
            message="Preferred date must be a valid calendar date.",
            status_code=400,
            details={"field": "preferred_date"},
        )

    kolkata_today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    if parsed_date < kolkata_today:
        return error_response(
            code="VALIDATION_ERROR",
            message="Preferred date cannot be in the past.",
            status_code=400,
            details={"field": "preferred_date"},
        )

    # 4. Validate preferred_time
    preferred_time = data.get("preferred_time")
    if not preferred_time or not isinstance(preferred_time, str):
        return error_response(
            code="VALIDATION_ERROR",
            message="Preferred time slot is required.",
            status_code=400,
            details={"field": "preferred_time"},
        )
    clean_time_str = preferred_time.strip()
    if clean_time_str not in ALLOWED_TIME_SLOTS:
        return error_response(
            code="VALIDATION_ERROR",
            message="Preferred time slot must be either '09:00-12:00' or '14:00-17:00'.",
            status_code=400,
            details={"field": "preferred_time"},
        )

    # 5. Validate optional notes
    notes = data.get("notes")
    clean_notes = None
    if notes is not None:
        if not isinstance(notes, str):
            return error_response(
                code="VALIDATION_ERROR",
                message="Notes must be a string value.",
                status_code=400,
                details={"field": "notes"},
            )
        stripped_notes = notes.strip()
        if stripped_notes:
            if len(stripped_notes) > MAX_NOTES_LEN:
                return error_response(
                    code="VALIDATION_ERROR",
                    message=f"Notes cannot exceed {MAX_NOTES_LEN} characters.",
                    status_code=400,
                    details={"field": "notes"},
                )
            clean_notes = stripped_notes

    # 6. Set farmer ownership from authenticated session
    authenticated_farmer_id = g.current_user["id"]
    plot_id = data.get("plot_id")
    delivery_address_id = data.get("delivery_address_id")

    db = get_db()
    with db:
        cursor = db.execute(
            """
            INSERT INTO appointments (
                farmer_id, land_details, address, preferred_date, preferred_time, notes, status,
                plot_id, delivery_address_id
            ) VALUES (?, ?, ?, ?, ?, ?, 'Pending', ?, ?)
            """,
            (
                authenticated_farmer_id,
                clean_land_details,
                clean_address,
                clean_date_str,
                clean_time_str,
                clean_notes,
                plot_id,
                delivery_address_id,
            ),
        )
        appointment_id = cursor.lastrowid

        # Seed sample record and emit Stage 1 event
        sample = get_or_create_soil_sample(db, appointment_id)
        record_sample_event(
            db,
            sample_id=sample["id"],
            stage_number=1,
            status="COMPLETED",
            actor_user_id=authenticated_farmer_id,
            actor_role="farmer",
            department="Customer Service",
            description="Soil testing appointment booked by farmer.",
            details_dict={"preferred_date": clean_date_str, "preferred_time": clean_time_str},
        )

        appointment = db.execute(
            """
            SELECT id, farmer_id, land_details, address, preferred_date, preferred_time, notes, status,
                   plot_id, delivery_address_id, created_at, updated_at
            FROM appointments
            WHERE id = ?
            """,
            (appointment_id,),
        ).fetchone()

    return jsonify({
        "status": "success",
        "message": "Appointment booked successfully.",
        "appointment": {
            "id": appointment["id"],
            "farmer_id": appointment["farmer_id"],
            "land_details": appointment["land_details"],
            "address": appointment["address"],
            "preferred_date": appointment["preferred_date"],
            "preferred_time": appointment["preferred_time"],
            "notes": appointment["notes"],
            "status": appointment["status"],
            "plot_id": appointment["plot_id"],
            "delivery_address_id": appointment["delivery_address_id"],
            "sample_code": sample["sample_code"],
            "created_at": appointment["created_at"],
            "updated_at": appointment["updated_at"],
        }
    }), 201


# ============================================================================
# 2. LIST MY APPOINTMENTS (GET /api/appointments)
# ============================================================================

@appointments_bp.route("", methods=["GET"])
@farmer_required
def list_appointments():
    """
    Retrieves all appointments booked by the authenticated farmer.
    Strictly isolated by farmer_id; never accepts client query parameters to view others.
    """
    farmer_id = g.current_user["id"]
    db = get_db()

    rows = db.execute(
        """
        SELECT id, farmer_id, land_details, address, preferred_date, preferred_time, notes, status, created_at, updated_at
        FROM appointments
        WHERE farmer_id = ?
        ORDER BY created_at DESC, id DESC
        """,
        (farmer_id,),
    ).fetchall()

    appointment_list = [
        {
            "id": row["id"],
            "farmer_id": row["farmer_id"],
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
        "appointments": appointment_list
    }), 200


# ============================================================================
# 3. VIEW ONE APPOINTMENT (GET /api/appointments/<int:appointment_id>)
# ============================================================================

@appointments_bp.route("/<int:appointment_id>", methods=["GET"])
@farmer_required
def get_appointment(appointment_id):
    """
    Retrieves a single appointment by ID.
    Enforces strict ownership: if the appointment does not exist OR belongs
    to another farmer, returns HTTP 404 Not Found to prevent ID enumeration.
    """
    farmer_id = g.current_user["id"]
    db = get_db()

    appointment = db.execute(
        """
        SELECT id, farmer_id, land_details, address, preferred_date, preferred_time, notes, status, created_at, updated_at
        FROM appointments
        WHERE id = ?
        """,
        (appointment_id,),
    ).fetchone()

    # Ownership check: return 404 if missing or if owned by another farmer (anti-IDOR)
    if appointment is None or appointment["farmer_id"] != farmer_id:
        return error_response(
            code="NOT_FOUND",
            message="Appointment not found.",
            status_code=404,
        )

    return jsonify({
        "status": "success",
        "appointment": {
            "id": appointment["id"],
            "farmer_id": appointment["farmer_id"],
            "land_details": appointment["land_details"],
            "address": appointment["address"],
            "preferred_date": appointment["preferred_date"],
            "preferred_time": appointment["preferred_time"],
            "notes": appointment["notes"],
            "status": appointment["status"],
            "created_at": appointment["created_at"],
            "updated_at": appointment["updated_at"],
        }
    }), 200

