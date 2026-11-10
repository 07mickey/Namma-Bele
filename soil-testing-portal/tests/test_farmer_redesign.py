import os
import tempfile
import sqlite3
import pytest
from app import create_app
from app.db import init_db
from werkzeug.security import generate_password_hash


@pytest.fixture
def test_setup():
    temp_dir = tempfile.TemporaryDirectory()
    db_path = os.path.join(temp_dir.name, "test_redesign.db")
    reports_dir = os.path.join(temp_dir.name, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    app = create_app({
        "TESTING": True,
        "DATABASE": db_path,
        "REPORT_FOLDER": reports_dir,
        "SECRET_KEY": "test-farmer-redesign-secret",
    })

    with app.app_context():
        init_db()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (name, phone, password_hash, role) VALUES (?, ?, ?, 'farmer')",
        ("Ramesh Patel", "+919876543210", generate_password_hash("FarmerSecret123"))
    )
    farmer_id = cur.lastrowid
    conn.commit()
    conn.close()

    client = app.test_client()

    yield {
        "app": app,
        "client": client,
        "db_path": db_path,
        "farmer_id": farmer_id
    }

    temp_dir.cleanup()


def test_soil_guide_view_public_access(test_setup):
    """
    Verifies that GET /soil-guide is publicly accessible, renders semantic
    Jinja2 layout with base navbar, educational N-P-K content, pH scale,
    sampling methodology, and local Three.js asset inclusions.
    """
    client = test_setup["client"]
    resp = client.get("/soil-guide")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # 1. Branding and Title
    assert "Soil Health &amp; Testing Guide" in html
    assert "Farmer's Practical Soil Health &amp; Testing Guide" in html

    # 2. Primary Nutrients (N-P-K)
    assert "Nitrogen (N)" in html
    assert "Phosphorus (P)" in html
    assert "Potassium (K)" in html
    assert "Chlorophyll" in html
    assert "Deficiency Symptoms" in html

    # 3. Soil pH Section
    assert "Soil pH &amp; Nutrient Availability" in html
    assert "Acidic (&lt; 6.0)" in html
    assert "Neutral Loam (6.0 – 7.5) Optimal" in html
    assert "Alkaline (&gt; 7.5)" in html

    # 4. Standard 5-Step Field Sampling Protocol
    assert "Standard 5-Step Field Soil Sampling Protocol" in html
    assert "V-Shaped Cut" in html
    assert "Uniform Furrow Slice" in html
    assert "Zig-Zag Sub-Samples" in html
    assert "Quartering Reduction" in html
    assert "Shade Drying &amp; Bagging" in html

    # 5. Scientific Advisory Notice
    assert "Official Agronomic Advisory Notice" in html
    assert "official laboratory soil test certificate" in html

    # 6. Three.js Canvas Container & WebGL Fallback Card
    assert 'id="threejs-soil-canvas-container"' in html
    assert 'id="webgl-fallback"' in html
    assert "three.min.js" in html
    assert "soil_3d.js" in html


