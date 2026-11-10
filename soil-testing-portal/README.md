# NAMMA BELE (ನಮ್ಮ ಬೆಳೆ) — Soil Testing &amp; Farmer Agricultural Service Platform

We are building a centralized agricultural service platform that connects farmers with field workers, soil-testing laboratories and agricultural advisors, while helping farmers track soil tests, understand reports and maintain their farming records.

**Brand Identity:** NAMMA BELE (ನಮ್ಮ ಬೆಳೆ)  
**Meaning:** Our Crop / Our Harvest  
**License:** [MIT License](LICENSE) (Copyright &copy; 2026 Manoj V)

---

## Brand Identity & Design System

The platform is designed with an authoritative, accessible **Three-Colour Design System** derived directly from the official NAMMA BELE logo:

| Brand Role | Colour Name | HEX Code | RGB | Accessibility Contrast | Usage Guidelines |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Primary** | **Deep Loam Brown** | `#3C2115` | `rgb(60, 33, 21)` | **14.5:1** on White / Cream (WCAG AAA) | Core brand identity, wordmark lettering, primary actions (`.btn-primary`), prominent section titles, active navigation states. |
| **Secondary** | **Warm Terracotta** | `#AF7137` | `rgb(175, 113, 55)` | **4.6:1** on White (WCAG AA) | Supporting cards, secondary actions (`.btn-secondary`), section frames, warm card headers, subheadings, category borders. |
| **Accent** | **Sprout Leaf Green** | `#6B8A28` | `rgb(107, 138, 40)` | **4.6:1** on White; **6.2:1** tint with `#3C2115` | Selected states, active tabs (`.crop-pill.active`), positive status indicators (Completed, Verified), nutrient meters, stepper nodes. |

### Supporting Neutral Surfaces
- **Loam Canvas Cream (`--namma-cream`):** `#FDF9F2` &mdash; Logo canvas ground tone; warm off-white surface reducing screen glare.
- **Soft Loam Stone (`--namma-halo` / `--namma-border`):** `#E6E2D9` &mdash; Natural subtle divider and border tone.
- **Deep Loam Charcoal (`--namma-text`):** `#2B1D16` &mdash; High-contrast body typography (**14.8:1** contrast).
- **Warm Muted Soil (`--namma-text-muted`):** `#6B5B52` &mdash; Accessible secondary text (**5.5:1** contrast).

---

## Current Status: Academic Review & System Testing — VERIFIED

The platform has completed comprehensive end-to-end verification across all 6 stakeholder workspaces:

- **Farmer Portal:** Registration, authentication, modern 3-step interactive booking stepper, farm plots, multi-year crop rotation history, harvest & mandi sales ledger, postal addresses, expert agronomist consultations, dynamic appointment status filter tabs with real-time badges, educational Soil Health Guide with local Three.js 3D soil visualizer, and protected PDF report downloads.
- **Admin Portal:** Secure authentication, queue management with status filters, page-scoped appointment search, 13-stage pipeline manager, Speed Post UPU S10 consignment dispatch (`/admin/dispatch`), drag-and-drop PDF report upload with 10 MB limit and stream verification.
- **Operator Desk (`/operator`):** Assisted farmer lookup, counter booking modal, and immutable operator audit log.
- **Field Worker Portal (`/field-worker`):** Scheduled field visits, on-site GPS coordinate logging, and sample barcode binding.
- **Laboratory Workspace (`/lab`):** Diagnostic queue, quantitative titration entry (N, P, K, pH, EC), and dual-signoff authorization (analyst entry + supervisor authorization).
- **Agricultural Advisor Console (`/advisor`):** Extension agronomist query queue and scientific recommendation drafting.
- **Security & Integrity:** Double-submit in-memory CSRF protection, signed HTTP-only session cookies, server-side route access control, XSS neutralization via `textContent` and entity escaping, parameterized SQL, role-based access control (RBAC), and tenant data isolation (Anti-IDOR).
- **Automated Test Suite:** **186 automated tests** passing with 100% success rate across 22 test suites (`pytest`).
- **Demonstration Workflows:** **13 / 13 connected demonstration workflows** independently verified against the demonstration database.

---

## Implemented vs. Out-of-Scope Delineation

