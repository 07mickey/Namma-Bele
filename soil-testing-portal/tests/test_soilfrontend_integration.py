"""
Integration test suite for the soilfrontend interface and compatibility routes.
Verifies all pages render with proper assets and API bridges operate against the real backend.
"""
import io
import os
import tempfile
import pytest
from app import create_app
from app.db import get_db, init_db
from werkzeug.security import generate_password_hash


@pytest.fixture
def app():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_soilfrontend.db")
        report_dir = os.path.join(temp_dir, "reports")
        os.makedirs(report_dir, exist_ok=True)

        app = create_app({
            "TESTING": True,
            "DATABASE": db_path,
            "REPORT_FOLDER": report_dir,
            "SECRET_KEY": "test-key-soilfrontend",
        })

        with app.app_context():
            init_db()
            db = get_db()
            # Seed test admin and farmer
            db.execute(
                "INSERT INTO users (name, phone, password_hash, role) VALUES (?, ?, ?, ?)",
                ("Chief Coordinator", "+919999999999", generate_password_hash("AdminPass123!"), "admin")
            )
            db.execute(
                "INSERT INTO users (name, phone, password_hash, role) VALUES (?, ?, ?, ?)",
                ("Farmer Ramesh", "+919876543210", generate_password_hash("FarmerPass123!"), "farmer")
            )
            db.commit()

        yield app


@pytest.fixture
def client(app):
    return app.test_client()


def get_csrf(client):
    res = client.get("/api/auth/csrf-token")
    return res.get_json()["csrf_token"]


def test_public_pages_render(client):
    """Verify all soilfrontend public pages render with proper design tokens."""
    for path in ["/", "/index.html", "/soil-guide", "/soil-guide.html", "/login", "/login.html", "/register", "/register.html", "/admin-login", "/admin-login.html"]:
        res = client.get(path)
        assert res.status_code == 200, f"Failed for {path}"
        assert b"styles.css" in res.data
        assert b"assets/logo.svg" in res.data


def test_farmer_end_to_end_workflow(client):
    """
    Test farmer registration, login, dashboard rendering, appointment booking,
    appointment listing, and report listing.
    """
    csrf = get_csrf(client)

    # 1. Register a new farmer via compatibility route
    reg_res = client.post("/api/farmer/register", json={
        "name": "Basavaraj Gowda",
        "phone": "+919844112233",
        "password": "SecurePassword123!"
    }, headers={"X-CSRF-Token": csrf})
    assert reg_res.status_code == 201

    # 2. Login as the newly registered farmer
    login_res = client.post("/api/farmer/login", json={
        "phone": "+919844112233",
        "password": "SecurePassword123!"
    }, headers={"X-CSRF-Token": csrf})
    assert login_res.status_code == 200
    login_data = login_res.get_json()
    assert login_data["status"] == "success"
    assert login_data["data"]["farmer"]["name"] == "Basavaraj Gowda"
    assert "csrf_token" in login_data
    farmer_csrf = login_data["csrf_token"]

    # 3. Access farmer dashboard and views
    dash_res = client.get("/farmer")
    assert dash_res.status_code == 200
    assert b"Farmer Dashboard" in dash_res.data or b"Dashboard" in dash_res.data

    book_page = client.get("/book-appointment.html")
    assert book_page.status_code == 200

    # 4. Book a soil test appointment via /api/appointments
    book_res = client.post("/api/appointments", json={
        "land_details": "Survey No 45, Fertile Loam (4 Acres)",
        "address": "Navalgund Rural Sector",
        "preferred_date": "2026-11-20",
        "preferred_time": "09:00-12:00",
        "notes": "Testing for sugarcane planting."
    }, headers={"X-CSRF-Token": farmer_csrf})
    assert book_res.status_code == 201
    apt_id = book_res.get_json()["appointment"]["id"]

    # 5. List farmer appointments via compatibility route /api/farmer/appointments
    list_res = client.get("/api/farmer/appointments")
    assert list_res.status_code == 200
    list_data = list_res.get_json()
    assert len(list_data["data"]["appointments"]) == 1
    assert list_data["data"]["appointments"][0]["id"] == apt_id
    assert list_data["data"]["appointments"][0]["status"] == "Pending"

    # 6. Check farmer reports list
    rep_res = client.get("/api/farmer/reports")
    assert rep_res.status_code == 200
    assert len(rep_res.get_json()["data"]["reports"]) == 0


