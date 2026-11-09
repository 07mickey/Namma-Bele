import io
import os
import tempfile
import pytest
from app import create_app
from app.db import init_db

VALID_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< >>\n%%EOF"


@pytest.fixture
def app():
    """Creates a temporary, isolated Flask application instance with its own test database."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_views.db")
        reports_dir = os.path.join(temp_dir, "reports")
        os.makedirs(reports_dir, exist_ok=True)

        app = create_app({
            "TESTING": True,
            "DATABASE": db_path,
            "REPORT_FOLDER": reports_dir,
            "SECRET_KEY": "test-views-secret-key-12345",
        })

        with app.app_context():
            init_db()

        yield app


@pytest.fixture
def client(app):
    """Provides a test client with cookie jar."""
    return app.test_client()


# ============================================================================
# 1. HTML PAGE RENDERING TESTS
# ============================================================================

def test_render_index_page(client):
    """GET / renders index.html with portal branding and diagnostic elements."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "Community Soil Testing Portal" in html
    assert "Portal Diagnostics" in html
    assert "/static/css/style.css" in html
    assert "/static/js/api.js" in html


def test_render_register_page(client):
    """GET /register renders register.html with farmer registration form."""
    res = client.get("/register")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "Farmer Registration" in html
    assert 'id="register-form"' in html
    assert 'name="name"' in html
    assert 'name="phone"' in html
    assert 'name="password"' in html


def test_render_login_page(client):
    """GET /login renders login.html with authentication form and dual Farmer & Staff/Admin entry options."""
    res = client.get("/login")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "Portal Login" in html
    assert 'id="login-form"' in html
    assert 'id="login-phone"' in html
    assert 'id="login-password"' in html

    # Dual Login Options
    assert 'id="tab-farmer-login"' in html
    assert 'id="tab-staff-login"' in html
    assert "Farmer Login" in html
    assert "Staff / Admin Login" in html

    # Staff description requirement
    assert "Authorized access for operators, field workers, laboratory staff, and administrators." in html

    # Farmer links requirement
    assert 'id="link-forgot-password"' in html
    assert "Forgot password?" in html
    assert 'href="/register"' in html
    assert "Register here" in html

    # Staff security notice (no public registration)
    assert 'id="staff-footer-notice"' in html
    assert "Staff accounts are provisioned exclusively by authorized administrators." in html


def test_render_farmer_page_unauthenticated_redirects(client):
    """GET /farmer without authentication redirects (302) to /login."""
    res = client.get("/farmer")
    assert res.status_code == 302
    assert res.headers["Location"] == "/login" or res.headers["Location"].endswith("/login")


def test_render_admin_page_unauthenticated_redirects(client):
    """GET /admin without authentication redirects (302) to /login."""
    res = client.get("/admin")
    assert res.status_code == 302
    assert res.headers["Location"] == "/login" or res.headers["Location"].endswith("/login")


def test_render_farmer_page_authenticated(app, client):
    """GET /farmer with farmer session renders farmer.html (200), but GET /admin redirects to /farmer."""
    from app.db import get_db
    from werkzeug.security import generate_password_hash

    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users (name, phone, password_hash, role) VALUES (?, ?, ?, ?)",
            ("Kishan Kumar", "+919876543290", generate_password_hash("Pass1234"), "farmer"),
        )
        db.commit()

    csrf_token = client.get("/api/auth/csrf-token").get_json()["csrf_token"]
    client.post(
        "/api/auth/login",
        json={"phone": "+919876543290", "password": "Pass1234"},
        headers={"X-CSRF-Token": csrf_token},
    )

    res = client.get("/farmer")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "Farmer Portal" in html
    assert "Book a Soil Sample Collection Appointment" in html
    assert 'id="appointment-form"' in html
    assert 'id="appointments-table"' in html
    assert "/static/js/farmer.js" in html

    # Farmer accessing /admin is redirected to /farmer
    res_admin = client.get("/admin")
    assert res_admin.status_code == 302
    assert res_admin.headers["Location"] == "/farmer" or res_admin.headers["Location"].endswith("/farmer")

    # Farmer accessing /login or /register is redirected to /farmer
    assert client.get("/login").status_code == 302
    assert client.get("/register").status_code == 302


