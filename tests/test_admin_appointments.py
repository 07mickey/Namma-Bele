import os
import sys
import tempfile
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
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
        db_path = os.path.join(temp_dir, "test_admin_appts_soil_testing.db")
        app = create_app({
            "TESTING": True,
            "DATABASE": db_path,
            "SECRET_KEY": "test-secret-key-for-admin-appointments",
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


def create_appointment_direct(app, farmer_id, land="2 acres", addr="Field 1", p_date="2026-11-20", p_time="09:00-12:00", notes=None, status="Pending"):
    """Helper to directly insert an appointment."""
    with app.app_context():
        db = get_db()
        cursor = db.execute(
            """
            INSERT INTO appointments (farmer_id, land_details, address, preferred_date, preferred_time, notes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (farmer_id, land, addr, p_date, p_time, notes, status),
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
    # Retrieve fresh CSRF token after session initialization
    return get_csrf(client)


# ============================================================================
# 1. ADMIN LISTING TESTS (GET /api/admin/appointments)
# ============================================================================

def test_admin_list_appointments_empty(client, app):
    """Admin sees empty list when no appointments exist."""
    create_user_direct(app, "Admin One", "+919876543200", role="admin")
    login_user(client, "+919876543200")

    res = client.get("/api/admin/appointments")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["appointments"] == []
    assert data["pagination"]["total_count"] == 0
    assert data["pagination"]["page"] == 1


def test_admin_list_appointments_multiple_farmers(client, app):
    """Admin sees appointments from multiple farmers with joined farmer details."""
    admin_id = create_user_direct(app, "Admin One", "+919876543200", role="admin")
    f1_id = create_user_direct(app, "Farmer Ramesh", "+919876543201", role="farmer")
    f2_id = create_user_direct(app, "Farmer Suresh", "+919876543202", role="farmer")

    appt1 = create_appointment_direct(app, f1_id, land="5 acres paddy", addr="Village 1")
    appt2 = create_appointment_direct(app, f2_id, land="3 acres wheat", addr="Village 2")

    login_user(client, "+919876543200")
    res = client.get("/api/admin/appointments")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["appointments"]) == 2
    assert data["pagination"]["total_count"] == 2

    # Check farmer information is joined and passwords are not present
    for appt in data["appointments"]:
        assert "password_hash" not in appt
        assert "farmer_name" in appt
        assert "farmer_phone" in appt
        if appt["id"] == appt1:
            assert appt["farmer_name"] == "Farmer Ramesh"
            assert appt["farmer_phone"] == "+919876543201"
        elif appt["id"] == appt2:
            assert appt["farmer_name"] == "Farmer Suresh"
            assert appt["farmer_phone"] == "+919876543202"


def test_admin_list_status_filters(client, app):
    """Status filtering returns only appointments matching the requested status."""
    create_user_direct(app, "Admin One", "+919876543200", role="admin")
    f_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")

    create_appointment_direct(app, f_id, status="Pending")
    create_appointment_direct(app, f_id, status="Pending")
    create_appointment_direct(app, f_id, status="Approved")
    create_appointment_direct(app, f_id, status="Rejected")
    create_appointment_direct(app, f_id, status="Completed")

    login_user(client, "+919876543200")

    # Filter Pending
    res_pending = client.get("/api/admin/appointments?status=Pending")
    assert res_pending.status_code == 200
    data = res_pending.get_json()
    assert data["pagination"]["total_count"] == 2
    assert all(a["status"] == "Pending" for a in data["appointments"])

    # Filter Approved
    res_approved = client.get("/api/admin/appointments?status=Approved")
    assert res_approved.status_code == 200
    data = res_approved.get_json()
    assert data["pagination"]["total_count"] == 1
    assert data["appointments"][0]["status"] == "Approved"

    # Filter Rejected
    res_rejected = client.get("/api/admin/appointments?status=Rejected")
    assert res_rejected.status_code == 200
    data = res_rejected.get_json()
    assert data["pagination"]["total_count"] == 1
    assert data["appointments"][0]["status"] == "Rejected"

    # Filter Completed
    res_completed = client.get("/api/admin/appointments?status=Completed")
    assert res_completed.status_code == 200
    data = res_completed.get_json()
    assert data["pagination"]["total_count"] == 1
    assert data["appointments"][0]["status"] == "Completed"


def test_admin_list_invalid_status_filter_returns_400(client, app):
    """Filtering by an unsupported status returns HTTP 400 VALIDATION_ERROR."""
    create_user_direct(app, "Admin One", "+919876543200", role="admin")
    login_user(client, "+919876543200")

    res = client.get("/api/admin/appointments?status=Cancelled")
    assert res.status_code == 400
    data = res.get_json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "Invalid status filter" in data["error"]["message"]


def test_admin_list_deterministic_ordering(client, app):
    """Appointments are ordered by created_at DESC, id DESC."""
    create_user_direct(app, "Admin One", "+919876543200", role="admin")
    f_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")

    id1 = create_appointment_direct(app, f_id, land="Plot 1")
    id2 = create_appointment_direct(app, f_id, land="Plot 2")
    id3 = create_appointment_direct(app, f_id, land="Plot 3")

    login_user(client, "+919876543200")
    res = client.get("/api/admin/appointments")
    assert res.status_code == 200
    ids = [a["id"] for a in res.get_json()["appointments"]]
    assert ids == [id3, id2, id1]


def test_admin_list_pagination(client, app):
    """Pagination splits results correctly across pages."""
    create_user_direct(app, "Admin One", "+919876543200", role="admin")
    f_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")

    for i in range(5):
        create_appointment_direct(app, f_id, land=f"Plot {i}")

    login_user(client, "+919876543200")

    # Page 1 with per_page=2
    res_p1 = client.get("/api/admin/appointments?page=1&per_page=2")
    assert res_p1.status_code == 200
    data_p1 = res_p1.get_json()
    assert len(data_p1["appointments"]) == 2
    assert data_p1["pagination"]["total_count"] == 5
    assert data_p1["pagination"]["total_pages"] == 3
    assert data_p1["pagination"]["page"] == 1
    assert data_p1["pagination"]["per_page"] == 2

    # Page 2 with per_page=2
    res_p2 = client.get("/api/admin/appointments?page=2&per_page=2")
    assert res_p2.status_code == 200
    data_p2 = res_p2.get_json()
    assert len(data_p2["appointments"]) == 2
    assert data_p2["pagination"]["page"] == 2

    # Page 3 with per_page=2 (last item)
    res_p3 = client.get("/api/admin/appointments?page=3&per_page=2")
    assert res_p3.status_code == 200
    data_p3 = res_p3.get_json()
    assert len(data_p3["appointments"]) == 1

    # Ensure items on page 1 and page 2 do not overlap
    p1_ids = {a["id"] for a in data_p1["appointments"]}
    p2_ids = {a["id"] for a in data_p2["appointments"]}
    assert p1_ids.isdisjoint(p2_ids)


def test_admin_list_pagination_invalid_parameters(client, app):
    """Invalid page or per_page values are rejected with HTTP 400."""
    create_user_direct(app, "Admin One", "+919876543200", role="admin")
    login_user(client, "+919876543200")

    # Invalid page
    for invalid_page in ["0", "-1", "abc", ""]:
        res = client.get(f"/api/admin/appointments?page={invalid_page}")
        assert res.status_code == 400
        assert res.get_json()["error"]["code"] == "VALIDATION_ERROR"

    # Invalid per_page
    for invalid_per_page in ["0", "-5", "101", "xyz", ""]:
        res = client.get(f"/api/admin/appointments?per_page={invalid_per_page}")
        assert res.status_code == 400
        assert res.get_json()["error"]["code"] == "VALIDATION_ERROR"


# ============================================================================
# 2. ADMIN APPOINTMENT DETAILS TESTS (GET /api/admin/appointments/<id>)
# ============================================================================

def test_admin_get_appointment_details_success(client, app):
    """Admin retrieves full details of an existing appointment with farmer info."""
    create_user_direct(app, "Admin One", "+919876543200", role="admin")
    f_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, f_id, land="Black soil 4 acres", addr="Plot 10, Mandya", notes="Call first")

    login_user(client, "+919876543200")
    res = client.get(f"/api/admin/appointments/{appt_id}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    appt = data["appointment"]
    assert appt["id"] == appt_id
    assert appt["farmer_name"] == "Farmer Joy"
    assert appt["farmer_phone"] == "+919876543201"
    assert appt["land_details"] == "Black soil 4 acres"
    assert appt["address"] == "Plot 10, Mandya"
    assert appt["notes"] == "Call first"
    assert appt["status"] == "Pending"
    assert "password_hash" not in appt


def test_admin_get_appointment_details_not_found(client, app):
    """Admin receives 404 for non-existent appointment ID."""
    create_user_direct(app, "Admin One", "+919876543200", role="admin")
    login_user(client, "+919876543200")

    res = client.get("/api/admin/appointments/99999")
    assert res.status_code == 404
    data = res.get_json()
    assert data["error"]["code"] == "NOT_FOUND"


# ============================================================================
# 3. STATUS TRANSITION STATE MACHINE TESTS (PATCH /api/admin/appointments/<id>/status)
# ============================================================================

def test_transition_pending_to_approved(client, app):
    """Pending -> Approved is allowed."""
    create_user_direct(app, "Admin One", "+919876543200", role="admin")
    f_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, f_id, status="Pending")

    csrf = login_user(client, "+919876543200")
    res = client.patch(
        f"/api/admin/appointments/{appt_id}/status",
        json={"status": "Approved"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["appointment"]["status"] == "Approved"


def test_transition_pending_to_rejected(client, app):
    """Pending -> Rejected is allowed."""
    create_user_direct(app, "Admin One", "+919876543200", role="admin")
    f_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, f_id, status="Pending")

    csrf = login_user(client, "+919876543200")
    res = client.patch(
        f"/api/admin/appointments/{appt_id}/status",
        json={"status": "Rejected"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["appointment"]["status"] == "Rejected"


def test_transition_approved_to_completed(client, app):
    """Approved -> Completed is allowed."""
    create_user_direct(app, "Admin One", "+919876543200", role="admin")
    f_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, f_id, status="Approved")

    csrf = login_user(client, "+919876543200")
    res = client.patch(
        f"/api/admin/appointments/{appt_id}/status",
        json={"status": "Completed"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["appointment"]["status"] == "Completed"


@pytest.mark.parametrize("initial_status, target_status", [
    ("Pending", "Completed"),     # Cannot skip Approved
    ("Approved", "Rejected"),    # Approved cannot be Rejected
    ("Approved", "Pending"),     # Cannot go backwards to Pending
    ("Rejected", "Approved"),    # Rejected is terminal
    ("Rejected", "Completed"),   # Rejected is terminal
    ("Rejected", "Pending"),     # Rejected is terminal
    ("Completed", "Approved"),   # Completed is terminal
    ("Completed", "Rejected"),   # Completed is terminal
    ("Completed", "Pending"),    # Completed is terminal
])
def test_disallowed_status_transitions_return_409(client, app, initial_status, target_status):
    """Disallowed status transitions return HTTP 409 Conflict."""
    create_user_direct(app, "Admin One", "+919876543200", role="admin")
    f_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, f_id, status=initial_status)

    csrf = login_user(client, "+919876543200")
    res = client.patch(
        f"/api/admin/appointments/{appt_id}/status",
        json={"status": target_status},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 409
    data = res.get_json()
    assert data["error"]["code"] == "CONFLICT"
    assert f"Invalid status transition from '{initial_status}' to '{target_status}'" in data["error"]["message"]


def test_transition_unsupported_status_returns_400(client, app):
    """Submitting an invalid status string returns HTTP 400 VALIDATION_ERROR."""
    create_user_direct(app, "Admin One", "+919876543200", role="admin")
    f_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, f_id, status="Pending")

    csrf = login_user(client, "+919876543200")
    res = client.patch(
        f"/api/admin/appointments/{appt_id}/status",
        json={"status": "Finished"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 400
    assert res.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_transition_missing_or_empty_status_returns_400(client, app):
    """Missing, non-string, or whitespace-only status returns HTTP 400."""
    create_user_direct(app, "Admin One", "+919876543200", role="admin")
    f_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, f_id, status="Pending")

    csrf = login_user(client, "+919876543200")

    # Missing status key
    res1 = client.patch(
        f"/api/admin/appointments/{appt_id}/status",
        json={},
        headers={"X-CSRF-Token": csrf},
    )
    assert res1.status_code == 400

    # Whitespace only
    res2 = client.patch(
        f"/api/admin/appointments/{appt_id}/status",
        json={"status": "   "},
        headers={"X-CSRF-Token": csrf},
    )
    assert res2.status_code == 400

    # Non-string
    res3 = client.patch(
        f"/api/admin/appointments/{appt_id}/status",
        json={"status": 123},
        headers={"X-CSRF-Token": csrf},
    )
    assert res3.status_code == 400


def test_transition_malformed_json_returns_400(client, app):
    """Malformed non-JSON request body returns HTTP 400 MALFORMED_REQUEST."""
    create_user_direct(app, "Admin One", "+919876543200", role="admin")
    f_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, f_id, status="Pending")

    csrf = login_user(client, "+919876543200")
    res = client.patch(
        f"/api/admin/appointments/{appt_id}/status",
        data="not json",
        content_type="application/json",
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 400
    assert res.get_json()["error"]["code"] == "MALFORMED_REQUEST"


def test_transition_nonexistent_appointment_returns_404(client, app):
    """Status update on a non-existent appointment returns HTTP 404."""
    create_user_direct(app, "Admin One", "+919876543200", role="admin")
    csrf = login_user(client, "+919876543200")

    res = client.patch(
        "/api/admin/appointments/88888/status",
        json={"status": "Approved"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 404
    assert res.get_json()["error"]["code"] == "NOT_FOUND"


def test_transition_same_status_is_successful_noop(client, app):
    """Submitting the current status is a successful no-op and preserves updated_at."""
    create_user_direct(app, "Admin One", "+919876543200", role="admin")
    f_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, f_id, status="Pending")

    # Get initial updated_at
    with app.app_context():
        db = get_db()
        initial_row = db.execute("SELECT updated_at FROM appointments WHERE id = ?", (appt_id,)).fetchone()
        initial_updated_at = initial_row["updated_at"]

    csrf = login_user(client, "+919876543200")
    res = client.patch(
        f"/api/admin/appointments/{appt_id}/status",
        json={"status": "Pending"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "already set" in data["message"]
    assert data["appointment"]["status"] == "Pending"
    assert data["appointment"]["updated_at"] == initial_updated_at


def test_transition_updates_updated_at_timestamp(client, app):
    """A real status change updates updated_at explicitly."""
    create_user_direct(app, "Admin One", "+919876543200", role="admin")
    f_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, f_id, status="Pending")

    # Backdate the initial updated_at to verify it changes
    with app.app_context():
        db = get_db()
        db.execute(
            "UPDATE appointments SET updated_at = '2020-01-01 00:00:00' WHERE id = ?",
            (appt_id,),
        )
        db.commit()

    csrf = login_user(client, "+919876543200")
    res = client.patch(
        f"/api/admin/appointments/{appt_id}/status",
        json={"status": "Approved"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    updated_at = res.get_json()["appointment"]["updated_at"]
    assert updated_at != "2020-01-01 00:00:00"


def test_transition_concurrency_safe_conditional_update(client, app):
    """Simulates a race condition where the status changed between read and write."""
    create_user_direct(app, "Admin One", "+919876543200", role="admin")
    f_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, f_id, status="Pending")

    csrf = login_user(client, "+919876543200")

    # If status becomes 'Rejected' concurrently, an attempt expecting 'Pending' detects collision
    with app.app_context():
        db = get_db()
        # Pretend another admin rejected it
        db.execute("UPDATE appointments SET status = 'Rejected' WHERE id = ?", (appt_id,))
        db.commit()

    # Now trying to approve based on stale 'Pending' state will be rejected as 409
    res = client.patch(
        f"/api/admin/appointments/{appt_id}/status",
        json={"status": "Approved"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 409
    assert res.get_json()["error"]["code"] == "CONFLICT"


# ============================================================================
# 4. AUTHORIZATION AND CSRF PROTECTION TESTS
# ============================================================================

def test_unauthenticated_requests_rejected(client, app):
    """Unauthenticated users cannot access any admin appointment endpoints."""
    f_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, f_id, status="Pending")

    res_list = client.get("/api/admin/appointments")
    assert res_list.status_code == 401
    assert res_list.get_json()["error"]["code"] == "UNAUTHENTICATED"

    res_detail = client.get(f"/api/admin/appointments/{appt_id}")
    assert res_detail.status_code == 401
    assert res_detail.get_json()["error"]["code"] == "UNAUTHENTICATED"

    res_patch = client.patch(f"/api/admin/appointments/{appt_id}/status", json={"status": "Approved"})
    # CSRF or unauthenticated rejection:
    assert res_patch.status_code in (401, 403)


def test_farmer_cannot_access_admin_endpoints(client, app):
    """Farmers receive HTTP 403 Forbidden when attempting admin appointment endpoints."""
    f_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, f_id, status="Pending")

    csrf = login_user(client, "+919876543201")

    # 1. Listing
    res_list = client.get("/api/admin/appointments")
    assert res_list.status_code == 403
    assert res_list.get_json()["error"]["code"] == "FORBIDDEN"

    # 2. Detail
    res_detail = client.get(f"/api/admin/appointments/{appt_id}")
    assert res_detail.status_code == 403
    assert res_detail.get_json()["error"]["code"] == "FORBIDDEN"

    # 3. Status update
    res_patch = client.patch(
        f"/api/admin/appointments/{appt_id}/status",
        json={"status": "Approved"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res_patch.status_code == 403
    assert res_patch.get_json()["error"]["code"] == "FORBIDDEN"


def test_admin_patch_status_csrf_protection(client, app):
    """PATCH status requires valid CSRF token."""
    create_user_direct(app, "Admin One", "+919876543200", role="admin")
    f_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    appt_id = create_appointment_direct(app, f_id, status="Pending")

    csrf = login_user(client, "+919876543200")

    # Missing CSRF token
    res_missing = client.patch(
        f"/api/admin/appointments/{appt_id}/status",
        json={"status": "Approved"},
    )
    assert res_missing.status_code == 403
    assert res_missing.get_json()["error"]["code"] == "CSRF_ERROR"

    # Invalid CSRF token
    res_invalid = client.patch(
        f"/api/admin/appointments/{appt_id}/status",
        json={"status": "Approved"},
        headers={"X-CSRF-Token": "invalid-token-value"},
    )
    assert res_invalid.status_code == 403
    assert res_invalid.get_json()["error"]["code"] == "CSRF_ERROR"

    # Valid CSRF token succeeds
    res_valid = client.patch(
        f"/api/admin/appointments/{appt_id}/status",
        json={"status": "Approved"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res_valid.status_code == 200
    assert res_valid.get_json()["appointment"]["status"] == "Approved"


# ============================================================================
# 5. TIMEZONE DATE VALIDATION TEST (Step 8)
# ============================================================================

def test_kolkata_timezone_date_validation(client, app):
    """Verifies that appointment date validation adheres to Asia/Kolkata date."""
    f_id = create_user_direct(app, "Farmer Joy", "+919876543201", role="farmer")
    csrf = login_user(client, "+919876543201")

    kolkata_today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    yesterday_kolkata = (kolkata_today - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow_kolkata = (kolkata_today + timedelta(days=1)).strftime("%Y-%m-%d")

    # Yesterday in Kolkata rejected
    res_past = client.post(
        "/api/appointments",
        json={
            "land_details": "4 acres",
            "address": "Taluk Mandya",
            "preferred_date": yesterday_kolkata,
            "preferred_time": "09:00-12:00",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res_past.status_code == 400
    assert res_past.get_json()["error"]["code"] == "VALIDATION_ERROR"
    assert "past" in res_past.get_json()["error"]["message"]

    # Tomorrow in Kolkata accepted
    res_future = client.post(
        "/api/appointments",
        json={
            "land_details": "4 acres",
            "address": "Taluk Mandya",
            "preferred_date": tomorrow_kolkata,
            "preferred_time": "09:00-12:00",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res_future.status_code == 201
    assert res_future.get_json()["appointment"]["preferred_date"] == tomorrow_kolkata


def test_admin_list_farmers_access(app, client):
    """Verifies that GET /api/admin/farmers returns registered farmers and restricts non-admins."""
    farmer_id = create_user_direct(app, "Ramesh Patil", "+919876543210", "Password123", role="farmer")
    admin_id = create_user_direct(app, "Admin Lead", "+919999999999", "AdminPass123", role="admin")

    # 1. Unauthenticated request rejected
    res_unauth = client.get("/api/admin/farmers")
    assert res_unauth.status_code in (401, 302)

    # 2. Farmer request rejected with 403 Forbidden
    login_user(client, "+919876543210", "Password123")
    res_farmer = client.get("/api/admin/farmers")
    assert res_farmer.status_code == 403

    # 3. Admin request succeeds with 200 OK and list of farmers
    client.post("/api/auth/logout")
    login_user(client, "+919999999999", "AdminPass123")
    res_admin = client.get("/api/admin/farmers")
    assert res_admin.status_code == 200
    data = res_admin.get_json()
    assert data["status"] == "success"
    farmers = data["data"]["farmers"]
    assert len(farmers) >= 1
    assert any(f["phone"] == "+919876543210" for f in farmers)



