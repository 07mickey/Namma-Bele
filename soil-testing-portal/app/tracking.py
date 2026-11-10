from datetime import datetime, timezone
from flask import Blueprint, g, jsonify, request

from app.auth import login_required, field_worker_required, admin_required, error_response
from app.db import get_db
from app.services.tracking_service import (
    build_full_timeline,
    get_or_create_soil_sample,
    record_sample_event,
)

tracking_bp = Blueprint("tracking", __name__, url_prefix="/api")


# ============================================================================
# 1. TIMELINE TRACKING ENDPOINTS
# ============================================================================

@tracking_bp.route("/tracking/appointment/<int:appointment_id>", methods=["GET"])
@login_required
def get_appointment_timeline(appointment_id):
    """
    Returns the comprehensive 13-stage timeline for a given appointment.
    Ensures strict role-based access control and sanitizes sensitive data:
    - Farmers: can only access their own appointments (returns 404 on unowned to prevent enumeration).
    - Field workers: can only access appointments where a field visit is assigned to them.
    - Laboratory staff: can only access samples assigned to their designated laboratory.
    - Operators, Administrators, Advisors: authorized for system oversight.
    """
    db = get_db()
    appt = db.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,)).fetchone()
    if not appt:
        return error_response("NOT_FOUND", "Appointment or tracking timeline not found.", 404)

    user = g.current_user
    role = user["role"]

    # Role-based authorization
    if role == "farmer":
        if appt["farmer_id"] != user["id"]:
            return error_response("NOT_FOUND", "Appointment or tracking timeline not found.", 404)
    elif role == "field_worker":
        visit = db.execute(
            "SELECT assigned_worker_id FROM field_visits WHERE appointment_id = ?",
            (appointment_id,),
        ).fetchone()
        if not visit or visit["assigned_worker_id"] != user["id"]:
            return error_response("FORBIDDEN", "Unauthorized access: Field worker is not assigned to this appointment.", 403)
    elif role == "lab_staff":
        sample = db.execute(
            "SELECT assigned_lab_id FROM soil_samples WHERE appointment_id = ?",
            (appointment_id,),
        ).fetchone()
        if user.get("laboratory_id") and sample and sample["assigned_lab_id"] != user["laboratory_id"]:
            return error_response("FORBIDDEN", "Unauthorized access: Sample is assigned to a different laboratory.", 403)
    elif role not in ("admin", "operator", "advisor"):
        return error_response("FORBIDDEN", "Access denied.", 403)

    # Ensure sample record exists for timeline tracking
    get_or_create_soil_sample(db, appointment_id)
    timeline_data = build_full_timeline(db, appointment_id)

    # Privacy and security sanitization:
    # 1. Appointment metadata
    appt_meta = {
        "id": appt["id"],
        "land_details": appt["land_details"],
        "preferred_date": appt["preferred_date"],
        "preferred_time": appt["preferred_time"],
        "status": appt["status"],
        "created_at": appt["created_at"],
    }
    # Only the farmer, admin, or call-center operator may access postal residential address
    if role in ("farmer", "admin", "operator"):
        appt_meta["farmer_id"] = appt["farmer_id"]
        appt_meta["address"] = appt["address"]

    timeline_data["appointment"] = appt_meta

    # 2. Sanitize visit details: strip internal staff notes for non-admin/non-operator
    if timeline_data.get("visit"):
        v = dict(timeline_data["visit"])
        if role in ("farmer", "lab_staff"):
            v.pop("worker_notes", None)
        timeline_data["visit"] = v

    # 3. Sanitize dispatch details: exclude private address snapshots from field/lab staff
    if timeline_data.get("dispatch"):
        d = dict(timeline_data["dispatch"])
        d.pop("notes", None)
        if role in ("field_worker", "lab_staff"):
            d.pop("delivery_address_snapshot", None)
            d.pop("recipient_name", None)
            d.pop("recipient_phone", None)
        timeline_data["dispatch"] = d

    return jsonify({"status": "success", "timeline": timeline_data}), 200


@tracking_bp.route("/tracking/sample/<sample_code>", methods=["GET"])
@login_required
def get_sample_timeline(sample_code):
    """
    Looks up tracking timeline by unique sample code (e.g. SMP-2026-00001).
    Validates ownership to prevent enumeration.
    """
    db = get_db()
    sample = db.execute("SELECT * FROM soil_samples WHERE sample_code = ?", (sample_code.strip(),)).fetchone()
    if not sample:
        return error_response("NOT_FOUND", "Sample tracking record not found.", 404)

    user = g.current_user
    if user["role"] == "farmer":
        appt = db.execute("SELECT farmer_id FROM appointments WHERE id = ?", (sample["appointment_id"],)).fetchone()
        if not appt or appt["farmer_id"] != user["id"]:
            return error_response("NOT_FOUND", "Sample tracking record not found.", 404)

    return get_appointment_timeline(sample["appointment_id"])


