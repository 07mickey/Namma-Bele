# Database Design Specification
## Soil Testing Appointment & Report Access Platform

> **Architecture Status:** Implemented & Verified (Expanded Operational & Agricultural Platform)  
> **Schema Definition:** Implemented in `app/schema.sql`  
> **Database Helper & CLI:** Implemented in `app/db.py` (`init-db`, `init-admin`, `init-staff`, `init-demo`)  
> **Current Active Schema:** 18 Relational Tables, 14 Performance Indexes, WAL Mode  
> **Verification Status:** `PRAGMA foreign_key_check` executed with 0 violations  

---

## 1. Overview & Core Philosophy

The database architecture is designed with the following strict priorities:
**Correctness → Security → Maintainability → Concurrency Performance → Scalability**

- **Database Engine:** SQLite 3 with Write-Ahead Logging (`PRAGMA journal_mode = WAL;`).
- **Connection Policy:** Foreign key enforcement (`PRAGMA foreign_keys = ON;`) and 5000ms busy timeout enabled on every connection in `app/db.py`.
- **Data Integrity:** Strict foreign keys with `ON DELETE RESTRICT` for financial and historical audit records, `ON DELETE CASCADE` for owned entity relationships, and `ON DELETE SET NULL` for nullable references.
- **Segregation of Concerns:** Separation of agricultural land parcels (`farm_plots`), sampling visits (`field_visits`), core samples (`soil_samples`), chemical assays (`lab_test_assays`), and postal delivery addresses (`farmer_delivery_addresses`).

---

## 2. Table Specifications (18 Active Tables)

### 2.1 `laboratories` Table
District and regional accredited soil testing laboratories and research centers.

| Column | Type | Nullable | Constraints & Defaults | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INTEGER` | NO | `PRIMARY KEY AUTOINCREMENT` | Unique identifier. |
| `name` | `TEXT` | NO | None | Official institutional name. |
| `code` | `TEXT` | NO | `UNIQUE` | Standard laboratory code (e.g. `DSTL-MND-01`). |
| `district` | `TEXT` | NO | None | Administrative district location. |
| `address` | `TEXT` | NO | None | Postal address. |
| `contact_phone` | `TEXT` | YES | None | Official landline/contact number. |
| `is_active` | `INTEGER` | NO | `DEFAULT 1` | 1 if active, 0 if retired. |
| `created_at` | `TEXT` | NO | `DEFAULT (CURRENT_TIMESTAMP)` | Registration timestamp. |

### 2.2 `users` Table
Stores authentication credentials, contact numbers, and access roles for farmers and all operational staff.

| Column | Type | Nullable | Constraints & Defaults | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INTEGER` | NO | `PRIMARY KEY AUTOINCREMENT` | Unique user identifier. |
| `name` | `TEXT` | NO | None | Full legal or display name. |
| `phone` | `TEXT` | NO | `UNIQUE` | Normalized E.164 phone number. |
| `password_hash` | `TEXT` | NO | None | Salted password hash (`scrypt` / `pbkdf2:sha256`). |
| `role` | `TEXT` | NO | `DEFAULT 'farmer'`, `CHECK (role IN ('farmer', 'admin', 'operator', 'field_worker', 'lab_staff', 'advisor'))` | System authorization role. |
| `account_status` | `TEXT` | NO | `DEFAULT 'ACTIVE'`, `CHECK (account_status IN ('ACTIVE', 'UNCLAIMED', 'SUSPENDED'))` | Account lifecycle status. |
| `created_by_user_id`| `INTEGER` | YES | `FOREIGN KEY -> users(id) ON DELETE SET NULL` | Operator who created assisted record. |
| `assigned_lab_id` | `INTEGER` | YES | `FOREIGN KEY -> laboratories(id) ON DELETE SET NULL` | Bound lab for laboratory technicians. |
| `preferred_language`| `TEXT` | NO | `DEFAULT 'en'` | UI language preference (`en`, `kn`). |
| `created_at` | `TEXT` | NO | `DEFAULT (CURRENT_TIMESTAMP)` | Registration timestamp. |

### 2.3 `farmer_delivery_addresses` Table
Postal delivery addresses separate from agricultural land coordinates.