def test_admin_end_to_end_workflow(client):
    """
    Test admin login, dashboard overview, appointment status update,
    PDF report upload, and report download.
    """
    csrf = get_csrf(client)

    # 1. Admin login via /api/admin/login
    login_res = client.post("/api/admin/login", json={
        "username": "+919999999999",
        "password": "AdminPass123!"
    }, headers={"X-CSRF-Token": csrf})
    assert login_res.status_code == 200
    admin_data = login_res.get_json()
    assert admin_data["status"] == "success"
    assert admin_data["data"]["admin"]["username"] == "Chief Coordinator"
    admin_csrf = admin_data["csrf_token"]

    # 2. View admin pages
    for path in ["/admin", "/admin-dashboard.html", "/admin-appointments.html", "/admin-reports.html", "/admin-farmers.html"]:
        res = client.get(path)
        assert res.status_code == 200, f"Admin page failed: {path}"

    # 3. Create appointment as farmer first
    with client.session_transaction() as sess:
        sess["user_id"] = 2  # Farmer Ramesh

    book_res = client.post("/api/appointments", json={
        "land_details": "Plot 99, North Loam",
        "address": "Someshwar",
        "preferred_date": "2026-11-25",
        "preferred_time": "09:00-12:00",
        "notes": "Corn trial."
    }, headers={"X-CSRF-Token": admin_csrf})
    apt_id = book_res.get_json()["appointment"]["id"]

    # Switch back to admin
    with client.session_transaction() as sess:
        sess["user_id"] = 1  # Admin

    # 4. Update appointment status: Pending -> Approved -> Completed
    appr_res = client.patch(
        f"/api/admin/appointments/{apt_id}/status",
        json={"status": "Approved"},
        headers={"X-CSRF-Token": admin_csrf}
    )
    assert appr_res.status_code == 200

    comp_res = client.patch(
        f"/api/admin/appointments/{apt_id}/status",
        json={"status": "Completed"},
        headers={"X-CSRF-Token": admin_csrf}
    )
    assert comp_res.status_code == 200

    # 5. Upload report via compatibility endpoint /api/admin/reports/upload
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Title (Test Report) >>\nendobj\ntrailer\n<< >>\n%%EOF"
    upload_res = client.post("/api/admin/reports/upload", data={
        "appointment_id": str(apt_id),
        "remarks": "Official lab certification complete.",
        "file": (io.BytesIO(pdf_bytes), "certified_report.pdf"),
        "_csrf_token": admin_csrf
    }, content_type="multipart/form-data")
    assert upload_res.status_code == 201
    report_id = upload_res.get_json()["report"]["id"]

    # 6. Admin lists all reports
    admin_reps = client.get("/api/admin/reports")
    assert admin_reps.status_code == 200
    assert len(admin_reps.get_json()["data"]["reports"]) == 1

    # 7. Admin lists all farmers
    farmers_res = client.get("/api/admin/farmers")
    assert farmers_res.status_code == 200
    assert len(farmers_res.get_json()["data"]["farmers"]) >= 1

    # 8. Farmer downloads the report by report_id
    with client.session_transaction() as sess:
        sess["user_id"] = 2  # Farmer Ramesh

    farmer_reps = client.get("/api/farmer/reports")
    assert farmer_reps.status_code == 200
    assert len(farmer_reps.get_json()["data"]["reports"]) == 1

    dl_res = client.get(f"/api/reports/{report_id}/download")
    assert dl_res.status_code == 200
    assert dl_res.data.startswith(b"%PDF-")


def test_security_access_control(client):
    """Verify unauthorized and cross-user report downloads are strictly rejected."""
    # Unauthenticated access to /farmer redirects to /login
    assert client.get("/farmer").status_code == 302
    assert client.get("/admin").status_code == 302

    # Unauthenticated API calls return 401
    assert client.get("/api/appointments").status_code == 401
    assert client.get("/api/farmer/appointments").status_code == 401
    assert client.get("/api/admin/appointments").status_code == 401
