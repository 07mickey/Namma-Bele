# SOIL TESTING & FARMER AGRICULTURAL SERVICE PLATFORM
## ACADEMIC PROJECT DEMONSTRATION & EVALUATION GUIDE
**Target Academic Review Date:** 11 November 2026  
**Project Workspace:** `/Users/manojv/Community Project/soil-testing-portal/`  
**Server Environment:** Isolated Demonstration Mode (`DEMO_MODE=1`)  
**Automated Test Suite Status:** 183 / 183 Passing (100% Pass Rate)

---

## 1. Executive Summary & Safety Guarantees

This document serves as the official demonstration protocol for the academic review on **11 November 2026**.

To ensure a seamless, professional, and convincing live presentation without reliance on blank state setups or unpredictable manual record creation, the platform includes a **fully pre-seeded demonstration environment**.

### Strict Data Isolation Guarantees
- **Zero Production Overwrite:** Demonstration operations run exclusively against `instance/demo_soil_testing.db` and report files stored in `instance/demo_reports/`. The authoritative production database (`instance/soil_testing.db`) remains completely untouched.
- **Repeatable 1-Second Reset:** The entire demonstration state can be reset or re-seeded cleanly at any time using `flask init-demo` or `python3 scripts/seed_demo_data.py`.
- **Realistic Agricultural Integrity:** All crop cycles, yield figures, mandi procurement prices, soil fertility indices, and laboratory workflows adhere strictly to standard agronomic science (ICAR / KAU soil rating standards).
- **Safe Academic Labeling:** All synthetic PDF reports and dispatch records carry prominent watermarks and disclaimers indicating they are generated solely for academic evaluation.

---

## 2. Server Startup & Quick Verification

### One-Command Server Startup
To launch the application in demonstration mode on port `5001`:

```bash
cd "/Users/manojv/Community Project/soil-testing-portal"
DEMO_MODE=1 PORT=5001 python3 run.py
```