| Column | Type | Nullable | Constraints & Defaults | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INTEGER` | NO | `PRIMARY KEY AUTOINCREMENT` | Unique address identifier. |
| `farmer_id` | `INTEGER` | NO | `FOREIGN KEY -> users(id) ON DELETE CASCADE` | Farmer owner. |
| `recipient_name` | `TEXT` | NO | None | Name of recipient. |
| `recipient_phone` | `TEXT` | NO | None | Contact phone number for courier. |
| `house_details` | `TEXT` | NO | None | Door number, building, or road. |
| `street_or_village` | `TEXT` | NO | None | Village or street name. |
| `landmark` | `TEXT` | YES | None | Prominent landmark. |
| `taluk` | `TEXT` | NO | None | Sub-district / Taluk. |
| `district` | `TEXT` | NO | None | District. |
| `state` | `TEXT` | NO | `DEFAULT 'Karnataka'` | State. |
| `pincode` | `TEXT` | NO | None | 6-digit postal code. |
| `is_default` | `INTEGER` | NO | `DEFAULT 0` | 1 if default dispatch address. |
| `created_at` | `TEXT` | NO | `DEFAULT (CURRENT_TIMESTAMP)` | Timestamp created. |

### 2.4 `farmer_account_activations` Table
Secure OTP tokens for assisted-registration farmers claiming online access.

| Column | Type | Nullable | Constraints & Defaults | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INTEGER` | NO | `PRIMARY KEY AUTOINCREMENT` | Unique identifier. |
| `farmer_id` | `INTEGER` | NO | `UNIQUE`, `FOREIGN KEY -> users(id) ON DELETE CASCADE` | Farmer account to activate. |
| `claim_token_hash`| `TEXT` | NO | None | SHA-256 hash of activation session token. |
| `otp_hash` | `TEXT` | NO | None | SHA-256 hash of 6-digit verification OTP. |
| `expires_at` | `TEXT` | NO | None | Expiration timestamp (15 minutes). |
| `attempts_remaining`| `INTEGER` | NO | `DEFAULT 5` | Decrementing brute-force counter. |
| `created_at` | `TEXT` | NO | `DEFAULT (CURRENT_TIMESTAMP)` | Generation timestamp. |

### 2.5 `farm_plots` Table
Agricultural land holdings with cadastral survey numbers, acreage, soil and water details.

| Column | Type | Nullable | Constraints & Defaults | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INTEGER` | NO | `PRIMARY KEY AUTOINCREMENT` | Unique plot identifier. |
| `farmer_id` | `INTEGER` | NO | `FOREIGN KEY -> users(id) ON DELETE CASCADE` | Registered farmer owner. |
| `plot_name` | `TEXT` | NO | None | Farmer plot label (e.g. `Canal Side Acre`). |
| `survey_number` | `TEXT` | NO | None | Cadastral land survey number. |
| `area` | `REAL` | NO | `CHECK (area > 0)` | Plot area measurement. |
| `area_unit` | `TEXT` | NO | `DEFAULT 'Acres'`, `CHECK (area_unit IN ('Acres', 'Guntas', 'Hectares'))` | Measurement unit. |
| `soil_type` | `TEXT` | NO | `DEFAULT 'Red Sandy Loam'` | Farmer-observed soil type. |
| `irrigation_source`| `TEXT` | NO | `DEFAULT 'Rainfed'`, `CHECK (irrigation_source IN ('Rainfed', 'Borewell', 'Canal', 'Drip', 'Sprinkler', 'Well'))` | Water source. |
| `landmark` | `TEXT` | YES | None | Local parcel landmark. |
| `taluk` | `TEXT` | YES | None | Taluk location. |
| `district` | `TEXT` | YES | None | District location. |
| `created_at` | `TEXT` | NO | `DEFAULT (CURRENT_TIMESTAMP)` | Registration timestamp. |

### 2.6 `crop_records` Table
Multi-year season-by-season crop rotation history per plot. Standardizes Paddy / Rice naming.

| Column | Type | Nullable | Constraints & Defaults | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INTEGER` | NO | `PRIMARY KEY AUTOINCREMENT` | Unique crop record identifier. |
| `farmer_id` | `INTEGER` | NO | `FOREIGN KEY -> users(id) ON DELETE CASCADE` | Farmer owner. |
| `plot_id` | `INTEGER` | NO | `FOREIGN KEY -> farm_plots(id) ON DELETE CASCADE` | Farm plot parcel. |
| `crop_name` | `TEXT` | NO | None | Standardized crop name (e.g. `Paddy / Rice`). |
| `variety` | `TEXT` | YES | None | Seed variety or cultivar. |
| `year` | `INTEGER` | NO | `CHECK (year >= 2000 AND year <= 2100)` | Cultivation year. |
| `season` | `TEXT` | NO | `CHECK (season IN ('Kharif', 'Rabi', 'Zaid', 'Summer', 'Perennial'))` | Agricultural season. |
| `sowing_date` | `TEXT` | YES | None | Sowing date (`YYYY-MM-DD`). |
| `harvest_date` | `TEXT` | YES | None | Harvest date (`YYYY-MM-DD`). |
| `actual_harvested_quantity` | `REAL` | NO | `DEFAULT 0.0`, `CHECK (actual_harvested_quantity >= 0)` | Total accumulated yield. |
| `quantity_unit` | `TEXT` | NO | `DEFAULT 'Quintals'`, `CHECK (quantity_unit IN ('Quintals', 'Kg', 'Tonnes', 'Bags'))` | Harvest unit. |
| `notes` | `TEXT` | YES | None | Cultivation remarks. |
| `created_at` | `TEXT` | NO | `DEFAULT (CURRENT_TIMESTAMP)` | Created timestamp. |

