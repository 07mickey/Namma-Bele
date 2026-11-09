import os
import sys
import tempfile
import pytest
from werkzeug.security import generate_password_hash, check_password_hash

# Ensure soil-testing-portal directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.db import get_db, init_db


@pytest.fixture
def app_and_db():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_staff_foundation.db")
        app = create_app({
            "TESTING": True,
            "DATABASE": db_path,
            "SECRET_KEY": "test-staff-key",
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


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


def get_csrf(client):
    res = client.get("/api/auth/csrf-token")
    assert res.status_code == 200
    return res.get_json()["csrf_token"]


def create_user_direct(app, name, phone, password="Password123", role="farmer", account_status="ACTIVE"):
    with app.app_context():
        db = get_db()
        cur = db.execute(
            """
            INSERT INTO users (name, phone, password_hash, role, account_status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, phone, generate_password_hash(password), role, account_status),
        )
        db.commit()
        return cur.lastrowid


def login_user(client, phone, password="Password123"):
    csrf = get_csrf(client)
    res = client.post(
        "/api/auth/login",
        json={"phone": phone, "password": password},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    return get_csrf(client)


# ============================================================================
# 1. CLI STAFF PROVISIONING TESTS (flask init-staff)
# ============================================================================

def test_init_staff_cli_success_all_roles(runner, app):
    """Test provisioning staff accounts for operator, field_worker, lab_staff, advisor."""
    roles = [
        ("Operator Ramesh", "+919876543101", "operator"),
        ("Field Tech Suresh", "+919876543102", "field_worker"),
        ("Lab Analyst Priya", "+919876543103", "lab_staff"),
        ("Agri Expert Dr. Rao", "+919876543104", "advisor"),
    ]

    for name, phone, role in roles:
        res = runner.invoke(
            args=["init-staff", "--name", name, "--phone", phone, "--role", role],
            input="StaffPassword123\nStaffPassword123\n",
        )
        assert res.exit_code == 0
        assert f"Staff account created successfully" in res.output

    with app.app_context():
        db = get_db()
        for name, phone, role in roles:
            user = db.execute("SELECT * FROM users WHERE phone = ?", (phone,)).fetchone()
            assert user is not None
            assert user["name"] == name
            assert user["role"] == role
            assert user["account_status"] == "ACTIVE"
            assert check_password_hash(user["password_hash"], "StaffPassword123")


def test_init_staff_cli_rejects_invalid_role(runner):
    """CLI rejects invalid role."""
    res = runner.invoke(
        args=["init-staff", "--name", "Bad Role", "--phone", "+919876543105", "--role", "hacker"],
        input="StaffPassword123\nStaffPassword123\n",
    )
    assert res.exit_code != 0
    assert "Invalid staff role" in res.output


# ============================================================================
# 2. RBAC TEST-ONLY ROUTE CHECKS
# ============================================================================

def test_staff_role_access_boundaries(client, app):
    """Verify authorization checks strictly isolate roles."""
    create_user_direct(app, "Farmer Joy", "+919876543110", role="farmer")
    create_user_direct(app, "Operator One", "+919876543111", role="operator")
    create_user_direct(app, "Field Tech One", "+919876543112", role="field_worker")
    create_user_direct(app, "Lab Analyst One", "+919876543113", role="lab_staff")
    create_user_direct(app, "Advisor One", "+919876543114", role="advisor")
    create_user_direct(app, "Admin One", "+919876543115", role="admin")

    # Farmer cannot access staff endpoints
    login_user(client, "+919876543110")
    assert client.get("/api/test/operator-only").status_code == 403
    assert client.get("/api/test/field-worker-only").status_code == 403
    assert client.get("/api/test/lab-staff-only").status_code == 403
    assert client.get("/api/test/advisor-only").status_code == 403
    assert client.get("/api/test/admin-only").status_code == 403
    assert client.get("/api/test/farmer-only").status_code == 200

    # Operator can access operator-only and staff-only
    login_user(client, "+919876543111")
    assert client.get("/api/test/operator-only").status_code == 200
    assert client.get("/api/test/staff-only").status_code == 200
    assert client.get("/api/test/field-worker-only").status_code == 403
    assert client.get("/api/test/farmer-only").status_code == 403

    # Admin has access to all staff test routes
    login_user(client, "+919876543115")
    assert client.get("/api/test/operator-only").status_code == 200
    assert client.get("/api/test/field-worker-only").status_code == 200
    assert client.get("/api/test/lab-staff-only").status_code == 200
    assert client.get("/api/test/advisor-only").status_code == 200
    assert client.get("/api/test/admin-only").status_code == 200


# ============================================================================
# 3. ASSISTED REGISTRATION & ACTIVATION (CLAIM) TESTS
# ============================================================================

def test_assisted_registration_and_account_claim(client, app):
    """
    1. Operator creates assisted farmer account (account_status='UNCLAIMED').
    2. Web login fails with HTTP 403 ACCOUNT_UNCLAIMED.
    3. Farmer initiates claim flow, receives OTP.
    4. Farmer verifies OTP and sets new password.
    5. Farmer can now log into web dashboard!
    """
    create_user_direct(app, "Service Operator", "+919876543120", role="operator")
    csrf = login_user(client, "+919876543120")

    # 1. Operator registers assisted farmer
    assisted_payload = {
        "name": "Basavaraj Gowda",
        "phone": "+919876543121",
        "preferred_language": "kn",
        "address": {
            "recipient_name": "Basavaraj Gowda",
            "house_details": "House No 45, Near Temple",
            "street_or_village": "Maddur Hobli",
            "taluk": "Maddur",
            "district": "Mandya",
            "pincode": "571428",
        },
        "plot": {
            "plot_name": "North Field",
            "survey_number": "SY-104/A",
            "area": 3.5,
            "area_unit": "Acres",
        }
    }
    res_reg = client.post("/api/operator/farmers", json=assisted_payload, headers={"X-CSRF-Token": csrf})
    assert res_reg.status_code == 201
    data_reg = res_reg.get_json()
    farmer_id = data_reg["farmer"]["id"]
    assert data_reg["farmer"]["account_status"] == "UNCLAIMED"

    # Logout operator
    client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})

    # 2. Attempting web login with dummy password fails with ACCOUNT_UNCLAIMED
    csrf_anon = get_csrf(client)
    res_fail_login = client.post(
        "/api/auth/login",
        json={"phone": "+919876543121", "password": "Password123"},
        headers={"X-CSRF-Token": csrf_anon},
    )
    assert res_fail_login.status_code == 403
    assert res_fail_login.get_json()["error"]["code"] == "ACCOUNT_UNCLAIMED"

    # 3. Initiate account claim
    res_initiate = client.post(
        "/api/auth/claim/initiate",
        json={"phone": "+919876543121"},
        headers={"X-CSRF-Token": csrf_anon},
    )
    assert res_initiate.status_code == 200
    data_claim = res_initiate.get_json()
    claim_token = data_claim["claim_token"]
    otp = data_claim["otp_preview"]  # Available in TESTING mode

    # 4. Complete claim with OTP and new password
    res_complete = client.post(
        "/api/auth/claim/complete",
        json={
            "phone": "+919876543121",
            "claim_token": claim_token,
            "otp": otp,
            "password": "FarmerNewPassword123",
        },
        headers={"X-CSRF-Token": csrf_anon},
    )
    assert res_complete.status_code == 200
    assert "activated successfully" in res_complete.get_json()["message"]

    # 5. Farmer can now log into web portal!
    csrf_fresh = get_csrf(client)
    res_login_success = client.post(
        "/api/auth/login",
        json={"phone": "+919876543121", "password": "FarmerNewPassword123"},
        headers={"X-CSRF-Token": csrf_fresh},
    )
    assert res_login_success.status_code == 200
    assert res_login_success.get_json()["user"]["name"] == "Basavaraj Gowda"


# ============================================================================
# 4. DELIVERY ADDRESSES CRUD TESTS
# ============================================================================

def test_delivery_addresses_management(client, app):
    """Test farmer postal delivery address creation, default toggling, and deletion."""
    farmer_id = create_user_direct(app, "Farmer Address Test", "+919876543130", role="farmer")
    csrf = login_user(client, "+919876543130")

    # 1. Add first address (should auto-become default)
    addr1_payload = {
        "recipient_name": "Farmer Address Test",
        "recipient_phone": "+919876543130",
        "house_details": "Plot 12, Agro Layout",
        "street_or_village": "Hunsur Road",
        "taluk": "Mysuru",
        "district": "Mysuru",
        "pincode": "570001",
    }
    res1 = client.post(f"/api/farmers/{farmer_id}/delivery-addresses", json=addr1_payload, headers={"X-CSRF-Token": csrf})
    assert res1.status_code == 201
    addr1_id = res1.get_json()["address"]["id"]
    assert res1.get_json()["address"]["is_default"] == 1

    # 2. Add second address (non-default)
    addr2_payload = {
        "recipient_name": "Farmer Brother",
        "recipient_phone": "+919876543131",
        "house_details": "Farm House #2",
        "street_or_village": "K.R. Pet Village",
        "taluk": "K.R. Pet",
        "district": "Mandya",
        "pincode": "571426",
        "is_default": False,
    }
    res2 = client.post(f"/api/farmers/{farmer_id}/delivery-addresses", json=addr2_payload, headers={"X-CSRF-Token": csrf})
    assert res2.status_code == 201
    addr2_id = res2.get_json()["address"]["id"]
    assert res2.get_json()["address"]["is_default"] == 0

    # 3. List addresses
    res_list = client.get(f"/api/farmers/{farmer_id}/delivery-addresses")
    assert res_list.status_code == 200
    addresses = res_list.get_json()["addresses"]
    assert len(addresses) == 2

    # 4. Set second address as default
    res_def = client.put(f"/api/farmers/{farmer_id}/delivery-addresses/{addr2_id}/default", headers={"X-CSRF-Token": csrf})
    assert res_def.status_code == 200

    # Verify default switched
    res_list_after = client.get(f"/api/farmers/{farmer_id}/delivery-addresses")
    addrs_after = {a["id"]: a["is_default"] for a in res_list_after.get_json()["addresses"]}
    assert addrs_after[addr2_id] == 1
    assert addrs_after[addr1_id] == 0

    # 5. Delete address
    res_del = client.delete(f"/api/farmers/{farmer_id}/delivery-addresses/{addr1_id}", headers={"X-CSRF-Token": csrf})
    assert res_del.status_code == 200
    res_list_final = client.get(f"/api/farmers/{farmer_id}/delivery-addresses")
    assert len(res_list_final.get_json()["addresses"]) == 1

