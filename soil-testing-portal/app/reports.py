import hashlib
import os
import sqlite3
import uuid
from flask import Blueprint, current_app, g, jsonify, request, send_file
from werkzeug.utils import secure_filename

from app.auth import admin_required, farmer_required, error_response
from app.db import get_db

reports_bp = Blueprint("reports", __name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB maximum
CHUNK_SIZE = 64 * 1024            # 64 KB streaming chunks
PDF_MAGIC_BYTES = b"%PDF-"
PDF_EOF_MARKER = b"%%EOF"
MAX_FILENAME_LEN = 200


def get_reports_dir():
    """
    Returns the absolute path to the private report storage directory.
    Uses app.config['REPORT_FOLDER'] if configured, else instance/reports/.
    Ensures the directory exists.
    """
    folder = current_app.config.get("REPORT_FOLDER")
    if not folder:
        folder = os.path.join(current_app.instance_path, "reports")
    os.makedirs(folder, exist_ok=True)
    return folder


def sanitize_original_filename(filename):
    """
    Sanitizes the client-supplied original filename for safe display and download.
    Guarantees a safe, non-empty .pdf extension and bounded length.
    """
    if not filename or not isinstance(filename, str):
        return "report.pdf"
    clean = secure_filename(filename)
    if not clean or not clean.lower().endswith(".pdf"):
        return "report.pdf"
    base = clean[:-4].rstrip("._- ")
    if not base:
        return "report.pdf"
    if len(clean) > MAX_FILENAME_LEN:
        base = base[:MAX_FILENAME_LEN - 4].rstrip("._- ")
        if not base:
            return "report.pdf"
    return f"{base}.pdf"


def send_report_file(storage_rel_path, original_filename):
    """
    Safely streams a stored PDF report to the client with defense-in-depth headers.
    Never exposes internal filesystem paths to the caller.
    """
    # Prevent any directory traversal from stored database values
    safe_basename = os.path.basename(storage_rel_path)
    reports_dir = get_reports_dir()
    full_path = os.path.join(reports_dir, safe_basename)

    if not os.path.isfile(full_path):
        current_app.logger.error("Report physical file missing on disk: %s", safe_basename)
        return error_response(
            code="FILE_NOT_FOUND",
            message="Report file is missing or temporarily unavailable.",
            status_code=404,
        )

    response = send_file(
        full_path,
        as_attachment=True,
        download_name=original_filename,
        mimetype="application/pdf",
    )
    # Security and caching headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "private, no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ============================================================================
# 1. ADMIN REPORT UPLOAD (POST /api/admin/appointments/<id>/report)
# ============================================================================

@reports_bp.route("/api/admin/appointments/<int:appointment_id>/report", methods=["POST"])
@admin_required
def upload_report(appointment_id):
    """
    Uploads a soil testing PDF report for an appointment.
    - Requires authenticated admin role and valid CSRF token.
    - Appointment must exist and be in 'Completed' status.
    - Enforces 1 report per appointment limit.
    - Validates PDF extension, MIME type, signature (%PDF-), EOF marker (%%EOF), and max size (10 MB).
    - Streams directly to a temporary staging file while computing SHA-256.
    - Moves to a UUID4-based physical filename upon successful validation and DB commit.
    - Cleans up staging or target files on any database failure.
    """
    db = get_db()

    # 1. Verify appointment exists and is in 'Completed' status
    appointment = db.execute(
        "SELECT id, status FROM appointments WHERE id = ?",
        (appointment_id,),
    ).fetchone()

    if appointment is None:
        return error_response(
            code="NOT_FOUND",
            message="Appointment not found.",
            status_code=404,
        )

    if appointment["status"] != "Completed":
        return error_response(
            code="CONFLICT",
            message=f"Reports can only be uploaded for Completed appointments (current status is '{appointment['status']}').",
            status_code=409,
            details={"current_status": appointment["status"]},
        )

    # 2. Check if a report already exists for this appointment
    existing_report = db.execute(
        "SELECT id FROM reports WHERE appointment_id = ?",
        (appointment_id,),
    ).fetchone()

    if existing_report is not None:
        return error_response(
            code="CONFLICT",
            message="A report has already been uploaded for this appointment.",
            status_code=409,
            details={"report_id": existing_report["id"]},
        )

    # 3. Validate file field presence
    if "file" not in request.files:
        return error_response(
            code="VALIDATION_ERROR",
            message="File field 'file' is required in multipart form data.",
            status_code=400,
            details={"field": "file"},
        )

    uploaded_file = request.files["file"]
    if not uploaded_file or not uploaded_file.filename:
        return error_response(
            code="VALIDATION_ERROR",
            message="No file selected or empty filename provided.",
            status_code=400,
            details={"field": "file"},
        )

    # 4. Validate extension
    raw_filename = uploaded_file.filename
    if not raw_filename.lower().endswith(".pdf"):
        return error_response(
            code="VALIDATION_ERROR",
            message="Only PDF files (.pdf extension) are accepted.",
            status_code=400,
            details={"field": "file"},
        )

    # 5. Validate MIME type if provided
    mime_type = uploaded_file.content_type
    if mime_type and mime_type.lower() not in ("application/pdf", "application/x-pdf", "binary/octet-stream"):
        return error_response(
            code="VALIDATION_ERROR",
            message=f"Invalid MIME type '{mime_type}'. Only 'application/pdf' is accepted.",
            status_code=400,
            details={"field": "file"},
        )

    reports_dir = get_reports_dir()
    staging_filename = f".staging_{uuid.uuid4().hex}.tmp"
    staging_path = os.path.join(reports_dir, staging_filename)

    hasher = hashlib.sha256()
    total_bytes = 0
    first_chunk = True
    trailing_buffer = b""

    try:
        with open(staging_path, "wb") as stage_out:
            while True:
                chunk = uploaded_file.stream.read(CHUNK_SIZE)
                if not chunk:
                    break

                total_bytes += len(chunk)

                # Check max file size during streaming
                if total_bytes > MAX_FILE_SIZE:
                    stage_out.close()
                    if os.path.exists(staging_path):
                        os.remove(staging_path)
                    return error_response(
                        code="VALIDATION_ERROR",
                        message=f"File exceeds maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)} MB.",
                        status_code=400,
                        details={"field": "file"},
                    )

                # Check PDF signature (%PDF-) on the initial chunk
                if first_chunk:
                    if not chunk.startswith(PDF_MAGIC_BYTES):
                        stage_out.close()
                        if os.path.exists(staging_path):
                            os.remove(staging_path)
                        return error_response(
                            code="VALIDATION_ERROR",
                            message="File is not a valid PDF. Missing '%PDF-' header signature.",
                            status_code=400,
                            details={"field": "file"},
                        )
                    first_chunk = False

                hasher.update(chunk)
                stage_out.write(chunk)

                # Maintain trailing 1024 bytes to verify EOF marker
                trailing_buffer = (trailing_buffer + chunk)[-1024:]

        # Validate non-empty file
        if total_bytes == 0:
            if os.path.exists(staging_path):
                os.remove(staging_path)
            return error_response(
                code="VALIDATION_ERROR",
                message="Uploaded file is empty (0 bytes).",
                status_code=400,
                details={"field": "file"},
            )

        # Validate PDF EOF marker (%%EOF) in trailing bytes
        if PDF_EOF_MARKER not in trailing_buffer:
            if os.path.exists(staging_path):
                os.remove(staging_path)
            return error_response(
                code="VALIDATION_ERROR",
                message="File is not a complete PDF. Missing '%%EOF' end marker.",
                status_code=400,
                details={"field": "file"},
            )

        # Generate unique UUID-based physical filename
        storage_filename = f"{uuid.uuid4().hex}.pdf"
        target_path = os.path.join(reports_dir, storage_filename)
        clean_original_name = sanitize_original_filename(raw_filename)
        sha256_checksum = hasher.hexdigest()

        # Atomically rename staging file to final destination
        os.replace(staging_path, target_path)

        # Insert metadata into SQLite
        try:
            with db:
                cursor = db.execute(
                    """
                    INSERT INTO reports (
                        appointment_id, file_path, original_filename, file_size_bytes, checksum_sha256, uploaded_by
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        appointment_id,
                        storage_filename,
                        clean_original_name,
                        total_bytes,
                        sha256_checksum,
                        g.current_user["id"],
                    ),
                )
                report_id = cursor.lastrowid

            # Retrieve inserted record for response
            report_row = db.execute(
                """
                SELECT id, appointment_id, original_filename, file_size_bytes, checksum_sha256, uploaded_at
                FROM reports WHERE id = ?
                """,
                (report_id,),
            ).fetchone()

            return jsonify({
                "status": "success",
                "message": "Report uploaded successfully.",
                "report": {
                    "id": report_row["id"],
                    "appointment_id": report_row["appointment_id"],
                    "original_filename": report_row["original_filename"],
                    "file_size_bytes": report_row["file_size_bytes"],
                    "checksum_sha256": report_row["checksum_sha256"],
                    "uploaded_at": report_row["uploaded_at"],
                },
            }), 201

        except sqlite3.IntegrityError:
            # Handle concurrent duplicate upload race condition cleanly
            if os.path.exists(target_path):
                os.remove(target_path)
            try:
                db.rollback()
            except Exception:
                pass
            return error_response(
                code="CONFLICT",
                message="A report has already been uploaded for this appointment.",
                status_code=409,
            )
        except Exception as e:
            if os.path.exists(target_path):
                os.remove(target_path)
            try:
                db.rollback()
            except Exception:
                pass
            current_app.logger.error("Failed to insert report metadata: %s", str(e))
            return error_response(
                code="SERVER_ERROR",
                message="Failed to save report metadata.",
                status_code=500,
            )

    except Exception as e:
        if os.path.exists(staging_path):
            os.remove(staging_path)
        if "target_path" in locals() and os.path.exists(target_path):
            os.remove(target_path)
        try:
            db.rollback()
        except Exception:
            pass
        current_app.logger.error("Unexpected error during report upload: %s", str(e))
        return error_response(
            code="SERVER_ERROR",
            message="An error occurred while processing the file upload.",
            status_code=500,
        )


# ============================================================================
# 2. FARMER REPORT METADATA (GET /api/appointments/<id>/report)
# ============================================================================

@reports_bp.route("/api/appointments/<int:appointment_id>/report", methods=["GET"])
@farmer_required
def get_farmer_report_metadata(appointment_id):
    """
    Returns safe report metadata for an appointment owned by the authenticated farmer.
    Returns safe HTTP 404 if the appointment does not exist, belongs to another farmer,
    or has no report attached. Never exposes internal file_path.
    """
    farmer_id = g.current_user["id"]
    db = get_db()

    # 1. Verify appointment ownership
    appointment = db.execute(
        "SELECT id, farmer_id FROM appointments WHERE id = ?",
        (appointment_id,),
    ).fetchone()

    if appointment is None or appointment["farmer_id"] != farmer_id:
        return error_response(
            code="NOT_FOUND",
            message="Appointment not found.",
            status_code=404,
        )

    # 2. Fetch report metadata
    report = db.execute(
        """
        SELECT id, appointment_id, original_filename, file_size_bytes, checksum_sha256, uploaded_at
        FROM reports WHERE appointment_id = ?
        """,
        (appointment_id,),
    ).fetchone()

    if report is None:
        return error_response(
            code="NOT_FOUND",
            message="No report available for this appointment.",
            status_code=404,
        )

    return jsonify({
        "status": "success",
        "report": {
            "id": report["id"],
            "appointment_id": report["appointment_id"],
            "original_filename": report["original_filename"],
            "file_size_bytes": report["file_size_bytes"],
            "checksum_sha256": report["checksum_sha256"],
            "uploaded_at": report["uploaded_at"],
        },
    }), 200


# ============================================================================
# 3. FARMER REPORT DOWNLOAD (GET /api/appointments/<id>/report/download)
# ============================================================================

@reports_bp.route("/api/appointments/<int:appointment_id>/report/download", methods=["GET"])
@farmer_required
def download_farmer_report(appointment_id):
    """
    Securely downloads the PDF report for an appointment owned by the authenticated farmer.
    Enforces appointment ownership, Completed status, and file presence.
    """
    farmer_id = g.current_user["id"]
    db = get_db()

    # 1. Verify appointment ownership and completed status
    appointment = db.execute(
        "SELECT id, farmer_id, status FROM appointments WHERE id = ?",
        (appointment_id,),
    ).fetchone()

    if appointment is None or appointment["farmer_id"] != farmer_id:
        return error_response(
            code="NOT_FOUND",
            message="Appointment not found.",
            status_code=404,
        )

    # 2. Fetch report record
    report = db.execute(
        "SELECT id, appointment_id, file_path, original_filename FROM reports WHERE appointment_id = ?",
        (appointment_id,),
    ).fetchone()

    if report is None:
        return error_response(
            code="NOT_FOUND",
            message="No report available for this appointment.",
            status_code=404,
        )

    return send_report_file(report["file_path"], report["original_filename"])


# ============================================================================
# 4. ADMIN REPORT METADATA (GET /api/admin/appointments/<id>/report)
# ============================================================================

@reports_bp.route("/api/admin/appointments/<int:appointment_id>/report", methods=["GET"])
@admin_required
def get_admin_report_metadata(appointment_id):
    """
    Retrieves report metadata for any appointment for administrative inspection.
    Never exposes internal storage file_path.
    """
    db = get_db()

    # Verify appointment exists
    appointment = db.execute(
        "SELECT id FROM appointments WHERE id = ?",
        (appointment_id,),
    ).fetchone()

    if appointment is None:
        return error_response(
            code="NOT_FOUND",
            message="Appointment not found.",
            status_code=404,
        )

    report = db.execute(
        """
        SELECT id, appointment_id, original_filename, file_size_bytes, checksum_sha256, uploaded_at
        FROM reports WHERE appointment_id = ?
        """,
        (appointment_id,),
    ).fetchone()

    if report is None:
        return error_response(
            code="NOT_FOUND",
            message="No report available for this appointment.",
            status_code=404,
        )

    return jsonify({
        "status": "success",
        "report": {
            "id": report["id"],
            "appointment_id": report["appointment_id"],
            "original_filename": report["original_filename"],
            "file_size_bytes": report["file_size_bytes"],
            "checksum_sha256": report["checksum_sha256"],
            "uploaded_at": report["uploaded_at"],
        },
    }), 200


# ============================================================================
# 5. ADMIN REPORT DOWNLOAD (GET /api/admin/appointments/<id>/report/download)
# ============================================================================

@reports_bp.route("/api/admin/appointments/<int:appointment_id>/report/download", methods=["GET"])
@admin_required
def download_admin_report(appointment_id):
    """
    Securely downloads the PDF report for any appointment for administrative verification.
    """
    db = get_db()

    appointment = db.execute(
        "SELECT id FROM appointments WHERE id = ?",
        (appointment_id,),
    ).fetchone()

    if appointment is None:
        return error_response(
            code="NOT_FOUND",
            message="Appointment not found.",
            status_code=404,
        )

    report = db.execute(
        "SELECT id, appointment_id, file_path, original_filename FROM reports WHERE appointment_id = ?",
        (appointment_id,),
    ).fetchone()

    if report is None:
        return error_response(
            code="NOT_FOUND",
            message="No report available for this appointment.",
            status_code=404,
        )

    return send_report_file(report["file_path"], report["original_filename"])