def test_render_admin_page_authenticated(app, client):
    """GET /admin with admin session renders admin.html (200), but GET /farmer redirects to /admin."""
    from app.db import get_db
    from werkzeug.security import generate_password_hash

    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users (name, phone, password_hash, role) VALUES (?, ?, ?, ?)",
            ("Officer Admin", "+919876543291", generate_password_hash("AdminPass123"), "admin"),
        )
        db.commit()

    csrf_token = client.get("/api/auth/csrf-token").get_json()["csrf_token"]
    client.post(
        "/api/auth/login",
        json={"phone": "+919876543291", "password": "AdminPass123"},
        headers={"X-CSRF-Token": csrf_token},
    )

    res = client.get("/admin")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "Administrator Dashboard" in html
    assert "Appointment Queue" in html
    assert 'id="status-filter-bar"' in html
    assert 'id="admin-table"' in html
    assert "/static/js/admin.js" in html

    # Admin accessing /farmer is redirected to /admin
    res_farmer = client.get("/farmer")
    assert res_farmer.status_code == 302
    assert res_farmer.headers["Location"] == "/admin" or res_farmer.headers["Location"].endswith("/admin")

    # Admin accessing /login or /register is redirected to /admin
    assert client.get("/login").status_code == 302
    assert client.get("/register").status_code == 302


# ============================================================================
# 2. STATIC ASSETS TESTS
# ============================================================================

def test_static_css_and_js_served_correctly(client):
    """Static assets are served with proper content types."""
    res_css = client.get("/static/css/style.css")
    assert res_css.status_code == 200
    assert "text/css" in res_css.content_type
    assert "--primary:" in res_css.data.decode("utf-8")

    res_api = client.get("/static/js/api.js")
    assert res_api.status_code == 200
    assert "javascript" in res_api.content_type
    assert "const API =" in res_api.data.decode("utf-8")

    res_farmer = client.get("/static/js/farmer.js")
    assert res_farmer.status_code == 200
    assert "javascript" in res_farmer.content_type

    res_admin = client.get("/static/js/admin.js")
    assert res_admin.status_code == 200
    assert "javascript" in res_admin.content_type


# ============================================================================
# 3. END-TO-END WORKFLOW INTEGRATION TESTS
# ============================================================================

