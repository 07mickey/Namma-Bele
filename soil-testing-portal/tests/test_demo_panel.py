"""
Tests for NAMMA BELE Demo Account Access Panel on Login Page.
Verifies conditional rendering under DEMO_MODE=True and strict absence under DEMO_MODE=False.
"""
import os
import tempfile
import pytest
from app import create_app
from app.db import init_db


@pytest.fixture
def app():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_demo_panel.db")
        reports_dir = os.path.join(temp_dir, "reports")
        os.makedirs(reports_dir, exist_ok=True)

        app = create_app({
            "TESTING": True,
            "DATABASE": db_path,
            "REPORT_FOLDER": reports_dir,
            "SECRET_KEY": "test-demo-panel-secret-key",
            "DEMO_MODE": False,
        })

        with app.app_context():
            init_db()

        yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_demo_panel_rendered_when_demo_mode_true():
    """When DEMO_MODE is True, /login must display the full Explore NAMMA BELE demo access panel."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_demo_active.db")
        reports_dir = os.path.join(temp_dir, "reports")
        os.makedirs(reports_dir, exist_ok=True)

        app = create_app({
            "TESTING": True,
            "DATABASE": db_path,
            "REPORT_FOLDER": reports_dir,
            "SECRET_KEY": "test-demo-panel-secret-key",
            "DEMO_MODE": True,
        })
        with app.app_context():
            init_db()

        with app.test_client() as client:
            res = client.get("/login")
            assert res.status_code == 200
            html = res.data.decode("utf-8")

            # 1. Section headers
            assert "Explore NAMMA BELE — Demo Access" in html
            assert "Choose a role to explore the platform using our pre-configured demonstration accounts." in html
            assert "demo-access-panel" in html
            assert "demo-layout-active" in html
            assert "demo-loaded-banner" in html

            # 2. Common password indicator
            assert "DemoUser@2026!" in html

            # 3. All 9 pre-configured demo accounts
            # Farmer 1
            assert "Demo Farmer Mallikarjuna" in html
            assert "+919999000001" in html

            # Assisted Farmer (Unclaimed)
            assert "Demo Assisted Farmer Chennamma" in html
            assert "+919999000002" in html
            assert "UNCLAIMED" in html
            assert "123456" in html
            assert 'href="/claim"' in html

            # Operator
            assert "Demo Operator Pooja" in html
            assert "+919999000003" in html

            # Field Worker
            assert "Demo Field Technician Ravi Kumar" in html
            assert "+919999000004" in html

            # Lab Analyst
            assert "Demo Lab Analyst Dr. Anita" in html
            assert "+919999000005" in html

            # Lab Supervisor
            assert "Demo Lab Supervisor Dr. Patil" in html
            assert "+919999000006" in html

            # Agricultural Advisor
            assert "Demo Agronomist Dr. Hegde" in html
            assert "+919999000007" in html

            # Administrator
            assert "Demo Administrator Lead" in html
            assert "+919999000008" in html

            # Second Farmer
            assert "Demo Farmer Shivalingappa" in html
            assert "+919999000009" in html


def test_demo_panel_strictly_absent_when_demo_mode_false(client):
    """When DEMO_MODE is False (production default), demo panel and all demo credentials must be completely absent."""
    res = client.get("/login")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Must not contain demo panel or heading
    assert "Explore NAMMA BELE — Demo Access" not in html
    assert "demo-access-panel" not in html
    assert "demo-layout-active" not in html

    # Must not contain any demo phones
    assert "+919999000001" not in html
    assert "+919999000002" not in html
    assert "+919999000003" not in html
    assert "+919999000004" not in html
    assert "+919999000005" not in html
    assert "+919999000006" not in html
    assert "+919999000007" not in html
    assert "+919999000008" not in html
    assert "+919999000009" not in html

    # Must not contain demo password or OTP
    assert "DemoUser@2026!" not in html
    assert "123456" not in html
    assert "Mallikarjuna" not in html
    assert "Chennamma" not in html


def test_standard_login_form_remains_functional(client):
    """Ensure standard login form fields, tabs, and CSRF endpoint remain intact."""
    res = client.get("/login")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert 'id="login-form"' in html
    assert 'id="login-phone"' in html
    assert 'id="login-password"' in html
    assert 'id="tab-farmer-login"' in html
    assert 'id="tab-staff-login"' in html