# ============================================================================
# 2. FIELD WORKER ASSIGNMENT & VISIT ENDPOINTS
# ============================================================================

@tracking_bp.route("/admin/field-workers", methods=["GET"])
@login_required
def list_field_workers():
    """Lists all active field workers for task assignment."""
    if g.current_user["role"] not in ("admin", "operator"):
        return error_response("FORBIDDEN", "Staff privileges required.", 403)

    db = get_db()
    workers = db.execute(
        "SELECT id, name, phone, role FROM users WHERE role = 'field_worker' ORDER BY name ASC"
    ).fetchall()

    return jsonify({
        "status": "success",
        "field_workers": [dict(w) for w in workers]
    }), 200


@tracking_bp.route("/admin/appointments/<int:appointment_id>/assign", methods=["POST"])
@login_required
def assign_field_worker(appointment_id):
    """
    Assigns a designated field worker and confirms scheduled visit slot.
    Triggers Stage 3 (FIELD_WORKER_ASSIGNED) and Stage 4 (VISIT_SCHEDULED).
    """
    if g.current_user["role"] not in ("admin", "operator"):
        return error_response("FORBIDDEN", "Staff privileges required.", 403)

    data = request.get_json(silent=True) or {}
    worker_id = data.get("worker_id")
    scheduled_date = data.get("scheduled_date")
    scheduled_slot = data.get("scheduled_slot", "09:00-12:00")

    db = get_db()
    appt = db.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,)).fetchone()
    if not appt:
        return error_response("NOT_FOUND", "Appointment not found.", 404)

    if not scheduled_date:
        scheduled_date = appt["preferred_date"]

    worker = None
    if worker_id:
        worker = db.execute(
            "SELECT id, name, phone FROM users WHERE id = ? AND role = 'field_worker'",
            (worker_id,),
        ).fetchone()
        if not worker:
            return error_response("NOT_FOUND", "Field worker not found.", 404)

    with db:
        # Update or create field visit record
        visit = db.execute("SELECT id FROM field_visits WHERE appointment_id = ?", (appointment_id,)).fetchone()
        if visit:
            db.execute(
                """
                UPDATE field_visits 
                SET assigned_worker_id = ?, scheduled_date = ?, scheduled_slot = ?, visit_status = 'Scheduled'
                WHERE id = ?
                """,
                (worker_id, scheduled_date, scheduled_slot, visit["id"]),
            )
            visit_id = visit["id"]
        else:
            cur = db.execute(
                """
                INSERT INTO field_visits (appointment_id, assigned_worker_id, scheduled_date, scheduled_slot, visit_status)
                VALUES (?, ?, ?, ?, 'Scheduled')
                """,
                (appointment_id, worker_id, scheduled_date, scheduled_slot),
            )
            visit_id = cur.lastrowid

        # Make sure appointment status is Approved
        if appt["status"] == "Pending":
            db.execute("UPDATE appointments SET status = 'Approved', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (appointment_id,))

        sample = get_or_create_soil_sample(db, appointment_id)

        # Emit events
        if worker:
            record_sample_event(
                db,
                sample_id=sample["id"],
                stage_number=3,
                status="COMPLETED",
                actor_user_id=g.current_user["id"],
                actor_role=g.current_user["role"],
                department="Field Operations",
                description=f"Field technician {worker['name']} ({worker['phone']}) assigned to collect soil sample.",
                details_dict={"worker_id": worker["id"], "worker_name": worker["name"]},
            )

        record_sample_event(
            db,
            sample_id=sample["id"],
            stage_number=4,
            status="COMPLETED",
            actor_user_id=g.current_user["id"],
            actor_role=g.current_user["role"],
            department="Field Operations",
            description=f"Field visit scheduled for {scheduled_date} in slot {scheduled_slot}.",
            details_dict={"scheduled_date": scheduled_date, "scheduled_slot": scheduled_slot},
        )

    return jsonify({
        "status": "success",
        "message": "Field visit assigned successfully.",
        "visit_id": visit_id,
        "sample_code": sample["sample_code"],
    }), 200


@tracking_bp.route("/field-worker/visits", methods=["GET"])
@field_worker_required
def list_field_worker_visits():
    """
    Lists field visits assigned to the authenticated field worker (or all for admin).
    """
    user = g.current_user
    db = get_db()

    query_status = request.args.get("status")

    if user["role"] == "admin":
        where_clauses = ["1=1"]
        params = []
    else:
        where_clauses = ["v.assigned_worker_id = ?"]
        params = [user["id"]]

    if query_status:
        where_clauses.append("v.visit_status = ?")
        params.append(query_status)

    sql = f"""
        SELECT v.id AS visit_id, v.appointment_id, v.scheduled_date, v.scheduled_slot,
               v.visit_status, v.survey_number, v.gps_latitude, v.gps_longitude,
               v.worker_notes, v.completed_at,
               a.farmer_id, u.name AS farmer_name, u.phone AS farmer_phone,
               a.land_details,
               s.id AS sample_id, s.sample_code, s.sample_status
        FROM field_visits v
        JOIN appointments a ON v.appointment_id = a.id
        JOIN users u ON a.farmer_id = u.id
        LEFT JOIN soil_samples s ON s.appointment_id = a.id
        WHERE {' AND '.join(where_clauses)}
        ORDER BY v.scheduled_date ASC, v.id ASC
    """
    rows = db.execute(sql, params).fetchall()

    return jsonify({
        "status": "success",
        "count": len(rows),
        "visits": [dict(r) for r in rows],
    }), 200


@tracking_bp.route("/field-worker/visits/<int:visit_id>/collect", methods=["POST"])
@field_worker_required
def log_sample_collection(visit_id):
    """
    Field worker logs the actual on-site soil sample collection:
    - Sets visit_status to 'Completed'
    - Records sampling depth (e.g. 15cm), soil appearance, GPS coordinates
    - Sets sample_status to 'In_Transit'
    - Emits Stage 5 (SAMPLE_COLLECTED) and Stage 6 (SAMPLE_IN_TRANSIT)
    """
    data = request.get_json(silent=True) or {}
    depth_cm = float(data.get("sampling_depth_cm", 15.0))
    appearance = data.get("soil_appearance", "Red Sandy Loam, core composite").strip()
    notes = data.get("worker_notes", "").strip()
    survey_number = data.get("survey_number", "").strip()
    gps_lat = data.get("gps_latitude")
    gps_lng = data.get("gps_longitude")

    db = get_db()
    visit = db.execute("SELECT * FROM field_visits WHERE id = ?", (visit_id,)).fetchone()
    if not visit:
        return error_response("NOT_FOUND", "Field visit not found.", 404)

    user = g.current_user
    if user["role"] != "admin" and visit["assigned_worker_id"] != user["id"]:
        return error_response("FORBIDDEN", "You are not assigned to this field visit.", 403)

    sample = get_or_create_soil_sample(db, visit["appointment_id"])

    with db:
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # Update visit
        db.execute(
            """
            UPDATE field_visits
            SET visit_status = 'Completed', completed_at = ?,
                gps_latitude = ?, gps_longitude = ?, survey_number = ?, worker_notes = ?
            WHERE id = ?
            """,
            (now_str, gps_lat, gps_lng, survey_number or visit["survey_number"], notes, visit_id),
        )

        # Update soil sample
        db.execute(
            """
            UPDATE soil_samples
            SET visit_id = ?, sample_status = 'In_Transit', sampling_depth_cm = ?,
                soil_appearance = ?, collected_at = ?
            WHERE id = ?
            """,
            (visit_id, depth_cm, appearance, now_str, sample["id"]),
        )

        # Stage 5: SAMPLE_COLLECTED
        record_sample_event(
            db,
            sample_id=sample["id"],
            stage_number=5,
            status="COMPLETED",
            actor_user_id=user["id"],
            actor_role="field_worker",
            department="Field Operations",
            description=f"Soil sample extracted at {depth_cm} cm depth ({appearance}).",
            details_dict={
                "depth_cm": depth_cm,
                "appearance": appearance,
                "gps": f"{gps_lat}, {gps_lng}" if gps_lat and gps_lng else None,
                "survey_number": survey_number,
                "notes": notes,
            },
        )

        # Stage 6: SAMPLE_IN_TRANSIT
        record_sample_event(
            db,
            sample_id=sample["id"],
            stage_number=6,
            status="COMPLETED",
            actor_user_id=user["id"],
            actor_role="field_worker",
            department="Logistics & Transport",
            description=f"Sample {sample['sample_code']} sealed and dispatched in tamper-evident container.",
            details_dict={"sample_code": sample["sample_code"]},
        )

    return jsonify({
        "status": "success",
        "message": f"Sample collection logged for {sample['sample_code']}.",
        "sample_code": sample["sample_code"],
        "visit_status": "Completed",
        "sample_status": "In_Transit",
    }), 200

