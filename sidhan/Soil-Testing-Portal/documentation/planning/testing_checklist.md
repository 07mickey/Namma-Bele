# Testing Checklist

**Date:** 2026-11-02

## 1. Authentication Tests
| Test ID | Description | Steps | Expected Result |
|---|---|---|---|
| AUTH-001 | Valid admin login | POST `/api/admin/login` with correct username/password | Returns 200, JWT token, `role: admin` |
| AUTH-002 | Invalid credentials | POST `/api/admin/login` with wrong password | Returns 401 Unauthorized, error message |
| AUTH-003 | Token expiration | Use token after `expires_in` seconds | Returns 401 Unauthorized (token expired) |
| AUTH-004 | Access protected endpoint without token | GET `/api/admin/farmers` without `Authorization` header | Returns 401 Unauthorized |
| AUTH-005 | Access protected endpoint with non‑admin token | Use farmer JWT on admin endpoint | Returns 403 Forbidden |

## 2. Farmer Functionality Tests
| Test ID | Description | Steps | Expected Result |
|---|---|---|---|
| FARM-001 | List farmers | GET `/api/admin/farmers` with admin token | 200 OK, array of farmer objects |
| FARM-002 | Create farmer (valid) | POST `/api/admin/farmers` with required fields | 201 Created, farmer record with ID |
| FARM-003 | Create farmer (missing fields) | POST without `email` | 400 Bad Request, validation error |
| FARM-004 | Update farmer | PUT `/api/admin/farmers/{id}` with partial data | 200 OK, updated fields persisted |
| FARM-005 | Delete farmer | DELETE `/api/admin/farmers/{id}` | 200 OK, `{"deleted":true}` |
| FARM-006 | Access non‑existent farmer | GET `/api/admin/farmers/99999` | 404 Not Found |

## 3. Admin Functionality Tests
| Test ID | Description | Steps | Expected Result |
|---|---|---|---|
| ADMIN-001 | Dashboard load | GET `/admin/dashboard` (HTML page) with admin session | 200 OK, page renders summary cards |
| ADMIN-002 | Unauthorized dashboard access | Access dashboard without login | Redirect to login or 401 Unauthorized |
| ADMIN-003 | Session logout | POST `/api/admin/logout` with valid token | 200 OK, token invalidated |

## 4. Appointment Management Tests
| Test ID | Description | Steps | Expected Result |
|---|---|---|---|
| APPT-001 | List appointments | GET `/api/admin/appointments` | 200 OK, list of appointments |
| APPT-002 | Create appointment (valid) | POST with `farmer_id`, `date`, `time` | 201 Created, appointment returned with status `Pending` |
| APPT-003 | Create appointment (invalid date) | POST with malformed date | 400 Bad Request, validation error |
| APPT-004 | Update appointment status | PUT `/api/admin/appointments/{id}` to `Approved` | 200 OK, status updated |
| APPT-005 | Delete appointment | DELETE `/api/admin/appointments/{id}` | 200 OK, `{"deleted":true}` |
| APPT-006 | Conflict handling | Schedule overlapping appointments for same farmer | 409 Conflict or business‑rule error |

## 5. Report Upload and Access Tests
| Test ID | Description | Steps | Expected Result |
|---|---|---|---|
| REPORT-001 | Upload PDF (valid) | POST multipart `/api/admin/reports` with PDF and `appointment_id` | 201 Created, `report_id` and download URL |
| REPORT-002 | Upload non‑PDF file | POST with `.txt` file | 400 Bad Request, file type rejected |
| REPORT-003 | Download existing report | GET `/api/admin/reports/{id}` with admin token | 200 OK, `application/pdf` stream |
| REPORT-004 | Download non‑existent report | GET with invalid `id` | 404 Not Found |
| REPORT-005 | Delete report | DELETE `/api/admin/reports/{id}` | 200 OK, `{"deleted":true}` |

## 6. Integration Tests (Admin ↔ Backend ↔ Farmer Front‑end)
| Test ID | Description | Steps | Expected Result |
|---|---|---|---|
| INTEG-001 | End‑to‑end farmer creation | Admin creates farmer → Farmer frontend fetches list via public endpoint | Farmer appears in farmer UI
| INTEG-002 | Appointment flow | Admin schedules appointment → Farmer UI shows upcoming appointment → Farmer uploads report → Admin can download report | All steps succeed, data consistent across services
| INTEG-003 | Authorization boundary | Farmer attempts to call admin endpoint `/api/admin/farmers` | 403 Forbidden
| INTEG-004 | Report ownership validation | Farmer tries to download a report belonging to another farmer | 403 Forbidden

---
*Prepared by Person 3 (Admin Module, Testing & Security).*