### Health Check Verification
Verify the server status in your browser or terminal:
- **URL:** [http://127.0.0.1:5001/api/health](http://127.0.0.1:5001/api/health)
- **Expected JSON Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "demo_mode": true
}
```

### Instant Database Reset / Re-seed Command
If data is altered during live testing and you wish to restore the pristine demonstration state:

```bash
cd "/Users/manojv/Community Project/soil-testing-portal"
python3 scripts/seed_demo_data.py
```
*Or via Flask CLI:*
```bash
DEMO_MODE=1 flask init-demo
```

---

## 3. Master Demonstration Accounts & Credentials

All fictional demonstration accounts share a common, memorable evaluation password:  
**Password:** `DemoUser@2026!`

| Role | Persona Name | Login Identifier (Phone) | Key Responsibilities & Pre-seeded State |
| :--- | :--- | :--- | :--- |
| **Farmer (Primary)** | Demo Farmer Mallikarjuna | `+919999000001` | 2 Plots (5.5 ac Paddy, 2.0 ac Wheat), 3 Harvests, ₹1,31,500 Sales, 1 Completed report, 1 In-lab test, 1 Pending booking, 1 Answered consultation |
| **Farmer (Isolation)** | Demo Farmer Shivalingappa | `+919999000009` | Demonstrates tenant privacy; 3.2 ac Dryland Ragi, 1 Open advisory question, 1 Lab assay awaiting supervisor authorization |
| **Farmer (Assisted)** | Demo Assisted Farmer Chennamma | `+919999000002` | `UNCLAIMED` account registered via Call-Center operator; ready for live `/claim` account activation demo (OTP: `123456`) |
| **Call-Center Operator** | Demo Operator Pooja | `+919999000003` | Call-center desk; assisted farmer onboarding, appointment bookings, phone search lookup, audit activity log |
| **Field Technician** | Demo Field Technician Ravi Kumar | `+919999000004` | Field sample collection; GPS logging, anonymized land parcels, scheduled visit queue |
| **Laboratory Analyst** | Demo Lab Analyst Dr. Anita | `+919999000005` | District Soil Testing Lab Mandya; sample intake, chemical titration entry (pH, EC, OC, N, P, K); blocked from self-approval |
| **Laboratory Supervisor** | Demo Lab Supervisor Dr. Patil | `+919999000006` | Quality assurance; independent report authorization, segregation-of-duties enforcement |
| **Agronomist / Advisor** | Demo Agronomist Dr. Hegde | `+919999000007` | Crop & fertilizer consultation desk; 1 Answered paddy nutrient thread, 1 Open ragi intercropping question awaiting reply |
| **Administrator** | Demo Administrator Lead | `+919999000008` | Platform executive control; appointment approvals, field worker assignment, Speed Post dispatch & label generation |

### Interactive 1-Click Demo Login Panel (`/login`)
When running in `DEMO_MODE=1`, the `/login` page renders an interactive side panel titled **"Explore NAMMA BELE — Demo Access"**:
- **1-Click Auto-Fill:** Clicking any active role card (e.g. Farmer, Operator, Lab Analyst, etc.) automatically selects the correct portal tab (`Farmer Login` vs `Staff / Admin Login`), fills the mobile number and password (`DemoUser@2026!`), and displays a confirmation banner.
- **Safety & Verification:** Clicking a demo account does *not* automatically submit the form. The reviewer can inspect the credentials in the form fields and manually click **Sign In** to observe genuine session creation and CSRF validation.
- **Assisted Farmer Claiming:** The panel clearly flags **Demo Assisted Farmer Chennamma** as `UNCLAIMED`, explains that assisted accounts require first-time activation, displays demo OTP `123456`, and provides a direct shortcut link to `/claim`.
- **Zero Leak in Production:** When `DEMO_MODE=0` (or omitted), this panel is completely omitted from the HTML template, ensuring no synthetic accounts or credentials are ever exposed in production.

---

## 4. Platform Navigation Sitemap

| Portal View | Direct URL | Target Persona | Demonstration Highlights |
| :--- | :--- | :--- | :--- |
| **Public Landing Page** | [http://127.0.0.1:5001/](http://127.0.0.1:5001/) | General Public | Editorial design, Sprout visual, Interactive soil spotlight, Nutrient meters, FAQ accordion |
| **Unified Portal Login** | [http://127.0.0.1:5001/login](http://127.0.0.1:5001/login) | All Roles | Tabbed login (Farmer vs. Staff / Admin), session CSRF tokens, role-based redirection |
| **Farmer Portal** | [http://127.0.0.1:5001/farmer](http://127.0.0.1:5001/farmer) | Mallikarjuna (`...0001`) | Digital farm ledger, crop rotations, harvest yields, mandi sales ledger, report downloads |
| **Sample Tracking** | [http://127.0.0.1:5001/tracking](http://127.0.0.1:5001/tracking) | Mallikarjuna (`...0001`) | Complete 13-stage timeline tracking, postal dispatch consignment tracking |
| **Expert Advisory Desk** | [http://127.0.0.1:5001/farmer/expert](http://127.0.0.1:5001/farmer/expert) | Mallikarjuna (`...0001`) | Threaded agronomist consultations, scientific fertilizer split recommendations |
| **Account Claim Wizard** | [http://127.0.0.1:5001/claim](http://127.0.0.1:5001/claim) | Chennamma (`...0002`) | Assisted registration claim flow: OTP verification, password creation, account activation |
| **Operator Desk** | [http://127.0.0.1:5001/operator](http://127.0.0.1:5001/operator) | Pooja (`...0003`) | Assisted farmer onboarding, fast phone lookup, appointment booking, immutable audit log |
| **Field Worker Portal** | [http://127.0.0.1:5001/field-worker](http://127.0.0.1:5001/field-worker) | Ravi Kumar (`...0004`) | Assigned visits, upcoming schedule, on-site GPS coordinate and depth recording |
| **Laboratory Portal** | [http://127.0.0.1:5001/lab](http://127.0.0.1:5001/lab) | Dr. Anita / Dr. Patil | Sample intake queue, titration entry, segregation-of-duties authorization queue |
| **Advisor Portal** | [http://127.0.0.1:5001/advisor](http://127.0.0.1:5001/advisor) | Dr. Hegde (`...0007`) | Advisory queue, farmer query review, scientific advisory response drafting |
| **Admin Operations** | [http://127.0.0.1:5001/admin](http://127.0.0.1:5001/admin) | Admin Lead (`...0008`) | KPI overview, appointment approvals, field worker assignment, Speed Post dispatch queue |

---

## 5. Pre-Seeded Demonstration Records Catalog

### A. Farm Plots & Digital Crop Ledger (Farmer Mallikarjuna)
- **Plot 1:** `Main Paddy Field` (Survey `DEMO-MND-001`, 5.5 Acres, Red Sandy Loam, Canal Irrigated)
  - *2024 Kharif:* Paddy / Rice (`IR-64`), baseline archive.
  - *2025 Kharif:* Paddy / Rice (`JGL 1798`), Harvested: **120.0 Quintals** (Grade A, Warehouse Bay 1).
    - *Sale 1 (10 Nov 2025):* 30 Qtl @ ₹2,200/Qtl = ₹66,000 (Mandya APMC Yard).
    - *Sale 2 (05 Dec 2025):* 18 Qtl @ ₹2,250/Qtl = ₹40,500 (Mysuru APMC Mandi).
    - *Paddy Summary:* 48 Qtl sold, **72 Qtl remaining stock**, **₹1,06,500 gross revenue**.
- **Plot 2:** `Secondary Field` (Survey `DEMO-MND-002`, 2.0 Acres, Clay Loam, Borewell Irrigated)
  - *2026 Rabi:* Wheat (`Sharbati`), Harvested: **35.0 Quintals** (Grade A, Farm Silo).
    - *Sale 3 (02 Apr 2026):* 10 Qtl @ ₹2,500/Qtl = ₹25,000 (Bangalore Grain Exchange).
    - *Wheat Summary:* 10 Qtl sold, **25 Qtl remaining stock**, **₹25,000 gross revenue**.
- **Consolidated Ledger:** 155 Qtl Harvested, 58 Qtl Sold, **97.0 Quintals Total Remaining Stock**, **₹1,31,500.00 Total Gross Revenue** (explicitly separated from net profit).

### B. Demonstration Appointments Across Workflow Stages
1. **Appointment #1 (Completed & Delivered):**
   - Farmer: Mallikarjuna | Plot: Main Paddy Field
   - Sample: `SMP-2026-00001` | Depth: 15 cm | Appearance: Red Sandy Loam
   - Chemical Assay: pH 7.20 (Neutral), EC 0.45 dS/m (Normal), OC 0.68% (Medium), N 320 kg/ha, P 28.5 kg/ha, K 245 kg/ha.
   - Authorization: Verified & signed by Supervisor Dr. Patil on 13 Oct 2026.
   - PDF Health Card: Generated, uploaded, downloadable with SHA-256 integrity verification.
   - Physical Card Dispatch: India Post Speed Post consignment `EM123456789IN` (Delivered).
   - Audit Trail: Full 13 stages completed (Stages 1 through 13).
2. **Appointment #2 (In Lab Analysis):**
   - Farmer: Mallikarjuna | Plot: Secondary Field
   - Sample: `SMP-2026-00002` | Status: `Testing` (Stage 8 `LAB_ANALYSIS_IN_PROGRESS`).
3. **Appointment #3 (Pending Live Admin Approval):**
   - Farmer: Mallikarjuna | Status: `Pending`.
   - Purpose: Ready for live demonstration of Admin review and approval in 1 click.
4. **Appointment #4 (Approved & Field Visit Scheduled):**
   - Farmer: Mallikarjuna | Status: `Approved`.
   - Visit: Scheduled for tomorrow, assigned to Field Worker Ravi Kumar (awaiting collection).
5. **Appointment #5 (In Lab Queue - Assay Awaiting Authorization):**
   - Farmer: Shivalingappa | Plot: Dryland Ragi Field
   - Sample: `SMP-2026-00003` | Status: `Testing`.
   - Synthetic Assay Parameters: **pH 6.70**, **EC 0.32 dS/m**, **OC 0.62%**, **N 245.0 kg/ha (Low)**, **P 18.0 kg/ha (Medium)**, **K 210.0 kg/ha (Medium)**.
   - Status: `Submitted` by Analyst Dr. Anita.
   - Purpose: Supervisor Dr. Patil can log in, view this pending assay, and click "Authorize" live!
6. **Appointment #6 (Sample In Transit to Lab):**
   - Farmer: Shivalingappa | Sample: `SMP-2026-00004` | Status: `In_Transit` (Stage 6).
   - Purpose: Shows up on Lab Chemist dashboard under "Samples In Transit / Awaiting Intake".

### C. Expert Consultations (Agronomist Desk)
- **Consultation #1 (Answered):**
  - Farmer: Mallikarjuna | Advisor: Dr. Hegde
  - Category: Fertilizer Application
  - Subject: *"Nutrient split schedule for upcoming Kharif Paddy"*
  - Thread: Farmer queries whether to reduce basal DAP based on report SMP-2026-00001. Dr. Hegde confirms 20% reduction and outlines two split applications of MOP for optimal grain filling.
- **Consultation #2 (Open - Awaiting Review):**
  - Farmer: Shivalingappa | Advisor: Dr. Hegde
  - Category: Crop Recommendation
  - Subject: *"Bio-fertilizers and intercropping for Dryland Ragi"*
  - Thread: Farmer queries drought-resilient bio-fertilizer inoculants and field bean intercropping.
  - Purpose: Dr. Hegde sees this open query in the Advisor portal and can respond live.

---

## 6. Recommended 10–12 Minute Academic Presentation Script

Follow this chronological script during the project viva/review to cover all core competencies effortlessly:

### Minute 0:00 – 0:02 | Architectural Introduction & Editorial Landing Page
1. Open browser to [http://127.0.0.1:5001/](http://127.0.0.1:5001/).
2. **Talking Points:**
   - *"Our platform is an end-to-end Soil Testing & Agricultural Service Platform engineered to bridge rural farmers, field technicians, accredited testing laboratories, and agronomists."*
   - Highlight the **M2 Editorial Design Integration**: the SVG sprout illustration, interactive crop nutrient spotlight, dynamic nutrient meters, and accessible FAQ accordion.
   - Note the responsive typography and high-contrast color tokens designed for field readability.

### Minute 0:02 – 0:04 | Farmer Dashboard & Agricultural Farm Ledger
1. Navigate to `/login` and select the **Farmer** tab.
2. Log in as Mallikarjuna (`+919999000001` / `DemoUser@2026!`).
3. **Talking Points:**
   - Show the **Farm Ledger**: 2 distinct land holdings (*Main Paddy Field* and *Secondary Field*).
   - Scroll to the **Crop & Harvest Records**: Explain the multi-year rotation (Paddy Kharif 2024 baseline, Paddy Kharif 2025, Wheat Rabi 2026).
   - Point out the **Sales Ledger**: 155 Qtl harvested, 58 Qtl sold across Mandya APMC and Mysuru Mandi, leaving **97 Quintals verified in stock**.
   - Emphasize financial transparency: *"Notice that ₹1,31,500 is explicitly labeled as Gross Revenue, never conflated with net profit."*

### Minute 0:04 – 0:06 | Sample Tracking (13 Stages) & Certified PDF Report Access
1. Under Appointments, click **Track Status** for Appointment #1.
2. **Talking Points:**
   - Display the **13-Stage Sample Timeline**: From initial booking, through field collection, lab intake, titration, supervisor authorization, to postal delivery.
   - Point out the Speed Post tracking consignment `EM123456789IN` conforming to mathematical UPU S10 check-digit standards.
3. Click **"Download Verified PDF Report"**:
   - The PDF downloads instantly. Open it to show the clean layout, analytical values, supervisor signature metadata, and defense-in-depth headers (`X-Content-Type-Options: nosniff`).
   - Highlight the academic demonstration watermark protecting against official document imitation.

### Minute 0:06 – 0:07 | Tenant Privacy & Assisted Registration Claim Flow
1. Open an Incognito window and log in as Farmer B (`+919999000009` / `DemoUser@2026!`).
   - Show that Farmer B only sees his own *Dryland Ragi Field* and his own appointments—proving **multi-tenant data isolation**.
2. Open [http://127.0.0.1:5001/claim](http://127.0.0.1:5001/claim).
   - Enter Chennamma's phone `+919999000002`.
   - Enter OTP `123456` and set a password.
   - Explain: *"This demonstrates our assisted-registration bridge: farmers without smartphones can be onboarded via our call center operator, and later claim their online account securely."*

### Minute 0:07 – 0:09 | Laboratory Workflows & Segregation of Duties
1. Log in as Lab Analyst Dr. Anita (`+919999000005` / `DemoUser@2026!`) at [http://127.0.0.1:5001/lab](http://127.0.0.1:5001/lab).
   - Show the intake queue and recorded titration assays.
   - Point out Sample `SMP-2026-00003` with synthetic values: **pH 6.7, EC 0.32, OC 0.62%, N 245 kg/ha, P 18 kg/ha, K 210 kg/ha**.
   - Attempt to authorize this assay as the analyst: Note the system **blocks self-authorization with HTTP 403 Forbidden**.
2. Log out and log in as Lab Supervisor Dr. Patil (`+919999000006` / `DemoUser@2026!`).
   - The supervisor reviews the ICAR nutrient indices (Low Nitrogen, Medium Phosphorus/Potassium) and clicks **"Authorize Report"**.
   - Explain: *"This enforces strict segregation of duties required in accredited analytical testing."*

### Minute 0:09 – 0:11 | Operations Desk & Postal Speed Post Dispatch
1. Log in as Admin Lead (`+919999000008` / `DemoUser@2026!`) at [http://127.0.0.1:5001/admin](http://127.0.0.1:5001/admin).
   - Show Appointment #3 in `Pending` status. Click **"Approve Appointment"** and assign Field Worker Ravi Kumar.
   - Show the **Postal Dispatch Queue**: View consignment `EM123456789IN` with its immutable address snapshot (preventing address mutation after shipping).
2. Log in as Agronomist Dr. Hegde (`+919999000007` / `DemoUser@2026!`) at [http://127.0.0.1:5001/advisor](http://127.0.0.1:5001/advisor).
   - Show the consultation desk: 1 answered thread with Farmer Mallikarjuna, and 1 open question on Ragi bio-fertilizers.

### Minute 0:11 – 0:12 | Technical Architecture & Automated Test Evidence
1. Switch to terminal and run the test suite:
   ```bash
   pytest tests/
   ```
2. **Concluding Statement:**
   - *"Our entire architecture is backed by 18 relational tables, 79 registered endpoints across 12 blueprints, and 183 automated tests achieving 100% pass rate. Security controls include Argon2id hashing, secure CSRF tokens, strict role-based access control, parameterized SQL queries, and mathematical UPU S10 barcode validation."*

---

## 7. Troubleshooting & Frequently Asked Questions

### Q1: What happens if the demo server was stopped?
Simply restart it using:
```bash
cd "/Users/manojv/Community Project/soil-testing-portal"
DEMO_MODE=1 PORT=5001 python3 run.py
```

### Q2: What if a test during the viva altered the records and I need a clean slate?
Run the one-second re-seed script:
```bash
python3 scripts/seed_demo_data.py
```
This drops and re-applies the demo database cleanly without touching the production database.

### Q3: Why does India Post tracking not call an external API?
To maintain 100% offline reliability during academic evaluation and avoid external network failures or API rate limits, tracking conforms to the UPU S10 check-digit algorithm and internal 13-stage lifecycle state machine rather than external live carrier APIs.

### Q4: How is OTP handled in the demonstration environment?
In demonstration mode, OTPs are safely logged to the server console and the assisted farmer account has a pre-configured demo OTP (`123456`) to ensure a smooth, zero-latency demonstration without requiring third-party SMS gateway credits. In production mode, OTP secrets are strictly redacted from logs.

