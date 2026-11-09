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
        db_path = os.path.join(temp_dir, "test_lab_workflow.db")
        app = create_app({
            "TESTING": True,
            "DATABASE": db_path,
            "SECRET_KEY": "test-lab-key",
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
# LABORATORY WORKFLOW TESTS
# ============================================================================

def test_full_laboratory_lifecycle(client, app):
    """
    1. Farmer books appointment.
    2. Lab receives sample (Stage 7).
    3. Lab starts testing (Stage 8).
    4. Lab logs chemical assay (pH=6.5, EC=0.45, OC=0.65, N=310, P=28, K=220) -> Stage 9 & 10.
    5. Admin / Lab Head authorizes report -> Stage 11, appointment Completed, dispatch queued.
    """
    create_user(app, "Farmer Lab Test", "+919876543301", role="farmer")
    create_user(app, "Lab Analyst Kumar", "+919876543302", role="lab_staff")
    create_user(app, "Admin Supervisor", "+919876543303", role="admin")

    # Farmer books appointment
    farmer_csrf = login(client, "+919876543301")
    future_date = (date.today() + timedelta(days=2)).isoformat()
    res_appt = client.post(
        "/api/appointments",
        json={
            "land_details": "6 acres paddy field",
            "address": "Survey 12, Srirangapatna, Mandya",
            "preferred_date": future_date,
            "preferred_time": "09:00-12:00",
        },
        headers={"X-CSRF-Token": farmer_csrf},
    )
    assert res_appt.status_code == 201
    appt_id = res_appt.get_json()["appointment"]["id"]

    # 1. Lab analyst lists samples
    lab_csrf = login(client, "+919876543302")
    res_samples = client.get("/api/lab/samples")
    assert res_samples.status_code == 200
    samples = res_samples.get_json()["samples"]
    target_sample = [s for s in samples if s["appointment_id"] == appt_id][0]
    sample_id = target_sample["sample_id"]

    # 2. Lab checks in sample
    res_rcv = client.post(f"/api/lab/samples/{sample_id}/receive", headers={"X-CSRF-Token": lab_csrf})
    assert res_rcv.status_code == 200
    assert res_rcv.get_json()["sample_status"] == "Received"

    # 3. Lab starts testing
    res_start = client.post(f"/api/lab/samples/{sample_id}/start-test", headers={"X-CSRF-Token": lab_csrf})
    assert res_start.status_code == 200
    assert res_start.get_json()["sample_status"] == "Testing"

    # 4. Lab logs assay measurements
    assay_payload = {
        "ph_value": 6.8,
        "ec_ds_m": 0.42,
        "organic_carbon_pct": 0.68,
        "nitrogen_kg_ha": 320.0,
        "phosphorus_kg_ha": 35.0,
        "potassium_kg_ha": 210.0,
        "remarks": "Optimal neutral pH with balanced NPK levels.",
    }
    res_assay = client.post(
        f"/api/lab/samples/{sample_id}/assay",
        json=assay_payload,
        headers={"X-CSRF-Token": lab_csrf},
    )
    assert res_assay.status_code == 201
    assay_data = res_assay.get_json()
    assay_id = assay_data["assay_id"]
    ratings = assay_data["ratings"]

    assert ratings["ph_rating"] == "Neutral / Optimal"
    assert ratings["ec_rating"] == "Normal"
    assert ratings["oc_rating"] == "Medium"
    assert ratings["n_rating"] == "Medium"
    assert ratings["p_rating"] == "Medium"
    assert ratings["k_rating"] == "Medium"

    # 5. Authorize report
    admin_csrf = login(client, "+919876543303")
    res_auth = client.post(f"/api/lab/assays/{assay_id}/authorize", headers={"X-CSRF-Token": admin_csrf})
    assert res_auth.status_code == 200
    auth_data = res_auth.get_json()
    assert auth_data["lab_status"] == "Authorized"
    assert auth_data["appointment_status"] == "Completed"

    # 6. Verify appointment and dispatch queue
    with app.app_context():
        db = get_db()
        appt = db.execute("SELECT status FROM appointments WHERE id = ?", (appt_id,)).fetchone()
        assert appt["status"] == "Completed"

        dispatch = db.execute("SELECT * FROM report_dispatches WHERE appointment_id = ?", (appt_id,)).fetchone()
        assert dispatch is not None
        assert dispatch["dispatch_status"] == "Queued"
        assert dispatch["courier_service"] == "India Post Speed Post"

    # 7. Check timeline has stages 7, 8, 9, 10, 11 COMPLETED
    res_tl = client.get(f"/api/tracking/appointment/{appt_id}")
    assert res_tl.status_code == 200
    stages = {s["stage_number"]: s["status"] for s in res_tl.get_json()["timeline"]["stages"]}
    assert stages[7] == "COMPLETED"   # SAMPLE_RECEIVED_LAB
    assert stages[8] == "COMPLETED"   # LAB_ANALYSIS_IN_PROGRESS
    assert stages[9] == "COMPLETED"   # TEST_RESULTS_RECORDED
    assert stages[10] == "COMPLETED"  # REPORT_UNDER_REVIEW
    assert stages[11] == "COMPLETED"  # REPORT_AUTHORIZED

