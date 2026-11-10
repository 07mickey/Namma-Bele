# Integration Dependencies

**Date:** 2026-11-02

## 1. Dependencies on Person 1's Flask Backend
- Admin API endpoints are thin wrappers around Person 1’s core services. The following internal service routes must be available:
  - `/api/v1/farmers/*` – CRUD for farmer data.
  - `/api/v1/appointments/*` – CRUD for appointment scheduling and status updates.
  - `/api/v1/reports/*` – Storage and retrieval of soil‑test PDF files.
- Shared SQLite database schema (or equivalent) must include tables: `admin_user`, `farmer`, `appointment`, `soil_report`.
- Person 1 must expose **service‑to‑service authentication** (e.g., signed JWT with `role: service`) that the admin module can use when calling internal APIs.

## 2. Dependencies on Person 2's Farmer Front‑end
- Public read‑only endpoints that the farmer UI consumes:
  - `GET /api/public/farmers/{id}` – Returns limited farmer profile fields.
  - `GET /api/public/appointments?farmer_id=` – Lists a farmer’s own appointments.
  - `GET /api/public/reports/{id}` – Downloads a PDF report; must verify ownership.
- Front‑end expects **CORS** header allowing origin `https://farmer.soilportal.example.com`.
- Farmer UI will use its own JWT (issued by Person 1’s authentication service). Admin module must **not** accept these tokens for admin routes.

## 3. Required API Endpoints (Admin side)
| Category | Endpoint | Method | Auth | Purpose |
|---|---|---|---|---|
| Auth | `/api/admin/login` | POST | Public | Issue admin JWT (role=admin) |
| Auth | `/api/admin/logout` | POST | Admin JWT | Invalidate token |
| Farmers | `/api/admin/farmers` | GET/POST | Admin JWT | List or create farmers |
| Farmers | `/api/admin/farmers/{id}` | GET/PUT/DELETE | Admin JWT | Retrieve, update, delete farmer |
| Appointments | `/api/admin/appointments` | GET/POST | Admin JWT | List or schedule appointments |
| Appointments | `/api/admin/appointments/{id}` | GET/PUT/DELETE | Admin JWT | Manage specific appointment |
| Reports | `/api/admin/reports` | GET/POST | Admin JWT | List or upload PDF reports |
| Reports | `/api/admin/reports/{id}` | GET/DELETE | Admin JWT | Download or remove a report |

## 4. Authentication & Session Requirements
- Admin routes require **JWT** with claim `role: admin` and a short expiration (e.g., 1 hour).
- Tokens must be signed using a shared secret or RSA key known to Person 1.
- Optionally, server‑side session cookies (`HttpOnly`, `Secure`, `SameSite=Strict`) can be used for web UI.
- Farmer JWTs must be rejected on admin endpoints (403 Forbidden).

## 5. Agreed Appointment Statuses
- **Pending** – Created by admin, awaiting farmer confirmation.
- **Approved** – Farmer has confirmed; preparation can begin.
- **Rejected** – Farmer declined or admin cancelled before confirmation.
- **Completed** – Soil test performed and report uploaded.
- All status transitions must be validated by backend logic (Person 1).

## 6. Report Ownership & Access Rules
- Each `soil_report` record is linked to an `appointment_id`.
- Only **admin users** may **list, download, or delete** any report.
- Farmer UI may **download** a report **only if** the report’s `appointment_id` belongs to that farmer.
- Direct URL access without proper JWT must be blocked (401/403).

## 7. Items to Confirm Before Integration
- **Shared secret / public key** for JWT verification between admin module and Person 1.
- Exact **request/response schemas** for farmer, appointment, and report endpoints (field names, types, pagination).
- **CORS configuration** allowing Person 2’s origin and disallowing others.
- **Rate‑limit policy** (e.g., 100 req/min per admin token) to be enforced by Person 1.
- Confirmation that **appointment status enum** matches across services.
- **File storage path** for PDFs and any size limits (max 5 MB) agreed upon.
- **Error handling conventions** (JSON error format, HTTP status codes).

---
*Prepared by Person 3 (Admin Module, Testing & Security).*