### 2.7 `harvest_records` Table
Harvest yield batches logged per crop record.

| Column | Type | Nullable | Constraints & Defaults | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INTEGER` | NO | `PRIMARY KEY AUTOINCREMENT` | Unique harvest identifier. |
| `crop_record_id` | `INTEGER` | NO | `FOREIGN KEY -> crop_records(id) ON DELETE CASCADE` | Cultivation season. |
| `harvest_date` | `TEXT` | NO | None | Date crop was reaped. |
| `total_quantity` | `REAL` | NO | `CHECK (total_quantity > 0)` | Batch harvested quantity. |
| `quantity_unit` | `TEXT` | NO | `DEFAULT 'Quintals'`, `CHECK (quantity_unit IN ('Quintals', 'Kg', 'Tonnes', 'Bags'))` | Unit of measurement. |
| `quality_grade` | `TEXT` | YES | `DEFAULT 'Grade A'`, `CHECK (quality_grade IN ('Grade A', 'Grade B', 'Grade C', 'Standard'))` | Harvest quality rating. |
| `storage_location`| `TEXT` | YES | None | Godown or warehouse bay. |
| `notes` | `TEXT` | YES | None | Quality or moisture remarks. |
| `created_at` | `TEXT` | NO | `DEFAULT (CURRENT_TIMESTAMP)` | Logged timestamp. |

### 2.8 `sales_records` Table
Transparent sales records: gross revenue calculated as `(quantity_sold * price_per_unit)`. Never mislabels gross revenue as profit.

| Column | Type | Nullable | Constraints & Defaults | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INTEGER` | NO | `PRIMARY KEY AUTOINCREMENT` | Unique transaction ID. |
| `crop_record_id` | `INTEGER` | NO | `FOREIGN KEY -> crop_records(id) ON DELETE CASCADE` | Crop season reference. |
| `sale_date` | `TEXT` | NO | None | Date of sale transaction. |
| `quantity_sold` | `REAL` | NO | `CHECK (quantity_sold > 0)` | Quantity sold (bounded by available stock). |
| `price_per_unit` | `REAL` | NO | `CHECK (price_per_unit > 0)` | Mandi rate in ₹ per unit. |
| `gross_revenue` | `REAL` | NO | `CHECK (gross_revenue >= 0)` | Total sale value (gross revenue). |
| `buyer_market` | `TEXT` | NO | None | APMC mandi or buyer name. |
| `payment_status` | `TEXT` | NO | `DEFAULT 'Received'`, `CHECK (payment_status IN ('Received', 'Pending', 'Partial'))` | Settlement status. |
| `notes` | `TEXT` | YES | None | Transaction remarks. |
| `created_at` | `TEXT` | NO | `DEFAULT (CURRENT_TIMESTAMP)` | Logged timestamp. |

### 2.9 `appointments` Table
Tracks soil sample collection booking requests submitted by farmers or assisted by operators.

