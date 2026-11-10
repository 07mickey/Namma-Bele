#!/usr/bin/env python3
"""
Verification Script for Demonstration Workflows
Directly tests the demonstration database environment against all key operational workflows:
1. Farmer login and session authentication
2. Farmer appointment booking wizard
3. Admin approval and field worker assignment
4. Field worker on-site sample collection
5. Sample tracking timeline (13 stages)
6. Pre-seeded synthetic assay validation (pH 6.7, EC 0.32, OC 0.62%, N 245, P 18, K 210)
7. Laboratory assay entry & independent authorization (segregation of duties)
8. Farmer report access (secure PDF download)
9. Postal Speed Post dispatch recording (UPU S10 format)
10. Farm ledger, crop rotations, harvest stock & gross revenue calculations
11. Agricultural consultation Q&A threads (Answered & Open)
12. Multi-tenant privacy isolation between distinct farmers
13. Operator desk lookup and assisted registration audit logs
"""

import os
import sys
import json
import pytest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

from app import create_app
from app.db import get_db

DEMO_DB = os.path.join(PROJECT_ROOT, "instance", "demo_soil_testing.db")
DEMO_REPORTS = os.path.join(PROJECT_ROOT, "instance", "demo_reports")


def run_demo_verification():
    app = create_app({
        "TESTING": True,
        "DATABASE": DEMO_DB,
        "REPORT_FOLDER": DEMO_REPORTS,
        "SECRET_KEY": "demo-verification-key",
    })

    client = app.test_client()

    def get_csrf():
        res = client.get("/api/auth/csrf-token")
        assert res.status_code == 200
        return res.get_json()["csrf_token"]

    def login(phone, password="DemoUser@2026!"):
        csrf = get_csrf()
        res = client.post(
            "/api/auth/login",
            json={"phone": phone, "password": password},
            headers={"X-CSRF-Token": csrf},
        )
        assert res.status_code == 200, f"Login failed for {phone}: {res.get_json()}"
        return get_csrf()

    print("[*] Starting Verification of Demonstration Environment...")

    # 1. Farmer Login & Verification
    print("    [1/13] Verifying Farmer Login & Session...")
    csrf_farmer = login("+919999000001")
    res_me = client.get("/api/auth/me")
    assert res_me.status_code == 200
    user_info = res_me.get_json()["user"]
    assert user_info["name"] == "Demo Farmer Mallikarjuna"
    assert user_info["role"] == "farmer"
    print("           ✔ Farmer Mallikarjuna authenticated successfully")

    # 2. Farmer Appointment Booking Wizard
    print("    [2/13] Verifying Farmer Appointment Booking Wizard...")
    res_book = client.post(
        "/api/appointments",
        json={
            "land_details": "5.5 acres Red Loam near Canal",
            "address": "Kikkeri Village, Mandya",
            "delivery_address_id": 1,
            "plot_id": 1,
            "preferred_date": "2026-11-20",
            "preferred_time": "09:00-12:00",
        },
        headers={"X-CSRF-Token": csrf_farmer},
    )
    assert res_book.status_code == 201
    new_appt_id = res_book.get_json()["appointment"]["id"]
    assert res_book.get_json()["appointment"]["status"] == "Pending"
    print(f"           ✔ Appointment #{new_appt_id} booked in Pending status")

    # 3. Admin Approval & Field Worker Assignment
    print("    [3/13] Verifying Admin Approval & Assignment...")
    csrf_admin = login("+919999000008")
    res_appr = client.patch(
        f"/api/admin/appointments/{new_appt_id}/status",
        json={"status": "Approved"},
        headers={"X-CSRF-Token": csrf_admin},
    )
    assert res_appr.status_code == 200
    assert res_appr.get_json()["appointment"]["status"] == "Approved"

    res_assign = client.post(
        f"/api/admin/appointments/{new_appt_id}/assign",
        json={"worker_id": 4, "scheduled_date": "2026-11-20", "scheduled_slot": "09:00-12:00"},
        headers={"X-CSRF-Token": csrf_admin},
    )
    assert res_assign.status_code == 200
    visit_id = res_assign.get_json()["visit_id"]
    print(f"           ✔ Appointment #{new_appt_id} approved and assigned to Field Worker Ravi Kumar (Visit #{visit_id})")

    # 4. Field Worker Sample Collection
    print("    [4/13] Verifying Field Worker On-Site Sample Collection...")
    csrf_worker = login("+919999000004")
    res_collect = client.post(
        f"/api/field-worker/visits/{visit_id}/collect",
        json={
            "sampling_depth_cm": 15.0,
            "soil_appearance": "Red Sandy Loam, composite core",
            "survey_number": "DEMO-MND-001",
            "worker_notes": "Sampled at 8 points.",
        },
        headers={"X-CSRF-Token": csrf_worker},
    )
    assert res_collect.status_code == 200
    sample_code = res_collect.get_json()["sample_code"]
    assert sample_code.startswith("SMP-")
    print(f"           ✔ Field worker logged collection; unique sample code generated: {sample_code}")

    # 5. Sample Tracking Timeline (13 Stages)
    print("    [5/13] Verifying 13-Stage Timeline Generation...")
    csrf_farmer = login("+919999000001")
    res_tl1 = client.get("/api/tracking/appointment/1")
    assert res_tl1.status_code == 200
    tl1 = res_tl1.get_json()["timeline"]
    assert tl1["current_stage"] == 13
    assert tl1["current_stage_name"] == "REPORT_DELIVERED"
    assert len(tl1["stages"]) == 13
    assert tl1["dispatch"]["tracking_number"] == "EM123456789IN"
    print("           ✔ Verified complete 13-stage timeline on Appointment #1")

    # 6. Verify Pre-Seeded Synthetic Assay (Sample 3 / Appointment 5)
    print("    [6/13] Verifying Pre-Seeded Synthetic Assay in Lab Queue...")
    csrf_analyst = login("+919999000005")
    with app.app_context():
        db = get_db()
        assay_row = db.execute(
            "SELECT * FROM lab_test_assays WHERE id = 2"
        ).fetchone()
        assert assay_row is not None
        assert assay_row["ph_value"] == 6.70
        assert assay_row["ec_ds_m"] == 0.32
        assert assay_row["organic_carbon_pct"] == 0.62
        assert assay_row["nitrogen_kg_ha"] == 245.0
        assert assay_row["phosphorus_kg_ha"] == 18.0
        assert assay_row["potassium_kg_ha"] == 210.0
        assert assay_row["lab_status"] == "Submitted"
        assert assay_row["n_rating"] == "Low"
    print("           ✔ Verified pre-seeded assay (pH 6.7, EC 0.32, OC 0.62%, N 245, P 18, K 210, Status: Submitted)")

    # 7. Laboratory Assay Entry & Segregation of Duties Authorization
    print("    [7/13] Verifying Laboratory Assay Entry & Segregation of Duties...")
    with app.app_context():
        db = get_db()
        sample_row = db.execute("SELECT id FROM soil_samples WHERE appointment_id = ?", (new_appt_id,)).fetchone()
        new_sample_id = sample_row["id"]

    res_assay = client.post(
        f"/api/lab/samples/{new_sample_id}/assay",
        json={
            "ph_value": 7.3,
            "ec_ds_m": 0.40,
            "organic_carbon_pct": 0.65,
            "nitrogen_kg_ha": 315.0,
            "phosphorus_kg_ha": 30.0,
            "potassium_kg_ha": 230.0,
            "remarks": "Live demo assay verification.",
        },
        headers={"X-CSRF-Token": csrf_analyst},
    )
    assert res_assay.status_code == 201
    assay_id = res_assay.get_json()["assay_id"]

    # Analyst attempting self-approval -> Denied 403
    res_denied = client.post(f"/api/lab/assays/{assay_id}/authorize", headers={"X-CSRF-Token": csrf_analyst})
    assert res_denied.status_code == 403
    assert "Segregation of duties" in res_denied.get_json()["error"]["message"]
    print("           ✔ Self-approval correctly blocked under segregation of duties")

    # Independent supervisor authorizes -> 200
    csrf_sup = login("+919999000006")
    res_auth = client.post(f"/api/lab/assays/{assay_id}/authorize", headers={"X-CSRF-Token": csrf_sup})
    assert res_auth.status_code == 200
    assert res_auth.get_json()["lab_status"] == "Authorized"
    print("           ✔ Independent supervisor Dr. Patil authorized report successfully")

    # 8. Farmer Report Access & PDF Download
    print("    [8/13] Verifying Farmer Report Access & PDF Download...")
    csrf_farmer = login("+919999000001")
    res_meta = client.get("/api/appointments/1/report")
    assert res_meta.status_code == 200
    report_info = res_meta.get_json()["report"]
    assert report_info["original_filename"] == "Soil_Health_Card_SMP_2026_00001.pdf"

    res_dl = client.get("/api/appointments/1/report/download")
    assert res_dl.status_code == 200
    assert res_dl.mimetype == "application/pdf"
    assert res_dl.data.startswith(b"%PDF-")
    assert b"DEMONSTRATION RECORD" in res_dl.data
    assert res_dl.headers.get("X-Content-Type-Options") == "nosniff"
    print(f"           ✔ Streamed PDF report successfully with security headers & demo watermark ({len(res_dl.data)} bytes)")

    # 9. Postal Dispatch Recording
    print("    [9/13] Verifying Postal Speed Post Dispatch & Delivery...")
    csrf_admin = login("+919999000008")
    with app.app_context():
        db = get_db()
        disp_row = db.execute("SELECT id FROM report_dispatches WHERE appointment_id = ?", (new_appt_id,)).fetchone()
        new_disp_id = disp_row["id"]

    res_print = client.post(f"/api/dispatch/{new_disp_id}/print", headers={"X-CSRF-Token": csrf_admin})
    assert res_print.status_code == 200

    res_disp = client.post(
        f"/api/dispatch/{new_disp_id}/dispatch",
        json={"courier_service": "India Post Speed Post", "tracking_number": "EM987654321IN"},
        headers={"X-CSRF-Token": csrf_admin},
    )
    assert res_disp.status_code == 200
    assert res_disp.get_json()["tracking_number"] == "EM987654321IN"
    print("           ✔ Dispatched via India Post Speed Post with verified UPU S10 barcode")

    # 10. Farm Ledger, Crop Rotations & Sales Calculations
    print("    [10/13] Verifying Farm Plots, Crop Rotations & Revenue Ledger...")
    csrf_farmer = login("+919999000001")
    res_summary = client.get("/api/farm/summary")
    assert res_summary.status_code == 200
    summary = res_summary.get_json()
    assert summary["total_plots"] == 2
    assert summary["active_crops_count"] == 3
    assert summary["total_harvested_quantity"] == 155.0  # 120 Paddy + 35 Wheat
    assert summary["total_sold_quantity"] == 58.0        # 48 Paddy + 10 Wheat
    assert summary["remaining_stock"] == 97.0            # 72 Paddy + 25 Wheat
    assert summary["total_gross_revenue"] == 131500.0    # 106,500 + 25,000
    print(f"           ✔ Verified revenue ledger: ₹{summary['total_gross_revenue']:,.2f} gross revenue, {summary['remaining_stock']} Quintals remaining stock")

    # 11. Agricultural Consultation Threads (Answered & Open)
    print("    [11/13] Verifying Expert Consultation Threads...")
    res_consult1 = client.get("/api/consultations/1")
    assert res_consult1.status_code == 200
    c_data1 = res_consult1.get_json()
    assert c_data1["consultation"]["status"] == "ANSWERED"
    assert c_data1["consultation"]["assigned_advisor_id"] == 7
    assert len(c_data1["messages"]) == 2
    assert "MOP (Muriate of Potash)" in c_data1["messages"][1]["message_text"]

    # Advisor checks consultations queue
    csrf_adv = login("+919999000007")
    res_adv_list = client.get("/api/consultations")
    assert res_adv_list.status_code == 200
    adv_consultations = res_adv_list.get_json()["consultations"]
    open_cases = [c for c in adv_consultations if c["status"] == "OPEN"]
    assert len(open_cases) >= 1
    print(f"           ✔ Verified consultation threads: 1 Answered thread and {len(open_cases)} Open thread awaiting advisor response")

    # 12. Multi-Tenant Privacy Isolation
    print("    [12/13] Verifying Multi-Tenant Privacy Isolation...")
    csrf_farmer_b = login("+919999000009")  # Shivalingappa
    res_b_plots = client.get("/api/farm/plots")
    assert res_b_plots.status_code == 200
    b_plots = res_b_plots.get_json()["plots"]
    assert len(b_plots) == 1
    assert b_plots[0]["plot_name"] == "Dryland Ragi Field"
    # Attempt to access Farmer A's appointment details -> Should return 404/403
    res_unauth = client.get("/api/appointments/1")
    assert res_unauth.status_code in (403, 404)
    print("           ✔ Multi-tenant privacy verified: Farmer B cannot view Farmer A's plots or appointments")

    # 13. Operator Desk Lookup & Assisted Registration Records
    print("    [13/13] Verifying Operator Desk Lookup & Assisted Registrations...")
    csrf_op = login("+919999000003")  # Pooja
    res_search = client.get("/api/operator/farmers/search?phone=%2B919999000002")
    assert res_search.status_code == 200
    search_data = res_search.get_json()
    assert len(search_data["farmers"]) >= 1
    farmer_c = search_data["farmers"][0]
    assert farmer_c["name"] == "Demo Assisted Farmer Chennamma"
    assert farmer_c["account_status"] == "UNCLAIMED"
    print("           ✔ Operator desk successfully searched assisted farmer Chennamma (Status: UNCLAIMED)")

    print("\n[🎉] ALL 13 DEMONSTRATION WORKFLOWS EMPIRICALLY VERIFIED AGAINST DEMO DATABASE!")


if __name__ == "__main__":
    run_demo_verification()