def test_e2e_farmer_registration_and_booking_workflow(client):
    """Simulates complete farmer journey: register, login, check session, book, view list & details."""
    # 1. Fetch CSRF token
    csrf_res = client.get("/api/auth/csrf-token")
    csrf_token = csrf_res.get_json()["csrf_token"]

    # 2. Register Farmer
    reg_res = client.post(
        "/api/auth/register",
        json={
            "name": "Kishan Lal",
            "phone": "+919876543211",
            "password": "FarmerPassword123",
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert reg_res.status_code == 201
    assert reg_res.get_json()["user"]["role"] == "farmer"

    # 3. Login
    login_res = client.post(
        "/api/auth/login",
        json={
            "phone": "+919876543211",
            "password": "FarmerPassword123",
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert login_res.status_code == 200
    assert login_res.get_json()["user"]["role"] == "farmer"

    # 4. Check Auth Session
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    me_data = me_res.get_json()
    assert me_data["authenticated"] is True
    assert me_data["user"]["phone"] == "+919876543211"

    # 5. Refresh CSRF token for subsequent state change
    csrf_token = client.get("/api/auth/csrf-token").get_json()["csrf_token"]

    # 6. Book an appointment
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    tomorrow = (datetime.now(ZoneInfo("Asia/Kolkata")) + timedelta(days=1)).strftime("%Y-%m-%d")

    book_res = client.post(
        "/api/appointments",
        json={
            "land_details": "5 acres wheat crop, black cotton soil",
            "address": "Survey 108, South Farm, Rampur",
            "preferred_date": tomorrow,
            "preferred_time": "09:00-12:00",
            "notes": "Near water canal gate",
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert book_res.status_code == 201
    appt = book_res.get_json()["appointment"]
    appt_id = appt["id"]
    assert appt["status"] == "Pending"

    # 7. List appointments
    list_res = client.get("/api/appointments")
    assert list_res.status_code == 200
    appointments = list_res.get_json()["appointments"]
    assert len(appointments) == 1
    assert appointments[0]["id"] == appt_id

    # 8. Get appointment details
    detail_res = client.get(f"/api/appointments/{appt_id}")
    assert detail_res.status_code == 200
    assert detail_res.get_json()["appointment"]["land_details"] == "5 acres wheat crop, black cotton soil"

    # 9. Logout
    csrf_token = client.get("/api/auth/csrf-token").get_json()["csrf_token"]
    logout_res = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert logout_res.status_code == 200

    # 10. Verify unauthenticated state
    me_res_after = client.get("/api/auth/me")
    assert me_res_after.get_json()["authenticated"] is False


def test_e2e_admin_management_and_report_upload_workflow(app, client):
    """Simulates admin workflow: login, inspect queue, approve, complete, upload report, download report."""
    from app.db import get_db
    from werkzeug.security import generate_password_hash
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    # Create admin and farmer in database
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users (name, phone, password_hash, role) VALUES (?, ?, ?, ?)",
            ("Admin Incharge", "+919876543200", generate_password_hash("AdminPass123"), "admin"),
        )
        db.execute(
            "INSERT INTO users (name, phone, password_hash, role) VALUES (?, ?, ?, ?)",
            ("Farmer Ramesh", "+919876543201", generate_password_hash("FarmerPass123"), "farmer"),
        )
        farmer_row = db.execute("SELECT id FROM users WHERE phone = '+919876543201'").fetchone()
        farmer_id = farmer_row["id"]

        tomorrow = (datetime.now(ZoneInfo("Asia/Kolkata")) + timedelta(days=1)).strftime("%Y-%m-%d")
        db.execute(
            """
            INSERT INTO appointments (farmer_id, land_details, address, preferred_date, preferred_time, status)
            VALUES (?, ?, ?, ?, ?, 'Pending')
            """,
            (farmer_id, "2 acres vegetables", "Plot 14", tomorrow, "14:00-17:00"),
        )
        appt_row = db.execute("SELECT id FROM appointments WHERE farmer_id = ?", (farmer_id,)).fetchone()
        appt_id = appt_row["id"]
        db.commit()

    # 1. Admin login
    csrf_token = client.get("/api/auth/csrf-token").get_json()["csrf_token"]
    login_res = client.post(
        "/api/auth/login",
        json={"phone": "+919876543200", "password": "AdminPass123"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert login_res.status_code == 200
    assert login_res.get_json()["user"]["role"] == "admin"

    # 2. Admin views queue
    queue_res = client.get("/api/admin/appointments")
    assert queue_res.status_code == 200
    appts = queue_res.get_json()["appointments"]
    assert len(appts) == 1
    assert appts[0]["id"] == appt_id
    assert appts[0]["status"] == "Pending"

    # 3. Admin transitions status: Pending -> Approved
    csrf_token = client.get("/api/auth/csrf-token").get_json()["csrf_token"]
    appr_res = client.patch(
        f"/api/admin/appointments/{appt_id}/status",
        json={"status": "Approved"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert appr_res.status_code == 200
    assert appr_res.get_json()["appointment"]["status"] == "Approved"

    # 4. Admin transitions status: Approved -> Completed
    csrf_token = client.get("/api/auth/csrf-token").get_json()["csrf_token"]
    comp_res = client.patch(
        f"/api/admin/appointments/{appt_id}/status",
        json={"status": "Completed"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert comp_res.status_code == 200
    assert comp_res.get_json()["appointment"]["status"] == "Completed"

    # 5. Admin uploads official PDF report
    csrf_token = client.get("/api/auth/csrf-token").get_json()["csrf_token"]
    upload_res = client.post(
        f"/api/admin/appointments/{appt_id}/report",
        data={"file": (io.BytesIO(VALID_PDF_BYTES), "Ramesh_Soil_Report.pdf")},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert upload_res.status_code == 201
    assert upload_res.get_json()["report"]["original_filename"] == "Ramesh_Soil_Report.pdf"

    # 6. Admin inspects report metadata
    meta_res = client.get(f"/api/admin/appointments/{appt_id}/report")
    assert meta_res.status_code == 200
    assert meta_res.get_json()["report"]["original_filename"] == "Ramesh_Soil_Report.pdf"

    # 7. Admin downloads report
    dl_admin = client.get(f"/api/admin/appointments/{appt_id}/report/download")
    assert dl_admin.status_code == 200
    assert dl_admin.data == VALID_PDF_BYTES

    # 8. Farmer logs in and downloads report
    csrf_token = client.get("/api/auth/csrf-token").get_json()["csrf_token"]
    client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_token})

    csrf_token = client.get("/api/auth/csrf-token").get_json()["csrf_token"]
    client.post(
        "/api/auth/login",
        json={"phone": "+919876543201", "password": "FarmerPass123"},
        headers={"X-CSRF-Token": csrf_token},
    )

    farmer_dl = client.get(f"/api/appointments/{appt_id}/report/download")
    assert farmer_dl.status_code == 200
    assert farmer_dl.data == VALID_PDF_BYTES


def test_xss_resilience_in_appointment_and_client_escaping(app, client):
    """
    Verifies that appointment fields with script tags or markup are safely stored as plain text
    and client escaping patterns properly neutralize HTML tags.
    """
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    csrf_token = client.get("/api/auth/csrf-token").get_json()["csrf_token"]
    reg_res = client.post(
        "/api/auth/register",
        json={
            "name": "<script>alert('xss-name')</script>",
            "phone": "+919876543299",
            "password": "Password123",
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert reg_res.status_code == 201

    csrf_token = client.get("/api/auth/csrf-token").get_json()["csrf_token"]
    login_res = client.post(
        "/api/auth/login",
        json={
            "phone": "+919876543299",
            "password": "Password123",
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert login_res.status_code == 200

    csrf_token = client.get("/api/auth/csrf-token").get_json()["csrf_token"]
    tomorrow = (datetime.now(ZoneInfo("Asia/Kolkata")) + timedelta(days=1)).strftime("%Y-%m-%d")

    book_res = client.post(
        "/api/appointments",
        json={
            "land_details": "<img src=x onerror=alert('xss-land')>",
            "address": "<b>Plot 101</b><script>fetch('/steal')</script>",
            "preferred_date": tomorrow,
            "preferred_time": "14:00-17:00",
            "notes": "<svg onload=alert('xss-notes')>",
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert book_res.status_code == 201
    appt = book_res.get_json()["appointment"]

    # Verify API stores and returns data faithfully as string text
    assert appt["land_details"] == "<img src=x onerror=alert('xss-land')>"
    assert appt["address"] == "<b>Plot 101</b><script>fetch('/steal')</script>"
    assert appt["notes"] == "<svg onload=alert('xss-notes')>"

    # Verify python equivalent of client escapeHtml logic:
    def client_escape_html(s):
        return (
            str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#039;")
        )

    escaped_land = client_escape_html(appt["land_details"])
    escaped_addr = client_escape_html(appt["address"])
    assert "<img" not in escaped_land
    assert "&lt;img" in escaped_land
    assert "<script" not in escaped_addr
    assert "&lt;script&gt;" in escaped_addr


def test_render_new_operational_views(app, client):
    """Verifies that all newly added views render correctly with HTTP 200."""
    from werkzeug.security import generate_password_hash
    from app.db import get_db

    # Public pages
    assert client.get("/contact").status_code == 200
    assert client.get("/claim").status_code == 200

    # Create users
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users (name, phone, password_hash, role) VALUES ('Farmer View', '+919876543701', ?, 'farmer')",
            (generate_password_hash("Password123"),),
        )
        db.execute(
            "INSERT INTO users (name, phone, password_hash, role) VALUES ('Operator View', '+919876543702', ?, 'operator')",
            (generate_password_hash("Password123"),),
        )
        db.execute(
            "INSERT INTO users (name, phone, password_hash, role) VALUES ('Field Worker View', '+919876543703', ?, 'field_worker')",
            (generate_password_hash("Password123"),),
        )
        db.execute(
            "INSERT INTO users (name, phone, password_hash, role) VALUES ('Lab View', '+919876543704', ?, 'lab_staff')",
            (generate_password_hash("Password123"),),
        )
        db.execute(
            "INSERT INTO users (name, phone, password_hash, role) VALUES ('Advisor View', '+919876543705', ?, 'advisor')",
            (generate_password_hash("Password123"),),
        )
        db.commit()

    # Authenticate farmer
    csrf = client.get("/api/auth/csrf-token").get_json()["csrf_token"]
    client.post("/api/auth/login", json={"phone": "+919876543701", "password": "Password123"}, headers={"X-CSRF-Token": csrf})

    # Farmer views
    assert client.get("/farmer/tracking").status_code == 200
    assert client.get("/farmer/plots").status_code == 200
    assert client.get("/farmer/crop-history").status_code == 200
    assert client.get("/farmer/farm-records").status_code == 200
    assert client.get("/farmer/addresses").status_code == 200
    assert client.get("/farmer/expert-help").status_code == 200

    # Staff views as operator
    csrf = client.get("/api/auth/csrf-token").get_json()["csrf_token"]
    client.post("/api/auth/login", json={"phone": "+919876543702", "password": "Password123"}, headers={"X-CSRF-Token": csrf})
    assert client.get("/operator").status_code == 200
    assert client.get("/admin/tracking").status_code == 200
    assert client.get("/admin/dispatch").status_code == 200

    # Field worker
    csrf = client.get("/api/auth/csrf-token").get_json()["csrf_token"]
    client.post("/api/auth/login", json={"phone": "+919876543703", "password": "Password123"}, headers={"X-CSRF-Token": csrf})
    assert client.get("/field-worker").status_code == 200

    # Lab staff
    csrf = client.get("/api/auth/csrf-token").get_json()["csrf_token"]
    client.post("/api/auth/login", json={"phone": "+919876543704", "password": "Password123"}, headers={"X-CSRF-Token": csrf})
    assert client.get("/lab").status_code == 200

    # Advisor
    csrf = client.get("/api/auth/csrf-token").get_json()["csrf_token"]
    client.post("/api/auth/login", json={"phone": "+919876543705", "password": "Password123"}, headers={"X-CSRF-Token": csrf})
    assert client.get("/advisor").status_code == 200