| Column | Type | Nullable | Constraints & Defaults | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INTEGER` | NO | `PRIMARY KEY AUTOINCREMENT` | Unique appointment ID. |
| `farmer_id` | `INTEGER` | NO | `FOREIGN KEY -> users(id) ON DELETE RESTRICT` | Farmer owner. |
| `land_details` | `TEXT` | NO | None | Acreage, crop, and soil description. |
| `address` | `TEXT` | NO | None | Farm parcel collection location. |
| `preferred_date`| `TEXT` | NO | None | Requested sampling date (`YYYY-MM-DD`). |
| `preferred_time`| `TEXT` | NO | `CHECK (preferred_time IN ('09:00-12:00', '14:00-17:00'))` | Time window. |
| `notes` | `TEXT` | YES | None | Farmer instructions. |
| `status` | `TEXT` | NO | `DEFAULT 'Pending'`, `CHECK (status IN ('Pending', 'Approved', 'Rejected', 'Completed'))` | Lifecycle status. |
| `plot_id` | `INTEGER` | YES | `FOREIGN KEY -> farm_plots(id) ON DELETE SET NULL` | Bound farm plot. |
| `delivery_address_id`| `INTEGER`| YES | `FOREIGN KEY -> farmer_delivery_addresses(id) ON DELETE SET NULL` | Postal delivery destination. |
| `created_at` | `TEXT` | NO | `DEFAULT (CURRENT_TIMESTAMP)` | Creation timestamp. |
| `updated_at` | `TEXT` | NO | `DEFAULT (CURRENT_TIMESTAMP)` | Update timestamp. |

### 2.10 `field_visits` Table
Field worker assignment and sample collection visit tracking.

| Column | Type | Nullable | Constraints & Defaults | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INTEGER` | NO | `PRIMARY KEY AUTOINCREMENT` | Unique visit identifier. |
| `appointment_id` | `INTEGER` | NO | `UNIQUE`, `FOREIGN KEY -> appointments(id) ON DELETE CASCADE` | Bound appointment. |
| `assigned_worker_id`| `INTEGER`| YES | `FOREIGN KEY -> users(id) ON DELETE SET NULL` | Assigned technician. |
| `scheduled_date` | `TEXT` | NO | None | Scheduled visit date. |
| `scheduled_slot` | `TEXT` | NO | `CHECK (scheduled_slot IN ('09:00-12:00', '14:00-17:00'))` | Scheduled time slot. |
| `visit_status` | `TEXT` | NO | `DEFAULT 'Scheduled'`, `CHECK (visit_status IN ('Scheduled', 'In_Progress', 'Completed', 'Cancelled', 'Rescheduled'))` | Status of visit. |
| `survey_number` | `TEXT` | YES | None | Verified survey number. |
| `gps_latitude` | `REAL` | YES | None | GPS latitude of sampling point. |
| `gps_longitude` | `REAL` | YES | None | GPS longitude of sampling point. |
| `worker_notes` | `TEXT` | YES | None | Field technician notes. |
| `completed_at` | `TEXT` | YES | None | Visit completion timestamp. |
| `created_at` | `TEXT` | NO | `DEFAULT (CURRENT_TIMESTAMP)` | Created timestamp. |

### 2.11 `soil_samples` Table
Physical sample metadata tagged with a unique barcoded sample code.

