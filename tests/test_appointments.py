import os
import sys
import tempfile
from datetime import date, timedelta
import pytest
from werkzeug.security import generate_password_hash

# Ensure the soil-testing-portal directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.db import get_db, init_db


@pytest.fixture
def app_and_db():
    """Creates an isolated test application with a fresh temporary database."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_appts_soil_testing.db")
        app = create_app({
            "TESTING": True,
            "DATABASE": db_path,
            "SECRET_KEY": "test-secret-key-for-appointments",
        })

        with app.app_context():
            init_db()

        yield app, db_path


@pytest.fixture
def app(app_and_db):
    app, _ = app_and_db
    return app


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


def login_user(client, phone, password="Password123"):
    """Helper to authenticate a user and establish session cookies."""
    csrf = get_csrf(client)
    res = client.post(
        "/api/auth/login",
        json={"phone": phone, "password": password},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    return get_csrf(client)


# ============================================================================
# 1. APPOINTMENT CREATION TESTS (POST /api/appointments)
# ============================================================================

def test_create_appointment_success(client, app):
    """Test successful appointment creation with valid fields."""
    farmer_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    csrf = login_user(client, "+919876543201")

    future_date = (date.today() + timedelta(days=5)).isoformat()
    payload = {
        "land_details": "5 acres cotton field, sandy loam soil",
        "address": "Survey No 88, Green Valley, District X",
        "preferred_date": future_date,
        "preferred_time": "09:00-12:00",
        "notes": "Gate is open on east side",
    }

    res = client.post("/api/appointments", json=payload, headers={"X-CSRF-Token": csrf})
    assert res.status_code == 201
    data = res.get_json()
    assert data["status"] == "success"
    assert "appointment" in data

    appt = data["appointment"]
    assert appt["id"] is not None
    assert appt["farmer_id"] == farmer_id
    assert appt["land_details"] == payload["land_details"]
    assert appt["address"] == payload["address"]
    assert appt["preferred_date"] == future_date
    assert appt["preferred_time"] == "09:00-12:00"
    assert appt["notes"] == payload["notes"]
    assert appt["status"] == "Pending"
    assert appt["created_at"] is not None
    assert appt["updated_at"] is not None


def test_create_appointment_status_is_always_pending(client, app):
    """Client cannot override status; status is strictly set to 'Pending'."""
    create_user_direct(app, "Tamper Farmer", "+919876543202", role="farmer")
    csrf = login_user(client, "+919876543202")

    future_date = (date.today() + timedelta(days=2)).isoformat()
    payload = {
        "land_details": "Plot 12",
        "address": "Farm Road 4",
        "preferred_date": future_date,
        "preferred_time": "14:00-17:00",
        "status": "Approved",  # Attempting to self-approve
    }

    res = client.post("/api/appointments", json=payload, headers={"X-CSRF-Token": csrf})
    assert res.status_code == 201
    assert res.get_json()["appointment"]["status"] == "Pending"

    with app.app_context():
        row = get_db().execute("SELECT status FROM appointments WHERE id = ?", (res.get_json()["appointment"]["id"],)).fetchone()
        assert row["status"] == "Pending"


def test_create_appointment_farmer_id_cannot_be_spoofed(client, app):
    """Client cannot set farmer_id to another user; server assigns authenticated ID."""
    real_farmer = create_user_direct(app, "Real Farmer", "+919876543203", role="farmer")
    other_user = create_user_direct(app, "Victim Farmer", "+919876543204", role="farmer")

    csrf = login_user(client, "+919876543203")

    future_date = (date.today() + timedelta(days=3)).isoformat()
    payload = {
        "farmer_id": other_user,  # Client tries to attribute booking to victim
        "land_details": "Plot 99",
        "address": "North Sector",
        "preferred_date": future_date,
        "preferred_time": "09:00-12:00",
    }

    res = client.post("/api/appointments", json=payload, headers={"X-CSRF-Token": csrf})
    assert res.status_code == 201
    appt = res.get_json()["appointment"]
    # Must be real_farmer, NOT other_user
    assert appt["farmer_id"] == real_farmer
    assert appt["farmer_id"] != other_user


def test_create_appointment_missing_required_fields(client, app):
    """Missing land_details or address returns HTTP 400 VALIDATION_ERROR."""
    create_user_direct(app, "Incomplete Farmer", "+919876543205", role="farmer")
    csrf = login_user(client, "+919876543205")
    future_date = (date.today() + timedelta(days=4)).isoformat()

    # Missing land_details
    res1 = client.post(
        "/api/appointments",
        json={"address": "Village", "preferred_date": future_date, "preferred_time": "09:00-12:00"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res1.status_code == 400
    assert res1.get_json()["error"]["code"] == "VALIDATION_ERROR"

    # Missing address
    res2 = client.post(
        "/api/appointments",
        json={"land_details": "2 acres", "preferred_date": future_date, "preferred_time": "09:00-12:00"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res2.status_code == 400
    assert res2.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_appointment_whitespace_only_fields_rejected(client, app):
    """Whitespace-only fields are rejected."""
    create_user_direct(app, "Whitespace Farmer", "+919876543206", role="farmer")
    csrf = login_user(client, "+919876543206")
    future_date = (date.today() + timedelta(days=4)).isoformat()

    res = client.post(
        "/api/appointments",
        json={"land_details": "   ", "address": "   ", "preferred_date": future_date, "preferred_time": "09:00-12:00"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 400
    assert res.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_appointment_excessive_lengths_rejected(client, app):
    """Fields exceeding maximum length constraints are rejected."""
    create_user_direct(app, "LongText Farmer", "+919876543207", role="farmer")
    csrf = login_user(client, "+919876543207")
    future_date = (date.today() + timedelta(days=4)).isoformat()

    # land_details > 500 chars
    res1 = client.post(
        "/api/appointments",
        json={"land_details": "A" * 501, "address": "Village", "preferred_date": future_date, "preferred_time": "09:00-12:00"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res1.status_code == 400
    assert "cannot exceed" in res1.get_json()["error"]["message"]

    # notes > 1000 chars
    res2 = client.post(
        "/api/appointments",
        json={"land_details": "Valid", "address": "Valid", "preferred_date": future_date, "preferred_time": "09:00-12:00", "notes": "B" * 1001},
        headers={"X-CSRF-Token": csrf},
    )
    assert res2.status_code == 400


def test_create_appointment_date_validations(client, app):
    """Tests date validation: bad format, impossible date, past date, today date."""
    create_user_direct(app, "Date Farmer", "+919876543208", role="farmer")
    csrf = login_user(client, "+919876543208")

    # Invalid format (DD-MM-YYYY)
    res_fmt = client.post(
        "/api/appointments",
        json={"land_details": "Land", "address": "Address", "preferred_date": "15-11-2026", "preferred_time": "09:00-12:00"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res_fmt.status_code == 400
    assert "exact YYYY-MM-DD" in res_fmt.get_json()["error"]["message"]

    # Impossible date (February 30)
    res_imp = client.post(
        "/api/appointments",
        json={"land_details": "Land", "address": "Address", "preferred_date": "2027-02-30", "preferred_time": "09:00-12:00"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res_imp.status_code == 400
    assert "valid calendar date" in res_imp.get_json()["error"]["message"]

    # Past date
    past_date = (date.today() - timedelta(days=1)).isoformat()
    res_past = client.post(
        "/api/appointments",
        json={"land_details": "Land", "address": "Address", "preferred_date": past_date, "preferred_time": "09:00-12:00"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res_past.status_code == 400
    assert "cannot be in the past" in res_past.get_json()["error"]["message"]

    # Valid today date is accepted
    today_date = date.today().isoformat()
    res_today = client.post(
        "/api/appointments",
        json={"land_details": "Land", "address": "Address", "preferred_date": today_date, "preferred_time": "09:00-12:00"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res_today.status_code == 201


def test_create_appointment_time_slots(client, app):
    """Only '09:00-12:00' and '14:00-17:00' are accepted."""
    create_user_direct(app, "Time Farmer", "+919876543209", role="farmer")
    csrf = login_user(client, "+919876543209")
    future_date = (date.today() + timedelta(days=1)).isoformat()

    # Valid afternoon slot
    res_pm = client.post(
        "/api/appointments",
        json={"land_details": "Land", "address": "Address", "preferred_date": future_date, "preferred_time": "14:00-17:00"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res_pm.status_code == 201
    assert res_pm.get_json()["appointment"]["preferred_time"] == "14:00-17:00"

    # Invalid time slot
    res_inv = client.post(
        "/api/appointments",
        json={"land_details": "Land", "address": "Address", "preferred_date": future_date, "preferred_time": "10:00-11:00"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res_inv.status_code == 400
    assert "Preferred time slot must be either" in res_inv.get_json()["error"]["message"]


def test_create_appointment_optional_notes(client, app):
    """Notes can be omitted or null."""
    create_user_direct(app, "Notes Farmer", "+919876543210", role="farmer")
    csrf = login_user(client, "+919876543210")
    future_date = (date.today() + timedelta(days=2)).isoformat()

    # Omitted notes
    res1 = client.post(
        "/api/appointments",
        json={"land_details": "Land", "address": "Address", "preferred_date": future_date, "preferred_time": "09:00-12:00"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res1.status_code == 201
    assert res1.get_json()["appointment"]["notes"] is None

    # Null notes
    res2 = client.post(
        "/api/appointments",
        json={"land_details": "Land", "address": "Address", "preferred_date": future_date, "preferred_time": "09:00-12:00", "notes": None},
        headers={"X-CSRF-Token": csrf},
    )
    assert res2.status_code == 201
    assert res2.get_json()["appointment"]["notes"] is None


def test_create_appointment_csrf_enforced(client, app):
    """POST /api/appointments without CSRF header is rejected with 403."""
    create_user_direct(app, "CSRF Appt Farmer", "+919876543211", role="farmer")
    login_user(client, "+919876543211")
    future_date = (date.today() + timedelta(days=2)).isoformat()

    res = client.post(
        "/api/appointments",
        json={"land_details": "Land", "address": "Address", "preferred_date": future_date, "preferred_time": "09:00-12:00"},
    )
    assert res.status_code == 403
    assert res.get_json()["error"]["code"] == "CSRF_ERROR"


# ============================================================================
# 2. RBAC & AUTHORIZATION TESTS
# ============================================================================

def test_unauthenticated_requests_rejected(client):
    """Unauthenticated requests to appointment routes return HTTP 401."""
    assert client.get("/api/appointments").status_code == 401
    assert client.get("/api/appointments/1").status_code == 401
    # POST without session fails auth/csrf with 401 or 403
    csrf = get_csrf(client)
    res_post = client.post(
        "/api/appointments",
        json={"land_details": "L", "address": "A", "preferred_date": "2026-11-15", "preferred_time": "09:00-12:00"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res_post.status_code == 401


def test_admin_cannot_use_farmer_appointment_endpoints(client, app):
    """Admin users are forbidden from creating or accessing farmer appointment routes (HTTP 403)."""
    create_user_direct(app, "Admin User", "+919876543212", role="admin")
    csrf = login_user(client, "+919876543212")
    future_date = (date.today() + timedelta(days=3)).isoformat()

    # Admin cannot POST /api/appointments
    res_post = client.post(
        "/api/appointments",
        json={"land_details": "Land", "address": "Address", "preferred_date": future_date, "preferred_time": "09:00-12:00"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res_post.status_code == 403
    assert res_post.get_json()["error"]["code"] == "FORBIDDEN"

    # Admin cannot GET /api/appointments (farmer view)
    assert client.get("/api/appointments").status_code == 403
    assert client.get("/api/appointments/1").status_code == 403


# ============================================================================
# 3. LIST APPOINTMENTS TESTS (GET /api/appointments)
# ============================================================================

def test_list_appointments_empty(client, app):
    """Farmer with zero appointments receives an empty list."""
    create_user_direct(app, "Empty Farmer", "+919876543213", role="farmer")
    login_user(client, "+919876543213")

    res = client.get("/api/appointments")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["appointments"] == []


def test_list_appointments_returns_only_own_appointments(client, app):
    """Farmer sees only their own appointments, never another farmer's."""
    farmer_a = create_user_direct(app, "Farmer A", "+919876543214", role="farmer")
    farmer_b = create_user_direct(app, "Farmer B", "+919876543215", role="farmer")

    # Farmer A creates 2 appointments
    csrf_a = login_user(client, "+919876543214")
    future_date = (date.today() + timedelta(days=5)).isoformat()

    client.post(
        "/api/appointments",
        json={"land_details": "Plot A1", "address": "Address A1", "preferred_date": future_date, "preferred_time": "09:00-12:00"},
        headers={"X-CSRF-Token": csrf_a},
    )
    client.post(
        "/api/appointments",
        json={"land_details": "Plot A2", "address": "Address A2", "preferred_date": future_date, "preferred_time": "14:00-17:00"},
        headers={"X-CSRF-Token": csrf_a},
    )

    # Farmer A lists appointments
    res_a = client.get("/api/appointments")
    assert res_a.status_code == 200
    appts_a = res_a.get_json()["appointments"]
    assert len(appts_a) == 2
    assert all(a["farmer_id"] == farmer_a for a in appts_a)

    # Farmer B logs in
    csrf_b = login_user(client, "+919876543215")
    # Farmer B creates 1 appointment
    client.post(
        "/api/appointments",
        json={"land_details": "Plot B1", "address": "Address B1", "preferred_date": future_date, "preferred_time": "09:00-12:00"},
        headers={"X-CSRF-Token": csrf_b},
    )

    # Farmer B lists appointments
    res_b = client.get("/api/appointments")
    assert res_b.status_code == 200
    appts_b = res_b.get_json()["appointments"]
    assert len(appts_b) == 1
    assert appts_b[0]["farmer_id"] == farmer_b
    assert appts_b[0]["land_details"] == "Plot B1"

    # Query param tampering (e.g. ?farmer_id=...) must be completely ignored
    res_tamper = client.get(f"/api/appointments?farmer_id={farmer_a}")
    assert res_tamper.status_code == 200
    assert len(res_tamper.get_json()["appointments"]) == 1
    assert res_tamper.get_json()["appointments"][0]["farmer_id"] == farmer_b


