from flask import Blueprint, g, jsonify, request

from app.auth import login_required, error_response
from app.db import get_db

farm_bp = Blueprint("farm", __name__, url_prefix="/api/farm")

VALID_SEASONS = ("Kharif", "Rabi", "Zaid", "Summer", "Perennial")
VALID_AREA_UNITS = ("Acres", "Guntas", "Hectares")
VALID_IRRIGATION = ("Rainfed", "Borewell", "Canal", "Drip", "Sprinkler", "Well")
VALID_QUANTITY_UNITS = ("Quintals", "Kg", "Tonnes", "Bags")


def standardize_crop_name(name):
    """Ensures Paddy / Rice standard naming for variants like paddy, rice, bhatta, paddy bhatta, dhan."""
    clean = name.strip()
    lower = clean.lower()
    if any(k in lower for k in ("paddy", "bhatta", "dhan")) or lower in ("rice", "paddy / rice", "paddy/rice"):
        return "Paddy / Rice"
    return clean


def get_target_farmer_id():
    """
    Returns farmer_id: from query params if staff, or authenticated farmer's id.
    """
    user = g.current_user
    if user["role"] in ("admin", "operator", "advisor"):
        fid = request.args.get("farmer_id")
        if fid:
            try:
                return int(fid)
            except ValueError:
                return None
    if user["role"] == "farmer":
        return user["id"]
    return None


# ============================================================================
# 1. FARM PLOTS ENDPOINTS
# ============================================================================

@farm_bp.route("/plots", methods=["GET"])
@login_required
def list_plots():
    """Lists farm plots for the farmer."""
    farmer_id = get_target_farmer_id()
    if not farmer_id:
        return error_response("FORBIDDEN", "Target farmer ID required or unauthorized.", 403)

    db = get_db()
    rows = db.execute(
        """
        SELECT id, farmer_id, plot_name, survey_number, area, area_unit,
               soil_type, irrigation_source, landmark, taluk, district, created_at
        FROM farm_plots
        WHERE farmer_id = ?
        ORDER BY id DESC
        """,
        (farmer_id,),
    ).fetchall()

    return jsonify({"status": "success", "farmer_id": farmer_id, "plots": [dict(r) for r in rows]}), 200