| Column | Type | Nullable | Constraints & Defaults | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INTEGER` | NO | `PRIMARY KEY AUTOINCREMENT` | Unique sample identifier. |
| `appointment_id` | `INTEGER` | NO | `FOREIGN KEY -> appointments(id) ON DELETE CASCADE` | Source appointment. |
| `visit_id` | `INTEGER` | YES | `FOREIGN KEY -> field_visits(id) ON DELETE SET NULL` | Field visit record. |
| `sample_code` | `TEXT` | NO | `UNIQUE` | Unique barcode code (`SMP-YYYY-XXXXX`). |
| `assigned_lab_id`| `INTEGER` | YES | `FOREIGN KEY -> laboratories(id) ON DELETE SET NULL` | Testing laboratory. |
| `sampling_depth_cm`| `REAL` | YES | `DEFAULT 15.0` | Core sampling depth. |
| `soil_appearance`| `TEXT` | YES | None | Visual texture & moisture. |
| `sample_status` | `TEXT` | NO | `DEFAULT 'Collected'`, `CHECK (sample_status IN ('Collected', 'In_Transit', 'Received', 'Testing', 'Completed', 'Rejected'))` | Custody status. |
| `collected_at` | `TEXT` | NO | `DEFAULT (CURRENT_TIMESTAMP)` | Collection timestamp. |
| `created_at` | `TEXT` | NO | `DEFAULT (CURRENT_TIMESTAMP)` | Created timestamp. |

### 2.12 `sample_events` Table
Immutable 13-stage timeline event audit trail for sample tracking.

| Column | Type | Nullable | Constraints & Defaults | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INTEGER` | NO | `PRIMARY KEY AUTOINCREMENT` | Event identifier. |
| `sample_id` | `INTEGER` | NO | `FOREIGN KEY -> soil_samples(id) ON DELETE CASCADE` | Tracked sample. |
| `stage_number` | `INTEGER` | NO | `CHECK (stage_number BETWEEN 1 AND 13)` | Sequential stage (1 to 13). |
| `stage_name` | `TEXT` | NO | None | Constant stage name. |
| `status` | `TEXT` | NO | `DEFAULT 'COMPLETED'`, `CHECK (status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED'))` | Event status. |
| `actor_user_id` | `INTEGER` | YES | `FOREIGN KEY -> users(id) ON DELETE SET NULL` | User who triggered event. |
| `actor_role` | `TEXT` | NO | None | Operational role of actor. |
| `department` | `TEXT` | NO | None | Operational unit responsible. |
| `description` | `TEXT` | NO | None | Plain English event description. |
| `details_json` | `TEXT` | YES | None | Structured event metadata. |
| `created_at` | `TEXT` | NO | `DEFAULT (CURRENT_TIMESTAMP)` | Event timestamp. |

### 2.13 `lab_test_assays` Table
Chemical test measurements (pH, EC, OC, N, P, K) with ICAR scientific index ratings.

| Column | Type | Nullable | Constraints & Defaults | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INTEGER` | NO | `PRIMARY KEY AUTOINCREMENT` | Unique assay identifier. |
| `sample_id` | `INTEGER` | NO | `UNIQUE`, `FOREIGN KEY -> soil_samples(id) ON DELETE CASCADE` | Measured sample. |
| `lab_id` | `INTEGER` | NO | `FOREIGN KEY -> laboratories(id) ON DELETE RESTRICT` | Testing laboratory. |
| `tested_by_user_id`| `INTEGER`| NO | `FOREIGN KEY -> users(id) ON DELETE RESTRICT` | Lab chemist who performed assay. |
| `ph_value` | `REAL` | NO | `CHECK (ph_value >= 0.0 AND ph_value <= 14.0)` | Soil pH (0–14 scale). |
| `ec_ds_m` | `REAL` | NO | `CHECK (ec_ds_m >= 0.0)` | Electrical conductivity in dS/m. |
| `organic_carbon_pct`| `REAL`| NO | `CHECK (organic_carbon_pct >= 0.0 AND organic_carbon_pct <= 100.0)` | Soil organic carbon %. |
| `nitrogen_kg_ha` | `REAL` | NO | `CHECK (nitrogen_kg_ha >= 0.0)` | Available Nitrogen (kg/ha). |
| `phosphorus_kg_ha`| `REAL` | NO | `CHECK (phosphorus_kg_ha >= 0.0)` | Available Phosphorus (kg/ha). |
| `potassium_kg_ha` | `REAL` | NO | `CHECK (potassium_kg_ha >= 0.0)` | Available Potassium (kg/ha). |
| `ph_rating` | `TEXT` | NO | None | `Acidic`, `Neutral / Optimal`, `Alkaline`. |
| `ec_rating` | `TEXT` | NO | None | `Normal`, `Critical`, `Saline / Injurious`. |
| `oc_rating` | `TEXT` | NO | None | `Low`, `Medium`, `High`. |
| `n_rating` | `TEXT` | NO | None | `Low`, `Medium`, `High`. |
| `p_rating` | `TEXT` | NO | None | `Low`, `Medium`, `High`. |
| `k_rating` | `TEXT` | NO | None | `Low`, `Medium`, `High`. |
| `lab_status` | `TEXT` | NO | `DEFAULT 'Submitted'`, `CHECK (lab_status IN ('Draft', 'Submitted', 'Authorized', 'Rejected'))` | Workflow state. |
| `authorized_by_user_id`| `INTEGER`| YES | `FOREIGN KEY -> users(id) ON DELETE SET NULL` | Supervisor authorizer (segregation of duties). |
| `authorized_at` | `TEXT` | YES | None | Authorization timestamp. |
| `remarks` | `TEXT` | YES | None | Analytical observations. |
| `completed_at` | `TEXT` | NO | `DEFAULT (CURRENT_TIMESTAMP)` | Assay completion timestamp. |
| `created_at` | `TEXT` | NO | `DEFAULT (CURRENT_TIMESTAMP)` | Record creation timestamp. |

### 2.14 `reports` Table
Stores metadata and filesystem vault storage references for completed PDF reports.

| Column | Type | Nullable | Constraints & Defaults | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INTEGER` | NO | `PRIMARY KEY AUTOINCREMENT` | Unique report identifier. |
| `appointment_id` | `INTEGER` | NO | `UNIQUE`, `FOREIGN KEY -> appointments(id) ON DELETE RESTRICT` | Source appointment. |
| `file_path` | `TEXT` | NO | `UNIQUE` | Internal UUID4 filename (`instance/reports/<uuid>.pdf`). |
| `original_filename`| `TEXT` | NO | None | Sanitized filename restored on download. |
| `file_size_bytes`| `INTEGER`| NO | `CHECK (file_size_bytes > 0)` | File size in bytes (max 10 MB). |
| `checksum_sha256`| `TEXT` | NO | None | SHA-256 cryptographic digest. |
| `uploaded_by` | `INTEGER` | NO | `FOREIGN KEY -> users(id) ON DELETE RESTRICT` | Admin/staff who uploaded PDF. |
| `uploaded_at` | `TEXT` | NO | `DEFAULT (CURRENT_TIMESTAMP)` | Upload timestamp. |
| `assay_id` | `INTEGER` | YES | `FOREIGN KEY -> lab_test_assays(id) ON DELETE SET NULL` | Chemical assay record. |
| `authorized_by` | `INTEGER` | YES | `FOREIGN KEY -> users(id) ON DELETE SET NULL` | Authorizing supervisor. |
| `authorized_at` | `TEXT` | YES | None | Official authorization timestamp. |

