# API Contract & Endpoint Specification
## Soil Testing Appointment & Report Access Platform

> **Status:** Authoritative Full-Stack Specification  
> **Total Registered Routes:** 79 (60 REST API Endpoints, 18 Jinja2 HTML Views, 1 Static Handler)  
> **Authentication Mechanism:** Signed Session Cookie (`user_id`, `role`), double-submit CSRF token (`X-CSRF-Token`)  
> **Response Architecture:** Uniform JSON envelope (`{"status": "success", ...}` or `{"error": {"code": "...", "message": "...", "details": {...}}}`)  

---

## 1. Global Conventions & Error Handling

### 1.1 Standard Success Envelope
```json
{
  "status": "success",
  "data": { ... }
}
```

### 1.2 Standard Error Envelope
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Detailed error explanation.",
    "details": {
      "field": "phone"
    }
  }
}
```

### 1.3 Standard HTTP Status Codes
- `200 OK`: Request succeeded.
- `201 Created`: Resource successfully created.
- `400 Bad Request`: Validation failure or malformed JSON payload.
- `401 Unauthorized`: Unauthenticated request (session cookie missing or expired).
- `403 Forbidden`: Authenticated user lacks required role, or violates segregation of duties.
- `404 Not Found`: Target entity does not exist or user lacks ownership (anti-IDOR defense).
- `409 Conflict`: Business logic conflict (e.g. duplicate phone, invalid status transition).
- `413 Payload Too Large`: Upload payload exceeds 12 MB streaming limit.

---

## 2. API Endpoints by Subsystem

### 2.1 System Health (`api_bp`)
| Method | Path | Auth | CSRF | Description |
|---|---|---|---|---|
| `GET` | `/api/health` | Public | Exempt | Returns system status and database ping. |

### 2.2 Authentication & Account Activation (`auth_bp`)
| Method | Path | Auth | CSRF | Description |
|---|---|---|---|---|
| `GET` | `/api/auth/csrf-token` | Public | Exempt | Issues fresh CSRF token bound to session. |
| `POST` | `/api/auth/register` | Public | Yes | Farmer self-registration (forces `role='farmer'`). |
| `POST` | `/api/auth/login` | Public | Yes | Authenticates user via phone & password; sets cookie. |
| `POST` | `/api/auth/logout` | Authenticated | Yes | Clears session cookie and invalidates credentials. |
| `GET` | `/api/auth/me` | Public/Auth | Exempt | Returns current authenticated user and role. |
| `POST` | `/api/auth/claim/initiate`| Public | Yes | Generates 6-digit SMS OTP for assisted account claim. |
| `POST` | `/api/auth/claim/complete`| Public | Yes | Verifies OTP and sets permanent farmer password. |

### 2.3 Farmer Appointments (`appointments_bp`)
| Method | Path | Auth | CSRF | Description |
|---|---|---|---|---|
| `GET` | `/api/appointments` | Farmer | Exempt | Lists appointments owned by the farmer. |
| `POST` | `/api/appointments` | Farmer | Yes | Books appointment with date, slot, and delivery address. |
| `GET` | `/api/appointments/<id>`| Farmer | Exempt | Returns appointment details (enforces ownership). |

### 2.4 Administrative Appointment Oversight (`admin_bp`)
| Method | Path | Auth | CSRF | Description |
|---|---|---|---|---|
| `GET` | `/api/admin/appointments` | Admin | Exempt | Paginated appointment list with status filters. |
| `GET` | `/api/admin/appointments/<id>` | Admin | Exempt | Full appointment details for administrative review. |
| `PATCH`| `/api/admin/appointments/<id>/status` | Admin | Yes | Transitions status (`Pending` -> `Approved`/`Rejected`). |

### 2.5 Field Operations & Sample Tracking (`tracking_bp`)
| Method | Path | Auth | CSRF | Description |
|---|---|---|---|---|
| `GET` | `/api/admin/field-workers` | Admin/Operator | Exempt | Lists active technicians for assignment. |
| `POST` | `/api/admin/appointments/<id>/assign` | Admin/Operator | Yes | Assigns technician and schedules visit. |
| `GET` | `/api/field-worker/visits` | Field Worker | Exempt | Lists visits assigned to authenticated technician. |
| `POST` | `/api/field-worker/visits/<id>/collect` | Field Worker | Yes | Records on-site soil core sampling & GPS. |
| `GET` | `/api/tracking/appointment/<id>` | Farmer/Staff | Exempt | Returns 13-stage timeline for appointment. |
| `GET` | `/api/tracking/sample/<code>` | Farmer/Staff | Exempt | Looks up 13-stage timeline by sample code. |

### 2.6 Laboratory Testing & Dual-Signoff (`lab_bp`)
| Method | Path | Auth | CSRF | Description |
|---|---|---|---|---|
| `GET` | `/api/lab/samples` | Lab Staff/Admin | Exempt | Sample intake queue in laboratory pipeline. |
| `POST` | `/api/lab/samples/<id>/receive` | Lab Staff/Admin | Yes | Logs physical sample arrival at lab (Stage 7). |
| `POST` | `/api/lab/samples/<id>/start-test` | Lab Staff/Admin | Yes | Marks sample under preparation (Stage 8). |
| `POST` | `/api/lab/samples/<id>/assay` | Lab Staff/Admin | Yes | Records quantitative NPK & pH assays. |
| `POST` | `/api/lab/assays/<id>/authorize` | Supervisor/Admin | Yes | Authorizes report (segregation of duties). |

### 2.7 Soil Report Management & PDF Downloads (`reports_bp`)
| Method | Path | Auth | CSRF | Description |
|---|---|---|---|---|
| `POST` | `/api/admin/appointments/<id>/report` | Admin | Yes | Uploads validated PDF report (10 MB max). |
| `GET` | `/api/admin/appointments/<id>/report` | Admin | Exempt | Retrieves report metadata for administrator. |
| `GET` | `/api/admin/appointments/<id>/report/download` | Admin | Exempt | Downloads report PDF for administrator. |
| `GET` | `/api/appointments/<id>/report` | Farmer | Exempt | Retrieves report metadata for farmer owner. |
| `GET` | `/api/appointments/<id>/report/download` | Farmer | Exempt | Streams report PDF to farmer owner. |

### 2.8 Farm Plots & Multi-Year Crop Management (`farm_bp`)
| Method | Path | Auth | CSRF | Description |
|---|---|---|---|---|
| `GET` | `/api/farm/plots` | Farmer/Staff | Exempt | Lists cadastral land plots. |
| `POST` | `/api/farm/plots` | Farmer/Staff | Yes | Registers a new farm parcel with survey number. |
| `PUT` | `/api/farm/plots/<id>` | Farmer/Staff | Yes | Updates plot details. |
| `DELETE`| `/api/farm/plots/<id>` | Farmer/Staff | Yes | Removes a farm plot. |
| `GET` | `/api/farm/crops` | Farmer/Staff | Exempt | Lists multi-year crop rotations. |
| `POST` | `/api/farm/crops` | Farmer/Staff | Yes | Logs seasonal planting (Paddy/Rice normalized). |
| `GET` | `/api/farm/harvests` | Farmer/Staff | Exempt | Lists harvest batches. |
| `POST` | `/api/farm/harvests` | Farmer/Staff | Yes | Records harvested quantity and storage location. |
| `GET` | `/api/farm/sales` | Farmer/Staff | Exempt | Lists sales transactions. |
| `POST` | `/api/farm/sales` | Farmer/Staff | Yes | Records mandi sale with stock limit validation. |
| `GET` | `/api/farm/summary` | Farmer/Staff | Exempt | Aggregates acreage, harvests, and gross revenue. |

### 2.9 Postal Delivery Addresses (`addresses_bp`)
| Method | Path | Auth | CSRF | Description |
|---|---|---|---|---|
| `GET` | `/api/farmers/<id>/delivery-addresses` | Farmer/Staff | Exempt | Lists saved postal addresses for hardcopy delivery. |
| `POST` | `/api/farmers/<id>/delivery-addresses` | Farmer/Staff | Yes | Creates new residential postal address. |
| `PUT` | `/api/farmers/<id>/delivery-addresses/<aid>/default` | Farmer/Staff | Yes | Sets default delivery address for dispatches. |
| `DELETE`| `/api/farmers/<id>/delivery-addresses/<aid>` | Farmer/Staff | Yes | Removes a delivery address. |

### 2.10 Operator Assisted Services (`operator_bp`)
| Method | Path | Auth | CSRF | Description |
|---|---|---|---|---|
| `POST` | `/api/operator/farmers` | Operator/Admin | Yes | Assisted registration (creates UNCLAIMED user). |
| `GET` | `/api/operator/farmers/search` | Operator/Admin | Exempt | Looks up farmers by phone or name. |
| `POST` | `/api/operator/appointments` | Operator/Admin | Yes | Books appointment on behalf of farmer. |
| `GET` | `/api/operator/audit-logs` | Operator/Admin | Exempt | Immutable audit trail of operator actions. |

### 2.11 Expert Agricultural Consultations (`consultations_bp`)
| Method | Path | Auth | CSRF | Description |
|---|---|---|---|---|
| `GET` | `/api/consultations` | Farmer/Staff | Exempt | Lists consultations (filtered by role). |
| `POST` | `/api/consultations` | Farmer/Staff | Yes | Submits a new agronomic question. |
| `GET` | `/api/consultations/<id>` | Farmer/Staff | Exempt | Full conversation thread and context. |
| `POST` | `/api/consultations/<id>/messages` | Farmer/Staff | Yes | Appends expert recommendation or follow-up. |
| `POST` | `/api/consultations/<id>/close` | Farmer/Staff | Yes | Closes an answered consultation. |

### 2.12 Physical Report Postal Dispatch (`dispatch_bp`)
| Method | Path | Auth | CSRF | Description |
|---|---|---|---|---|
| `GET` | `/api/dispatch/queue` | Staff | Exempt | Print queue with delivery address snapshots. |
| `POST` | `/api/dispatch/<id>/print` | Staff | Yes | Marks report printed (Stage 12). |
| `POST` | `/api/dispatch/<id>/dispatch` | Staff | Yes | Dispatches consignment with UPU S10 tracking barcode. |
| `POST` | `/api/dispatch/<id>/deliver` | Staff | Yes | Confirms delivery to doorstep (Stage 13). |

---

## 3. Server-Rendered Jinja2 HTML Views (`views_bp`)

| Route | Template File | Access | Description |
|---|---|---|---|
| `/` | `index.html` | Public | Editorial homepage with M2 hero, bento grid, and spotlight. |
| `/soil-guide` | `soil_guide.html` | Public | 3D Soil Profile diagram and ICAR nutrient science guide. |
| `/contact` | `contact.html` | Public | Kisan helpline numbers and district lab directory. |
| `/login` | `login.html` | Public | Tabbed login: Farmer Login & Staff / Admin Login. |
| `/register` | `register.html` | Public | Self-service registration for farmers. |
| `/claim` | `claim.html` | Public | Account activation wizard for assisted-registration farmers. |
| `/farmer` | `farmer.html` | Farmer | Farmer dashboard, booking wizard, and appointment history. |
| `/farmer/tracking` | `farmer_tracking.html` | Farmer | Real-time 13-stage sample tracking timeline. |
| `/farmer/plots` | `farmer_plots.html` | Farmer | Cadastral land plot registry. |
| `/farmer/crop-history` | `farmer_crop_history.html` | Farmer | Seasonal crop rotation journal. |
| `/farmer/farm-records` | `farmer_farm_records.html`| Farmer | Harvest yields and mandi sales revenue ledger. |
| `/farmer/addresses` | `farmer_addresses.html` | Farmer | Postal delivery destination management. |
| `/farmer/expert-help` | `farmer_expert.html` | Farmer | Q&A consultations with agricultural experts. |
| `/operator` | `operator.html` | Operator/Admin | Assisted farmer registration and appointment desk. |
| `/field-worker` | `field_worker.html` | Field Worker | On-site collection visit list and sample logger. |
| `/lab` | `lab_dashboard.html` | Lab Staff/Admin | Lab intake, N-P-K & pH assays, and supervisor signoff. |
| `/advisor` | `advisor_dashboard.html` | Advisor/Admin | Agronomic consultation queue and recommendation console. |
| `/admin` | `admin.html` | Admin | Operations management and report upload console. |
| `/admin/tracking` | `admin_tracking.html` | Admin | System-wide 13-stage sample tracking monitor. |
| `/admin/dispatch` | `admin_dispatch.html` | Admin/Staff | Physical report print queue and Speed Post dispatch. |
