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
        db_path = os.path.join(temp_dir, "test_tracking.db")
        app = create_app({
            "TESTING": True,
            "DATABASE": db_path,
            "SECRET_KEY": "test-tracking-key",
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


def create_appointment(client, csrf):
    future_date = (date.today() + timedelta(days=3)).isoformat()
    res = client.post(
        "/api/appointments",
        json={
            "land_details": "4 acres sugarcane plot",
            "address": "Survey 44, Maddur, Mandya",
            "preferred_date": future_date,
            "preferred_time": "09:00-12:00",
            "notes": "Near canal gate",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 201
    return res.get_json()["appointment"]["id"], res.get_json()["appointment"]["sample_code"]


# ============================================================================
# TRACKING & FIELD TESTS
# ============================================================================

def test_13_stage_timeline_generation(client, app):
    """Test that appointment has complete 13-stage timeline structure."""
    farmer_id = create_user(app, "Farmer Tracking", "+919876543201", role="farmer")
    csrf = login(client, "+919876543201")
    appt_id, sample_code = create_appointment(client, csrf)

    res = client.get(f"/api/tracking/appointment/{appt_id}")
    assert res.status_code == 200
    data = res.get_json()["timeline"]

    assert data["appointment_id"] == appt_id
    assert data["sample_code"] == sample_code
    assert len(data["stages"]) == 13

    # Stage 1 must be COMPLETED
    stage1 = data["stages"][0]
    assert stage1["stage_number"] == 1
    assert stage1["stage_name"] == "APPOINTMENT_REQUESTED"
    assert stage1["status"] == "COMPLETED"
    assert stage1["department"] == "Customer Service"
    assert stage1["timestamp"] is not None

    # Later stages should be PENDING or IN_PROGRESS
    stage13 = data["stages"][12]
    assert stage13["stage_number"] == 13
    assert stage13["stage_name"] == "REPORT_DELIVERED"
    assert stage13["status"] == "PENDING"


def test_field_worker_assignment_and_visit_lifecycle(client, app):
    """
    1. Admin assigns field worker to appointment.
    2. Field worker sees visit in their assignments.
    3. Field worker logs sample collection.
    4. Stages 3, 4, 5, 6 are completed in tracking timeline.
    """
    create_user(app, "Farmer Field", "+919876543210", role="farmer")
    worker_id = create_user(app, "Tech Chandru", "+919876543211", role="field_worker")
    create_user(app, "Admin Ops", "+919876543212", role="admin")

    # Farmer books appointment
    farmer_csrf = login(client, "+919876543210")
    appt_id, sample_code = create_appointment(client, farmer_csrf)

    # 1. Admin assigns field worker
    admin_csrf = login(client, "+919876543212")
    sched_date = (date.today() + timedelta(days=2)).isoformat()
    res_assign = client.post(
        f"/api/admin/appointments/{appt_id}/assign",
        json={
            "worker_id": worker_id,
            "scheduled_date": sched_date,
            "scheduled_slot": "09:00-12:00",
        },
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert res_assign.status_code == 200
    visit_id = res_assign.get_json()["visit_id"]

    # 2. Field worker checks visits
    worker_csrf = login(client, "+919876543211")
    res_visits = client.get("/api/field-worker/visits")
    assert res_visits.status_code == 200
    visits = res_visits.get_json()["visits"]
    assert len(visits) >= 1
    target_visit = [v for v in visits if v["visit_id"] == visit_id][0]
    assert target_visit["farmer_name"] == "Farmer Field"
    assert target_visit["visit_status"] == "Scheduled"

    # 3. Field worker collects soil sample
    res_collect = client.post(
        f"/api/field-worker/visits/{visit_id}/collect",
        json={
            "sampling_depth_cm": 15.0,
            "soil_appearance": "Red sandy loam, moist composite core",
            "gps_latitude": 12.5204,
            "gps_longitude": 76.8953,
            "survey_number": "SY-88/2",
            "worker_notes": "Sample collected from 5 zigzag spots on plot.",
        },
        headers={"X-CSRF-Token": worker_csrf},
    )
    assert res_collect.status_code == 200
    data_collect = res_collect.get_json()
    assert data_collect["visit_status"] == "Completed"
    assert data_collect["sample_status"] == "In_Transit"

    # 4. Verify timeline reflects sample collection & transit
    res_tl = client.get(f"/api/tracking/sample/{sample_code}")
    assert res_tl.status_code == 200
    timeline = res_tl.get_json()["timeline"]

    stages_by_num = {s["stage_number"]: s for s in timeline["stages"]}
    assert stages_by_num[3]["status"] == "COMPLETED"  # FIELD_WORKER_ASSIGNED
    assert stages_by_num[4]["status"] == "COMPLETED"  # VISIT_SCHEDULED
    assert stages_by_num[5]["status"] == "COMPLETED"  # SAMPLE_COLLECTED
    assert stages_by_num[6]["status"] == "COMPLETED"  # SAMPLE_IN_TRANSIT
    assert stages_by_num[5]["details"]["depth_cm"] == 15.0

