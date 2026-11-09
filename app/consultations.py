from datetime import datetime, timezone
from flask import Blueprint, g, jsonify, request

from app.auth import login_required, advisor_required, error_response
from app.db import get_db

consultations_bp = Blueprint("consultations", __name__, url_prefix="/api/consultations")

VALID_CATEGORIES = (
    "Crop Recommendation",
    "Soil Health",
    "Pest Control",
    "Fertilizer Application",
    "Irrigation",
    "General Advice",
)
VALID_STATUSES = ("OPEN", "IN_REVIEW", "ANSWERED", "CLOSED")


@consultations_bp.route("", methods=["GET"])
@login_required
def list_consultations():
    """
    Lists expert consultations:
    - Farmers see their own submitted questions.
    - Advisors & admins see the advisory queue with optional status filter.
    """
    user = g.current_user
    db = get_db()
    status_filter = request.args.get("status")

    where_clauses = []
    params = []

    if user["role"] == "farmer":
        where_clauses.append("c.farmer_id = ?")
        params.append(user["id"])
    else:
        # Advisor / Admin / Staff
        pass

    if status_filter:
        if status_filter not in VALID_STATUSES:
            return error_response("VALIDATION_ERROR", f"Invalid status filter. Allowed: {', '.join(VALID_STATUSES)}", 400)
        where_clauses.append("c.status = ?")
        params.append(status_filter)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    sql = f"""
        SELECT c.id, c.farmer_id, u.name AS farmer_name, u.phone AS farmer_phone,
               c.category, c.subject, c.question_text, c.status,
               c.assigned_advisor_id, adv.name AS advisor_name,
               c.plot_id, p.plot_name,
               c.report_id,
               c.created_at, c.updated_at
        FROM expert_consultations c
        JOIN users u ON c.farmer_id = u.id
        LEFT JOIN users adv ON c.assigned_advisor_id = adv.id
        LEFT JOIN farm_plots p ON c.plot_id = p.id
        {where_sql}
        ORDER BY CASE c.status WHEN 'OPEN' THEN 1 WHEN 'IN_REVIEW' THEN 2 WHEN 'ANSWERED' THEN 3 ELSE 4 END,
                 c.updated_at DESC
    """
    rows = db.execute(sql, params).fetchall()

    return jsonify({"status": "success", "count": len(rows), "consultations": [dict(r) for r in rows]}), 200


@consultations_bp.route("", methods=["POST"])
@login_required
def create_consultation():
    """
    Farmer submits a new agricultural query to an expert.
    """
    user = g.current_user
    data = request.get_json(silent=True) or {}

    subject = data.get("subject", "").strip()
    category = data.get("category", "General Advice").strip()
    question_text = data.get("question_text", "").strip()
    plot_id = data.get("plot_id")
    report_id = data.get("report_id")

    if not subject:
        return error_response("VALIDATION_ERROR", "Subject is required.", 400, {"field": "subject"})
    if not question_text:
        return error_response("VALIDATION_ERROR", "Question details are required.", 400, {"field": "question_text"})
    if category not in VALID_CATEGORIES:
        return error_response("VALIDATION_ERROR", f"Invalid category. Allowed: {', '.join(VALID_CATEGORIES)}", 400)

    db = get_db()
    with db:
        cur = db.execute(
            """
            INSERT INTO expert_consultations (farmer_id, plot_id, report_id, category, subject, question_text, status)
            VALUES (?, ?, ?, ?, ?, ?, 'OPEN')
            """,
            (user["id"], plot_id, report_id, category, subject, question_text),
        )
        consultation_id = cur.lastrowid

        # Insert initial question into consultation_messages thread
        db.execute(
            """
            INSERT INTO consultation_messages (consultation_id, sender_user_id, sender_role, message_text)
            VALUES (?, ?, ?, ?)
            """,
            (consultation_id, user["id"], user["role"], question_text),
        )

    return jsonify({
        "status": "success",
        "message": "Consultation question submitted to agricultural expert team.",
        "consultation_id": consultation_id,
    }), 201


