import json
from datetime import datetime, timezone
from flask import Blueprint, g, jsonify, request

from app.auth import staff_required, login_required, error_response
from app.db import get_db
from app.services.tracking_service import record_sample_event

dispatch_bp = Blueprint("dispatch", __name__, url_prefix="/api/dispatch")


@dispatch_bp.route("/queue", methods=["GET"])
@staff_required
def list_dispatch_queue():
    """
    Lists physical report dispatch queue with filters.
    """
    db = get_db()
    status_filter = request.args.get("status")

    where = ["1=1"]
    params = []
    if status_filter:
        where.append("d.dispatch_status = ?")
        params.append(status_filter)

    sql = f"""
        SELECT d.id AS dispatch_id, d.report_id, d.appointment_id,
               d.recipient_name, d.recipient_phone, d.delivery_address_snapshot,
               d.courier_service, d.tracking_number, d.dispatch_status,
               d.dispatched_at, d.delivered_at, d.created_at,
               a.farmer_id, u.name AS farmer_name,
               s.sample_code, s.id AS sample_id
        FROM report_dispatches d
        JOIN appointments a ON d.appointment_id = a.id
        JOIN users u ON a.farmer_id = u.id
        LEFT JOIN soil_samples s ON s.appointment_id = a.id
        WHERE {' AND '.join(where)}
        ORDER BY CASE d.dispatch_status WHEN 'Queued' THEN 1 WHEN 'Printed' THEN 2 WHEN 'Dispatched' THEN 3 ELSE 4 END,
                 d.id DESC
    """
    rows = db.execute(sql, params).fetchall()

    items = []
    for r in rows:
        item = dict(r)
        if item["delivery_address_snapshot"]:
            try:
                item["address"] = json.loads(item["delivery_address_snapshot"])
            except Exception:
                item["address"] = item["delivery_address_snapshot"]
        items.append(item)

    return jsonify({"status": "success", "count": len(items), "queue": items}), 200


@dispatch_bp.route("/<int:dispatch_id>/print", methods=["POST"])
@staff_required
def mark_report_printed(dispatch_id):
    """
    Marks report as printed for postal dispatch.
    Emits Stage 12: PHYSICAL_REPORT_PRINTED.
    """
    db = get_db()
    dispatch = db.execute("SELECT * FROM report_dispatches WHERE id = ?", (dispatch_id,)).fetchone()
    if not dispatch:
        return error_response("NOT_FOUND", "Dispatch record not found.", 404)

    sample = db.execute("SELECT id, sample_code FROM soil_samples WHERE appointment_id = ?", (dispatch["appointment_id"],)).fetchone()

    with db:
        db.execute(
            "UPDATE report_dispatches SET dispatch_status = 'Printed' WHERE id = ?",
            (dispatch_id,),
        )

        if sample:
            record_sample_event(
                db,
                sample_id=sample["id"],
                stage_number=12,
                status="COMPLETED",
                actor_user_id=g.current_user["id"],
                actor_role=g.current_user["role"],
                department="Postal Logistics",
                description=f"Physical Soil Health Card printed with barcode. Addressed to: {dispatch['recipient_name']}.",
                details_dict={"dispatch_id": dispatch_id, "recipient": dispatch["recipient_name"]},
            )

    return jsonify({"status": "success", "message": "Report marked as printed.", "dispatch_status": "Printed"}), 200


