import hashlib
import io
import os
import sys
import tempfile
import pytest
from werkzeug.security import generate_password_hash

# Ensure the soil-testing-portal directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.db import get_db, init_db

# Minimal valid PDF payload conforming to signature and EOF marker
VALID_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Count 0 >>\nendobj\nxref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \ntrailer\n<< /Root 1 0 R /Size 3 >>\nstartxref\n115\n%%EOF"


@pytest.fixture
def app_and_db():
    """Creates an isolated test application with a fresh temporary database and private report storage."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_reports.db")
        report_dir = os.path.join(temp_dir, "reports")
        os.makedirs(report_dir, exist_ok=True)

        app = create_app({
            "TESTING": True,
            "DATABASE": db_path,
            "REPORT_FOLDER": report_dir,
            "SECRET_KEY": "test-secret-key-for-reports",
        })

        with app.app_context():
            init_db()

        yield app, db_path, report_dir


@pytest.fixture
def app(app_and_db):
    app, _, _ = app_and_db
    return app


@pytest.fixture
def report_dir(app_and_db):
    _, _, report_dir = app_and_db
    return report_dir


@pytest.fixture
def client(app):
    return app.test_client()


def get_csrf(client):
    """Helper to fetch a fresh CSRF token."""
    res = client.get("/api/auth/csrf-token")
    assert res.status_code == 200
    return res.get_json()["csrf_token"]


def create_user_direct(app, name, phone, password="Password123", role="farmer"):
    """Helper to directly insert a user with a hashed password."""
    with app.app_context():
        db = get_db()
        cursor = db.execute(
            "INSERT INTO users (name, phone, password_hash, role) VALUES (?, ?, ?, ?)",
            (name, phone, generate_password_hash(password), role),
        )
        db.commit()
        return cursor.lastrowid


def create_appointment_direct(app, farmer_id, land="2 acres", addr="Field 1", status="Completed"):
    """Helper to directly insert an appointment."""
    with app.app_context():
        db = get_db()
        cursor = db.execute(
            """
            INSERT INTO appointments (farmer_id, land_details, address, preferred_date, preferred_time, notes, status)
            VALUES (?, ?, ?, '2026-11-20', '09:00-12:00', 'Test notes', ?)
            """,
            (farmer_id, land, addr, status),
        )
        db.commit()
        return cursor.lastrowid


def login_user(client, phone, password="Password123"):
    """Helper to authenticate a user and return the fresh post-login CSRF token."""
    csrf = get_csrf(client)
    res = client.post(
        "/api/auth/login",
        json={"phone": phone, "password": password},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    return get_csrf(client)


# ============================================================================
# 1. REPORT UPLOAD SUCCESS AND METADATA TESTS
# ============================================================================

def test_admin_upload_report_success(client, app, report_dir):
    """Admin uploads a valid PDF report for a Completed appointment."""
    admin_id = create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    csrf = login_user(client, "+919876543200")

    file_data = (io.BytesIO(VALID_PDF_BYTES), "Soil_Analysis_Report.pdf")
    res = client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": file_data},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf},
    )

    assert res.status_code == 201
    data = res.get_json()
    assert data["status"] == "success"
    report = data["report"]

    assert report["appointment_id"] == appt_id
    assert report["original_filename"] == "Soil_Analysis_Report.pdf"
    assert report["file_size_bytes"] == len(VALID_PDF_BYTES)
    expected_checksum = hashlib.sha256(VALID_PDF_BYTES).hexdigest()
    assert report["checksum_sha256"] == expected_checksum
    assert "uploaded_at" in report
    # Critical security requirement: internal storage file_path must never be leaked
    assert "file_path" not in report

    # Verify physical file in private report directory
    with app.app_context():
        db = get_db()
        row = db.execute("SELECT file_path FROM reports WHERE appointment_id = ?", (appt_id,)).fetchone()
        stored_filename = row["file_path"]

    # Must be UUID-based .pdf and must NOT use original filename
    assert stored_filename.endswith(".pdf")
    assert stored_filename != "Soil_Analysis_Report.pdf"
    assert len(stored_filename) == 32 + 4  # uuid hex (32) + .pdf (4)

    full_disk_path = os.path.join(report_dir, stored_filename)
    assert os.path.isfile(full_disk_path)
    with open(full_disk_path, "rb") as f:
        disk_bytes = f.read()
    assert disk_bytes == VALID_PDF_BYTES


# ============================================================================
# 2. APPOINTMENT RESTRICTIONS AND DUPLICATE UPLOADS
# ============================================================================

def test_upload_nonexistent_appointment_returns_404(client, app):
    """Uploading for a non-existent appointment returns HTTP 404."""
    create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    csrf = login_user(client, "+919876543200")

    file_data = (io.BytesIO(VALID_PDF_BYTES), "test.pdf")
    res = client.post(
        "/api/admin/appointments/99999/report",
        data={"file": file_data},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 404
    assert res.get_json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("invalid_status", ["Pending", "Approved", "Rejected"])
def test_upload_for_non_completed_appointment_returns_409(client, app, invalid_status):
    """Uploading report for appointments not in 'Completed' status returns HTTP 409 Conflict."""
    create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status=invalid_status)

    csrf = login_user(client, "+919876543200")
    file_data = (io.BytesIO(VALID_PDF_BYTES), "test.pdf")
    res = client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": file_data},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 409
    data = res.get_json()
    assert data["error"]["code"] == "CONFLICT"
    assert "Completed" in data["error"]["message"]


def test_upload_duplicate_report_returns_409(client, app):
    """Submitting a second report for an appointment returns HTTP 409 Conflict."""
    create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    csrf = login_user(client, "+919876543200")

    # 1. First upload succeeds
    file_data1 = (io.BytesIO(VALID_PDF_BYTES), "report_one.pdf")
    res1 = client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": file_data1},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf},
    )
    assert res1.status_code == 201

    # 2. Second upload rejected
    file_data2 = (io.BytesIO(VALID_PDF_BYTES), "report_two.pdf")
    res2 = client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": file_data2},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf},
    )
    assert res2.status_code == 409
    assert res2.get_json()["error"]["code"] == "CONFLICT"


# ============================================================================
# 3. FILE VALIDATION TESTS
# ============================================================================

def test_upload_missing_file_field(client, app):
    """Multipart request without 'file' field returns HTTP 400."""
    create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    csrf = login_user(client, "+919876543200")
    res = client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"wrong_field": (io.BytesIO(VALID_PDF_BYTES), "test.pdf")},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 400
    assert res.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_upload_empty_file_rejected(client, app, report_dir):
    """Empty (0-byte) file upload is rejected and temporary files cleaned up."""
    create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    csrf = login_user(client, "+919876543200")
    empty_file = (io.BytesIO(b""), "empty.pdf")
    res = client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": empty_file},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 400
    assert res.get_json()["error"]["code"] == "VALIDATION_ERROR"
    # Ensure no leftover files in report dir
    assert len(os.listdir(report_dir)) == 0


def test_upload_non_pdf_extension_rejected(client, app):
    """Files without .pdf extension are rejected."""
    create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    csrf = login_user(client, "+919876543200")
    for bad_name in ["report.txt", "report.png", "report.exe", "report.pdf.exe"]:
        file_data = (io.BytesIO(VALID_PDF_BYTES), bad_name)
        res = client.post(
            f"/api/admin/appointments/{appt_id}/report",
            data={"file": file_data},
            content_type="multipart/form-data",
            headers={"X-CSRF-Token": csrf},
        )
        assert res.status_code == 400
        assert res.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_upload_invalid_mime_type_rejected(client, app):
    """Files with non-PDF MIME type are rejected."""
    create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    csrf = login_user(client, "+919876543200")
    file_data = (io.BytesIO(VALID_PDF_BYTES), "report.pdf", "image/png")
    res = client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": file_data},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 400
    assert res.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_upload_invalid_pdf_signature_rejected(client, app, report_dir):
    """Files missing the %PDF- magic byte signature are rejected."""
    create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    csrf = login_user(client, "+919876543200")
    fake_pdf = b"NOT_A_PDF_HEADER\n%%EOF"
    res = client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": (io.BytesIO(fake_pdf), "fake.pdf")},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 400
    data = res.get_json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "%PDF-" in data["error"]["message"]
    assert len(os.listdir(report_dir)) == 0


def test_upload_missing_eof_marker_rejected(client, app, report_dir):
    """Files missing the %%EOF trailer marker are rejected."""
    create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    csrf = login_user(client, "+919876543200")
    truncated_pdf = b"%PDF-1.4\nSome body without trailer"
    res = client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": (io.BytesIO(truncated_pdf), "incomplete.pdf")},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 400
    data = res.get_json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "%%EOF" in data["error"]["message"]
    assert len(os.listdir(report_dir)) == 0


def test_upload_exceeding_10mb_rejected(client, app, report_dir):
    """Files larger than 10 MB are rejected during stream reading."""
    create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    csrf = login_user(client, "+919876543200")
    # Construct a payload slightly exceeding 10 MB
    header = b"%PDF-1.4\n"
    padding = b"A" * (10 * 1024 * 1024 + 100)
    footer = b"\n%%EOF"
    large_payload = header + padding + footer

    res = client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": (io.BytesIO(large_payload), "large.pdf")},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 400
    data = res.get_json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "exceeds maximum allowed size" in data["error"]["message"]
    assert len(os.listdir(report_dir)) == 0


def test_upload_path_traversal_filename_sanitized(client, app):
    """Filenames with path traversal characters are sanitized for original_filename metadata."""
    create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    csrf = login_user(client, "+919876543200")
    file_data = (io.BytesIO(VALID_PDF_BYTES), "../../etc/passwd.pdf")
    res = client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": file_data},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 201
    orig_name = res.get_json()["report"]["original_filename"]
    assert ".." not in orig_name
    assert "/" not in orig_name


# ============================================================================
# 4. FARMER REPORT ACCESS AND IDOR TESTS
# ============================================================================

def test_farmer_view_own_report_metadata_success(client, app):
    """Farmer views report metadata for their own completed appointment."""
    admin_id = create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    # Admin uploads report
    csrf_admin = login_user(client, "+919876543200")
    client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": (io.BytesIO(VALID_PDF_BYTES), "my_soil_test.pdf")},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf_admin},
    )

    # Farmer logs in
    login_user(client, "+919876543201")
    res = client.get(f"/api/appointments/{appt_id}/report")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    report = data["report"]
    assert report["appointment_id"] == appt_id
    assert report["original_filename"] == "my_soil_test.pdf"
    assert "file_path" not in report


def test_farmer_download_own_report_success(client, app):
    """Farmer downloads the official PDF report with proper headers."""
    admin_id = create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    # Admin uploads report
    csrf_admin = login_user(client, "+919876543200")
    client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": (io.BytesIO(VALID_PDF_BYTES), "official_report.pdf")},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf_admin},
    )

    # Farmer logs in and downloads
    login_user(client, "+919876543201")
    res = client.get(f"/api/appointments/{appt_id}/report/download")
    assert res.status_code == 200
    assert res.mimetype == "application/pdf"
    assert "attachment; filename=official_report.pdf" in res.headers.get("Content-Disposition", "")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert "no-store" in res.headers.get("Cache-Control", "")
    assert res.data == VALID_PDF_BYTES


def test_idor_farmer_cannot_access_or_download_another_farmers_report(client, app):
    """Anti-IDOR: Farmer B cannot access metadata or download Farmer A's report (returns safe 404)."""
    admin_id = create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_a_id = create_user_direct(app, "Farmer A", "+919876543201", role="farmer")
    farmer_b_id = create_user_direct(app, "Farmer B", "+919876543202", role="farmer")
    appt_a_id = create_appointment_direct(app, farmer_a_id, status="Completed")

    # Admin uploads report for Farmer A
    csrf_admin = login_user(client, "+919876543200")
    client.post(
        f"/api/admin/appointments/{appt_a_id}/report",
        data={"file": (io.BytesIO(VALID_PDF_BYTES), "farmer_a_report.pdf")},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf_admin},
    )

    # Farmer B logs in
    login_user(client, "+919876543202")

    # Farmer B metadata attempt on Farmer A appointment -> 404
    res_meta = client.get(f"/api/appointments/{appt_a_id}/report")
    assert res_meta.status_code == 404
    assert res_meta.get_json()["error"]["code"] == "NOT_FOUND"

    # Farmer B download attempt on Farmer A appointment -> 404
    res_down = client.get(f"/api/appointments/{appt_a_id}/report/download")
    assert res_down.status_code == 404
    assert res_down.get_json()["error"]["code"] == "NOT_FOUND"


