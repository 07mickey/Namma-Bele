import json
import re
from datetime import datetime, timezone
from flask import Blueprint, g, jsonify, request
from werkzeug.security import generate_password_hash

from app.auth import operator_required, error_response, normalize_phone, E164_REGEX
from app.db import get_db
from app.services.tracking_service import get_or_create_soil_sample, record_sample_event

operator_bp = Blueprint("operator", __name__, url_prefix="/api/operator")

DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def log_operator_action(db, action, target_type, target_id, details=None):
    """Writes an immutable log entry into operator_audit_logs."""
    actor = g.current_user
    ip = request.remote_addr if request else "127.0.0.1"
    details_json = json.dumps(details) if details else None
    db.execute(
        """
        INSERT INTO operator_audit_logs (actor_user_id, actor_role, action, target_entity_type, target_entity_id, details_json, ip_address)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (actor["id"], actor["role"], action, target_type, target_id, details_json, ip),
    )


@operator_bp.route("/farmers", methods=["POST"])
@operator_required
def register_assisted_farmer():
    """
    Operator registers a farmer without requiring them to set a web password.
    Creates account with account_status='UNCLAIMED'.
    Optionally records initial delivery address and farm plot.
    """
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return error_response("MALFORMED_REQUEST", "Request body must be a valid JSON object.", 400)

    name = data.get("name", "").strip()
    raw_phone = data.get("phone", "")
    language = data.get("preferred_language", "en").strip()

    if not name:
        return error_response("VALIDATION_ERROR", "Farmer name is required.", 400, {"field": "name"})

    clean_phone = normalize_phone(raw_phone)
    if not clean_phone or not E164_REGEX.match(clean_phone):
        return error_response("VALIDATION_ERROR", "Valid E.164 phone number required.", 400, {"field": "phone"})

    db = get_db()
    existing = db.execute("SELECT id, name, role FROM users WHERE phone = ?", (clean_phone,)).fetchone()
    if existing:
        return error_response(
            "CONFLICT",
            f"An account with phone number {clean_phone} already exists (Name: {existing['name']}).",
            409,
            {"field": "phone"},
        )

    # Secure random dummy hash; account cannot be authenticated until activated
    dummy_hash = generate_password_hash("UNCLAIMED_ASSISTED_REGISTRATION_" + clean_phone)

    with db:
        cursor = db.execute(
            """
            INSERT INTO users (name, phone, password_hash, role, account_status, created_by_user_id, preferred_language)
            VALUES (?, ?, ?, 'farmer', 'UNCLAIMED', ?, ?)
            """,
            (name, clean_phone, dummy_hash, g.current_user["id"], language),
        )
        farmer_id = cursor.lastrowid

        # Optional initial delivery address
        addr_data = data.get("address")
        address_id = None
        if addr_data and isinstance(addr_data, dict):
            house = addr_data.get("house_details", "Assisted Registration").strip()
            village = addr_data.get("street_or_village", "Main Village").strip()
            taluk = addr_data.get("taluk", "Default Taluk").strip()
            district = addr_data.get("district", "Default District").strip()
            pincode = addr_data.get("pincode", "571401").strip()
            state = addr_data.get("state", "Karnataka").strip()
            recipient_name = addr_data.get("recipient_name", name).strip()
            recipient_phone = normalize_phone(addr_data.get("recipient_phone", clean_phone))

            addr_cursor = db.execute(
                """
                INSERT INTO farmer_delivery_addresses (
                    farmer_id, recipient_name, recipient_phone, house_details,
                    street_or_village, taluk, district, state, pincode, is_default
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (farmer_id, recipient_name, recipient_phone, house, village, taluk, district, state, pincode),
            )
            address_id = addr_cursor.lastrowid

        # Optional initial plot
        plot_data = data.get("plot")
        plot_id = None
        if plot_data and isinstance(plot_data, dict):
            plot_name = plot_data.get("plot_name", "Main Farm Plot").strip()
            survey_no = plot_data.get("survey_number", "SN-01").strip()
            area = float(plot_data.get("area", 2.0))
            area_unit = plot_data.get("area_unit", "Acres").strip()
            soil_type = plot_data.get("soil_type", "Red Sandy Loam").strip()
            irrigation = plot_data.get("irrigation_source", "Rainfed").strip()

            plot_cursor = db.execute(
                """
                INSERT INTO farm_plots (farmer_id, plot_name, survey_number, area, area_unit, soil_type, irrigation_source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (farmer_id, plot_name, survey_no, area, area_unit, soil_type, irrigation),
            )
            plot_id = plot_cursor.lastrowid

        log_operator_action(
            db,
            action="ASSISTED_FARMER_REGISTRATION",
            target_type="user",
            target_id=farmer_id,
            details={"phone": clean_phone, "name": name, "address_id": address_id, "plot_id": plot_id},
        )

    return jsonify({
        "status": "success",
        "message": f"Farmer account created successfully for {name} ({clean_phone}). Status: UNCLAIMED.",
        "farmer": {
            "id": farmer_id,
            "name": name,
            "phone": clean_phone,
            "account_status": "UNCLAIMED",
            "preferred_language": language,
            "address_id": address_id,
            "plot_id": plot_id,
        }
    }), 201


@operator_bp.route("/farmers/search", methods=["GET"])
@operator_required
def search_farmers():
    """
    Search for registered farmers by phone, name, or survey number to prevent duplicates.
    """
    phone_query = request.args.get("phone", "").strip()
    name_query = request.args.get("name", "").strip()
    general_query = request.args.get("q", "").strip()

    db = get_db()
    params = []
    where_clauses = ["role = 'farmer'"]

    if phone_query:
        clean_phone = normalize_phone(phone_query)
        where_clauses.append("phone LIKE ?")
        params.append(f"%{clean_phone}%")
    elif name_query:
        where_clauses.append("name LIKE ?")
        params.append(f"%{name_query}%")
    elif general_query:
        clean_q = normalize_phone(general_query) if general_query.startswith("+") or general_query.isdigit() else general_query
        where_clauses.append("(name LIKE ? OR phone LIKE ?)")
        params.extend([f"%{clean_q}%", f"%{clean_q}%"])

    sql = f"""
        SELECT id, name, phone, account_status, preferred_language, created_at
        FROM users
        WHERE {' AND '.join(where_clauses)}
        ORDER BY id DESC
        LIMIT 25
    """
    farmers = [dict(row) for row in db.execute(sql, params).fetchall()]

    # Attach summary of addresses and plots
    for f in farmers:
        addr = db.execute(
            "SELECT id, recipient_name, house_details, street_or_village, taluk, district, pincode, is_default FROM farmer_delivery_addresses WHERE farmer_id = ? AND is_default = 1",
            (f["id"],),
        ).fetchone()
        f["default_address"] = dict(addr) if addr else None

        plots = db.execute(
            "SELECT id, plot_name, survey_number, area, area_unit FROM farm_plots WHERE farmer_id = ?",
            (f["id"],),
        ).fetchall()
        f["plots"] = [dict(p) for p in plots]

    return jsonify({
        "status": "success",
        "count": len(farmers),
        "farmers": farmers,
    }), 200


@operator_bp.route("/appointments", methods=["POST"])
@operator_required
def assisted_book_appointment():
    """
    Operator books an appointment on behalf of a farmer.
    Accepts farmer_id, plot_id or land_details, address or delivery_address_id, date, and slot.
    """
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return error_response("MALFORMED_REQUEST", "Request body must be a valid JSON object.", 400)

    farmer_id = data.get("farmer_id")
    if not farmer_id:
        return error_response("VALIDATION_ERROR", "farmer_id is required.", 400, {"field": "farmer_id"})

    preferred_date = data.get("preferred_date", "").strip()
    if not preferred_date or not DATE_REGEX.match(preferred_date):
        return error_response("VALIDATION_ERROR", "Valid preferred_date (YYYY-MM-DD) is required.", 400, {"field": "preferred_date"})

    preferred_time = data.get("preferred_time", "09:00-12:00").strip()
    if preferred_time not in ("09:00-12:00", "14:00-17:00"):
        return error_response("VALIDATION_ERROR", "preferred_time must be '09:00-12:00' or '14:00-17:00'.", 400)

    land_details = data.get("land_details", "").strip()
    plot_id = data.get("plot_id")
    address = data.get("address", "").strip()
    delivery_address_id = data.get("delivery_address_id")
    notes = data.get("notes", "Assisted booking via service operator").strip()

    db = get_db()
    farmer = db.execute("SELECT id, name, phone FROM users WHERE id = ? AND role = 'farmer'", (farmer_id,)).fetchone()
    if not farmer:
        return error_response("NOT_FOUND", "Farmer not found.", 404)

    # Resolve plot if plot_id provided
    if plot_id:
        plot = db.execute("SELECT * FROM farm_plots WHERE id = ? AND farmer_id = ?", (plot_id, farmer_id)).fetchone()
        if plot and not land_details:
            land_details = f"Plot: {plot['plot_name']} (Survey #{plot['survey_number']}, {plot['area']} {plot['area_unit']}, Soil: {plot['soil_type']})"

    if not land_details:
        land_details = f"Assisted booking for farmer {farmer['name']} (Survey details pending verification)"

    # Resolve delivery address
    if delivery_address_id:
        addr = db.execute("SELECT * FROM farmer_delivery_addresses WHERE id = ? AND farmer_id = ?", (delivery_address_id, farmer_id)).fetchone()
        if addr and not address:
            address = f"{addr['house_details']}, {addr['street_or_village']}, {addr['taluk']}, {addr['district']} - {addr['pincode']}"

    if not address:
        # Check if farmer has default address
        addr = db.execute("SELECT * FROM farmer_delivery_addresses WHERE farmer_id = ? AND is_default = 1", (farmer_id,)).fetchone()
        if addr:
            address = f"{addr['house_details']}, {addr['street_or_village']}, {addr['taluk']}, {addr['district']} - {addr['pincode']}"
            delivery_address_id = addr["id"]
        else:
            address = f"Village residence of {farmer['name']} ({farmer['phone']})"

    with db:
        cursor = db.execute(
            """
            INSERT INTO appointments (
                farmer_id, land_details, address, preferred_date, preferred_time, notes, status,
                plot_id, delivery_address_id
            ) VALUES (?, ?, ?, ?, ?, ?, 'Approved', ?, ?)
            """,
            (farmer_id, land_details, address, preferred_date, preferred_time, notes, plot_id, delivery_address_id),
        )
        appointment_id = cursor.lastrowid

        # Automatically schedule field visit
        db.execute(
            """
            INSERT OR REPLACE INTO field_visits (appointment_id, scheduled_date, scheduled_slot, visit_status)
            VALUES (?, ?, ?, 'Scheduled')
            """,
            (appointment_id, preferred_date, preferred_time),
        )

        # Generate soil sample and record initial stages
        sample = get_or_create_soil_sample(db, appointment_id)
        record_sample_event(
            db,
            sample_id=sample["id"],
            stage_number=1,
            status="COMPLETED",
            actor_user_id=g.current_user["id"],
            actor_role="operator",
            department="Customer Service",
            description=f"Assisted appointment booked by operator for {farmer['name']}.",
        )
        record_sample_event(
            db,
            sample_id=sample["id"],
            stage_number=2,
            status="COMPLETED",
            actor_user_id=g.current_user["id"],
            actor_role="operator",
            department="Operations Planning",
            description=f"Appointment automatically confirmed for {preferred_date} ({preferred_time}).",
        )
        record_sample_event(
            db,
            sample_id=sample["id"],
            stage_number=4,
            status="COMPLETED",
            actor_user_id=g.current_user["id"],
            actor_role="operator",
            department="Field Operations",
            description=f"Field visit scheduled for {preferred_date} slot {preferred_time}.",
        )

        log_operator_action(
            db,
            action="ASSISTED_APPOINTMENT_BOOKED",
            target_type="appointment",
            target_id=appointment_id,
            details={"farmer_id": farmer_id, "date": preferred_date, "slot": preferred_time},
        )

    return jsonify({
        "status": "success",
        "message": f"Appointment booked and confirmed for {farmer['name']}.",
        "appointment_id": appointment_id,
        "sample_code": sample["sample_code"],
        "status": "Approved",
    }), 201


@operator_bp.route("/audit-logs", methods=["GET"])
@operator_required
def get_audit_logs():
    """Returns recent operator audit events."""
    db = get_db()
    rows = db.execute(
        """
        SELECT l.id, l.actor_user_id, u.name AS actor_name, l.actor_role,
               l.action, l.target_entity_type, l.target_entity_id, l.details_json, l.ip_address, l.created_at
        FROM operator_audit_logs l
        LEFT JOIN users u ON l.actor_user_id = u.id
        ORDER BY l.id DESC
        LIMIT 50
        """
    ).fetchall()

    logs = []
    for r in rows:
        d = dict(r)
        if d["details_json"]:
            try:
                d["details"] = json.loads(d["details_json"])
            except Exception:
                d["details"] = d["details_json"]
        logs.append(d)

    return jsonify({"status": "success", "count": len(logs), "logs": logs}), 200

