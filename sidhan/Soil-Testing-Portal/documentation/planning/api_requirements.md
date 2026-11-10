# Proposed Admin API Requirements

**Date:** 2026-11-02

## Overview
The Admin Module will expose a set of RESTful APIs consumed by the admin frontend (Flask templates/JS) and, where necessary, by Person 2’s farmer frontend for shared data. All endpoints must be secured via JWT‑based authentication (admin role). Responses are JSON unless a file (PDF) is streamed.

---
### Authentication
| Method | Endpoint | Request | Response | Notes |
|---|---|---|---|---|
| `POST` | `/api/admin/login` | `{ "username": "admin", "password": "<plain>" }` | `{ "access_token": "<jwt>", "expires_in": 3600 }` | Returns JWT with `role: admin`. |
| `POST` | `/api/admin/logout` | Header `Authorization: Bearer <jwt>` | `{ "message": "Logged out" }` | Optional token revocation list. |

---
### Farmer Management
| Method | Endpoint | Request | Response | Auth |
|---|---|---|---|---|
| `GET` | `/api/admin/farmers` | – | `[{ farmer_id, name, email, farms: [] }]` | Admin JWT |
| `POST` | `/api/admin/farmers` | `{ "name": "...", "email": "...", "farms": [{"id":...}] }` | Created object with `farmer_id` | Admin JWT |
| `PUT` | `/api/admin/farmers/{farmer_id}` | Partial update JSON | Updated object | Admin JWT |
| `DELETE` | `/api/admin/farmers/{farmer_id}` | – | `{ "deleted": true }` | Admin JWT |

---
### Appointment Management
| Method | Endpoint | Request | Response | Auth |
|---|---|---|---|---|
| `GET` | `/api/admin/appointments` | Query params (`date`, `farmer_id`, `status`) | List of appointments | Admin JWT |
| `POST` | `/api/admin/appointments` | `{ "farmer_id":…, "date": "YYYY‑MM‑DD", "time": "HH:MM", "status": "scheduled" }` | Created appointment | Admin JWT |
| `PUT` | `/api/admin/appointments/{id}` | Partial update | Updated appointment | Admin JWT |
| `DELETE` | `/api/admin/appointments/{id}` | – | `{ "deleted": true }` | Admin JWT |

---
### Soil‑Test PDF Report Management
| Method | Endpoint | Request | Response | Auth |
|---|---|---|---|---|
| `GET` | `/api/admin/reports` | Query (`appointment_id`) | List of report metadata | Admin JWT |
| `POST` | `/api/admin/reports` | `multipart/form-data` with `appointment_id` and `file` (PDF) | `{ "report_id":…, "url": "/api/admin/reports/{id}" }` | Admin JWT |
| `GET` | `/api/admin/reports/{id}` | – | Stream PDF (`application/pdf`) | Admin JWT |
| `DELETE` | `/api/admin/reports/{id}` | – | `{ "deleted": true }` | Admin JWT |

---
### Common Conventions
- **Error format:** `{ "error": "Message", "code": 400 }`.
- **Pagination:** `?page=1&per_page=20` on list endpoints.
- **Rate limiting:** 100 requests/min per admin token.
- **CORS:** Allow origin `https://frontend.admin.soilportal.example.com` only.

---
## Dependencies on Person 1’s Backend
- The admin APIs will delegate to Person 1’s core services for actual data persistence. The above endpoints are thin wrappers that call Person 1’s internal services:
  - Farmer CRUD → `/api/v1/farmers/*`
  - Appointment CRUD → `/api/v1/appointments/*`
  - Report storage → `/api/v1/reports/*`
- Therefore the admin module must agree on request/response schemas with Person 1 and share authentication/authorization tokens (or use service‑to‑service JWT). 

---
## Coordination with Person 2 (Farmer Front‑end)
- Expose **read‑only** endpoints for farmer‑viewable data:
  - `GET /api/public/farmers/{id}` – limited fields (no admin metadata).
  - `GET /api/public/appointments?farmer_id=` – farmer’s own appointments.
  - `GET /api/public/reports/{id}` – PDF download (must verify farmer owns the appointment).
- Person 2 should consume the same JWT issued to the farmer after login; admin JWT must **not** be accepted by the farmer UI.

---
*Prepared for discussion with Person 1 and Person 2.*