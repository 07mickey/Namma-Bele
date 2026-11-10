import json
from datetime import datetime, timezone
from flask import Blueprint, g, jsonify, request

from app.auth import lab_staff_required, admin_required, login_required, error_response
from app.db import get_db
from app.services.tracking_service import record_sample_event

lab_bp = Blueprint("lab", __name__, url_prefix="/api/lab")


def calculate_scientific_ratings(ph, ec, oc, n, p, k):
    """
    Computes standard ICAR / Agricultural University soil health index ratings.
    """
    # pH
    if ph < 6.0:
        ph_rating = "Acidic"
    elif ph <= 7.5:
        ph_rating = "Neutral / Optimal"
    else:
        ph_rating = "Alkaline"

    # Electrical Conductivity (dS/m)
    if ec < 1.0:
        ec_rating = "Normal"
    elif ec <= 2.0:
        ec_rating = "Critical"
    else:
        ec_rating = "Saline / Injurious"

    # Organic Carbon (%)
    if oc < 0.50:
        oc_rating = "Low"
    elif oc <= 0.75:
        oc_rating = "Medium"
    else:
        oc_rating = "High"

    # Nitrogen (kg/ha)
    if n < 280.0:
        n_rating = "Low"
    elif n <= 560.0:
        n_rating = "Medium"
    else:
        n_rating = "High"

    # Phosphorus (kg/ha)
    if p < 23.0:
        p_rating = "Low"
    elif p <= 56.0:
        p_rating = "Medium"
    else:
        p_rating = "High"

    # Potassium (kg/ha)
    if k < 145.0:
        k_rating = "Low"
    elif k <= 337.0:
        k_rating = "Medium"
    else:
        k_rating = "High"

    return {
        "ph_rating": ph_rating,
        "ec_rating": ec_rating,
        "oc_rating": oc_rating,
        "n_rating": n_rating,
        "p_rating": p_rating,
        "k_rating": k_rating,
    }


@lab_bp.route("/samples", methods=["GET"])
@lab_staff_required
def list_lab_samples():
    """
    Lists samples in the laboratory pipeline.
    """
    db = get_db()
    status_filter = request.args.get("status")

    where_clauses = ["1=1"]
    params = []

    if status_filter:
        where_clauses.append("s.sample_status = ?")
        params.append(status_filter)

    sql = f"""
        SELECT s.id AS sample_id, s.sample_code, s.appointment_id, s.sample_status,
               s.sampling_depth_cm, s.soil_appearance, s.collected_at,
               l.name AS lab_name, l.code AS lab_code,
               a.farmer_id, u.name AS farmer_name,
               a.land_details,
               assay.id AS assay_id, assay.lab_status AS assay_status,
               assay.ph_value, assay.ec_ds_m, assay.organic_carbon_pct,
               assay.nitrogen_kg_ha, assay.phosphorus_kg_ha, assay.potassium_kg_ha
        FROM soil_samples s
        LEFT JOIN laboratories l ON s.assigned_lab_id = l.id
        JOIN appointments a ON s.appointment_id = a.id
        JOIN users u ON a.farmer_id = u.id
        LEFT JOIN lab_test_assays assay ON assay.sample_id = s.id
        WHERE {' AND '.join(where_clauses)}
        ORDER BY s.id DESC
    """
    rows = db.execute(sql, params).fetchall()

    return jsonify({
        "status": "success",
        "count": len(rows),
        "samples": [dict(r) for r in rows],
    }), 200


