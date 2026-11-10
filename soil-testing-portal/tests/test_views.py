"""
Views and end-to-end integration test suite.
Updated to test the integrated soilfrontend pages and full workflow capabilities.
"""
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
    """GET / renders index.html with portal branding and navigation."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "Soil Testing" in html or "SoilTest" in html
    assert "styles.css" in html
    assert "logo.svg" in html


def test_render_register_page(client):
    """GET /register renders register.html with farmer registration form."""
    res = client.get("/register")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "register" in html.lower() or "farmer" in html.lower()
    assert 'name="name"' in html or 'id="name"' in html
    assert 'name="phone"' in html or 'id="phone"' in html
    assert 'name="password"' in html or 'id="password"' in html


def test_render_login_page(client):
    """GET /login renders login.html."""
    res = client.get("/login")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "login" in html.lower() or "sign in" in html.lower()


def test_render_farmer_page_unauthenticated_redirects(client):
    """GET /farmer without authentication redirects (302) to /login."""
    res = client.get("/farmer")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]


def test_render_admin_page_unauthenticated_redirects(client):
    """GET /admin without authentication redirects (302)."""
    res = client.get("/admin")
    assert res.status_code == 302


def test_render_farmer_page_authenticated(app, client):
    """GET /farmer with farmer session renders dashboard.html (200)."""
    from app.db import get_db
    from werkzeug.security import generate_password_hash

    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users (name, phone, password_hash, role) VALUES (?, ?, ?, ?)",
            ("Kavitha Farmer", "+919876543290", generate_password_hash("Pass1234"), "farmer"),
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
    assert "Dashboard" in html


def test_render_admin_page_authenticated(app, client):
    """GET /admin with admin session renders admin-dashboard.html (200)."""
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
    assert "Admin Dashboard" in html


def test_static_css_and_js_served_correctly(client):
    """Static assets are served with proper content types."""
    res_css = client.get("/static/css/styles.css")
    assert res_css.status_code == 200
    assert "text/css" in res_css.content_type

    res_api = client.get("/static/js/api.js")
    assert res_api.status_code == 200
    assert "javascript" in res_api.content_type

    res_admin = client.get("/static/js/admin.js")
    assert res_admin.status_code == 200
    assert "javascript" in res_admin.content_type
