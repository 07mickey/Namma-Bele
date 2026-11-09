import os
import sys
import tempfile
import pytest
from werkzeug.security import generate_password_hash, check_password_hash

# Ensure the soil-testing-portal directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.db import get_db, init_db


@pytest.fixture
def app_and_db():
    """
    Creates and configures an isolated Flask test application
    with a fresh, dedicated temporary database file.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_auth_soil_testing.db")
        app = create_app({
            "TESTING": True,
            "DATABASE": db_path,
            "SECRET_KEY": "test-secret-key-for-auth",
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
    """Helper to fetch a fresh CSRF token from the server."""
    res = client.get("/api/auth/csrf-token")
    assert res.status_code == 200
    data = res.get_json()
    assert "csrf_token" in data
    return data["csrf_token"]


def create_user_direct(app, name, phone, password, role="farmer"):
    """Helper to directly insert a user with a hashed password."""
    with app.app_context():
        db = get_db()
        cursor = db.execute(
            "INSERT INTO users (name, phone, password_hash, role) VALUES (?, ?, ?, ?)",
            (name, phone, generate_password_hash(password), role),
        )
        db.commit()
        return cursor.lastrowid


# ============================================================================
# 1. CSRF PROTECTION TESTS
# ============================================================================

def test_csrf_missing_token_on_post_rejected(client):
    """State-changing POST request without CSRF token must return HTTP 403."""
    res = client.post("/api/auth/register", json={
        "name": "No CSRF Farmer",
        "phone": "+919876543210",
        "password": "Password123",
    })
    assert res.status_code == 403
    data = res.get_json()
    assert data["error"]["code"] == "CSRF_ERROR"


def test_csrf_invalid_token_rejected(client):
    """State-changing POST request with invalid CSRF token must return HTTP 403."""
    # Establish session
    get_csrf(client)
    res = client.post(
        "/api/auth/register",
        json={
            "name": "Invalid CSRF Farmer",
            "phone": "+919876543210",
            "password": "Password123",
        },
        headers={"X-CSRF-Token": "completely-invalid-token"},
    )
    assert res.status_code == 403
    data = res.get_json()
    assert data["error"]["code"] == "CSRF_ERROR"


def test_csrf_safe_get_requests_usable_without_token(client):
    """Safe GET requests do not require a CSRF token."""
    res = client.get("/api/auth/me")
    assert res.status_code == 200
    assert res.get_json()["authenticated"] is False


# ============================================================================
# 2. REGISTRATION TESTS (POST /api/auth/register)
# ============================================================================

def test_register_farmer_success(client, app):
    """Test successful registration of a farmer account."""
    csrf = get_csrf(client)
    res = client.post(
        "/api/auth/register",
        json={
            "name": "Ramesh Patel",
            "phone": "+919876543210",
            "password": "ValidPassword123",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 201
    data = res.get_json()
    assert data["status"] == "success"
    assert data["user"]["name"] == "Ramesh Patel"
    assert data["user"]["phone"] == "+919876543210"
    assert data["user"]["role"] == "farmer"
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]

    # Verify database state: password is NOT plaintext
    with app.app_context():
        user = get_db().execute("SELECT * FROM users WHERE phone = ?", ("+919876543210",)).fetchone()
        assert user is not None
        assert user["password_hash"] != "ValidPassword123"
        assert check_password_hash(user["password_hash"], "ValidPassword123")


def test_register_missing_or_empty_name(client):
    """Test rejection when name is missing or whitespace-only."""
    csrf = get_csrf(client)
    # Missing name
    res1 = client.post(
        "/api/auth/register",
        json={"phone": "+919876543211", "password": "Password123"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res1.status_code == 400
    assert res1.get_json()["error"]["code"] == "VALIDATION_ERROR"

    # Empty name
    res2 = client.post(
        "/api/auth/register",
        json={"name": "   ", "phone": "+919876543211", "password": "Password123"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res2.status_code == 400
    assert res2.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_register_invalid_or_non_e164_phone(client):
    """Test rejection of invalid phone formats."""
    csrf = get_csrf(client)
    # Missing country code
    res1 = client.post(
        "/api/auth/register",
        json={"name": "Bad Phone", "phone": "9876543210", "password": "Password123"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res1.status_code == 400
    assert "E.164" in res1.get_json()["error"]["message"]

    # Alphabetic string
    res2 = client.post(
        "/api/auth/register",
        json={"name": "Bad Phone", "phone": "not-a-number", "password": "Password123"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res2.status_code == 400


def test_register_missing_or_short_password(client):
    """Test rejection when password is missing or under 8 characters."""
    csrf = get_csrf(client)
    # Short password
    res1 = client.post(
        "/api/auth/register",
        json={"name": "Farmer Short", "phone": "+919876543212", "password": "short"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res1.status_code == 400
    assert "at least 8 characters" in res1.get_json()["error"]["message"]

    # Missing password
    res2 = client.post(
        "/api/auth/register",
        json={"name": "Farmer NoPass", "phone": "+919876543212"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res2.status_code == 400


def test_register_duplicate_phone_rejected(client):
    """Test that duplicate phone registration returns HTTP 409 Conflict."""
    csrf = get_csrf(client)
    # First registration
    client.post(
        "/api/auth/register",
        json={"name": "Farmer 1", "phone": "+919876543213", "password": "Password123"},
        headers={"X-CSRF-Token": csrf},
    )

    # Duplicate registration
    res = client.post(
        "/api/auth/register",
        json={"name": "Farmer 2", "phone": "+919876543213", "password": "Password123"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 409
    assert res.get_json()["error"]["code"] == "CONFLICT"


def test_register_client_cannot_escalate_to_admin(client, app):
    """Test that client passing role='admin' is forced to role='farmer'."""
    csrf = get_csrf(client)
    res = client.post(
        "/api/auth/register",
        json={
            "name": "Attacker",
            "phone": "+919876543214",
            "password": "Password123",
            "role": "admin",  # Client attempts role escalation
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 201
    assert res.get_json()["user"]["role"] == "farmer"

    with app.app_context():
        user = get_db().execute("SELECT * FROM users WHERE phone = ?", ("+919876543214",)).fetchone()
        assert user["role"] == "farmer"


# ============================================================================
# 3. LOGIN TESTS (POST /api/auth/login)
# ============================================================================

def test_login_farmer_success(client, app):
    """Test successful login for a farmer account."""
    create_user_direct(app, "Login Farmer", "+919876543220", "FarmerSecret123", role="farmer")

    csrf = get_csrf(client)
    res = client.post(
        "/api/auth/login",
        json={"phone": "+919876543220", "password": "FarmerSecret123"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["user"]["phone"] == "+919876543220"
    assert data["user"]["role"] == "farmer"
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]

    # Verify session cookie was set
    assert "session" in res.headers.get("Set-Cookie", "").lower()


def test_login_admin_success(client, app):
    """Test successful login for an admin account."""
    create_user_direct(app, "Login Admin", "+919876543221", "AdminSecret123", role="admin")

    csrf = get_csrf(client)
    res = client.post(
        "/api/auth/login",
        json={"phone": "+919876543221", "password": "AdminSecret123"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["user"]["role"] == "admin"


def test_login_wrong_password_generic_error(client, app):
    """Test wrong password returns generic 401 without leaking details."""
    create_user_direct(app, "Real Farmer", "+919876543222", "FarmerSecret123")

    csrf = get_csrf(client)
    res = client.post(
        "/api/auth/login",
        json={"phone": "+919876543222", "password": "WrongPassword456"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 401
    data = res.get_json()
    assert data["error"]["code"] == "INVALID_CREDENTIALS"
    assert data["error"]["message"] == "Invalid phone number or password."


def test_login_unknown_phone_generic_error(client):
    """Test unknown phone returns generic 401 identical to wrong password."""
    csrf = get_csrf(client)
    res = client.post(
        "/api/auth/login",
        json={"phone": "+919999999999", "password": "AnyPassword123"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 401
    data = res.get_json()
    assert data["error"]["code"] == "INVALID_CREDENTIALS"
    assert data["error"]["message"] == "Invalid phone number or password."


def test_login_missing_fields(client):
    """Test missing phone or password returns HTTP 400."""
    csrf = get_csrf(client)
    res = client.post(
        "/api/auth/login",
        json={"phone": "+919876543223"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 400


# ============================================================================
# 4. SESSION & CURRENT USER TESTS (GET /api/auth/me)
# ============================================================================

def test_me_unauthenticated(client):
    """Test GET /api/auth/me when no user is logged in."""
    res = client.get("/api/auth/me")
    assert res.status_code == 200
    data = res.get_json()
    assert data["authenticated"] is False
    assert data["user"] is None


def test_me_authenticated_farmer(client, app):
    """Test GET /api/auth/me returns farmer information after login."""
    create_user_direct(app, "Me Farmer", "+919876543230", "Password123", role="farmer")

    csrf = get_csrf(client)
    client.post(
        "/api/auth/login",
        json={"phone": "+919876543230", "password": "Password123"},
        headers={"X-CSRF-Token": csrf},
    )

    res = client.get("/api/auth/me")
    assert res.status_code == 200
    data = res.get_json()
    assert data["authenticated"] is True
    assert data["user"]["name"] == "Me Farmer"
    assert data["user"]["role"] == "farmer"


def test_me_authenticated_admin(client, app):
    """Test GET /api/auth/me returns admin information after login."""
    create_user_direct(app, "Me Admin", "+919876543231", "Password123", role="admin")

    csrf = get_csrf(client)
    client.post(
        "/api/auth/login",
        json={"phone": "+919876543231", "password": "Password123"},
        headers={"X-CSRF-Token": csrf},
    )

    res = client.get("/api/auth/me")
    assert res.status_code == 200
    data = res.get_json()
    assert data["authenticated"] is True
    assert data["user"]["role"] == "admin"


def test_me_role_reloaded_from_database(client, app):
    """Test that role changes in database take immediate effect on /api/auth/me."""
    user_id = create_user_direct(app, "Role Change User", "+919876543232", "Password123", role="farmer")

    csrf = get_csrf(client)
    client.post(
        "/api/auth/login",
        json={"phone": "+919876543232", "password": "Password123"},
        headers={"X-CSRF-Token": csrf},
    )

    # Initial check: farmer
    res1 = client.get("/api/auth/me")
    assert res1.get_json()["user"]["role"] == "farmer"

    # Simulate database admin promotion directly
    with app.app_context():
        db = get_db()
        db.execute("UPDATE users SET role = 'admin' WHERE id = ?", (user_id,))
        db.commit()

    # Next check: reloaded from database, role reflects 'admin'
    res2 = client.get("/api/auth/me")
    assert res2.get_json()["user"]["role"] == "admin"


def test_me_deleted_user_session_cleared_safely(client, app):
    """Test that if a user is deleted from database, the stale session is cleared."""
    user_id = create_user_direct(app, "Deleted User", "+919876543233", "Password123", role="farmer")

    csrf = get_csrf(client)
    client.post(
        "/api/auth/login",
        json={"phone": "+919876543233", "password": "Password123"},
        headers={"X-CSRF-Token": csrf},
    )

    # Delete the user from the database
    with app.app_context():
        db = get_db()
        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.commit()

    # Next request detects non-existent user and clears session
    res = client.get("/api/auth/me")
    assert res.status_code == 200
    data = res.get_json()
    assert data["authenticated"] is False
    assert data["user"] is None


# ============================================================================
# 5. LOGOUT TESTS (POST /api/auth/logout)
# ============================================================================

def test_logout_success_and_clears_session(client, app):
    """Test that logging out clears session and prevents authenticated access."""
    create_user_direct(app, "Logout Farmer", "+919876543240", "Password123", role="farmer")

    csrf = get_csrf(client)
    client.post(
        "/api/auth/login",
        json={"phone": "+919876543240", "password": "Password123"},
        headers={"X-CSRF-Token": csrf},
    )

    # Check authenticated
    assert client.get("/api/auth/me").get_json()["authenticated"] is True

    # Logout
    csrf_after_login = get_csrf(client)
    res = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_after_login})
    assert res.status_code == 200
    assert res.get_json()["status"] == "success"

    # Verify session is cleared
    assert client.get("/api/auth/me").get_json()["authenticated"] is False


def test_logout_while_already_logged_out_is_safe(client):
    """Test that calling logout when unauthenticated is completely safe."""
    csrf = get_csrf(client)
    res = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200
    assert res.get_json()["status"] == "success"


# ============================================================================
# 6. AUTHORIZATION DECORATOR TESTS
# ============================================================================

def test_authorization_unauthenticated_rejected(client):
    """Unauthenticated requests to protected test routes must return HTTP 401."""
    res1 = client.get("/api/test/login-only")
    assert res1.status_code == 401
    assert res1.get_json()["error"]["code"] == "UNAUTHENTICATED"

    res2 = client.get("/api/test/admin-only")
    assert res2.status_code == 401
    assert res2.get_json()["error"]["code"] == "UNAUTHENTICATED"


def test_authorization_farmer_cannot_access_admin_only(client, app):
    """Authenticated farmer accessing admin-only route must return HTTP 403."""
    create_user_direct(app, "Test Farmer Role", "+919876543250", "Password123", role="farmer")

    csrf = get_csrf(client)
    client.post(
        "/api/auth/login",
        json={"phone": "+919876543250", "password": "Password123"},
        headers={"X-CSRF-Token": csrf},
    )

    # Farmer can access login-only and farmer-only
    res_login = client.get("/api/test/login-only")
    assert res_login.status_code == 200

    res_farmer = client.get("/api/test/farmer-only")
    assert res_farmer.status_code == 200

    # Farmer accessing admin-only MUST be rejected with 403 Forbidden
    res_admin = client.get("/api/test/admin-only")
    assert res_admin.status_code == 403
    assert res_admin.get_json()["error"]["code"] == "FORBIDDEN"


def test_authorization_admin_can_access_admin_only(client, app):
    """Authenticated admin accessing admin-only route is permitted."""
    create_user_direct(app, "Test Admin Role", "+919876543251", "Password123", role="admin")

    csrf = get_csrf(client)
    client.post(
        "/api/auth/login",
        json={"phone": "+919876543251", "password": "Password123"},
        headers={"X-CSRF-Token": csrf},
    )

    # Admin can access admin-only
    res_admin = client.get("/api/test/admin-only")
    assert res_admin.status_code == 200
    assert res_admin.get_json()["status"] == "success"

    # Admin can access general login-only
    res_login = client.get("/api/test/login-only")
    assert res_login.status_code == 200

