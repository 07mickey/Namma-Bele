import os
import tempfile
import sqlite3
import pytest
from app import create_app
from app.db import init_db
from werkzeug.security import generate_password_hash


@pytest.fixture
def m2_client():
    temp_dir = tempfile.TemporaryDirectory()
    db_path = os.path.join(temp_dir.name, "test_m2.db")
    reports_dir = os.path.join(temp_dir.name, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    app = create_app({
        "TESTING": True,
        "DATABASE": db_path,
        "REPORT_FOLDER": reports_dir,
        "SECRET_KEY": "test-m2-integration-secret",
    })

    with app.app_context():
        init_db()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (name, phone, password_hash, role) VALUES (?, ?, ?, 'farmer')",
        ("Anand Rao", "+919876543222", generate_password_hash("FarmerSecret123"))
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


def test_landing_page_m2_editorial_triad_and_sprout(m2_client):
    """
    Verifies that GET / renders M2's Editorial Top Triad:
    - Mission Statement
    - Handcrafted Loam Soil Mound Sprout SVG
    - Authentic Extension Support Box (Free of Unsupported Ratings)
    - Community Soil Health Initiative badge
    """
    client = m2_client["client"]
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # 1. Editorial Triad & Sprout SVG
    assert "hero-editorial-top" in html
    assert "hero-editorial-statement" in html
    assert "soil-mound-wrapper" in html
    assert "soil-mound-svg" in html
    assert "sproutGrad" in html
    assert "hero-trust-box" in html
    assert "Agricultural Extension" in html
    assert "Connecting village farms" in html
    # Ensure unsupported rating is removed
    assert "4.9/5" not in html

    # 2. Pill Button
    assert "btn-pill-arrow" in html
    assert "Book a Soil Test" in html

    # 3. Authoritative Title
    assert "Community Soil Testing Portal" in html
    assert "Portal Diagnostics" in html


def test_landing_page_bento_grid_and_spotlight(m2_client):
    """
    Verifies that GET / renders M2's 3x2 Asymmetric Bento Grid
    and Interactive Soil Health Card Spotlight with Crop Selector
    using verified, scientifically responsible agronomic claims.
    """
    client = m2_client["client"]
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # 1. Bento Grid (6 cards with verified claims)
    assert "bento-section" in html
    assert "Why Village Soil Testing Matters" in html
    assert "bento-grid" in html
    assert "Standardized Field Sampling" in html
    assert "Promotes Soil Health" in html
    assert "Farm Plot Identification" in html
    assert "Informed Fertilizer Usage" in html
    assert "Biological Soil Activity" in html
    assert "Prevents Soil Degradation" in html

    # 2. Spotlight Section
    assert "spotlight-wrapper" in html
    assert "Official Soil Health Cards" in html
    assert "spotlight-card" in html
    assert "Sample Demonstration" in html
    assert 'data-crop="cotton"' in html
    assert 'data-crop="sugarcane"' in html
    assert 'data-crop="paddy"' in html
    assert 'data-crop="maize"' in html
    assert 'data-crop="groundnut"' in html

    # 3. Nutrient Meters & Explicit Disclaimer
    assert "nutrient-meters" in html
    assert "Available Nitrogen (N)" in html
    assert "Available Phosphorus (P)" in html
    assert "Available Potassium (K)" in html
    assert "Soil Reaction (pH)" in html
    assert "crop-advising-box" in html
    assert "illustrative examples" in html
    assert "verified laboratory test report" in html


def test_landing_page_accordion_faq(m2_client):
    """
    Verifies that GET / renders M2's Clean Pill Accordion FAQ with 5 items.
    """
    client = m2_client["client"]
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    assert "faq-section" in html
    assert "Frequently Asked Questions" in html
    assert "What parameters are tested in the official soil report?" in html
    assert "When is the ideal time to book a soil sample collection?" in html
    assert "Do I need to be present at the field when the coordinator visits?" in html
    assert "How do I access and download my report once testing is complete?" in html
    assert "Is there a fee for soil sample collection and testing?" in html


def test_farmer_portal_m2_components(m2_client):
    """
    Verifies that authenticated GET /farmer renders:
    - M2 Latest Appointment Status Card (#latest-status)
    - M2 Farmer Portal Services Quick Action Cards (.action-card)
    - Multi-step booking wizard and accessible filter tabs
    """
    client = m2_client["client"]

    # Authenticate as farmer
    csrf_resp = client.get("/api/auth/csrf-token")
    csrf_token = csrf_resp.get_json()["csrf_token"]

    login_resp = client.post("/api/auth/login", json={
        "phone": "+919876543222",
        "password": "FarmerSecret123"
    }, headers={"X-CSRF-Token": csrf_token})
    assert login_resp.status_code == 200

    resp = client.get("/farmer")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # 1. Latest Status Card
    assert 'id="latest-status"' in html
    assert 'id="status-badge-container"' in html
    assert 'id="status-card-content"' in html

    # 2. Farmer Portal Action Cards
    assert "Farmer Portal Services" in html
    assert "action-card" in html
    assert "Book Soil Test" in html
    assert "Live Sample Tracking" in html
    assert "Appointments &amp; Reports" in html


def test_style_css_contains_m2_tokens_and_classes(m2_client):
    """
    Verifies that /static/css/style.css serves all M2 color tokens,
    glassmorphism utilities, bento grid, and spotlight styling.
    """
    client = m2_client["client"]
    resp = client.get("/static/css/style.css")
    assert resp.status_code == 200
    css = resp.get_data(as_text=True)

    assert "--color-primary-green" in css
    assert "--color-earth-brown" in css
    assert "--glass-bg" in css
    assert ".hero-editorial-top" in css
    assert ".soil-mound-wrapper" in css
    assert ".btn-pill-arrow" in css
    assert ".bento-grid" in css
    assert ".spotlight-wrapper" in css
    assert ".faq-section" in css
    assert ".action-card" in css