@consultations_bp.route("/<int:consultation_id>", methods=["GET"])
@login_required
def get_consultation_details(consultation_id):
    """
    Retrieves full consultation details and conversation messages thread.
    """
    db = get_db()
    consultation = db.execute(
        """
        SELECT c.*, u.name AS farmer_name, u.phone AS farmer_phone,
               adv.name AS advisor_name, p.plot_name, p.survey_number
        FROM expert_consultations c
        JOIN users u ON c.farmer_id = u.id
        LEFT JOIN users adv ON c.assigned_advisor_id = adv.id
        LEFT JOIN farm_plots p ON c.plot_id = p.id
        WHERE c.id = ?
        """,
        (consultation_id,),
    ).fetchone()

    if not consultation:
        return error_response("NOT_FOUND", "Consultation not found.", 404)

    user = g.current_user
    if user["role"] == "farmer" and consultation["farmer_id"] != user["id"]:
        return error_response("FORBIDDEN", "Unauthorized access.", 403)

    messages = db.execute(
        """
        SELECT m.id, m.consultation_id, m.sender_user_id, u.name AS sender_name,
               m.sender_role, m.message_text, m.attachment_filename, m.created_at
        FROM consultation_messages m
        JOIN users u ON m.sender_user_id = u.id
        WHERE m.consultation_id = ?
        ORDER BY m.id ASC
        """,
        (consultation_id,),
    ).fetchall()

    return jsonify({
        "status": "success",
        "consultation": dict(consultation),
        "messages": [dict(m) for m in messages],
    }), 200


@consultations_bp.route("/<int:consultation_id>/messages", methods=["POST"])
@login_required
def reply_to_consultation(consultation_id):
    """
    Appends a message to the consultation thread.
    - If expert (advisor or admin) replies, updates status to 'ANSWERED' and assigns advisor.
    - If farmer replies, updates status to 'IN_REVIEW'.
    """
    data = request.get_json(silent=True) or {}
    message_text = data.get("message_text", "").strip()

    if not message_text:
        return error_response("VALIDATION_ERROR", "Message text is required.", 400)

    db = get_db()
    consultation = db.execute("SELECT * FROM expert_consultations WHERE id = ?", (consultation_id,)).fetchone()
    if not consultation:
        return error_response("NOT_FOUND", "Consultation not found.", 404)

    user = g.current_user
    if user["role"] == "farmer" and consultation["farmer_id"] != user["id"]:
        return error_response("FORBIDDEN", "Unauthorized access.", 403)

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    with db:
        db.execute(
            """
            INSERT INTO consultation_messages (consultation_id, sender_user_id, sender_role, message_text)
            VALUES (?, ?, ?, ?)
            """,
            (consultation_id, user["id"], user["role"], message_text),
        )

        if user["role"] in ("advisor", "admin"):
            db.execute(
                """
                UPDATE expert_consultations
                SET status = 'ANSWERED', assigned_advisor_id = COALESCE(assigned_advisor_id, ?), updated_at = ?
                WHERE id = ?
                """,
                (user["id"], now_str, consultation_id),
            )
        elif user["role"] == "farmer":
            db.execute(
                """
                UPDATE expert_consultations
                SET status = 'IN_REVIEW', updated_at = ?
                WHERE id = ?
                """,
                (now_str, consultation_id),
            )

    return jsonify({"status": "success", "message": "Reply posted successfully."}), 201


@consultations_bp.route("/<int:consultation_id>/close", methods=["POST"])
@login_required
def close_consultation(consultation_id):
    """Marks a consultation as resolved / CLOSED."""
    db = get_db()
    consultation = db.execute("SELECT * FROM expert_consultations WHERE id = ?", (consultation_id,)).fetchone()
    if not consultation:
        return error_response("NOT_FOUND", "Consultation not found.", 404)

    user = g.current_user
    if user["role"] == "farmer" and consultation["farmer_id"] != user["id"]:
        return error_response("FORBIDDEN", "Unauthorized.", 403)

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with db:
        db.execute(
            "UPDATE expert_consultations SET status = 'CLOSED', updated_at = ? WHERE id = ?",
            (now_str, consultation_id),
        )

    return jsonify({"status": "success", "message": "Consultation marked as closed."}), 200

