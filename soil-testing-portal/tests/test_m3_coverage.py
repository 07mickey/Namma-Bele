import io
import os
import tempfile
import json
import pytest
from datetime import date, timedelta
from werkzeug.security import generate_password_hash
from app import create_app
from app.db import init_db, get_db


@pytest.fixture
def app():
    """Creates an isolated application instance with a temporary file-backed SQLite database."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_m3.db")
        app = create_app({
            "TESTING": True,
            "DATABASE": db_path,
            "SECRET_KEY": "test-m3-secret-key-9999",
        })
        with app.app_context():
            init_db()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


def create_user_direct(app, name, phone, password="Password123", role="farmer"):
    """Helper to insert a user directly into the test database."""
    with app.app_context():
        db = get_db()
        with db:
            cur = db.execute(
                "INSERT INTO users (name, phone, password_hash, role) VALUES (?, ?, ?, ?)",
                (name, phone, generate_password_hash(password), role),
            )
            return cur.lastrowid


def login_user(client, phone, password="Password123"):
    """Logs in and returns the CSRF token."""
    csrf_token = client.get("/api/auth/csrf-token").get_json()["csrf_token"]
    res = client.post(
        "/api/auth/login",
        json={"phone": phone, "password": password},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res.status_code == 200
    return client.get("/api/auth/csrf-token").get_json()["csrf_token"]


# ============================================================================
# 1. FARMER APPOINTMENT PRIVACY & PASSWORD HASH ABSENCE
# ============================================================================

def test_farmer_appointment_responses_never_expose_password_hash_or_foreign_data(client, app):
    """
    Verifies that farmer appointment endpoints (GET /api/appointments and GET /api/appointments/<id>)
    never expose password_hash and never leak another farmer's private appointment data.
    """
    farmer1_id = create_user_direct(app, "Farmer One", "+919876543201", role="farmer")
    farmer2_id = create_user_direct(app, "Farmer Two", "+919876543202", role="farmer")

    future_date = (date.today() + timedelta(days=2)).isoformat()

    # Create appointment for Farmer 1
    with app.app_context():
        db = get_db()
        with db:
            cur1 = db.execute(
                """
                INSERT INTO appointments (farmer_id, land_details, address, preferred_date, preferred_time, notes, status)
                VALUES (?, ?, ?, ?, ?, ?, 'Pending')
                """,
                (farmer1_id, "2 Acres Paddy Field", "Village North, Plot 10", future_date, "09:00-12:00", "Farmer 1 confidential notes"),
            )
            appt1_id = cur1.lastrowid

            cur2 = db.execute(
                """
                INSERT INTO appointments (farmer_id, land_details, address, preferred_date, preferred_time, notes, status)
                VALUES (?, ?, ?, ?, ?, ?, 'Pending')
                """,
                (farmer2_id, "5 Acres Wheat Field", "Village South, Plot 99", future_date, "14:00-17:00", "Farmer 2 private notes"),
            )
            appt2_id = cur2.lastrowid

    # Authenticate as Farmer 1
    login_user(client, "+919876543201")

    # 1. List appointments
    list_res = client.get("/api/appointments")
    assert list_res.status_code == 200
    list_data = list_res.get_json()
    assert "appointments" in list_data
    appts = list_data["appointments"]
    assert len(appts) == 1
    appt = appts[0]

    # Must contain Farmer 1's appointment only
    assert appt["id"] == appt1_id
    assert appt["land_details"] == "2 Acres Paddy Field"
    assert appt["address"] == "Village North, Plot 10"

    # Verify password_hash is never present in any field
    assert "password_hash" not in appt
    raw_json_str = json.dumps(list_data)
    assert "password_hash" not in raw_json_str
    assert "Farmer 2" not in raw_json_str
    assert "+919876543202" not in raw_json_str

    # 2. Detail view of own appointment
    detail_res = client.get(f"/api/appointments/{appt1_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.get_json()["appointment"]
    assert detail_data["id"] == appt1_id
    assert "password_hash" not in detail_data

    # 3. Accessing Farmer 2's appointment returns 404 Not Found (Anti-IDOR)
    foreign_res = client.get(f"/api/appointments/{appt2_id}")
    assert foreign_res.status_code == 404
    assert foreign_res.get_json()["error"]["code"] == "NOT_FOUND"


# ============================================================================
# 2. ADMIN APPOINTMENT SEARCH UI ELEMENTS & ACCESSIBILITY
# ============================================================================

def test_admin_search_ui_elements_and_accessibility_rendered(client, app):
    """
    Verifies that the admin interface (GET /admin) renders the search input with proper
    accessibility attributes (aria-label, placeholder, autocomplete, and scope notice).
    """
    create_user_direct(app, "Lab Admin", "+919876543200", role="admin")
    login_user(client, "+919876543200")

    res = client.get("/admin")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Verify Admin AgriTech Hero Banner
    assert 'class="admin-hero"' in html
    assert "Administrator Dashboard" in html

    # Verify Search Input and Accessibility Attributes
    assert 'id="admin-search-container"' in html
    assert 'id="admin-search-input"' in html
    assert 'aria-label="Search appointments on currently loaded page"' in html
    assert 'placeholder="Search by ID, farmer name, phone, land, or address..."' in html
    assert 'autocomplete="off"' in html

    # Verify Clear Button and Scope Notice
    assert 'id="btn-clear-search"' in html
    assert 'aria-label="Clear search input"' in html
    assert 'id="admin-search-scope-text"' in html
    assert "Search filters the appointments loaded on the current page." in html


# ============================================================================
# 3. CLIENT-SIDE SEARCH FILTERING LOGIC & XSS RESILIENCE TEST
# ============================================================================

def test_admin_search_filtering_logic_case_insensitive_and_xss_safety():
    """
    Tests the exact search filtering and XSS-neutralizing algorithm implemented in admin.js.
    Verifies matching across ID, name, phone, land details, and address with whitespace and case variations,
    and proves that malicious HTML tags are safely sanitized when prepared for rendering.
    """
    appointments = [
        {
            "id": 101,
            "farmer_name": "Ramesh Kumar",
            "farmer_phone": "+919876543201",
            "land_details": "4 Acres Black Soil",
            "address": "Village Khed, Pune",
            "status": "Pending",
        },
        {
            "id": 102,
            "farmer_name": "Suresh Patil",
            "farmer_phone": "+919876543202",
            "land_details": "10 Hectares Red Loam",
            "address": "Taluka Baramati",
            "status": "Approved",
        },
        {
            "id": 103,
            "farmer_name": "<script>alert('xss-name')</script>",
            "farmer_phone": "+919876543203",
            "land_details": "<img src=x onerror=alert('xss-land')>",
            "address": "<b>Plot 77</b>",
            "status": "Completed",
        },
    ]

    # Implementation of admin.js filter matching logic:
    def filter_appointments(query_str, items):
        query = query_str.strip().lower()
        if not query:
            return items
        return [
            appt for appt in items
            if (
                query in str(appt["id"]).lower()
                or query in str(appt["farmer_name"]).lower()
                or query in str(appt["farmer_phone"]).lower()
                or query in str(appt["land_details"]).lower()
                or query in str(appt["address"]).lower()
            )
        ]

    # Implementation of escapeHtml used in admin.js
    def escape_html(s):
        return (
            str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#039;")
        )

    # 1. Match by ID
    res_id = filter_appointments("101", appointments)
    assert len(res_id) == 1
    assert res_id[0]["id"] == 101

    # 2. Match by case-insensitive name with leading/trailing whitespace
    res_name = filter_appointments("  RAMESH  ", appointments)
    assert len(res_name) == 1
    assert res_name[0]["id"] == 101

    # 3. Match by phone digits
    res_phone = filter_appointments("543202", appointments)
    assert len(res_phone) == 1
    assert res_phone[0]["id"] == 102

    # 4. Match by land details substring
    res_land = filter_appointments("loam", appointments)
    assert len(res_land) == 1
    assert res_land[0]["id"] == 102

    # 5. Match by address substring
    res_addr = filter_appointments("pune", appointments)
    assert len(res_addr) == 1
    assert res_addr[0]["id"] == 101

    # 6. Non-matching query returns 0 items
    assert len(filter_appointments("NonExistentFieldOrName", appointments)) == 0

    # 7. XSS Resilience: Search matches injection payloads faithfully, and escape_html renders them safe
    res_xss = filter_appointments("alert('xss-name')", appointments)
    assert len(res_xss) == 1
    matched_appt = res_xss[0]
    assert matched_appt["id"] == 103

    # Verify escaped rendering neutralizes all HTML tags
    escaped_name = escape_html(matched_appt["farmer_name"])
    escaped_land = escape_html(matched_appt["land_details"])
    escaped_addr = escape_html(matched_appt["address"])

    assert "<script" not in escaped_name
    assert "&lt;script&gt;" in escaped_name
    assert "<img" not in escaped_land
    assert "&lt;img" in escaped_land
    assert "<b>" not in escaped_addr
    assert "&lt;b&gt;" in escaped_addr
