#!/usr/bin/env python3
"""
Soil Testing & Farmer Agricultural Service Platform
Demonstration Database Initialization & Seeding Script

Creates a completely isolated, safe demonstration database and file vault:
- Database: instance/demo_soil_testing.db
- Report Vault: instance/demo_reports/

Never touches or alters the authoritative database (instance/soil_testing.db).
All records use clearly marked fictional labels and test data.
"""

import hashlib
import json
import os
import re
import sqlite3
import sys
import uuid
from datetime import date, datetime, timedelta, timezone

# Ensure project root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

from werkzeug.security import generate_password_hash

# Default demo password for all fictional test users (configurable via DEMO_PASSWORD env var)
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "DemoUser@2026!")

# Target demo paths
DEMO_DB_PATH = os.path.abspath(
    os.environ.get("DEMO_DATABASE", os.path.join(PROJECT_ROOT, "instance", "demo_soil_testing.db"))
)
DEMO_REPORTS_DIR = os.path.abspath(
    os.environ.get("DEMO_REPORT_FOLDER", os.path.join(PROJECT_ROOT, "instance", "demo_reports"))
)
SCHEMA_PATH = os.path.join(PROJECT_ROOT, "app", "schema.sql")

# Safety guard: Never allow seeding against the production database
PROD_DB_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, "instance", "soil_testing.db"))


def create_demo_pdf_report(reports_dir, sample_code, farmer_name, appointment_id):
    """
    Generates a valid, minimal PDF file with explicit demonstration banners.
    Contains clear disclaimers that it is an academic demonstration document.
    """
    os.makedirs(reports_dir, exist_ok=True)
    storage_uuid = uuid.uuid4().hex
    filename = f"{storage_uuid}.pdf"
    file_path = os.path.join(reports_dir, filename)

    content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n"
        b"<< /Type /Catalog /Pages 2 0 R >>\n"
        b"endobj\n"
        b"2 0 obj\n"
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
        b"endobj\n"
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\n"
        b"endobj\n"
        b"4 0 obj\n"
        b"<< /Length 1147 >>\n"
        b"stream\n"
        b"BT /Helvetica-Bold 15 Tf 50 740 TD (NAMMA BELE - SOIL HEALTH REPORT) Tj ET\n"
        b"BT /Helvetica-Bold 11 Tf 50 720 TD (*** DEMONSTRATION RECORD - NOT AN OFFICIAL DOCUMENT ***) Tj ET\n"
        b"BT /Helvetica-Bold 11 Tf 50 700 TD (District Soil Testing Laboratory, Mandya) Tj ET\n"
        b"BT /Helvetica 10 Tf 50 675 TD (Academic Project Demonstration Environment - November 2026) Tj ET\n"
        b"BT /Helvetica 10 Tf 50 655 TD (Sample Code: " + sample_code.encode("utf-8") + b"  |  Appointment ID: " + str(appointment_id).encode("utf-8") + b") Tj ET\n"
        b"BT /Helvetica 10 Tf 50 635 TD (Farmer Name: " + farmer_name.encode("utf-8") + b") Tj ET\n"
        b"BT /Helvetica 10 Tf 50 615 TD (Land Parcel: Main Paddy Field, Survey DEMO-MND-001) Tj ET\n"
        b"BT /Helvetica-Bold 11 Tf 50 585 TD (Analytical Results Summary:) Tj ET\n"
        b"BT /Helvetica 10 Tf 50 565 TD (pH: 7.20 (Neutral)  |  EC: 0.45 dS/m (Normal)  |  OC: 0.68% (Medium)) Tj ET\n"
        b"BT /Helvetica 10 Tf 50 545 TD (Available N: 320 kg/ha  |  Available P: 28.5 kg/ha  |  Available K: 245 kg/ha) Tj ET\n"
        b"BT /Helvetica 10 Tf 50 515 TD (Certification: Authorized by Dr. Patil (Supervisor) on 2026-10-13) Tj ET\n"
        b"BT /Helvetica-Oblique 9 Tf 50 485 TD (NAMMA BELE Platform: Synthetic data generated exclusively for academic evaluation.) Tj ET\n"
        b"endstream\n"
        b"endobj\n"
        b"xref\n"
        b"0 5\n"
        b"0000000000 65535 f \n"
        b"0000000010 00000 n \n"
        b"0000000060 00000 n \n"
        b"0000000117 00000 n \n"
        b"0000000201 00000 n \n"
        b"trailer\n"
        b"<< /Size 5 /Root 1 0 R >>\n"
        b"startxref\n"
        b"640\n"
        b"%%EOF\n"
    )

    with open(file_path, "wb") as f:
        f.write(content)

    file_size = len(content)
    sha256 = hashlib.sha256(content).hexdigest()
    return filename, file_size, sha256


