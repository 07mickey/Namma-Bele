#!/usr/bin/env bash
set -e

echo "=========================================================="
echo " Soil Testing Portal - Complete Project UI Test Suite      "
echo "=========================================================="

echo "[1/10] Testing CSS Design System & Glassmorphism Tokens..."
node tests/test_css_tokens.js

echo "[2/10] Testing Core JavaScript Validation & Config Modules..."
node tests/test_core_js.js

echo "[3/10] Testing Farmer Home Page & Process Workflow..."
node tests/test_home_page.js

echo "[4/10] Testing Farmer Registration & Login Pages..."
node tests/test_auth_pages.js

echo "[5/10] Testing Farmer Dashboard & Status Banner..."
node tests/test_dashboard_page.js

echo "[6/10] Testing Soil Test Booking Form & Validation..."
node tests/test_booking_page.js

echo "[7/10] Testing Appointments Listing & Secure Reports Access..."
node tests/test_appointments_and_reports.js

echo "[8/10] Testing Sanitization & Fix Pass Requirements..."
node tests/test_fix_pass.js

echo "[9/10] Testing Admin API Module Structure..."
node tests/test_admin_module.js

echo "[10/11] Testing Admin Portal & Management Interfaces..."
node tests/test_admin_pages.js
node tests/test_admin_mgmt_pages.js

echo "[11/11] Testing Demo Sandbox & Auto-Fill System..."
node tests/test_demo_sandbox.js

echo "=========================================================="
echo " All 11 Portal Test Suites Passed Cleanly with Zero Errors!"
echo "=========================================================="