def test_farmer_dashboard_wizard_elements_and_status_tabs_rendered(test_setup):
    """
    Verifies that GET /farmer renders the 3-step booking wizard stepper,
    official time slot radio cards, review confirmation card, and the
    accessible appointment status tabs with counters.
    """
    client = test_setup["client"]

    # 1. Obtain CSRF token
    csrf_resp = client.get("/api/auth/csrf-token")
    csrf_token = csrf_resp.get_json()["csrf_token"]

    # 2. Log in as farmer
    login_resp = client.post("/api/auth/login", json={
        "phone": "+919876543210",
        "password": "FarmerSecret123"
    }, headers={"X-CSRF-Token": csrf_token})
    assert login_resp.status_code == 200

    resp = client.get("/farmer")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # 1. AgriTech Hero Banner & Brand Logo
    assert "Registered Farmer Dashboard" in html
    assert "logo.svg" in html

    # 2. Multi-step Stepper Components
    assert 'class="booking-stepper"' in html
    assert 'id="step-node-1"' in html
    assert 'id="step-node-2"' in html
    assert 'id="step-node-3"' in html
    assert 'id="booking-step-1"' in html
    assert 'id="booking-step-2"' in html
    assert 'id="booking-step-3"' in html

    # 3. Step 2 Official Slot Selection Cards
    assert 'id="slot-card-morning"' in html
    assert 'id="slot-card-afternoon"' in html
    assert "09:00 AM – 12:00 PM" in html
    assert "02:00 PM – 05:00 PM" in html

    # 4. Step 3 Review Card Elements
    assert 'class="review-summary-card"' in html
    assert 'id="review-land"' in html
    assert 'id="review-address"' in html
    assert 'id="review-date"' in html
    assert 'id="review-time"' in html

    # 5. Accessible Status Filter Tabs & Counters
    assert 'role="tablist"' in html
    assert 'data-status="All"' in html
    assert 'data-status="Pending"' in html
    assert 'data-status="Approved"' in html
    assert 'data-status="Rejected"' in html
    assert 'data-status="Completed"' in html
    assert 'id="count-all"' in html
    assert 'id="count-pending"' in html
    assert 'id="count-approved"' in html
    assert 'id="count-rejected"' in html
    assert 'id="count-completed"' in html


def test_farmer_multi_step_booking_workflow_submission(test_setup):
    """
    Tests the complete end-to-end booking flow: authenticates as farmer,
    obtains double-submit CSRF token, and submits an appointment with
    the approved time slot window (09:00-12:00).
    """
    client = test_setup["client"]

    # 1. Get CSRF token
    csrf_resp = client.get("/api/auth/csrf-token")
    assert csrf_resp.status_code == 200
    csrf_token = csrf_resp.get_json()["csrf_token"]

    # 2. Log in
    login_resp = client.post("/api/auth/login", json={
        "phone": "+919876543210",
        "password": "FarmerSecret123"
    }, headers={"X-CSRF-Token": csrf_token})
    assert login_resp.status_code == 200

    # 3. Fetch fresh post-login CSRF token
    post_csrf = client.get("/api/auth/csrf-token").get_json()["csrf_token"]

    # 4. Submit appointment request with valid future date
    from datetime import date, timedelta
    future_date = (date.today() + timedelta(days=5)).isoformat()
    book_resp = client.post("/api/appointments", json={
        "land_details": "4.5 Acres Black Soil Plot (Kharif Cotton)",
        "address": "Survey No. 42, Someshwar Village, Hubli",
        "preferred_date": future_date,
        "preferred_time": "09:00-12:00",
        "notes": "Near north irrigation pump"
    }, headers={"X-CSRF-Token": post_csrf})

    assert book_resp.status_code == 201
    data = book_resp.get_json()
    assert data["status"] == "success"
    assert data["appointment"]["status"] == "Pending"
    assert data["appointment"]["preferred_time"] == "09:00-12:00"

    # 5. Verify listing reflects the newly created booking
    list_resp = client.get("/api/appointments")
    assert list_resp.status_code == 200
    apts = list_resp.get_json()["appointments"]
    assert len(apts) == 1
    assert apts[0]["land_details"] == "4.5 Acres Black Soil Plot (Kharif Cotton)"


def test_local_static_assets_availability(test_setup):
    """
    Verifies that the new local assets (Three.js vendor library, 3D visualizer script,
    and SVG logo) are properly served by Flask static routing without external CDNs.
    """
    client = test_setup["client"]

    # 1. Three.js Vendor Library
    three_resp = client.get("/static/js/vendor/three.min.js")
    assert three_resp.status_code == 200
    assert len(three_resp.data) > 100000

    # 2. Soil 3D Visualizer Script
    vis_resp = client.get("/static/js/soil_3d.js")
    assert vis_resp.status_code == 200
    assert b"isWebGLAvailable" in vis_resp.data
    assert b"THREE.WebGLRenderer" in vis_resp.data

    # 3. Logo SVG
    logo_resp = client.get("/static/img/logo.svg")
    assert logo_resp.status_code == 200
    assert b"<svg" in logo_resp.data
    assert b"badgeGrad" in logo_resp.data
