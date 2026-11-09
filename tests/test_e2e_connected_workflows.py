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
        db_path = os.path.join(temp_dir, "test_e2e_connected.db")
        app = create_app({
            "TESTING": True,
            "DATABASE": db_path,
            "SECRET_KEY": "test-e2e-connected-key",
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


def login(client, phone, password="Password123"):
    csrf = get_csrf(client)
    res = client.post(
        "/api/auth/login",
        json={"phone": phone, "password": password},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    return get_csrf(client)


# ============================================================================
# COMPREHENSIVE CONNECTED END-TO-END WORKFLOWS (A through F)
# ============================================================================

def test_complete_connected_agricultural_lifecycle(client, app):
    """
    Executes connected workflows A through F sequentially:
    - Workflow A: Farmer registration & booking
    - Workflow B: Admin approval, field worker assignment & on-site sample collection
    - Workflow C: Laboratory intake, chemical assay analysis & scientific authorization
    - Workflow D: Print queue, India Post Speed Post consignment dispatch & delivery
    - Workflow E: Plot creation, crop rotation history, harvest yield & gross sales revenue
    - Workflow F: Expert advisory question submission & agronomist recommendation thread
    """
    # 0. Set up actors
    admin_id = create_user(app, "Chief Coordinator", "+919876543600", role="admin")
    worker_id = create_user(app, "Technician Manjunath", "+919876543601", role="field_worker")
    analyst_id = create_user(app, "Lab Analyst Shruthi", "+919876543602", role="lab_staff")
    supervisor_id = create_user(app, "Lab Supervisor Dr. Patil", "+919876543603", role="lab_staff")
    advisor_id = create_user(app, "Agronomist Dr. Hegde", "+919876543604", role="advisor")

    # ------------------------------------------------------------------------
    # WORKFLOW A — Farmer Registration, Login, Address & Booking
    # ------------------------------------------------------------------------
    csrf = get_csrf(client)
    res_reg = client.post(
        "/api/auth/register",
        json={
            "name": "Basavaraju M",
            "phone": "+919876543610",
            "password": "FarmerPassword123",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res_reg.status_code == 201
    farmer_id = res_reg.get_json()["user"]["id"]

    # Farmer logs in
    csrf_f = get_csrf(client)
    res_login = client.post(
        "/api/auth/login",
        json={"phone": "+919876543610", "password": "FarmerPassword123"},
        headers={"X-CSRF-Token": csrf_f},
    )
    assert res_login.status_code == 200
    csrf_f = get_csrf(client)

    # Save postal delivery address (separated from land)
    res_addr = client.post(
        f"/api/farmers/{farmer_id}/delivery-addresses",
        json={
            "recipient_name": "Basavaraju M",
            "recipient_phone": "+919876543610",
            "house_details": "House #15, Main Road",
            "street_or_village": "Kikkeri Village",
            "taluk": "KR Pet",
            "district": "Mandya",
            "state": "Karnataka",
            "pincode": "571423",
            "is_default": True,
        },
        headers={"X-CSRF-Token": csrf_f},
    )
    assert res_addr.status_code == 201
    address_id = res_addr.get_json()["address"]["id"]

    # Farmer books appointment linking land location & delivery address
    future_date = (date.today() + timedelta(days=2)).isoformat()
    res_appt = client.post(
        "/api/appointments",
        json={
            "land_details": "5.5 acres Canal-irrigated Black Clay, Survey 108",
            "address": "Kikkeri Village, KR Pet, Mandya - 571423",
            "delivery_address_id": address_id,
            "preferred_date": future_date,
            "preferred_time": "09:00-12:00",
        },
        headers={"X-CSRF-Token": csrf_f},
    )
    assert res_appt.status_code == 201
    appt_id = res_appt.get_json()["appointment"]["id"]

    # Verify Stage 1 APPOINTMENT_REQUESTED
    res_tl1 = client.get(f"/api/tracking/appointment/{appt_id}")
    assert res_tl1.status_code == 200
    assert res_tl1.get_json()["timeline"]["current_stage"] >= 1

    # ------------------------------------------------------------------------
    # WORKFLOW B — Field Operations: Approval, Worker Assignment & Sampling
    # ------------------------------------------------------------------------
    csrf_admin = login(client, "+919876543600")

    # Admin approves appointment
    res_appr = client.patch(
        f"/api/admin/appointments/{appt_id}/status",
        json={"status": "Approved"},
        headers={"X-CSRF-Token": csrf_admin},
    )
    assert res_appr.status_code == 200

    # Admin assigns field worker
    res_assign = client.post(
        f"/api/admin/appointments/{appt_id}/assign",
        json={"worker_id": worker_id, "scheduled_date": future_date, "scheduled_slot": "09:00-12:00"},
        headers={"X-CSRF-Token": csrf_admin},
    )
    assert res_assign.status_code == 200
    visit_id = res_assign.get_json()["visit_id"]

    # Field worker logs in, inspects assigned visit, and logs on-site collection
    csrf_w = login(client, "+919876543601")
    res_w_visits = client.get("/api/field-worker/visits")
    assert res_w_visits.status_code == 200
    assert len(res_w_visits.get_json()["visits"]) == 1

    res_collect = client.post(
        f"/api/field-worker/visits/{visit_id}/collect",
        json={
            "sampling_depth_cm": 15.0,
            "soil_appearance": "Black Clay Loam, moist composite",
            "survey_number": "108/2A",
            "worker_notes": "6 zigzag cores sampled across 5.5 acres.",
        },
        headers={"X-CSRF-Token": csrf_w},
    )
    assert res_collect.status_code == 200
    sample_code = res_collect.get_json()["sample_code"]
    assert sample_code.startswith("SMP-")

    # ------------------------------------------------------------------------
    # WORKFLOW C — Laboratory: Intake, Chemical Assay & Dual-Signoff Review
    # ------------------------------------------------------------------------
    csrf_tech = login(client, "+919876543602")

    # Lab intake
    res_samples = client.get("/api/lab/samples")
    assert res_samples.status_code == 200
    s_entry = [s for s in res_samples.get_json()["samples"] if s["appointment_id"] == appt_id][0]
    sample_id = s_entry["sample_id"]

    res_rcv = client.post(f"/api/lab/samples/{sample_id}/receive", headers={"X-CSRF-Token": csrf_tech})
    assert res_rcv.status_code == 200

    # Lab commences testing
    res_test = client.post(f"/api/lab/samples/{sample_id}/start-test", headers={"X-CSRF-Token": csrf_tech})
    assert res_test.status_code == 200

    # Lab records quantitative assay
    res_assay = client.post(
        f"/api/lab/samples/{sample_id}/assay",
        json={
            "ph_value": 7.4,
            "ec_ds_m": 0.55,
            "organic_carbon_pct": 0.72,
            "nitrogen_kg_ha": 340.0,
            "phosphorus_kg_ha": 32.0,
            "potassium_kg_ha": 260.0,
            "remarks": "Slightly alkaline fertile soil with balanced nutrient indices.",
        },
        headers={"X-CSRF-Token": csrf_tech},
    )
    assert res_assay.status_code == 201
    assay_id = res_assay.get_json()["assay_id"]

    # Supervisor performs independent review and authorizes report (Stage 11)
    csrf_sup = login(client, "+919876543603")
    res_auth = client.post(f"/api/lab/assays/{assay_id}/authorize", headers={"X-CSRF-Token": csrf_sup})
    assert res_auth.status_code == 200
    assert res_auth.get_json()["lab_status"] == "Authorized"

    # ------------------------------------------------------------------------
    # WORKFLOW D — Physical Postal Dispatch: Print, Consignment & Delivery
    # ------------------------------------------------------------------------
    csrf_admin = login(client, "+919876543600")

    # Check print queue
    res_q = client.get("/api/dispatch/queue?status=Queued")
    assert res_q.status_code == 200
    d_entry = [d for d in res_q.get_json()["queue"] if d["appointment_id"] == appt_id][0]
    dispatch_id = d_entry["dispatch_id"]

    # Mark printed (Stage 12)
    res_print = client.post(f"/api/dispatch/{dispatch_id}/print", headers={"X-CSRF-Token": csrf_admin})
    assert res_print.status_code == 200

    # Handover to Speed Post with verified UPU S10 consignment barcode
    res_disp = client.post(
        f"/api/dispatch/{dispatch_id}/dispatch",
        json={"courier_service": "India Post Speed Post", "tracking_number": "EM765432109IN"},
        headers={"X-CSRF-Token": csrf_admin},
    )
    assert res_disp.status_code == 200
    assert res_disp.get_json()["tracking_number"] == "EM765432109IN"

    # Delivery confirmation (Stage 13)
    res_deliv = client.post(f"/api/dispatch/{dispatch_id}/deliver", headers={"X-CSRF-Token": csrf_admin})
    assert res_deliv.status_code == 200

    # Farmer verifies complete 13-stage timeline
    csrf_f = login(client, "+919876543610", password="FarmerPassword123")
    res_final_tl = client.get(f"/api/tracking/appointment/{appt_id}")
    assert res_final_tl.status_code == 200
    tl = res_final_tl.get_json()["timeline"]
    assert tl["current_stage"] == 13
    assert tl["current_stage_name"] == "REPORT_DELIVERED"
    assert tl["dispatch"]["tracking_number"] == "EM765432109IN"

    # ------------------------------------------------------------------------
    # WORKFLOW E — Farm Plots, Crop History, Harvests & Revenue
    # ------------------------------------------------------------------------
    # 1. Create farm plot
    res_plot = client.post(
        "/api/farm/plots",
        json={
            "plot_name": "Canal Side Acre",
            "survey_number": "108/2A",
            "area": 5.5,
            "area_unit": "Acres",
            "soil_type": "Clay Loam",
            "irrigation_source": "Canal",
            "taluk": "KR Pet",
            "district": "Mandya",
        },
        headers={"X-CSRF-Token": csrf_f},
    )
    assert res_plot.status_code == 201
    plot_id = res_plot.get_json()["plot"]["id"]

    # 2. Add crop record with non-standard name variant "paddy bhatta" -> normalized to "Paddy / Rice"
    res_crop = client.post(
        "/api/farm/crops",
        json={
            "plot_id": plot_id,
            "crop_name": "paddy bhatta",
            "variety": "JGL 1798",
            "season": "Kharif",
            "year": 2026,
            "sowing_date": "2026-06-15",
        },
        headers={"X-CSRF-Token": csrf_f},
    )
    assert res_crop.status_code == 201
    assert res_crop.get_json()["crop_name"] == "Paddy / Rice"
    crop_id = res_crop.get_json()["crop_id"]

    # 3. Log harvest record
    res_harv = client.post(
        "/api/farm/harvests",
        json={
            "crop_record_id": crop_id,
            "harvest_date": "2026-10-25",
            "total_quantity": 120.0,
            "quantity_unit": "Quintals",
            "storage_location": "Village Warehouse Bay 4",
        },
        headers={"X-CSRF-Token": csrf_f},
    )
    assert res_harv.status_code == 201
    harvest_id = res_harv.get_json()["harvest_id"]

    # 4. Record sales transaction: 50 Quintals @ Rs 2,300/Quintal -> Gross Revenue = Rs 115,000
    res_sale = client.post(
        "/api/farm/sales",
        json={
            "crop_record_id": crop_id,
            "buyer_market": "Mandya APMC Market Yard",
            "sale_date": "2026-11-01",
            "quantity_sold": 50.0,
            "price_per_unit": 2300.0,
        },
        headers={"X-CSRF-Token": csrf_f},
    )
    assert res_sale.status_code == 201
    sale_data = res_sale.get_json()
    assert sale_data["gross_revenue"] == 115000.0
    assert sale_data["remaining_stock"] == 70.0

    # 5. Verify remaining stock: 120 - 50 = 70 Quintals
    res_farm_sum = client.get("/api/farm/summary")
    assert res_farm_sum.status_code == 200
    sum_data = res_farm_sum.get_json()
    assert sum_data["total_gross_revenue"] == 115000.0
    assert sum_data["total_harvested_quantity"] == 120.0
    assert sum_data["total_sold_quantity"] == 50.0
    assert sum_data["remaining_stock"] == 70.0

    # ------------------------------------------------------------------------
    # WORKFLOW F — Agricultural Expert Consultation
    # ------------------------------------------------------------------------
    # Farmer asks a question
    res_q = client.post(
        "/api/consultations",
        json={
            "plot_id": plot_id,
            "category": "Fertilizer Application",
            "subject": "Yellowing leaf tips in Kharif Paddy",
            "question_text": "Observed slight yellowing on lower leaves after recent rain. Need fertilizer guidance.",
        },
        headers={"X-CSRF-Token": csrf_f},
    )
    assert res_q.status_code == 201
    consultation_id = res_q.get_json()["consultation_id"]

    # Agronomist advisor reviews and responds
    csrf_adv = login(client, "+919876543604")
    res_adv_reply = client.post(
        f"/api/consultations/{consultation_id}/messages",
        json={
            "message_text": "Based on your laboratory soil report (pH 7.4, medium nitrogen), apply 25 kg/acre urea top-dressing with adequate soil moisture. Avoid waterlogging."
        },
        headers={"X-CSRF-Token": csrf_adv},
    )
    assert res_adv_reply.status_code == 201

    # Farmer views response in consultation thread
    csrf_f = login(client, "+919876543610", password="FarmerPassword123")
    res_thread = client.get(f"/api/consultations/{consultation_id}")
    assert res_thread.status_code == 200
    thread_data = res_thread.get_json()
    assert len(thread_data["messages"]) == 2
    assert thread_data["consultation"]["status"] == "ANSWERED"
    assert "urea top-dressing" in thread_data["messages"][1]["message_text"]