@lab_bp.route("/samples/<int:sample_id>/receive", methods=["POST"])
@lab_staff_required
def receive_sample_at_lab(sample_id):
    """
    Lab staff checks in physical soil sample at testing laboratory.
    Emits Stage 7: SAMPLE_RECEIVED_LAB.
    """
    db = get_db()
    sample = db.execute("SELECT * FROM soil_samples WHERE id = ?", (sample_id,)).fetchone()
    if not sample:
        return error_response("NOT_FOUND", "Sample not found.", 404)

    user = g.current_user
    with db:
        db.execute(
            "UPDATE soil_samples SET sample_status = 'Received' WHERE id = ?",
            (sample_id,),
        )

        record_sample_event(
            db,
            sample_id=sample_id,
            stage_number=7,
            status="COMPLETED",
            actor_user_id=user["id"],
            actor_role=user["role"],
            department="Laboratory Services",
            description=f"Sample {sample['sample_code']} checked in and catalogued at laboratory.",
            details_dict={"sample_code": sample["sample_code"]},
        )

    return jsonify({
        "status": "success",
        "message": f"Sample {sample['sample_code']} received at laboratory.",
        "sample_status": "Received",
    }), 200


@lab_bp.route("/samples/<int:sample_id>/start-test", methods=["POST"])
@lab_staff_required
def start_lab_testing(sample_id):
    """
    Lab staff marks sample under active preparation and chemical analysis.
    Emits Stage 8: LAB_ANALYSIS_IN_PROGRESS.
    """
    db = get_db()
    sample = db.execute("SELECT * FROM soil_samples WHERE id = ?", (sample_id,)).fetchone()
    if not sample:
        return error_response("NOT_FOUND", "Sample not found.", 404)

    user = g.current_user
    with db:
        db.execute(
            "UPDATE soil_samples SET sample_status = 'Testing' WHERE id = ?",
            (sample_id,),
        )

        record_sample_event(
            db,
            sample_id=sample_id,
            stage_number=8,
            status="COMPLETED",
            actor_user_id=user["id"],
            actor_role=user["role"],
            department="Laboratory Services",
            description=f"Sample {sample['sample_code']} prepared for chemical assay (drying, 2mm sieving, titration).",
            details_dict={"sample_code": sample["sample_code"]},
        )

    return jsonify({
        "status": "success",
        "message": "Sample testing commenced.",
        "sample_status": "Testing",
    }), 200


