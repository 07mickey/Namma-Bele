import re
from flask import Blueprint, g, jsonify, request
from app.auth import login_required, error_response, normalize_phone, E164_REGEX
from app.db import get_db

addresses_bp = Blueprint("addresses", __name__, url_prefix="/api/farmers")

PINCODE_REGEX = re.compile(r"^\d{6}$")


def check_farmer_access(farmer_id):
    """
    Ensures the requesting user is either the owner farmer or an operator/admin.
    """
    user = g.current_user
    if user["role"] in ("admin", "operator"):
        return True
    if user["role"] == "farmer" and user["id"] == farmer_id:
        return True
    return False


@addresses_bp.route("/<int:farmer_id>/delivery-addresses", methods=["GET"])
@login_required
def list_delivery_addresses(farmer_id):
    """
    Returns all registered postal delivery addresses for a farmer.
    Accessible by the farmer themselves, or staff (operators/admins).
    """
    if not check_farmer_access(farmer_id):
        return error_response(
            code="FORBIDDEN",
            message="You do not have permission to view delivery addresses for this farmer.",
            status_code=403,
        )

    db = get_db()
    rows = db.execute(
        """
        SELECT id, farmer_id, recipient_name, recipient_phone, house_details,
               street_or_village, landmark, taluk, district, state, pincode, is_default, created_at
        FROM farmer_delivery_addresses
        WHERE farmer_id = ?
        ORDER BY is_default DESC, id DESC
        """,
        (farmer_id,),
    ).fetchall()

    addresses = [dict(row) for row in rows]
    return jsonify({
        "status": "success",
        "farmer_id": farmer_id,
        "addresses": addresses,
    }), 200


@addresses_bp.route("/<int:farmer_id>/delivery-addresses", methods=["POST"])
@login_required
def add_delivery_address(farmer_id):
    """
    Adds a new delivery address for the farmer.
    Can be marked as default.
    """
    if not check_farmer_access(farmer_id):
        return error_response(
            code="FORBIDDEN",
            message="You do not have permission to modify delivery addresses for this farmer.",
            status_code=403,
        )

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return error_response(
            code="MALFORMED_REQUEST",
            message="Request body must be a valid JSON object.",
            status_code=400,
        )

    recipient_name = data.get("recipient_name", "").strip()
    recipient_phone = normalize_phone(data.get("recipient_phone", ""))
    house_details = data.get("house_details", "").strip()
    street_or_village = data.get("street_or_village", "").strip()
    landmark = data.get("landmark", "").strip()
    taluk = data.get("taluk", "").strip()
    district = data.get("district", "").strip()
    state = data.get("state", "Karnataka").strip()
    pincode = data.get("pincode", "").strip()
    is_default = 1 if data.get("is_default") in (True, 1, "1") else 0

    if not recipient_name:
        return error_response("VALIDATION_ERROR", "Recipient name is required.", 400, {"field": "recipient_name"})
    if not recipient_phone or not E164_REGEX.match(recipient_phone):
        return error_response("VALIDATION_ERROR", "Recipient phone must be valid E.164.", 400, {"field": "recipient_phone"})
    if not house_details:
        return error_response("VALIDATION_ERROR", "House/door details are required.", 400, {"field": "house_details"})
    if not street_or_village:
        return error_response("VALIDATION_ERROR", "Street or village name is required.", 400, {"field": "street_or_village"})
    if not taluk:
        return error_response("VALIDATION_ERROR", "Taluk is required.", 400, {"field": "taluk"})
    if not district:
        return error_response("VALIDATION_ERROR", "District is required.", 400, {"field": "district"})
    if not pincode or not PINCODE_REGEX.match(pincode):
        return error_response("VALIDATION_ERROR", "Valid 6-digit postal PIN code is required.", 400, {"field": "pincode"})

    db = get_db()
    # Check farmer exists
    farmer = db.execute("SELECT id FROM users WHERE id = ?", (farmer_id,)).fetchone()
    if not farmer:
        return error_response("NOT_FOUND", "Farmer account not found.", 404)

    with db:
        if is_default == 1:
            db.execute("UPDATE farmer_delivery_addresses SET is_default = 0 WHERE farmer_id = ?", (farmer_id,))
        else:
            # If farmer has no existing addresses, make this the default automatically
            existing_count = db.execute(
                "SELECT COUNT(*) AS c FROM farmer_delivery_addresses WHERE farmer_id = ?",
                (farmer_id,),
            ).fetchone()["c"]
            if existing_count == 0:
                is_default = 1

        cursor = db.execute(
            """
            INSERT INTO farmer_delivery_addresses (
                farmer_id, recipient_name, recipient_phone, house_details,
                street_or_village, landmark, taluk, district, state, pincode, is_default
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (farmer_id, recipient_name, recipient_phone, house_details, street_or_village,
             landmark, taluk, district, state, pincode, is_default),
        )
        address_id = cursor.lastrowid

    return jsonify({
        "status": "success",
        "message": "Delivery address added successfully.",
        "address": {
            "id": address_id,
            "farmer_id": farmer_id,
            "recipient_name": recipient_name,
            "recipient_phone": recipient_phone,
            "house_details": house_details,
            "street_or_village": street_or_village,
            "landmark": landmark,
            "taluk": taluk,
            "district": district,
            "state": state,
            "pincode": pincode,
            "is_default": is_default,
        }
    }), 201


@addresses_bp.route("/<int:farmer_id>/delivery-addresses/<int:address_id>/default", methods=["PUT"])
@login_required
def set_default_address(farmer_id, address_id):
    """Sets a specific delivery address as the farmer's primary default address."""
    if not check_farmer_access(farmer_id):
        return error_response("FORBIDDEN", "Unauthorized access.", 403)

    db = get_db()
    addr = db.execute(
        "SELECT id FROM farmer_delivery_addresses WHERE id = ? AND farmer_id = ?",
        (address_id, farmer_id),
    ).fetchone()
    if not addr:
        return error_response("NOT_FOUND", "Address not found for this farmer.", 404)

    with db:
        db.execute("UPDATE farmer_delivery_addresses SET is_default = 0 WHERE farmer_id = ?", (farmer_id,))
        db.execute("UPDATE farmer_delivery_addresses SET is_default = 1 WHERE id = ?", (address_id,))

    return jsonify({"status": "success", "message": "Default delivery address updated."}), 200


@addresses_bp.route("/<int:farmer_id>/delivery-addresses/<int:address_id>", methods=["DELETE"])
@login_required
def delete_delivery_address(farmer_id, address_id):
    """Deletes an address belonging to the farmer."""
    if not check_farmer_access(farmer_id):
        return error_response("FORBIDDEN", "Unauthorized access.", 403)

    db = get_db()
    addr = db.execute(
        "SELECT id, is_default FROM farmer_delivery_addresses WHERE id = ? AND farmer_id = ?",
        (address_id, farmer_id),
    ).fetchone()
    if not addr:
        return error_response("NOT_FOUND", "Address not found.", 404)

    with db:
        db.execute("DELETE FROM farmer_delivery_addresses WHERE id = ?", (address_id,))
        # If deleted address was default, promote another address to default if available
        if addr["is_default"] == 1:
            first = db.execute(
                "SELECT id FROM farmer_delivery_addresses WHERE farmer_id = ? ORDER BY id ASC LIMIT 1",
                (farmer_id,),
            ).fetchone()
            if first:
                db.execute("UPDATE farmer_delivery_addresses SET is_default = 1 WHERE id = ?", (first["id"],))

    return jsonify({"status": "success", "message": "Address deleted successfully."}), 200