# ============================================================================
# 4. SINGLE APPOINTMENT & IDOR PROTECTION (GET /api/appointments/<id>)
# ============================================================================

def test_view_own_appointment_success(client, app):
    """Farmer can retrieve details of an appointment they own."""
    create_user_direct(app, "Detail Farmer", "+919876543216", role="farmer")
    csrf = login_user(client, "+919876543216")
    future_date = (date.today() + timedelta(days=4)).isoformat()

    create_res = client.post(
        "/api/appointments",
        json={"land_details": "Plot Detail", "address": "Farm Lane", "preferred_date": future_date, "preferred_time": "09:00-12:00"},
        headers={"X-CSRF-Token": csrf},
    )
    appt_id = create_res.get_json()["appointment"]["id"]

    res = client.get(f"/api/appointments/{appt_id}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["appointment"]["id"] == appt_id
    assert data["appointment"]["land_details"] == "Plot Detail"


def test_idor_farmer_cannot_view_another_farmers_appointment(client, app):
    """
    IDOR / Horizontal Privilege Escalation Test:
    Farmer B attempts to view Farmer A's appointment by passing Farmer A's ID.
    Must return HTTP 404 Not Found to prevent data leakage and ID enumeration.
    """
    create_user_direct(app, "Farmer Victim", "+919876543217", role="farmer")
    create_user_direct(app, "Farmer Attacker", "+919876543218", role="farmer")

    # Farmer Victim creates an appointment
    csrf_victim = login_user(client, "+919876543217")
    future_date = (date.today() + timedelta(days=6)).isoformat()
    res_victim = client.post(
        "/api/appointments",
        json={"land_details": "Victim's Secret Land", "address": "Confidential Road", "preferred_date": future_date, "preferred_time": "09:00-12:00"},
        headers={"X-CSRF-Token": csrf_victim},
    )
    victim_appt_id = res_victim.get_json()["appointment"]["id"]

    # Farmer Attacker logs in
    login_user(client, "+919876543218")

    # Farmer Attacker attempts to GET victim's appointment
    res_attack = client.get(f"/api/appointments/{victim_appt_id}")
    assert res_attack.status_code == 404
    assert res_attack.get_json()["error"]["code"] == "NOT_FOUND"
    assert "not found" in res_attack.get_json()["error"]["message"].lower()


def test_view_nonexistent_appointment_returns_404(client, app):
    """Non-existent appointment ID returns HTTP 404 Not Found."""
    create_user_direct(app, "Lookup Farmer", "+919876543219", role="farmer")
    login_user(client, "+919876543219")

    res = client.get("/api/appointments/999999")
    assert res.status_code == 404
    assert res.get_json()["error"]["code"] == "NOT_FOUND"


def test_no_unauthorized_modification_endpoint_exists(client, app):
    """Farmers cannot modify appointments or change status (status PATCH does not exist)."""
    create_user_direct(app, "Modify Farmer", "+919876543220", role="farmer")
    csrf = login_user(client, "+919876543220")
    future_date = (date.today() + timedelta(days=3)).isoformat()

    create_res = client.post(
        "/api/appointments",
        json={"land_details": "Plot A", "address": "Address A", "preferred_date": future_date, "preferred_time": "09:00-12:00"},
        headers={"X-CSRF-Token": csrf},
    )
    appt_id = create_res.get_json()["appointment"]["id"]

    # Any PATCH or PUT should return 404 or 405 Method Not Allowed
    res_patch = client.patch(f"/api/appointments/{appt_id}", json={"status": "Approved"}, headers={"X-CSRF-Token": csrf})
    assert res_patch.status_code in (404, 405)

    res_put = client.put(f"/api/appointments/{appt_id}", json={"status": "Completed"}, headers={"X-CSRF-Token": csrf})
    assert res_put.status_code in (404, 405)