@lab_bp.route("/samples/<int:sample_id>/assay", methods=["POST"])
@lab_staff_required
def record_test_assay(sample_id):
    """
    Records laboratory chemical test measurements:
    - pH value (0-14)
    - Electrical Conductivity (dS/m)
    - Organic Carbon (%)
    - Available Nitrogen (kg/ha)
    - Available Phosphorus (kg/ha)
    - Available Potassium (kg/ha)
    Calculates scientific index ratings.
    Emits Stage 9 (TEST_RESULTS_RECORDED) and Stage 10 (REPORT_UNDER_REVIEW).
    """
    data = request.get_json(silent=True) or {}
    try:
        ph = float(data.get("ph_value"))
        ec = float(data.get("ec_ds_m"))
        oc = float(data.get("organic_carbon_pct"))
        n = float(data.get("nitrogen_kg_ha"))
        p = float(data.get("phosphorus_kg_ha"))
        k = float(data.get("potassium_kg_ha"))
    except (TypeError, ValueError):
        return error_response("VALIDATION_ERROR", "All 6 chemical parameters (pH, EC, OC, N, P, K) must be valid numbers.", 400)

    if not (0.0 <= ph <= 14.0):
        return error_response("VALIDATION_ERROR", "pH must be between 0.0 and 14.0.", 400)
    if ec < 0.0:
        return error_response("VALIDATION_ERROR", "EC must be non-negative.", 400)
    if not (0.0 <= oc <= 100.0):
        return error_response("VALIDATION_ERROR", "Organic Carbon must be between 0% and 100%.", 400)
    if n < 0.0 or p < 0.0 or k < 0.0:
        return error_response("VALIDATION_ERROR", "N, P, and K values must be non-negative.", 400)

    remarks = data.get("remarks", "Standard spectrophotometric and flame photometer analysis").strip()

    db = get_db()
    sample = db.execute("SELECT * FROM soil_samples WHERE id = ?", (sample_id,)).fetchone()
    if not sample:
        return error_response("NOT_FOUND", "Sample not found.", 404)

    lab_id = sample["assigned_lab_id"] or 1
    ratings = calculate_scientific_ratings(ph, ec, oc, n, p, k)

    user = g.current_user
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    with db:
        # Check if assay already exists
        existing_assay = db.execute("SELECT id, lab_status FROM lab_test_assays WHERE sample_id = ?", (sample_id,)).fetchone()
        if existing_assay:
            if existing_assay["lab_status"] == "Authorized":
                return error_response("FORBIDDEN", "Authorized laboratory results are locked and cannot be modified.", 403)
            db.execute(
                """
                UPDATE lab_test_assays
                SET ph_value = ?, ec_ds_m = ?, organic_carbon_pct = ?,
                    nitrogen_kg_ha = ?, phosphorus_kg_ha = ?, potassium_kg_ha = ?,
                    ph_rating = ?, ec_rating = ?, oc_rating = ?,
                    n_rating = ?, p_rating = ?, k_rating = ?,
                    remarks = ?, lab_status = 'Submitted', tested_by_user_id = ?, completed_at = ?
                WHERE id = ?
                """,
                (ph, ec, oc, n, p, k, ratings["ph_rating"], ratings["ec_rating"], ratings["oc_rating"],
                 ratings["n_rating"], ratings["p_rating"], ratings["k_rating"], remarks, user["id"], now_str, existing_assay["id"]),
            )
            assay_id = existing_assay["id"]
        else:
            cur = db.execute(
                """
                INSERT INTO lab_test_assays (
                    sample_id, lab_id, tested_by_user_id, ph_value, ec_ds_m, organic_carbon_pct,
                    nitrogen_kg_ha, phosphorus_kg_ha, potassium_kg_ha,
                    ph_rating, ec_rating, oc_rating, n_rating, p_rating, k_rating,
                    remarks, lab_status, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Submitted', ?)
                """,
                (sample_id, lab_id, user["id"], ph, ec, oc, n, p, k,
                 ratings["ph_rating"], ratings["ec_rating"], ratings["oc_rating"],
                 ratings["n_rating"], ratings["p_rating"], ratings["k_rating"],
                 remarks, now_str),
            )
            assay_id = cur.lastrowid

        # Stage 9: TEST_RESULTS_RECORDED
        record_sample_event(
            db,
            sample_id=sample_id,
            stage_number=9,
            status="COMPLETED",
            actor_user_id=user["id"],
            actor_role=user["role"],
            department="Laboratory Services",
            description=f"Chemical assay complete. pH: {ph:.2f} ({ratings['ph_rating']}), OC: {oc:.2f}%, NPK: {n:.1f}/{p:.1f}/{k:.1f} kg/ha.",
            details_dict={"ph": ph, "ec": ec, "oc": oc, "n": n, "p": p, "k": k, **ratings},
        )

        # Stage 10: REPORT_UNDER_REVIEW
        record_sample_event(
            db,
            sample_id=sample_id,
            stage_number=10,
            status="COMPLETED",
            actor_user_id=user["id"],
            actor_role=user["role"],
            department="Quality Assurance",
            description="Assay submitted for scientific authorization and quality verification.",
            details_dict={"assay_id": assay_id},
        )

    return jsonify({
        "status": "success",
        "message": "Assay results recorded and queued for authorization.",
        "assay_id": assay_id,
        "ratings": ratings,
    }), 201


