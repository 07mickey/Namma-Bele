# Backend Integration Handover for Person 1 (Flask Backend Developer)

**Prepared by:** Person 3 (Admin Module, Testing & Security)  
**Date:** November 2, 2026  
**Status:** Handover Ready  

---

## 1. Files Provided for Backend Integration

Person 1 will integrate the following static frontend assets and templates with the Flask application:

### A. Frontend HTML Pages (Templates / Static)
- `frontend/admin_login.html` – Admin login screen
- `frontend/admin_dashboard.html` – Main admin overview and statistical metrics
- `frontend/farmer_management.html` – Farmer accounts directory and details view
- `frontend/appointment_management.html` – Soil testing appointment scheduling & status management
- `frontend/report_management.html` – PDF soil report upload, replacement, and access

### B. Frontend Stylesheets
- `frontend/admin_login.css`
- `frontend/admin_dashboard.css` (contains global design system variables and sidebar rules)
- `frontend/farmer_management.css`
- `frontend/appointment_management.css`
- `frontend/report_management.css`

### C. Frontend JavaScript Files
- `frontend/admin_login.js` (Form handling, client validation, login submit event)
- `frontend/admin_dashboard.js` (Stats rendering, recent appointments table)
- `frontend/farmer_management.js` (Farmer list rendering, search filtering, modal details)
- `frontend/appointment_management.js` (Status filter, search, status action transition triggers)
- `frontend/report_management.js` (Multipart upload handling, validation, table rendering, view/replace actions)

### D. Image Assets
- `frontend/images/farmland.jpg` (Login background)
- `frontend/images/dashboard_bg.jpg` (Dashboard header)
- `frontend/images/farmer_bg.jpg` (Farmer header)
- `frontend/images/appointment_bg.jpg` (Appointment header)
- `frontend/images/report_bg.jpg` (Report header)

---

## 2. Proposed API Endpoints (Pending Team Agreement)

> [!IMPORTANT]
> The endpoints listed below are **proposed contracts** created by Person 3 to guide frontend integration. They are subject to final mutual agreement between Person 1 (Backend) and Person 3 (Frontend/Admin). No backend code has been created or finalized by Person 3.

| Category | Method | Proposed Route | Expected Request Body / Params | Expected Response | Status / Note |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Auth** | `POST` | `/api/admin/login` | `{ "email": "...", "password": "..." }` | `{ "token": "...", "admin": { "name": "...", "email": "..." } }` | ⚠️ Proposed (Pending Agreement) |
| **Auth** | `POST` | `/api/admin/logout` | Header: `Authorization: Bearer <token>` | `{ "message": "Logged out successfully" }` | ⚠️ Proposed (Pending Agreement) |
| **Dashboard** | `GET` | `/api/admin/stats` | Header: `Authorization: Bearer <token>` | `{ "totalFarmers": 42, "pendingAppts": 5, "approvedAppts": 12, "completedAppts": 30, "totalReports": 28 }` | ⚠️ Proposed (Pending Agreement) |
| **Dashboard** | `GET` | `/api/admin/recent-appointments` | Query: `?limit=5` | Array of recent appointment objects | ⚠️ Proposed (Pending Agreement) |
| **Farmers** | `GET` | `/api/admin/farmers` | Query: `?search=...&page=1&limit=10` | `{ "farmers": [...], "total": 42 }` | ⚠️ Proposed (Pending Agreement) |
| **Farmers** | `GET` | `/api/admin/farmers/<id>` | Path: `<id>` | Full farmer profile object | ⚠️ Proposed (Pending Agreement) |
| **Appointments**| `GET` | `/api/admin/appointments` | Query: `?status=...&search=...` | Array of appointment objects | ⚠️ Proposed (Pending Agreement) |
| **Appointments**| `PUT` | `/api/admin/appointments/<id>/status` | `{ "status": "Approved" \| "Rejected" \| "Completed" }` | Updated appointment object | ⚠️ Proposed (Pending Agreement) |
| **Reports** | `GET` | `/api/admin/reports` | Query: `?search=...` | Array of report objects | ⚠️ Proposed (Pending Agreement) |
| **Reports** | `POST` | `/api/admin/reports` | Multipart form: `farmerId`, `appointmentId`, `file` (PDF) | Created report metadata object | ⚠️ Proposed (Pending Agreement) |
| **Reports** | `GET` | `/api/admin/reports/<id>/download`| Header: `Authorization: Bearer <token>` | Binary stream (`application/pdf`) | ⚠️ Proposed (Pending Agreement) |
| **Reports** | `PUT` | `/api/admin/reports/<id>` | Multipart form: `file` (PDF) | Updated report metadata object | ⚠️ Proposed (Pending Agreement) |

---

## 3. Strict Distinction: Frontend Demo vs. Real Backend Functionality

To prevent false assumptions during integration:

1. **Authentication & Session:**
   - *Current Frontend:* Validates email format and ensures non-empty inputs. Simulates login delay with a spinner, displays a simulated error message if empty, or redirects to `admin_dashboard.html`.
   - *Required Backend:* Secure database query with `bcrypt` password verification, issuance of signed JWT or secure session cookie with `HttpOnly`, `SameSite=Strict`, `Secure`.
2. **Data Persistence:**
   - *Current Frontend:* Operates entirely on temporary in-memory JavaScript objects (`demoFarmers`, `demoAppointments`, `demoReports`). Any status updates or uploaded files are stored only in client memory and reset upon page reload.
   - *Required Backend:* Relational SQL persistence (e.g., PostgreSQL or SQLite via SQLAlchemy).
3. **Report File Storage:**
   - *Current Frontend:* Uses `URL.createObjectURL(file)` to generate a transient local browser blob for viewing/downloading in the current session.
   - *Required Backend:* Save uploaded PDF to a secure directory outside the public web root; verify file magic bytes (`%PDF`); scan for malware; serve via streaming responses guarded by authentication.

---

## 4. Business Logic & Security Requirements for Person 1

### A. Appointment Status Transition Rules
The backend **must** strictly enforce the business state machine regardless of frontend checks:
```
[Pending]   ───► [Approved]
[Pending]   ───► [Rejected]
[Approved]  ───► [Completed]
[Rejected]  ───► (No further changes allowed - 400 Bad Request)
[Completed] ───► (No further changes allowed - 400 Bad Request)
```

### B. Access Control & Authorization (RBAC)
- All `/api/admin/*` routes must check for an authenticated user with `role === 'admin'`.
- If an unauthenticated request or a standard farmer JWT accesses an admin route, return `401 Unauthorized` or `403 Forbidden`.

### C. File Upload Security
- Do not rely solely on the `.pdf` extension or the client-supplied `Content-Type` header. Validate the file header bytes on the server (`%PDF-1.`).
- Limit server-side upload body size to 5 MB (`MAX_CONTENT_LENGTH = 5 * 1024 * 1024`).
- Generate unique UUIDs or sanitized filenames when saving files to disk to prevent path traversal (`../../`).

### D. CORS & Headers
- If Flask and the frontend are served on different origins during development, configure Flask-CORS restricted strictly to the frontend origin.
- Set standard security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`).
