import os
import sys
import tempfile
from datetime import date, timedelta
import pytest
from werkzeug.security import generate_password_hash

# Ensure soil-testing-portal directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.db import get_db, init_db


@pytest.fixture
def app_and_db():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_security.db")
        app = create_app({
            "TESTING": True,
            "DATABASE": db_path,
            "SECRET_KEY": "test-security-audit-key",
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
    res = client.get("/api/auth/csrf-token")
    assert res.status_code == 200
    return res.get_json()["csrf_token"]


def create_user(app, name, phone, role="farmer"):
    with app.app_context():
        db = get_db()
        cur = db.execute(
            "INSERT INTO users (name, phone, password_hash, role) VALUES (?, ?, ?, ?)",
            (name, phone, generate_password_hash("Password123"), role),
        )
        db.commit()
        return cur.lastrowid


def login(client, phone):
    csrf = get_csrf(client)
    res = client.post(
        "/api/auth/login",
        json={"phone": phone, "password": "Password123"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    return get_csrf(client)


# ============================================================================
# SECURITY & STABILIZATION AUDIT TESTS
# ============================================================================

def test_tracking_ownership_and_anti_enumeration(client, app):
    """
    Verifies that a farmer cannot view or enumerate another farmer's appointment/sample.
    Attempts return 404 (safe anti-enumeration) rather than revealing existence via 403.
    """
    farmer_a_id = create_user(app, "Farmer Ramesh", "+919876543501", role="farmer")
    farmer_b_id = create_user(app, "Farmer Suresh", "+919876543502", role="farmer")

    # Farmer A books an appointment
    csrf_a = login(client, "+919876543501")
    res_appt = client.post(
        "/api/appointments",
        json={
            "land_details": "4 acres coconut grove",
            "address": "Survey 9, Pandavapura, Mandya",
            "preferred_date": (date.today() + timedelta(days=3)).isoformat(),
            "preferred_time": "09:00-12:00",
        },
        headers={"X-CSRF-Token": csrf_a},
    )
    assert res_appt.status_code == 201
    appt_id = res_appt.get_json()["appointment"]["id"]

    # Retrieve sample code for appt_id
    with app.app_context():
        db = get_db()
        sample = db.execute("SELECT sample_code FROM soil_samples WHERE appointment_id = ?", (appt_id,)).fetchone()
        sample_code = sample["sample_code"]

    # Farmer A can access their own appointment timeline
    res_own = client.get(f"/api/tracking/appointment/{appt_id}")
    assert res_own.status_code == 200
    assert res_own.get_json()["timeline"]["appointment"]["land_details"] == "4 acres coconut grove"

    # Farmer B logs in and attempts to access Farmer A's appointment ID
    csrf_b = login(client, "+919876543502")
    res_unauthorized_appt = client.get(f"/api/tracking/appointment/{appt_id}")
    assert res_unauthorized_appt.status_code == 404
    assert res_unauthorized_appt.get_json()["error"]["code"] == "NOT_FOUND"

    # Farmer B attempts to query sample code directly
    res_unauthorized_sample = client.get(f"/api/tracking/sample/{sample_code}")
    assert res_unauthorized_sample.status_code == 404
    assert res_unauthorized_sample.get_json()["error"]["code"] == "NOT_FOUND"

    # Nonexistent sample returns identical 404 (preventing enumeration)
    res_fake = client.get("/api/tracking/sample/SMP-2099-99999")
    assert res_fake.status_code == 404


def test_field_worker_isolation_and_privacy(client, app):
    """
    Verifies that:
    1. Unassigned field worker is denied access to appointment tracking.
    2. Field worker visit list does not expose farmer's postal residential address.
    """
    farmer_id = create_user(app, "Farmer Kempanna", "+919876543510", role="farmer")
    worker_1_id = create_user(app, "Technician Anand", "+919876543511", role="field_worker")
    worker_2_id = create_user(app, "Technician Basavaraj", "+919876543512", role="field_worker")
    admin_id = create_user(app, "Admin Officer", "+919876543513", role="admin")

    # Farmer books appointment with distinct land and residential address
    csrf_f = login(client, "+919876543510")
    res_appt = client.post(
        "/api/appointments",
        json={
            "land_details": "Plot 44B, Sugarcane Belt, Maddur",
            "address": "House #12, 3rd Cross, Ashok Nagar, Mandya 571401",
            "preferred_date": (date.today() + timedelta(days=2)).isoformat(),
            "preferred_time": "14:00-17:00",
        },
        headers={"X-CSRF-Token": csrf_f},
    )
    appt_id = res_appt.get_json()["appointment"]["id"]

    # Admin assigns Worker 1
    csrf_admin = login(client, "+919876543513")
    res_assign = client.post(
        f"/api/admin/appointments/{appt_id}/assign",
        json={"worker_id": worker_1_id, "scheduled_date": (date.today() + timedelta(days=2)).isoformat()},
        headers={"X-CSRF-Token": csrf_admin},
    )
    assert res_assign.status_code == 200

    # Worker 1 logs in -> can access tracking
    csrf_w1 = login(client, "+919876543511")
    res_w1_tl = client.get(f"/api/tracking/appointment/{appt_id}")
    assert res_w1_tl.status_code == 200
    # Field worker does NOT receive the residential postal address in tracking
    assert "address" not in res_w1_tl.get_json()["timeline"]["appointment"]

    # Worker 1 visits list: does not leak residential address
    res_visits = client.get("/api/field-worker/visits")
    assert res_visits.status_code == 200
    v = res_visits.get_json()["visits"][0]
    assert v["land_details"] == "Plot 44B, Sugarcane Belt, Maddur"
    assert "farmer_address" not in v

    # Worker 2 logs in -> attempts to access unassigned appointment tracking -> FORBIDDEN 403
    csrf_w2 = login(client, "+919876543512")
    res_w2_tl = client.get(f"/api/tracking/appointment/{appt_id}")
    assert res_w2_tl.status_code == 403
    assert res_w2_tl.get_json()["error"]["code"] == "FORBIDDEN"


def test_lab_segregation_of_duties_and_locking(client, app):
    """
    Verifies that:
    1. Lab technician cannot self-approve their own test submission (dual signoff required).
    2. Lab staff cannot access farmer phone numbers in sample queue.
    3. Once authorized, laboratory results cannot be silently overwritten or modified.
    """
    farmer_id = create_user(app, "Farmer Siddaiah", "+919876543520", role="farmer")
    tech_id = create_user(app, "Analyst Praveen", "+919876543521", role="lab_staff")
    supervisor_id = create_user(app, "Supervisor Divya", "+919876543522", role="lab_staff")
    admin_id = create_user(app, "Admin Lead", "+919876543523", role="admin")

    # Farmer books appointment
    csrf_f = login(client, "+919876543520")
    res_appt = client.post(
        "/api/appointments",
        json={
            "land_details": "2 acres mulberry plantation",
            "address": "Survey 33, Malavalli, Mandya",
            "preferred_date": (date.today() + timedelta(days=2)).isoformat(),
            "preferred_time": "09:00-12:00",
        },
        headers={"X-CSRF-Token": csrf_f},
    )
    appt_id = res_appt.get_json()["appointment"]["id"]

    # Technician checks in sample
    csrf_tech = login(client, "+919876543521")
    res_samples = client.get("/api/lab/samples")
    assert res_samples.status_code == 200
    sample_item = [s for s in res_samples.get_json()["samples"] if s["appointment_id"] == appt_id][0]
    sample_id = sample_item["sample_id"]

    # Verify technician does NOT receive farmer's private phone number in sample list
    assert "farmer_phone" not in sample_item

    # Technician records chemical assay
    assay_payload = {
        "ph_value": 7.1,
        "ec_ds_m": 0.35,
        "organic_carbon_pct": 0.55,
        "nitrogen_kg_ha": 290.0,
        "phosphorus_kg_ha": 26.0,
        "potassium_kg_ha": 180.0,
        "remarks": "Standard chemical analysis complete.",
    }
    res_assay = client.post(
        f"/api/lab/samples/{sample_id}/assay",
        json=assay_payload,
        headers={"X-CSRF-Token": csrf_tech},
    )
    assert res_assay.status_code == 201
    assay_id = res_assay.get_json()["assay_id"]

    # Technician attempts to self-approve the assay -> Denied 403 under segregation of duties
    res_self_auth = client.post(f"/api/lab/assays/{assay_id}/authorize", headers={"X-CSRF-Token": csrf_tech})
    assert res_self_auth.status_code == 403
    assert "Segregation of duties" in res_self_auth.get_json()["error"]["message"]

    # Distinct supervisor authorizes the assay -> Approved 200
    csrf_sup = login(client, "+919876543522")
    res_sup_auth = client.post(f"/api/lab/assays/{assay_id}/authorize", headers={"X-CSRF-Token": csrf_sup})
    assert res_sup_auth.status_code == 200
    assert res_sup_auth.get_json()["lab_status"] == "Authorized"

    # Attempt to re-authorize already authorized assay -> Denied 400
    res_reauth = client.post(f"/api/lab/assays/{assay_id}/authorize", headers={"X-CSRF-Token": csrf_sup})
    assert res_reauth.status_code == 400

    # Technician logs in again and attempts to modify/overwrite authorized assay -> Denied 403 (Locked)
    csrf_tech_again = login(client, "+919876543521")
    res_tamper = client.post(
        f"/api/lab/samples/{sample_id}/assay",
        json={**assay_payload, "ph_value": 4.5},
        headers={"X-CSRF-Token": csrf_tech_again},
    )
    assert res_tamper.status_code == 403
    assert "Authorized laboratory results are locked" in res_tamper.get_json()["error"]["message"]


def test_postal_dispatch_consignment_validation(client, app):
    """
    Verifies that:
    1. Fake, demo, or placeholder consignment numbers are rejected.
    2. Invalid Speed Post formats are rejected.
    3. Valid India Post Speed Post consignment barcodes (UPU S10 13-character) are accepted.
    """
    admin_id = create_user(app, "Dispatch Manager", "+919876543530", role="admin")
    farmer_id = create_user(app, "Farmer Gowda", "+919876543531", role="farmer")

    with app.app_context():
        db = get_db()
        cur_a = db.execute(
            "INSERT INTO appointments (farmer_id, land_details, address, preferred_date, preferred_time, status) VALUES (?, ?, ?, ?, ?, 'Completed')",
            (farmer_id, "5 acres", "Mandya", "2026-11-05", "09:00-12:00"),
        )
        appt_id = cur_a.lastrowid
        cur_d = db.execute(
            "INSERT INTO report_dispatches (appointment_id, recipient_name, recipient_phone, delivery_address_snapshot, courier_service, dispatch_status) VALUES (?, 'Farmer Gowda', '+919876543531', '{}', 'India Post Speed Post', 'Printed')",
            (appt_id,),
        )
        dispatch_id = cur_d.lastrowid
        db.commit()

    csrf_admin = login(client, "+919876543530")

    # 1. Prohibit DEMO placeholders
    for demo_code in ["DEMO", "TEST", "0000000000000", "EK000000000IN", "TEST123456789"]:
        res_demo = client.post(
            f"/api/dispatch/{dispatch_id}/dispatch",
            json={"courier_service": "India Post Speed Post", "tracking_number": demo_code},
            headers={"X-CSRF-Token": csrf_admin},
        )
        assert res_demo.status_code == 400
        assert res_demo.get_json()["error"]["code"] == "VALIDATION_ERROR"

    # 2. Reject malformed Speed Post consignment code (e.g. wrong length or missing letters)
    res_bad = client.post(
        f"/api/dispatch/{dispatch_id}/dispatch",
        json={"courier_service": "India Post Speed Post", "tracking_number": "EK123IN"},
        headers={"X-CSRF-Token": csrf_admin},
    )
    assert res_bad.status_code == 400
    assert "Invalid India Post Speed Post" in res_bad.get_json()["error"]["message"]

    # 3. Accept valid 13-character Speed Post barcode (UPU S10 standard)
    res_ok = client.post(
        f"/api/dispatch/{dispatch_id}/dispatch",
        json={"courier_service": "India Post Speed Post", "tracking_number": "EM123456789IN"},
        headers={"X-CSRF-Token": csrf_admin},
    )
    assert res_ok.status_code == 200
    assert res_ok.get_json()["dispatch_status"] == "Dispatched"
    assert res_ok.get_json()["tracking_number"] == "EM123456789IN"
