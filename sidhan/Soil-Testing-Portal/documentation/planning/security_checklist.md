# Security Checklist

**Date:** 2026-11-02

## 1. Farmer A/B Data Isolation
| Test ID | Description | Steps | Expected Result |
|---|---|---|---|
| SEC-001 | Verify farmer A cannot access farmer B data | Use farmer A JWT to request `/api/public/farmers/{B_id}` | 403 Forbidden or 404 Not Found |
| SEC-002 | Verify admin can view all farmers | Admin JWT GET `/api/admin/farmers` | 200 OK, all farmer records returned |

## 2. Admin‑Only Access Protection
| Test ID | Description | Steps | Expected Result |
|---|---|---|---|
| SEC-003 | Access admin dashboard without admin session | Open `/admin/dashboard` in private/incognito browser | Redirect to login or 401 Unauthorized |
| SEC-004 | Call admin API with farmer token | Farmer JWT GET `/api/admin/farmers` | 403 Forbidden |

## 3. Direct URL / API Access Protection
| Test ID | Description | Steps | Expected Result |
|---|---|---|---|
| SEC-005 | Access PDF report URL without authentication | Direct GET to `/api/admin/reports/{id}` without token | 401 Unauthorized |
| SEC-006 | Access public farmer endpoint without token (should be allowed for read‑only data) | GET `/api/public/farmers/{id}` | 200 OK (only allowed fields) |

## 4. IDOR and Invalid ID Testing
| Test ID | Description | Steps | Expected Result |
|---|---|---|---|
| SEC-007 | Insecure Direct Object Reference on appointment | Admin JWT changes appointment ID in request payload to another farmer's ID | 403 Forbidden or validation error |
| SEC-008 | Use non‑numeric ID values | GET `/api/admin/farmers/abc` | 400 Bad Request (invalid format) |
| SEC-009 | Access deleted resource | Delete farmer then GET same ID | 404 Not Found |

## 5. PDF Upload Validation
| Test ID | Description | Steps | Expected Result |
|---|---|---|---|
| SEC-010 | Enforce PDF MIME type | POST `/api/admin/reports` with `.txt` file | 400 Bad Request, file type rejected |
| SEC-011 | File size limit (e.g., 5 MB) | Upload PDF > 5 MB | 413 Payload Too Large |
| SEC-012 | Scan for malicious content (basic) | Upload PDF containing executable payload | Rejected or sanitized, 400 Bad Request |

## 6. Input Validation
| Test ID | Description | Steps | Expected Result |
|---|---|---|---|
| SEC-013 | SQL injection attempt on farmer create | POST `/api/admin/farmers` with `name": "test'); DROP TABLE farmer;--` | Input sanitized, operation fails gracefully with 400 Bad Request |
| SEC-014 | XSS in farmer name | Create farmer with `<script>alert(1)</script>` | Stored value escaped, UI does not execute script |
| SEC-015 | Date format validation on appointment | POST appointment with `date": "2022-13-01` | 400 Bad Request, invalid date error |

## 7. Session & Authentication Security
| Test ID | Description | Steps | Expected Result |
|---|---|---|---|
| SEC-016 | Secure cookie flags | Inspect auth cookie after login | `HttpOnly`, `Secure`, `SameSite=Strict` set |
| SEC-017 | Brute‑force protection | Repeated failed login attempts (>5) | Account lockout or exponential back‑off, 429 Too Many Requests |
| SEC-018 | JWT signature verification | Tamper with token payload and send request | 401 Unauthorized, token rejected |
| SEC-019 | Logout revokes token | Logout, then reuse previous token on protected endpoint | 401 Unauthorized |

---
*Prepared by Person 3 (Testing & Security).*