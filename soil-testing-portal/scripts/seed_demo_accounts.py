#!/usr/bin/env python3
"""
Soil Testing & Farmer Agricultural Service Platform
Deterministic, Idempotent Demo Accounts Seeder

Safely ensures that all 6 required application roles have deterministic,
verified demonstration accounts in instance/demo_soil_testing.db.
Never touches instance/soil_testing.db.
"""

import os
import sqlite3
import sys
from werkzeug.security import generate_password_hash

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

DEMO_DB_PATH = os.path.abspath(
    os.environ.get("DEMO_DATABASE", os.path.join(PROJECT_ROOT, "instance", "demo_soil_testing.db"))
)
PROD_DB_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, "instance", "soil_testing.db"))

DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "DemoUser@2026!")

DEMO_ACCOUNTS = [
    {
        "id": 1,
        "name": "Demo Farmer Mallikarjuna",
        "phone": "+919999000001",
        "role": "farmer",
        "account_status": "ACTIVE",
        "assigned_lab_id": None,
    },
    {
        "id": 3,
        "name": "Demo Call-Center Operator Pooja",
        "phone": "+919999000003",
        "role": "operator",
        "account_status": "ACTIVE",
        "assigned_lab_id": None,
    },
    {
        "id": 4,
        "name": "Demo Field Technician Ravi Kumar",
        "phone": "+919999000004",
        "role": "field_worker",
        "account_status": "ACTIVE",
        "assigned_lab_id": None,
    },
    {
        "id": 5,
        "name": "Demo Lab Analyst Dr. Anita",
        "phone": "+919999000005",
        "role": "lab_staff",
        "account_status": "ACTIVE",
        "assigned_lab_id": 1,
    },
    {
        "id": 7,
        "name": "Demo Agronomist Dr. Hegde",
        "phone": "+919999000007",
        "role": "advisor",
        "account_status": "ACTIVE",
        "assigned_lab_id": None,
    },
    {
        "id": 8,
        "name": "Demo Administrator Lead",
        "phone": "+919999000008",
        "role": "admin",
        "account_status": "ACTIVE",
        "assigned_lab_id": None,
    },
]


def seed_demo_accounts(db_path=DEMO_DB_PATH):
    if os.path.abspath(db_path) == PROD_DB_PATH:
        raise RuntimeError("FATAL: Refusing to seed demo accounts into production database instance/soil_testing.db!")

    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Demo database not found at {db_path}. Please initialize it first.")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    pw_hash = generate_password_hash(DEMO_PASSWORD)
    seeded_count = 0
    updated_count = 0

    with conn:
        for acc in DEMO_ACCOUNTS:
            existing = conn.execute(
                "SELECT id, phone, role FROM users WHERE phone = ?",
                (acc["phone"],)
            ).fetchone()

            if existing is None:
                conn.execute(
                    """
                    INSERT INTO users (id, name, phone, password_hash, role, account_status, assigned_lab_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (acc["id"], acc["name"], acc["phone"], pw_hash, acc["role"], acc["account_status"], acc["assigned_lab_id"])
                )
                seeded_count += 1
            else:
                # Update role and password to ensure deterministic login capability without duplicates
                conn.execute(
                    """
                    UPDATE users
                    SET name = ?, role = ?, account_status = ?, password_hash = ?
                    WHERE phone = ?
                    """,
                    (acc["name"], acc["role"], acc["account_status"], pw_hash, acc["phone"])
                )
                updated_count += 1

    conn.close()
    print(f"[*] Demo accounts verified in {os.path.basename(db_path)}: {seeded_count} newly inserted, {updated_count} refreshed.")


if __name__ == "__main__":
    seed_demo_accounts()