### 2.15 `report_dispatches` Table
Physical print queue and Speed Post tracking with immutable address snapshots.

| Column | Type | Nullable | Constraints & Defaults | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INTEGER` | NO | `PRIMARY KEY AUTOINCREMENT` | Unique dispatch ID. |
| `report_id` | `INTEGER` | YES | `FOREIGN KEY -> reports(id) ON DELETE CASCADE` | Digital report reference. |
| `appointment_id` | `INTEGER` | NO | `FOREIGN KEY -> appointments(id) ON DELETE CASCADE` | Source appointment. |
| `recipient_name` | `TEXT` | NO | None | Snapshot of recipient name. |
| `recipient_phone` | `TEXT` | NO | None | Snapshot of recipient phone. |
| `delivery_address_snapshot`| `TEXT`| NO | None | Immutable JSON serialized destination address. |
| `courier_service` | `TEXT` | NO | `DEFAULT 'India Post Speed Post'` | Carrier name. |
| `tracking_number` | `TEXT` | YES | None | 13-character consignment tracking barcode. |
| `dispatch_status` | `TEXT` | NO | `DEFAULT 'Queued'`, `CHECK (dispatch_status IN ('Queued', 'Printed', 'Dispatched', 'Delivered', 'Returned'))` | Postal logistics status. |
| `dispatched_at` | `TEXT` | YES | None | Courier handover timestamp. |
| `delivered_at` | `TEXT` | YES | None | Final delivery timestamp. |
| `created_at` | `TEXT` | NO | `DEFAULT (CURRENT_TIMESTAMP)` | Queueing timestamp. |

### 2.16 `expert_consultations` Table
Advisory questions submitted by farmers to qualified agricultural scientists.

| Column | Type | Nullable | Constraints & Defaults | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INTEGER` | NO | `PRIMARY KEY AUTOINCREMENT` | Unique consultation ID. |
| `farmer_id` | `INTEGER` | NO | `FOREIGN KEY -> users(id) ON DELETE CASCADE` | Asking farmer. |
| `plot_id` | `INTEGER` | YES | `FOREIGN KEY -> farm_plots(id) ON DELETE SET NULL` | Farm parcel context. |
| `report_id` | `INTEGER` | YES | `FOREIGN KEY -> reports(id) ON DELETE SET NULL` | Test report context. |
| `category` | `TEXT` | NO | `CHECK (category IN ('Crop Recommendation', 'Soil Health', 'Pest Control', 'Fertilizer Application', 'Irrigation', 'General Advice'))` | Agronomic topic. |
| `subject` | `TEXT` | NO | None | Summary subject line. |
| `question_text` | `TEXT` | NO | None | Farmer's detailed question. |
| `status` | `TEXT` | NO | `DEFAULT 'OPEN'`, `CHECK (status IN ('OPEN', 'IN_REVIEW', 'ANSWERED', 'CLOSED'))` | Consultation state. |
| `assigned_advisor_id`| `INTEGER`| YES | `FOREIGN KEY -> users(id) ON DELETE SET NULL` | Responding agronomist. |
| `created_at` | `TEXT` | NO | `DEFAULT (CURRENT_TIMESTAMP)` | Created timestamp. |
| `updated_at` | `TEXT` | NO | `DEFAULT (CURRENT_TIMESTAMP)` | Last updated timestamp. |