def test_farmer_report_endpoints_when_no_report_exists_returns_404(client, app):
    """When an appointment has no report, metadata and download return 404."""
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    login_user(client, "+919876543201")
    res_meta = client.get(f"/api/appointments/{appt_id}/report")
    assert res_meta.status_code == 404
    assert res_meta.get_json()["error"]["code"] == "NOT_FOUND"

    res_down = client.get(f"/api/appointments/{appt_id}/report/download")
    assert res_down.status_code == 404
    assert res_down.get_json()["error"]["code"] == "NOT_FOUND"


# ============================================================================
# 5. ADMIN REPORT ACCESS TESTS
# ============================================================================

def test_admin_view_and_download_report_success(client, app):
    """Admin can view metadata and download any uploaded report."""
    create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    csrf_admin = login_user(client, "+919876543200")
    client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": (io.BytesIO(VALID_PDF_BYTES), "admin_view.pdf")},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf_admin},
    )

    # Admin view metadata
    res_meta = client.get(f"/api/admin/appointments/{appt_id}/report")
    assert res_meta.status_code == 200
    assert res_meta.get_json()["report"]["original_filename"] == "admin_view.pdf"

    # Admin download
    res_down = client.get(f"/api/admin/appointments/{appt_id}/report/download")
    assert res_down.status_code == 200
    assert res_down.data == VALID_PDF_BYTES
    assert "attachment; filename=admin_view.pdf" in res_down.headers.get("Content-Disposition", "")