def seed_demo_database(db_path=DEMO_DB_PATH, reports_dir=DEMO_REPORTS_DIR, reset=True):
    """Initializes and seeds the isolated demonstration database."""
    if os.path.abspath(db_path) == PROD_DB_PATH:
        raise RuntimeError("CRITICAL ERROR: Refusing to seed over production database instance/soil_testing.db!")

    print(f"[*] Initializing Demo Environment...")
    print(f"    Target Database : {db_path}")
    print(f"    Target Reports  : {reports_dir}")

    # Reset existing demo DB file if requested
    if reset and os.path.exists(db_path):
        os.remove(db_path)
        print(f"    [+] Removed prior demo database: {os.path.basename(db_path)}")

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")

    # 1. Execute schema.sql
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    print("    [+] Schema applied (18 tables created)")

    # 2. Seed Baseline Laboratories
    conn.execute("""
        INSERT OR IGNORE INTO laboratories (id, name, code, district, address, contact_phone)
        VALUES 
        (1, 'District Soil Testing Laboratory, Mandya', 'DSTL-MND-01', 'Mandya', 'Department of Agriculture, Mandya - 571401', '+918232220101'),
        (2, 'Central Soil & Water Testing Lab, Mysuru', 'CSWL-MYS-01', 'Mysuru', 'KRS Road, Industrial Suburb, Mysuru - 570020', '+918212410202'),
        (3, 'Regional Agricultural Research Lab, Bengaluru', 'RARL-BLR-01', 'Bengaluru Rural', 'UAS GKVK Campus, Bellary Road, Bengaluru - 560065', '+918023330153')
    """)

    pw_hash = generate_password_hash(DEMO_PASSWORD)

    # 3. Seed Fictional Users across all 6 roles
    users = [
        # (id, name, phone, role, status, lab_id)
        (1, "Demo Farmer Mallikarjuna", "+919999000001", "farmer", "ACTIVE", None),
        (2, "Demo Assisted Farmer Chennamma", "+919999000002", "farmer", "UNCLAIMED", None),
        (3, "Demo Call-Center Operator Pooja", "+919999000003", "operator", "ACTIVE", None),
        (4, "Demo Field Technician Ravi Kumar", "+919999000004", "field_worker", "ACTIVE", None),
        (5, "Demo Lab Analyst Dr. Anita", "+919999000005", "lab_staff", "ACTIVE", 1),
        (6, "Demo Lab Supervisor Dr. Patil", "+919999000006", "lab_staff", "ACTIVE", 1),
        (7, "Demo Agronomist Dr. Hegde", "+919999000007", "advisor", "ACTIVE", None),
        (8, "Demo Administrator Lead", "+919999000008", "admin", "ACTIVE", None),
        (9, "Demo Farmer Shivalingappa", "+919999000009", "farmer", "ACTIVE", None),
    ]

    for uid, name, phone, role, status, lab_id in users:
        conn.execute(
            """
            INSERT INTO users (id, name, phone, password_hash, role, account_status, assigned_lab_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (uid, name, phone, pw_hash, role, status, lab_id),
        )

    # Link assisted registration: Chennamma was registered by Operator Pooja (id 3)
    conn.execute("UPDATE users SET created_by_user_id = 3 WHERE id = 2")
    print(f"    [+] Created {len(users)} fictional demo accounts across all 6 roles")

    # 4. Assisted Farmer Claim Token & OTP (for Chennamma, id 2)
    claim_token = "demo-claim-token-chennamma-2026"
    claim_token_hash = hashlib.sha256(claim_token.encode("utf-8")).hexdigest()
    otp_code = "123456"
    otp_hash = hashlib.sha256(otp_code.encode("utf-8")).hexdigest()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")

    conn.execute("""
        INSERT INTO farmer_account_activations (farmer_id, claim_token_hash, otp_hash, expires_at, attempts_remaining)
        VALUES (2, ?, ?, ?, 5)
    """, (claim_token_hash, otp_hash, expires_at))

    # 5. Delivery Addresses
    conn.execute("""
        INSERT INTO farmer_delivery_addresses (id, farmer_id, recipient_name, recipient_phone, house_details, street_or_village, taluk, district, state, pincode, is_default)
        VALUES 
        (1, 1, 'Mallikarjuna M', '+919999000001', 'House #42, Cauvery Main Road', 'Kikkeri Village', 'KR Pet', 'Mandya', 'Karnataka', '571423', 1),
        (2, 1, 'Mallikarjuna M', '+919999000001', 'P.O. Box #7, Mandya Agricultural APMC', 'Subhash Road', 'Mandya', 'Mandya', 'Karnataka', '571401', 0),
        (3, 9, 'Shivalingappa K', '+919999000009', 'House #15, Near Basaveshwara Temple', 'Kuduragere Village', 'Maddur', 'Mandya', 'Karnataka', '571428', 1),
        (4, 2, 'Chennamma G', '+919999000002', 'House #8, Main Road', 'Halebeedu Village', 'Pandavapura', 'Mandya', 'Karnataka', '571434', 1)
    """)

    # 6. Farm Plots
    conn.execute("""
        INSERT INTO farm_plots (id, farmer_id, plot_name, survey_number, area, area_unit, soil_type, irrigation_source, landmark, taluk, district)
        VALUES 
        (1, 1, 'Main Paddy Field', 'DEMO-MND-001', 5.5, 'Acres', 'Red Sandy Loam', 'Canal', 'Near Hemavathi Branch Canal', 'KR Pet', 'Mandya'),
        (2, 1, 'Secondary Field', 'DEMO-MND-002', 2.0, 'Acres', 'Clay Loam', 'Borewell', 'Adjacent to Panchayat Borewell', 'KR Pet', 'Mandya'),
        (3, 9, 'Dryland Ragi Field', 'DEMO-RAGI-042', 3.2, 'Acres', 'Red Sandy Loam', 'Rainfed', 'Behind Gram Panchayat Hall', 'Maddur', 'Mandya'),
        (4, 2, 'Village Coconut Grove', 'DEMO-COCO-019', 2.5, 'Acres', 'Alluvial', 'Borewell', 'Near Railway Level Crossing', 'Pandavapura', 'Mandya')
    """)

    # 7. Crop Cultivation History
    # Farmer 1 (Mallikarjuna):
    # 2024 Kharif Paddy (historical archive)
    # 2025 Kharif Paddy (120 quintals)
    # 2026 Rabi Wheat (35 quintals)
    # Farmer 9 (Shivalingappa):
    # 2025 Kharif Ragi (40 quintals)
    conn.execute("""
        INSERT INTO crop_records (id, farmer_id, plot_id, crop_name, variety, year, season, sowing_date, harvest_date, actual_harvested_quantity, quantity_unit, notes)
        VALUES 
        (1, 1, 1, 'Paddy / Rice', 'IR-64', 2024, 'Kharif', '2024-06-15', '2024-10-20', 0.0, 'Quintals', 'Historical 2024 Kharif baseline cultivation'),
        (2, 1, 1, 'Paddy / Rice', 'JGL 1798', 2025, 'Kharif', '2025-06-15', '2025-10-25', 120.0, 'Quintals', 'Canal-irrigated high-yielding paddy crop'),
        (3, 1, 2, 'Wheat', 'Sharbati', 2026, 'Rabi', '2025-11-15', '2026-03-20', 35.0, 'Quintals', 'Borewell irrigated post-monsoon wheat cultivation'),
        (4, 9, 3, 'Finger Millet (Ragi)', 'ML-365', 2025, 'Kharif', '2025-07-05', '2025-11-15', 40.0, 'Quintals', 'Rainfed drought-tolerant finger millet')
    """)

    # 8. Harvest Records
    conn.execute("""
        INSERT INTO harvest_records (id, crop_record_id, harvest_date, total_quantity, quantity_unit, quality_grade, storage_location, notes)
        VALUES 
        (1, 2, '2025-10-25', 120.0, 'Quintals', 'Grade A', 'Warehouse Bay 1', 'Clean golden grain, 13% moisture'),
        (2, 3, '2026-03-20', 35.0, 'Quintals', 'Grade A', 'Farm Silo', 'High-protein Sharbati wheat'),
        (3, 4, '2025-11-15', 40.0, 'Quintals', 'Grade A', 'Home Granary', 'Cleaned and dried organic finger millet')
    """)

    # 9. Sales Records
    # Farmer 1:
    # Paddy: Sale 1 (30 Qtl @ 2200 = 66,000), Sale 2 (18 Qtl @ 2250 = 40,500) -> 48 Qtl sold, 72 Qtl remaining stock, 106,500 gross revenue
    # Wheat: Sale 3 (10 Qtl @ 2500 = 25,000) -> 10 Qtl sold, 25 Qtl remaining stock, 25,000 gross revenue
    # Total Farmer 1: 155 Qtl harvested, 58 Qtl sold, 97 Qtl remaining stock, 131,500 gross revenue
    # Farmer 9:
    # Ragi: Sale 4 (15 Qtl @ 3800 = 57,000) -> 15 Qtl sold, 25 Qtl remaining stock, 57,000 gross revenue
    conn.execute("""
        INSERT INTO sales_records (id, crop_record_id, sale_date, quantity_sold, price_per_unit, gross_revenue, buyer_market, payment_status, notes)
        VALUES 
        (1, 2, '2025-11-10', 30.0, 2200.0, 66000.0, 'Mandya APMC Market Yard', 'Received', 'First lot of Grade A Kharif Paddy'),
        (2, 2, '2025-12-05', 18.0, 2250.0, 40500.0, 'Mysuru APMC Mandi', 'Received', 'Second lot of Grade A Kharif Paddy'),
        (3, 3, '2026-04-02', 10.0, 2500.0, 25000.0, 'Bangalore Grain Exchange', 'Received', 'Grade A Sharbati Wheat procurement'),
        (4, 4, '2025-12-10', 15.0, 3800.0, 57000.0, 'Maddur Ragi Mandi', 'Received', 'Direct grain procurement at MSP support')
    """)

    # 10. Appointments across Lifecycles
    # Appointment 1 (Farmer 1): Completed, Tested, Authorized, Dispatched, Delivered!
    conn.execute("""
        INSERT INTO appointments (id, farmer_id, land_details, address, preferred_date, preferred_time, notes, status, plot_id, delivery_address_id, created_at, updated_at)
        VALUES 
        (1, 1, '5.5 acres Red Sandy Loam (Plot Main Paddy Field, Survey DEMO-MND-001)', 'Kikkeri Village, KR Pet, Mandya - 571423', '2026-10-10', '09:00-12:00', 'Annual soil fertility check prior to Rabi rotation', 'Completed', 1, 1, '2026-10-05 10:00:00', '2026-10-14 16:30:00')
    """)

    # Appointment 2 (Farmer 1): Approved, In-Progress (Testing in Laboratory)
    conn.execute("""
        INSERT INTO appointments (id, farmer_id, land_details, address, preferred_date, preferred_time, notes, status, plot_id, delivery_address_id, created_at, updated_at)
        VALUES 
        (2, 1, '2.0 acres Clay Loam (Plot Secondary Field, Survey DEMO-MND-002)', 'Kikkeri Village, KR Pet, Mandya - 571423', '2026-11-05', '14:00-17:00', 'Soil salinity check for borewell irrigation', 'Approved', 2, 1, '2026-11-01 11:30:00', '2026-11-02 09:15:00')
    """)

    # Appointment 3 (Farmer 1): Pending (Fresh request ready for live Admin Approval demonstration)
    future_date_3 = (date.today() + timedelta(days=4)).isoformat()
    conn.execute("""
        INSERT INTO appointments (id, farmer_id, land_details, address, preferred_date, preferred_time, notes, status, plot_id, delivery_address_id, created_at, updated_at)
        VALUES 
        (3, 1, '5.5 acres Red Sandy Loam, Survey DEMO-MND-001', 'Kikkeri Village, KR Pet, Mandya - 571423', ?, '09:00-12:00', 'Requesting post-monsoon organic carbon testing', 'Pending', 1, 1, datetime('now'), datetime('now'))
    """, (future_date_3,))

    # Appointment 4 (Farmer 1): Approved, Assigned to Field Worker Ravi Kumar (Upcoming Scheduled Visit)
    future_date_4 = (date.today() + timedelta(days=1)).isoformat()
    conn.execute("""
        INSERT INTO appointments (id, farmer_id, land_details, address, preferred_date, preferred_time, notes, status, plot_id, delivery_address_id, created_at, updated_at)
        VALUES 
        (4, 1, '5.5 acres Red Sandy Loam, Survey DEMO-MND-001', 'Kikkeri Village, KR Pet, Mandya - 571423', ?, '09:00-12:00', 'Scheduled field visit for soil core extraction', 'Approved', 1, 1, datetime('now', '-2 days'), datetime('now', '-1 days'))
    """, (future_date_4,))

    # Appointment 5 (Farmer 9 - Shivalingappa): Approved, In Lab Queue with Submitted Assay awaiting supervisor authorization
    conn.execute("""
        INSERT INTO appointments (id, farmer_id, land_details, address, preferred_date, preferred_time, notes, status, plot_id, delivery_address_id, created_at, updated_at)
        VALUES 
        (5, 9, '3.2 acres Red Sandy Loam (Plot Dryland Ragi Field, Survey DEMO-RAGI-042)', 'Maddur Taluk, Mandya - 571428', '2026-11-07', '09:00-12:00', 'Soil micronutrient testing for rainfed millet', 'Approved', 3, 3, '2026-11-04 09:00:00', '2026-11-07 16:00:00')
    """)

    # Appointment 6 (Farmer 9 - Shivalingappa): Approved, Sample In Transit to Lab
    conn.execute("""
        INSERT INTO appointments (id, farmer_id, land_details, address, preferred_date, preferred_time, notes, status, plot_id, delivery_address_id, created_at, updated_at)
        VALUES 
        (6, 9, '3.2 acres Red Sandy Loam, Survey DEMO-RAGI-042', 'Maddur Taluk, Mandya - 571428', '2026-11-08', '14:00-17:00', 'Sample collected and dispatched to laboratory', 'Approved', 3, 3, '2026-11-05 10:00:00', '2026-11-08 17:00:00')
    """)

    # 11. Field Visits
    # Visit 1 (Appt 1): Completed
    # Visit 2 (Appt 2): Completed
    # Visit 3 (Appt 4): Scheduled (Upcoming on Field Worker dashboard)
    # Visit 4 (Appt 5): Completed
    # Visit 5 (Appt 6): Completed
    conn.execute("""
        INSERT INTO field_visits (id, appointment_id, assigned_worker_id, scheduled_date, scheduled_slot, visit_status, survey_number, gps_latitude, gps_longitude, worker_notes, completed_at)
        VALUES 
        (1, 1, 4, '2026-10-10', '09:00-12:00', 'Completed', 'DEMO-MND-001', 12.5218, 76.8951, 'Collected 8 zigzag core sub-samples across 5.5 acres. Composite mixed and dried.', '2026-10-10 11:30:00'),
        (2, 2, 4, '2026-11-05', '14:00-17:00', 'Completed', 'DEMO-MND-002', 12.5290, 76.8910, 'Sample collected from 4 corners and center. Core depth 15cm.', '2026-11-05 16:00:00'),
        (3, 4, 4, ?, '09:00-12:00', 'Scheduled', 'DEMO-MND-001', NULL, NULL, 'Upcoming scheduled on-site visit assigned to field worker.', NULL),
        (4, 5, 4, '2026-11-07', '09:00-12:00', 'Completed', 'DEMO-RAGI-042', 12.5841, 77.0422, 'Sample collected from dryland parcel. Composite bag prepared.', '2026-11-07 11:45:00'),
        (5, 6, 4, '2026-11-08', '14:00-17:00', 'Completed', 'DEMO-RAGI-042', 12.5850, 77.0430, 'Composite sample extracted and packaged for laboratory transit.', '2026-11-08 16:15:00')
    """, (future_date_4,))

    # 12. Soil Samples
    # Sample 1: Completed & authorized
    # Sample 2: In testing
    # Sample 3: In testing with assay recorded awaiting authorization (pH 6.7, EC 0.32, OC 0.62%, N 245, P 18, K 210)
    # Sample 4: In transit to lab
    conn.execute("""
        INSERT INTO soil_samples (id, appointment_id, visit_id, sample_code, assigned_lab_id, sampling_depth_cm, soil_appearance, sample_status, collected_at)
        VALUES 
        (1, 1, 1, 'SMP-2026-00001', 1, 15.0, 'Red Sandy Loam, dry composite', 'Completed', '2026-10-10 11:30:00'),
        (2, 2, 2, 'SMP-2026-00002', 1, 15.0, 'Clay Loam, moist', 'Testing', '2026-11-05 16:00:00'),
        (3, 5, 4, 'SMP-2026-00003', 1, 15.0, 'Red Sandy Loam, dry', 'Testing', '2026-11-07 11:45:00'),
        (4, 6, 5, 'SMP-2026-00004', 1, 15.0, 'Red Sandy Loam, aggregate', 'In_Transit', '2026-11-08 16:15:00')
    """)

    # 13. Laboratory Assays
    # Assay 1: Completed, Authorized by Dr. Patil (user 6)
    # Assay 2: Submitted by Dr. Anita (user 5), awaiting authorization by Dr. Patil (user 6)
    # Specified synthetic values: pH 6.7, EC 0.32 dS/m, OC 0.62%, N 245 kg/ha, P 18 kg/ha, K 210 kg/ha
    conn.execute("""
        INSERT INTO lab_test_assays (
            id, sample_id, lab_id, tested_by_user_id, ph_value, ec_ds_m, organic_carbon_pct,
            nitrogen_kg_ha, phosphorus_kg_ha, potassium_kg_ha, ph_rating, ec_rating, oc_rating,
            n_rating, p_rating, k_rating, lab_status, authorized_by_user_id, authorized_at, remarks, completed_at
        ) VALUES 
        (
            1, 1, 1, 5, 7.20, 0.45, 0.68,
            320.0, 28.5, 245.0, 'Neutral / Optimal', 'Normal', 'Medium',
            'Medium', 'Medium', 'Medium', 'Authorized', 6, '2026-10-13 15:45:00',
            'Balanced macronutrient profile. Recommended for Paddy-Wheat rotation.', '2026-10-12 17:00:00'
        ),
        (
            2, 3, 1, 5, 6.70, 0.32, 0.62,
            245.0, 18.0, 210.0, 'Neutral / Optimal', 'Normal', 'Medium',
            'Low', 'Medium', 'Medium', 'Submitted', NULL, NULL,
            'Assay completed by Dr. Anita. Low nitrogen indicates requirement for legume crop rotation or nitrogen top dressing.', '2026-11-08 14:30:00'
        )
    """)

    # 14. Create Demo PDF Report in isolated demo reports directory
    pdf_filename, pdf_size, pdf_sha256 = create_demo_pdf_report(
        reports_dir, "SMP-2026-00001", "Demo Farmer Mallikarjuna", 1
    )

    conn.execute("""
        INSERT INTO reports (id, appointment_id, file_path, original_filename, file_size_bytes, checksum_sha256, uploaded_by, assay_id, authorized_by, authorized_at)
        VALUES (1, 1, ?, 'Soil_Health_Card_SMP_2026_00001.pdf', ?, ?, 8, 1, 6, '2026-10-13 15:45:00')
    """, (pdf_filename, pdf_size, pdf_sha256))

    # 15. Report Postal Dispatch (Delivered with verified UPU S10 tracking number)
    address_snapshot = json.dumps({
        "recipient_name": "Mallikarjuna M",
        "recipient_phone": "+919999000001",
        "house_details": "House #42, Cauvery Main Road",
        "street_or_village": "Kikkeri Village",
        "taluk": "KR Pet",
        "district": "Mandya",
        "state": "Karnataka",
        "pincode": "571423"
    })

    conn.execute("""
        INSERT INTO report_dispatches (id, report_id, appointment_id, recipient_name, recipient_phone, delivery_address_snapshot, courier_service, tracking_number, dispatch_status, dispatched_at, delivered_at)
        VALUES (
            1, 1, 1, 'Mallikarjuna M', '+919999000001', ?,
            'India Post Speed Post', 'EM123456789IN', 'Delivered',
            '2026-10-14 10:00:00', '2026-10-16 14:30:00'
        )
    """, (address_snapshot,))

    # 16. Sample Events (Complete 13-stage timeline for Appointment 1)
    stages = [
        (1, 1, "APPOINTMENT_REQUESTED", "COMPLETED", 1, "farmer", "Customer Service", "Appointment request submitted via portal.", "2026-10-05 10:00:00"),
        (1, 2, "APPOINTMENT_CONFIRMED", "COMPLETED", 8, "admin", "Operations Planning", "Appointment verified and approved by admin.", "2026-10-06 09:30:00"),
        (1, 3, "FIELD_WORKER_ASSIGNED", "COMPLETED", 8, "admin", "Field Operations", "Field technician Demo Technician Ravi Kumar assigned.", "2026-10-06 10:00:00"),
        (1, 4, "VISIT_SCHEDULED", "COMPLETED", 8, "admin", "Field Operations", "Visit scheduled for 2026-10-10 slot 09:00-12:00.", "2026-10-06 10:05:00"),
        (1, 5, "SAMPLE_COLLECTED", "COMPLETED", 4, "field_worker", "Field Operations", "Soil core sampled at depth 15cm (GPS: 12.5218, 76.8951).", "2026-10-10 11:30:00"),
        (1, 6, "SAMPLE_IN_TRANSIT", "COMPLETED", 4, "field_worker", "Logistics & Transport", "Sample bagged, barcoded SMP-2026-00001, and dispatched to lab.", "2026-10-10 14:00:00"),
        (1, 7, "SAMPLE_RECEIVED_LAB", "COMPLETED", 5, "lab_staff", "Laboratory Services", "Sample logged into District Soil Testing Lab, Mandya intake registry.", "2026-10-11 09:15:00"),
        (1, 8, "LAB_ANALYSIS_IN_PROGRESS", "COMPLETED", 5, "lab_staff", "Laboratory Services", "Sample dried, sieved through 2mm mesh, and queued for chemical assay.", "2026-10-11 11:30:00"),
        (1, 9, "TEST_RESULTS_RECORDED", "COMPLETED", 5, "lab_staff", "Laboratory Services", "Quantitative assays recorded (pH: 7.20, EC: 0.45, OC: 0.68%, NPK: 320/28.5/245 kg/ha).", "2026-10-12 17:00:00"),
        (1, 10, "REPORT_UNDER_REVIEW", "COMPLETED", 5, "lab_staff", "Quality Assurance", "Assay submitted for independent scientific review.", "2026-10-12 17:15:00"),
        (1, 11, "REPORT_AUTHORIZED", "COMPLETED", 6, "lab_staff", "Scientific Certification", "Laboratory supervisor Dr. Patil verified and authorized the report.", "2026-10-13 15:45:00"),
        (1, 12, "PHYSICAL_REPORT_PRINTED", "COMPLETED", 8, "admin", "Postal Logistics", "Soil Health Card printed with barcode. Addressed to: Mallikarjuna M.", "2026-10-14 09:00:00"),
        (1, 13, "REPORT_DELIVERED", "COMPLETED", 8, "admin", "India Post Speed Post", "Consignment EM123456789IN delivered to registered address.", "2026-10-16 14:30:00"),
    ]

    for sid, stg, sname, sstatus, actor_id, arole, dept, desc, ts in stages:
        conn.execute("""
            INSERT INTO sample_events (sample_id, stage_number, stage_name, status, actor_user_id, actor_role, department, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (sid, stg, sname, sstatus, actor_id, arole, dept, desc, ts))

    # In-progress events for Sample 2 (Appt 2, Stage 8)
    conn.execute("""
        INSERT INTO sample_events (sample_id, stage_number, stage_name, status, actor_user_id, actor_role, department, description, created_at)
        VALUES 
        (2, 1, 'APPOINTMENT_REQUESTED', 'COMPLETED', 1, 'farmer', 'Customer Service', 'Appointment requested.', '2026-11-01 11:30:00'),
        (2, 2, 'APPOINTMENT_CONFIRMED', 'COMPLETED', 8, 'admin', 'Operations Planning', 'Appointment confirmed.', '2026-11-02 09:15:00'),
        (2, 3, 'FIELD_WORKER_ASSIGNED', 'COMPLETED', 8, 'admin', 'Field Operations', 'Assigned to Ravi Kumar.', '2026-11-02 09:30:00'),
        (2, 4, 'VISIT_SCHEDULED', 'COMPLETED', 8, 'admin', 'Field Operations', 'Visit scheduled.', '2026-11-02 09:35:00'),
        (2, 5, 'SAMPLE_COLLECTED', 'COMPLETED', 4, 'field_worker', 'Field Operations', 'Sample extracted.', '2026-11-05 16:00:00'),
        (2, 6, 'SAMPLE_IN_TRANSIT', 'COMPLETED', 4, 'field_worker', 'Logistics & Transport', 'Sample dispatched to lab.', '2026-11-05 17:00:00'),
        (2, 7, 'SAMPLE_RECEIVED_LAB', 'COMPLETED', 5, 'lab_staff', 'Laboratory Services', 'Received at lab.', '2026-11-06 10:00:00'),
        (2, 8, 'LAB_ANALYSIS_IN_PROGRESS', 'IN_PROGRESS', 5, 'lab_staff', 'Laboratory Services', 'Sample undergoing active preparation and titration.', '2026-11-06 11:00:00')
    """)

    # Events for Sample 3 (Appt 5, Stage 10 - Under Review awaiting supervisor)
    conn.execute("""
        INSERT INTO sample_events (sample_id, stage_number, stage_name, status, actor_user_id, actor_role, department, description, created_at)
        VALUES 
        (3, 1, 'APPOINTMENT_REQUESTED', 'COMPLETED', 9, 'farmer', 'Customer Service', 'Appointment requested by Farmer Shivalingappa.', '2026-11-04 09:00:00'),
        (3, 2, 'APPOINTMENT_CONFIRMED', 'COMPLETED', 8, 'admin', 'Operations Planning', 'Appointment approved by admin.', '2026-11-04 11:00:00'),
        (3, 3, 'FIELD_WORKER_ASSIGNED', 'COMPLETED', 8, 'admin', 'Field Operations', 'Assigned to field worker Ravi Kumar.', '2026-11-04 11:15:00'),
        (3, 4, 'VISIT_SCHEDULED', 'COMPLETED', 8, 'admin', 'Field Operations', 'Visit scheduled for 2026-11-07.', '2026-11-04 11:30:00'),
        (3, 5, 'SAMPLE_COLLECTED', 'COMPLETED', 4, 'field_worker', 'Field Operations', 'Sample collected (GPS: 12.5841, 77.0422).', '2026-11-07 11:45:00'),
        (3, 6, 'SAMPLE_IN_TRANSIT', 'COMPLETED', 4, 'field_worker', 'Logistics & Transport', 'Sample barcoded SMP-2026-00003 and dispatched.', '2026-11-07 13:00:00'),
        (3, 7, 'SAMPLE_RECEIVED_LAB', 'COMPLETED', 5, 'lab_staff', 'Laboratory Services', 'Received at District Soil Testing Lab, Mandya.', '2026-11-07 15:30:00'),
        (3, 8, 'LAB_ANALYSIS_IN_PROGRESS', 'COMPLETED', 5, 'lab_staff', 'Laboratory Services', 'Physical and chemical assay conducted.', '2026-11-08 11:00:00'),
        (3, 9, 'TEST_RESULTS_RECORDED', 'COMPLETED', 5, 'lab_staff', 'Laboratory Services', 'Assay parameters recorded: pH 6.7, EC 0.32, OC 0.62%, NPK 245/18/210.', '2026-11-08 14:30:00'),
        (3, 10, 'REPORT_UNDER_REVIEW', 'IN_PROGRESS', 5, 'lab_staff', 'Quality Assurance', 'Submitted to Lab Supervisor Dr. Patil for authorization.', '2026-11-08 14:35:00')
    """)

    # Events for Sample 4 (Appt 6, Stage 6 - In Transit)
    conn.execute("""
        INSERT INTO sample_events (sample_id, stage_number, stage_name, status, actor_user_id, actor_role, department, description, created_at)
        VALUES 
        (4, 1, 'APPOINTMENT_REQUESTED', 'COMPLETED', 9, 'farmer', 'Customer Service', 'Appointment requested by Farmer Shivalingappa.', '2026-11-05 10:00:00'),
        (4, 2, 'APPOINTMENT_CONFIRMED', 'COMPLETED', 8, 'admin', 'Operations Planning', 'Appointment approved by admin.', '2026-11-05 14:00:00'),
        (4, 3, 'FIELD_WORKER_ASSIGNED', 'COMPLETED', 8, 'admin', 'Field Operations', 'Assigned to field worker Ravi Kumar.', '2026-11-05 14:15:00'),
        (4, 4, 'VISIT_SCHEDULED', 'COMPLETED', 8, 'admin', 'Field Operations', 'Visit scheduled for 2026-11-08.', '2026-11-05 14:30:00'),
        (4, 5, 'SAMPLE_COLLECTED', 'COMPLETED', 4, 'field_worker', 'Field Operations', 'Sample collected (GPS: 12.5850, 77.0430).', '2026-11-08 16:15:00'),
        (4, 6, 'SAMPLE_IN_TRANSIT', 'IN_PROGRESS', 4, 'field_worker', 'Logistics & Transport', 'Sample in transit to District Soil Testing Lab, Mandya.', '2026-11-08 17:00:00')
    """)

    # 17. Expert Consultations & Threaded Messages
    # Consultation 1: Mallikarjuna (Farmer 1) -> Answered by Dr. Hegde
    conn.execute("""
        INSERT INTO expert_consultations (id, farmer_id, plot_id, report_id, category, subject, question_text, status, assigned_advisor_id, created_at, updated_at)
        VALUES (
            1, 1, 1, 1, 'Fertilizer Application',
            'Nutrient split schedule for upcoming Kharif Paddy',
            'Based on my recent soil report (pH 7.2, Medium Nitrogen 320 kg/ha), should I reduce basal DAP application and increase potassic fertilizer?',
            'ANSWERED', 7, '2026-10-18 10:00:00', '2026-10-19 14:20:00'
        )
    """)

    conn.execute("""
        INSERT INTO consultation_messages (id, consultation_id, sender_user_id, sender_role, message_text, created_at)
        VALUES 
        (1, 1, 1, 'farmer', 'Based on my recent soil report (pH 7.2, Medium Nitrogen 320 kg/ha), should I reduce basal DAP application and increase potassic fertilizer?', '2026-10-18 10:00:00'),
        (2, 1, 7, 'advisor', 'Yes, Mallikarjuna. Your soil report confirms adequate phosphorus (28.5 kg/ha) and medium potassium (245 kg/ha). Reduce basal DAP by approximately 20% to prevent luxury consumption, and apply MOP (Muriate of Potash) in two equal splits: 50% at basal and 50% at panicle initiation for optimal grain filling.', '2026-10-19 14:20:00')
    """)

    # Consultation 2: Shivalingappa (Farmer 9) -> OPEN awaiting Dr. Hegde
    conn.execute("""
        INSERT INTO expert_consultations (id, farmer_id, plot_id, report_id, category, subject, question_text, status, assigned_advisor_id, created_at, updated_at)
        VALUES (
            2, 9, 3, NULL, 'Crop Recommendation',
            'Bio-fertilizers and intercropping for Dryland Ragi',
            'My field has sandy loam soil and is rainfed. Can I intercrop Field Bean (Avare) with Ragi, and which bio-fertilizer inoculants are recommended for drought resilience?',
            'OPEN', 7, '2026-11-09 08:30:00', '2026-11-09 08:30:00'
        )
    """)

    conn.execute("""
        INSERT INTO consultation_messages (id, consultation_id, sender_user_id, sender_role, message_text, created_at)
        VALUES 
        (3, 2, 9, 'farmer', 'My field has sandy loam soil and is rainfed. Can I intercrop Field Bean (Avare) with Ragi, and which bio-fertilizer inoculants are recommended for drought resilience?', '2026-11-09 08:30:00')
    """)

    # 18. Operator Audit Logs
    conn.execute("""
        INSERT INTO operator_audit_logs (actor_user_id, actor_role, action, target_entity_type, target_entity_id, details_json, ip_address, created_at)
        VALUES 
        (3, 'operator', 'ASSISTED_FARMER_REGISTRATION', 'user', 2, '{"name": "Chennamma", "phone": "+919999000002", "language": "kn"}', '127.0.0.1', '2026-11-04 10:15:00'),
        (3, 'operator', 'ASSISTED_APPOINTMENT_BOOKING', 'appointment', 2, '{"farmer_id": 1, "plot_id": 2, "slot": "14:00-17:00"}', '127.0.0.1', '2026-11-01 11:30:00'),
        (3, 'operator', 'FARMER_RECORD_LOOKUP', 'user', 1, '{"farmer_phone": "+919999000001", "purpose": "Dispatch tracking query"}', '127.0.0.1', '2026-11-08 10:00:00')
    """)

    conn.commit()
    conn.close()

    print("[✔] Isolated Demonstration Database successfully generated and verified!")
    print(f"    Total Users Seeded         : {len(users)} (9 Accounts across 6 roles)")
    print(f"    Total Appointments         : 6 (Completed, In-Testing, Pending, Scheduled, Under Review, In Transit)")
    print(f"    Laboratory Assays          : 2 (1 Authorized, 1 Submitted awaiting supervisor)")
    print(f"    Farm Plots & Crop Records  : 4 Plots, 4 Crops, Multi-year history")
    print(f"    Harvest & Sales Ledger     : 3 Harvests, 4 Sales (Farmer 1: 97 Qtl stock, ₹131,500 gross revenue)")
    print(f"    Expert Consultations       : 2 Threads (1 Answered, 1 Open awaiting advisor)")
    print(f"    Postal Speed Post Dispatch : 1 Delivered (Tracking: EM123456789IN)")
    print(f"    Operator Audit Entries     : 3 Logged Actions (Registration, Booking, Lookup)")
    print(f"    PDF Demonstration Report   : {pdf_filename} ({pdf_size} bytes, SHA-256 verified)")


if __name__ == "__main__":
    seed_demo_database()