@dispatch_bp.route("/<int:dispatch_id>/dispatch", methods=["POST"])
@staff_required
def mark_report_dispatched(dispatch_id):
    """
    Marks report as handed over to postal/courier service with tracking consignment number.
    """
    data = request.get_json(silent=True) or {}
    courier = data.get("courier_service", "India Post Speed Post").strip()
    tracking_no = data.get("tracking_number", "").strip().upper()

    if not tracking_no:
        return error_response("VALIDATION_ERROR", "Consignment tracking number is required.", 400)

    # Reject obvious demo and test placeholders
    demo_placeholders = {"DEMO", "TEST", "0000000000000", "EK000000000IN", "123456789"}
    if tracking_no in demo_placeholders or tracking_no.startswith("DEMO") or tracking_no.startswith("TEST"):
        return error_response(
            "VALIDATION_ERROR",
            "Demonstration or placeholder tracking numbers are prohibited in production records.",
            400,
        )

    import re
    if "SPEED POST" in courier.upper() or "INDIA POST" in courier.upper():
        # UPU S10 standard for India Post Speed Post: 2 letters, 9 digits, 2 letters (e.g. EK123456789IN)
        if not re.match(r"^[A-Z]{2}[0-9]{9}[A-Z]{2}$", tracking_no):
            return error_response(
                "VALIDATION_ERROR",
                "Invalid India Post Speed Post tracking number. Format must match 13-character standard (e.g. EK123456789IN).",
                400,
            )
    else:
        if not re.match(r"^[A-Z0-9\-]{8,30}$", tracking_no):
            return error_response(
                "VALIDATION_ERROR",
                "Invalid consignment tracking number format (8-30 alphanumeric characters).",
                400,
            )

    db = get_db()
    dispatch = db.execute("SELECT * FROM report_dispatches WHERE id = ?", (dispatch_id,)).fetchone()
    if not dispatch:
        return error_response("NOT_FOUND", "Dispatch record not found.", 404)

    sample = db.execute("SELECT id, sample_code FROM soil_samples WHERE appointment_id = ?", (dispatch["appointment_id"],)).fetchone()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    with db:
        db.execute(
            """
            UPDATE report_dispatches
            SET dispatch_status = 'Dispatched', courier_service = ?, tracking_number = ?, dispatched_at = ?
            WHERE id = ?
            """,
            (courier, tracking_no, now_str, dispatch_id),
        )

        if sample:
            record_sample_event(
                db,
                sample_id=sample["id"],
                stage_number=12,
                status="COMPLETED",
                actor_user_id=g.current_user["id"],
                actor_role=g.current_user["role"],
                department="Postal Logistics",
                description=f"Consignment dispatched via {courier} (Tracking #: {tracking_no}).",
                details_dict={"courier": courier, "tracking_number": tracking_no},
            )

    return jsonify({
        "status": "success",
        "message": f"Report dispatched via {courier} ({tracking_no}).",
        "dispatch_status": "Dispatched",
        "tracking_number": tracking_no,
    }), 200


@dispatch_bp.route("/<int:dispatch_id>/deliver", methods=["POST"])
@staff_required
def mark_report_delivered(dispatch_id):
    """
    Marks physical report as delivered to the recipient address.
    Emits Stage 13: REPORT_DELIVERED.
    """
    db = get_db()
    dispatch = db.execute("SELECT * FROM report_dispatches WHERE id = ?", (dispatch_id,)).fetchone()
    if not dispatch:
        return error_response("NOT_FOUND", "Dispatch record not found.", 404)

    sample = db.execute("SELECT id, sample_code FROM soil_samples WHERE appointment_id = ?", (dispatch["appointment_id"],)).fetchone()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    with db:
        db.execute(
            """
            UPDATE report_dispatches
            SET dispatch_status = 'Delivered', delivered_at = ?
            WHERE id = ?
            """,
            (now_str, dispatch_id),
        )

        if sample:
            record_sample_event(
                db,
                sample_id=sample["id"],
                stage_number=13,
                status="COMPLETED",
                actor_user_id=g.current_user["id"],
                actor_role=g.current_user["role"],
                department="India Post Speed Post",
                description=f"Physical Soil Health Card successfully delivered to {dispatch['recipient_name']}.",
                details_dict={"tracking_number": dispatch["tracking_number"]},
            )

    return jsonify({"status": "success", "message": "Delivery confirmed.", "dispatch_status": "Delivered"}), 200