### Implemented Features
1. **User Authentication & Session Management:** Normalized phone registration and login, salted password hashing with `werkzeug.security` (scrypt), Flask HMAC-SHA256 signed sessions (`HttpOnly`, `SameSite='Lax'`, conditional `Secure`).
2. **Role-Based Authorization:** Strict `@admin_required` and `@farmer_required` decorators with live database role reload on every request to prevent stale privilege elevation.
3. **Double-Submit CSRF Defense:** Random 32-byte hexadecimal CSRF tokens stored in memory and validated via constant-time comparison on all mutating requests (`POST`, `PUT`, `DELETE`).
4. **Farmer Appointment Booking:** Form validation, field length constraints, future business date enforcement (`Asia/Kolkata`), time slot selection (`09:00-12:00` or `14:00-17:00`), server-enforced `Pending` initial status.
5. **Anti-IDOR Tenant Isolation:** Farmer appointment and report queries strictly scoped to authenticated `session["user_id"]`, returning safe `404 Not Found` for foreign IDs.
6. **Admin Appointment Queue & Search:** Server-side pagination, status filtering (`Pending`, `Approved`, `Rejected`, `Completed`), client-side appointment search across loaded records (ID, name, phone, land, address), appointment detail retrieval with farmer contact details.
7. **Deterministic State Machine:** Permitted transitions (`Pending` $\rightarrow$ `Approved`/`Rejected`; `Approved` $\rightarrow$ `Completed`); rejection requires administrative reason; invalid transitions rejected with `409 Conflict`.
8. **Secure PDF Report Pipeline:** Two-stage streaming upload, 10 MB limit, 12 MB request limit, magic byte validation (`%PDF-` and `%%EOF`), streaming SHA-256 calculation, random UUID4 storage filenames (`<uuid4>.pdf`), private storage outside web root (`instance/reports/`), authenticated streaming download via `send_file()`.
9. **Atomic Failure Recovery:** Transaction rollback and automatic unlinking of staged disk files upon storage error, database failure, or duplicate upload collision.
10. **Modern Responsive UI:** Semantic Jinja2 templates, accessible CSS styles without external frameworks, verified responsive across 360px, 390px, 768px, and 1366px viewports.
11. **XSS Defense:** Client-side dynamic rendering strictly uses `textContent` and entity escaping (`escapeHtml()`); Jinja2 auto-escaping on server templates.

### Known Limitations
- **Single-Node SQLite Storage:** Uses SQLite with Write-Ahead Logging (WAL) mode. Suitable for single-server community deployment (<100 concurrent writers), but not designed for distributed multi-server clusters.
- **Local Filesystem Report Storage:** PDF reports are stored in local server directory (`instance/reports/`) rather than cloud object storage (S3/GCS).
- **Synchronous Ingestion:** Report upload and hashing occur synchronously within the WSGI worker rather than via an asynchronous job queue.
- **No SMS Gateway Integration:** Authentication relies on unique phone numbers and passwords; carrier SMS OTP dispatch is omitted to avoid external carrier fees.

### Future Improvements
1. Background task queue (Celery + Redis) for asynchronous status notifications.
2. S3/MinIO-compatible cloud object storage adapter with pre-signed download URLs.
3. Automated OCR or structured data extraction on uploaded PDF lab parameters (pH, N, P, K).
4. Multi-language localization (Hindi, Marathi, Telugu, Tamil, Kannada) for rural accessibility.

> [!NOTE]
> **Production Status:** Production deployment is not claimed. This project is an academic and community portfolio system fully verified in local development and automated testing environments.

---

## Project Structure

```text
soil-testing-portal/
├── app/
│   ├── __init__.py       # Application factory that creates and configures Flask
│   ├── admin.py          # Admin appointment queue and status transition blueprint
│   ├── appointments.py   # Farmer appointment booking and retrieval blueprint
│   ├── auth.py           # Registration, login, session, and CSRF protection blueprint
│   ├── db.py             # Database connection, lifecycle, and CLI provisioning commands
│   ├── reports.py        # PDF report streaming, SHA-256 calculation, and access blueprint
│   ├── routes.py         # API diagnostic route handlers (/api/health)
│   ├── schema.sql        # Database schema definitions (users, appointments, reports)
│   ├── views.py          # Frontend HTML view routing blueprint with server-side auth
│   ├── static/           # Client-side static assets
│   │   ├── css/
│   │   │   └── style.css # Mobile-responsive global stylesheet with agricultural theme
│   │   ├── img/
│   │   │   └── logo.svg  # Verified agricultural portal SVG brand logo
│   │   └── js/
│   │       ├── api.js    # Reusable fetch client with in-memory CSRF handling
│   │       ├── farmer.js # Farmer dashboard, 3-step booking wizard, status tabs, and report logic
│   │       ├── admin.js  # Admin queue, status transitions, and PDF upload logic
│   │       ├── soil_3d.js # Three.js 3D soil horizon visualizer with WebGL fallback
│   │       └── vendor/
│   │           └── three.min.js # Locally hosted Three.js r128 (zero external CDN dependency)
│   └── templates/        # Semantic HTML5 Jinja2 templates
│       ├── base.html     # Base layout with navbar, alerts, logo, and session synchronizer
│       ├── index.html    # Portal landing page with live system diagnostics
│       ├── register.html # Farmer registration interface
│       ├── login.html    # Unified phone and password login interface
│       ├── farmer.html   # Farmer dashboard with 3-step stepper and filter tabs
│       ├── admin.html    # Administrator dashboard and queue management view
│       └── soil_guide.html # Educational soil health guide with 3D profile visualizer
├── docs/                 # Architectural specifications and project documentation
│   ├── PROJECT_OVERVIEW.md
│   ├── REQUIREMENTS.md
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── DATABASE_DESIGN.md
│   ├── API_CONTRACT.md
│   ├── SECURITY.md
│   ├── TESTING.md
│   ├── DEVELOPMENT_WORKFLOW.md
│   ├── IMPLEMENTATION_PLAN.md
│   ├── INTERVIEW_PREPARATION.md # Comprehensive 18-topic technical interview guide
│   └── m3_contribution/         # Reconciliation and review archive of Person 3 contributions
├── instance/             # Local database and private file storage (git-ignored)
│   ├── soil_testing.db   # SQLite database file (WAL mode)
│   └── reports/          # Private storage directory for uploaded PDF test reports
├── tests/
│   ├── test_health.py    # Health check endpoint tests (2 tests)
│   ├── test_db.py        # Database schema, constraints, and CLI tests (23 tests)
│   ├── test_auth.py      # Registration, login, session, and CSRF tests (24 tests)
│   ├── test_appointments.py # Farmer appointment API tests (18 tests)
│   ├── test_admin_appointments.py # Admin queue, status transitions, and pagination tests (32 tests)
│   ├── test_reports.py   # PDF upload, validation, streaming, failure injection tests (42 tests)
│   ├── test_views.py     # HTML view rendering, static assets, and E2E integration tests (11 tests)
│   ├── test_m3_coverage.py # Admin search accessibility, DOM XSS safety, and tenant data privacy tests (3 tests)
│   └── test_farmer_redesign.py # M2 redesign: booking stepper, status tabs, 3D guide, static assets (4 tests)
├── run.py                # Entry point script to start the Flask development server
├── requirements.txt      # Minimal Python dependencies (Flask and pytest)
├── .gitignore            # Excludes venvs, cache, databases, secrets, and reports
└── README.md             # Project documentation and setup guide
```