### 2.17 `consultation_messages` Table
Threaded conversation dialogue between farmer and agricultural expert.

| Column | Type | Nullable | Constraints & Defaults | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INTEGER` | NO | `PRIMARY KEY AUTOINCREMENT` | Message ID. |
| `consultation_id` | `INTEGER` | NO | `FOREIGN KEY -> expert_consultations(id) ON DELETE CASCADE` | Thread ID. |
| `sender_user_id` | `INTEGER` | NO | `FOREIGN KEY -> users(id) ON DELETE CASCADE` | Message author. |
| `sender_role` | `TEXT` | NO | None | Role (`farmer`, `advisor`, `admin`). |
| `message_text` | `TEXT` | NO | None | Detailed guidance message. |
| `attachment_filename`| `TEXT` | YES | None | Optional attached image or file. |
| `created_at` | `TEXT` | NO | `DEFAULT (CURRENT_TIMESTAMP)` | Message timestamp. |

### 2.18 `operator_audit_logs` Table
Immutable audit trail of call-center operator actions.

| Column | Type | Nullable | Constraints & Defaults | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INTEGER` | NO | `PRIMARY KEY AUTOINCREMENT` | Audit log ID. |
| `actor_user_id` | `INTEGER` | NO | `FOREIGN KEY -> users(id) ON DELETE CASCADE` | Operator user. |
| `actor_role` | `TEXT` | NO | None | Actor role. |
| `action` | `TEXT` | NO | None | Action identifier (e.g. `ASSISTED_FARMER_REGISTRATION`). |
| `target_entity_type`| `TEXT` | NO | None | Entity type (`user`, `appointment`). |
| `target_entity_id` | `INTEGER` | YES | None | Entity ID. |
| `details_json` | `TEXT` | YES | None | Action payload snapshot. |
| `ip_address` | `TEXT` | YES | None | Client IP address. |
| `created_at` | `TEXT` | NO | `DEFAULT (CURRENT_TIMESTAMP)` | Action timestamp. |

---

## 3. Database Performance Indexes

Fourteen performance indexes ensure sub-millisecond query execution across foreign keys and status filters:

```sql
CREATE INDEX IF NOT EXISTS idx_appointments_farmer_id ON appointments (farmer_id);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments (status);
CREATE INDEX IF NOT EXISTS idx_field_visits_worker ON field_visits (assigned_worker_id);
CREATE INDEX IF NOT EXISTS idx_field_visits_status ON field_visits (visit_status);
CREATE INDEX IF NOT EXISTS idx_soil_samples_appt ON soil_samples (appointment_id);
CREATE INDEX IF NOT EXISTS idx_soil_samples_code ON soil_samples (sample_code);
CREATE INDEX IF NOT EXISTS idx_sample_events_sample ON sample_events (sample_id);
CREATE INDEX IF NOT EXISTS idx_farm_plots_farmer ON farm_plots (farmer_id);
CREATE INDEX IF NOT EXISTS idx_crop_records_farmer ON crop_records (farmer_id);
CREATE INDEX IF NOT EXISTS idx_harvest_records_crop ON harvest_records (crop_record_id);
CREATE INDEX IF NOT EXISTS idx_sales_records_crop ON sales_records (crop_record_id);
CREATE INDEX IF NOT EXISTS idx_consultations_farmer ON expert_consultations (farmer_id);
CREATE INDEX IF NOT EXISTS idx_consultations_status ON expert_consultations (status);
CREATE INDEX IF NOT EXISTS idx_dispatch_status ON report_dispatches (dispatch_status);
```