def test_admin_report_endpoints_nonexistent_or_missing_returns_404(client, app):
    """Admin querying missing appointment or appointment with no report receives 404."""
    create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    login_user(client, "+919876543200")

    # Nonexistent appointment
    res1 = client.get("/api/admin/appointments/99999/report")
    assert res1.status_code == 404

    # Appointment without report
    res2 = client.get(f"/api/admin/appointments/{appt_id}/report")
    assert res2.status_code == 404


# ============================================================================
# 6. ROLE AND CSRF BOUNDARY TESTS
# ============================================================================

def test_unauthenticated_requests_rejected(client, app):
    """Unauthenticated users receive HTTP 401 on all report endpoints."""
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    assert client.get(f"/api/appointments/{appt_id}/report").status_code == 401
    assert client.get(f"/api/appointments/{appt_id}/report/download").status_code == 401
    assert client.get(f"/api/admin/appointments/{appt_id}/report").status_code == 401
    assert client.get(f"/api/admin/appointments/{appt_id}/report/download").status_code == 401


def test_farmer_cannot_access_admin_report_endpoints(client, app):
    """Farmers receive HTTP 403 when calling admin report upload, metadata, or download."""
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    csrf = login_user(client, "+919876543201")

    # 1. Upload attempt
    res_upload = client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": (io.BytesIO(VALID_PDF_BYTES), "test.pdf")},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf},
    )
    assert res_upload.status_code == 403
    assert res_upload.get_json()["error"]["code"] == "FORBIDDEN"

    # 2. Admin metadata attempt
    res_meta = client.get(f"/api/admin/appointments/{appt_id}/report")
    assert res_meta.status_code == 403

    # 3. Admin download attempt
    res_down = client.get(f"/api/admin/appointments/{appt_id}/report/download")
    assert res_down.status_code == 403


