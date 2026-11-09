import os
import sys
import tempfile
import json
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
        db_path = os.path.join(temp_dir, "test_expert_dispatch.db")
        app = create_app({
            "TESTING": True,
            "DATABASE": db_path,
            "SECRET_KEY": "test-expert-dispatch-key",
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
# EXPERT CONSULTATION TESTS
# ============================================================================

def test_expert_consultation_lifecycle(client, app):
    """
    1. Farmer posts consultation question.
    2. Advisor views queue and replies -> status ANSWERED.
    3. Farmer replies -> status IN_REVIEW.
    4. Farmer marks consultation CLOSED.
    """
    create_user(app, "Farmer Query", "+919876543501", role="farmer")
    create_user(app, "Dr. Swaminathan", "+919876543502", role="advisor")

    farmer_csrf = login(client, "+919876543501")

    # 1. Farmer creates consultation
    res_create = client.post(
        "/api/consultations",
        json={
            "subject": "Yellowing of paddy leaves in tillering stage",
            "category": "Pest Control",
            "question_text": "Leaves are turning pale yellow from the tip downwards. Field was fertilized with urea 10 days ago.",
        },
        headers={"X-CSRF-Token": farmer_csrf},
    )
    assert res_create.status_code == 201
    cid = res_create.get_json()["consultation_id"]

    # 2. Advisor checks queue
    advisor_csrf = login(client, "+919876543502")
    res_queue = client.get("/api/consultations?status=OPEN")
    assert res_queue.status_code == 200
    consultations = res_queue.get_json()["consultations"]
    assert any(c["id"] == cid for c in consultations)

    # Advisor replies
    res_reply1 = client.post(
        f"/api/consultations/{cid}/messages",
        json={"message_text": "Yellowing from the tip in tillering paddy typically indicates Zinc deficiency (Khaira disease) or Nitrogen leaching. Apply 25 kg/ha Zinc Sulphate mixed with sand."},
        headers={"X-CSRF-Token": advisor_csrf},
    )
    assert res_reply1.status_code == 201

    # Check status changed to ANSWERED
    res_get1 = client.get(f"/api/consultations/{cid}")
    assert res_get1.status_code == 200
    assert res_get1.get_json()["consultation"]["status"] == "ANSWERED"
    assert len(res_get1.get_json()["messages"]) == 2

    # 3. Farmer replies back
    farmer_csrf = login(client, "+919876543501")
    res_reply2 = client.post(
        f"/api/consultations/{cid}/messages",
        json={"message_text": "Thank you Dr. Swaminathan. Should I spray Zinc Sulphate or broadcast it into the water?"},
        headers={"X-CSRF-Token": farmer_csrf},
    )
    assert res_reply2.status_code == 201
    res_get2 = client.get(f"/api/consultations/{cid}")
    assert res_get2.get_json()["consultation"]["status"] == "IN_REVIEW"

    # 4. Farmer closes consultation
    res_close = client.post(f"/api/consultations/{cid}/close", headers={"X-CSRF-Token": farmer_csrf})
    assert res_close.status_code == 200
    res_get3 = client.get(f"/api/consultations/{cid}")
    assert res_get3.get_json()["consultation"]["status"] == "CLOSED"


# ============================================================================
# PHYSICAL REPORT DISPATCH TESTS
# ============================================================================

def test_physical_report_postal_dispatch_workflow(client, app):
    """
    1. Seed an authorized report with queued physical dispatch.
    2. Staff marks report printed -> Stage 12 (PHYSICAL_REPORT_PRINTED).
    3. Staff dispatches report with Speed Post tracking number -> Dispatched.
    4. Staff confirms delivery -> Stage 13 (REPORT_DELIVERED).
    """
    farmer_id = create_user(app, "Farmer Postal", "+919876543601", role="farmer")
    admin_id = create_user(app, "Admin Postal", "+919876543602", role="admin")

    with app.app_context():
        db = get_db()
        # Insert appointment
        cur_appt = db.execute(
            """
            INSERT INTO appointments (farmer_id, land_details, address, preferred_date, preferred_time, status)
            VALUES (?, '5 acres wetland', 'Village Green, Mandya', '2026-11-10', '09:00-12:00', 'Completed')
            """,
            (farmer_id,),
        )
        appt_id = cur_appt.lastrowid

        # Insert soil sample
        cur_smp = db.execute(
            """
            INSERT INTO soil_samples (appointment_id, sample_code, sample_status)
            VALUES (?, 'SMP-2026-09999', 'Completed')
            """,
            (appt_id,),
        )
        smp_id = cur_smp.lastrowid

        # Insert dispatch queued
        addr_snap = json.dumps({
            "recipient_name": "Farmer Postal",
            "house_details": "House #15",
            "street_or_village": "Maddur Road",
            "taluk": "Mandya",
            "district": "Mandya",
            "pincode": "571401",
        })
        cur_disp = db.execute(
            """
            INSERT INTO report_dispatches (
                report_id, appointment_id, recipient_name, recipient_phone,
                delivery_address_snapshot, courier_service, dispatch_status
            ) VALUES (NULL, ?, 'Farmer Postal', '+919876543601', ?, 'India Post Speed Post', 'Queued')
            """,
            (appt_id, addr_snap),
        )
        dispatch_id = cur_disp.lastrowid
        db.commit()

    admin_csrf = login(client, "+919876543602")

    # 1. Staff views queue
    res_q = client.get("/api/dispatch/queue?status=Queued")
    assert res_q.status_code == 200
    queue = res_q.get_json()["queue"]
    assert any(d["dispatch_id"] == dispatch_id for d in queue)

    # 2. Staff marks printed
    res_print = client.post(f"/api/dispatch/{dispatch_id}/print", headers={"X-CSRF-Token": admin_csrf})
    assert res_print.status_code == 200
    assert res_print.get_json()["dispatch_status"] == "Printed"

    # 3. Staff dispatches with Speed Post tracking number
    res_disp = client.post(
        f"/api/dispatch/{dispatch_id}/dispatch",
        json={"courier_service": "India Post Speed Post", "tracking_number": "EK987654321IN"},
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert res_disp.status_code == 200
    assert res_disp.get_json()["dispatch_status"] == "Dispatched"
    assert res_disp.get_json()["tracking_number"] == "EK987654321IN"

    # 4. Staff confirms postal delivery
    res_deliv = client.post(f"/api/dispatch/{dispatch_id}/deliver", headers={"X-CSRF-Token": admin_csrf})
    assert res_deliv.status_code == 200
    assert res_deliv.get_json()["dispatch_status"] == "Delivered"

    # 5. Verify timeline reaches Stage 13 REPORT_DELIVERED
    res_tl = client.get(f"/api/tracking/appointment/{appt_id}")
    assert res_tl.status_code == 200
    stages = {s["stage_number"]: s["status"] for s in res_tl.get_json()["timeline"]["stages"]}
    assert stages[12] == "COMPLETED"  # PHYSICAL_REPORT_PRINTED
    assert stages[13] == "COMPLETED"  # REPORT_DELIVERED