@lab_bp.route("/assays/<int:assay_id>/authorize", methods=["POST"])
@login_required
def authorize_assay_report(assay_id):
    """
    Authorizes the laboratory report.
    Permitted for users with role='admin' or 'lab_staff' (supervisor).
    - Sets lab_status = 'Authorized'
    - Updates appointment status = 'Completed'
    - Emits Stage 11: REPORT_AUTHORIZED
    - Automatically queues physical report for postal dispatch!
    """
    user = g.current_user
    if user["role"] not in ("admin", "lab_staff"):
        return error_response("FORBIDDEN", "Authorization privileges required.", 403)

    db = get_db()
    assay = db.execute("SELECT * FROM lab_test_assays WHERE id = ?", (assay_id,)).fetchone()
    if not assay:
        return error_response("NOT_FOUND", "Assay record not found.", 404)

    if assay["lab_status"] == "Authorized":
        return error_response("BAD_REQUEST", "Assay is already authorized and cannot be re-authorized.", 400)

    # Segregation of duties: Laboratory technicians cannot self-approve their own submitted assay
    if user["role"] == "lab_staff" and assay["tested_by_user_id"] == user["id"]:
        return error_response(
            "FORBIDDEN",
            "Segregation of duties: Laboratory technicians cannot authorize their own test assay. Review by an independent supervisor or administrator is required.",
            403,
        )

    sample = db.execute("SELECT * FROM soil_samples WHERE id = ?", (assay["sample_id"],)).fetchone()
    appt = db.execute("SELECT * FROM appointments WHERE id = ?", (sample["appointment_id"],)).fetchone()
    farmer = db.execute("SELECT id, name, phone FROM users WHERE id = ?", (appt["farmer_id"],)).fetchone()

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    with db:
        # Authorize assay
        db.execute(
            """
            UPDATE lab_test_assays
            SET lab_status = 'Authorized', authorized_by_user_id = ?, authorized_at = ?
            WHERE id = ?
            """,
            (user["id"], now_str, assay_id),
        )

        # Update appointment status to Completed
        db.execute(
            "UPDATE appointments SET status = 'Completed', updated_at = ? WHERE id = ?",
            (now_str, appt["id"]),
        )

        # Update sample status
        db.execute("UPDATE soil_samples SET sample_status = 'Completed' WHERE id = ?", (sample["id"],))

        # Stage 11: REPORT_AUTHORIZED
        record_sample_event(
            db,
            sample_id=sample["id"],
            stage_number=11,
            status="COMPLETED",
            actor_user_id=user["id"],
            actor_role=user["role"],
            department="Scientific Certification",
            description=f"Soil Health Report officially certified and authorized by {user['name']}.",
            details_dict={"authorized_by": user["name"], "assay_id": assay_id},
        )

        # Automatically queue physical report dispatch if not already created
        dispatch = db.execute("SELECT id FROM report_dispatches WHERE appointment_id = ?", (appt["id"],)).fetchone()
        if not dispatch:
            # Look up farmer's delivery address
            addr = None
            if appt["delivery_address_id"]:
                addr = db.execute("SELECT * FROM farmer_delivery_addresses WHERE id = ?", (appt["delivery_address_id"],)).fetchone()
            if not addr:
                addr = db.execute("SELECT * FROM farmer_delivery_addresses WHERE farmer_id = ? AND is_default = 1", (farmer["id"],)).fetchone()

            if addr:
                addr_snapshot = json.dumps({
                    "recipient_name": addr["recipient_name"],
                    "recipient_phone": addr["recipient_phone"],
                    "house_details": addr["house_details"],
                    "street_or_village": addr["street_or_village"],
                    "taluk": addr["taluk"],
                    "district": addr["district"],
                    "state": addr["state"],
                    "pincode": addr["pincode"],
                })
                recip_name = addr["recipient_name"]
                recip_phone = addr["recipient_phone"]
            else:
                addr_snapshot = json.dumps({
                    "recipient_name": farmer["name"],
                    "recipient_phone": farmer["phone"],
                    "address": appt["address"],
                })
                recip_name = farmer["name"]
                recip_phone = farmer["phone"]

            # Look up existing PDF report if any
            rep = db.execute("SELECT id FROM reports WHERE appointment_id = ?", (appt["id"],)).fetchone()
            report_id = rep["id"] if rep else None

            db.execute(
                """
                INSERT INTO report_dispatches (
                    report_id, appointment_id, recipient_name, recipient_phone,
                    delivery_address_snapshot, courier_service, dispatch_status
                ) VALUES (?, ?, ?, ?, ?, 'India Post Speed Post', 'Queued')
                """,
                (report_id, appt["id"], recip_name, recip_phone, addr_snapshot),
            )

    return jsonify({
        "status": "success",
        "message": "Report authorized successfully and published.",
        "assay_id": assay_id,
        "lab_status": "Authorized",
        "appointment_status": "Completed",
    }), 200