def test_admin_cannot_access_farmer_report_endpoints(client, app):
    """Admins receive HTTP 403 when calling farmer-specific report endpoints."""
    admin_id = create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    login_user(client, "+919876543200")
    assert client.get(f"/api/appointments/{appt_id}/report").status_code == 403
    assert client.get(f"/api/appointments/{appt_id}/report/download").status_code == 403


def test_admin_upload_report_csrf_protection(client, app):
    """Report upload requires valid CSRF token."""
    create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    csrf = login_user(client, "+919876543200")

    # Missing CSRF token
    res_missing = client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": (io.BytesIO(VALID_PDF_BYTES), "test.pdf")},
        content_type="multipart/form-data",
    )
    assert res_missing.status_code == 403
    assert res_missing.get_json()["error"]["code"] == "CSRF_ERROR"

    # Invalid CSRF token
    res_invalid = client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": (io.BytesIO(VALID_PDF_BYTES), "test.pdf")},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": "bad-token"},
    )
    assert res_invalid.status_code == 403
    assert res_invalid.get_json()["error"]["code"] == "CSRF_ERROR"


# ============================================================================
# 7. STORAGE INTEGRITY AND CLEANUP ON ERROR
# ============================================================================

def test_missing_disk_file_during_download_returns_safe_error(client, app, report_dir):
    """If database references a report whose disk file is deleted, returns safe 404 without leaking path."""
    admin_id = create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    csrf = login_user(client, "+919876543200")
    client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": (io.BytesIO(VALID_PDF_BYTES), "will_be_deleted.pdf")},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf},
    )

    # Delete physical file from disk to simulate orphaned record
    for f in os.listdir(report_dir):
        os.remove(os.path.join(report_dir, f))

    # Farmer attempts download
    login_user(client, "+919876543201")
    res = client.get(f"/api/appointments/{appt_id}/report/download")
    assert res.status_code == 404
    data = res.get_json()
    assert data["error"]["code"] == "FILE_NOT_FOUND"
    assert "missing or temporarily unavailable" in data["error"]["message"]
    # Internal path must not be present in output
    assert report_dir not in str(data)


