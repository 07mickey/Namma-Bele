"""
Test suite for the Demo Login Accounts and Safe Demo Environment.
Verifies all 6 roles, credential security, role isolation, and database separation.
"""
import os
import sqlite3
import tempfile
import pytest
from app import create_app
from app.db import init_db, get_db
from scripts.seed_demo_accounts import seed_demo_accounts, DEMO_ACCOUNTS, DEMO_PASSWORD


@pytest.fixture
def demo_app_and_client():
    with tempfile.TemporaryDirectory() as temp_dir:
        prod_db_path = os.path.join(temp_dir, "soil_testing.db")
        demo_db_path = os.path.join(temp_dir, "demo_soil_testing.db")
        reports_dir = os.path.join(temp_dir, "demo_reports")
        os.makedirs(reports_dir, exist_ok=True)

        # 1. Initialize empty prod DB with 1 user
        prod_app = create_app({
            "TESTING": True,
            "DATABASE": prod_db_path,
            "DEMO_MODE": False,
            "SECRET_KEY": "prod-secret-test",
        })
        with prod_app.app_context():
            init_db()
            db = get_db()
            from werkzeug.security import generate_password_hash
            db.execute(
                "INSERT INTO users (name, phone, password_hash, role) VALUES (?, ?, ?, ?)",
                ("Real Prod Farmer", "+919876543210", generate_password_hash("ProdPass123!"), "farmer")
            )
            db.commit()

        # 2. Initialize demo DB and seed demo accounts
        demo_app = create_app({
            "TESTING": True,
            "DATABASE": demo_db_path,
            "REPORT_FOLDER": reports_dir,
            "DEMO_MODE": True,
            "SECRET_KEY": "demo-secret-test",
        })
        with demo_app.app_context():
            init_db()
            seed_demo_accounts(db_path=demo_db_path)

        yield demo_app, demo_app.test_client(), prod_db_path, demo_db_path


def get_csrf(client):
    res = client.get("/api/auth/csrf-token")
    return res.get_json()["csrf_token"]


def test_demo_accounts_stored_exclusively_in_demo_db(demo_app_and_client):
    """Verify demo accounts exist strictly in demo DB, leaving prod DB untouched."""
    _, _, prod_db, demo_db = demo_app_and_client

    # Check Prod DB
    p_conn = sqlite3.connect(prod_db)
    prod_users = p_conn.execute("SELECT phone FROM users").fetchall()
    p_conn.close()
    assert len(prod_users) == 1
    assert prod_users[0][0] == "+919876543210"

    # Check Demo DB
    d_conn = sqlite3.connect(demo_db)
    demo_users = d_conn.execute("SELECT phone, role FROM users").fetchall()
    d_conn.close()
    assert len(demo_users) >= 6
    demo_phones = [u[0] for u in demo_users]
    for acc in DEMO_ACCOUNTS:
        assert acc["phone"] in demo_phones


def test_seed_demo_accounts_is_idempotent(demo_app_and_client):
    """Re-running seeding must refresh without duplicate creation."""
    _, _, _, demo_db = demo_app_and_client
    seed_demo_accounts(db_path=demo_db)
    seed_demo_accounts(db_path=demo_db)

    d_conn = sqlite3.connect(demo_db)
    count = d_conn.execute("SELECT count(*) FROM users").fetchone()[0]
    d_conn.close()
    assert count == len(DEMO_ACCOUNTS)


def test_login_success_for_all_six_roles(demo_app_and_client):
    """Verify every one of the 6 application roles can authenticate cleanly."""
    _, client, _, _ = demo_app_and_client
    csrf = get_csrf(client)

    role_destinations = {
        "farmer": "/dashboard.html",
        "admin": "/admin-dashboard.html",
        "operator": "/operator",
        "field_worker": "/field-worker",
        "lab_staff": "/lab",
        "advisor": "/advisor",
    }

    for acc in DEMO_ACCOUNTS:
        csrf = get_csrf(client)
        # 1. Login with correct password
        login_res = client.post("/api/auth/login", json={
            "phone": acc["phone"],
            "password": DEMO_PASSWORD
        }, headers={"X-CSRF-Token": csrf})
        assert login_res.status_code == 200, f"Login failed for {acc['role']} ({acc['phone']})"
        data = login_res.get_json()
        assert data["status"] == "success"
        assert data["user"]["role"] == acc["role"]

        # 2. Verify redirect / access to appropriate dashboard
        expected_route = role_destinations[acc["role"]]
        dash_res = client.get(expected_route)
        assert dash_res.status_code == 200, f"Dashboard {expected_route} unreachable for {acc['role']}"

        # Logout with fresh CSRF token
        fresh_csrf = get_csrf(client)
        client.post("/api/auth/logout", headers={"X-CSRF-Token": fresh_csrf})


def test_incorrect_password_rejected(demo_app_and_client):
    """Verify invalid password returns HTTP 401."""
    _, client, _, _ = demo_app_and_client
    csrf = get_csrf(client)

    login_res = client.post("/api/auth/login", json={
        "phone": "+919999000008",
        "password": "WrongPassword123!"
    }, headers={"X-CSRF-Token": csrf})
    assert login_res.status_code == 401


def test_unauthorized_role_access_rejected(demo_app_and_client):
    """Verify a farmer account cannot access admin or staff endpoints."""
    _, client, _, _ = demo_app_and_client
    csrf = get_csrf(client)

    # Login as Farmer
    client.post("/api/auth/login", json={
        "phone": "+919999000001",
        "password": DEMO_PASSWORD
    }, headers={"X-CSRF-Token": csrf})

    # Access admin appointments API -> 403 Forbidden
    admin_api = client.get("/api/admin/appointments")
    assert admin_api.status_code == 403

    # Access operator API -> 403 Forbidden
    op_api = client.get("/api/operator/audit-logs")
    assert op_api.status_code == 403


def test_demo_accounts_ui_displayed_only_when_demo_mode_active(demo_app_and_client):
    """Verify Demo Accounts section renders when DEMO_MODE=True and is hidden when False."""
    demo_app, client, _, _ = demo_app_and_client

    # When DEMO_MODE=True
    res = client.get("/login")
    assert res.status_code == 200
    assert "Explore NAMMA BELE — Demo Access" in res.data.decode("utf-8")
    assert "+919999000001" in res.data.decode("utf-8")

    # When DEMO_MODE=False
    prod_app = create_app({"TESTING": True, "DEMO_MODE": False, "SECRET_KEY": "test-key-prod"})
    with prod_app.test_client() as prod_client:
        prod_res = prod_client.get("/login")
        assert prod_res.status_code == 200
        assert "Explore NAMMA BELE — Demo Access" not in prod_res.data.decode("utf-8")