@farm_bp.route("/plots", methods=["POST"])
@login_required
def create_plot():
    """Creates a new agricultural plot."""
    farmer_id = get_target_farmer_id()
    if not farmer_id:
        return error_response("FORBIDDEN", "Unauthorized or missing farmer ID.", 403)

    data = request.get_json(silent=True) or {}
    plot_name = data.get("plot_name", "").strip()
    survey_number = data.get("survey_number", "").strip()
    area_unit = data.get("area_unit", "Acres").strip()
    soil_type = data.get("soil_type", "Red Sandy Loam").strip()
    irrigation_source = data.get("irrigation_source", "Rainfed").strip()
    landmark = data.get("landmark", "").strip()
    taluk = data.get("taluk", "").strip()
    district = data.get("district", "").strip()

    if not plot_name:
        return error_response("VALIDATION_ERROR", "Plot name is required.", 400, {"field": "plot_name"})
    if not survey_number:
        return error_response("VALIDATION_ERROR", "Survey number is required.", 400, {"field": "survey_number"})
    try:
        area = float(data.get("area", 0))
        if area <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return error_response("VALIDATION_ERROR", "Plot area must be a positive number.", 400, {"field": "area"})

    if area_unit not in VALID_AREA_UNITS:
        return error_response("VALIDATION_ERROR", f"Invalid area unit. Allowed: {', '.join(VALID_AREA_UNITS)}", 400)
    if irrigation_source not in VALID_IRRIGATION:
        return error_response("VALIDATION_ERROR", f"Invalid irrigation source. Allowed: {', '.join(VALID_IRRIGATION)}", 400)

    db = get_db()
    with db:
        cur = db.execute(
            """
            INSERT INTO farm_plots (farmer_id, plot_name, survey_number, area, area_unit, soil_type, irrigation_source, landmark, taluk, district)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (farmer_id, plot_name, survey_number, area, area_unit, soil_type, irrigation_source, landmark, taluk, district),
        )
        plot_id = cur.lastrowid

    return jsonify({
        "status": "success",
        "message": "Farm plot created successfully.",
        "plot": {
            "id": plot_id,
            "farmer_id": farmer_id,
            "plot_name": plot_name,
            "survey_number": survey_number,
            "area": area,
            "area_unit": area_unit,
            "soil_type": soil_type,
            "irrigation_source": irrigation_source,
        }
    }), 201


@farm_bp.route("/plots/<int:plot_id>", methods=["PUT"])
@login_required
def update_plot(plot_id):
    """Updates farm plot information."""
    db = get_db()
    plot = db.execute("SELECT * FROM farm_plots WHERE id = ?", (plot_id,)).fetchone()
    if not plot:
        return error_response("NOT_FOUND", "Plot not found.", 404)

    user = g.current_user
    if user["role"] == "farmer" and plot["farmer_id"] != user["id"]:
        return error_response("FORBIDDEN", "Unauthorized access to this plot.", 403)

    data = request.get_json(silent=True) or {}
    plot_name = data.get("plot_name", plot["plot_name"]).strip()
    survey_number = data.get("survey_number", plot["survey_number"]).strip()
    area = float(data.get("area", plot["area"]))
    area_unit = data.get("area_unit", plot["area_unit"]).strip()
    soil_type = data.get("soil_type", plot["soil_type"]).strip()
    irrigation_source = data.get("irrigation_source", plot["irrigation_source"]).strip()

    with db:
        db.execute(
            """
            UPDATE farm_plots
            SET plot_name = ?, survey_number = ?, area = ?, area_unit = ?, soil_type = ?, irrigation_source = ?
            WHERE id = ?
            """,
            (plot_name, survey_number, area, area_unit, soil_type, irrigation_source, plot_id),
        )

    return jsonify({"status": "success", "message": "Plot updated successfully."}), 200


@farm_bp.route("/plots/<int:plot_id>", methods=["DELETE"])
@login_required
def delete_plot(plot_id):
    """Deletes a farm plot."""
    db = get_db()
    plot = db.execute("SELECT * FROM farm_plots WHERE id = ?", (plot_id,)).fetchone()
    if not plot:
        return error_response("NOT_FOUND", "Plot not found.", 404)

    user = g.current_user
    if user["role"] == "farmer" and plot["farmer_id"] != user["id"]:
        return error_response("FORBIDDEN", "Unauthorized.", 403)

    with db:
        db.execute("DELETE FROM farm_plots WHERE id = ?", (plot_id,))

    return jsonify({"status": "success", "message": "Plot deleted successfully."}), 200


# ============================================================================
# 2. CROP RECORDS & CROP HISTORY ENDPOINTS
# ============================================================================

@farm_bp.route("/crops", methods=["GET"])
@login_required
def list_crops():
    """Lists crop cultivation records."""
    farmer_id = get_target_farmer_id()
    if not farmer_id:
        return error_response("FORBIDDEN", "Unauthorized or missing farmer ID.", 403)

    db = get_db()
    plot_id = request.args.get("plot_id")
    where = ["c.farmer_id = ?"]
    params = [farmer_id]
    if plot_id:
        where.append("c.plot_id = ?")
        params.append(plot_id)

    sql = f"""
        SELECT c.id, c.farmer_id, c.plot_id, p.plot_name, p.survey_number,
               c.crop_name, c.variety, c.year, c.season, c.sowing_date, c.harvest_date,
               c.actual_harvested_quantity, c.quantity_unit, c.notes, c.created_at
        FROM crop_records c
        JOIN farm_plots p ON c.plot_id = p.id
        WHERE {' AND '.join(where)}
        ORDER BY c.year DESC, c.id DESC
    """
    rows = db.execute(sql, params).fetchall()

    return jsonify({"status": "success", "crops": [dict(r) for r in rows]}), 200


@farm_bp.route("/crops", methods=["POST"])
@login_required
def add_crop_record():
    """Adds a new seasonal crop record."""
    farmer_id = get_target_farmer_id()
    if not farmer_id:
        return error_response("FORBIDDEN", "Unauthorized or missing farmer ID.", 403)

    data = request.get_json(silent=True) or {}
    plot_id = data.get("plot_id")
    raw_crop_name = data.get("crop_name", "").strip()
    variety = data.get("variety", "").strip()
    year = data.get("year")
    season = data.get("season", "Kharif").strip()
    sowing_date = data.get("sowing_date")
    harvest_date = data.get("harvest_date")
    unit = data.get("quantity_unit", "Quintals").strip()
    notes = data.get("notes", "").strip()

    if not plot_id:
        return error_response("VALIDATION_ERROR", "plot_id is required.", 400, {"field": "plot_id"})
    if not raw_crop_name:
        return error_response("VALIDATION_ERROR", "crop_name is required.", 400, {"field": "crop_name"})

    crop_name = standardize_crop_name(raw_crop_name)

    try:
        year = int(year)
        if year < 2000 or year > 2100:
            raise ValueError()
    except (ValueError, TypeError):
        return error_response("VALIDATION_ERROR", "year must be between 2000 and 2100.", 400, {"field": "year"})

    if season not in VALID_SEASONS:
        return error_response("VALIDATION_ERROR", f"Invalid season. Allowed: {', '.join(VALID_SEASONS)}", 400)

    db = get_db()
    plot = db.execute("SELECT id FROM farm_plots WHERE id = ? AND farmer_id = ?", (plot_id, farmer_id)).fetchone()
    if not plot:
        return error_response("NOT_FOUND", "Plot not found for this farmer.", 404)

    with db:
        cur = db.execute(
            """
            INSERT INTO crop_records (
                farmer_id, plot_id, crop_name, variety, year, season,
                sowing_date, harvest_date, actual_harvested_quantity, quantity_unit, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?)
            """,
            (farmer_id, plot_id, crop_name, variety, year, season, sowing_date, harvest_date, unit, notes),
        )
        crop_id = cur.lastrowid

    return jsonify({
        "status": "success",
        "message": f"Crop record created for {crop_name}.",
        "crop_id": crop_id,
        "crop_name": crop_name,
    }), 201


# ============================================================================
# 3. HARVEST RECORDS ENDPOINTS
# ============================================================================

@farm_bp.route("/harvests", methods=["GET"])
@login_required
def list_harvests():
    """Lists harvest records for a crop or farmer."""
    farmer_id = get_target_farmer_id()
    if not farmer_id:
        return error_response("FORBIDDEN", "Unauthorized.", 403)

    db = get_db()
    crop_id = request.args.get("crop_record_id")
    where = ["c.farmer_id = ?"]
    params = [farmer_id]
    if crop_id:
        where.append("h.crop_record_id = ?")
        params.append(crop_id)

    sql = f"""
        SELECT h.id, h.crop_record_id, c.crop_name, c.variety, c.season, c.year,
               h.harvest_date, h.total_quantity, h.quantity_unit, h.quality_grade,
               h.storage_location, h.notes, h.created_at
        FROM harvest_records h
        JOIN crop_records c ON h.crop_record_id = c.id
        WHERE {' AND '.join(where)}
        ORDER BY h.harvest_date DESC, h.id DESC
    """
    rows = db.execute(sql, params).fetchall()

    return jsonify({"status": "success", "harvests": [dict(r) for r in rows]}), 200


@farm_bp.route("/harvests", methods=["POST"])
@login_required
def add_harvest_record():
    """
    Records harvested yield and increments crop_records.actual_harvested_quantity.
    """
    farmer_id = get_target_farmer_id()
    if not farmer_id:
        return error_response("FORBIDDEN", "Unauthorized.", 403)

    data = request.get_json(silent=True) or {}
    crop_record_id = data.get("crop_record_id")
    harvest_date = data.get("harvest_date")
    quality_grade = data.get("quality_grade", "Grade A").strip()
    storage_loc = data.get("storage_location", "Farm Godown / Home").strip()
    notes = data.get("notes", "").strip()

    try:
        total_quantity = float(data.get("total_quantity", 0))
        if total_quantity <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return error_response("VALIDATION_ERROR", "total_quantity must be a positive number.", 400)

    db = get_db()
    crop = db.execute("SELECT * FROM crop_records WHERE id = ? AND farmer_id = ?", (crop_record_id, farmer_id)).fetchone()
    if not crop:
        return error_response("NOT_FOUND", "Crop record not found.", 404)

    unit = data.get("quantity_unit", crop["quantity_unit"]).strip()

    with db:
        cur = db.execute(
            """
            INSERT INTO harvest_records (crop_record_id, harvest_date, total_quantity, quantity_unit, quality_grade, storage_location, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (crop_record_id, harvest_date, total_quantity, unit, quality_grade, storage_loc, notes),
        )
        harvest_id = cur.lastrowid

        # Update cumulative harvested quantity on crop record
        db.execute(
            """
            UPDATE crop_records
            SET actual_harvested_quantity = actual_harvested_quantity + ?,
                harvest_date = COALESCE(harvest_date, ?)
            WHERE id = ?
            """,
            (total_quantity, harvest_date, crop_record_id),
        )

    return jsonify({
        "status": "success",
        "message": f"Harvest of {total_quantity} {unit} recorded.",
        "harvest_id": harvest_id,
    }), 201


# ============================================================================
# 4. SALES RECORDS ENDPOINTS (TRANSPARENT REVENUE CALCULATIONS)
# ============================================================================

@farm_bp.route("/sales", methods=["GET"])
@login_required
def list_sales():
    """Lists sales transactions."""
    farmer_id = get_target_farmer_id()
    if not farmer_id:
        return error_response("FORBIDDEN", "Unauthorized.", 403)

    db = get_db()
    crop_id = request.args.get("crop_record_id")
    where = ["c.farmer_id = ?"]
    params = [farmer_id]
    if crop_id:
        where.append("s.crop_record_id = ?")
        params.append(crop_id)

    sql = f"""
        SELECT s.id, s.crop_record_id, c.crop_name, c.variety, c.season, c.year,
               s.sale_date, s.quantity_sold, s.price_per_unit, s.gross_revenue,
               s.buyer_market, s.payment_status, s.notes, s.created_at
        FROM sales_records s
        JOIN crop_records c ON s.crop_record_id = c.id
        WHERE {' AND '.join(where)}
        ORDER BY s.sale_date DESC, s.id DESC
    """
    rows = db.execute(sql, params).fetchall()

    return jsonify({"status": "success", "sales": [dict(r) for r in rows]}), 200


@farm_bp.route("/sales", methods=["POST"])
@login_required
def add_sales_record():
    """
    Records a sale of harvested crop.
    Validates that quantity_sold does not exceed available harvested quantity.
    Calculates gross_revenue = quantity_sold * price_per_unit.
    Never labels gross revenue as profit.
    """
    farmer_id = get_target_farmer_id()
    if not farmer_id:
        return error_response("FORBIDDEN", "Unauthorized.", 403)

    data = request.get_json(silent=True) or {}
    crop_record_id = data.get("crop_record_id")
    sale_date = data.get("sale_date")
    buyer_market = data.get("buyer_market", "APMC Mandi").strip()
    payment_status = data.get("payment_status", "Received").strip()
    notes = data.get("notes", "").strip()

    try:
        quantity_sold = float(data.get("quantity_sold", 0))
        price_per_unit = float(data.get("price_per_unit", 0))
        if quantity_sold <= 0 or price_per_unit <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return error_response("VALIDATION_ERROR", "quantity_sold and price_per_unit must be positive numbers.", 400)

    db = get_db()
    crop = db.execute("SELECT * FROM crop_records WHERE id = ? AND farmer_id = ?", (crop_record_id, farmer_id)).fetchone()
    if not crop:
        return error_response("NOT_FOUND", "Crop record not found.", 404)

    # Check total harvested vs already sold
    harvested_total = crop["actual_harvested_quantity"]
    already_sold_row = db.execute(
        "SELECT COALESCE(SUM(quantity_sold), 0) AS sold FROM sales_records WHERE crop_record_id = ?",
        (crop_record_id,),
    ).fetchone()
    already_sold = already_sold_row["sold"]

    available_stock = harvested_total - already_sold
    if quantity_sold > available_stock:
        return error_response(
            "VALIDATION_ERROR",
            f"Quantity sold ({quantity_sold} {crop['quantity_unit']}) exceeds available stock ({available_stock:.2f} {crop['quantity_unit']}). Total harvested: {harvested_total:.2f}, already sold: {already_sold:.2f}.",
            400,
            {"field": "quantity_sold", "available_stock": available_stock},
        )

    # Calculate gross revenue (strictly gross sales revenue, not profit)
    gross_revenue = round(quantity_sold * price_per_unit, 2)

    with db:
        cur = db.execute(
            """
            INSERT INTO sales_records (crop_record_id, sale_date, quantity_sold, price_per_unit, gross_revenue, buyer_market, payment_status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (crop_record_id, sale_date, quantity_sold, price_per_unit, gross_revenue, buyer_market, payment_status, notes),
        )
        sale_id = cur.lastrowid

    return jsonify({
        "status": "success",
        "message": f"Sale of {quantity_sold} {crop['quantity_unit']} recorded. Gross Revenue: ₹{gross_revenue:,.2f}.",
        "sale_id": sale_id,
        "gross_revenue": gross_revenue,
        "remaining_stock": round(available_stock - quantity_sold, 2),
    }), 201


# ============================================================================
# 5. FARM SUMMARY & STOCK OVERVIEW
# ============================================================================

@farm_bp.route("/summary", methods=["GET"])
@login_required
def get_farm_summary():
    """
    Returns aggregated farm metrics:
    - Total plots & acreage
    - Active crops
    - Total harvest & remaining stock
    - Cumulative gross sales revenue
    """
    farmer_id = get_target_farmer_id()
    if not farmer_id:
        return error_response("FORBIDDEN", "Unauthorized.", 403)

    db = get_db()

    plots = db.execute("SELECT id, area, area_unit FROM farm_plots WHERE farmer_id = ?", (farmer_id,)).fetchall()
    total_plots = len(plots)
    total_area_acres = sum(
        p["area"] * (1.0 if p["area_unit"] == "Acres" else (0.025 if p["area_unit"] == "Guntas" else 2.471))
        for p in plots
    )

    crops = db.execute("SELECT id, crop_name, actual_harvested_quantity, quantity_unit FROM crop_records WHERE farmer_id = ?", (farmer_id,)).fetchall()
    active_crops_count = len(crops)

    sales = db.execute(
        """
        SELECT COALESCE(SUM(s.gross_revenue), 0) AS total_gross_rev,
               COALESCE(SUM(s.quantity_sold), 0) AS total_sold
        FROM sales_records s
        JOIN crop_records c ON s.crop_record_id = c.id
        WHERE c.farmer_id = ?
        """,
        (farmer_id,),
    ).fetchone()

    total_harvested_quantity = sum(c["actual_harvested_quantity"] for c in crops)
    total_sold_quantity = sales["total_sold"]
    remaining_stock = max(0.0, total_harvested_quantity - total_sold_quantity)

    return jsonify({
        "status": "success",
        "farmer_id": farmer_id,
        "total_plots": total_plots,
        "total_area_acres": round(total_area_acres, 2),
        "active_crops_count": active_crops_count,
        "total_harvested_quantity": round(total_harvested_quantity, 2),
        "total_sold_quantity": round(total_sold_quantity, 2),
        "remaining_stock": round(remaining_stock, 2),
        "total_gross_revenue": round(sales["total_gross_rev"], 2),
    }), 200