# ============================================================================
# 8. FAILURE INJECTION AND CONTROLLED CRASH TESTS
# ============================================================================

def test_failure_injection_staging_write_error(client, app, report_dir, monkeypatch):
    """If an I/O error occurs while writing the staging file, staging file is cleaned up and 500 returned."""
    create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    csrf = login_user(client, "+919876543200")

    orig_open = open
    def mock_open(file, mode="r", *args, **kwargs):
        if isinstance(file, str) and ".staging_" in file:
            raise IOError("Simulated disk write failure")
        return orig_open(file, mode, *args, **kwargs)

    monkeypatch.setattr("builtins.open", mock_open)

    res = client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": (io.BytesIO(VALID_PDF_BYTES), "test.pdf")},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 500
    assert res.get_json()["error"]["code"] == "SERVER_ERROR"

    # Confirm no orphan files left on disk
    assert len(os.listdir(report_dir)) == 0

    # Confirm no report metadata record was created
    with app.app_context():
        db = get_db()
        count = db.execute("SELECT COUNT(*) FROM reports WHERE appointment_id = ?", (appt_id,)).fetchone()[0]
        assert count == 0


def test_failure_injection_atomic_move_error(client, app, report_dir, monkeypatch):
    """If atomic rename fails, staging file is cleaned up and 500 returned."""
    create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    csrf = login_user(client, "+919876543200")

    def mock_replace(src, dst):
        raise OSError("Simulated atomic rename failure")

    monkeypatch.setattr("os.replace", mock_replace)

    res = client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": (io.BytesIO(VALID_PDF_BYTES), "test.pdf")},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 500
    assert res.get_json()["error"]["code"] == "SERVER_ERROR"

    # Confirm staging and destination files are removed
    assert len(os.listdir(report_dir)) == 0


