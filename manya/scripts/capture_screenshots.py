#!/usr/bin/env python3
import os
import subprocess
import time

CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BASE_URL = "http://localhost:3000"
OUTPUT_DIR = "screenshots"

os.makedirs(OUTPUT_DIR, exist_ok=True)

PAGES = [
    ("01_home_page.png", f"{BASE_URL}/index.html", 1280, 950),
    ("02_farmer_login.png", f"{BASE_URL}/login.html", 1280, 950),
    ("03_farmer_register.png", f"{BASE_URL}/register.html", 1280, 950),
    ("04_farmer_dashboard.png", f"{BASE_URL}/dashboard.html?demo=1", 1280, 950),
    ("05_book_appointment.png", f"{BASE_URL}/book-appointment.html?demo=1", 1280, 950),
    ("06_farmer_appointments.png", f"{BASE_URL}/appointments.html?demo=1", 1280, 950),
    ("07_farmer_reports.png", f"{BASE_URL}/reports.html?demo=1", 1280, 950),
    ("08_admin_login.png", f"{BASE_URL}/admin-login.html", 1280, 950),
    ("09_admin_dashboard.png", f"{BASE_URL}/admin-dashboard.html?demo=1", 1280, 950),
    ("10_admin_appointments.png", f"{BASE_URL}/admin-appointments.html?demo=1", 1280, 950),
    ("11_admin_reports_upload.png", f"{BASE_URL}/admin-reports.html?demo=1", 1280, 950),
    ("12_admin_farmers.png", f"{BASE_URL}/admin-farmers.html?demo=1", 1280, 950),
    ("13_soil_guide.png", f"{BASE_URL}/soil-guide.html", 1280, 950)
]

print("Capturing UI/UX screenshots with headless Google Chrome...")

for filename, url, width, height in PAGES:
    out_path = os.path.join(OUTPUT_DIR, filename)
    cmd = [
        CHROME_BIN,
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--window-size={width},{height}",
        f"--screenshot={out_path}",
        url
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
            print(f"  [OK] {filename} ({os.path.getsize(out_path):,} bytes)")
        else:
            print(f"  [FAILED] {filename}: output file too small or missing")
    except Exception as e:
        print(f"  [ERROR] {filename}: {e}")

print("Screenshot capture complete!")