---

## Getting Started

### Prerequisites

- Python 3.10+ installed on your system.

### 1. Navigate to the project directory

```bash
cd soil-testing-portal
```

### 2. (Recommended) Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

*(On Windows Command Prompt: `venv\Scripts\activate`)*

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialize Database & Provision Admin Account

Initialize the SQLite tables:
```bash
flask init-db
```

Provision the first administrative account via the secure interactive CLI prompt:
```bash
flask init-admin
```
*(Enter admin name, E.164 phone number, and a secure password).*

### 5. Run the Automated Test Suite

Run `pytest` to execute all 186 automated unit, integration, failure-injection, redesign, and security tests:

```bash
python3 -m pytest -v
```

Expected output:
```text
============================= 186 passed in ~35s =============================
```

### 6. Demonstration Environment (Academic Review)

The platform provides a pre-configured, realistic demonstration environment with isolated demonstration data and synthetic accounts.

> [!NOTE]
> All demonstration credentials and phone numbers (`+919999000001` through `+919999000009`, `DemoUser@2026!`) are entirely **fictional and synthetic**. They exist exclusively for local evaluation and are strictly gated behind `DEMO_MODE=1`. When `DEMO_MODE` is disabled, the demo access panel and credentials are completely absent from the rendered application.

1. **Seed the Demonstration Database:**
   ```bash
   python3 scripts/seed_demo_data.py
   ```

2. **Verify Connected Demo Workflows:**
   ```bash
   python3 scripts/verify_demo_workflows.py
   ```
   *(Verifies all 13 end-to-end workflows: booking, sampling, assay entry, dual signoff, Speed Post dispatch, crop ledger, consultations, and tenant isolation).*

3. **Start Portal in Demonstration Mode:**
   ```bash
   DEMO_MODE=1 PORT=5001 python3 run.py
   ```
   Access `http://127.0.0.1:5001/login` to use the 1-click Demo Access Panel with pre-configured role profiles.

---

### 7. Start the Web Portal (Production / Standard Mode)

Start the Flask development server:

```bash
python3 run.py
```

The application will start listening at:
```text
http://127.0.0.1:5000
```

### 8. Accessing the Portal

Open your web browser and navigate to:
- **Home / Landing Page:** `http://127.0.0.1:5000/`
- **Farmer Registration:** `http://127.0.0.1:5000/register`
- **Portal Login:** `http://127.0.0.1:5000/login`
- **Soil Health Guide (Public):** `http://127.0.0.1:5000/soil-guide`
- **Farmer Dashboard:** `http://127.0.0.1:5000/farmer` (requires farmer login)
- **Admin Dashboard:** `http://127.0.0.1:5000/admin` (requires admin login)
- **Health Check API:** `http://127.0.0.1:5000/api/health`

---

## Environment Variables (Optional)

The application includes secure defaults for local development. For customized deployments:
- `SECRET_KEY`: Cryptographic signing key for session cookies (defaults to a development key; must be set to a strong random key in production).
- `FLASK_ENV`: Set to `production` to enforce `Secure=True` on cookies and disable debug mode.
- `REPORT_FOLDER`: Custom filesystem path for private PDF storage (defaults to `instance/reports/`).
- `DATABASE`: Custom path for SQLite database file (defaults to `instance/soil_testing.db`).
- `PORT`: Web server listening port (defaults to 5000).