def test_failure_injection_db_insert_error_cleans_up_file(client, app, report_dir, monkeypatch):
    """If SQLite insertion fails, the newly moved physical PDF file is deleted and 0 DB rows remain."""
    create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    csrf = login_user(client, "+919876543200")

    from app import db as db_module
    orig_get_db = db_module.get_db

    class FaultyConnection:
        def __init__(self, real_con):
            self._con = real_con
        def __getattr__(self, name):
            return getattr(self._con, name)
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            return self._con.__exit__(exc_type, exc_val, exc_tb)
        def execute(self, sql, params=()):
            if "INSERT INTO reports" in sql:
                import sqlite3
                raise sqlite3.OperationalError("Simulated database failure during report insert")
            return self._con.execute(sql, params)

    def faulty_get_db():
        return FaultyConnection(orig_get_db())

    monkeypatch.setattr("app.reports.get_db", faulty_get_db)

    res = client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": (io.BytesIO(VALID_PDF_BYTES), "test.pdf")},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 500
    assert res.get_json()["error"]["code"] == "SERVER_ERROR"

    # Verify physical file was deleted from disk
    assert len(os.listdir(report_dir)) == 0

    # Verify no database metadata row exists
    with app.app_context():
        db = orig_get_db()
        count = db.execute("SELECT COUNT(*) FROM reports WHERE appointment_id = ?", (appt_id,)).fetchone()[0]
        assert count == 0


def test_failure_injection_db_integrity_error_cleans_up_file(client, app, report_dir, monkeypatch):
    """Simulates a low-level race condition where SQLite raises IntegrityError on insert."""
    create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    csrf = login_user(client, "+919876543200")

    from app import db as db_module
    orig_get_db = db_module.get_db

    class FaultyIntegrityConnection:
        def __init__(self, real_con):
            self._con = real_con
        def __getattr__(self, name):
            return getattr(self._con, name)
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            return self._con.__exit__(exc_type, exc_val, exc_tb)
        def execute(self, sql, params=()):
            if "INSERT INTO reports" in sql:
                import sqlite3
                raise sqlite3.IntegrityError("UNIQUE constraint failed: reports.appointment_id")
            return self._con.execute(sql, params)

    def faulty_get_db():
        return FaultyIntegrityConnection(orig_get_db())

    monkeypatch.setattr("app.reports.get_db", faulty_get_db)

    res = client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": (io.BytesIO(VALID_PDF_BYTES), "test.pdf")},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 409
    assert res.get_json()["error"]["code"] == "CONFLICT"

    # Verify file was cleaned up and no orphan file left on disk
    assert len(os.listdir(report_dir)) == 0


def test_failure_injection_db_commit_error_cleans_up_file(client, app, report_dir, monkeypatch):
    """If database COMMIT fails after moving file to final storage, file is deleted and 0 DB rows remain."""
    create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    csrf = login_user(client, "+919876543200")

    from app import db as db_module
    orig_get_db = db_module.get_db

    class FaultyCommitConnection:
        def __init__(self, real_con):
            self._con = real_con

        def __getattr__(self, name):
            return getattr(self._con, name)

        def __enter__(self):
            self._con.__enter__()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is None:
                # Simulate commit failure when exiting the 'with db:' transaction
                import sqlite3
                raise sqlite3.OperationalError("Simulated database commit failure (e.g. disk I/O error)")
            return self._con.__exit__(exc_type, exc_val, exc_tb)

        def rollback(self):
            return self._con.rollback()

    def faulty_get_db():
        return FaultyCommitConnection(orig_get_db())

    monkeypatch.setattr("app.reports.get_db", faulty_get_db)

    res = client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": (io.BytesIO(VALID_PDF_BYTES), "test.pdf")},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 500
    assert res.get_json()["error"]["code"] == "SERVER_ERROR"

    # Verify physical file was deleted from disk and no staging or orphaned files remain
    assert len(os.listdir(report_dir)) == 0

    # Verify no database metadata record was committed
    with app.app_context():
        db = orig_get_db()
        count = db.execute("SELECT COUNT(*) FROM reports WHERE appointment_id = ?", (appt_id,)).fetchone()[0]
        assert count == 0


# ============================================================================
# 9. CONCURRENT UPLOAD VERIFICATION
# ============================================================================

def test_concurrent_uploads_prevent_duplicate_reports(app, report_dir):
    """Two concurrent upload requests targeting the same completed appointment cannot create duplicate reports."""
    import concurrent.futures

    create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    def worker_upload(thread_id):
        cl = app.test_client()
        csrf_init = cl.get("/api/auth/csrf-token").get_json()["csrf_token"]
        cl.post("/api/auth/login", json={"phone": "+919876543200", "password": "Password123"}, headers={"X-CSRF-Token": csrf_init})
        csrf = cl.get("/api/auth/csrf-token").get_json()["csrf_token"]
        return cl.post(
            f"/api/admin/appointments/{appt_id}/report",
            data={"file": (io.BytesIO(VALID_PDF_BYTES), f"worker_{thread_id}.pdf")},
            content_type="multipart/form-data",
            headers={"X-CSRF-Token": csrf},
        ).status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(worker_upload, 1)
        f2 = executor.submit(worker_upload, 2)
        results = sorted([f1.result(), f2.result()])

    # Exactly one must succeed (201) and one must be rejected (409)
    assert results == [201, 409]

    # Exactly one report record in SQLite
    with app.app_context():
        db = get_db()
        count = db.execute("SELECT COUNT(*) FROM reports WHERE appointment_id = ?", (appt_id,)).fetchone()[0]
        assert count == 1
        stored_path = db.execute("SELECT file_path FROM reports WHERE appointment_id = ?", (appt_id,)).fetchone()["file_path"]

    # Exactly one physical PDF file on disk, matching the DB record
    disk_files = [f for f in os.listdir(report_dir) if not f.startswith(".")]
    assert len(disk_files) == 1
    assert disk_files[0] == stored_path


# ============================================================================
# 10. REQUEST SIZE LIMIT (MAX_CONTENT_LENGTH) TESTS
# ============================================================================

def test_request_entity_too_large_rejected_by_max_content_length(client, app, report_dir):
    """Requests exceeding MAX_CONTENT_LENGTH (12 MB) are rejected with HTTP 413 before processing."""
    create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    csrf = login_user(client, "+919876543200")

    # 13 MB payload (exceeds 12 MB MAX_CONTENT_LENGTH)
    huge_payload = b"%PDF-1.4\n" + b"X" * (13 * 1024 * 1024) + b"\n%%EOF"
    res = client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": (io.BytesIO(huge_payload), "huge.pdf")},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 413
    assert res.get_json() == {
        "error": {
            "code": "PAYLOAD_TOO_LARGE",
            "message": "Request payload exceeds maximum permitted size.",
        }
    }

    # Confirm nothing was written to report storage
    assert len(os.listdir(report_dir)) == 0


def test_upload_valid_file_within_max_content_length(client, app, report_dir):
    """A valid 1 MB PDF is well within MAX_CONTENT_LENGTH and uploads successfully."""
    create_user_direct(app, "Admin Chief", "+919876543200", role="admin")
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, farmer_id, status="Completed")

    csrf = login_user(client, "+919876543200")

    # 1 MB valid PDF
    body = b"A" * (1024 * 1024)
    valid_1mb_pdf = b"%PDF-1.4\n" + body + b"\n%%EOF"

    res = client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": (io.BytesIO(valid_1mb_pdf), "valid_1mb.pdf")},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 201
    assert res.get_json()["report"]["file_size_bytes"] == len(valid_1mb_pdf)


# ============================================================================
# 11. FILENAME SANITIZATION SAFETY AND FALLBACK TESTS
# ============================================================================

@pytest.mark.parametrize("input_name, expected_output", [
    ("", "report.pdf"),
    ("   ", "report.pdf"),
    (".pdf", "report.pdf"),
    ("....pdf", "report.pdf"),
    ("___..pdf", "report.pdf"),
    ("my report.pdf", "my_report.pdf"),
    ("sample#1@field.pdf", "sample1field.pdf"),
    ("../../etc/shadow.pdf", "etc_shadow.pdf"),
    ("a" * 300 + ".pdf", "a" * 196 + ".pdf"),
])
def test_filename_safety_edge_cases_and_fallbacks(input_name, expected_output):
    """Verifies that sanitize_original_filename always produces a safe, non-empty .pdf filename."""
    from app.reports import sanitize_original_filename
    result = sanitize_original_filename(input_name)
    assert result.endswith(".pdf")
    assert ".." not in result
    assert "/" not in result
    assert "\\" not in result
    assert len(result) <= 200
    assert result == expected_output

